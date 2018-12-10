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
import tkinter.messagebox

# Global Variables that can be set via command-line arguments.
debug = False
inference = False
name_resolution = False
useGui = False

# Indentation level in outputted Java code.
NUM_SPACES_PER_LEVEL = 4

# This variable tracks how many cloud variables have been generated, and
# serves as each cloud var's id
cloudVars = 0

worldClassName = ""

# A list of all variables, some local, some global
allVars = []

# Set up arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("-d", "--dotypeinference", action="store_true", help="Automatically infer variable types")
parser.add_argument("-r", "--resolvevariablenames", action="store_true", help="Automatically convert to java ids")
parser.add_argument("-g", "--gui", action="store_true", help="Use GUI converter (Experimental)")
parser.add_argument('-o', "--onlydecode", action="store_true",
                    help="Only decode the project.json, don't move files, etc.")
parser.add_argument("--scratch_file", help="Location of scratch sb2/sb3 file", default=os.getcwd(), required=False)
parser.add_argument("--greenfoot_dir", help="Location of greenfoot project directory", default=os.getcwd(),
                    required=False)
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
onlyDecode = args.onlydecode

SCRATCH_FILE = args.scratch_file.strip()
# Take off spaces and a possible trailing "/"
PROJECT_DIR = args.greenfoot_dir.strip().rstrip("/")
SCRATCH_PROJ_DIR = "scratch_code"
if SCRATCH_FILE.endswith('.sb2'):
    print('Scratch conversion only works with Scratch 3.0')
    sys.exit(-1)

# Initialize stage globally
stage = None

JAVA_KEYWORDS = ('abstract', 'continue', 'for', 'new', 'switch', 'assert', 'default', 'goto', \
                 'package', 'synchronized', 'boolean', 'do', 'if', 'private', 'this', 'break', \
                 'double', 'implements', 'protected', 'throw', 'byte', 'else', 'import', 'public', \
                 'throws', 'case', 'enum', 'instanceof', 'return', 'transient', 'catch', 'extends', \
                 'int', 'short', 'try', 'char', 'final', 'interface', 'static', 'void', 'class', 'finally', \
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
                ch = ch.upper()  # does nothing if isdigit.
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


class Variable:
    """Represents a single variable defined in Scratch, and
    includes properties of it: its name, type, what sprite
    it belongs to, whether it is a cloud variable or not, its
    uniqueId defined in Scratch, etc."""

    # NOTE NOTE NOTE: there does not seem to be any information in the project.json
    # file now about persistence, whether it is shown or not, slider, etc...
    def __init__(self, uniqId, json):
        """json is of this format
           [
              "vic",                          <-- unsanitized scratch name
              "44"                            <-- initial value
           ]
           or for a list
           [
              "alist",
              [  "firstitem", "seconditem" ]
           ]
        """
        self._json = json
        self._uniqId = uniqId
        self._type = None
        self._scratchName = json[0]
        self._initValue = json[1]
        self._isCloud = False
        self._owner = None
        self._local_or_global = None
        self._gfName = None
        # Stuff used for GUI when converting types, resolving
        # names, etc.
        self._nameEntry = None
        self._typeStringVar = None
        self._initValueEntry = None
        print('Variable with name %s, gfname %s, uniqId %s defined' % (self._scratchName, self._gfName, self._uniqId), self._initValue)
        allVars.append(self)

    def setGfName(self, name):
        self._gfName = name

    def setType(self, type):
        self._type = type

    def setOwner(self, owner):
        self._owner = owner

    def setGlobal(self):
        self._local_or_global = 'global'

    def setLocal(self):
        self._local_or_global = 'local'

    def getName(self): return self._scratchName

    def getInitValue(self): return self._initValue

    def getOwner(self): return self._owner

    def getType(self): return self._type

    def getGfName(self): return self._gfName

    def getUniqueId(self): return self._uniqId

    def isLocal(self):
        assert self._local_or_global is not None
        return self._local_or_global == 'local'

    def isGlobal(self):
        assert self._local_or_global is not None
        return self._local_or_global == 'global'

    def setNameEntry(self, ent):
        self._ent = ent

    def setTypeStringVar(self, svar):
        self._svar = svar

    def setInitialValueEntry(self, ive):
        self._initValueEntry = ive


def getVariableBySpriteAndName(sprite, name):
    """
    :param sprite: the sprite object
    :param name: the name of the variable
    :return: var found in allVars list
    """

    for v in allVars:
        if v.getOwner() == sprite and v.getName() == name:
            return v
    return None


def getVariableByUniqueId(id):
    """
    :param id: unique block id
    :return: var found in allVars list
    """

    print('looking up var with id', id)

    for v in allVars:
        if v.getUniqueId() == id:
            return v
    return None


class Block:
    """
    This represents a Scratch Block, with its opcode, parent,
    children, inputs, etc.
    """

    def __init__(self, id, opcode):
        self._id = id
        self._opcode = opcode
        self._inputs = {}
        self._fields = {}
        self._topLevel = False
        self._next = None
        # dictionary mapping key -> child block.
        self._children = {}
        # Used for calling a user-defined procedure.
        self._procCode = None
        self._procArgIds = []
        self._procDefnParamNames = []

    def setInputs(self, inputs):
        """inputs are a json object (for now)"""
        self._inputs = inputs

    def setFields(self, fields):
        """fields are a json object (for now)"""
        self._fields = fields

    def setTopLevel(self, val):
        self._topLevel = val

    def setNext(self, blockObj):
        self._next = blockObj

    def setChild(self, key, childBlock):
        if key in self._children:
            raise ValueError('block has child with key %s already' % key)
        self._children[key] = childBlock

    def setProcCode(self, proccode):
        self._procCode = proccode

    def setProcCallArgIds(self, j):
        self._procArgIds = json.loads(j)

    def setProcDefnParamNames(self, j):
        self._procDefnParamNames = json.loads(j)

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

    def getInput(self, key):
        return self._inputs[key]

    def getFields(self):
        return self._fields

    def getField(self, key, index=0):
        return self.getFields()[key][index]

    def getChild(self, key):
        return self._children[key]

    def getProcCode(self):
        return self._procCode

    def getProcCallArgIds(self):
        return self._procArgIds

    def getProcDefnParamNames(self):
        return self._procDefnParamNames

    def strWithIndent(self, indentLevel=0):
        res = ("  " * indentLevel) + str(self)
        n = self._next
        while n:
            res += "\n" + str(n)
            n = n._next
        return res

    def __str__(self):
        return "BLOCK: " + self._opcode


class SpriteOrStage:
    """This is an abstract class that represents either a Stage class or
    Sprite class to be generated in Java.  The two are the same for
    most/all script code generation.  They differ primarily in the set up
    code, constructor code, etc.
    """

    def __init__(self, name, sprData):
        """Construct an object holding information about the sprite,
        including code we are generating for it, its name, world
        constructor code for it, etc.
        """

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
        """Might return None if name not found in the mapping.
        Otherwise, returns a tuple: (clean name, varType)"""
        return self.varInfo.get(name)

    def getListInfo(self, name):
        """Might return None if name not found in the mapping.
        Otherwise, returns a tuple: (clean name, varType)"""
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

    def genVariablesDefnCode(self, varsObjects, listsObjects, allChildren, cloudVars):
        """Generate code to define instance variables for this sprite.
        The varsObjects is a list of dictionaries, one per variable (see below).
        The allChildren is the list of dictionaries defined for this
        project. It is necessary because sprites and their scripts (in a
        dictionary with an "objName" key) are in children, also a dictionary
        exists for each variable, with a "cmd" --> "getVar:" entry.  We
        need info from both the varsObjects and each of those other
        variable-specific dictionaries.
        """

        # TODO: fix all this documentation.

        # The varsObjects has this format:
        #  [{ "name": "xloc",
        #     "value": false,
        #     "isPersistent": false
        #     }]
        # We get the name and default value from this easily, but we have to derive
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
        # for each variable in the varsObjects list:
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
                    e.insert(tkinter.END, convertToJavaId(s))
                for i in range(0, len(typeList)):
                    try:
                        typeList[i].set(deriveType("", valueList[i].get())[1])
                    except ValueError:
                        typeList[i].set("String")
                keypress()

            # Display a help message informing the user how to use the namer
            def helpCB():
                tkinter.messagebox.showinfo("Help",
                                            "If a name is red, that means it is not valid in Java. Java variable names must " +
                                            "start with a letter, and contain only letters, numbers and _. (No spaces!) There are also " +
                                            "some words that can't be variable names because they mean something special in java: \n" +
                                            str(JAVA_KEYWORDS) + ". \n\nIf a type " +
                                            "is red, that means it is not a valid type. The types that work with this " +
                                            "converter are:\n\tInt: a number that will never be a decimal\n\tDouble: a number " +
                                            "that can be a decimal\n\tString: symbols, letters, and text\n\nIf a value is red, " +
                                            "that means that the variable cannot store that value. For example, an Int " +
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
                    print(("Processing var: " + name).encode('utf-8'))
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
                            x = varInfo['x']  # Not used at this time.
                            y = varInfo['y']  # Not used at this time.
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
                        sanname = convertToJavaId(name)
                    except:
                        print("Error converting list to java id")
                        sys.exit(0)

                    self.listInfo[name] = sanname

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

            # --------------- genVariablesDefnCodeGui main ------------------------------------

            gui = tkinter.Toplevel(root)
            # gui.bind("<Any-KeyPress>", keypress)

            gui.title("Variable Namer")
            gui.grab_set()

            table = tkinter.Frame(gui)
            table.pack()
            buttons = tkinter.Frame(gui)
            buttons.pack(side=tkinter.BOTTOM)
            auto = tkinter.Button(buttons, text="Auto-Convert", command=autoCB)
            auto.pack(side=tkinter.LEFT)
            confirm = tkinter.Button(buttons, text="Confirm", command=confirmCB)
            confirm.pack(side=tkinter.LEFT)
            help = tkinter.Button(buttons, text="Help", command=helpCB)
            help.pack(side=tkinter.LEFT)
            tkinter.Label(table, text="  Scratch Name  ").grid(row=0, column=0)
            tkinter.Label(table, text="Java Name").grid(row=0, column=1)
            tkinter.Label(table, text="Java Type").grid(row=0, column=2)
            tkinter.Label(table, text="Starting Value").grid(row=0, column=3)

            # Populate lists
            row = 1
            for var in listOfVars:
                name = var['name']  # unsanitized Scratch name
                value = var['value']
                cloud = var['isPersistent']
                lbl = tkinter.Entry(table)
                lbl.insert(tkinter.END, name)
                lbl.configure(state="readonly")
                lbl.grid(row=row, column=0, sticky=tkinter.W + tkinter.E)

                ent = tkinter.Entry(table)
                ent.insert(tkinter.END, name)
                ent.grid(row=row, column=1, sticky=tkinter.W + tkinter.E)

                nameList.append(ent)
                svar = tkinter.StringVar(gui)
                ent2 = tkinter.OptionMenu(table, svar, "Int", "Double", "String")
                ent2.grid(row=row, column=2, sticky=tkinter.W + tkinter.E)
                # ent2.bind("<Button-1>", keypress)

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
                    theType = input("\tInt: A number that won't have decimals\n\tDouble:" +
                                    " A number that can have decimals\n\tString: Text or letters\n" +
                                    "This variable looks like: " + typechosen +
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
                    if input("Could not convert " + str(val) + " to " + theType +
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
                raise ValueError("deriveType cannot figure out type of -->" +
                                 str(val) + "<--")

        # -------------------------- genVariablesDefnCode main starts here -----------------------------

        # create an object for each variable and store in a list.
        # Each variable definition block looks like this:
        # "jd59I%YWo]3`[L`d?tD[": [         <-- unique id
        # "vic",                          <-- name
        # "44"                            <-- initial value
        # ]
        theseVars = [Variable(varId, varsObjects[varId]) for varId in varsObjects]

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
            genVariablesDefnCodeGui(varsObjects, listsObjects, allChildren, cloudVars)
            return

        for var in theseVars:
            name = var.getName()  # unsanitized Scratch name
            value = var.getInitValue()
            cloud = False  # TODO var['isPersistent']

            # return the varType and the value converted to a java equivalent
            # for that type. (e.g., False --> false)
            # varType is one of 'Boolean', 'Double', 'Int', 'String'
            if cloud:  # TODO: this is always False for now.
                value = cloudVars
                cloudVars += 1
                varType = 'Cloud'
                # The first character is a weird Unicode cloud glyph and the
                # second is a space.  Get rid of them.
                name = name[2:]
            else:
                value, varType = chooseType(name, value)

            var.setType(varType)

            # Sanitize the name: make it a legal Java identifier.
            try:
                if name_resolution:
                    sanname = convertToJavaId(name)
                elif not convertToJavaId(name) == name:
                    sanname = self.resolveName(name)
                else:
                    sanname = convertToJavaId(name)
            except:
                print("Error converting variable to java id")
                sys.exit(0)

            var.setGfName(sanname)
            self.setVariableIsLocalOrGlobal(var)
            var.setOwner(self)

            '''
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
            '''

            # Something like "Scratch.IntVar score; or ScratchWorld.IntVar score;"
            self._varDefnCode += self.genVarDefnCode(1, var)

            # Something like "score = createIntVariable((MyWorld) world, "score", 0);
            self._addedToWorldCode += '%s%s = create%sVariable((%s) world, "%s", %s);\n' % \
                                      (genIndent(2), sanname, varType, worldClassName, name, str(value))
            # if not visible:
            #     self._addedToWorldCode += genIndent(2) + sanname + ".hide();\n"

        # Add blank line after variable definitions.
        self._varDefnCode += "\n"
        self._addedToWorldCode += genIndent(2) + "// List initializations.\n"

        theseVars = [Variable(varId, listsObjects[varId]) for varId in listsObjects]

        for alist in theseVars:
            name = alist.getName()  # unsanitized Scratch name
            contents = alist.getInitValue()
            print('contents is -->', contents)
            try:
                sanname = convertToJavaId(name)
            except:
                print("Error converting list to java id")
                sys.exit(0)
            alist.setGfName(sanname)
            self.setVariableIsLocalOrGlobal(alist)
            alist.setOwner(self)

            self._varDefnCode += self.genListDefnCode(1, alist)

            self._addedToWorldCode += '%s%s = createList(world, "%s"' % (genIndent(2), sanname, name)
            for obj in contents:
                # use deriveType to convert to an Int or Double or Boolean, etc.
                convertedVal, valType = deriveType(name, obj)
                self._addedToWorldCode += ', %s' % str(convertedVal)
            self._addedToWorldCode += ');\n'

            # TODO: not supported in scratch 3.0 downloaded file yet.
            # if not visible:
            #     self._addedToWorldCode += '%s%s.hide();\n' % (genIndent(2), sanname)

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

        allBlocks = {}  # Map of blockId to Block object.

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
            if 'mutation' in vals:
                if 'proccode' in vals['mutation']:
                    block.setProcCode(vals['mutation']['proccode'])
                if 'argumentids' in vals['mutation']:
                    block.setProcCallArgIds(vals['mutation']['argumentids'])
                if 'argumentnames' in vals['mutation']:
                    block.setProcDefnParamNames(vals['mutation']['argumentnames'])

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

    def topBlock(self, level, topBlock, deferYield=False):
        """Handle a top block containing a list of statements wrapped in { }."""
        return genIndent(level) + "{\n" + self.statements(level, topBlock.getNext(), deferYield) + \
               genIndent(level) + "}\n"

    def block(self, level, block, deferYield=False):
        """Handle a block that is the first in a list of statements wrapped in { }."""
        return genIndent(level) + "{\n" + self.statements(level, block, deferYield) + \
               genIndent(level) + "}\n"

    def statements(self, level, firstBlock, deferYield=False):
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

    def stmt(self, level, block, deferYield=False):
        """Handle a statement, which is a block object
        """

        scratchStmt2genCode = {

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

            'looks_sayforsecs': self.sayForSecs,
            'looks_say': self.say,
            'looks_thinkforsecs': self.thinkForSecs,
            'looks_think': self.think,
            'looks_show': self.show,
            'looks_hide': self.hide,
            'looks_switchcostumeto': self.switchCostumeTo,
            'looks_nextcostume': self.nextCostume,
            'looks_switchbackdropto': self.switchBackdropTo,
            'looks_changesizeby': self.changeSizeBy,
            'looks_setsizeto': self.setSizeTo,
            'looks_gotofrontback': self.goToFrontBack,
            'looks_goforwardbackwardlayers': self.goForwBackNLayers,
            'looks_nextbackdrop': self.nextBackdrop,
            'looks_changeeffectby': self.changeGraphicBy,
            'looks_seteffectto': self.setGraphicTo,

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
            'data_setvariableto': self.setVariable,
            'data_hidevariable': self.hideVariable,
            'data_showvariable': self.showVariable,
            'data_changevariableby': self.changeVarBy,

            'data_addtolist': self.listAppend,
            'data_deleteoflist': self.listDeleteAt,
            'data_deletealloflist': self.listDeleteAll,
            'data_insertatlist': self.listInsert,
            'data_replaceitemoflist': self.listSet,
            'hideList:': self.hideList,
            'showList:': self.showList,

            'event_broadcast': self.broadcast,
            'event_broadcastandwait': self.broadcastAndWait,

            'control_forever': self.doForever,
            'control_wait': self.doWait,
            'control_repeat': self.doRepeat,
            'control_create_clone_of': self.createCloneOf,
            'control_delete_this_clone': self.deleteThisClone,
            'control_if': self.doIf,
            'control_if_else': self.doIfElse,
            'control_wait_until': self.doWaitUntil,
            'control_repeat_until': self.repeatUntil,
            'control_stop': self.stopScripts,

            # Sensing commands
            'sensing_askandwait': self.doAsk,
            'sensing_resettimer': self.resetTimer,

            # Sound commands
            'sound_play': self.playSound,
            'sound_playuntildone': self.playSoundUntilDone,

            # Midi commands
            'music_playNoteForBeats': self.playNote,
            'music_setInstrument': self.instrument,
            'music_playDrumForBeats': self.playDrum,
            'music_restForBeats': self.rest,
            'music_changeTempo': self.changeTempoBy,
            'music_setTempo': self.setTempoTo,

            # User-defined function
            'procedures_call': self.callABlock,
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
        """

        opcode = block.getOpcode()
        if opcode == 'operator_lt':
            # TODO: assume numbers for less than... bad idea?
            return '(' + self.mathExpr(block, 'OPERAND1') + ' < ' + \
                   self.mathExpr(block, 'OPERAND2') + ')'
        elif opcode == 'operator_gt':
            # TODO: assume numbers for less than... bad idea?
            return '(' + self.mathExpr(block, 'OPERAND1') + ' > ' + \
                   self.mathExpr(block, 'OPERAND2') + ')'
        elif opcode == 'operator_equals':
            # TODO: assume numbers for equals... bad idea?
            return '(' + self.mathExpr(block, 'OPERAND1') + ' == ' + \
                   self.mathExpr(block, 'OPERAND2') + ')'
        elif opcode == 'operator_and':
            return '(' + self.boolExpr(block.getChild('OPERAND1')) + ' && ' + \
                   self.boolExpr(block.getChild('OPERAND2')) + ')'
        elif opcode == 'operator_or':
            return '(' + self.boolExpr(block.getChild('OPERAND1')) + ' || ' + \
                   self.boolExpr(block.getChild('OPERAND2')) + ')'
        elif opcode == 'operator_not':
            return '( !' + self.boolExpr(block.getChild('OPERAND')) + ')'
        elif opcode == 'sensing_touchingobject':
            arg = block.getChild('TOUCHINGOBJECTMENU').getField('TOUCHINGOBJECTMENU')
            if arg == '_mouse_':
                return "(isTouchingMouse())"
            elif arg == "_edge_":
                return "(isTouchingEdge())"
            else:  # touching another sprite
                return '(isTouching("' + arg + '"))'
        elif opcode == 'sensing_touchingcolor':
            # TODO: does not support expressions that evaluate to a color
            color = block.getInputs()['COLOR'][1][1][1:]  # remove the leading #-sign
            return "(isTouchingColor(new java.awt.Color(0x" + color + ")))"
        elif opcode == 'sensing_coloristouchingcolor':
            return 'Unsupported boolean expression: ' + opcode
        elif opcode == 'sensing_mousedown':
            return "(isMouseDown())"
        elif opcode == 'sensing_keypressed':
            keyoption = block.getChild('KEY_OPTION').getField('KEY_OPTION')
            return '(isKeyPressed("' + convertKeyPressName(keyoption) + '"))'
        elif opcode == 'data_listcontainsitem':
            return self.listContains(block)
        else:
            raise ValueError('unsupported op', opcode)

        '''
        elif firstOp == 'list:contains:':
            resStr += self.listContains(tokenList[1], tokenList[2])
        elif firstOp == False:
            resStr += "false"
        else:
            raise ValueError(firstOp)
        return resStr
        '''

    def strExpr(self, block, exprKey):
        """Evaluate a string-producing expression (or literal).
        """
        expr = block.getInput(exprKey)
        assert isinstance(expr, list)

        if debug:
            print('strExpr: ', block, exprKey, expr)

        if not block.hasChild(exprKey):
            expr = block.getInput(exprKey)
            # if expr[1][0] is 12, then we are referencing a variable (guess).
            if expr[1][0] == 12:  # TOTAL GUESS!
                return self.handleVariableReference(expr[1])
            return '"' + expr[1][1] + '"'

        # e.g., [  3,  'alongidhere', [ 4, "10" ] ]
        # the value after 'alongidhere' is the default value -- we don't care about this.
        child = block.getChild(exprKey)
        opcode = child.getOpcode()
        if opcode == 'operator_join':
            return 'join(' + self.strExpr(child, 'STRING1') + ', ' + self.strExpr(child, 'STRING2') + ')'
        elif opcode == 'operator_letter_of':
            return "letterNOf(" + self.mathExpr(child, 'LETTER') + ", " + self.strExpr(child, 'STRING') + ")"
        elif opcode == 'looks_costumenumbername':
            numberOrName = child.getField('NUMBER_NAME')
            if numberOrName == 'name':
                return 'costumeName()'
            elif numberOrName == 'number':
                return "String.valueOf(costumeNumber())"
        elif opcode == 'looks_backdropnumbername':
            numberOrName = child.getField('NUMBER_NAME')
            if numberOrName == 'name':
                return 'backdropName()'
            elif numberOrName == 'number':
                return "String.valueOf(backdropNumber())"
        elif opcode == 'looks_costume':
            return '"' + child.getField('COSTUME') + '"'
        elif opcode == 'looks_backdrops':
            return '"' + child.getField('BACKDROP') + '"'
        elif opcode == 'sensing_answer':
            return 'answer'
        elif opcode == 'sensing_of':
            return 'String.valueOf(' + self.getAttributeOf(child) + ')'
        elif opcode == 'argument_reporter_string_number':
            return self.procDefnUseParamName(child)
        elif opcode == 'data_itemnumoflist':
            return self.listElement(child)
        else:
            # You can put math expression in where strings are expected
            # and they are automatically used.  So, we'll try that
            # too.
            return "String.valueOf(" + str(self.mathExpr(block, 'MESSAGE')) + ")"

    def handleVariableReference(self, expr):
        # Handle variable references here.
        # The item at index 1 is the name, and the item at index 2 is the uniqueId
        # of the block where the variable was defined.
        # The first thing in expr is always a number and I can't figure out what that means.
        assert len(expr) == 3
        var = getVariableByUniqueId(expr[2])
        if var.isLocal():
            return var.getGfName() + ".get()"
        else:
            return 'Stage.%s.get()' % var.getGfName()

    def evalMathThenStrThenBool(self, block, key):
        try:
            resStr = self.mathExpr(block, key)
        except:
            try:
                resStr = self.strExpr(block, key)
            except:
                resStr = self.boolExpr(block.getChild(key))
        return resStr

    def mathExpr(self, block, exprKey):
        """Evaluate the expression in block[exprKey] and its children, as a math expression,
        returning a string equivalent."""

        expr = block.getInput(exprKey)
        assert isinstance(expr, list)

        print('mathExpr: Evaluating block', block, ' and expr ', expr)

        if not block.hasChild(exprKey):
            expr = block.getInput(exprKey)

            # if expr[1][0] is 12, then we are referencing a variable (guess).
            if expr[1][0] == 12:  # TOTAL GUESS!
                return self.handleVariableReference(expr[1])
            val = expr[1][1]
            if val == '':
                # Scratch allows an empty placeholder and seems to use
                # the value 0 in this case.
                return '0'
            try:
                int(val)
                return str(val)
            except:
                try:
                    float(val)
                    return str(val)
                except:
                    # the raw value does not convert to a number, so
                    # raise an error
                    raise

        # e.g., [  3,  'alongidhere', [ 4, "10" ] ]
        # the value after 'alongidhere' is the default value -- we don't care about this.
        child = block.getChild(exprKey)
        opcode = child.getOpcode()
        if opcode == 'operator_add':
            return '(' + self.mathExpr(child, 'NUM1') + ' + ' + self.mathExpr(child, 'NUM2') + ')'
        elif opcode == 'operator_subtract':
            return '(' + self.mathExpr(child, 'NUM1') + ' - ' + self.mathExpr(child, 'NUM2') + ')'
        elif opcode == 'operator_multiply':
            return '(' + self.mathExpr(child, 'NUM1') + ' * ' + self.mathExpr(child, 'NUM2') + ')'
        elif opcode == 'operator_divide':
            return '(' + self.mathExpr(child, 'NUM1') + ' / ' + self.mathExpr(child, 'NUM2') + ')'
        elif opcode == 'operator_mod':
            return '(' + "Math.floorMod(" + self.mathExpr(child, 'NUM1') + ", " + self.mathExpr(child, 'NUM2') + "))"
        elif opcode == 'operator_round':
            return '(' + "Math.round((float) " + self.mathExpr(child, 'NUM') + "))"
        elif opcode == 'operator_mathop':
            mathop = child.getField('OPERATOR')
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
        elif opcode == 'operator_length':
            arg = child.getInputs()['STRING'][1][1]
            # TODO: should call strExpr 
            return "lengthOf(" + arg + ")"
        elif opcode == 'operator_random':
            return "pickRandom(" + self.mathExpr(child, 'FROM') + ", " + self.mathExpr(child, 'TO') + ")"
        elif opcode == 'motion_xposition':
            return 'getX()'
        elif opcode == 'motion_ypos':
            return "getY()"
        elif opcode == 'motion_direction':
            return "getDirection()"
        elif opcode == "looks_costumenumbername":
            if child.getField('NUMBER_NAME') == 'number':
                return "costumeNumber()"
            else:
                raise ValueError('not supported yet')
        elif opcode == 'looks_backdropnumbername':
            if child.getField('NUMBER_NAME') == 'number':
                return 'getBackdropNumber()'
            else:
                raise ValueError('not supported yet')
        elif opcode == "looks_size":
            return "size()"
        elif opcode == "sensing_mousedown":
            # this will produce uncompileable Java code... but if you try this kind of
            # thing, you are kind of asking for it...
            return " (int) isMouseDown()"
        elif opcode == "sensing_mousex":
            return "getMouseX()"
        elif opcode == 'sensing_mousey':
            return "getMouseY()"
        elif opcode == "sensing_timer":
            return "getTimer()"
        elif opcode == "sensing_dayssince2000":
            return "daysSince2000()"
        elif opcode == 'sensing_current':
            return self.genSensingCurrentDateEtc(child)
        elif opcode == "sensing_distanceto":
            grandchild = child.getChild('DISTANCETOMENU')
            arg = grandchild.getField('DISTANCETOMENU')
            if arg == '_mouse_':
                return "distanceToMouse()"
            else:  # must be distance to a sprite
                return 'distanceTo("' + arg + '")'
        elif opcode == 'sensing_of':
            return self.getAttributeOf(child)
        elif opcode == 'argument_reporter_string_number':
            return self.procDefnUseParamName(child)
        else:
            raise ValueError("Unsupported operator %s" % opcode)

    def procDefnUseParamName(self, block):
        paramName = block.getField('VALUE')
        return convertToJavaId(paramName)

    def genSensingCurrentDateEtc(self, block):
        option = block.getField('CURRENTMENU')
        if option == "MINUTE":
            return 'getCurrentMinute()'
        elif option == "MONTH":
            return 'getCurrentMonth()'
        elif option == "SECOND":
            return 'getCurrentSecond()'
        elif option == "HOUR":
            return 'getCurrentHour()'
        elif option == "YEAR":
            return 'getCurrentYear()'
        elif option == 'DAYOFWEEK':
            return 'getCurrentDayOfWeek()'
        elif option == 'DATE':
            return 'getCurrentDate()'
        else:
            raise ValueError('Unknown date/time sensing: ' + option)

    def getAttributeOf(self, block):
        """Return code to handle the various sensing_of calls
        from the sensing block.
        """
        objChild = block.getChild('OBJECT').getField('OBJECT')
        prop = block.getField('PROPERTY')

        if objChild == 'Stage':
            # most of the attributes -- direction, x position, etc. --
            # return 0 in Scratch.  We'll do the same, obviously.
            if prop in ('direction', 'x position', 'y position', 'costume name', 'costume #', 'size', 'volume'):
                return 0
            if prop == 'backdrop #':
                return "backdropNumber()"
            elif prop == 'backdrop name':
                return 'backdropName()'
            else:
                return 'Unknown property: ' + prop

        # object is a sprite name
        mapping = {'x position': 'xPositionOf',
                   'y position': 'yPositionOf',
                   'direction': 'directionOf',
                   'costume #': 'costumeNumberOf',
                   'costume name': 'costumeNameOf',
                   'size': 'sizeOf',
                   }
        if prop in mapping:
            return mapping[prop] + '("' + objChild + '")'
        elif prop in ('backdrop #', 'backdrop name', 'volume'):
            return 0  # bogus in Scratch and here too
        else:
            # TODO: We must assume that this is a variable, as not all variable have necessarily
            # been parsed yet. Note that because of this, we cannot look up the actual name
            # of the variable, we must use the unsanitized name. TODO fix this 
            return '((' + prop + ')world.getActorByName("' + objChild + '")).' + tok1 + '.get()'

    def whenFlagClicked(self, codeObj, block):
        """Generate code to handle the whenFlagClicked block.
        All code in block goes into a callback.
        """
        scriptNum = codeObj.getNextScriptId()
        # Build a name like whenFlagClickedCb0 
        cbName = 'whenFlagClickedCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenFlagClicked("' + cbName + '");\n')

        level = 1  # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                "(Sequence s)\n"
        cbStr += self.topBlock(level, block) + "\n"  # add blank line after defn.
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
        cbStr += self.topBlock(1, topBlock) + "\n"  # add blank line after defn.
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
        key = topBlock.getField('KEY_OPTION')
        key = convertKeyPressName(key)

        # Build a name like whenAPressedCb0 or whenLeftPressedCb0.
        cbName = 'when' + key.capitalize() + 'PressedCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenKeyPressed("' +
                          key + '", "' + cbName + '");\n')

        level = 1  # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                "(Sequence s)\n"
        cbStr += self.topBlock(level, topBlock) + "\n"  # add blank line after defn.

        codeObj.addToCbCode(cbStr)

    def whenIReceive(self, codeObj, topBlock):
        """Generate code to handle the whenIReceive block.  
        topBlock contains the message and the list of statements to be put
        into a callback to be called when that message is received.
        """
        scriptNum = codeObj.getNextScriptId()

        # Build a name like whenIReceiveMessage1Cb0
        message = topBlock.getField('BROADCAST_OPTION')
        messageId = convertToJavaId(message, noLeadingNumber=False, capitalizeFirst=True)
        cbName = 'whenIReceive' + messageId + 'Cb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenRecvMessage("' +
                          message + '", "' + cbName + '");\n')

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        # All cb code is at level 1
        cbStr = "\n\n" + genIndent(1) + "public void " + cbName + "(Sequence s)\n"
        cbStr += self.topBlock(1, topBlock) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)

    def whenSwitchToBackdrop(self, codeObj, backdrop, tokens):
        """Generate code to handle the whenSwitchToBackdrop block.  key is
        the key to wait for, and tokens is the list of statements to be put
        into a callback to be called when that key is pressed.
        """
        scriptNum = codeObj.getNextScriptId()

        # Build a name like whenAPressedCb0 or whenLeftPressedCb0.
        cbName = 'whenSwitchedToBackdropCb' + str(scriptNum)

        # Code in the constructor is always level 2.
        codeObj.addToCode(genIndent(2) + 'whenSwitchToBackdrop("' +
                          backdrop + '", "' + cbName + '");\n')

        level = 1  # all callbacks are at level 1.

        # Generate callback code, into the codeObj's cbCode string.
        # Add two blank lines before each method definition.
        cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                "(Sequence s)\n"
        cbStr += self.topBlock(level, tokens) + "\n"  # add blank line after defn.

        codeObj.addToCbCode(cbStr)

    def doForever(self, level, block, deferYield=False):
        """Generate doForever code.  block is the topblock with 
        children hanging off of it.
        forever loop is turned into a while (true) loop, with the last
        operation being a yield(s) call.
        """
        retStr = genIndent(level) + "while (true)\t\t// forever loop\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.statements(level, block.getChild('SUBSTACK'))
        if (deferYield):
            retStr += genIndent(level + 1) + \
                      "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                      "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"

    def doIf(self, level, block, deferYield=False):
        """Generate code for if <test> : <block>.
        """
        # Handle the boolean expression
        # We don't generate parens around the boolExpr as it will put them there.

        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(block.getChild('CONDITION'))
        resStr += "\n"
        resStr += self.block(level, block.getChild('SUBSTACK'))
        return resStr

    def doIfElse(self, level, block, deferYield=False):
        """Generate code for if <test> : <block> else: <block>.
        """

        resStr = genIndent(level) + "if "
        resStr += self.boolExpr(block.getChild('CONDITION'))
        resStr += "\n"
        resStr += self.block(level, block.getChild('SUBSTACK'))
        resStr += genIndent(level) + "else\n"
        resStr += self.block(level, block.getChild('SUBSTACK2'))
        return resStr

    def ifOnEdgeBounce(self, level, block, deferYield=False):
        """Generate code to handle Motion blocks with 0 arguments"""
        return genIndent(level) + "ifOnEdgeBounce();\n"

    def stripOutsideParens(self, s):
        if s[0] == '(' and s[-1] == ')':
            return s[1:-1]
        return s

    def moveSteps(self, level, block, deferYield=False):
        #     "inputs": {
        #       "STEPS": [  1,  [ 4, "10" ] ]
        #     },
        arg = self.stripOutsideParens(self.mathExpr(block, 'STEPS'))
        return genIndent(level) + "move(" + arg + ");\n"

    def turnRight(self, level, block, deferYield=False):
        # inputs is similar to moveSteps, but with DEGREES
        return genIndent(level) + "turnRightDegrees(" + self.mathExpr(block, 'DEGREES') + ");\n"

    def turnLeft(self, level, block, deferYield=False):
        return genIndent(level) + "turnLeftDegrees(" + self.mathExpr(block, 'DEGREES') + ");\n"

    def pointInDirection(self, level, block, deferYield=False):
        return genIndent(level) + "pointInDirection(" + self.mathExpr(block, 'DIRECTION') + ");\n"

    def goto(self, level, block, deferYield=False):
        return self.genGoto(level, block)

    def changeXBy(self, level, block, deferYield=False):
        return genIndent(level) + "changeXBy(" + self.mathExpr(block, 'DX') + ");\n"

    def changeYBy(self, level, block, deferYield=False):
        return genIndent(level) + "changeYBy(" + self.mathExpr(block, 'DY') + ");\n"

    def setX(self, level, block, deferYield=False):
        return genIndent(level) + "setXTo(" + self.mathExpr(block, 'X') + ");\n"

    def setY(self, level, block, deferYield=False):
        return genIndent(level) + "setYTo(" + self.mathExpr(block, 'Y') + ");\n"

    def setRotationStyle(self, level, block, deferYield=False):
        arg = block.getField('STYLE')
        return self.genRotationStyle(level, arg)

    def genGoto(self, level, block):
        child = block.getChild('TO')
        argVal = child.getField('TO')
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

    def gotoXY(self, level, block, deferYield=False):
        """Generate code to handle Motion blocks with 2 arguments:
        gotoxy, etc."""
        #  "inputs": {
        #     "X": [ 1,  [ 4, "0" ]  ],
        #     "Y": [ 1,  [ 4, "0" ]  ]
        #  },
        return genIndent(level) + "goTo(" + self.mathExpr(block, 'X') + \
               ", " + self.mathExpr(block, 'Y') + ");\n"

    def pointTowards(self, level, block, deferYield=False):
        """Generate code to turn the sprite to point to something.
        """
        child = block.getChild('TOWARDS')
        argVal = child.getField('TOWARDS')
        if argVal == '_mouse_':
            return genIndent(level) + "pointTowardMouse();\n"
        else:  # pointing toward a sprite
            return genIndent(level) + 'pointToward("' + argVal + '");\n'

    def glideTo(self, level, block, deferYield=False):
        """Generate code to make the sprite glide to a certain x,y position
        in a certain amount of time.
        The block contains the time, and a child block that specifies if
        it is gliding to a random position, the mouse, or another sprite
        """
        child = block.getChild('TO')
        argVal = child.getField('TO')
        if argVal == "_mouse_":
            return genIndent(level) + "glideToMouse(s, " + self.mathExpr(block, 'SECS') + ");\n"
        elif argVal == "_random_":
            return genIndent(level) + "glideToRandomPosition(s, " + self.mathExpr(block, 'SECS') + ");\n"
        else:  # gliding to another sprite
            return genIndent(level) + 'glideToSprite(s, "%s", %s);\n' % \
                   (argVal, self.mathExpr(block, 'DURATION'))

    def sayForSecs(self, level, block, deferYield=False):
        """Generate code to handle say <str> for <n> seconds.
        """
        # inputs contains (for the basic case):
        # "MESSAGE": [ 1, [ 10, "Hello!" ] ],
        # "SECS": [ 1, [ 4, "2" ] ]
        message = self.strExpr(block, 'MESSAGE')
        return genIndent(level) + "sayForNSeconds(s, " + message + ", " + \
               self.mathExpr(block, 'SECS') + ");\n"

    def say(self, level, block, deferYield=False):
        """Generate code to handle say <str>.
        """
        return genIndent(level) + "say(" + self.strExpr(block, 'MESSAGE') + ");\n"

    def thinkForSecs(self, level, block, deferYield=False):
        """Generate code to handle think <str> for <n> seconds.
        """
        return genIndent(level) + "thinkForNSeconds(s, " + self.strExpr(block, 'MESSAGE') + ", " + \
               self.mathExpr(block, 'SECS') + ");\n"

    def think(self, level, block, deferYield=False):
        """Generate code to handle think <str>.
        """
        return genIndent(level) + "think(" + self.strExpr(block, 'MESSAGE') + ");\n"

    def show(self, level, block, deferYield=False):
        """Generate code for the show block.
        """
        return genIndent(level) + "show();\n"

    def hide(self, level, block, deferYield=False):
        """Generate code for the show block.
        """
        return genIndent(level) + "hide();\n"

    def switchCostumeTo(self, level, block, deferYield=False):
        """Generate code for the switch costume block.
        """
        try:
            return genIndent(level) + "switchToCostume(" + self.strExpr(block, 'COSTUME') + ");\n"
        except Exception:
            # if strExpr is unable to resolve arg, use mathExpr instead
            return genIndent(level) + "switchToCostume(" + self.mathExpr(block, 'COSTUME') + ");\n"

    def nextCostume(self, level, block, deferYield=False):
        """Generate code for the next costume block.
        """
        assert block.getOpcode() == "looks_nextcostume"
        return genIndent(level) + "nextCostume();\n"

    def switchBackdropTo(self, level, block, deferYield=False):
        """Generate code to switch the backdrop.
        """
        try:
            return genIndent(level) + "switchBackdropTo(" + self.strExpr(block, 'BACKDROP') + ");\n"
        except Exception:
            # if strExpr is unable to resolve arg, use mathExpr instead
            return genIndent(level) + "switchBackdropTo(" + self.mathExpr(block, 'BACKDROP') + ");\n"

    def nextBackdrop(self, level, block, deferYield=False):
        """Generate code to switch to the next backdrop.
        """
        block.getOpcode()
        return genIndent(level) + "nextBackdrop();\n"

    def changeSizeBy(self, level, block, deferYield=False):
        """Generate code to change the size of the sprite
        """
        return genIndent(level) + "changeSizeBy(" + self.mathExpr(block, 'CHANGE') + ");\n"

    def setSizeTo(self, level, block, deferYield=False):
        """Generate code to change the size of the sprite to a certain percentage
        """
        return genIndent(level) + "setSizeTo(" + self.mathExpr(block, 'SIZE') + ");\n"

    def goToFrontBack(self, level, block, deferYield=False):
        """Generate code to move the sprite to the front
        """
        option = block.getField('FRONT_BACK')
        if option == 'front':
            return genIndent(level) + "goToFront();\n"
        else:
            return genIndent(level) + "goToBack();\n"

    def goForwBackNLayers(self, level, block, deferYield=False):
        """Generate code to move the sprite back 1 layer in the paint order
        """
        option = block.getField('FORWARD_BACKWARD')
        if option == 'forward':
            return genIndent(level) + "goForwardNLayers(" + self.mathExpr(block, 'NUM') + ");\n"
        else:
            return genIndent(level) + "goBackwardNLayers(" + self.mathExpr(block, 'NUM') + ");\n"

    def changeGraphicBy(self, level, block, deferYield=False):
        """Generate code to change the graphics effect on this sprite"""
        effect = block.getField('EFFECT')
        value = self.mathExpr(block, 'CHANGE')
        if effect == "GHOST":
            return genIndent(level) + "changeGhostEffectBy(" + value + ");\n"
        elif effect == "PIXELATE":
            return genIndent(level) + "changePixelateEffectBy(" + value + ");\n"
        elif effect == "WHIRL":
            return genIndent(level) + "changeWhirlEffectBy(" + value + ");\n"
        elif effect == "FISHEYE":
            return genIndent(level) + "changeFisheyeEffectBy(" + value + ");\n"
        elif effect == "MOSAIC":
            return genIndent(level) + "changeMosaicEffectBy(" + value + ");\n"
        elif effect == "BRIGHTNESS":
            return genIndent(level) + "changeBrightnessEffectBy(" + value + ");\n"
        elif effect == "COLOR":
            return genIndent(level) + "changeColorEffectBy(" + value + ");\n"
        else:
            return genIndent(level) + "// " + effect + " effect is not implemented\n"

    def setGraphicTo(self, level, block, deferYield=False):
        effect = block.getField('EFFECT')
        value = self.mathExpr(block, 'VALUE')
        if effect == "GHOST":
            return genIndent(level) + "setGhostEffectTo(" + value + ");\n"
        elif effect == "PIXELATE":
            return genIndent(level) + "setPixelateEffectTo(" + value + ");\n"
        elif effect == "WHIRL":
            return genIndent(level) + "setWhirlEffectTo(" + value + ");\n"
        elif effect == "FISHEYE":
            return genIndent(level) + "setFisheyeEffectTo(" + value + ");\n"
        elif effect == "MOSAIC":
            return genIndent(level) + "setMosaicEffectTo(" + value + ");\n"
        elif effect == "BRIGHTNESS":
            return genIndent(level) + "setBrightnessEffectTo(" + value + ");\n"
        elif effect == "COLOR":
            return genIndent(level) + "setColorEffectTo(" + value + ");\n"
        else:
            return genIndent(level) + "// " + effect + " effect is not implemented\n"

    def penClear(self, level, block, deferYield=False):
        return genIndent(level) + "clear();\n"

    def penDown(self, level, block, deferYield=False):
        return genIndent(level) + "penDown();\n"

    def penUp(self, level, block, deferYield=False):
        return genIndent(level) + "penDown();\n"

    def penStamp(self, level, block, deferYield=False):
        return genIndent(level) + "stamp();\n"

    def setPenColor(self, level, block, deferYield=False):
        # color is a string like "#a249e8"
        # TODO: TEST!
        color = block.getInputs()['COLOR'][1][1]
        color = color[1:]  # lose the first # sign
        return genIndent(level) + 'setPenColor(new java.awt.Color(0x%s));\n' % color

    def changePenSizeBy(self, level, block, deferYield=False):
        return genIndent(level) + "changePenSizeBy(" + self.mathExpr(block, 'SIZE') + ");\n"

    def setPenSizeTo(self, level, block, deferYield=False):
        return genIndent(level) + "setPenSize(" + self.mathExpr(block, 'SIZE') + ");\n"

    def setPenColorParamBy(self, level, block, deferYield=False):
        """Change color or saturation, etc., by an amount"""
        thingToChange = block.getChild('COLOR_PARAM').getField('colorParam')
        if thingToChange == 'color':
            return genIndent(level) + "changePenColorBy(" + self.mathExpr(block, 'VALUE') + ");\n"
        else:
            raise ValueError('Cannot change pen %s now' % thingToChange)

    def setPenColorParamTo(self, level, block, deferYield=False):
        """Set color or saturation, etc., to an amount"""
        thingToChange = block.getChild('COLOR_PARAM').getField('colorParam')
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

    # def getNameTypeAndLocalGlobal(self, varTok):
    #     """Look up the token representing a variable name in the varInfo
    #     dictionaries.  If it is found, return the type and whether it
    #     is a local variable or global.  Global is known if it is found
    #     in the stage object.  Raise ValueError if it isn't found
    #     in the dictionaries.
    #     """
    #
    #     global stage
    #
    #     nameAndVarType = self.varInfo.get(varTok)
    #     if nameAndVarType is not None:
    #         # if self is the stage object, then finding it means it
    #         # is global, else not.
    #         return (nameAndVarType[0], nameAndVarType[1], self == stage)
    #     nameAndVarType = stage.getVarInfo(varTok)
    #     if nameAndVarType is not None:
    #         return (nameAndVarType[0], nameAndVarType[1], True)
    #     raise ValueError("Sprite " + self._name + " variable " +
    #                      varTok + " unknown.")

    def getListNameAndScope(self, listTok):
        global stage

        name = self.listInfo.get(listTok)
        if name is not None:
            return (name, self == stage)
        name = stage.getListInfo(listTok)
        if name is not None:
            return (name, True)
        raise ValueError("Sprite " + self._name + " list " + listTok + " unknown.")

    def setVariable(self, level, block, deferYield=False):
        """Set a variable's value from within the code.
        Generate code like this:
        var.set(value)
        """

        var = getVariableBySpriteAndName(self, block.getField('VARIABLE'))
        if var == None:
            raise ValueError('No Variable object found for', block.getField('VARIABLE'))

        if var.getType() == 'Boolean':
            val = self.boolExpr(block)
        elif var.getType() in ('Int', 'Double'):
            val = self.mathExpr(block, 'VALUE')
        else:
            val = self.strExpr(block, 'VALUE')

        if var.isLocal():
            return genIndent(level) + var.getGfName() + ".set(" + val + ");\n"
        else:
            # Something like: Stage.counter.set(0);
            return genIndent(level) + "Stage.%s.set(%s);\n" % (var.getGfName(), val)

    # def readVariable(self, varname):
    #     """Get a variable's value from within the code.
    #     Generate code like this:
    #     var.get() or
    #     world.varname.get()
    #
    #     The variable may be sprite-specific or global.  We have to check
    #     both dictionaries to figure it out.
    #     """
    #
    #     varName, _, isGlobal = self.getNameTypeAndLocalGlobal(varname)
    #     if isGlobal:
    #         return varName + ".get()"
    #     else:
    #         # Something like: world.counter.get();
    #         return "Stage.%s.get()" % varName

    def hideVariable(self, level, block, deferYield=False):
        """Generate code to hide a variable.
        """
        id = block.getField('VARIABLE', 1)  # 0 is name, 1 is id
        var = getVariableByUniqueId(id)
        if var.isGlobal():
            # Something like: Stage.counter.hide();
            return genIndent(level) + "Stage.%s.hide();\n" % var.getGfName()
        else:
            return genIndent(level) + var.getGfName() + ".hide();\n"

    def showVariable(self, level, block, deferYield=False):
        """Generate code to hide a variable.
        """
        id = block.getField('VARIABLE', 1)  # 0 is name, 1 is id
        var = getVariableByUniqueId(id)
        if var.isGlobal():
            return genIndent(level) + "Stage.%s.show();\n" % var.getGfName()
        else:
            return genIndent(level) + var.getGfName() + ".show();\n"

    def changeVarBy(self, level, block, deferYield=False):
        """Generate code to change the value of a variable.
        Code will be like this:
        aVar.set(aVar.get() + 3);
        NOTE: only works for numeric expressions in Scratch, afaict.
        """
        id = block.getField('VARIABLE', 1)  # 0 is name, 1 is id
        var = getVariableByUniqueId(id)
        varName = var.getGfName()
        if var.isGlobal():
            # Something like: Stage.counter.set(world.counter.get() + 1);
            return genIndent(level) + \
                   "Stage.%s.set(Stage.%s.get() + %s);\n" % \
                   (varName, varName, self.mathExpr(block, 'VALUE'))
        else:
            return genIndent(level) + varName + ".set(" + \
                   varName + ".get() + " + self.mathExpr(block, 'VALUE') + ");\n"

    def listContains(self, block):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        item = self.evalMathThenStrThenBool(block, 'ITEM')

        if theList.isGlobal():
            return '(Stage.%s.contains(%s))' % (theList.getGfName(), item)
        else:
            return '(%s.contains(%s))' % (theList.getGfName(), item)

    def listElement(self, block):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        item = self.mathExpr(block, 'ITEM')

        if theList.isGlobal():
            return "Stage.%s.indexOf(%s)" % (theList.getGfName(), item)
        else:
            return "%s.indexOf(%s)" % (theList.getGfName(), item)

    def listLength(self, listname):
        disp, glob = self.getListNameAndScope(listname)
        if glob:
            return "Stage.%s.length()" % (disp)
        else:
            return "%s.length()" % (disp)

    def listAppend(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)

        resStr = self.evalMathThenStrThenBool(block, 'ITEM')

        if theList.isGlobal():
            return '%sStage.%s.add(%s);\n' % (genIndent(level), theList.getGfName(), resStr)
        else:
            return '%s%s.add(%s);\n' % (genIndent(level), theList.getGfName(), resStr)

    def listDeleteAt(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        index = self.mathExpr(block, 'INDEX')

        if theList.isGlobal():
            return "%sStage.%s.deleteAt(%s);\n" % (genIndent(level), theList.getGfName(), index)
        else:
            return "%s%s.deleteAt(%s);\n" % (genIndent(level), theList.getGfName(), index)

    def listDeleteAll(self, level, block, deferYield=False):
        """delete all the contents of the list"""

        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)

        if theList.isGlobal():
            return '%sStage.%s.deleteAll();\n' % (genIndent(level), theList.getGfName())
        else:
            return '%s%s.deleteAll();\n' % (genIndent(level), theList.getGfName())


    def listInsert(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        index = self.mathExpr(block, 'INDEX')

        resStr = self.evalMathThenStrThenBool(block, 'ITEM')

        if theList.isGlobal():
            return '%sStage.%s.insertAt(%s, %s);\n' % (genIndent(level), theList.getGfName(), index, resStr)
        else:
            return '%s%s.insertAt(%s, %s);\n' % (genIndent(level), theList.getGfName(), index, resStr)

    def listSet(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        index = self.mathExpr(block, 'INDEX')

        resStr = self.evalMathThenStrThenBool(block, 'ITEM')

        if theList.isGlobal():
            return '%sStage.%s.replaceItem(%s, %s);\n' % (genIndent(level), theList.getGfName(), index, resStr)
        else:
            return '%s%s.replaceItem(%s, %s);\n' % (genIndent(level), theList.getGfName(), index, resStr)

    def hideList(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        if theList.isGlobal():
            return "%sStage.%s.hide();\n" % (genIndent(level), theList.getGfName())
        else:
            return "%s%s.hide();\n" % (genIndent(level), theList.getGfName())

    def showList(self, level, block, deferYield=False):
        listId = block.getField('LIST', 1)   # index 1 is the list id.
        theList = getVariableByUniqueId(listId)
        if theList.isGlobal():
            return "%sStage.%s.show();\n" % (genIndent(level), theList.getGfName())
        else:
            return "%s%s.show();\n" % (genIndent(level), theList.getGfName())

    def broadcast(self, level, block, deferYield=False):
        """Generate code to handle sending a broacast message.
        """
        return genIndent(level) + "broadcast(" + self.strExpr(block, 'BROADCAST_INPUT') + ");\n"

    def broadcastAndWait(self, level, block, deferYield=False):
        """Generate code to handle sending a broacast message and
        waiting until all the handlers have completed.
        """
        return genIndent(level) + "broadcastAndWait(s, " + self.strExpr(block, 'BROADCAST_INPUT') + ");\n"

    def doAsk(self, level, block, deferYield=False):
        """Generate code to ask the user for input.  Returns the resulting string."""

        question = self.strExpr(block, 'QUESTION')
        return genIndent(level) + 'String answer = askStringAndWait(' + \
               question + ');\t\t// may want to replace answer with a better name\n'

    def doWait(self, level, block, deferYield=False):
        """Generate a wait call."""
        assert block.getOpcode() == "control_wait"
        # inputs: "DURATION": [ 1,  [  5,  "1" ] ]
        return genIndent(level) + "wait(s, " + self.mathExpr(block, 'DURATION') + ");\n"

    def doRepeat(self, level, block, deferYield=False):
        """Generate a repeat <n> times loop.
        """
        retStr = genIndent(level) + "for (int i" + str(level) + " = 0; i" + str(level) + " < " + \
                 self.mathExpr(block, 'TIMES') + "; i" + str(level) + "++)\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.statements(level, block.getChild('SUBSTACK'))
        if deferYield:
            retStr += genIndent(level + 1) + \
                      "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                      "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"

    def doWaitUntil(self, level, block, deferYield=False):
        """Generate doWaitUtil code: in java we'll do this:
           while (true) {
               if (condition)
                   break;
               yield(s);
           }
        """
        condition = self.boolExpr(block.getChild('CONDITION'))
        retStr = genIndent(level) + "// wait until code\n"
        retStr += genIndent(level) + "while (true) {\n"
        retStr += genIndent(level + 1) + "if (" + condition + ")\n"
        retStr += genIndent(level + 2) + "break;\n"
        retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"

    def repeatUntil(self, level, block, deferYield=False):
        """Generate doUntil code, which translates to this:
           while (! condition)
           {
               statements
               yield(s);
           }
        """
        condition = self.boolExpr(block.getChild('CONDITION'))
        retStr = genIndent(level) + "// repeat until code\n"
        retStr += genIndent(level) + "while (! " + condition + ")\n"
        retStr += genIndent(level) + "{\n"
        retStr += self.statements(level, block.getChild('SUBSTACK'))
        if deferYield:
            retStr += genIndent(level + 1) + \
                      "deferredYield(s);   // allow other sequences to run occasionally\n"
        else:
            retStr += genIndent(level + 1) + \
                      "yield(s);   // allow other sequences to run\n"
        return retStr + genIndent(level) + "}\n"

    def stopScripts(self, level, block, deferYield=False):
        """Generate code to stop scripts: all, other, etc.
        """
        option = block.getField('STOP_OPTION')
        if option == "all":
            return genIndent(level) + "stopAll();\n"
        elif option == "this script":
            return genIndent(level) + "stopThisScript();\n"
        elif option == "other scripts in sprite":
            return genIndent(level) + "stopOtherScriptsInSprite();\n"
        else:
            raise ValueError("stopScripts: unknown option", option)

    def createCloneOf(self, level, block, deferYield=False):
        """Create a clone of the sprite itself or of the given sprite.
        """
        child = block.getChild('CLONE_OPTION')
        argVal = child.getField('CLONE_OPTION')
        if argVal == "_myself_":
            return genIndent(level) + "createCloneOfMyself();\n"
        else:
            return genIndent(level) + 'createCloneOf("' + argVal + '");\n'

    def deleteThisClone(self, level, block, deferYield=False):
        """Delete this sprite.
        """
        return genIndent(level) + "deleteThisClone();\n"

    def resetTimer(self, level, block, deferYield=False):
        return genIndent(level) + "resetTimer();\n"

    def genProcDefCode(self, codeObj, topBlock):
        """Generate code for a custom block definition in Scratch.
        All the generated code goes into codeObj's cbCode since it doesn't
        belong in the constructor.
        """

        # topBlock has a child, 'procedures_prototype', that has the info like this:
        #   "inputs": {
        #     "W4-$x?M#(z-O;zL#JGtD": [ 1, ";wRdEi9dvXIeYHWSe]qY" ],
        #     "8DW5FO+wpV?B_E07*Gd{": [ 2, ".ksStxZtV=A6)v.2F=5b" ],
        #     "]lPKh6+rN{|NDMR,K|)t": [ 2, "V%Lqx`q;;-4(US)kpqpo" ]
        #   },
        #   "mutation": {
        #     "proccode": "turnamount %s %b degrees %s",
        #     "argumentids": "[\"W4-$x?M#(z-O;zL#JGtD\",\"8DW5FO+wpV?B_E07*Gd{\",\"]lPKh6+rN{|NDMR,K|)t\"]",
        #     "argumentnames": "[\"number\",\"boolean\",\"number or text\"]",
        #     "argumentdefaults": "[\"\",\"false\",\"\"]",
        #     "warp": "false"
        #   }

        block = topBlock.getChild('custom_block')

        # funcname and param types: e.g., block3args %s %s %b
        (funcname, paramTypes) = self.extractInfoFromProcCode(block)

        # convert all names to legal java ids.
        paramNames = list(map(convertToJavaId, block.getProcDefnParamNames()))

        assert len(paramTypes) == len(paramNames)

        if len(paramTypes) == 0:
            codeObj.addToCbCode(genIndent(1) + "private void " + funcname + "(Sequence s")
        else:
            codeObj.addToCbCode(genIndent(1) + "private void " + funcname + "(Sequence s, ")

        for i in range(len(paramTypes)):
            if paramTypes[i] == 'stringOrNumber':
                t = 'String'  # Assuming everything is a string now... nasty.
            else:
                t = 'boolean'
            codeObj.addToCbCode(t + " " + paramNames[i])
            # Add following ", " if not add end of list.
            if i < len(paramTypes) - 1:
                codeObj.addToCbCode(", ")

        codeObj.addToCbCode(")\n")
        codeObj.addToCbCode(self.block(1, topBlock.getNext()))
        codeObj.addToCbCode("\n")  # add blank line after function defn.
        return codeObj

    def extractInfoFromProcCode(self, block):
        """extract the function to call and list of argument types from
        the proccode string.  return tuple: (funcname, listOfArgType),
        where arg types are 'stringOrNumber', 'boolean'
        """

        # proccode is a string like this: nameOfFunc %s %b someword %s
        # We could parse this to get some type info from it, although numbers and strings
        # are always %s.

        argsList = []

        proccode = block.getProcCode()
        firstPercent = proccode.find("%")
        if firstPercent == -1:
            # No percent sign, so no parameters.
            return proccode.strip(), argsList

        func2Call = proccode[0:firstPercent].strip()  # remove trailing blanks.

        proccode = proccode[firstPercent:]  # remove func2call name

        # split on spaces to get each word.
        paramsEtc = proccode.split()
        for param in paramsEtc:
            if param[0] == '%':
                # we have a param
                if param[1] == 's' or param[1] == 'n':  # only s will be seen (now)
                    argsList.append('stringOrNumber')
                elif param[1] == 'b':
                    argsList.append('boolean')
                else:
                    raise ValueError('unknown specifier in args list')
            # else do nothing: it is a string in the middle of the args list and we'll
            # ignore those (for now)
        return func2Call, argsList

    def callABlock(self, level, block, deferYield=False):
        """Generate a call to a custom-defined block.
        inputs in the block look like this:
        "inputs": {
            "W4-$x?M#(z-O;zL#JGtD": [
              1,
              [
                10,
                "3"         <-- value to pass 
              ]
            ],
            "8DW5FO+wpV?B_E07*Gd{": [
              2,
              "?i(/2Z~tf~8@O=8#khV1"        <-- blockid to be evaluated to a value
            ]
          },
        Also, there is a "mutation" block:
        {
            "tagName": "mutation",
            "children": [],
            "proccode": "turnamount %s %b",
            "argumentids": "[\"W4-$x?M#(z-O;zL#JGtD\",\"8DW5FO+wpV?B_E07*Gd{\"]",
            "warp": "false"
        }
        The name of the function to call is only found in the proccode, afaict.
        It is (perhaps) impossible to tell if an argument is supposed to be a 
        string or a number.  So, we'll try to evaluate as a number, and if that
        fails, try strExpr, and if that fails, boolean expression.
        """

        (func2Call, argTypes) = self.extractInfoFromProcCode(block)
        func2Call = convertToJavaId(func2Call)

        if len(argTypes) == 0:
            return genIndent(level) + func2Call + "(s);\n"

        resStr = genIndent(level) + func2Call + "(s, "

        # Determine order of the arguments.  This comes from the "argumentids" in the
        # mutation block.  It is a jsonified list of blockIds.... E.g.,
        # "argumentids": "[\"W4-$x?M#(z-O;zL#JGtD\",\"8DW5FO+wpV?B_E07*Gd{\",\"]lPKh6+rN{|NDMR,K|)t\"]",
        argIdList = block.getProcCallArgIds()

        # each argId is in inputs.
        resStrs = []
        for argIdx in range(len(argIdList)):  # skip last one.
            argId = argIdList[argIdx]
            if argTypes[argIdx] == 'stringOrNumber':
                try:
                    resStrs.append(self.mathExpr(block, argId))
                except:
                    resStrs.append(self.strExpr(block, argId))
            else:  # boolean
                boolExprBlock = block.getChild(argId)
                resStrs.append(self.boolExpr(boolExprBlock))

        resStr += ', '.join(resStrs) + ');\n'
        return resStr

    def playSound(self, level, block, deferYield=False):
        """ Play the given sound
        """
        return genIndent(level) + 'playSound("' + self.mathExpr(block, 'SOUND_MENU') + '");\n'

    def playSoundUntilDone(self, level, block, deferYield=False):
        """ Play the given sound without interrupting it.
        """
        return genIndent(level) + 'playSoundUntilDone("' + self.mathExpr(block, 'SOUND_MENU') + '");\n'

    def playNote(self, level, block, deferYield=False):
        """ Play the given note for a given number of beats
        """
        return genIndent(level) + "playNote(s, " + self.mathExpr(block, 'NOTE') + ", " + \
               self.mathExpr(block, 'BEATS') + ");\n"

    def instrument(self, level, block, deferYield=False):
        """ Play the given instrument
        """
        return genIndent(level) + "changeInstrument(" + self.mathExpr(block, 'INSTRUMENT') + ");\n"

    def playDrum(self, level, block, deferYield=False):
        """ Play the given drum
        """
        return genIndent(level) + "playDrum(s, " + self.mathExpr(block, 'DRUM') + ", " + \
               self.mathExpr(block, 'BEATS') + ");\n"

    def rest(self, level, block, deferYield=False):
        """ Play a rest for the given number of beats.
        """
        return genIndent(level) + "rest(s, " + self.mathExpr(block, 'BEATS') + ");\n"

    def changeTempoBy(self, level, block, deferYield=False):
        """ Change the tempo.
        """
        return genIndent(level) + "changeTempoBy(" + self.mathExpr(block, 'TEMPO') + ");\n"

    def setTempoTo(self, level, block, deferYield=False):
        """ Set the tempo
        """
        return genIndent(level) + "setTempo(" + self.mathExpr(block, 'TEMPO') + ");\n"

    # ----------------------------------------------------------

    def resolveName(self, name):
        """Ask the user what each variable should be named if it is not a
        legal identifier
        """
        while True:
            try:
                print("\"" + name + "\" is not a valid java variable name.")
                n = input("Java variables must start with a letter and contain only letters and numbers.\n" + \
                          "Enter a new name, or type nothing to use \"" + convertToJavaId(name) + "\"\n> ")
                if n == "":
                    return convertToJavaId(name)
                name = n
                if convertToJavaId(n) == n:
                    return n
            except IndexError:
                # The variable name has no valid characters
                print("\"" + name + "\" must have some alphanumeric character in order to suggest a name")
                name = "variable:" + name

    def genScriptCode(self, topBlock):
        """Generate code (and callback code) for the given topBlock, which may be
        associated with either a sprite or the main stage.
        """

        codeObj = CodeAndCb()  # Holds all the code that is generated.

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
        elif opcode == 'procedures_definition':
            self.genProcDefCode(codeObj, topBlock)
        elif isinstance(topBlock, list) and topBlock[0] == 'whenSceneStarts':
            self.whenSwitchToBackdrop(codeObj, topBlock[1], blocks[1:])

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
    """This class represents a Sprite for code generation."""

    def __init__(self, sprData):

        # Handle sprites with names that are illegal Java identifiers.
        # E.g., the sprite could be called "1", but we cannot create a "class 1".
        name = convertToJavaId(sprData['name'], True, True)

        super().__init__(name, sprData)

    def setVariableIsLocalOrGlobal(self, var):
        """All variables defined in a sprite are local"""
        var.setLocal()

    def genVarDefnCode(self, level, var):
        return genIndent(level) + '%sVar %s;\n' % (var.getType(), var.getGfName())

    def genListDefnCode(self, level, var):
        return genIndent(level) + 'ScratchList %s;\n' % var.getGfName()

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
        cbStr += self.topBlock(1, block) + "\n"  # add blank line after defn.
        codeObj.addToCbCode(cbStr)


class Stage(SpriteOrStage):
    """This class represents the Stage class."""

    def __init__(self, sprData):
        super().__init__("Stage", sprData)

        self._bgCode = ""

    def setVariableIsLocalOrGlobal(self, var):
        """All stage variables are global."""
        var.setGlobal()

    def genVarDefnCode(self, level, var):
        return genIndent(level) + 'static %sVar %s;\n' % (var.getType(), var.getGfName())

    def genListDefnCode(self, level, var):
        return genIndent(level) + 'static ScratchList %s;\n' % var.getGfName()

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
    global onlyDecode

    # Make a directory into which to unzip the scratch zip file.
    scratch_dir = os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR)

    if not onlyDecode:
        print("------------ Processing " + SCRATCH_FILE + ' ---------------\n')

        if not os.path.exists(SCRATCH_FILE):
            print("Scratch download file " + SCRATCH_FILE + " not found.")
            sys.exit(1)
        if not os.path.exists(PROJECT_DIR):
            if useGui:
                if (
                        tkinter.messagebox.askokcancel("Make New Directory",
                                                       "Greenfoot directory not found, generate it?")):
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

        try:
            os.mkdir(scratch_dir)
        except FileExistsError as e:
            pass  # If the directory exists already, no problem.

        # Unzip the .sb3 file into the project/scratch_code directory.
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
            size = res[1].split()[2]  # got the geometry.
            width, height = size.split("x")  # got the width and height, as strings
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
    with open(os.path.join(scratch_dir, "project.json"), encoding="utf_8") as data_file:
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

    stage.genVariablesDefnCode(stageData['variables'], stageData['lists'], data['targets'], cloudVars)

    # Code to be written into the World.java file.
    worldCtorCode = ""

    # ---------------------------------------------------------------------------
    # Start processing each sprite's info: scripts, costumes, variables, etc.
    # ---------------------------------------------------------------------------
    for sprData in spritesData:
        if sprData['isStage']:
            continue  # skip the stage for now.

        sprite = Sprite(sprData)

        # Copy the sounds associated with this sprite to the appropriate directory
        sprite.copySounds(soundsDir)

        # Generate world construct code that adds the sprite to the world.
        sprite.genAddSpriteCall()
        sprite.genLoadCostumesCode(sprData['costumes'])
        # Like location, direction, shown or hidden, etc.
        sprite.genInitSettingsCode()

        # Handle variables defined for this sprite.  This has to be done
        # before handling the scripts, as the scripts may refer to the
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
        SCRATCH_FILE = tkinter.filedialog.askopenfilename(initialdir=SCRATCH_FILE,
                                                          filetypes=[('Scratch3 files', '.sb3'),
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
    entryFrame.pack(side=tkinter.TOP)
    scratchFrame = tkinter.Frame(entryFrame)
    scratchFrame.pack(side=tkinter.LEFT)
    scratchLabel = tkinter.Label(scratchFrame, text="Scratch File")
    scratchLabel.pack(side=tkinter.TOP)
    scrEntryVar = tkinter.StringVar()
    scrEntryVar.set(SCRATCH_FILE)
    scratchEntry = tkinter.Entry(scratchFrame, textvariable=scrEntryVar, width=len(SCRATCH_FILE))
    scratchEntry.pack(side=tkinter.TOP)
    tkinter.Button(scratchFrame, text="Find file", command=findScratchFile).pack(side=tkinter.TOP)

    gfFrame = tkinter.Frame(entryFrame)
    gfFrame.pack(side=tkinter.RIGHT)
    gfLabel = tkinter.Label(gfFrame, text="Greenfoot Project Directory")
    gfLabel.pack(side=tkinter.TOP)
    gfEntryVar = tkinter.StringVar()
    gfEntryVar.set(PROJECT_DIR)
    gfEntry = tkinter.Entry(gfFrame, textvariable=gfEntryVar, width=len(PROJECT_DIR))
    gfEntry.pack(side=tkinter.TOP)
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


    convertButton = tkinter.Button(root, text="Convert", command=convertButtonCb)
    convertButton.pack(side=tkinter.BOTTOM)
    root.mainloop()
