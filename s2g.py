#!/bin/env python3

# Copyright (C) 2016 - 2019  Victor T. Norman, Calvin College, Grand Rapids, MI, USA
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
import re
from pprint import pprint
import shutil
from subprocess import call, getstatusoutput
import sys
import tkinter

# Global Variables that can be set via command-line arguments.
debug = False
inference = False
name_resolution = False
useGui= False

# Indentation level in outputted Java code.
NUM_SPACES_PER_LEVEL = 4

# This variable tracks how many cloud variables have been generated, and
# serves as each cloud var's id
cloudVars = 0

worldClassName = ""


# Set up arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("-d", "--dotypeinference", action="store_true", help="Automatically infer variable types")
parser.add_argument("-r", "--resolvevariablenames", action = "store_true", help="Automatically convert to java ids")
parser.add_argument("-g", "--gui", action="store_true", help="Use GUI converter (Experimental)")
parser.add_argument("--scratch_file", help="Location of scratch sb2/sb3 file", default = os.getcwd(), required=False)
parser.add_argument("--greenfoot_dir", help="Location of greenfoot project directory", default = os.getcwd(), required=False)
args = parser.parse_args()

# Apply arguments
if args.verbose:
    debug = True
if args.dotypeinference:
    inference = True
if args.resolvevariablenames:
    name_resolution = True
if args.gui:
    useGui = True

SCRATCH_FILE = args.scratch_file.strip()
# Take off spaces and a possible trailing "/"
PROJECT_DIR = args.greenfoot_dir.strip().rstrip("/")
SCRATCH_PROJ_DIR = "scratch_code"
if SCRATCH_FILE.endswith('.sb2'):
    print('Scratch conversion only works with Scratch 3.0')
    sys.exit(-1)

# Initialize stage globally
stage = None

JAVA_KEYWORDS = ('abstract', 'continue', 'for', 'new', 'switch', 'assert', 'default', 'goto',\
                 'package', 'synchronized', 'boolean', 'do', 'if', 'private', 'this', 'break',\
                 'double', 'implements', 'protected', 'throw', 'byte', 'else', 'import', 'public',\
                 'throws', 'case', 'enum', 'instanceof', 'return', 'transient', 'catch', 'extends',\
                 'int', 'short', 'try', 'char', 'final', 'interface', 'static', 'void', 'class', 'finally',\
                 'long', 'strictfp', 'volatile', 'const', 'float', 'native', 'super', 'while')

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
    
    # Ensure that the resulting name is not a java keyword
    if res in JAVA_KEYWORDS:
        res += '_'
    return res


class Block:
    '''
    This represents a Scratch Block, with its opcode, parent,
    children, inputs, etc.
    '''
    def __init__(self, id, opcode):
        self._id = id
        self._opcode = opcode
        self._inputs = {}
        self._fields = {}
        self._topLevel = False
        self._next = None
        # dictionary mapping key -> child block.
        self._children = {}
    
    def setInputs(self, inputs):
        '''inputs are a json object (for now)'''
        self._inputs = inputs

    def setFields(self, fields):
        '''fields are a json object (for now)'''
        self._fields = fields

    def setTopLevel(self, val):
        self._topLevel = val

    def setNext(self, blockObj):
        self._next = blockObj

    def setChild(self, key, childBlock):
        if key in self._children:
            raise ValueError('block has child with key %s already' % key)
        self._children[key] = childBlock

    def isTopLevel(self):
        return self._topLevel

    def hasChild(self, key):
        return key in self._children

    def getId(self):
        return self._id

    def getOpcode(self):
        return self._opcode

    def getNext(self):
        return self._next

    def getInputs(self):
        return self._inputs

    def getFields(self):
        return self._fields

    def getChild(self, key):
        return self._children[key]

    def strWithIndent(self, indentLevel = 0):
        res = ("  " * indentLevel) + str(self)
        n = self._next
        while n:
            res += "\n" + str(n)
            n = n._next
        return res

    def __str__(self):
        return "BLOCK: " + self._opcode

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

        # Remember if we've generated code for a copy constructor
        # so that we don't do it multiple times.
        self._copyConstructorMade = False

        # A dictionary mapping variableName --> (sanitizedName, variableType).
        # We need this so we can generate code that calls the correct
        # functions to generate the correct type of results.
        # E.g., if a variable is boolean, we'll call boolExpr()
        # from setVariables(), not mathExpr().
        # The name is the sanitized name.
        self.varInfo = {}
        self.listInfo = {}


        print("\n----------- Sprite: %s ----------------" % self._name)
    
    def copySounds(self, soundsDir):
        # Move all of this sprites sounds to project/sounds/[spritename]
        if 'sounds' in self._sprData:
            if not os.path.exists(os.path.join(soundsDir, self.getName())):
                os.makedirs(os.path.join(soundsDir, self.getName()))
            for sound in self._sprData['sounds']:
                soundName = sound['name']
                id = sound['assetId']
                if sound['format'] == 'adpcm':
                    print("Warning: Sound is in adpcm format and will not work:", soundName)
                shutil.copyfile(os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR, str(id) + '.wav'),
                                os.path.join(soundsDir, self.getName(), soundName + '.wav'))

    def getName(self):
        return self._name

    def getVarInfo(self, name):
        '''Might return None if name not found in the mapping.
        Otherwise, returns a tuple: (clean name, varType)'''
        return self.varInfo.get(name)
    
    def getListInfo(self, name):
        '''Might return None if name not found in the mapping.
        Otherwise, returns a tuple: (clean name, varType)'''
        return self.listInfo.get(name)

    def whenClicked(self, codeObj, block):
        raise NotImplementedError('Implemented in subclass')

    def genAddSpriteCall(self):
        self._worldCtorCode += '%saddSprite("%s", %d, %d);\n' % \
                              (genIndent(2), self._name, self._sprData['x'], self._sprData['y'])

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

    def genVariablesDefnCode(self, listOfVars, listOfLists, allChildren, cloudVars):
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
        def genVariablesDefnCodeGui(listOfVars, listOfLists, allChildren, cloudVars):
            """Generate code to define instance variables for this sprite.
            Uses a tkinter GUI to simplify the process
            """
            nameList = []
            typeList = []
            valueList = []
            self.ready = False
            # Whenever the user presses a key, check validity of all fields
            def keypress():
                # Turns the text green if it's a valid name, red otherwise
                self.ready = True
                # track what names are in use
                names = {}
                for e in nameList:
                    # if this name is already in use turn both red
                    if e.get() in names.keys():
                        names[e.get()]['fg'] = 'red'
                        e['fg'] = 'red'
                        self.ready = False
                        # update the reference, this loses the old reference,
                        names[e.get()] = e
                        continue
                    # otherwise store the current name-entry pair
                    else:
                        names[e.get()] = e
                    # Check if the name is a valid java id
                    if re.match(r"[A-Za-z][A-Za-z0-9_]*$", e.get()):
                        e['fg'] = 'green'
                    else:
                        e['fg'] = 'red'
                        self.ready = False
                    # Check if the name is a java keyword
                    if e.get() in JAVA_KEYWORDS:
                        e['fg'] = 'red'
                        self.ready = False
                for e in typeList:
                    # Ensure the type is valid
                    if not e.get().lower() in ('int', 'string', 'double'):
                        
                        self.ready = False
                for i in range(0, len(valueList)):
                    # Check if the current value is valid for the type specified
                    if typeList[i].get().lower() == 'string':
                        try:
                            str(valueList[i].get())
                            valueList[i]['fg'] = 'green'
                        except:
                            valueList[i]['fg'] = 'red'
                            self.ready = False
                    elif typeList[i].get().lower() == 'int':
                        try:
                            int(valueList[i].get())
                            valueList[i]['fg'] = 'green'
                        except:
                            valueList[i]['fg'] = 'red'
                            self.ready = False
                    elif typeList[i].get().lower() == 'double':
                        try:
                            float(valueList[i].get())
                            valueList[i]['fg'] = 'green'
                        except:
                            valueList[i]['fg'] = 'red'
                            self.ready = False
                    else:
                        valueList[i]['fg'] = 'blue'
                        self.ready = False
                gui.after(25, keypress)

            # Automatically convert names and determine types for all variables
            def autoCB():
                for e in nameList:
                    s = e.get()
                    e.delete(0, tkinter.END)
                    e.insert(tkinter.END, convertToJavaId(s, True, False))
                for i in range(0, len(typeList)):
                    try:
                        typeList[i].set(deriveType("", valueList[i].get())[1])
                    except ValueError:
                        typeList[i].set("String")
                keypress()

            # Display a help message informing the user how to use the namer
            def helpCB():
                tkinter.messagebox.showinfo("Help", "If a name is red, that means it is not valid in Java. Java variable names must " + \
                                    "start with a letter, and contain only letters, numbers and _. (No spaces!) There are also " + \
                                    "some words that can't be variable names because they mean something special in java: \n" + \
                                    str(JAVA_KEYWORDS) + ". \n\nIf a type " + \
                                    "is red, that means it is not a valid type. The types that work with this " + \
                                    "converter are:\n\tInt: a number that will never be a decimal\n\tDouble: a number " + \
                                    "that can be a decimal\n\tString: symbols, letters, and text\n\nIf a value is red, " + \
                                    "that means that the variable cannot store that value. For example, an Int " + \
                                    "cannot store the value 1.5, since it has to store whole numbers.")
            # Write out the results to the file
            def confirmCB():
                global cloudVars
                if not self.ready:
                    tkinter.messagebox.showerror("Error", "Some of the inputs are still invalid. Click help for more " + \
                                         "details on how to fix them.")
                    gui.focus_set()
                    return
                for i in range(len(listOfVars)):  # var is a dictionary.
                    var = listOfVars[i]
                    name = var['name']  # unsanitized Scratch name
                    value = var['value']
                    cloud = var['isPersistent']
                    print(("Proceesing var: " + name).encode('utf-8'))
                    # return the varType and the value converted to a java equivalent
                    # for that type. (e.g., False --> false)
                    # varType is one of 'Boolean', 'Double', 'Int', 'String'
                    varType = typeList[i].get().title()
                    if cloud:
                        value = cloudVars
                        cloudVars += 1
                        varType = 'Cloud'
                        # The first character is a weird Unicode cloud glyph and the
                        # second is a space.  Get rid of them.
                        name = name[2:]
        
                    # Sanitize the name: make it a legal Java identifier.
                    sanname = nameList[i].get()
        
                    # We need this so we can generate code that calls the correct
                    # functions to generate the correct type of results.
                    # E.g., if a variable is boolean, we'll call boolExpr()
                    # from setVariables(), not mathExpr().
                    # Record a mapping from unsanitized name --> (sanitized name, type)
                    self.varInfo[name] = (sanname, varType)
                    if True:
                        print("Adding varInfo entry for", self._name, ":", name,
                              "--> (" + sanname + ", " + varType + ")")
                    
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
                            label = name
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
        
        
                    # TODO: FIX THIS: move code into subclass!!!
                    # Something like "Scratch.IntVar score; or ScratchWorld.IntVar score;"
                    if self.getNameTypeAndLocalGlobal(name)[2]:
                        self._varDefnCode += genIndent(1) + 'static %sVar %s;\n' % (varType, sanname)
                    else:
                        self._varDefnCode += genIndent(1) + "%sVar %s;\n" % (varType, sanname)
                    # Escape any quotes in the label
                    label = re.sub('"', '\\"', label)
                    if (varType.lower() == "string"):
                        # Escape any quotes, and add make it a string literal
                        value = '"' + re.sub('"', '\\"', value) + '"'
                        
                    # Something like "score = createIntVariable((MyWorld) world, "score", 0);
                    self._addedToWorldCode += '%s%s = create%sVariable((%s) world, "%s", %s);\n' % \
                        (genIndent(2), sanname, varType, worldClassName, label, str(value))
                    if not visible:
                        self._addedToWorldCode += genIndent(2) + sanname + ".hide();\n"
                # Add blank line after variable definitions.
                self._varDefnCode += "\n"
                self._addedToWorldCode += genIndent(2) + "// List initializations.\n"
                for l in listOfLists:
                    name = l['listName']
                    contents = l['contents']
                    visible = l['visible']
                    try:
                        sanname = convertToJavaId(name, True, False)
                    except:
                        print("Error converting list to java id")
                        sys.exit(0)
                    
                    self.listInfo[name]  = sanname
                    
                    # I know this is bad style, but at the moment it's necessary
                    # Later down the line we can move all this code to subclasses instead
                    if type(self) == Stage:
                        self._varDefnCode += genIndent(1) + 'static ScratchList %s;\n' % (sanname)
                    else:
                        self._varDefnCode += genIndent(1) + "ScratchList %s;\n" % (sanname)
                    
                    self._addedToWorldCode += '%s%s = createList(world, "%s"' % (genIndent(2), sanname, name)
                    for obj in contents:
                        disp = deriveType(name, obj)
                        self._addedToWorldCode += ', %s' % (str(disp[0]))
                    self._addedToWorldCode += ');\n'
                    if not visible:
                        self._addedToWorldCode += '%s%s.hide();\n' % (genIndent(2), sanname)
        
                # Close the addedToWorld() method definition.
                self._addedToWorldCode += genIndent(1) + "}\n"
                # Return focus and execution back to the main window
                root.focus_set()
                gui.quit()
                gui.destroy()
            # Main method code
            # Construct the GUI
            gui = tkinter.Toplevel(root)
            #gui.bind("<Any-KeyPress>", keypress)
            
            gui.title("Variable Namer")
            gui.grab_set()


            table = tkinter.Frame(gui)
            table.pack()
            buttons = tkinter.Frame(gui)
            buttons.pack(side = tkinter.BOTTOM)
            auto = tkinter.Button(buttons, text = "Auto-Convert", command = autoCB)
            auto.pack(side = tkinter.LEFT)
            confirm = tkinter.Button(buttons, text = "Confirm", command = confirmCB)
            confirm.pack(side = tkinter.LEFT)
            help = tkinter.Button(buttons, text = "Help", command = helpCB)
            help.pack(side = tkinter.LEFT)
            tkinter.Label(table, text = "  Scratch Name  ").grid(row=0, column=0)
            tkinter.Label(table, text = "Java Name").grid(row=0, column=1)
            tkinter.Label(table, text = "Java Type").grid(row=0, column=2)
            tkinter.Label(table, text = "Starting Value").grid(row=0, column=3)

            # Populate lists
            row = 1
            for var in listOfVars:
                name = var['name']  # unsanitized Scratch name
                value = var['value']
                cloud = var['isPersistent']
                lbl = tkinter.Entry(table)
                lbl.insert(tkinter.END, name)
                lbl.configure(state = "readonly")
                lbl.grid(row=row, column=0, sticky=tkinter.W + tkinter.E)

                ent = tkinter.Entry(table)
                ent.insert(tkinter.END, name)
                ent.grid(row=row, column=1, sticky=tkinter.W + tkinter.E)

                nameList.append(ent)
                svar = tkinter.StringVar(gui)
                ent2 = tkinter.OptionMenu(table, svar, "Int", "Double", "String")
                ent2.grid(row=row, column=2, sticky=tkinter.W + tkinter.E)
                #ent2.bind("<Button-1>", keypress)

                typeList.append(svar)
                ent3 = tkinter.Entry(table)
                ent3.insert(tkinter.END, value)
                ent3.grid(row=row, column=3, sticky=tkinter.W + tkinter.E)
                valueList.append(ent3)
                row += 1

            # Update the text color
            keypress()
            gui.mainloop()

        def chooseType(name, val):
            i, typechosen = deriveType(name, val)
            while not inference:
                try:
                    print("\n\nWhat type of variable should \"" + name + "\": " + str(val) + " be?")
                    theType = input("\tInt: A number that won't have decimals\n\tDouble:" + \
                                 " A number that can have decimals\n\tString: Text or letters\n" + \
                                 "This variable looks like: " + typechosen +\
                                 "\nPress enter without typing anything to use suggested type\n> ").capitalize()
                    # Try to convert the value to the chosen type, only the first character needs to be entered
                    if theType[0] == 'I':
                        return int(val), 'Int'
                    elif theType[0] == 'D':
                        return float(val), 'Double'
                    elif theType[0] == 'S':
                        return '"' + str(val) + '"', "String"
                    # If ? is chosen, continue with automatic derivation
                    elif theType == "?":
                        break
                    print(theType, "not recognized, please choose one of these (Int,Double,String)")
                except IndexError:
                    # Nothing was entered
                    break
                except:
                    # If val is not able to be converted to type, it will be set to default, or the user may choose
                    # a different type.
                    if input("Could not convert " + str(val) + " to " + theType +\
                             " Set to default value? (y/n)\n> ") == "y":
                        if theType[0] == 'I':
                            return (0, 'Int')
                        elif theType[0] == 'F':
                            return 0.0, 'Double'
                        elif theType[0] == 'S':
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

        #
        # Initialization goes into the method addedToWorld() for Sprites, but
        # into the ctor for World.
        #
        self._addedToWorldCode += "\n" + genIndent(1) + "private " + worldClassName + " world;"
        self._addedToWorldCode += "\n" + genIndent(1) + "public void addedToWorld(World w)\n"
        self._addedToWorldCode += genIndent(1) + "{\n"
        self._addedToWorldCode += genIndent(2) + "world = (" + worldClassName + ") w;\n"
        self._addedToWorldCode += genIndent(2) + "super.addedToWorld(w);\n"
        self._addedToWorldCode += genIndent(2) + "// Variable initializations.\n"
        # If running in gui mode, call the gui method instead
        if useGui:
            genVariablesDefnCodeGui(listOfVars, listOfLists, allChildren, cloudVars)
            return

        for var in listOfVars:  # var is a dictionary.
            name = var['name']  # unsanitized Scratch name
            value = var['value']
            cloud = var['isPersistent']
            # return the varType and the value converted to a java equivalent
            # for that type. (e.g., False --> false)
            # varType is one of 'Boolean', 'Double', 'Int', 'String'
            if cloud:
                value = cloudVars
                cloudVars += 1
                varType = 'Cloud'
                # The first character is a weird Unicode cloud glyph and the
                # second is a space.  Get rid of them.
                name = name[2:]   
            else:
                value, varType = chooseType(name, value)

            # Sanitize the name: make it a legal Java identifier.
            try:
                if name_resolution:
                    sanname = convertToJavaId(name, True, False)
                elif not convertToJavaId(name, True, False) == name:
                    sanname = self.resolveName(name)
                else:
                    sanname = convertToJavaId(name, True, False)
            except:
                print("Error converting variable to java id")
                sys.exit(0)

            # We need this so we can generate code that calls the correct
            # functions to generate the correct type of results.
            # E.g., if a variable is boolean, we'll call boolExpr()
            # from setVariables(), not mathExpr().
            # Record a mapping from unsanitized name --> (sanitized name, type)
            self.varInfo[name] = (sanname, varType)
            if True:
                print("Adding varInfo entry for", self._name, ":", name,
                      "--> (" + sanname + ", " + varType + ")")
            
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
                    label = name
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


            # TODO: FIX THIS: move code into subclass!!!
            # Something like "Scratch.IntVar score; or ScratchWorld.IntVar score;"
            if self.getNameTypeAndLocalGlobal(name)[2]:
                self._varDefnCode += genIndent(1) + 'static %sVar %s;\n' % (varType, sanname)
            else:
                self._varDefnCode += genIndent(1) + "%sVar %s;\n" % (varType, sanname)
                
            # Something like "score = createIntVariable((MyWorld) world, "score", 0);
            self._addedToWorldCode += '%s%s = create%sVariable((%s) world, "%s", %s);\n' % \
                (genIndent(2), sanname, varType, worldClassName, label, str(value))
            if not visible:
                self._addedToWorldCode += genIndent(2) + sanname + ".hide();\n"
        # Add blank line after variable definitions.
        self._varDefnCode += "\n"
        self._addedToWorldCode += genIndent(2) + "// List initializations.\n"
        for l in listOfLists:
            name = l['listName']
            contents = l['contents']
            visible = l['visible']
            try:
                sanname = convertToJavaId(name, True, False)
            except:
                print("Error converting list to java id")
                sys.exit(0)
            
            self.listInfo[name]  = sanname
            
            # I know this is bad style, but at the moment it's necessary
            # Later down the line we can move all this code to subclasses instead
            if type(self) == Stage:
                self._varDefnCode += genIndent(1) + 'static ScratchList %s;\n' % (sanname)
            else:
                self._varDefnCode += genIndent(1) + "ScratchList %s;\n" % (sanname)
            
            self._addedToWorldCode += '%s%s = createList(world, "%s"' % (genIndent(2), sanname, name)
            for obj in contents:
                disp = deriveType(name, obj)
                self._addedToWorldCode += ', %s' % (str(disp[0]))
            self._addedToWorldCode += ');\n'
            if not visible:
                self._addedToWorldCode += '%s%s.hide();\n' % (genIndent(2), sanname)

        # Close the addedToWorld() method definition.
        self._addedToWorldCode += genIndent(1) + "}\n"
            
    

    def getVarDefnCode(self):
        return self._varDefnCode
    def getAddedToWorldCode(self):
        return self._addedToWorldCode

    def genCodeForScripts(self):
        # The value of the 'blocks' key is the list of the scripts.  It may be a
        # list of 1 or of many.

        if 'blocks' not in self._sprData:
            print("No scripts found in", self._name)
            # if debug:
            #     print("sprData is -->" + str(self._sprData) + "<--")
            return

        blocksJson = self._sprData['blocks']
        blocks = self.genBlocksList(blocksJson)
        for b in blocks:
            print(b.strWithIndent())
            print()
        
        for topBlock in blocks:
            codeObj = self.genScriptCode(topBlock)
            self._regCallbacksCode += codeObj.code
            if codeObj.cbCode != "":
                # The script generate callback code.
                self._cbCode.append(codeObj.cbCode)

    def genBlocksList(self, blocksJson):
        """
        Given a json object that contains blocks definitions, generate
        a list of Block objects, where Blocks in a script are in a list,
        and Blocks that contain other Blocks have sub-lists, etc.
        Return the list of topLevel blocks, with other blocks "hanging off".
        """
        # script is an object containing objects indexed by a unique identifier for 
        # each block, and each block object contains links to parent (previous) and next
        # identifier.  E.g.:
        # 
        # {
        #   "h2blUU?#$l!dd*n}-Q1Y": {
        #     "opcode": "event_whenflagclicked",
        #     "next": "%?R0lmqrvySH00}u~j,l",
        #     "parent": null,
        #     "inputs": {},
        #     "fields": {},
        #     "topLevel": true,
        #     "shadow": false,
        #     "x": 53,
        #     "y": 56
        #   },
        #   "%?R0lmqrvySH00}u~j,l": {
        #     "opcode": "motion_movesteps",
        #     "next": "T:Al*H@POT=8dOCzpm0(",
        #     "parent": "h2blUU?#$l!dd*n}-Q1Y",
        #     "inputs": {
        #         "STEPS": [
        #         1,
        #         [
        #             4,
        #             "10"
        #         ]
        #         ]
        #     },
        #     ... etc ...

        allBlocks = {}   # Map of blockId to Block object.

        # Create all the block objects first
        for blockId in blocksJson:
            vals = blocksJson[blockId]
            block = Block(blockId, vals['opcode'])
            allBlocks[blockId] = block
            # print('adding block with id to collection', blockId, vals['opcode'])
            if vals['inputs']: 
                block.setInputs(vals['inputs'])
            if vals['fields']: 
                block.setFields(vals['fields'])
            if vals['topLevel']:
                block.setTopLevel(vals['topLevel'])

        # Link the blocks together.
        for blockId in blocksJson:
            blockJson = blocksJson[blockId]
            block = allBlocks[blockId]
            if blockJson['next'] != None:
                nextBlock = allBlocks[blockJson['next']]
                print('setting next block of %s to be %s' % (str(block), str(nextBlock)))
                block.setNext(nextBlock)
            inputs = blockJson['inputs']
            for inputKey in inputs:
                # inputs is like this:
                # "OPERAND1": [
                #   3,          
                #   "#70%(-M,b|(xTdgz(p@p",   <-- here is the child at index 1
                #   [
                #     10,
                #     ""
                #   ]
                # ],
                # "OPERAND2": [
                #   1,
                #   [
                #     10,
                #     "50"
                #   ]
                # ]
                if isinstance(inputs[inputKey][1], str) and inputs[inputKey][1] in allBlocks:
                    block.setChild(inputKey, allBlocks[inputs[inputKey][1]])
                    print('setting child block of %s with key %s to %s' %
                        (str(block), inputKey, str(allBlocks[inputs[inputKey][1]])))
        
        listOfTopLevelBlocks = [block for block in allBlocks.values() if block.isTopLevel()]
        return listOfTopLevelBlocks

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


    def block(self, level, topBlock, deferYield = False):
        """Handle a block containing a list of statements wrapped in { }."""

        if debug:
            print("block: topBlock = ")
            print(topBlock.strWithIndent(level))

        return genIndent(level) + "{\n" + self.stmts(level, topBlock.getNext(), deferYield) + \
               genIndent(level) + "}\n"


    def stmts(self, level, firstBlock, deferYield = False):
        """Generate code for the list of statements, by repeatedly calling stmt(), 
        following the chain of next pointers from the firstBlock."""
        if firstBlock is None:
            return ""
        retStr = ""
        aBlock = firstBlock
        while aBlock:
            # Call stmt to generate the statement, appending the result to the
            # overall resulting string.
            retStr += self.stmt(level + 1, aBlock, deferYield)
            aBlock = aBlock.getNext()
        return retStr


    def stmt(self, level, block, deferYield = False):
        """Handle a statement, which is a block object
        """

        scratchStmt2genCode = {
            'control_if': self.doIf,
            'doIfElse': self.doIfElse,

            # Motion commands
            'motion_movesteps': self.moveSteps,
            'motion_turnleft': self.turnLeft,
            'motion_turnright': self.turnRight,
            'motion_pointindirection': self.pointInDirection,
            'motion_gotoxy': self.gotoXY,
            'motion_goto': self.goto,
            'motion_changexby': self.changeXBy,
            'motion_setx': self.setX,
            'motion_changeyby': self.changeYBy,
            'motion_sety': self.setY,
            'motion_ifonedgebounce': self.ifOnEdgeBounce,
            'motion_setrotationstyle': self.setRotationStyle,
            'motion_pointtowards': self.pointTowards,
            'motion_glideto': self.glideTo,

            # Looks commands
            'looks_sayforsecs': self.sayForSecs,
            'looks_say': self.say,
            'looks_thinkforsecs':self.thinkForSecs,
            'looks_think': self.think,
            'looks_show': self.show,
            'looks_hide': self.hide,
            'looks_switchcostumeto': self.switchCostumeTo,
            'looks_nextcostume': self.nextCostume,
            'startScene': self.switchBackdropTo,
            'looks_changesizeby': self.changeSizeBy,
            'looks_setsizeto': self.setSizeTo,
            'comeToFront': self.goToFront,
            'goBackByLayers:': self.goBackNLayers,
            'looks_nextbackdrop': self.nextBackdrop,
            'changeGraphicEffect:by:': self.changeGraphicBy,
            'setGraphicEffect:to:': self.setGraphicTo,

            # Pen commands
            'pen_clear': self.penClear,
            'pen_stamp': self.penStamp,
            'pen_penDown': self.penDown,
            'pen_penUp': self.penUp,
            
            'pen_setPenColorToColor': self.setPenColor,
            'pen_setPenColorParamTo': self.setPenColorParamTo,
            'pen_changePenColorParamBy': self.setPenColorParamBy,
            'pen_setPenSizeTo': self.setPenSizeTo,
            'pen_changePenSizeBy': self.changePenSizeBy,

            # Data commands
            'setVar:to:': self.setVariable,
            'hideVariable:': self.hideVariable,
            'showVariable:': self.showVariable,
            'changeVar:by:': self.changeVarBy,

            'append:toList:': self.listAppend,
            'deleteLine:ofList:': self.listRemove,
            'insert:at:ofList:': self.listInsert,
            'setLine:ofList:to:': self.listSet,
            'hideList:': self.hideList,
            'showList:': self.showList,

            # Events commands
            'event_broadcast': self.broadcast,
            'event_broadcastandwait': self.broadcastAndWait,

            # Control commands
            'control_forever': self.doForever,
            'control_wait': self.doWait,
            'control_repeat': self.doRepeat,
            'doWaitUntil': self.doWaitUntil,
            'doUntil': self.repeatUntil,
            'stopScripts': self.stopScripts,
            'control_create_clone_of': self.createCloneOf,
            'control_delete_this_clone': self.deleteThisClone,

            # Sensing commands
            'doAsk': self.doAsk,
            'timerReset': self.resetTimer,

            # Blocks commands
            'call': self.callABlock,

            # Sound commands
            'sound_play': self.playSound,
            'sound_playuntildone': self.playSoundUntilDone,

            #Midi commands
            'music_playNoteForBeats': self.playNote,
            'music_setInstrument': self.instrument,
            'music_playDrumForBeats': self.playDrum,
            'music_restForBeats': self.rest,
            'music_changeTempo': self.changeTempoBy,
            'music_setTempo': self.setTempoTo

            }
        if debug:
            print("stmt: block = ")
            print(block.strWithIndent(level))

        cmd = block.getOpcode()

        if cmd in scratchStmt2genCode:
            genCodeFunc = scratchStmt2genCode[cmd]
            return genCodeFunc(level, block, deferYield)
        else:
            return genIndent(level) + 'System.out.println("Unimplemented stmt: ' + cmd + '");\n'


    def boolExpr(self, block):
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
            resStr += "(" + self.oldMathExpr(tokenList[1])
            if firstOp == '<':
                resStr += " < "
            elif firstOp == '>':
                resStr += " > "
            else: 	# must be ' = '
                resStr += " == "
            resStr += self.oldMathExpr(tokenList[2]) + ")"
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
            resStr += "(isTouchingColor(new java.awt.Color(" + self.oldMathExpr(tokenList[1]) + ")))"
        elif firstOp == 'keyPressed:':
            resStr += '(isKeyPressed("' + convertKeyPressName(tokenList[1]) + '"))'
        elif firstOp == 'mousePressed':
            resStr += "(isMouseDown())"
        elif firstOp == 'readVariable':
            resStr += self.readVariable(tokenList[1])
        elif firstOp == 'list:contains:':
            resStr += self.listContains(tokenList[1], tokenList[2])
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
                return "letterNOf(" + self.strExpr(tok2) + ", " + self.oldMathExpr(tok1) + ")"
            elif op == 'getAttribute:of:':
                return self.getAttributeOf(tok1, tok2)
        print("No string operator '" + tokenOrList[0] + "' trying mathExpr")
        return "String.valueOf(" + str(self.oldMathExpr(tokenOrList)) + ")"

    def mathExpr(self, block, exprKey):
        '''Evaluate the expression in block[exprKey] and its children, as a math expression,
        returning a string equivalent.'''

        expr = block.getInputs()[exprKey]

        assert isinstance(expr, list)
        if not block.hasChild(exprKey):
            expr = block.getInputs()[exprKey]
            val = expr[1][1]
            return '0' if val == '' else val
        else:
            # e.g., [  3,  'alongidhere', [ 4, "10" ] ]
            # the value after 'alongidhere' is the default value -- we don't care about this.
            child = block.getChild(exprKey)
            if child.getOpcode() == 'operator_add':
                return '(' + self.mathExpr(child, 'NUM1') + ' + ' + self.mathExpr(child, 'NUM2') + ')'
            elif child.getOpcode() == 'operator_subtract':
                return '(' + self.mathExpr(child, 'NUM1') + ' - ' + self.mathExpr(child, 'NUM2') + ')'
            elif child.getOpcode() == 'operator_multiply':
                return '(' + self.mathExpr(child, 'NUM1') + ' * ' + self.mathExpr(child, 'NUM2') + ')'
            elif child.getOpcode() == 'operator_divide':
                return '(' + self.mathExpr(child, 'NUM1') + ' / ' + self.mathExpr(child, 'NUM2') + ')'
            elif child.getOpcode() == 'operator_mod':
                return '(' + "Math.floorMod(" + self.mathExpr(child, 'NUM1') + ", " + self.mathExpr(child, 'NUM2') + "))"
            elif child.getOpcode() == 'operator_round':
                return '(' + "Math.round((float) " + self.mathExpr(child, 'NUM') + "))"
            elif child.getOpcode() == 'operator_mathop':
                mathop = child.getFields()['OPERATOR'][0]
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
                return '(' + op2Func[mathop] + self.mathExpr(child, 'NUM') + "))"
            elif child.getOpcode() == 'operator_length':
                arg = child.getInputs()['STRING'][1][1]
                # TODO: should call strExpr 
                return "lengthOf(" + arg + ")"
            elif child.getOpcode() == 'motion_xposition':
                return 'getX()'
            elif child.getOpcode() == 'motion_ypos':
                return "getY()"
            elif child.getOpcode() == 'motion_direction':
                return "getDirection()"
            elif child.getOpcode() == "looks_costumenumbername":
                if child.getFields()['NUMBER_NAME'][0] == 'number':
                    return "costumeNumber()"
                else:
                    raise ValueError('not supported yet')
            elif child.getOpcode() == 'looks_backdropnumbername':
                if child.getFields()['NUMBER_NAME'][0] == 'number':
                    return 'getBackdropNumber()'
                else:
                    raise ValueError('not supported yet')
            elif child.getOpcode() == "looks_size":
                return "size()"
            elif child.getOpcode() == "sensing_mousedown":
                # this will produce uncompileable Java code... but if you try this kind of
                # thing, you are kind of asking for it...
                return " (int) isMouseDown()"   
            elif child.getOpcode() == "sensing_mousex":
                return "getMouseX()"
            elif child.getOpcode() == 'sensing_mousey':
                return "getMouseY()"
            elif child.getOpcode() == "sensing_timer":
                return "getTimer()"
            elif child.getOpcode() == "sensing_dayssince2000":
                return "daysSince2000()"
            elif child.getOpcode() == "sensing_distanceto":
                grandchild = child.getChild('DISTANCETOMENU')
                arg = grandchild.getFields()['DISTANCETOMENU'][0]
                if arg == '_mouse_':
                    return "distanceToMouse()"
                else:   # must be distance to a sprite
                    return 'distanceTo("' + arg + '")'
            else:
                raise ValueError("Unsupported operator %s" % child.getOpcode())


    def oldMathExpr(self, tokenOrList):

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
                return "costumeNumber()"
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
            elif op == "timestamp":
                return "daysSince2000()"
            else:
                raise ValueError("Unknown operation " + op)

        if len(tokenOrList) == 2:
            # Handle cases of operations that take 1 argument.
            op, tok1 = tokenOrList
            if op == "rounded":
                return "Math.round((float) " + self.oldMathExpr(tok1) + ")"
            elif op == "stringLength:":
                return "lengthOf(" + self.strExpr(tok1) + ")"
            elif op == "distanceTo:":
                if tok1 == "_mouse_":
                    return "distanceToMouse()"
                else:   # must be distance to a sprite
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
            elif op == 'lineCountOfList:':
                return self.listLength(tok1)
            else:
                raise ValueError("Unknown operation " + op)

        assert len(tokenOrList) == 3	# Bad assumption?
        op, tok1, tok2 = tokenOrList	

        # Handle special cases before doing the basic ones which are inorder
        # ops (value op value).
        if op == 'randomFrom:to:':
            # tok1 and tok2 may be math expressions.
            return "pickRandom(" + self.oldMathExpr(tok1) + ", " + self.oldMathExpr(tok2) + ")"
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
            return op2Func[tok1] + self.oldMathExpr(tok2) + ")"
        elif op == "getAttribute:of:":
            return self.getAttributeOf(tok1, tok2)
        elif op == 'getLine:ofList:':
                return self.listElement(tok1, tok2)
        else:
            assert op in ('+', '-', '*', '/', '%'), "Unknown op: " + op
        
        if op == '%':
            resStr = "Math.floorMod(" + self.oldMathExpr(tok1) + ", " + self.oldMathExpr(tok2) + ")"
            return resStr

        resStr = "(" + self.oldMathExpr(tok1)
        if op == '+':
            resStr += " + "
        elif op == '-':
            resStr += " - "
        elif op == '*':
            resStr += " * "
        elif op == '/':
            resStr += " / "
        else:
            raise ValueError(op)
        resStr += self.oldMathExpr(tok2) + ")"
        return resStr


    def getAttributeOf(self, tok1, tok2):
        """Return code to handle the various getAttributeOf calls
        from the sensing block.
        """
        if tok2 == '_stage_':
            if tok1 == 'backdrop name':
                return "backdropName()"
            elif tok1 == 'backdrop #':
                return "getBackdropNumber()"
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
                    'costume name': 'costumeNameOf',
                    'size': 'sizeOf',
                    }
        if tok1 in mapping:
            return mapping[tok1] + '("' + tok2 + '")'
        else:   # volumeOf, backdropNumberOf
            # TODO: We must assume that this is a variable, as not all variable have necessarily
            # been parsed yet. Note that because of this, we cannot look up the actual name
            # of the variable, we must use the unsanitized name. TODO fix this 
            return '((' + tok2 + ')world.getActorByName("' + tok2 + '")).' + tok1 + '.get()'

    def whenFlagClicked(self, codeObj, block):
        """Generate code to handle the whenFlagClicked block.
        All code in block goes into a callback.
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
        cbStr += self.block(level, block) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)


    def whenSpriteCloned(self, codeObj, topBlock):
        """Generate code to handle the whenCloned block.
        All code in children of topBlock goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        cbName = 'whenIStartAsACloneCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenIStartAsAClone("' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(1, topBlock) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)

        # Generate a copy constructor too.
        if not self._copyConstructorMade:
            cbStr = "\n\n" + genIndent(1) + "// copy constructor, required for cloning\n"
            cbStr += genIndent(1) + "public " + self._name + "(" + \
                     self._name + " other, int x, int y) {\n"
            cbStr += genIndent(2) + "super(other, x, y);\n"
            cbStr += genIndent(2) + "// add code here to copy any instance variables'\n"
            cbStr += genIndent(2) + "// values from other to this.\n"
            cbStr += genIndent(1) + "}\n\n"
            codeObj.addToCbCode(cbStr)
            self._copyConstructorMade = True


    def whenKeyPressed(self, codeObj, topBlock):
        """Generate code to handle the whenKeyPressed block.
        topBlock is the keypressed block. Child block code is generated
        into a callback to be called when that key is pressed.
        """
        scriptNum = codeObj.getNextScriptId()
        key = topBlock.getFields()['KEY_OPTION'][0]
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
        cbStr += self.block(level, topBlock) + "\n"  # add blank line after defn.

        codeObj.addToCbCode(cbStr)


    def whenIReceive(self, codeObj, topBlock):
        """Generate code to handle the whenIReceive block.  
        topBlock contains the message and the list of stmts to be put
        into a callback to be called when that message is received.
        """
        scriptNum = codeObj.getNextScriptId()

        # Build a name like whenIReceiveMessage1Cb0
        message = topBlock.getFields()['BROADCAST_OPTION'][0]
        messageId = convertToJavaId(message, noLeadingNumber=False, capitalizeFirst=True)
        cbName = 'whenIReceive' + messageId + 'Cb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenRecvMessage("' +
                          message + '", "' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        # All cb code is at level 1
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + "(Sequence s)\n"
        cbStr += self.block(1, topBlock) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr) 
        
    def whenSwitchToBackdrop(self, codeObj, backdrop, tokens):
        """Generate code to handle the whenSwitchToBackdrop block.  key is
        the key to wait for, and tokens is the list of stmts to be put
        into a callback to be called when that key is pressed.
        """
        scriptNum = codeObj.getNextScriptId()

        # Build a name like whenAPressedCb0 or whenLeftPressedCb0.
        cbName = 'whenSwitchedToBackdropCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenSwitchToBackdrop("' +
                          backdrop + '", "' + cbName + '");\n')

        level = 1    # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                "(Sequence s)\n"
        cbStr += self.block(level, tokens) + "\n"  # add blank line after defn.

        codeObj.addToCbCode(cbStr)


    def doForever(self, level, block, deferYield = False):
        """Generate doForever code.  block is the topblock with 
        children hanging off of it.
        forever loop is turned into a while (true) loop, with the last
        operation being a yield(s) call.
        """
        retStr = genIndent(level) + "while (true)\t\t// forever loop\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.stmts(level, block.getChild('SUBSTACK'))
        if (deferYield):
            retStr += genIndent(level + 1) + \
                        "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                        "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def doIf(self, level, block, deferYield = False):
        """Generate code for if <test> : <block>.
        """
        # Handle the boolean expression
        # We don't generate parens around the boolExpr as it will put them there.
        
        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(block.getChild('CONDITION'))
        resStr += "\n"
        resStr += self.block(level, block.getChild('SUBSTACK'))
        return resStr


    def doIfElse(self, level, block, deferYield = False):
        """Generate code for if <test> : <block> else: <block>.
        """

        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(block.getChild('CONDITION'))
        resStr += "\n"
        resStr += self.block(level, block.getChild('SUBSTACK'))
        resStr += genIndent(level) + "else\n"
        resStr += self.block(level, block.getChild('SUBSTACK2'))
        return resStr


    def ifOnEdgeBounce(self, level, block, deferYield = False):
        """Generate code to handle Motion blocks with 0 arguments"""
        return genIndent(level) + "ifOnEdgeBounce();\n"

    def stripOutsideParens(self, s):
        if s[0] == '(' and s[-1] == ')':
            return s[1:-1]
        return s

    def moveSteps(self, level, block, deferYield = False):
        #     "inputs": {
        #       "STEPS": [  1,  [ 4, "10" ] ]
        #     },
        arg = self.stripOutsideParens(self.mathExpr(block, 'STEPS'))
        return genIndent(level) + "move(" + arg + ");\n"

    def turnRight(self, level, block, deferYield = False):
        # inputs is similar to moveSteps, but with DEGREES
        return genIndent(level) + "turnRightDegrees(" + self.mathExpr(block, 'DEGREES') + ");\n"

    def turnLeft(self, level, block, deferYield = False):
        return genIndent(level) + "turnLeftDegrees(" + self.mathExpr(block, 'DEGREES') + ");\n"

    def pointInDirection(self, level, block, deferYield = False):
        return genIndent(level) + "pointInDirection(" + self.mathExpr(block, 'DIRECTION') + ");\n"

    def goto(self, level, block, deferYield = False):
        return self.genGoto(level, block)

    def changeXBy(self, level, block, deferYield = False):
        return genIndent(level) + "changeXBy(" + self.mathExpr(block, 'DX') + ");\n"

    def changeYBy(self, level, block, deferYield = False):
        return genIndent(level) + "changeYBy(" + self.mathExpr(block, 'DY') + ");\n"

    def setX(self, level, block, deferYield = False):
        return genIndent(level) + "setXTo(" + self.mathExpr(block, 'X') + ");\n"

    def setY(self, level, block, deferYield = False):
        return genIndent(level) + "setYTo(" + self.mathExpr(block, 'Y') + ");\n"

    def setRotationStyle(self, level, block, deferYield = False):
        arg = block.getFields()['STYLE'][0]
        return self.genRotationStyle(level, arg)

    def genGoto(self, level, block):
        child = block.getChild('TO')
        argVal = child.getFields()['TO'][0]
        if argVal == "_mouse_":
            return genIndent(level) + "goToMouse();\n"
        elif argVal == "_random_":
            return genIndent(level) + "goToRandomPosition();\n"
        else:           
            return genIndent(level) + 'goTo("%s");\n' % argVal

    def genRotationStyle(self, level, arg):
        resStr = genIndent(level) + "setRotationStyle("
        if arg in ("left-right", "leftRight"):
            return resStr + "RotationStyle.LEFT_RIGHT);\n"
        elif arg in ("don't rotate", "none"):
            return resStr + "RotationStyle.DONT_ROTATE);\n"
        elif arg in ("all around", "normal"):
            return resStr + "RotationStyle.ALL_AROUND);\n"
        else:
            raise ValueError('setRotationStyle')

    def gotoXY(self, level, block, deferYield = False):
        """Generate code to handle Motion blocks with 2 arguments:
        gotoxy, etc."""
        #  "inputs": {
        #     "X": [ 1,  [ 4, "0" ]  ],
        #     "Y": [ 1,  [ 4, "0" ]  ]
        #  },
        return genIndent(level) + "goTo(" + self.mathExpr(block, 'X') + \
                ", " + self.mathExpr(block, 'Y') + ");\n"

    def pointTowards(self, level, block, deferYield = False):
        """Generate code to turn the sprite to point to something.
        """
        child = block.getChild('TOWARDS')
        argVal = child.getFields()['TOWARDS'][0]
        if argVal == '_mouse_':
            return genIndent(level) + "pointTowardMouse();\n"
        else:   # pointing toward a sprite
            return genIndent(level) + 'pointToward("' + argVal + '");\n'


    def glideTo(self, level, block, deferYield = False):
        """Generate code to make the sprite glide to a certain x,y position
        in a certain amount of time.
        The block contains the time, and a child block that specifies if
        it is gliding to a random position, the mouse, or another sprite
        """
        child = block.getChild('TO')
        argVal = child.getFields()['TO'][0]
        if argVal == "_mouse_":
            return genIndent(level) + "glideToMouse(s, " + self.mathExpr(block, 'SECS') + ");\n"
        elif argVal == "_random_":
            return genIndent(level) + "glideToRandomPosition(s, " + self.mathExpr(block, 'SECS') + ");\n"
        else:       # gliding to another sprite
            return genIndent(level) + 'glideToSprite(s, "%s", %s);\n' % \
                        (argVal, self.mathExpr(block, 'DURATION'))

    def sayForSecs(self, level, block, deferYield = False):
        """Generate code to handle say <str> for <n> seconds.
        """
        # inputs contains (for the basic case):
        # "MESSAGE": [ 1, [ 10, "Hello!" ] ],
        # "SECS": [ 1, [ 4, "2" ] ]
        arg1 = block.getInputs()['MESSAGE'][1][1]
        return genIndent(level) + "sayForNSeconds(s, " + self.strExpr(arg1) + ", " + \
               self.mathExpr(block, 'SECS') + ");\n"

    def say(self, level, block, deferYield = False):
        """Generate code to handle say <str>.
        """
        arg = block.getInputs()['MESSAGE'][1][1]
        assert block.getOpcode() == "looks_say"
        return genIndent(level) + "say(" + self.strExpr(arg) + ");\n"
    
    def thinkForSecs(self, level, block, deferYield = False):
        """Generate code to handle think <str> for <n> seconds.
        """
        arg1 = block.getInputs()['MESSAGE'][1][1]
        return genIndent(level) + "thinkForNSeconds(s, " + self.strExpr(arg1) + ", " + \
               self.mathExpr(block, 'SECS') + ");\n"
    
    def think(self, level, block, deferYield = False):
        """Generate code to handle think <str>.
        """
        arg1 = block.getInputs()['MESSAGE'][1][1]
        assert block.getOpcode() == "looks_think"
        return genIndent(level) + "think(" + self.strExpr(arg1) + ");\n"

    def show(self, level, block, deferYield = False):
        """Generate code for the show block.
        """
        return genIndent(level) + "show();\n"

    def hide(self, level, block, deferYield = False):
        """Generate code for the show block.
        """
        return genIndent(level) + "hide();\n"

    def switchCostumeTo(self, level, block, deferYield = False):
        """Generate code for the switch costume block.
        """
        # the child of block is a looks_costume block, with COSTUME in 'fields',
        # and the value in 'fields' being the costume name.
        arg = block.getChild('COSTUME').getFields()['COSTUME'][0]
        try:
            # TODO!
            return genIndent(level) + "switchToCostume(" + self.oldMathExpr(arg) + ");\n"
        except (ValueError, AssertionError):
            # if mathExpr is unable to resolve arg, use strExpr instead
            return genIndent(level) + "switchToCostume(" + self.strExpr(arg) + ");\n"

    def nextCostume(self, level, block, deferYield = False):
        """Generate code for the next costume block.
        """
        assert block.getOpcode() == "looks_nextcostume"
        return genIndent(level) + "nextCostume();\n"

    def switchBackdropTo(self, level, tokens, deferYield = False):
        """Generate code to switch the backdrop.
        """
        cmd, arg1 = tokens
        assert cmd == "startScene"
        return genIndent(level) + "switchBackdropTo(" + self.strExpr(arg1) + ");\n"

    def nextBackdrop(self, level, block, deferYield = False):
        """Generate code to switch to the next backdrop.
        """
        return genIndent(level) + "nextBackdrop();\n"

    def changeSizeBy(self, level, block, deferYield = False):
        """Generate code to change the size of the sprite
        """
        return genIndent(level) + "changeSizeBy(" + self.mathExpr(block, 'CHANGE') + ");\n"

    def setSizeTo(self, level, block, deferYield = False):
        """Generate code to change the size of the sprite to a certain percentage
        """
        return genIndent(level) + "setSizeTo(" + self.mathExpr(block, 'SIZE') + ");\n"

    def goToFront(self, level, tokens, deferYield = False):
        """Generate code to move the sprite to the front
        """
        assert tokens[0] == "comeToFront"
        return genIndent(level) + "goToFront();\n"

    def goBackNLayers(self, level, tokens, deferYield = False):
        """Generate code to move the sprite back 1 layer in the paint order
        """
        cmd, arg1 = tokens
        assert cmd == "goBackByLayers:"
        return genIndent(level) + "goBackNLayers(" + self.oldMathExpr(arg1) + ");\n"

    def changeGraphicBy(self, level, tokens, deferYield = False):
        cmd, arg1, arg2 = tokens
        assert(cmd == "changeGraphicEffect:by:")
        if arg1 == "ghost":
            return genIndent(level) + "changeGhostEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "pixelate":
            return genIndent(level) + "changePixelateEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "whirl":
            return genIndent(level) + "changeWhirlEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "fisheye":
            return genIndent(level) + "changeFisheyeEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "mosaic":
            return genIndent(level) + "changeMosaicEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "brightness":
            return genIndent(level) + "changeBrightnessEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "color":
            return genIndent(level) + "changeColorEffectBy(" + self.oldMathExpr(arg2) + ");\n"
        else:
            return genIndent(level) + "// " + arg1 + " effect is not implemented\n" 
        
    def setGraphicTo(self, level, tokens, deferYield = False):
        cmd, arg1, arg2 = tokens
        assert(cmd == "setGraphicEffect:to:")
        if arg1 == "ghost":
            return genIndent(level) + "setGhostEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "pixelate":
            return genIndent(level) + "setPixelateEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "whirl":
            return genIndent(level) + "setWhirlEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "fisheye":
            return genIndent(level) + "setFisheyeEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "mosaic":
            return genIndent(level) + "setMosaicEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "brightness":
            return genIndent(level) + "setBrightnessEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        elif arg1 == "color":
            return genIndent(level) + "setColorEffectTo(" + self.oldMathExpr(arg2) + ");\n"
        else:
            return genIndent(level) + "// " + arg1 + " effect is not implemented\n"  


    def penClear(self, level, block, deferYield = False):
        return genIndent(level) + "clear();\n"

    def penDown(self, level, block, deferYield = False):
        return genIndent(level) + "penDown();\n"

    def penUp(self, level, block, deferYield = False):
        return genIndent(level) + "penDown();\n"

    def penStamp(self, level, block, deferYield = False):
        return genIndent(level) + "stamp();\n"

    def setPenColor(self, level, block, deferYield = False):
        # TODO: need to add code to import java.awt.Color  ??
        # color is a string like "#a249e8"
        # TODO: TEST!
        color = block.getInputs()['COLOR'][1][1]
        color = color[1:]       # lose the first # sign
        return genIndent(level) + 'setPenColor(new java.awt.Color(0x%s));\n' % color

    def changePenSizeBy(self, level, block, deferYield = False):
        return genIndent(level) + "changePenSizeBy(" + self.mathExpr(block, 'SIZE') + ");\n"

    def setPenSizeTo(self, level, block, deferYield = False):
        return genIndent(level) + "setPenSize(" + self.mathExpr(block, 'SIZE') + ");\n"

    def setPenColorParamBy(self, level, block, deferYield = False):
        '''Change color or saturation, etc., by an amount'''
        thingToChange = block.getChild('COLOR_PARAM').getFields()['colorParam'][0]
        if thingToChange == 'color':
            return genIndent(level) + "changePenColorBy(" + self.mathExpr(block, 'VALUE') + ");\n"
        else:
            raise ValueError('Cannot change pen %s now' % thingToChange)

    def setPenColorParamTo(self, level, block, deferYield = False):
        '''Set color or saturation, etc., to an amount'''
        thingToChange = block.getChild('COLOR_PARAM').getFields()['colorParam'][0]
        if thingToChange == 'color':
            return genIndent(level) + "setPenColor(" + self.mathExpr(block, 'VALUE') + ");\n"
        else:
            raise ValueError('Cannot change pen %s now' % thingToChange)

    # def pen1Arg(self, level, block, deferYield = False):
    #     """Generate code to handle Pen blocks with 1 argument."""

    #     assert len(tokens) == 2
    #     cmd, arg = tokens
    #     resStr = genIndent(level)
    #     if cmd == "changePenHueBy:":
    #         return resStr + "changePenColorBy(" + self.oldMathExpr(arg) + ");\n"
    #     elif cmd == "setPenHueTo:":
    #         return resStr + "setPenColor(" + self.oldMathExpr(arg) + ");\n"
    #     else:
    #         raise ValueError(cmd)

    def getNameTypeAndLocalGlobal(self, varTok):
        """Look up the token representing a variable name in the varInfo
        dictionaries.  If it is found, return the type and whether it
        is a local variable or global.  Global is known if it is found
        in the stage object.  Raise ValueError if it isn't found
        in the dictionaries.
        """

        global stage

        nameAndVarType = self.varInfo.get(varTok)
        if nameAndVarType is not None:
            # if self is the stage object, then finding it means it
            # is global, else not.
            return (nameAndVarType[0], nameAndVarType[1], self == stage)
        nameAndVarType = stage.getVarInfo(varTok)
        if nameAndVarType is not None:
            return (nameAndVarType[0], nameAndVarType[1], True)
        raise ValueError("Sprite " + self._name + " variable " +
                         varTok + " unknown.")
        
    def getListNameAndScope(self, listTok):
        global stage
        
        name = self.listInfo.get(listTok)
        if name is not None:
            return (name, self == stage)
        name = stage.getListInfo(listTok)
        if name is not None:
            return (name, True)
        raise ValueError("Sprite " + self._name + " list " + listTok + " unknown.")

    def setVariable(self, level, tokens, deferYield = False):
        """Set a variable's value from within the code.
        Generate code like this:
        var.set(value)
        tokens is: ["setVar:to:", "varName", [expression]]

        The variable may be sprite-specific or global.  We have to check
        both dictionaries to figure it out.
        """
        varName, varType, isGlobal = self.getNameTypeAndLocalGlobal(tokens[1])
        if varType == 'Boolean':
            val = self.boolExpr(tokens[2])
        elif varType in ('Int', 'Double'):
            val = self.oldMathExpr(tokens[2])
        else:
            val = self.strExpr(tokens[2])

        if isGlobal:
            # Something like: world.counter.set(0);
            return genIndent(level) + "Stage.%s.set(%s);\n" % \
                   (varName, val)
        else:
            return genIndent(level) + varName + ".set(" + val + ");\n"


    def readVariable(self, varname):
        """Get a variable's value from within the code.
        Generate code like this:
        var.get() or
        world.varname.get()

        The variable may be sprite-specific or global.  We have to check
        both dictionaries to figure it out.
        """

        varName, _, isGlobal = self.getNameTypeAndLocalGlobal(varname)
        if isGlobal:
            # Something like: world.counter.get();
            return "Stage.%s.get()" % varName
        else:
            return varName + ".get()"


    def hideVariable(self, level, tokens, deferYield = False):
        """Generate code to hide a variable.
        """
        varName, _, isGlobal = self.getNameTypeAndLocalGlobal(tokens[1])
        if isGlobal:
            # Something like: world.counter.hide();
            return genIndent(level) + "Stage.%s.hide();\n" % varName
        else:
            return genIndent(level) + varName + ".hide();\n"


    def showVariable(self, level, tokens, deferYield = False):
        """Generate code to hide a variable.
        """
        varName, _, isGlobal = self.getNameTypeAndLocalGlobal(tokens[1])
        if isGlobal:
            # Something like: world.counter.show();
            return genIndent(level) + "Stage.%s.show();\n" % varName
        else:
            return genIndent(level) + varName + ".show();\n"


    def changeVarBy(self, level, tokens, deferYield = False):
        """Generate code to change the value of a variable.
        Code will be like this:
        aVar.set(aVar.get() + 3);
        """
        varName, _, isGlobal = self.getNameTypeAndLocalGlobal(tokens[1])
        if isGlobal:
            # Something like:
            # world.counter.set(world.counter.get() + 1);
            return genIndent(level) + \
                   "Stage.%s.set(Stage.%s.get() + %s);\n" % \
                   (varName, varName, self.oldMathExpr(tokens[2]))
        else:
            return genIndent(level) + varName + ".set(" + \
                   varName + ".get() + " + self.oldMathExpr(tokens[2]) + ");\n"
                   
    def listContains(self, listname, obj):
        disp, glob = self.getListNameAndScope(listname)
        
        # If the argument is a int or double literal, use that, otherwise strExpr
        if isinstance(obj, int):
            obj = str(obj)
        elif isinstance(obj, float):
            obj = str(obj)
        else:
            obj = self.strExpr(obj)

        if glob:
            return '(Stage.%s.contains(%s))' % (disp, obj)
        else:
            return '(%s.contains(%s))' % (disp, obj)
        
    def listElement(self, index, listname):
        disp, glob = self.getListNameAndScope(listname)
        
        # If the argument is a int or double literal, use that, otherwise strExpr
        if isinstance(index, int):
            index = str(index)
        elif isinstance(index, float):
            index = str(index)
        elif index == 'last':
            index = '"last"'
        elif index == 'random':
            index = '"random"'
        else:
            index = self.strExpr(index)

        if glob:
            return "Stage.%s.numberAt(%s)" % (disp, index)
        else:
            return "%s.numberAt(%s)" % (disp, index)
        
    def listLength(self, listname):
        disp, glob = self.getListNameAndScope(listname)
        if glob:
            return "Stage.%s.length()" % (disp)
        else:
            return "%s.length()" % (disp)
        
    def listAppend(self, level, tokens, deferYield = False):
        cmd, obj, name = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'append:toList:'
        
        # If the argument is a int or double literal, use that, otherwise strExpr
        if isinstance(obj, int):
            obj = str(obj)
        elif isinstance(obj, float):
            obj = str(obj)
        else:
            obj = self.strExpr(obj)
        
        if glob:
            return '%sStage.%s.add(%s);\n' % (genIndent(level), disp, obj)
        else:
            return '%s%s.add(%s);\n' % (genIndent(level), disp, obj)
        
    def listRemove(self, level, tokens, deferYield = False):
        cmd, index, name = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'deleteLine:ofList:'        
        # If the argument is a int or double literal, use that, otherwise mathExpr
        if isinstance(index, int):
            index = str(index)
        elif isinstance(index, float):
            index = str(index)           
        elif index == 'last':
            index = '"last"'
        elif index == 'all':
            index = '"all"'
        else:
            index = self.oldMathExpr(index)
            
        if glob:
            return "%sStage.%s.delete(%s);\n" % (genIndent(level), disp, index)
        else:
            return "%s%s.delete(%s);\n" % (genIndent(level), disp, index)
    
    def listInsert(self, level, tokens, deferYield = False):
        cmd, obj, index, name = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'insert:at:ofList:'
        
        # If the argument is a int or double literal, use that, otherwise strExpr
        if isinstance(obj, int):
            obj = str(obj)
        elif isinstance(obj, float):
            obj = str(obj)
        else:
            obj = self.strExpr(obj)
        # If the argument is a int or double literal, use that, otherwise mathExpr
        if isinstance(index, int):
            index = str(index)
        elif isinstance(index, float):
            index = str(index)
        elif index == 'last':
            index = '"last"'
        elif index == 'random':
            index = '"random"'
        else:
            index = self.oldMathExpr(index)

        if glob:
            return '%sStage.%s.insert(%s, %s);\n' % (genIndent(level), disp, index, obj)
        else:
            return '%s%s.insert(%s, %s);\n' % (genIndent(level), disp, index, obj)
                
    def listSet(self, level, tokens, deferYield = False):
        cmd, index, name, obj = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'setLine:ofList:to:'
        
        # If the argument is a int or double literal, use that, otherwise strExpr
        if isinstance(obj, int):
            obj = str(obj)
        elif isinstance(obj, float):
            obj = str(obj)
        else:
            obj = self.strExpr(obj)
        # If the argument is a int or double literal, use that, otherwise mathExpr
        if isinstance(index, int):
            index = str(index)
        elif isinstance(index, float):
            index = str(index)
        elif index == 'last':
            index = '"last"'
        elif index == 'random':
            index = '"random"'
        else:
            index = self.oldMathExpr(index)

        if glob:
            return '%sStage.%s.replaceItem(%s, %s);\n' % (genIndent(level), disp, index, obj)
        else:
            return '%s%s.replaceItem(%s, %s);\n' % (genIndent(level), disp, index, obj)
                    
    def hideList(self, level, tokens, deferYield = False):
        cmd, name = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'hideList:'
        if glob:
            return "%sStage.%s.hide();\n" % (genIndent(level), disp)
        else:
            return "%s%s.hide();\n" % (genIndent(level), disp)
        
    def showList(self, level, tokens, deferYield = False):
        cmd, name = tokens
        disp, glob = self.getListNameAndScope(name)
        assert cmd == 'showList:'
        if glob:
            return "%sStage.%s.show();\n" % (genIndent(level), disp)
        else:
            return "%s%s.show();\n" % (genIndent(level), disp)

    def broadcast(self, level, block, deferYield = False):
        """Generate code to handle sending a broacast message.
        """
        arg = block.getInputs()['BROADCAST_INPUT'][1][1]
        return genIndent(level) + "broadcast(" + self.strExpr(arg) + ");\n"


    def broadcastAndWait(self, level, block, deferYield = False):
        """Generate code to handle sending a broacast message and
        waiting until all the handlers have completed.
        """
        arg = block.getInputs()['BROADCAST_INPUT'][1][1]
        return genIndent(level) + "broadcastAndWait(s, " + self.strExpr(arg) + ");\n"


    def doAsk(self, level, tokens, deferYield = False):
        """Generate code to ask the user for input.  Returns the resulting String."""

        assert len(tokens) == 2 and tokens[0] == "doAsk"
        quest = tokens[1]
        return genIndent(level) + "String answer = askStringAndWait(" + \
               self.strExpr(quest) + ");\t\t// may want to replace answer with a better name\n"


    def doWait(self, level, block, deferYield = False):
        """Generate a wait call."""
        assert block.getOpcode() == "control_wait"
        # inputs: "DURATION": [ 1,  [  5,  "1" ] ]
        return genIndent(level) + "wait(s, " + self.mathExpr(block, 'DURATION') + ");\n"


    def doRepeat(self, level, block, deferYield = False):
        """Generate a repeat <n> times loop.
        """
        retStr = genIndent(level) + "for (int i" + str(level) + " = 0; i" + str(level) + " < " + \
                 self.mathExpr(block, 'TIMES') + "; i" + str(level) + "++)\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.stmts(level, block.getChild('SUBSTACK'))
        if (deferYield):
            retStr += genIndent(level + 1) + \
                        "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                        "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def doWaitUntil(self, level, block, deferYield = False):
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


    def repeatUntil(self, level, tokens, deferYield = False):
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
        if (deferYield):
            retStr += genIndent(level + 1) + \
                        "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                        "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"


    def stopScripts(self, level, tokens, deferYield = False):
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


    def createCloneOf(self, level, block, deferYield = False):
        """Create a clone of the sprite itself or of the given sprite.
        """
        child = block.getChild('CLONE_OPTION')
        argVal = child.getFields()['CLONE_OPTION'][0]
        if argVal == "_myself_":
            return genIndent(level) + "createCloneOfMyself();\n"
        else:
            return genIndent(level) + 'createCloneOf("' + argVal + '");\n'


    def deleteThisClone(self, level, block, deferYield = False):
        """Delete this sprite.
        """
        return genIndent(level) + "deleteThisClone();\n"


    def resetTimer(self, level, tokens, deferYield = False):
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
                    paramTypes.append("double")	# TODO: probably usually int
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
        codeObj.addToCbCode(self.block(1, code, decl[4]))
        codeObj.addToCbCode("\n")	# add blank line after function defn.
        return codeObj


    def callABlock(self, level, tokens, deferYield = False):
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
            resStr += self.oldMathExpr(tokens[i]) + ", "
        resStr += self.oldMathExpr(tokens[-1]) + ");\n"
        return resStr

    def playSound(self, level, block, deferYield = False):
        """ Play the given sound
        """
        arg = block.getChild('SOUND_MENU').getFields()['SOUND_MENU'][0]
        return genIndent(level) + "playSound(" + self.strExpr(arg) + ");\n"

    def playSoundUntilDone(self, level, block, deferYield = False):
        """ Play the given sound without interrupting it.
        """
        arg = block.getChild('SOUND_MENU').getFields()['SOUND_MENU'][0]
        return genIndent(level) + "playSoundUntilDone(" + self.strExpr(arg) + ");\n"
    
    def playNote(self, level, block, deferYield = False):
        """ Play the given note for a given number of beats
        """
        note = block.getChild('NOTE').getFields()['NOTE'][0]
        return genIndent(level) + "playNote(s, " + self.oldMathExpr(note) + ", " + self.mathExpr(block, 'BEATS') + ");\n"
    
    def instrument(self, level, block, deferYield = False):
        """ Play the given instrument
        """
        arg = block.getChild('INSTRUMENT').getFields()['INSTRUMENT'][0]
        return genIndent(level) + "changeInstrument(" + self.oldMathExpr(arg) + ");\n"
    
    def playDrum(self, level, block, deferYield = False):
        """ Play the given drum
        """
        drum = block.getChild('DRUM').getFields()['DRUM'][0]
        return genIndent(level) + "playDrum(s, " + self.oldMathExpr(drum) + ", " + self.mathExpr(block, 'BEATS') + ");\n"
    
    def rest(self, level, block, deferYield = False):
        """ Play a rest for the given number of beats.
        """
        return genIndent(level) + "rest(s, " + self.mathExpr(block, 'BEATS') + ");\n"
    
    def changeTempoBy(self, level, block, deferYield = False):
        """ Change the tempo.
        """
        return genIndent(level) + "changeTempoBy(" + self.mathExpr(block, 'TEMPO') + ");\n"
    
    def setTempoTo(self, level, block, deferYield = False):
        """ Set the tempo
        """
        return genIndent(level) + "setTempo(" + self.mathExpr(block, 'TEMPO') + ");\n"

    def resolveName(self, name):
        """Ask the user what each variable should be named if it is not a
        legal identifier
        """
        while True:
            try:
                print("\"" + name + "\" is not a valid java variable name.")
                n = input("Java variables must start with a letter and contain only letters and numbers.\n" +\
                      "Enter a new name, or type nothing to use \"" + convertToJavaId(name, True, False) + "\"\n> ")
                if n == "":
                    return convertToJavaId(name, True, False)
                name = n
                if convertToJavaId(n, True, False) == n:
                    return n
            except IndexError:
                # The variable name has no valid characters
                print("\"" + name + "\" must have some alphanumeric character in order to suggest a name")
                name = "variable:" + name
            

              
    def genScriptCode(self, topBlock):
        """Generate code (and callback code) for the given topBlock, which may be
        associated with either a sprite or the main stage.
        """

        codeObj = CodeAndCb()	# Holds all the code that is generated.

        opcode = topBlock.getOpcode()
        if opcode == 'event_whenflagclicked':
            self.whenFlagClicked(codeObj, topBlock)
        elif opcode == 'control_start_as_clone':
            self.whenSpriteCloned(codeObj, topBlock)
        elif opcode == 'event_whenthisspriteclicked':
            self.whenClicked(codeObj, topBlock)
        elif opcode == 'event_whenkeypressed':
            self.whenKeyPressed(codeObj, topBlock)
        elif opcode == 'event_whenbroadcastreceived':
            self.whenIReceive(codeObj, topBlock)
        elif isinstance(topBlock, list) and topBlock[0] == 'whenSceneStarts':
            self.whenSwitchToBackdrop(codeObj, topBlock[1], blocks[1:])
        elif isinstance(topBlock, list) and topBlock[0] == 'procDef':
            # Defining a procedure in Scratch.
            self.genProcDefCode(codeObj, blocks)

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
        name = convertToJavaId(sprData['name'], True, True)

        super().__init__(name, sprData)

    def genLoadCostumesCode(self, costumes):
        """Generate code to load costumes from files for a sprite.
        """
        # print("genLoadCC: costumes ->" + str(costumes) + "<-")
        resStr = ""
        # imagesDir = os.path.join(PROJECT_DIR, "images")
        for cos in costumes:
            fname = cos['assetId'] + ".png"
            resStr += genIndent(2) + 'addCostume("' + fname + \
                      '", "' + cos['name'] + '");\n'
        self._costumeCode += resStr

    def genInitSettingsCode(self):
        """Generate code to set the sprite's initial settings, like its
        location on the screen, the direction it is facing, whether shown
        or hidden, etc.
        """
        resStr = ""

        costumeIdx = self._sprData['currentCostume']
        costumeName = self._sprData['costumes'][costumeIdx]['name']

        # Set the initial costume 
        resStr = genIndent(2) + 'switchToCostume("' + costumeName + '");\n'

        # TODO: using size instead of scale.  Removed multiplying by 100 here!  Test!
        if self._sprData['size'] != 100:
            resStr += genIndent(2) + 'setSizeTo(' + str(self._sprData['size']) + ');\n'
        if not self._sprData['visible']:
            resStr += genIndent(2) + 'hide();\n'
        resStr += genIndent(2) + 'pointInDirection(' + str(self._sprData['direction']) + ');\n'
        resStr += self.genRotationStyle(2, self._sprData['rotationStyle'])
        self._initSettingsCode += resStr

    def whenClicked(self, codeObj, block):
        """Generate code to handle the whenClicked block.
        All code in block goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        cbName = 'whenSpriteClickedCb' + str(scriptNum)
        codeObj.addToCode(genIndent(2) + 'whenSpriteClicked("' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + \
                        "(Sequence s)\n"
        cbStr += self.block(1, block) + "\n"  # add blank line after defn.
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
        resStr = ""
        for costume in costumes:
            fname = costume['assetId'] + ".png"
            resStr += genIndent(2) + 'addBackdrop("' + fname + \
                      '", "' + costume['name'] + '");\n'
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
        if debug:
            print("initSettingsCode =", self._initSettingsCode)

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
        outFile.write(self._varDefnCode)

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
def convert():
    global SCRATCH_FILE
    global PROJECT_DIR
    global SCRATCH_PROJ_DIR
    
    global imagesDir 
    global soundsDir 
    global worldClassName
    global stage
    print ("---------" + SCRATCH_FILE)
    
    if not os.path.exists(SCRATCH_FILE):
        print("Scratch download file " + SCRATCH_FILE + " not found.")
        sys.exit(1)
    if not os.path.exists(PROJECT_DIR):
        if useGui:
            if (tkinter.messagebox.askokcancel("Make New Directory", "Greenfoot directory not found, generate it?")):
                print("Generating new project directory...")
                os.makedirs(PROJECT_DIR)
            else:
                sys.exit(1)
        else:
            if (input("Project directory not found, generate it? (y/n)\n> ") == "y"):
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
        if width >= 480:
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
    except Exception as e:
        print("\n\tScratch.java and ScratchWorld.java were NOT copied!", e)
        
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
    except Exception as e:
        print("\n\tImages for say/think were NOT all copied!", e)
    
    worldClassName = convertToJavaId(os.path.basename(PROJECT_DIR).replace(" ", ""), True, True) + "World"
    
    # End of preparing directories, copying files, etc,
    # ---------------------------------------------------------------------------
    
    
    # Now, (finally!), open the project.json file and start processing it.
    with open(os.path.join(scratch_dir, "project.json"), encoding = "utf_8") as data_file:
        data = json.load(data_file)

    spritesData = data['targets']
    
    # We'll need to write configuration "code" to the greenfoot.project file.  Store
    # the lines to write out in this variable.
    projectFileCode = []
    
    # Determine the name of the ScratchWorld subclass.  This variable below
    # is used in some code above to generate casts.  I know this is a very bad
    # idea, but hey, what are you going to do...
    # Take the last component of the PROJECT_DIR, convert it to a legal
    # Java identifier, then add World to end.
    
    
    
    # If there are global variables, they are defined in the outermost part
    # of the json data, and more info about each is defined in objects labeled
    # with "target": "Stage" in 'childen'.
    # These need to be processed before we process any Sprite-specific code
    # which may reference these global variables.
    
    # stage information is in targets where isStage is set to true.
    for stageData in spritesData:
        if stageData['isStage']:
            break

    stage = Stage(stageData)
    
    if 'variables' in data and 'lists' in data:
        stage.genVariablesDefnCode(data['variables'], data['lists'], data['children'], cloudVars)
    elif 'variables' in data:
        stage.genVariablesDefnCode(data['variables'], (), data['children'], cloudVars)
    elif 'lists' in data:
        stage.genVariablesDefnCode((), data['lists'], data['children'], cloudVars)
    
    # Code to be written into the World.java file.
    worldCtorCode = ""
    
    
    # ---------------------------------------------------------------------------
    # Start processing each sprite's info: scripts, costumes, variables, etc.
    # ---------------------------------------------------------------------------
    for sprData in spritesData:
        if sprData['isStage']:
            continue                # skip the stage for now.

    
        sprite = Sprite(sprData)
        
        # Copy the sounds associated with this sprite to the appropriate directory
        sprite.copySounds(soundsDir)
        
        # Generate world construct code that adds the sprite to the world.
        sprite.genAddSpriteCall()
        sprite.genLoadCostumesCode(sprData['costumes'])
        # Like location, direction, shown or hidden, etc.
        sprite.genInitSettingsCode()

        # Handle variables defined for this sprite.  This has to be done
        # before handling the scripts, as the scripts may refer will the
        # variables.
        # Variable initializations have to be done in a method called
        # addedToWorld(), which is not necessary if no variable defns exist.
        sprite.genVariablesDefnCode(sprData['variables'], sprData['lists'], data['targets'], cloudVars)

        sprite.genCodeForScripts()
        sprite.writeCodeToFile()
        worldCtorCode += sprite.getWorldCtorCode()

        # Write out a line to the project.greenfoot file to indicate that this
        # sprite is a subclass of the Scratch class.
        projectFileCode.append("class." + sprite.getName() + ".superclass=Scratch\n")
        # Generate a line to the project.greenfoot file to set the image
        # file, like this: 
        #     class.Sprite1.image=1.png
        projectFileCode.append("class." + sprite.getName() + ".image=" + \
                            str(sprData['costumes'][0]['assetId']) + ".png\n")
    
    
    # --------- handle the Stage stuff --------------
    
    # Because the stage can have script in it much like any sprite,
    # we have to process it similarly.  So, lots of repeated code here
    # from above -- although small parts are different enough.

    costumes = stageData['costumes']
        
    # Write out a line to the project.greenfoot file to indicate that this
    # sprite is a subclass of the Scratch class.
    projectFileCode.append("class." + stage.getName() + ".superclass=Scratch\n")
    
    # Create the special Stage sprite.
    worldCtorCode += genIndent(2) + 'addSprite("' + stage.getName() + '", 0, 0);\n'
    
    stage.genInitSettingsCode()
    stage.genLoadCostumesCode(costumes)
    stage.genBackgroundHandlingCode()
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
    worldCode += genWorldCtorHeader(worldClassName)
    
    worldCode += stage.getWorldCtorCode()
    
    # Adding the backdrops will be done in the World constructor, not
    # the stage constructor because backdrops (backgrounds) are a property
    # of the World in Greenfoot.
    addBackdropsCode = stage.getCostumesCode()
    if debug:
        print("CostumeCode is ", addBackdropsCode)
    
    costumeIdx = stageData['currentCostume']
    costumeName = stageData['costumes'][costumeIdx]['name']
    addBackdropsCode += genIndent(2) + 'switchBackdropTo("' + costumeName + '");\n'
    
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
            projF.write("mainWindow.height=550\n")
            projF.write("mainWindow.width=800\n")
            projF.write("mainWindow.x=40\n")
            projF.write("mainWindow.y=40\n")
            projF.write("package.numDependencies=0\n")
            projF.write("package.numTargets=0\n")
            projF.write("project.charset=UTF-8\n")
            projF.write("version=3.1.0\n")
        
    # Read all lines into variable lines.
    lines = []
    with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "r") as projF:
        lines = projF.readlines()
    # Now, open in "w" mode which resets the file back to being empty.
    with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "w") as projF:
        for line in lines:
            if line in projectFileCode:
                # Remove the line in projectFileCode that matches.
                if debug:
                    print("DEBUG: removing " + line + " from projFileCode because already in file.")
                projectFileCode.remove(line)
            projF.write(line)
        # Now write the remaining lines out from projectFileCode
        for p in projectFileCode:
            if debug:
                print("DEBUG: writing this line to project.greenfoot file:", p)
            projF.write(p)




if not useGui:  # Everything provided on command line.
    imagesDir = os.path.join(PROJECT_DIR, "images")
    soundsDir = os.path.join(PROJECT_DIR, "sounds")
    convert()
else:
    def findScratchFile():
        global scrEntryVar, SCRATCH_FILE
        SCRATCH_FILE = tkinter.filedialog.askopenfilename(initialdir = SCRATCH_FILE,
                                                  filetypes = [('Scratch3 files', '.sb3'), 
                                                               ('All files', '.*')])
        scrEntryVar.set(SCRATCH_FILE)
            
    def findGfDir():
        global gfEntryVar, PROJECT_DIR
        PROJECT_DIR = tkinter.filedialog.askdirectory(initialdir=PROJECT_DIR)
        gfEntryVar.set(PROJECT_DIR)
    
    def exitTk():
        sys.exit(0)
    root = tkinter.Tk()
    root.title("Convert Scratch to Greenfoot")
    root.protocol('WM_DELETE_WINDOW', exitTk)
    
    entryFrame = tkinter.Frame(root)
    entryFrame.pack(side = tkinter.TOP)
    scratchFrame = tkinter.Frame(entryFrame)
    scratchFrame.pack(side = tkinter.LEFT)
    scratchLabel = tkinter.Label(scratchFrame, text="Scratch File")
    scratchLabel.pack(side = tkinter.TOP)
    scrEntryVar = tkinter.StringVar()
    scrEntryVar.set(SCRATCH_FILE)
    scratchEntry = tkinter.Entry(scratchFrame, textvariable=scrEntryVar, width=len(SCRATCH_FILE))
    scratchEntry.pack(side = tkinter.TOP)
    tkinter.Button(scratchFrame, text="Find file", command=findScratchFile).pack(side=tkinter.TOP)
    
    
    gfFrame = tkinter.Frame(entryFrame)
    gfFrame.pack(side = tkinter.RIGHT)
    gfLabel = tkinter.Label(gfFrame, text = "Greenfoot Project Directory")
    gfLabel.pack(side = tkinter.TOP)
    gfEntryVar = tkinter.StringVar()
    gfEntryVar.set(PROJECT_DIR)
    gfEntry = tkinter.Entry(gfFrame, textvariable=gfEntryVar, width=len(PROJECT_DIR))
    gfEntry.pack(side = tkinter.TOP)
    tkinter.Button(gfFrame, text="Find directory", command=findGfDir).pack(side=tkinter.TOP)

    def convertButtonCb():
        global SCRATCH_FILE
        global PROJECT_DIR
        global SCRATCH_PROJ_DIR
        
        global imagesDir 
        global soundsDir 
        
        # Take off spaces and a possible trailing "/"
        PROJECT_DIR = gfEntryVar.get().strip().rstrip("/")
        
        print("--------" + SCRATCH_FILE)
        SCRATCH_PROJ_DIR = "scratch_code"
    
        imagesDir = os.path.join(PROJECT_DIR, "images")
        soundsDir = os.path.join(PROJECT_DIR, "sounds")
        convert()
        
    convertButton = tkinter.Button(root, text = "Convert", command = convertButtonCb)
    convertButton.pack(side = tkinter.BOTTOM)
    root.mainloop()
