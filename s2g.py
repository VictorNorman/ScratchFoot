#!/bin/env python3

# Copyright (C) 2016  Victor T. Norman, Calvin College, Grand Rapids, MI, USA
#
# ScratchFoot: a Scratch emulation layer for Greenfoot, along with a program
# to convert a Scratch project to a Greenfoot scenario.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

    
import glob
import json
import os, os.path
import platform
import argparse
from pprint import pprint
import shutil
from subprocess import call, getstatusoutput
import sys

# Global Variables that can be set via command-line arguments.
debug = False
inference = False
name_resolution = False

# Indentation level in outputted Java code.
NUM_SPACES_PER_LEVEL = 4


# A global dictionary mapping (spriteName, variableName) --> variableType.
# We need this so we can generate code that calls the correct
# functions to generate the correct type of results.
# E.g., if a variable is boolean, we'll call boolExpr()
# from setVariables(), not mathExpr().
varTypes = {}

# This variable tracks how many cloud variables have been generated, and
# serves as each cloud var's id
cloudVars = 0

# A global dictionary mapping scratch variable names to the name chosen
# by convertToJavaID or the user.
varNames = {}

class CodeAndCb:
    """This class binds together code, and possibly code that that code
    will call that belongs in a callback."""

    # class variable
    cbScriptId = 0

    def __init__(self):
        self.code = ""
        self.cbCode = ""
        # self.varInitCode = ""
    def addToCbCode(self, code):
        self.cbCode += code
    def getNextScriptId(self):
        ret = CodeAndCb.cbScriptId
        CodeAndCb.cbScriptId += 1
        return ret
    def addToCode(self, code):
        self.code += code


def execOrDie(cmd, descr):
    try:
        print("Executing shell command: " + cmd)
        retcode = call(cmd, shell=True)
        if retcode < 0:
            print("Command to " + descr + " was terminated by signal", -retcode, \
                  file=sys.stderr)
            sys.exit(1)
        else:
            print("Command to " + descr + " succeeded")
    except OSError as e:
        print("Command to " + descr + ": Execution failed:", e, \
              file=sys.stderr)
        sys.exit(1)


def genIndent(level):
    return (" " * (level * NUM_SPACES_PER_LEVEL))



def convertKeyPressName(keyname):
    # Single letter/number keynames in Scratch and Greenfoot are identical.
    # Keyname "space" is the same in each.
    # Scratch does not have keynames for F1, F2, ..., Control, Backspace, etc.
    # 4 arrow keys in Scratch are called "left arrow", "right arrow", etc.
    # In Greenfoot, they are just "left", "right", etc.
    if "arrow" in keyname:
        keyname = keyname.rstrip(" arrow")
    return keyname


def convertToNumber(tok):
    if isinstance(tok, (float, int)):
        return tok
    # Try to convert the string/bool, etc., to an integer.
    try:
        val = int(tok)
    except ValueError:
        try:
            val = float(tok)
        except ValueError:
            raise
    return val


def convertToJavaId(id, noLeadingNumber=True, capitalizeFirst=False):
    """Convert the given string id to a legal java identifier,
    by removing all non-alphanumeric characters (spaces,
    pound signs, etc.).  If noLeadingNumber is true, then
    convert a leading digit to its corresponding name.
    """
    res = ""
    # Drop everything except letters and numbers.
    # Upper case letters in the middle that follow a space,
    # so that we get CamelCase-like results.
    lastWasSpace = False
    for ch in id:
        if ch.isspace():
            lastWasSpace = True
        elif ch.isalpha() or ch.isdigit():
            if lastWasSpace:
                ch = ch.upper()		# does nothing if isdigit.
                lastWasSpace = False
            res += ch
                

    # Look to see if res starts with a digit.
    if noLeadingNumber and res[0].isdigit():
        digit2name = ("zero", "one", "two", "three", "four", "five",
                      "six", "seven", "eight", "nine")
        res = digit2name[int(res[0])] + res[1:]

    if capitalizeFirst and not res[0].isdigit():
        res = res[0].upper() + res[1:]
    return res




class SpriteOrStage:
    '''This is an abstract class that represents either a Stage class or
    Sprite class to be generated in Java.  The two are the same for
    most/all script code generation.  They differ primarily in the set up
    code, constructor code, etc.
    '''
    
    def __init__(self, name, sprData):
        '''Construct an object holding information about the sprite,
        including code we are generating for it, its name, world
        constructor code for it, etc.
        '''

        # The parsed json structure.
        self._sprData = sprData

        self._name = name

        self._fileHeaderCode = ""
        self._worldCtorCode = ""
        self._ctorCode = ""
        # The next 3 code strings are written into the constructor.
        self._regCallbacksCode = ""
        self._costumeCode = ""
        self._initSettingsCode = ""
        
        self._varDefnCode = ""
        self._cbCode = []
        self._addedToWorldCode = ""
        print("\n----------- Sprite: %s ----------------" % self._name)

    def getName(self):
        return self._name


    def genAddSpriteCall(self):
        self._worldCtorCode += '%saddSprite("%s", %d, %d);\n' % \
                              (genIndent(2), self._name, self._sprData['scratchX'],
                               self._sprData['scratchY'])

    def getWorldCtorCode(self):
        return self._worldCtorCode

    def getCostumesCode(self):
        return self._costumeCode


    def genHeaderCode(self):
        """Generate code at the top of the output file -- imports, public class ..., etc."""
        self._fileHeaderCode = "import greenfoot.*;\n\n"
        self._fileHeaderCode += "/**\n * Write a description of class " + self._name + " here.\n"
        self._fileHeaderCode += " * \n * @author (your name)\n * @version (a version number or a date)\n"
        self._fileHeaderCode += " */\n"
        self._fileHeaderCode += "public class " + self._name + " extends Scratch\n{\n"
        

    def genConstructorCode(self):
        """Generate code for the constructor.
        This code will include calls to initialize data, etc., followed by code
        to register callbacks for whenFlagClicked,
        whenKeyPressed, etc.
        """
        self._ctorCode = genIndent(1) + "public " + self._name + "()\n"
        
        self._ctorCode += genIndent(1) + "{\n"
        self._ctorCode += self._costumeCode
        self._ctorCode += self._initSettingsCode
        self._ctorCode += self._regCallbacksCode
        self._ctorCode += genIndent(1) + "}\n"

    def genVariablesDefnCode(self, listOfVars, allChildren, cloudVars):
        """Generate code to define instance variables for this sprite.
        The listOfVars is a list of dictionaries, one per variable (see below).
        The allChildren is the list of dictionaries defined for this
        project. It is necessary because sprites and their scripts (in a
        dictionary with an "objName" key) are in children, also a dictionary
        exists for each variable, with a "cmd" --> "getVar:" entry.  We
        need info from both the listOfVars and each of those other
        variable-specific dictionaries.
        """

        # The listOfVars has this format:
        #  [{ "name": "xloc",
        #     "value": false,
        #     "isPersistent": false
        #     }]
        # We get the name and default value from this easily, but we have to derive
        # the type from the default value.
        # A variable-specific dictionary (in 'children' list) has this format:
        # {
        #			"target": "Sprite1",
        #			"cmd": "getVar:",
        #			"param": "xloc",
        #			"color": 15629590,
        #			"label": "Sprite1: xloc",
        #			"mode": 1,
        #			"sliderMin": 0,
        #			"sliderMax": 100,
        #			"isDiscrete": true,
        #			"x": 5,
        #			"y": 8,
        #			"visible": true
        #  },
        #
        # Algorithm:
        # for each variable in the listOfVars list:
        #   o get the *name* and *value* out.
        #   o derive the *type* from the *value*.
        #   o find the variable's dictionary in allChildren, where
        #     the dictionary has 'cmd' -> 'getVar:' and 'param' -> *name* and
        #     'target' -> *spriteName*.  From that entry,
        #     o get *label*
        #     o get *x* and *y* location
        #     o get *visible*
        #   o generate the variable's definition.
        #   o generate the code in the constructor to create the variable with
        #     the initial value.
        #   o generate code to possibly hide() the variable.
        #   o NOTE: api does not support putting the variable at a x,y
        #     location.   TODO

        global varTypes	# global dictionary
        def chooseType(name, val):
            i, typechosen = deriveType(name, val)
            while not inference:
                try:
                    print("\n\nWhat type of variable should \"" + name + "\": " + str(val) + " be?")
                    type = input("\tInt: A number that won't have decimals\n\tDouble:" + \
                                 " A number that can have decimals\n\tString: Text or letters\n" + \
                                 "This variable looks like: " + typechosen +\
                                 "\nPress enter without typing anything to use suggested type\n>").capitalize()
                    # Try to convert the value to the chosen type, only the first character needs to be entered
                    if type[0] == 'I':
                        return int(val), 'Int'
                    elif type[0] == 'D':
                        return float(val), 'Double'
                    elif type[0] == 'S':
                        return '"' + str(val) + '"', "String"
                    # If ? is chosen, continue with automatic derivation
                    elif type == "?":
                        break
                    print(type, "not recognized, please choose one of these (Int,Double,String)")
                except IndexError:
                    # Nothing was entered
                    break
                except:
                    # If val is not able to be converted to type, it will be set to default, or the user may choose
                    # a different type.
                    if input("Could not convert " + str(val) + " to " + type +\
                             " Set to default value? (y/n)\n>") == "y":
                        if type[0] == 'I':
                            return 0, 'Int'
                        elif type[0] == 'F':
                            return 0.0, 'Double'
                        elif type[0] == 'S':
                            return '""', "String"
            return deriveType(name, val)
        def deriveType(name, val):  
            if isinstance(val, str):
                #
                # See if the string value is a legal integer or floating point number.
                # If it is, assume it should be that.  This seems to be what Scratch
                # does -- represents things as strings, but if legal, treats them
                # as numbers.
                # 
                try:
                    i = int(val)
                    return i, 'Int'
                except:
                    pass
                try:
                    f = float(val)
                    return f, 'Double'
                except:
                    pass
                return '"' + val + '"', 'String'
            elif isinstance(val, bool):
                if val:
                    return "true", 'Boolean'
                else:
                    return "false", 'Boolean'
            elif isinstance(val, int):
                return val, 'Int'
            elif isinstance(val, float):
                return val, 'Double'
            else:
                raise ValueError("deriveType cannot figure out type of -->" + \
                                 str(val) + "<--")

        defnCode = ""

        # Initialization goes into the method addedToWorld() for Sprites, but
        # into the ctor for World.

        # TODO: put this in a subclass implementation...
        if self._name == "Stage":
            self._worldCtorCode += "\n" + genIndent(2) + "// Variable initializations.\n"
        else:
            self._addedToWorldCode += "\n" + genIndent(1) + "private " + worldClassName + " world;"
            self._addedToWorldCode += "\n" + genIndent(1) + "public void addedToWorld(World w)\n"
            self._addedToWorldCode += genIndent(1) + "{\n"
            self._addedToWorldCode += genIndent(2) + "world = (" + worldClassName + ") w;\n"
            self._addedToWorldCode += genIndent(2) + "super.addedToWorld(w);\n";
            self._addedToWorldCode += genIndent(2) + "// Variable initializations.\n"

        for var in listOfVars:  # var is a dictionary.
            name = var['name']
            value = var['value']
            cloud = var['isPersistent']
            # return the varType and the value converted to a java equivalent
            # for that type. (e.g., False --> false)
            # varType is one of 'Boolean', 'Double', 'Int', 'String'
            if cloud:
                value = cloudVars
                cloudVars += 1
                varType = 'Cloud'
                name = name[2:]
            else:
                value, varType = chooseType(name, value)
            try:
                if name_resolution:
                    varNames[name] = convertToJavaId(name, True, False)
                elif not convertToJavaId(name, True, False) == name:
                    varNames[name] = self.resolveName(name)
                else:
                    varNames[name] = convertToJavaId(name, True, False)
            except:
                print("Error converting variable to java id")
                sys.exit(0)
            name = varNames[name]
            for aDict in allChildren:
                if aDict.get('cmd') == 'getVar:' and \
                   aDict.get('param') == name and \
                   aDict.get('target') == self._name:
                    varInfo = aDict
                    # If variable definition dictionary found, use it
                    label = varInfo['label']
                    x = varInfo['x']    # Not used at this time.
                    y = varInfo['y']    # Not used at this time.
                    visible = varInfo['visible']
                    break
            else:
                if cloud:
                    # Cloud variables do not have a definition dictionary, so use default
                    # values.
                    label = name;
                    x = 0
                    y = 0
                    visible = True
                else:
                    # If no variable dict could be found, this variable is never shown
                    # so these values don't matter
                    label = "unknown: " + name
                    x = 0
                    y = 0
                    visible = False
                    print("No variable definition dictionary found in script json:", name)

            # Record this variable in the global variables dictionary.
            # We need this so we can generate code that calls the correct
            # functions to generate the correct type of results.
            # E.g., if a variable is boolean, we'll call boolExpr()
            # from setVariables(), not mathExpr().

            # If the spriteName is "GLOBAL" then it is a global variable.
            # However, we store global variable in the World, so we'll use
            # "GLOBAL" instead.
            if self._name == "Stage":
                varTypes[("GLOBAL", name)] = varType
            else:
                varTypes[(self._name, name)] = varType
            if debug:
                print("Adding entry for", self._name, ",", name,
                      "to dict with value", varType)

            # Something like "Scratch.IntVar score; or ScratchWorld.IntVar score;"
            if self._name == "Stage":
                # Code is going into the World
                self._varDefnCode += genIndent(1) + "ScratchWorld.%sVar %s;\n" % (varType, name)
                self._worldCtorCode += '%s%s = create%sVariable("%s", %s);\n' % \
                            (genIndent(2), name, varType, label, str(value))
                if not visible:
                    self._worldCtorCode += genIndent(2) + name + ".hide();\n"
            else:
                self._varDefnCode += genIndent(1) + "Scratch.%sVar %s;\n" % (varType, name)
                # Something like "score = createIntVariable((MyWorld) world, "score", 0);
                self._addedToWorldCode += '%s%s = create%sVariable((%s) world, "%s", %s);\n' % \
                    (genIndent(2), name, varType, worldClassName, label, str(value))
                if not visible:
                    self._addedToWorldCode += genIndent(2) + name + ".hide();\n"

        # Add blank line after variable definitions.
        self._varDefnCode += "\n"

        # TODO: This is terrible style: hardcoding a decision based on the
        # name of a subclass object.  Fix this!
        if self._name != "Stage":
            # Close the addedToWorld() method definition.
            self._addedToWorldCode += genIndent(1) + "}\n"
            

    def getVarDefnCode(self):
        return self._varDefnCode
    def getAddedToWorldCode(self):
        return self._addedToWorldCode

    def genDefaultAddedToWorld(self):

        # TODO: this code is very similar or repeated from above...  fix this.
        code =  genIndent(1) + "private " + worldClassName + " world;\n"
        code += genIndent(1) + "public void addedToWorld(World w)\n"
        code += genIndent(1) + "{\n"
        code += genIndent(2) + "world = (" + worldClassName + ") w;\n"
        code += genIndent(2) + "super.addedToWorld(w);\n"
        code += genIndent(1) + "}\n\n"
        self._addedToWorldCode += code

    def genCodeForScripts(self):
        # The value of the 'scripts' key is the list of the scripts.  It may be a
        # list of 1 or of many.
        if 'scripts' not in self._sprData:
            print("No scripts found in", self._name)
            if debug:
                print("sprData is -->" + str(self._sprData) + "<--")
            return

        for scr in self._sprData['scripts']:
            # items 0 and 1 in the sublist are the location on the
            # screen of the script. 
            # We don't care about that, obviously.  Item 2 is the actual code.
            script = scr[2]
            codeObj = self.genScriptCode(script)
            self._regCallbacksCode += codeObj.code
            if codeObj.cbCode != "":
                # The script generate callback code.
                self._cbCode.append(codeObj.cbCode)

    def writeCodeToFile(self):

	# Open file with correct name and generate code into there.
        filename = os.path.join(PROJECT_DIR, convertSpriteToFileName(self._name))
        print("Writing code to " + filename + ".")
        outFile = open(filename, "w")
        self.genHeaderCode()
        outFile.write(self._fileHeaderCode)

        outFile.write(self._varDefnCode)

        self.genConstructorCode()
        outFile.write(self._ctorCode)

        for code in self._cbCode:
            outFile.write(code)

        outFile.write(self._addedToWorldCode)

        outFile.write("}\n")
        outFile.close()


    def block(self, level, stmtList):
        """Handle block: a list of statements wrapped in { }."""

        if debug:
            print("block: stmtList = ")
            pprint(stmtList)
        return genIndent(level) + "{\n" + self.stmts(level, stmtList) + \
               genIndent(level) + "}\n"


    def stmts(self, level, stmtList):
        """Generate code for the list of statements, by repeatedly calling stmt()"""
        if stmtList is None:
            return ""
        retStr = ""
        for aStmt in stmtList:
            # Call stmt to generate the statement, appending the result to the
            # overall resulting string.
            retStr += self.stmt(level + 1, aStmt)
        return retStr


    def stmt(self, level, tokenList):
        """Handle a statement, which is a <cmd> followed by expressions.
        The stmt might be something like [doForever [<stmts>]].
        """

        scratchStmt2genCode = {
            'doIf': self.doIf,
            'doIfElse': self.doIfElse,

            # Motion commands
            'forward:': self.motion1Arg,
            'turnLeft:': self.motion1Arg,
            'turnRight:': self.motion1Arg,
            'heading:': self.motion1Arg,
            'gotoX:y:': self.motion2Arg,
            'gotoSpriteOrMouse:': self.motion1Arg,
            'changeXposBy:': self.motion1Arg,
            'xpos:': self.motion1Arg,
            'changeYposBy:': self.motion1Arg,
            'ypos:': self.motion1Arg,
            'bounceOffEdge': self.motion0Arg,
            'setRotationStyle': self.motion1Arg,
            'pointTowards:': self.pointTowards,
            'glideSecs:toX:y:elapsed:from:': self.glideTo,

            # Looks commands
            'say:duration:elapsed:from:': self.sayForSecs,
            'say:': self.say,
            'think:duration:elapsed:from:':self.thinkForSecs,
            'think:': self.think,
            'show': self.show,
            'hide': self.hide,
            'lookLike:': self.switchCostumeTo,
            'nextCostume': self.nextCostume,
            'startScene': self.switchBackdropTo,
            'changeSizeBy:': self.changeSizeBy,
            'setSizeTo:': self.setSizeTo,
            'comeToFront': self.goToFront,
            'goBackByLayers:': self.goBackNLayers,
            'nextScene': self.nextBackdrop,
            'changeGraphicEffect:by:': self.changeGraphicBy,
            'setGraphicEffect:to:': self.setGraphicTo,

            # Pen commands
            'clearPenTrails': self.pen0Arg,
            'stampCostume': self.pen0Arg,
            'putPenDown': self.pen0Arg,
            'putPenUp': self.pen0Arg,
            'penColor:': self.pen1Arg,
            'changePenHueBy:': self.pen1Arg,
            'setPenHueTo:': self.pen1Arg,

            # Data commands
            'setVar:to:': self.setVariable,
            'hideVariable:': self.hideVariable,
            'showVariable:': self.showVariable,
            'changeVar:by:': self.changeVarBy,

            # Events commands
            'broadcast:': self.broadcast,
            'doBroadcastAndWait': self.broadcastAndWait,

            # Control commands
            'doForever': self.doForever,
            'wait:elapsed:from:': self.doWait,
            'doRepeat': self.doRepeat,
            'doWaitUntil': self.doWaitUntil,
            'doUntil': self.repeatUntil,
            'stopScripts': self.stopScripts,
            'createCloneOf': self.createCloneOf,
            'deleteClone': self.deleteThisClone,

            # Sensing commands
            'doAsk': self.doAsk,
            'timerReset': self.resetTimer,

            # Blocks commands
            'call': self.callABlock,
            
            # Sound commands
            'playSound:': self.playSound,
            'doPlaySoundAndWait': self.playSoundUntilDone,

            }
        if debug:
            print("stmt: tokenList = ")
            pprint(tokenList)

        cmd = tokenList[0]

        if cmd in scratchStmt2genCode:
            genCodeFunc = scratchStmt2genCode[cmd]
            # Call the function to generate the code, passing in the rest of
            # the tokens. 
            return genCodeFunc(level, tokenList)
        else:
            return genIndent(level) + 'System.out.println("Unimplemented stmt: ' + cmd + '");\n'


    def boolExpr(self, tokenList):
        """Generate code for a boolean expression.
        It will have the format
        [<boolOp>, <boolExpr>, <boolExpr>], where boolOp is one of "&", "|"     or
        ['not', <boolExpr>]                                                     or
        [<cmpOp>, <mathExpr>, <mathExpr>], where <cmpOp> is one of "<", ">", or "="  or
        ['isTouching:' <val>], etc.						    or
        False	when the boolean expression was left empty in Scratch
        """
        resStr = ""
        if tokenList == False:  # means no condition was provided in Scratch.
            return "(false)"
        firstOp = tokenList[0]
        if firstOp in ('&', '|'):
            assert len(tokenList) == 3
            resStr += "(" + self.boolExpr(tokenList[1])
            if firstOp == '&':
                resStr += " && "
            else:
                resStr += " || "
            resStr += self.boolExpr(tokenList[2]) + ")"
        elif firstOp == 'not':
            assert len(tokenList) == 2
            resStr += "(! " + self.boolExpr(tokenList[1]) + ")"
        elif firstOp in ('<', '>', '='):
            assert len(tokenList) == 3
            resStr += "(" + self.mathExpr(tokenList[1])
            if firstOp == '<':
                resStr += " < "
            elif firstOp == '>':
                resStr += " > "
            else: 	# must be ' = '
                resStr += " == "
            resStr += self.mathExpr(tokenList[2]) + ")"
        elif firstOp == 'touching:':
            arg = tokenList[1]
            if arg == "_mouse_":
                resStr += "(isTouchingMouse())"
            elif arg == "_edge_":
                resStr += "(isTouchingEdge())"
            else:
                # touching another sprite
                resStr += '(isTouching("' + tokenList[1] + '"))'
        elif firstOp == 'touchingColor:':
            resStr += "(isTouchingColor(new java.awt.Color(" + self.mathExpr(tokenList[1]) + ")))"
        elif firstOp == 'keyPressed:':
            resStr += '(isKeyPressed("' + convertKeyPressName(tokenList[1]) + '"))'
        elif firstOp == 'mousePressed':
            resStr += "(isMouseDown())"
        elif firstOp == 'readVariable':
            resStr += self.readVariable(tokenList[1])
        elif firstOp == False:
            resStr += "false"
        else:
            raise ValueError(firstOp)
        return resStr

    def strExpr(self, tokenOrList):
        """Evaluate a string-producing expression (or literal).
        """
        if debug:
            print("strExpr: tokenOrList is", tokenOrList)

        if isinstance(tokenOrList, str):
            # Wrap in double quotes like Java.
            return '"' + str(tokenOrList) + '"'

        if len(tokenOrList) == 1:
            # Handle built-in variables.
            op = tokenOrList[0]
            if op == "sceneName":
                return "backdropName()"
            elif op == "username":
                return "username NOT IMPLEMENTED"
        if len(tokenOrList) == 2:
            if tokenOrList[0] == "readVariable":
                return self.readVariable(tokenOrList[1])
        if len(tokenOrList) == 3:
            op, tok1, tok2 = tokenOrList	
            if op == "concatenate:with:":
                # This is a little strange because I know you can join a string
                # with an integer literal or expression result in Scratch.
                return "join(" + self.strExpr(tok1) + ", " + self.strExpr(tok2) + ")"
            elif op == "letter:of:":
                return "letterNOf(" + self.strExpr(tok2) + ", " + self.mathExpr(tok1) + ")"
            elif op == 'getAttribute:of:':
                return self.getAttributeOf(tok1, tok2)
            else:
                raise ValueError("Unknown string operator " + op)
        raise ValueError("Unknown string operator " + tokenOrList[0])

    def mathExpr(self, tokenOrList):

        if isinstance(tokenOrList, str):
            # We have a literal value that is a string.  We should convert it
            # to an integer, if possible.
            # This is to cover cases like if you have (in Scratch) x position <
            # 0: Scratch give us "0" in the json.
            # (Convert to str() because everything we return is a str.)
            try:
                return str(int(tokenOrList))
            except ValueError:
                # The literal value is not an integer, so it should be a float
                return str(float(tokenOrList))

        if not isinstance(tokenOrList, list):
            # It is NOT an expression and not a string (handled above).
            # make it a string because everything we return is a string.
            return str(convertToNumber(tokenOrList))

        # It is a list, so it is an expression.

        if len(tokenOrList) == 1:
            # Handle built-in variables.
            op = tokenOrList[0]
            if op == "xpos":
                return "getX()"
            elif op == "ypos":
                return "getY()"
            elif op == "heading":
                return "getDirection()"
            elif op == "costumeIndex":	# Looks menu's costume # block
                # TODO: getCostumeNumber() and size() below are inconsistent names
                # I think getCostumeNumber() should be changed to just costumeNumber()...
                # This would be a change to Scratch.java.
                return "getCostumeNumber()"
            elif op == 'backgroundIndex':
                return 'getBackdropNumber()'
            elif op == "scale": 		# Look menu's size block
                return "size()"
            elif op == "mousePressed":
                return "isMouseDown()"
            elif op == "mouseX":
                return "getMouseX()"
            elif op == "mouseY":
                return "getMouseY()"
            elif op == "timer":
                return "getTimer()"
            elif op == "timeStamp":		# TODO: daysSince2000 in scratch.  float result
                return "daysSince2000 not implemented"
            else:
                raise ValueError("Unknown operation " + op)

        if len(tokenOrList) == 2:
            # Handle cases of operations that take 1 argument.
            op, tok1 = tokenOrList
            if op == "rounded":
                return "Math.round((float) " + self.mathExpr(tok1) + ")"
            elif op == "stringLength:":
                return "lengthOf(" + self.strExpr(tok1) + ")"
            elif op == "distanceTo:":
                if tok1 == "_mouse_":
                    return "distanceToMouse()"
                else:   # must be distance to a sprite
                    # TODO: this call requires a Scratch object, not a string.  Make string available.
                    return 'distanceTo("' + tok1 + '")'
            elif op == "getTimeAndDate":
                if tok1 == "minute":
                    return 'getCurrentMinute()'
                elif tok1 == "month":
                    return 'getCurrentMonth()'
                elif tok1 == "second":
                    return 'getCurrentSecond()'
                elif tok1 == "hour":
                    return 'getCurrentHour()'
                elif tok1 == "year":
                    return 'getCurrentYear()'
                elif tok1 == 'day of week':
                    return 'getCurrentDayOfWeek()'
                elif tok1 == 'date':
                    return 'getCurrentDate()'
                else:
                    raise ValueError(tokenOrList)
            elif op == 'readVariable':
                return self.readVariable(tok1)
            else:
                raise ValueError("Unknown operation " + op)

        assert len(tokenOrList) == 3	# Bad assumption?
        op, tok1, tok2 = tokenOrList	

        # Handle special cases before doing the basic ones which are inorder
        # ops (value op value).
        if op == 'randomFrom:to:':
            # tok1 and tok2 may be math expressions.
            return "pickRandom(" + self.mathExpr(tok1) + ", " + self.mathExpr(tok2) + ")"
        elif op == 'getParam':
            # getting a parameter value in a custom block.
            # format is ["getParam", "varname", 'r'] -- not sure what the 'r' is for.
            return tok1	# it is already a str
        elif op == "computeFunction:of:":
            assert tok1 in ("abs", "floor", "ceiling", "sqrt", "sin", "cos", "tan",
                          "asin", "acos", "atan", "ln", "log", "e ^", "10 ^")
            op2Func = {
                "abs": "Math.abs(",
                "floor": "Math.floor(",
                "ceiling": "Math.ceil(",
                "sqrt": "Math.sqrt(",
                "sin": "Math.sin(",
                "cos": "Math.cos(",
                "tan": "Math.tan(",
                "asin": "Math.asin(",
                "acos": "Math.acos(",
                "atan": "Math.atan(",
                "ln": "Math.log(",
                "log": "Math.log10(",
                "e ^": "Math.exp(",
                "10 ^": "Math.pow(10, "
                }
            return op2Func[tok1] + self.mathExpr(tok2) + ")"
        elif op == "getAttribute:of:":
            return self.getAttributeOf(tok1, tok2)
        else:
            assert op in ('+', '-', '*', '/', '%')
        
        if op == '%':
            resStr = "Math.floorMod(" + self.mathExpr(tok1) + ", " + self.mathExpr(tok2) + ")"
            return resStr

        resStr = "(" + self.mathExpr(tok1)
        if op == '+':
            resStr += " + "
        elif op == '-':
            resStr += " - "
        elif op == '*':
            resStr += " * "
        elif op == '/':
            resStr += " / "		# TODO: handle floating pt/int div.
        else:
            raise ValueError(op)
        resStr += self.mathExpr(tok2) + ")"
        return resStr


    def getAttributeOf(self, tok1, tok2):
        """Return code to handle the various getAttributeOf calls
        from the sensing block.
        """
        if tok2 == '_stage_':
            if tok1 == 'backdrop name':
                return "backdropName()"
            elif tok1 == 'backdrop #':
                return "world.getBackdropNumber()"
            elif tok1 == 'volume':
                return ' Volume not implemented '
            else:
                # TODO: We must assume that this is a variable, as not all variable have necessarily
                # been parsed yet. Note that because of this, we cannot look up the actual name
                # of the variable, we must use the unsanitized name.
                return 'world.' + tok1 + '.get()'

        mapping = { 'x position': 'xPositionOf',
                    'y position': 'yPositionOf',
                    'direction': 'directionOf',
                    'costume #': 'costumeNumberOf',
                    'costume name': 'costumeNameOf',   # TODO: implement this.
                    'size': 'sizeOf',
                    }
        if tok1 in mapping:
            return mapping[tok1] + '("' + tok2 + '")'
        else:   # volumeOf, backdropNumberOf
            # TODO: We must assume that this is a variable, as not all variable have necessarily
            # been parsed yet. Note that because of this, we cannot look up the actual name
            # of the variable, we must use the unsanitized name. TODO fix this 
            return '((' + tok2 + ')world.getActorByName("' + tok2 + '")).' + tok1 + '.get()'

    def whenFlagClicked(self, codeObj, tokens):
        """Generate code to handle the whenFlagClicked block.
        All code in tokens goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        # Build a name like whenFlagClickedCb0 
        cbName = 'whenFlagClickedCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenFlagClicked("' + cbName + '");\n')

        level = 1    # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(level, tokens) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)


    def whenSpriteCloned(self, codeObj, tokens):
        """Generate code to handle the whenCloned block.
        All code in tokens goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        cbName = 'whenIStartAsACloneCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenIStartAsAClone("' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(1, tokens) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)

        # TODO: we should have this code in one place!, and not here!
        # Generate a copy constructor too.
        cbStr = "\n\n" + genIndent(1) + "// copy constructor, required for cloning\n"
        cbStr += genIndent(1) + "public " + self._name + "(" + \
                 self._name + " other, int x, int y) {\n"
        cbStr += genIndent(2) + "super(other, x, y);\n"
        cbStr += genIndent(2) + "// add code here to copy any instance variables'\n"
        cbStr += genIndent(2) + "// values from other to this.\n"
        cbStr += genIndent(1) + "}\n\n"
        codeObj.addToCbCode(cbStr)


    def whenKeyPressed(self, codeObj, key, tokens):
        """Generate code to handle the whenKeyPressed block.  key is
        the key to wait for, and tokens is the list of stmts to be put
        into a callback to be called when that key is pressed.
        """
        scriptNum = codeObj.getNextScriptId()
        key = convertKeyPressName(key)

        # Build a name like whenAPressedCb0 or whenLeftPressedCb0.
        cbName = 'when' + key.capitalize() + 'PressedCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenKeyPressed("' +
                          key + '", "' + cbName + '");\n')

        level = 1    # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                "(Sequence s)\n"
        cbStr += self.block(level, tokens) + "\n"  # add blank line after defn.

        codeObj.addToCbCode(cbStr)


    def whenIReceive(self, codeObj, message, tokens):
        """Generate code to handle the whenIReceive block.  message is
        the message to wait for, and tokens is the list of stmts to be put
        into a callback to be called when that message is received.
        """
        scriptNum = codeObj.getNextScriptId()

        # Build a name like whenIReceiveMessage1Cb0
        messageId = convertToJavaId(message, noLeadingNumber=False, capitalizeFirst=True)
        cbName = 'whenIReceive' + messageId + 'Cb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenRecvMessage("' +
                          message + '", "' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        # All cb code is at level 1
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + "(Sequence s)\n"
        cbStr += self.block(1, tokens) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr) 


    def doForever(self, level, tokens):
        """Generate doForever code.  tokens is a list of comments.
        forever loop is turned into a while (true) loop, with the last
        operation being a yield(s) call.
        """
        retStr = genIndent(level) + "while (true)\t\t// forever loop\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.stmts(level, tokens[1])
        retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def doIf(self, level, tokens):
        """Generate code for if <test> : <block>.  Format of tokens is
        'doIf' [test expression] [true-block]
        """
        assert len(tokens) == 3 and tokens[0] == "doIf"

        # Handle the boolean expression
        # We don't generate parens around the boolExpr as it will put them there.
        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(tokens[1])
        resStr += "\n"
        resStr += self.block(level, tokens[2])
        return resStr


    def doIfElse(self, level, tokens):
        """Generate code for if <test> : <block> else: <block>.  Format of tokens is
        'doIfElse' [test expression] [true-block] [else-block]
        """

        assert len(tokens) == 4 and tokens[0] == 'doIfElse'

        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(tokens[1])
        resStr += "\n"
        resStr += self.block(level, tokens[2])
        resStr += genIndent(level) + "else\n"
        resStr += self.block(level, tokens[3])
        return resStr


    def motion0Arg(self, level, tokens):
        """Generate code to handle Motion blocks with 0 arguments"""
        assert len(tokens) == 1
        cmd = tokens[0]
        if cmd == "bounceOffEdge":
            return genIndent(level) + "ifOnEdgeBounce();\n"
        else:
            raise ValueError(cmd)

    def motion1Arg(self, level, tokens):
        """Generate code to handle Motion blocks with 1 argument:
        forward:, turnLeft:, turnRight:, etc."""
        assert len(tokens) == 2
        cmd, arg = tokens
        if cmd == "forward:":
            return genIndent(level) + "move(" + self.mathExpr(arg) + ");\n"
        elif cmd == "turnRight:":
            return genIndent(level) + "turnRightDegrees((int) " + self.mathExpr(arg) + ");\n"
            # TODO: be nice to get rid of the (int)
            # but would require knowing if mathExpr is
            # returning an int type or float...
            # OR, add turnRightDegrees(float) and convert it.
        elif cmd == "turnLeft:":
            return genIndent(level) + "turnLeftDegrees((int) " + self.mathExpr(arg) + ");\n"
            # TODO: be nice to get rid of the (int)
            # but would require knowing if mathExpr is
            # returning an int type or float...
        elif cmd == "heading:":
            return genIndent(level) + "pointInDirection((int) " + self.mathExpr(arg) + ");\n"
        elif cmd == "gotoSpriteOrMouse:":
            if arg == "_mouse_":
                return genIndent(level) + "goToMouse();\n"
            elif arg == "_random_":
                return genIndent(level) + "goToRandomPosition();\n"
            else:
                return genIndent(level) + "goTo(\"" + arg + "\");\n"
            # TODO: Looks like there is something new: gotoRandomPosition()
        elif cmd == "changeXposBy:":
            return genIndent(level) + "changeXBy(" + self.mathExpr(arg) + ");\n"
        elif cmd == "xpos:":
            return genIndent(level) + "setXTo((int) " + self.mathExpr(arg) + ");\n" 
        elif cmd == "changeYposBy:":
            return genIndent(level) + "changeYBy(" + self.mathExpr(arg) + ");\n"
        elif cmd == "ypos:":
            return genIndent(level) + "setYTo((int) " + self.mathExpr(arg) + ");\n"
        elif cmd == "setRotationStyle":
            resStr = genIndent(level) + "setRotationStyle("
            if arg in ("left-right", "leftRight"):
                return resStr + "RotationStyle.LEFT_RIGHT);\n"
            elif arg in ("don't rotate", "none"):
                return resStr + "RotationStyle.DONT_ROTATE);\n"
            elif arg in ("all around", "normal"):
                return resStr + "RotationStyle.ALL_AROUND);\n"
            else:
                raise ValueError(cmd)
        else:
            raise ValueError(cmd)

    def motion2Arg(self, level, tokens):
        """Generate code to handle Motion blocks with 2 arguments:
        gotoX:y:, etc."""
        cmd, arg1, arg2 = tokens
        if cmd == "gotoX:y:":
            return genIndent(level) + "goTo((int) " + self.mathExpr(arg1) + \
                   ", (int) " + self.mathExpr(arg2) + ");\n"
        else:
            raise ValueError(cmd)

    def pointTowards(self, level, tokens):
        """Generate code to turn the sprite to point to something.
        """
        cmd, arg1 = tokens
        if arg1 == '_mouse_':
            return genIndent(level) + "pointTowardMouse();\n"
        else:   # pointing toward a sprite
            return genIndent(level) + 'pointToward("' + arg1 + '");\n'


    def glideTo(self, level, tokens):
        """Generate code to make the sprite glide to a certain x,y position
        in a certain amount of time.
        Format of the cmd is: ["glideSecs:toX:y:elapsed:from:", time, x, y]
        """
        cmd, time, x, y = tokens
        return genIndent(level) + "glideTo(s, %s, %s, %s);\n" % \
               (self.mathExpr(time), self.mathExpr(x), self.mathExpr(y))

    def sayForSecs(self, level, tokens):
        """Generate code to handle say <str> for <n> seconds.
        """
        cmd, arg1, arg2 = tokens
        assert cmd == 'say:duration:elapsed:from:'
        return genIndent(level) + "sayForNSeconds(s, " + self.strExpr(arg1) + ", " + \
               self.mathExpr(arg2) + ");\n"

    def say(self, level, tokens):
        """Generate code to handle say <str>.
        """
        cmd, arg1 = tokens
        assert cmd == "say:"
        return genIndent(level) + "say(" + self.strExpr(arg1) + ");\n"
    
    def thinkForSecs(self, level, tokens):
        """Generate code to handle say <str> for <n> seconds.
        """
        cmd, arg1, arg2 = tokens
        assert cmd == 'think:duration:elapsed:from:'
        return genIndent(level) + "thinkForNSeconds(s, " + self.strExpr(arg1) + ", " + \
               self.mathExpr(arg2) + ");\n"
    
    def think(self, level, tokens):
        """Generate code to handle say <str>.
        """
        cmd, arg1 = tokens
        assert cmd == "think:"
        return genIndent(level) + "think(" + self.strExpr(arg1) + ");\n"

    def show(self, level, tokens):
        """Generate code for the show block.
        """
        assert tokens[0] == "show"
        return genIndent(level) + "show();\n"

    def hide(self, level, tokens):
        """Generate code for the show block.
        """
        assert tokens[0] == "hide"
        return genIndent(level) + "hide();\n"

    def switchCostumeTo(self, level, tokens):
        """Generate code for the switch costume block.
        """
        cmd, arg1 = tokens
        assert cmd == "lookLike:"
        try:
            return genIndent(level) + "switchToCostume(" + self.strExpr(arg1) + ");\n"
        except ValueError:
            # if strExpr is unable to resolve arg1, use mathExpr instead
            return genIndent(level) + "switchToCostume(" + self.mathExpr(arg1) + ");\n"

    def nextCostume(self, level, tokens):
        """Generate code for the next costume block.
        """
        assert tokens[0] == "nextCostume"
        return genIndent(level) + "nextCostume();\n"

    def switchBackdropTo(self, level, tokens):
        """Generate code to switch the backdrop.
        """
        cmd, arg1 = tokens
        assert cmd == "startScene"
        return genIndent(level) + "world.switchBackdropTo(" + self.strExpr(arg1) + ");\n"

    def nextBackdrop(self, level, tokens):
        """Generate code to switch to the next backdrop.
        """
        return genIndent(level) + "world.nextBackdrop();\n"

    def changeSizeBy(self, level, tokens):
        """Generate code to change the size of the sprite
        """
        cmd, arg1 = tokens
        assert cmd == "changeSizeBy:"
        return genIndent(level) + "changeSizeBy((int) " + self.mathExpr(arg1) + ");\n"

    def setSizeTo(self, level, tokens):
        """Generate code to change the size of the sprite to a certain percentage
        """
        cmd, arg1 = tokens
        assert cmd == "setSizeTo:"
        return genIndent(level) + "setSizeTo((int) " + self.mathExpr(arg1) + ");\n"

    def goToFront(self, level, tokens):
        """Generate code to move the sprite to the front
        """
        assert tokens[0] == "comeToFront"
        return genIndent(level) + "goToFront();\n"

    def goBackNLayers(self, level, tokens):
        """Generate code to move the sprite back 1 layer in the paint order
        """
        cmd, arg1 = tokens
        assert cmd == "goBackByLayers:"
        return genIndent(level) + "goBackNLayers((int) " + self.mathExpr(arg1) + ");\n"

    def changeGraphicBy(self, level, tokens):
        cmd, arg1, arg2 = tokens
        assert(cmd == "changeGraphicEffect:by:")
        if arg1 == "ghost":
            return genIndent(level) + "changeGhostEffectBy(" + self.mathExpr(arg2) + ");\n"
        else:
            return genIndent(level) + "// " + arg1 + " effect is not implemented\n" 
        
    def setGraphicTo(self, level, tokens):
        cmd, arg1, arg2 = tokens
        assert(cmd == "setGraphicEffect:to:")
        if arg1 == "ghost":
            return genIndent(level) + "setGhostEffectTo(" + self.mathExpr(arg2) + ");\n"
        else:
            return genIndent(level) + "// " + arg1 + " effect is not implemented\n" 
        
    def pen0Arg(self, level, tokens):
        """Generate code to handle Pen blocks with 0 arguments"""
        assert len(tokens) == 1
        resStr = genIndent(level)
        cmd = tokens[0]
        if cmd == "clearPenTrails":
            return resStr + "clear();\n"
        elif cmd == "stampCostume":
            return resStr + "stamp();\n"
        elif cmd == "putPenDown":
            return resStr + "penDown();\n"
        elif cmd == "putPenUp":
            return resStr + "penUp();\n"
        else:
            raise ValueError(cmd)

    def pen1Arg(self, level, tokens):
        """Generate code to handle Pen blocks with 1 argument."""

        assert len(tokens) == 2
        cmd, arg = tokens
        resStr = genIndent(level)
        if cmd == "penColor:":
            # arg is an integer representing a color.  
            # TODO: need to add code to import java.awt.Color  ??
            # TODO: we also will have problems here if we have to create
            # multiple variables in the same block.  They cannot both be named
            # "color".  If the order of rgb in the number from scratch is
            # correct, we can inline the creation of the color object to solve
            # this problem. 
            resStr += "java.awt.Color color = new java.awt.Color((int) " + self.mathExpr(arg) + ");\n"
            return resStr + genIndent(level) + "setPenColor(color);\n"
        elif cmd == "changePenHueBy:":
            return resStr + "changePenColorBy(" + self.mathExpr(arg) + ");\n"
        elif cmd == "setPenHueTo:":
            return resStr + "setPenColor(" + self.mathExpr(arg) + ");\n"
        else:
            raise ValueError(cmd)

    def getTypeAndLocalGlobal(self, varTok):
        """Look up the token representing a variable name in the varTypes
        dictionary.  If it is found, return the type and whether it
        is a local variable or global.  Global is known if it is found
        in GLOBAL object.  Raise ValueError if it isn't found
        in the dictionary.
        """
        
        isGlobal = False
        # TODO: move varTypes into the Sprite deifnition, and make a global mapping
        # called something like GlobalVarTypes, or access the global
        # variables from the Stage object.
        varType = varTypes.get((self._name, varTok))
        if varType is None:
            varType = varTypes.get(("GLOBAL", varTok))
            if varType is None:
                raise ValueError("Sprite " + self._name + " variable " +
                             varTok + " unknown.")
            else:
                isGlobal = True
        return (varType, isGlobal)

    def setVariable(self, level, tokens):
        """Set a variable's value from within the code.
        Generate code like this:
        var.set(value)
        tokens is: ["setVar:to:", "varName", [expression]]

        The variable may be sprite-specific or global.  We have to check
        both dictionaries to figure it out.
        """

        varType, isGlobal = self.getTypeAndLocalGlobal(varNames[tokens[1]])
        if varType == 'Boolean':
            val = self.boolExpr(tokens[2])
        elif varType in ('Int', 'Double'):
            val = self.mathExpr(tokens[2])
        else:
            val = self.strExpr(tokens[2])

        if isGlobal:
            # Something like: world.counter.set(0);
            return genIndent(level) + "world.%s.set(%s);\n" % \
                   (varNames[tokens[1]], val)
        else:
            return genIndent(level) + varNames[tokens[1]] + ".set(" + val + ");\n"


    def readVariable(self, varname):
        """Get a variable's value from within the code.
        Generate code like this:
        var.get() or
        world.varname.get()

        The variable may be sprite-specific or global.  We have to check
        both dictionaries to figure it out.
        """

        varType, isGlobal = self.getTypeAndLocalGlobal(varNames[varname])
        if isGlobal:
            # Something like: world.counter.get();
            return "world.%s.get()" % (varNames[varname])
        else:
            return varNames[varname] + ".get()"


    def hideVariable(self, level, tokens):
        """Generate code to hide a variable.
        """
        varType, isGlobal = self.getTypeAndLocalGlobal(varNames[tokens[1]])
        if isGlobal:
            # Something like: world.counter.hide();
            return genIndent(level) + "world.%s.hide();\n" % \
                   (varNames[tokens[1]])
        else:
            return genIndent(level) + varNames[tokens[1]] + ".hide();\n"


    def showVariable(self, level, tokens):
        """Generate code to hide a variable.
        """
        varType, isGlobal = self.getTypeAndLocalGlobal(varNames[tokens[1]])
        if isGlobal:
            # Something like: world.counter.show();
            return genIndent(level) + "world.%s.show();\n" % \
                   (varNames[tokens[1]])
        else:
            return genIndent(level) + varNames[tokens[1]] + ".show();\n"


    def changeVarBy(self, level, tokens):
        """Generate code to change the value of a variable.
        Code will be like this:
        aVar.set(aVar.get() + 3);
        """
        varType, isGlobal = self.getTypeAndLocalGlobal(varNames[tokens[1]])
        if isGlobal:
            # Something like:
            # world.counter.set(world.counter.get() + 1);
            return genIndent(level) + \
                   "world.%s.set(world.%s.get() + %s);\n" % \
                   (varNames[tokens[1]], varNames[tokens[1]], self.mathExpr(tokens[2]))
        else:
            return genIndent(level) + varNames[tokens[1]] + ".set(" + \
                   varNames[tokens[1]] + ".get() + " + self.mathExpr(tokens[2]) + ");\n"

    def broadcast(self, level, tokens):
        """Generate code to handle sending a broacast message.
        """
        cmd, arg1 = tokens
        assert cmd == "broadcast:"
        return genIndent(level) + "broadcast(" + self.strExpr(arg1) + ");\n"


    def broadcastAndWait(self, level, tokens):
        """Generate code to handle sending a broacast message and
        waiting until all the handlers have completed.
        """
        cmd, arg1 = tokens
        assert cmd == "doBroadcastAndWait"
        return genIndent(level) + "// TODO: broadcastAndWait() not implemented yet.);\n"


    def doAsk(self, level, tokens):
        """Generate code to ask the user for input.  Returns the resulting String."""

        assert len(tokens) == 2 and tokens[0] == "doAsk"
        quest = tokens[1]
        return genIndent(level) + "String answer = askStringAndWait(" + \
               self.strExpr(quest) + ");\t\t// may want to replace answer with a better name\n"


    def doWait(self, level, tokens):
        """Generate a wait call."""
        assert len(tokens) == 2 and tokens[0] == "wait:elapsed:from:"
        return genIndent(level) + "wait(s, " + self.mathExpr(tokens[1]) + ");\n"


    def doRepeat(self, level, tokens):
        """Generate a repeat <n> times loop.
        """
        assert len(tokens) == 3 and tokens[0] == "doRepeat"

        retStr = genIndent(level) + "for (int i = 0; i < " + \
                 self.mathExpr(tokens[1]) + "; i++)\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.stmts(level, tokens[2])
        retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def doWaitUntil(self, level, tokens):
        """Generate doWaitUtil code: in java we'll do this:
           while (true) {
               if (condition)
                   break;
               yield(s);
           }
        """
        assert len(tokens) == 2 and tokens[0] == 'doWaitUntil'
        retStr =  genIndent(level) + "// wait until code\n"
        retStr += genIndent(level) + "while (true) {\n"
        retStr += genIndent(level + 1) + "if (" + self.boolExpr(tokens[1]) + ")\n"
        retStr += genIndent(level + 2) + "break;\n"
        retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def repeatUntil(self, level, tokens):
        """Generate doUntil code, which translates to this:
           while (! condition)
           {
               stmts
               yield(s);
           }
        """
        assert len(tokens) == 3 and tokens[0] == "doUntil"

        retStr =  genIndent(level) + "// repeat until code\n"
        retStr += genIndent(level) + "while (! " + self.boolExpr(tokens[1]) + ")\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.stmts(level, tokens[2])
        retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def stopScripts(self, level, tokens):
        """Generate code to stop all scripts.
        """
        assert len(tokens) == 2 and tokens[0] == "stopScripts"
        if tokens[1] == "all":
            return genIndent(level) + "stopAll();\n"
        elif tokens[1] == "this script":
            return genIndent(level) + "stopThisScript();\n"
        elif tokens[1] == "other scripts in sprite":
            return genIndent(level) + "stopOtherScriptsInSprite();\n"
        else:
            raise ValueError("stopScripts: unknown type")


    def createCloneOf(self, level, tokens):
        """Create a clone of the sprite itself or of the given sprite.
        """
        assert len(tokens) == 2 and tokens[0] == "createCloneOf"
        if tokens[1] == "_myself_":
            return genIndent(level) + "createCloneOfMyself();\n"

        return genIndent(level) + 'createCloneOf("' + tokens[1] + '");\n'


    def deleteThisClone(self, level, tokens):
        """Delete this sprite.
        """
        assert len(tokens) == 1 and tokens[0] == "deleteClone"
        return genIndent(level) + "deleteThisClone();\n"


    def resetTimer(self, level, tokens):
        return genIndent(level) + "resetTimer();\n"


    def genProcDefCode(self, codeObj, tokens):
        """Generate code for a custom block definition in Scratch.
        All the generated code goes into codeObj's cbCode since it doesn't
        belong in the constructor.
        """
        # Tokens is like this:
        # [["procDef", "name", [list of param-names], [list of values (not used)], false],
        #  [code here]]

        print("===========")
        print(tokens)
        decl = tokens[0]
        code = tokens[1:]
        # blockName and param types: e.g., block3args %n %s %b
        blockAndParamTypes = decl[1]    
        paramNames = decl[2]

        # TODO: need to sanitize blockName, paramNames, etc.

        # Need to split up blockAndParamTypes to extract the name of the
        # procedure and the types of the parameters.
        # The name of the procedure can have spaces, and there can be words
        # in the middle of the param specs.
        # Examples:
        # "aBlock"  -- no params
        # "a block" -- no params, but name has spaces
        # "block2args %n %n" -- 2 "number" params.  We'll use float for all
        #     numbers.
        # "blockwithtext %s a word or four %b" -- 2 params, a string and a
        #     boolean and words in the middle.

        # For now we'll just take the first words before the first % sign and
        # remove spaces and make that the procedure name.
        # TODO: somehow append words in the middle of the param list into the
        # name of the procedure.
        #
        paramTypes = []
        idx = 0
        # Look from beginning until we see a %.  The first part is the blockName.
        blockName = ""
        while idx < len(blockAndParamTypes):
            if blockAndParamTypes[idx] == "%":
                break
            blockName += blockAndParamTypes[idx]
            idx += 1
        # Trim off any trailing spaces in blockName
        blockName = blockName.strip()
        blockName = convertToJavaId(blockName, True, False)

        # Now, scanning through %? and words, which we'll drop for now.
        while idx < len(blockAndParamTypes):
            # TODO: perhaps rewrite this with str.find() or str.index().
            if blockAndParamTypes[idx] == "%":
                # Now, we are looking at %.  Must be %s, %b, or %n.
                idx += 1
                if blockAndParamTypes[idx] == "s":
                    paramTypes.append("String")
                elif blockAndParamTypes[idx] == "b":
                    paramTypes.append("boolean")
                elif blockAndParamTypes[idx] == "n":
                    paramTypes.append("float")	# TODO: probably usually int
                else:
                    raise ValueError("unknown Block param type %" +
                                     blockAndParamTypes[idx])
            # eat up everything else.
            idx += 1
        assert len(paramTypes) == len(paramNames)
        
        if len(paramTypes) == 0:
            codeObj.addToCbCode(genIndent(1) + "private void " + blockName + "(Sequence s")
        else:
            codeObj.addToCbCode(genIndent(1) + "private void " + blockName + "(Sequence s, ")

        for i in range(len(paramTypes)):
            codeObj.addToCbCode(paramTypes[i] + " " + paramNames[i])
            # Add following ", " if not add end of list.
            if i < len(paramTypes) - 1:
                codeObj.addToCbCode(", ")

        codeObj.addToCbCode(")\n")
        codeObj.addToCbCode(self.block(1, code))
        codeObj.addToCbCode("\n")	# add blank line after function defn.
        return codeObj


    def callABlock(self, level, tokens):
        """Generate a call to a custom-defined block.
        Format of tokens is: ["call", "blockToCall", param code]
        blockToCall has the param type specs in it: "blockToCall %n %s %b"
        We need to strip these out.
        """
        func2Call = tokens[1]
        firstPercent = func2Call.find("%")
        if firstPercent == -1:
            assert len(tokens) == 2    # just "call" and "blockToCall"
            return genIndent(level) + convertToJavaId(func2Call, True, False) + "(s);\n"
        func2Call = func2Call[0:firstPercent]
        func2Call = func2Call.strip()	# remove trailing blanks.

        resStr = genIndent(level) + convertToJavaId(func2Call, True, False) + "(s, "
        for i in range(2, len(tokens) - 1):
            resStr += self.mathExpr(tokens[i]) + ", "
        resStr += self.mathExpr(tokens[-1]) + ");\n"
        return resStr

    def playSound(self, level, tokens):
        """ Play the given sound
        """
        assert len(tokens) == 2 and tokens[0] == "playSound:"
        # TODO: should tokens[1] be a strExpr()?
        return genIndent(level) + "playSound(\"" + tokens[1] + "\");\n"

    def playSoundUntilDone(self, level, tokens):
        """ Play the given sound without interrupting it.
        """
        assert len(tokens) == 2 and tokens[0] == "doPlaySoundAndWait"
        # TODO: should tokens[1] be a strExpr()?
        return genIndent(level) + "playSoundUntilDone(\"" + tokens[1] + "\");\n"

    def resolveName(self, name):
        """Ask the user what each variable should be named if it is not a
        legal identifier
        """
        while True:
            try:
                print("\"" + name + "\" is not a valid java variable name.")
                n = input("Java variables must start with a letter and contain only letters and numbers.\n" +\
                      "Enter a new name, or type nothing to use \"" + convertToJavaId(name, True, False) + "\"\n>")
                if n == "":
                    return convertToJavaId(name, True, False)
                name = n
                if convertToJavaId(n, True, False) == n:
                    return n;
            except IndexError:
                # The variable name has no valid characters
                print("\"" + name + "\" must have some alphanumeric character in order to suggest a name")
                name = "variable:" + name
            

              
    def genScriptCode(self, script):
        """Generate code (and callback code) for the given script, which may be
        associated with a sprite or the main stage.
        """

        codeObj = CodeAndCb()	# Holds all the code that is generated.

        # script is a list of these: [[cmd] [arg] [arg]...]
        # The script starts with whenGreenFlag, whenSpriteClicked, etc. --
        # the "hat" blocks.
        if script[0] == ['whenGreenFlag']:
            self.whenFlagClicked(codeObj, script[1:])
        elif script[0] == ['whenCloned']:
            self.whenSpriteCloned(codeObj, script[1:])
        elif script[0] == ['whenClicked']:
            self.whenClicked(codeObj, script[1:])
        elif isinstance(script[0], list) and script[0][0] == 'whenKeyPressed':
            self.whenKeyPressed(codeObj, script[0][1], script[1:])
        elif isinstance(script[0], list) and script[0][0] == 'whenIReceive':
            self.whenIReceive(codeObj, script[0][1], script[1:])
        elif isinstance(script[0], list) and script[0][0] == 'procDef':
            # Defining a procedure in Scratch.
            self.genProcDefCode(codeObj, script)

        # If not in one of the above "hat blocks", then it is an
        # orphaned bit of code that will not be run in either Scratch
        # or ScratchFoot.

        # TODO: need to implement whenSwitchToBackdrop in
        # Scratch.java and add code here to handle it.

        return codeObj

# ---------------------------------------------------------------------------
# End of SpriteOrStage class definition.
# ---------------------------------------------------------------------------


class Sprite(SpriteOrStage):
    '''This class represents a Sprite for code generation.'''
    def __init__(self, sprData):

        # Handle sprites with names that are illegal Java identifiers.
        # E.g., the sprite could be called "1", but we cannot create a "class 1".
        name = convertToJavaId(sprData['objName'], True, True)

        super().__init__(name, sprData)

    def genLoadCostumesCode(self, costumes):
        """Generate code to load costumes from files for a sprite.
        """
        # print("genLoadCC: costumes ->" + str(costumes) + "<-")
        resStr = ""
        imagesDir = os.path.join(PROJECT_DIR, "images")
        for cos in costumes:
            # costume's filename is the baseLayerID (which is a small integer
            # (1, 2, 3, etc.)) plus ".png"
            fname = str(cos['baseLayerID']) + ".png"
            resStr += genIndent(2) + 'addCostume("' + fname + \
                      '", "' + cos['costumeName'] + '");\n'
        self._costumeCode += resStr

    def genInitSettingsCode(self):
        """Generate code to set the sprite's initial settings, like its
        location on the screen, the direction it is facing, whether shown
        or hidden, etc.
        """
        resStr = ""

        # Set the initial costume (NOTE: could use the name of the costume instead of index...)
        resStr = genIndent(2) + 'switchToCostume(' + str(self._sprData['currentCostumeIndex'] + 1) + ');\n'
        if self._sprData['scale'] != 1:
            resStr += genIndent(2) + 'setSizeTo((int)' + str(self._sprData['scale'] * 100) + ');\n'
        if not self._sprData['visible']:
            resStr += genIndent(2) + 'hide();\n';
        resStr += genIndent(2) + 'pointInDirection((int) ' + str(self._sprData['direction']) + ');\n';
        # TODO: need to test this!
        resStr += self.motion1Arg(2, ['setRotationStyle', self._sprData['rotationStyle']])
        self._initSettingsCode += resStr

    def whenClicked(self, codeObj, tokens):
        """Generate code to handle the whenClicked block.
        All code in tokens goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        cbName = 'whenSpriteClickedCb' + str(scriptNum)
        codeObj.addToCode(genIndent(2) + 'whenSpriteClicked("' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(1, tokens) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)


class Stage(SpriteOrStage):
    '''This class represents the Stage class.'''
    def __init__(self, sprData):
        super().__init__("Stage", sprData)

        self._bgCode = ""

    
    def genConstructorCode(self):
        """Generate code for the constructor.
        This code will include calls to initialize data, etc., followed by code
        to register callbacks for whenFlagClicked,
        whenKeyPressed, etc.
        Differs from super class in that the costumes code not generated
        for Stage.
        """
        self._ctorCode = genIndent(1) + "public " + self._name + "()\n"
        
        self._ctorCode += genIndent(1) + "{\n"
        self._ctorCode += self._initSettingsCode
        self._ctorCode += self._regCallbacksCode
        self._ctorCode += genIndent(1) + "}\n"

    def genLoadCostumesCode(self, costumes):
        """Generate code to load backdrops from files for the Stage.
        Note that this code is actually included in the World constructor.
        """
        # print("genLoadCC: costumes ->" + str(costumes) + "<-")
        resStr = ""
        imagesDir = os.path.join(PROJECT_DIR, "images")
        for cos in costumes:
            # costume's filename is the baseLayerID (which is a small integer
            # (1, 2, 3, etc.)) plus ".png"
            fname = str(cos['baseLayerID']) + ".png"
            resStr += genIndent(2) + 'addBackdrop("' + fname + \
                      '", "' + cos['costumeName'] + '");\n'
        self._costumeCode += resStr

    def whenClicked(self, codeObj, tokens):
        """Generate code to handle the whenClicked block.
        All code in tokens goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        cbName = 'whenStageClickedCb' + str(scriptNum)
        codeObj.addToCode(genIndent(2) + 'whenStageClicked("' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(1, tokens) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)

    def genInitSettingsCode(self):
        """Generate code to set the Stages initial settings: 
        Set the image for the Stage to bgImg -- a transparent image.  Backdrops are
        part of the World in Greenfoot, not the Stage object.
        """
        self._initSettingsCode += genIndent(2) + "bgImg.clear();\n" + \
                                  genIndent(2) + "setImage(bgImg);\n"

    def genBackgroundHandlingCode(self):
        #
        # Create the static variable "bgImg" which is a transparent image
        # for the stage onto which all drawing will be done.  That way
        # the background image can be changed but the drawing remains, just
        # like in Scratch.
        #
        self._bgCode = genIndent(1) + \
                    "static GreenfootImage bgImg = new GreenfootImage(ScratchWorld.SCRATCH_WIDTH,\n" + genIndent(1) + \
                    "                                                 ScratchWorld.SCRATCH_HEIGHT);\n"
        # Generate the accessor for the static background image.
        self._bgCode += genIndent(1) + "// The background image here is a transparent image\n"
        self._bgCode += genIndent(1) + "// that Scratch draws on to, instead of drawing on \n"
        self._bgCode += genIndent(1) + "// on the greenfoot image.  This way we can switch \n"
        self._bgCode += genIndent(1) + "// backgrounds and keep the stuff that has been drawn.\n"
        self._bgCode += genIndent(1) + "static public GreenfootImage getBackground() { return bgImg; }\n"

    def writeCodeToFile(self):

	# Open file with correct name and generate code into there.
        filename = os.path.join(PROJECT_DIR, convertSpriteToFileName(self._name))
        print("Writing code to " + filename + ".")
        outFile = open(filename, "w")
        self.genHeaderCode()
        outFile.write(self._fileHeaderCode)

        self.genConstructorCode()
        outFile.write(self._ctorCode)

        for code in self._cbCode:
            outFile.write(code)

        outFile.write(self._addedToWorldCode)
        outFile.write(self._bgCode)

        outFile.write("}\n")
        outFile.close()

# End of Stage class definition
# ---------------------------------------------------------------------------

def convertSpriteToFileName(sprite):
    """Make the filename with all words from sprite capitalized and
    joined, with no spaces between."""
    words = sprite.split()
    return ''.join(words) + ".java"



def genWorldHeaderCode(classname):
    """return code that goes into the World.java file, to define the class,
    constructor, call super(), etc.
    """
    boilerplate = """
import greenfoot.*;

/**
 * Write a description of class %s here.
 * 
 * @author (your name) 
 * @version (a version number or a date)
 */
public class %s extends ScratchWorld
{
"""
    return boilerplate % (classname, classname)


def genWorldCtorHeader(classname):
    boilerplate = """
    public %s()
    {
        // To change world size, pass in width, height values to super() below.
        super();
"""
    return boilerplate % classname


# ---------------------------------------------------------------------------
#                ----------------- main -------------------
# ---------------------------------------------------------------------------

# Set up arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("-d", "--dotypeinference", action="store_true", help="Automatically infer variable types")
parser.add_argument("-r", "--resolvevariablenames", action = "store_true", help="Automatically convert to java ids")
parser.add_argument("scratch", help="Location of scratch sb2 file")
parser.add_argument("greenfoot", help="Location of greenfoot project directory")
args = parser.parse_args()
# Apply arguments
if args.verbose:
    debug = True
if args.dotypeinference:
    inference = True
if args.resolvevariablenames:
    name_resolution = True
SCRATCH_FILE = args.scratch.strip()
# Take off spaces and a possible trailing "/"
PROJECT_DIR = args.greenfoot.strip().rstrip("/")

SCRATCH_PROJ_DIR = "scratch_code"

if not os.path.exists(SCRATCH_FILE):
    print("Scratch download file " + SCRATCH_FILE + " not found.")
    sys.exit(1)
if not os.path.exists(PROJECT_DIR):
    if (input("Project directory not found, generate it? (y/n)\n>") == "y"):
        print("Generating new project directory...")
        os.makedirs(PROJECT_DIR)
    else:
        print("Project directory could not be found")
        sys.exit(1)
if not os.path.isdir(PROJECT_DIR):
    print("Greenfoot folder " + PROJECT_DIR + " is not a directory.")
    sys.exit(1)

# Make a directory into which to unzip the scratch zip file.
scratch_dir = os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR)
try:
    os.mkdir(scratch_dir)
except FileExistsError as e:
    pass    # If the directory exists already, no problem.

# Unzip the .sb2 file into the project/scratch_code directory.
print("Unpacking Scratch download file.")
shutil.unpack_archive(SCRATCH_FILE, scratch_dir, "zip")

imagesDir = os.path.join(PROJECT_DIR, "images")
soundsDir = os.path.join(PROJECT_DIR, "sounds")

# Make directories if they don't exist yet
if not os.path.exists(imagesDir):
    os.makedirs(imagesDir)
if not os.path.exists(soundsDir):
    os.makedirs(soundsDir)

print("Copying image files to " + imagesDir)

files2Copy = glob.glob(os.path.join(scratch_dir, "*.png"))
for f in files2Copy:
    # Copy png files over to the images dir, but if they are large
    # (which probably means they are background images) convert
    # them to 480x360.
    res = getstatusoutput("identify " + f)
    if res[0] != 0:
        print(res[1])
        sys.exit(1)
    # Output from identify is like this:
    # 3.png PNG 960x720 960x720+0+0 8-bit sRGB 428KB 0.000u 0:00.000
    size = res[1].split()[2]     # got the geometry.
    width, height = size.split("x")	 # got the width and height, as strings
    width = int(width)
    height = int(height)
    if width > 480:
        # For now, just make 480x360.  This may not be correct in all cases.
        dest = os.path.join(imagesDir, os.path.basename(f))
        execOrDie("convert -resize 480x360 " + f + " " + dest,
              "copy and resize png file")
    else:
        dest = os.path.join(imagesDir, os.path.basename(f))
        execOrDie("convert -resize 50% " + f + " " + dest,
              "copy and resize png file")

# Convert svg images files to png files in the images dir.
files2Copy = glob.glob(os.path.join(scratch_dir, "*.svg"))
for f in files2Copy:
    # fname is just the file name -- all directories removed.
    fname = os.path.basename(f)
    dest = os.path.join(imagesDir, fname)
    dest = os.path.splitext(dest)[0] + ".png"  # remove extension and add .png
    # background -None keeps the transparent part of the image transparent.
    # -resize 50% shrinks the image by 50% in each dimension.  Then image is then
    # same size as you see on the screen with Scratch in the web browser.
    execOrDie("convert -background None " + f + " " + dest,
              "convert svg file to png")
# Copy Scratch.java and ScratchWorld.java to GF project directory
# They must be in the same directory as s2g.py
try: 
    # If the file already exists, skip copying it
    if not os.path.isfile(os.path.join(PROJECT_DIR, "Scratch.java")):
        shutil.copyfile("Scratch.java", os.path.join(PROJECT_DIR, "Scratch.java"))
        print("Scratch.java copied successfully")
    else:
        print("Scratch.java was already in the project directory")
    if not os.path.isfile(os.path.join(PROJECT_DIR, "ScratchWorld.java")):
        shutil.copyfile("ScratchWorld.java", os.path.join(PROJECT_DIR, "ScratchWorld.java"))
        print("ScratchWorld.java copied successfully")
    else:
        print("ScratchWorld.java was already in the project directory")
except:
    print("\n\tScratch.java and ScratchWorld.java were NOT copied!")
    
try: 
    # If the file already exists, skip copying it
    
    shutil.copyfile("say.png", os.path.join(imagesDir, "say.png"))
    print("say.png copied successfully")
    shutil.copyfile("say2.png", os.path.join(imagesDir, "say2.png"))
    print("say2.png copied successfully")
    shutil.copyfile("say3.png", os.path.join(imagesDir, "say3.png"))
    print("say3.png copied successfully")
    shutil.copyfile("think.png", os.path.join(imagesDir, "think.png"))
    print("think.png copied successfully")
except:
    print("\n\tImages for say/think were NOT all copied!")


# End of preparing directories, copying files, etc,
# ---------------------------------------------------------------------------


# Now, (finally!), open the project.json file and start processing it.
with open(os.path.join(scratch_dir, "project.json")) as data_file:
    data = json.load(data_file)

spritesData = data['children']

# We'll need to write configuration "code" to the greenfoot.project file.  Store
# the lines to write out in this variable.
projectFileCode = []

# Determine the name of the ScratchWorld subclass.  This variable below
# is used in some code above to generate casts.  I know this is a very bad
# idea, but hey, what are you going to do...
# Take the last component of the PROJECT_DIR, convert it to a legal
# Java identifier, then add World to end.

worldClassName = convertToJavaId(os.path.basename(PROJECT_DIR).replace(" ", ""), True, True) + "World"

# If there are global variables, they are defined in the outermost part
# of the json data, and more info about each is defined in objects labeled
# with "target": "Stage" in 'childen'.
# These need to be processed before we process any Sprite-specific code
# which may reference these global variables.

# stage information is in the top-most area of the json.
stage = Stage(data)

# Code to be written into the World.java file.
worldCtorCode = ""
worldDefnCode = ""
initCode = ""
if 'variables' in data:
    stage.genVariablesDefnCode(data['variables'], data['children'], cloudVars)


# ---------------------------------------------------------------------------
# Start processing each sprite's info: scripts, costumes, variables, etc.
# ---------------------------------------------------------------------------
for sprData in spritesData:
    if 'objName' in sprData:

        sprite = Sprite(sprData)

        # Write out a line to the project.greenfoot file to indicate that this
        # sprite is a subclass of the Scratch class.
        projectFileCode.append("class." + sprite.getName() + ".superclass=Scratch\n")

        # Generate world construct code that adds the sprite to the world.
        # TODO: could we embed this in a "bigger" call like genWorldConstructorCode...
        sprite.genAddSpriteCall()

        sprite.genLoadCostumesCode(sprData['costumes'])
        if debug:
            print("CostumeCode is ", sprite.getCostumesCode())

	# Like location, direction, shown or hidden, etc.
        sprite.genInitSettingsCode()
        if debug:
            print("Initial Settings Code is ", sprite.getInitSettingsCode())

        # Generate a line to the project.greenfoot file to set the image
        # file, like this: 
        #     class.Sprite1.image=1.png
        projectFileCode.append("class." + sprite.getName() + ".image=" + \
                           str(sprData['costumes'][0]['baseLayerID']) + ".png\n")

        # Move all of this sprites sounds to project/sounds/[spritename]
        if 'sounds' in sprData:
            if not os.path.exists(os.path.join(PROJECT_DIR, 'sounds', sprite.getName())):
                os.makedirs(os.path.join(PROJECT_DIR, 'sounds', sprite.getName()))
            for sound in sprData['sounds']:
                soundName = sound['soundName']
                id = sound['soundID']
                if sound['format'] == 'adpcm':
                    print("Warning: Sound is in adpcm format and will not work:", soundName)
                shutil.copyfile(os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR, str(id) + '.wav'),
                                os.path.join(PROJECT_DIR, 'sounds', sprite.getName(), soundName + '.wav'))

        # Handle variables defined for this sprite.  This has to be done
        # before handling the scripts, as the scripts may refer will the
        # variables.
        # Variable initializations have to be done in a method called
        # addedToWorld(), which is not necessary if no variable defns exist.
        if 'variables' in sprData:
            sprite.genVariablesDefnCode(sprData['variables'], data['children'], cloudVars)
        else:
            # Default "addedToWorld" code to simplify getting/setting variables
            sprite.genDefaultAddedToWorld()

        sprite.genCodeForScripts()

        sprite.writeCodeToFile()

        worldCtorCode += sprite.getWorldCtorCode()


    else:
        if debug:
            print("\n----------- Not a sprite --------------");
            print(spr)


# --------- handle the Stage stuff --------------

# Because the stage can have script in it much like any sprite,
# we have to process it similarly.  So, lots of repeated code here
# from above -- although small parts are different enough.

# Write out a line to the project.greenfoot file to indicate that this
# sprite is a subclass of the Scratch class.
projectFileCode.append("class." + stage.getName() + ".superclass=Scratch\n")

# Create the special Stage sprite.
worldCtorCode += genIndent(2) + 'addSprite("' + stage.getName() + '", 0, 0);\n'

# TODO: this is copied code.  Find a way to unify the copies.  Hopefully as
# a method in SpriteOrStage class.

# Move all of the stage's sounds to project/sounds/stage
if 'sounds' in data:
    if not os.path.exists(os.path.join(PROJECT_DIR, 'sounds', 'Stage')):
        os.makedirs(os.path.join(PROJECT_DIR, 'sounds', 'Stage'))
    for sound in data['sounds']:
        name = sound['soundName']
        id = sound['soundID']
        if sound['format'] == 'adpcm':
            print("Warning: Sound is in adpcm format and will not work:", name)
        shutil.copyfile(os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR, str(id) + '.wav'),
                        os.path.join(PROJECT_DIR, 'sounds', 'Stage', name + '.wav'))

stage.genInitSettingsCode()
stage.genLoadCostumesCode(data['costumes'])
stage.genBackgroundHandlingCode()
stage.genDefaultAddedToWorld()
stage.genCodeForScripts()
stage.writeCodeToFile()

# ----------------------- Create subclass of World ------------------------------


#
# Now, to make the *World file -- a subclass of ScratchWorld.
#
filename = os.path.join(PROJECT_DIR, worldClassName + ".java")
outFile = open(filename, "w")
print("Writing code to " + filename + ".")

worldCode = genWorldHeaderCode(worldClassName)
worldCode += stage.getVarDefnCode()
worldCode += genWorldCtorHeader(worldClassName)

worldCode += stage.getWorldCtorCode()

# Adding the backdrops will be done in the World constructor, not
# the stage constructor because backdrops (backgrounds) are a property
# of the World in Greenfoot.
addBackdropsCode = stage.getCostumesCode()
if debug:
    print("CostumeCode is ", addBackdropsCode)

addBackdropsCode += genIndent(2) + 'setBackdropNumber(' + \
                    str(data['currentCostumeIndex']) + ');\n'

worldCode += worldCtorCode
worldCode += addBackdropsCode
worldCode += genIndent(1) + "}\n"
worldCode += "}\n"

outFile.write(worldCode)
outFile.close()

projectFileCode.append("class." + worldClassName + ".superclass=ScratchWorld\n")
projectFileCode.append("world.lastInstantiated=" + worldClassName + "\n")


# ---------------------------------------------------------------------------
# Now, update the project.greenfoot file with this new
# configuration information.  If we have run this script before, then
# the config info will be in there already.  So, for each line in
# projectFileCode, we'll check if the line is in the file first before
# updating/adding it.
projectFileCode.append("class.Scratch.superclass=greenfoot.Actor\n")
projectFileCode.append("class.ScratchWorld.superclass=greenfoot.World\n")

# If there's no project.greenfoot in the project directory, create one with
# default values.
if not os.path.isfile(os.path.join(PROJECT_DIR, "project.greenfoot")):
    with open(os.path.join(PROJECT_DIR, "project.greenfoot"), "w") as projF:
        projF.write("mainWindow.height=500\n")
        projF.write("mainWindow.width=750\n")
        projF.write("mainWindow.x=40\n")
        projF.write("mainWindow.y=40\n")
        projF.write("package.numDependencies=0\n")
        projF.write("package.numTargets=0\n")
        projF.write("project.charset=UTF-8\n")
        projF.write("version=2.7.1\n")
    
# Read all lines into variable lines.
lines = []
with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "r") as projF:
    lines = projF.readlines()
# Now, open in "w" mode which resets the file back to being empty.
with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "w") as projF:
    for line in lines:
        if line in projectFileCode:
            # Remove the line in pfcLines that matches.
            if debug:
                print("DEBUG: removing " + line + " from projFileCode because already in file.")
            projectFileCode.remove(line)
        projF.write(line)
    # Now write the remaining lines out from projectFileCode
    for p in projectFileCode:
        if debug:
            print("DEBUG: writing this line to project.greenfoot file:", p)
        projF.write(p)

