###############################################################################################
###                                                                                         ###
###    ####   ####  #####      ##    ######   ####  ##  ##   #####   ####    ####   ######  ###
###   ##     ##     ##  ##    ####     ##    ##     ##  ##   ##     ##  ##  ##  ##    ##    ###
###   #####  ##     #####    ##  ##    ##    ##     ######   ####   ##  ##  ##  ##    ##    ###
###      ##  ##     ## ##    ######    ##    ##     ##  ##   ##     ##  ##  ##  ##    ##    ###
###   ####    ####  ##  ##  ##    ##   ##     ####  ##  ##   ##      ####    ####     ##    ###
###                                                                                         ###
###                                   #################                                     ###
##################################### ## AST Version ## #######################################
###                                   #################                                     ###
### Legal Information:                                                                      ###
###                                                                                         ###
### Copyright (C) 2016  Victor T. Norman, Calvin College, Grand Rapids, MI, USA             ###
###                                                                                         ###
### ScratchFoot: a Scratch emulation layer for Greenfoot, along with a program              ###
### to convert a Scratch project to a Greenfoot scenario.                                   ###
###                                                                                         ###
### This program is free software: you can redistribute it and/or modify                    ###
### it under the terms of the GNU General Public License as published by                    ###
### the Free Software Foundation, either version 3 of the License, or                       ###
### (at your option) any later version.                                                     ###
###                                                                                         ###
### This program is distributed in the hope that it will be useful,                         ###
### but WITHOUT ANY WARRANTY; without even the implied warranty of                          ###
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                           ###
### GNU General Public License for more details.                                            ###
###                                                                                         ###
### You should have received a copy of the GNU General Public License                       ###
### along with this program.  If not, see <http://www.gnu.org/licenses/>                    ###
###                                                                                         ###
###############################################################################################
### TODO LIST:                                                                              ###
### Fix various inline TODOs                                                                ###
### Get varaibles/lists working- Intermediate step between generation and construction      ###
### Get graphics effects/math functions working - Just check what token it is and generate  ### < and any other blocks I forgot
###     the appropriate object. May also need to implement object in some cases.            ###
### Finish moving generator assignment code out of constructor and into factory method      ###
### Separate variable renaming into a new step, and improve it using AST                    ###
### Move all 'construct()' code into '__init__()', and get rid of construct() everywhere    ###
### Copy from s2g the code to move sounds, images, etc.                                     ###
### Write to project.greenfoot. This can be copied from s2g and pasted in the right spots   ### < the stuff with projectFileCode
### Level argument determines how many spaces to add before a line, but could be cleaned up ### < This Refers to genCode(level...)
###     Whether level is the current tab level, or the children's tab level is inconsistent ###
### If a string literal is the same as a sprite's name, switch it to the Java id instead    ### < 'sprite 1' to 'Sprite1'
### Currently more parenthesis are used than necessary. This should be reduced              ### < turnR((1 + 1)); to turnR(1 + 1);
###     Be careful! Some parenthesis are necessary so things don't happen out of order!     ### < 1 / (2 + 1) NOT 
###############################################################################################
### Information:                                                                            ###
### The Abstract Syntax Tree consists of objects, each of which represents a scratch block  ###
### Each object, when constructed, constructs any objects that it depends on                ###
### The objects are created through factory methods, such as createBlock()                  ###
### The root of the tree is the Stage object, while blocks with no arguments are the leaves ###
### Each object has a generator object, passed to the constructor, which generates its code ###
### Each object will call genCode on its children, which should return a string, for each   ###
### These strings are passed into the generator, through the generator.genCode() method     ###
### The generator will then return a string combining the operands with its code template   ###
### These strings eventually combine to form full class files, which can be written to file ###
### The result is a dictionary with file names as keys and file contents as values          ###
###                                                                                         ###
### All Java specific code should be kept in Java generator classes, not scratch objects    ###
### To add support of a language other than Java, create new generators and factories       ###
### The stage/sprites have a Variables dictionary, which maps to unsanitized names to vars  ###
### These Variable objects store sanitized names, values, types etc.                        ###
### The same should be done for Lists, user-defined blocks (the purple ones)                ###
### All of these should go through the GUI renamer first, which currently only does vars    ### < Even sprite names, potentially
### The construct() methods shouldn't exist. For some reason I forgot what a constructor    ###
###     was for. Code should be moved to the constructor and the method removed             ###
###############################################################################################

import abc
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
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox


# Global Variables that can be set via command-line arguments.
debug = False
inference = False
name_resolution = False
useGui= True;

# Indentation level in outputted code.
TAB_SIZE = 4
TAB = " " * TAB_SIZE

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
parser.add_argument("--scratch_file", help="Location of scratch sb2 file", default = os.getcwd(), required=False)
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

# Initialize stage globally
stage = None



class CodeGenerator():
    """ This serves as the base class for all code generating objects
    Any subclasses should implement a genCode(self, oplist, level),
    which should return the code based on the outstring and ops
    """
    def __init__(self):
        self.output = ''
        self.opCount = 0
    def genCode(self, opList, level):
        print(str(opList) + " " + str(self.opCount) + " -" + self.output)
        assert len(opList) == self.opCount
        return TAB * level + (self.output % tuple(opList))

class JavaGenerator(CodeGenerator):
    JAVA_KEYWORDS = ('abstract', 'continue', 'for', 'new', 'switch', 'assert', 'default', 'goto',\
                 'package', 'synchronized', 'boolean', 'do', 'if', 'private', 'this', 'break',\
                 'double', 'implements', 'protected', 'throw', 'byte', 'else', 'import', 'public',\
                 'throws', 'case', 'enum', 'instanceof', 'return', 'transient', 'catch', 'extends',\
                 'int', 'short', 'try', 'char', 'final', 'interface', 'static', 'void', 'class', 'finally',\
                 'long', 'strictfp', 'volatile', 'const', 'float', 'native', 'super', 'while')
    def __init__(self):
        super().__init__()

class JavaStatementGenerator(JavaGenerator):
    """ This generator is used to generate code that takes up one line
    such as function calls
    """
    def __init__(self, outString, opCount):
        self.output = outString
        self.opCount = opCount
        
class JavaInlineGenerator(JavaGenerator):
    """ This generator is used to generate code within another statement
    such as arguments to functions
    """
    def __init__(self, outString, opCount):
        self.output = outString
        self.opCount = opCount
    def genCode(self, opList, level):
        print(str(opList) + " " + str(self.opCount))
        assert len(opList) == self.opCount
        print("codeGenerator operating: " + str(opList) + " on " + self.output)
        return self.output % tuple(opList)
    
class JavaBlockGenerator(JavaGenerator):
    """ This generator is used to generate code which will take up multiple lines
    such as scripts and loops
    """
    def __init__(self, prefix, postfix, opCount): 
        self.opCount = opCount
        self.output = prefix
        self.postfix = postfix
    def genCode(self, opList, level):
        print("Generating Block: " + self.output)
        
        spacing = TAB * (level + 1) # Why is this level + 1, while lowerSpacing is level - 1?
                                    # Probably something in the way statements are handled TODO: fix
        output = self.output % tuple(opList[:self.opCount])
        output = spacing + output
        s = ''
        for line in opList[self.opCount:]:
            #print(str(line))
            s += line
        
        lowerSpacing = TAB * (level - 1) # level of closing '}'
        for line in self.postfix:
            s += spacing + line
        
        return output + s
        

class JavaLiteralGenerator(JavaGenerator):
    """ This generator is used to generate literal values
    """
    def __init__(self, value, type):
        self.type = type
        self.value = value
    def genCode(self, opList, level):
        if self.type == 'int':
            return self.value
        if self.type == 'double':
            return self.value
        if self.type == 'str':
            return '"' + self.value + '"'

    
class Expression:
    """Abstract base class"""
    
    def __init__(self, tokens, generator):
        self.tokens = tokens;
        self.ops = []
        self.generator = generator
    
    def construct(self):
        """The construct method is a vestige of poor decision making on my part.
        This method is simply to maintain compatibilty, though the method and all
        references to it should be removed in favor of the constructor
        """
        return self
    
    @staticmethod
    def constructBlocklist(scripts):
        blockList = []
        for script in scripts:
            print("Constructing block: " + str(script))
            blockList.append(Block.createBlock(script).construct())
        return blockList
    
    def genCode(self, level):
        opstrings = []
        #print(str(self.ops))
        for op in self.ops:
            print("Ops of %s: %s" % (type(self), str(self.ops)))
            opstrings.append(op.genCode(level + 1))
        print("Expression Generating Code: " + str(type(self)) + "\n\t" + str(self.ops))
        return self.generator.genCode(opstrings, level + 1)
    
        
    

class Reporter(Expression):
    """A block that outputs a value. (Reporter block)"""
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)


    @staticmethod
    def createDoubleReporter(tokens):
        if isinstance(tokens, str) or isinstance(tokens, int) or isinstance(tokens, float):
            try:
                print("Constructing literal double block")
                return Literal(tokens, 'double', JavaLiteralGenerator(tokens, 'double'))
            except ValueError:
                raise ValueError("Non-double literal in DoubleReporter")
        op = tokens[0]
        if op == "xpos":
            return GetX(tokens, JavaInlineGenerator('getX()', 0))
        elif op == "ypos":
            return GetY(tokens, JavaInlineGenerator('getY()', 0))
        elif op == "heading":
            return Direction(tokens, JavaInlineGenerator('getDirection()', 0))
        if op == 'readVariable':
            return ReadVar(tokens, 'double')
        elif op == "timestamp":
            return Timestamp(tokens)
        elif op == "distanceTo:":
            return Distance(tokens, JavaInlineGenerator('distanceTo(%s)', 1))
        elif op == "computeFunction:of:":
            return MathFunction(tokens)
        elif op == "getTimeAndDate":
            return CurrentTime(tokens)
        if op == '+':
            return Plus(tokens, JavaInlineGenerator("(%s + %s)", 2))
        elif op == '-':
            return Minus(tokens, JavaInlineGenerator("(%s - %s)", 2))
        elif op == '*':
            return Times(tokens, JavaInlineGenerator("(%s * %s)", 2))
        elif op == '\\/':
            return Divide(tokens, JavaInlineGenerator("(%s / %s)", 2))
        else:
            raise ValueError("not valid double reporter")
    
    @staticmethod
    def createIntReporter(tokens):
        if isinstance(tokens, str):
            try:
                print("Constructing literal int block")
                return Literal(tokens, 'int', JavaLiteralGenerator(tokens, 'int'))
            except ValueError:
                raise ValueError("Non-int literal in IntReporter")
        op = tokens[0]
        if op == "costumeIndex":    # Looks menu's costume # block
            return CostumeNumber(tokens, JavaInlineGenerator('costumeNumber()', 0))
        if op == 'readVariable':
            return ReadVar(tokens, 'int')
        elif op == 'backgroundIndex':
            return BackdropNumber(tokens, JavaInlineGenerator('backdropNumber()', 0))
        elif op == "mouseX":
            return MouseX(tokens, JavaInlineGenerator('getMouseX()', 0))
        elif op == "mouseY":
            return MouseY(tokens, JavaInlineGenerator('getMouseY()', 0))
        elif op == "scale":         # Look menu's size block
            return Size(tokens, JavaInlineGenerator('size()', 0))
        elif op == 'rounded':
            return Round(tokens, JavaInlineGenerator('round(%s)', 1))
        elif op == "stringLength:":
            return StringLength(tokens, JavaInlineGenerator('lengthOf(%s)', 1))
        elif op == '%':
            return Mod(tokens, JavaInlineGenerator('%s \% %s', 2))
        else:
            raise ValueError("not valid int reporter")
    
    @staticmethod
    def createStringReporter(tokens):
        print('Creating String reporter')
        if isinstance(tokens, str):
            print('Creating String Literal reporter')
            return Literal(tokens, 'str', JavaLiteralGenerator(tokens, 'str'))
        op = tokens[0]
        if op == "sceneName":
            return BackdropName(tokens, JavaInlineGenerator('backdropName', 0))
        if op == 'readVariable':
            return ReadVar(tokens, 'string')
        if op == 'letter:of:':
            return LetterOf(tokens)
        if op == 'concatenate:with:':
            return Concat(tokens)
        else:
            print('Invalid: ' + str(tokens))
            raise ValueError("not valid string reporter")
    
    @staticmethod
    def createBooleanReporter(tokens):
        print(str(tokens))
        op = tokens[0]
        if op == '<':
            return Lt(tokens, JavaInlineGenerator('(%s < %s)', 2))
        elif op == '=':
            return Eq(tokens, JavaInlineGenerator('(%s = %s)', 2))
        elif op == '>':
            return Gt(tokens, JavaInlineGenerator('(%s > %s)', 2))
        elif op == '&':
            return And(tokens, JavaInlineGenerator('(%s && %s)', 2))
        elif op == '|':
            return Or(tokens, JavaInlineGenerator('(%s || %s)', 2))
        elif op == 'not':
            return Not(tokens, JavaInlineGenerator('!(%s)', 1))
        elif op == 'touching:':
            return Touching(tokens)
        elif op == 'touchingColor:':
            return TouchingColor(tokens)
        elif op == 'keyPressed:':
            return KeyPressed(tokens)
        elif op == 'mousePressed':
            return MousePressed(tokens)
        else:
            print('Undefined boolean:' + op)
            raise ValueError("not valid boolean reporter")

    @staticmethod
    def createReporter(tokens, type):
        rep = None
        print("Creating Reporter")
        if type == 'Int':
            print("Creating Int")
            try:
                rep = Reporter.createIntReporter(tokens)
            except ValueError:
                try:
                    rep = Reporter.createDoubleReporter(tokens)
                except ValueError:
                    rep = Reporter.createStringReporter(tokens)
        elif type == 'Double':
            print("Creating Double")
            try:
                rep = Reporter.createDoubleReporter(tokens)
            except ValueError:
                try:
                    rep = Reporter.createIntReporter(tokens)
                except ValueError:
                    rep = Reporter.createStringReporter(tokens)
        else:
            print("Creating String")
            rep = Reporter.createStringReporter(tokens)
        print("Done Creating reporter")
        return rep.construct()
    
        
        

class DoubleReporter(Reporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class IntReporter(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class StringReporter(Reporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class Plus(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        print("Constructing plus block")
        
        return self
class Minus(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
        self.generator = generator
    def construct(self):
        
        return self
class Times(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Divide(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class RandomD(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class RandomI(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Concat(StringReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "String"))
    def construct(self):
        
        return self
class LetterOf(StringReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class StringLength(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class Mod(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Int"))
    def construct(self):
        
        return self
class Round(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class MathFunction(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
##Todo: add java code
    
#### Add remaining math functions       
####
class Answer(StringReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
    ##Todo: add java code
class Volume(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
    ##Todo: add java code implemented in scratch.java
class Timer(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class Timestamp(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class CurrentTime(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
#### Add Other time blocks
####
class ReadVar(Reporter):
    def __init__(self, tokens, type):
        super().__init__(tokens)
    def construct(self):
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.generator = JavaInlineGenerator("/*unimplemented*/", 1)#TODO: var code
        return self
class Tempo(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class CostumeNumber(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class BackdropName(StringReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class BackdropNumber(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class Size(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class GetX(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class GetY(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class Direction(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class Distance(DoubleReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class MouseX(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class MouseY(IntReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)


class BooleanReporter(Reporter):
    """A reporter for boolean values. (Boolean block)"""
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)

class Lt(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Gt(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Eq(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class And(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createBooleanReporter(self.tokens[1]))
        self.ops.append(Reporter.createBooleanReporter(self.tokens[2]))
    def construct(self):
        
        return self
class Or(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createBooleanReporter(self.tokens[1]))
        self.ops.append(Reporter.createBooleanReporter(self.tokens[2]))
    def construct(self):
        
        return self
class Not(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createBooleanReporter(self.tokens[1]))
    def construct(self):
        
        return self
class Touching(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class TouchingColor(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class KeyPressed(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class MousePressed(BooleanReporter):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)

class Block(Expression):
    """A standard block. (Stack block)"""
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
    
    @staticmethod
    def createBlock(tokens):
        blockList = {
            'doIf': Block.doIf,
            'doIfElse': Block.doIfElse,
    
            # Motion commands
            'forward:': Block.motion1Arg,
            'turnLeft:': Block.motion1Arg,
            'turnRight:': Block.motion1Arg,
            'heading:': Block.motion1Arg,
            'gotoX:y:': Block.gotoXY,
            'gotoSpriteOrMouse:': Block.motion1Arg,
            'changeXposBy:': Block.motion1Arg,
            'xpos:': Block.motion1Arg,
            'changeYposBy:': Block.motion1Arg,
            'ypos:': Block.motion1Arg,
            'bounceOffEdge': Block.bounce,
            'setRotationStyle': Block.motion1Arg,
            'pointTowards:': Block.pointToward,
            'glideSecs:toX:y:elapsed:from:': Block.glideTo,
    
            # Looks commands
            'say:duration:elapsed:from:': Block.sayForSecs,
            'say:': Block.say,
            'think:duration:elapsed:from:':Block.thinkForSecs,
            'think:': Block.think,
            'show': Block.show,
            'hide': Block.hide,
            'lookLike:': Block.switchCostumeTo,
            'nextCostume': Block.nextCostume,
            'startScene': Block.switchBackdropTo,
            'changeSizeBy:': Block.changeSizeBy,
            'setSizeTo:': Block.setSizeTo,
            'comeToFront': Block.goToFront,
            'goBackByLayers:': Block.goBackNLayers,
            'nextScene': Block.nextBackdrop,
            'changeGraphicEffect:by:': Block.changeGraphicBy,
            'setGraphicEffect:to:': Block.setGraphicTo,
    
            # Pen commands
            'clearPenTrails': Block.pen0Arg,
            'stampCostume': Block.pen0Arg,
            'putPenDown': Block.pen0Arg,
            'putPenUp': Block.pen0Arg,
            'penColor:': Block.pen1Arg,
            'changePenHueBy:': Block.pen1Arg,
            'setPenHueTo:': Block.pen1Arg,
            'penSize:': Block.pen1Arg,
            'changePenSizeBy:': Block.pen1Arg,
    
            # Data commands
            'setVar:to:': Block.setVariable,
            'hideVariable:': Block.hideVariable,
            'showVariable:': Block.showVariable,
            'changeVar:by:': Block.changeVarBy,
            
            'append:toList:': Block.listAppend,
            'deleteLine:ofList:': Block.listRemove,
            'insert:at:ofList:': Block.listInsert,
            'setLine:ofList:to:': Block.listSet,
            'hideList:': Block.hideList,
            'showList:': Block.showList, 
    
            # Events commands
            'broadcast:': Block.broadcast,
            'doBroadcastAndWait': Block.broadcastAndWait,
    
            # Control commands
            'doForever': Block.doForever,
            'wait:elapsed:from:': Block.doWait,
            'doRepeat': Block.doRepeat,
            'doWaitUntil': Block.doWaitUntil,
            'doUntil': Block.doRepeatUntil,
            'stopScripts': Block.stopScripts,
            'createCloneOf': Block.createCloneOf,
            'deleteClone': Block.deleteThisClone,
    
            # Sensing commands
            'doAsk': Block.doAsk,
            'timerReset': Block.resetTimer,
    
            # Blocks commands
            'call': Block.callABlock,
            
            # Sound commands
            'playSound:': Block.playSound,
            'doPlaySoundAndWait': Block.playSoundUntilDone,
            
            #Midi commands
            'noteOn:duration:elapsed:from:': Block.noteOn,
            'instrument:': Block.instrument,
            'playDrum': Block.playDrum,
            'rest:elapsed:from:': Block.rest,
            'changeTempoBy:': Block.changeTempoBy,
            'setTempoTo:': Block.setTempoTo
            }
        cmd = tokens[0]
        if cmd in blockList:
            print("creating block: " + cmd)
            return blockList[cmd](tokens)
        else:
            raise ValueError("No block: " + cmd)
    
    @staticmethod
    def doIf(tokens):
        return If(tokens, JavaBlockGenerator('if (%s) {\n', ('}\n'), 1))
    @staticmethod
    def doIfElse(tokens):
        return IfElse(tokens, JavaIfElseGenerator())
    #### MOTION
    @staticmethod
    def motion1Arg(tokens):
        assert len(tokens) == 2
        cmd, arg = tokens
        if cmd == "forward:":
            return Move(tokens, JavaStatementGenerator("move(%s);\n", 1))
        elif cmd == "turnRight:":
            return TurnR(tokens, JavaStatementGenerator("turnR(%s);\n", 1))
        elif cmd == "turnLeft:":
            return TurnL(tokens, JavaStatementGenerator("turnL(%s);\n", 1))
        elif cmd == "heading:":
            return PointDir(tokens, JavaStatementGenerator("pointInDirection(%s);\n", 1))
        elif cmd == "gotoSpriteOrMouse:":
            if arg == "_mouse_":
                return GoToMouse(tokens, JavaStatementGenerator("goToMouse();\n", 0))
            elif arg == "_random_":
                return GoToRandom(tokens, JavaStatementGenerator("goToRandom();\n", 1))
            else:
                return GoToSprite(tokens, JavaStatementGenerator("goTo(%s);\n", 1))
        elif cmd == "changeXposBy:":
            return ChangeX(tokens, JavaStatementGenerator("changeXBy(%s);\n", 1))
        elif cmd == "xpos:":
            return SetX(tokens, JavaStatementGenerator("setXTo(%s);\n", 1))
        elif cmd == "changeYposBy:":
            return ChangeY(tokens, JavaStatementGenerator("changeYBy(%s);\n", 1))
        elif cmd == "ypos:":
            return SetY(tokens, JavaStatementGenerator("setYTo(%s);\n", 1))
        elif cmd == "setRotationStyle":
            return RotationStyle(tokens, JavaStatementGenerator("setRotationStyle(%s);\n", 1))
        else:
            raise ValueError(cmd)
    @staticmethod
    def gotoXY(tokens):
        return GoTo(tokens, JavaStatementGenerator("goTo(%s, %s);\n", 2))
    @staticmethod
    def bounce(tokens):
        return Bounce(tokens, JavaStatementGenerator("ifOnEdgeBounce();\n", 1))
    @staticmethod
    def pointToward(tokens):
        return PointAt(tokens, JavaStatementGenerator("pointToward(%s);\n", 1))
    @staticmethod
    def glideTo(tokens):
        return GlideTo(tokens, JavaStatementGenerator("glideTo(%s, %s);\n", 2))
    #### LOOKS
    @staticmethod
    def say(tokens):
        return Say(tokens, JavaStatementGenerator("say(%s);\n", 1))
    @staticmethod
    def sayForSecs(tokens):
        return SayFor(tokens, JavaStatementGenerator("sayForNSeconds(%s, %s);\n", 2))
    @staticmethod
    def think(tokens):
        return Think(tokens, JavaStatementGenerator("think(%s, %s);\n", 1))
    @staticmethod
    def thinkForSecs(tokens):
        return ThinkFor(tokens, JavaStatementGenerator("thinkForNSeconds(%s, %s);\n", 1))
    @staticmethod
    def show(tokens):
        return Show(tokens, JavaStatementGenerator("show();\n", 1))
    @staticmethod
    def hide(tokens):
        return Hide(tokens, JavaStatementGenerator("hide();\n", 1))
    @staticmethod
    def switchCostumeTo(tokens):
        return SwitchCostume(tokens, JavaStatementGenerator("switchToCostume(%s);\n", 1))
    @staticmethod
    def nextCostume(tokens):
        return NextCostume(tokens, JavaStatementGenerator("nextCostume();\n", 0))
    @staticmethod
    def switchBackdropTo(tokens):
        return SwitchBackdrop(tokens, JavaStatementGenerator("switchBackdropTo(%s);\n", 1))
    @staticmethod
    def changeSizeBy(tokens):
        return ChangeSize(tokens, JavaStatementGenerator("changeSizeBy(%s);\n", 1))
    @staticmethod
    def setSizeTo(tokens):
        return SetSize(tokens, JavaStatementGenerator("changeSizeBy(%s);\n", 1))
    @staticmethod
    def goToFront(tokens):
        return GoToFront(tokens, JavaStatementGenerator("goToFront();\n", 0))
    @staticmethod
    def goBackNLayers(tokens):
        return GoBackLayers(tokens, JavaStatementGenerator("goBackNLayers(%s);\n", 1))
    @staticmethod
    def nextBackdrop(tokens):
        return NextBackdrop(tokens, JavaStatementGenerator("nextBackdrop();\n", 0))
    @staticmethod
    def changeGraphicBy(tokens):
        return ChangeEffect(tokens).construct()
    @staticmethod
    def setGraphicTo(tokens):
        return SetEffect(tokens).construct()
    #### PEN
    @staticmethod
    def pen0Arg(tokens):
        assert len(tokens) == 1
        cmd = tokens[0]
        if cmd == "clearPenTrails":
            return Clear(tokens, JavaStatementGenerator("clear();\n", 0))
        elif cmd == "stampCostume":
            return Stamp(tokens, JavaStatementGenerator("stamp();\n", 0))
        elif cmd == "putPenDown":
            return PenDown(tokens, JavaStatementGenerator("penUp();\n", 0))
        elif cmd == "putPenUp":
            return PenUp(tokens, JavaStatementGenerator("penDown();\n", 0))
        else:
            raise ValueError(cmd)
    @staticmethod
    def pen1Arg(tokens):
        assert len(tokens) == 2
        cmd, arg = tokens
        if cmd == "penColor:":
            # arg is an integer representing a color.  
            # TODO: need to add code to import java.awt.Color  ??
            return SetPenColor(tokens, JavaStatementGenerator("setPenColor(%s);\n", 1))
        elif cmd == "changePenHueBy:":
            return ChangePenColor(tokens, JavaStatementGenerator("changePenColor(%s);\n", 1))
        elif cmd == "setPenHueTo:":
            return SetPenColor(tokens, JavaStatementGenerator("setPenColor(%s);\n", 1))
        elif cmd == "changePenSizeBy:":
            return ChangePenSize(tokens, JavaStatementGenerator("changePenSize(%s);\n", 1))
        elif cmd == "penSize:":
            return SetPenSize(tokens, JavaStatementGenerator("setPenSize(%s);\n", 1))
        else:
            raise ValueError(cmd)
    #### DATA
    @staticmethod
    def setVariable(tokens):
        return SetVar(tokens).construct()
    @staticmethod
    def hideVariable(tokens):
        return HideVar(tokens).construct()
    @staticmethod
    def showVariable(tokens):
        return ShowVar(tokens).construct()
    @staticmethod
    def changeVarBy(tokens):
        return ChangeVar(tokens).construct()
    @staticmethod
    def listAppend(tokens):
        return AddList(tokens).construct()
    @staticmethod
    def listRemove(tokens):
        return RemoveList(tokens).construct()
    @staticmethod
    def listInsert(tokens):
        return InsertList(tokens).construct()
    @staticmethod
    def listSet(tokens):
        return ReplaceList(tokens).construct()
    @staticmethod
    def hideList(tokens):
        return HideList(tokens).construct()
    @staticmethod
    def showList(tokens):
        return ShowList(tokens).construct()
    #### EVENTS
    @staticmethod
    def broadcast(tokens):
        return Broadcast(tokens, JavaStatementGenerator("broadcast(%s);\n", 1))
    @staticmethod
    def broadcastAndWait(tokens):
        return BroadcastWait(tokens, JavaStatementGenerator("broadcastAndWait(Sequence S, %s);\n", 1))
    #### CONTROL
    @staticmethod
    def doForever(tokens):
        return Forever(tokens, JavaBlockGenerator("while (true) {\n", ("    yield(s);\n", "}\n"),  0))
    @staticmethod
    def doWait(tokens):
        return Wait(tokens, JavaStatementGenerator("wait(Sequence S, %s);\n", 1))
    @staticmethod
    def doRepeat(tokens):
        return Repeat(tokens, JavaBlockGenerator("for (int i%s = 0; i < %s; i++) {\n", ("    yield(s);\n", "}\n"),  1))
    @staticmethod
    def doWaitUntil(tokens):
        return WaitUntil(tokens)
    @staticmethod
    def doRepeatUntil(tokens):
        return RepeatUntil(tokens, JavaBlockGenerator("while (!(%s)) {\n", ("    yield(s);\n", "}\n"),  1))
    @staticmethod
    def stopScripts(tokens):
        return StopScripts(tokens).construct() # TODO: Implement
    @staticmethod
    def createCloneOf(tokens):
        return CreateClone(tokens).construct()
    @staticmethod
    def deleteThisClone(tokens):
        return DeleteClone(tokens).construct() # TODO: Implement
    @staticmethod
    def doAsk(tokens):
        return Ask(tokens).construct() # TODO: Implement
    @staticmethod
    def resetTimer(tokens):
        return ResetTimer(tokens).construct() # TODO: Implement
    @staticmethod
    def callABlock(tokens):
        return Call(tokens).construct() # TODO: Implement
    @staticmethod
    def playSound(tokens):
        return PlaySound(tokens, JavaStatementGenerator("playSound(%s);\n", 1))
    @staticmethod
    def playSoundUntilDone(tokens):
        return PlayUntilDone(tokens, JavaStatementGenerator("playSoundUntilDone(%s);\n", 1))
    @staticmethod
    def noteOn(tokens):
        return PlayNote(tokens, JavaStatementGenerator("playNote(%s, %s, Sequence S);\n", 2))
    @staticmethod
    def instrument(tokens):
        return SetInstrument(tokens, JavaStatementGenerator("changeInstrument(%s);\n", 1))
    @staticmethod
    def playDrum(tokens):
        return PlayDrum(tokens, JavaStatementGenerator("playDrum(%s, %s, Sequence S);\n", 2))
    @staticmethod
    def rest(tokens):
        return Rest(tokens, JavaStatementGenerator("rest(%s, Sequence S);\n", 1))
    @staticmethod
    def changeTempoBy(tokens):
        return ChangeTempo(tokens, JavaStatementGenerator("changeTempoBy(%s);\n", 1))
    @staticmethod
    def setTempoTo(tokens):
        return SetTempo(tokens, JavaStatementGenerator("setTempo(%s);\n", 1))
    
#### Standard Blocks
## TODO Replace tokens with self.tokens
class Move(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class TurnR(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        print("Constructing turn R block: " + str(self.tokens[1]))

        return self
class TurnL(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):

        return self
class PointDir(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):

        return self
class PointAt(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):

        return self
class GoTo(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class GoToMouse(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class GoToSprite(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):

        return self
class GoToRandom(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)

class GlideTo(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
        
    def construct(self):
        
        return self
class ChangeX(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class SetX(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class ChangeY(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class SetY(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class Bounce(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class RotationStyle(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class SayFor(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Say(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class ThinkFor(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Think(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class Show(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)

class Hide(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)

class SwitchCostume(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class SwitchBackdrop(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class SwitchBackdropWait(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class NextCostume(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class NextBackdrop(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class ChangeEffect(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
        # TODO: implement the various graphics
    def construct(self):
        
        return self
class SetEffect(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
        # TODO: implement the various graphics
    def construct(self):
        
        return self
class ClearEffect(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        # TODO: implement the various graphics
class ChangeSize(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class SetSize(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class GoToFront(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class GoBackLayers(Block):
    def __init__(self, tokens):
        super().__init__(tokens)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class PlaySound(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class PlayUntilDone(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class StopSound(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class PlayDrum(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class Rest(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class PlayNote(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class SetInstrument(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class ChangeVolume(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        #TODO: volume
    def construct(self):
        
        return self
class SetVolume(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        #TODO: volume
    def construct(self):
        
        return self
class ChangeTempo(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class SetTempo(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class Clear(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class Stamp(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class PenUp(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class PenDown(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        
class SetPenColor(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class ChangePenColor(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class SetPenSize(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class ChangePenSize(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
    def construct(self):
        
        return self
class SetVar(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class ChangeVar(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Double"))
    def construct(self):
        
        return self
class ShowVar(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class HideVar(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class AddList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "String"))
    def construct(self):
        
        return self
class DeleteList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "String"))
    def construct(self):
        
        return self
class InsertList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[3], "String"))
    def construct(self):
        
        return self
class ReplaceList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Int"))
        self.ops.append(Reporter.createReporter(self.tokens[2], "String"))
        self.ops.append(Reporter.createReporter(self.tokens[3], "Double"))
    def construct(self):
        
        return self
class ShowList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class HideList(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class Broadcast(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class BroadcastWait(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "String"))
    def construct(self):
        
        return self
class Wait(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createReporter(self.tokens[1], "Double"))
    def construct(self):
        
        return self
class WaitUntil(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ops.append(Reporter.createBooleanReporter(self.tokens[1]))
    def construct(self):
        
        return self
class CreateClone(Block):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        # TODO Clone stuff

class Container(Block):
    """A block which contains other blocks. (C block)"""
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        children = tokens[1:]
#### The Container Blocks
class If(Container):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        print("Creating if")
        self.ops.append(Reporter.createBooleanReporter(self.tokens[1]))
        print("creating if children")
        self.children = Expression.constructBlocklist(tokens[-1])
        print("Done with if: " + str(self.children))
        
    def genCode(self, level):
        print("Generating if statement")
        opList = []
        opList.append(self.ops[0].genCode(level + 1))
        for child in self.children:
            opList.append(child.genCode(level + 1))
        return self.generator.genCode(opList, level)
        

class IfElse(Container):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
class Forever(Container):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        print("Creating forever")
        print("creating forever children")
        self.children = Expression.constructBlocklist(tokens[-1])
        print("Done with forever: " + str(self.children))
        
    def genCode(self, level):
        print("Generating forever statement")
        opList = []
        for child in self.children:
            opList.append(child.genCode(level + 1))
        return self.generator.genCode(opList, level)
class Repeat(Container):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.children = Expression.constructBlocklist(tokens[-1])
        self.ops.append(Reporter.createIntReporter(tokens[1]))
class RepeatUntil(Container):
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        print('Creating repeat children: ' + str(tokens[-1]))
        self.children = Expression.constructBlocklist(tokens[-1])
        self.ops.append(Reporter.createBooleanReporter(tokens[1]))
    def genCode(self, level):
        print("Generating forever statement")
        opList = []
        opList.append(self.ops[0].genCode(level + 1))
        for child in self.children:
            opList.append(child.genCode(level + 1))
        return self.generator.genCode(opList, level)
        
class Hat(Block):
    """A block that starts a script. (Hat block)"""
    def __init__(self, tokens, generator):
        super().__init__(tokens, generator)
        self.ctrGenerator = None
        self.construct()
    @staticmethod
    def GreenFlag(tokens, id):
        block = WhenFlagClicked(tokens, id, JavaBlockGenerator("public void whenFlagClickedCb" + \
                                            str(id) + '(Sequence S) {\n', ('}\n'),  0)) # TODO: add ID system
        block.ctrGenerator = JavaStatementGenerator('whenFlagClicked("whenFlagClickedCb' + str(id) + '");\n', 0)
        return block
    @staticmethod
    def keyPressed(tokens, id):
        key = tokens[0][1]
        block = WhenKeyPressed(tokens, id, JavaBlockGenerator("public void when" + key + "PressedCb" + \
                                            str(id) + '(Sequence S) {\n', ('}\n'),  0))
        block.ctrGenerator = JavaStatementGenerator('whenKeyPressed("' + key.lower() + '", "when' + key + 'ClickedCb' + str(id) + '");\n', 0)
        return block
    @staticmethod
    def whenClicked(tokens, id):
        block = WhenSpriteClicked(tokens, id, JavaBlockGenerator("public void whenSpriteClickedCb" + \
                                            str(id) + '(Sequence S) {\n', ('}\n'),  0))
        block.ctrGenerator = JavaStatementGenerator('whenSpriteClicked("whenSpriteClickedCb' + str(id) + '");\n', 0)
        return block
    @staticmethod
    def whenBackdropSwitched(tokens, id):
        block = WhenBackdropSwitched(tokens, id, JavaBlockGenerator("public void whenSwitchToBackdropCb" + \
                                            str(id) + '(Sequence S) {\n', ('}\n'),  0))
        block.ctrGenerator = JavaStatementGenerator('whenSwitchToBackdrop("' + bkName + '", "whenSwitchToBackdropCb' + str(id) + '");\n', 0)
        return block
    @staticmethod
    def whenRecv(tokens, id):
        block = WhenMsgRecvd(tokens, id, JavaBlockGenerator("public void messageRecvdCb" + \
                                            str(id) + '(Sequence S) {\n', ('}\n'),  0))
        block.ctrGenerator = JavaStatementGenerator('whenRcvMessage("' + bcName + '", "messageRecvdCb' + str(id) + '");\n', 0)
        return block
    
    @staticmethod
    def createHatBlock(tokens, id):
        hatScripts = { 'whenGreenFlag': Hat.GreenFlag,
                       'whenKeyPressed': Hat.keyPressed,
                       'whenClicked': Hat.whenClicked,
                       'whenSceneStarts': Hat.whenBackdropSwitched,
                       'whenIReceive': Hat.whenRecv
                        }
        
        hat = tokens[0][0]
        print("Checking for hat block: " + str(hat))
        if hat in hatScripts.keys():
            return hatScripts[hat](tokens, id)
        else:
            raise ValueError("No valid hat block")
    def construct(self):
        print("-----Beginning hat block-----\nTokens: " + str(self.tokens[1:]))
        for block in self.tokens[1:]:
            print("Running on token " + str(block))
            self.ops.append(Block.createBlock(block))
            print("Done running")
        print("Done with hat: " + str(self.ops))
    
    def genCtr(self, level):
        return self.ctrGenerator.genCode(self.ops[0:self.ctrGenerator.opCount], level)
    
    def genCode(self, level):
        opList = []
        for op in self.ops:
            opList.append(op.genCode(level + 1))
        return self.generator.genCode(opList, level)
        
            
        
class WhenFlagClicked(Hat):
    def __init__(self, tokens, id, generator):
        super().__init__(tokens, generator)
        print("Creating FlagClicked block: " + str(self.tokens))
        
    def genCode(self, level):
        print("Flag Ops: " + str(self.ops))
        return Hat.genCode(self, level)
        
class WhenKeyPressed(Hat):
    def __init__(self, tokens, id, generator):
        super().__init__(tokens, generator)
        print("Creating FlagClicked block: " + str(self.tokens))
        key = tokens[0][1]
        

class WhenSpriteClicked(Hat):
    def __init__(self, tokens, id, generator):
        super().__init__(tokens, generator)
        print("Creating SpriteClicked block: " + str(self.tokens))
        
        
class WhenBackdropSwitched(Hat):
    def __init__(self, tokens, id, generator):
        super().__init__(tokens, generator)
        print("Creating BackdropSwitch block: " + str(self.tokens))
        bkName = tokens[0][1]
        
        
class WhenMsgRecvd(Hat):
    def __init__(self, tokens, id, generator):
        super().__init__(tokens, generator)
        print("Creating MsgRecvd block: " + str(self.tokens))
        bcName = tokens[0][1]
        

class Literal(Expression):
    """Represents a literal value typed into a block"""
    def __init__(self, value, type, generator):
        super().__init__([value, type], generator)
        print("Instantiating literal value: " + str(value) + ", type: " + type)
        self.value = value
        self.type = type
        print("Creating literal generator: " + str(value) + " " + type)
    

class Variable:
    """Represents a variable that exists in the scratch world"""
    def __init__(self, name, sanName, value, type, cloud):
        self.name = name
        self.sanName = sanName
        self.value = value
        self.type = type
        self.cloud = cloud
    def construct(self):
        pass
    
class List(Variable):
    def __init__(self, name, sanName, values):
        self.name = name
        self.sanName = sanName
        self.value = values
        self.type = 'list'
        self.cloud = False
        
    """Represents a list that exists in the scratch world"""

def makeJavaId(name, capital = False):
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
    for ch in name:
        if ch.isspace():
            lastWasSpace = True
        elif ch.isalpha() or ch.isdigit():
            if lastWasSpace:
                ch = ch.upper()        # does nothing if isdigit.
                lastWasSpace = False
            res += ch
                

    # Look to see if res starts with a digit.
    if res[0].isdigit():
        digit2name = ("zero", "one", "two", "three", "four", "five",
                      "six", "seven", "eight", "nine")
        res = digit2name[int(res[0])] + res[1:]

    if capital and not res[0].isdigit():
        res = res[0].upper() + res[1:]
    
    # Ensure that the resulting name is not a java keyword
    if res in JavaGenerator.JAVA_KEYWORDS:
        res += '_'
    return res

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

class ScratchObject:
    """A sprite or the stage"""
    def __init__(self, tokens):
        self.tokens = tokens
        self.variables = {}
        self.lists = {}
        self.cloudVariables = []
        self.scripts = []
        self.sounds = []
        self.costumes = []
        self.children = []
    def resolveVars(self, vars, lists):
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
            print("Scheduling Run")
        # Automatically convert names and determine types for all variables
        def autoCB():
            for e in nameList:
                s = e.get()
                e.delete(0, END)
                e.insert(END, makeJavaId(s, False))
            for i in range(0, len(typeList)):
                try:
                    typeList[i].set(deriveType("", valueList[i].get())[1])
                except ValueError:
                    typeList[i].set("String")
        # Display a help message informing the user how to use the namer
        def helpCB():
            messagebox.showinfo("Help", "If a name is red, that means it is not valid in Java. Java variable names must " + \
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
                messagebox.showerror("Error", "Some of the inputs are still invalid. Click help for more " + \
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
                self.variables[name] = Variable(name, sanname, value, varType, cloud)
                if True:
                    print("Adding varInfo entry for", self._name, ":", name,
#                          "--> (" + sanname + ", " + varType + ")")
                
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
    
    
            for l in listOfLists:
                name = l['listName']
                contents = l['contents']
                visible = l['visible']
                try:
                    sanname = makeJavaId(name, False)
                except:
                    print("Error converting list to java id")
                    sys.exit(0)
                
                self.lists[name]  = sanname
                
            # Return focus and execution back to the main window
            root.focus_set()
            gui.quit()
            gui.destroy()
        # Main method code
        # Construct the GUI
        gui = Toplevel(root)
        #gui.bind("<Any-KeyPress>", keypress)
        
        gui.title("Variable Namer")
        gui.grab_set()


        table = Frame(gui)
        table.pack()
        buttons = Frame(gui)
        buttons.pack(side = BOTTOM)
        auto = Button(buttons, text = "Auto-Convert", command = autoCB)
        auto.pack(side = LEFT)
        confirm = Button(buttons, text = "Confirm", command = confirmCB)
        confirm.pack(side = LEFT)
        help = Button(buttons, text = "Help", command = helpCB)
        help.pack(side = LEFT)
        Label(table, text = "  Scratch Name  ").grid(row=0, column=0)
        Label(table, text = "Java Name").grid(row=0, column=1)
        Label(table, text = "Java Type").grid(row=0, column=2)
        Label(table, text = "Starting Value").grid(row=0, column=3)

        # Populate lists
        row = 1
        for var in listOfVars:
            name = var['name']  # unsanitized Scratch name
            value = var['value']
            cloud = var['isPersistent']
            lbl = Entry(table)
            lbl.insert(END, name)
            lbl.configure(state = "readonly")
            lbl.grid(row=row, column=0, sticky=W+E)

            ent = Entry(table)
            ent.insert(END, name)
            ent.grid(row=row, column=1, sticky=W+E)

            nameList.append(ent)
            svar = StringVar(gui)
            ent2 = OptionMenu(table, svar, "Int", "Double", "String")
            ent2.grid(row=row, column=2, sticky=W+E)
            #ent2.bind("<Button-1>", keypress)

            typeList.append(svar)
            ent3 = Entry(table)
            ent3.insert(END, value)
            ent3.grid(row=row, column=3, sticky=W+E)
            valueList.append(ent3)
            row += 1

        # Update the text color
        keypress()
        gui.mainloop()

class JavaSpriteClassGenerator(CodeGenerator):
    def __init__(self):
        self.output = ''
        self.opCount = 0
    def genCode(self, sprite):
        ctrScripts = []
        bodyScripts = []
        for i in range(len(sprite.scripts)):
            hat = sprite.scripts[i]
            bodyScripts.append(hat.genCode(0))
        for i in range(len(sprite.scripts)):
            hat = sprite.scripts[i]
            ctrScripts.append(hat.genCtr(1))
        
        classCode = sprite.header % (sprite.name, sprite.name)
        classCode += TAB + "public " + sprite.name + "()\n" + TAB + "{\n" + TAB * 2 + "super();\n"
        for costume in sprite.costumes:
            classCode += TAB * 2 + 'addCostume("' + str(costume['baseLayerID']) + '.png", "' + costume['costumeName'] + '");\n'
        classCode += TAB * 2 + "switchToCostume(" + str(sprite.costumeID) + ");\n"
        classCode += TAB * 2 + "setSizeTo(" + str(sprite.scale) + ");\n"
        if sprite.visible:
            classCode += TAB * 2 + "show();\n"
        else:
            classCode += TAB * 2 + "hide();\n"
        classCode += TAB * 2 + "pointInDirection(" + str(sprite.direction) + ");\n"
        for script in ctrScripts:
            classCode += TAB + script
        #TODO: rotation style
        classCode += TAB + '}\n\n' # Close constructor
        print(str(bodyScripts))
        for script in bodyScripts:
            classCode += script
        
        classCode += '\n}\n' # Close class
        return classCode
    def genWorld(self, stage):
        worldCode = stage.header % ('World', worldClassName)
        worldCode += TAB + "public " + stage.name + "World()\n" + TAB + "{\n" + TAB * 2 + "super();\n"
        for spr in stage.children:
            worldCode += TAB * 2 + 'addSprite("' + spr.name + '", ' + str(spr.x) + ', ' + str(spr.y) + ');\n'
            
        worldCode += TAB + '}\n\n' # Close constructor
        

        
        worldCode += '}\n' # Close class
        return worldCode
    
    def genStage(self, stage):
        stageCode = stage.header % ('Stage', 'Stage')
        for var in stage.variables:
            stageCode += 'static %svar %s;\n' % (var.type, var.sanName)
        stageCode += TAB + "public Stage()\n" + TAB + "{\n" + TAB * 2 + "super();\n"
        stageCode += TAB + '}\n'
        for script in stage.scripts:
            stageCode += script.genJava() + "\n"
        stageCode += '}\n'
        return stageCode
        
    
class Stage(ScratchObject):
    """The stage"""
    def __init__(self, tokens):
        super().__init__(tokens)
        self.children = []
        self.scripts = []
        self.name = tokens['objName']
        self.header = "import greenfoot.*\n\n/**\n * Discription of class %s.\n * @author (name)" + \
                      "\n * @version (version)\n */\npublic class %s extends Scratch\n{\n"
        self.generator = JavaSpriteClassGenerator()
    def construct(self):
        if "variables" in self.tokens and "lists" in self.tokens:
            resolveVars(tokens['variables'], tokens[lists])
        elif "variables" in self.tokens:
            resolveVars(tokens['variables'], ())
        elif "lists" in self.tokens:
            resolveVars((), tokens['lists'])
        
        for var in self.variables:
            var.construct()
        if 'scripts' in self.tokens:
            for script in self.tokens['scripts']:
                print(str(script))
                self.scripts = Hat.createHatBlock(script[2], id)
                
        if 'children' in self.tokens:
            for sprite in self.tokens['children']:
                self.children.append(Sprite(sprite))
                self.children[-1].construct()
    def genCode(self):
        files = {}
        global worldClassName
        files[worldClassName] = self.generator.genWorld(self)
        files['Stage'] = self.generator.genStage(self)
        for sprite in self.children:
            files[sprite.name] = sprite.generator.genCode(sprite)
        for key in files.keys():
            print(files[key])
        return files
        
        

class Sprite(Stage):
    """A sprite"""
    def __init__(self, tokens):
        super().__init__(tokens)
        self.costumes = tokens['costumes']
        self.costumeID = tokens['currentCostumeIndex']
        self.x = tokens["scratchX"]
        self.y = tokens["scratchY"]
        self.scale = tokens["scale"]
        self.direction = tokens['direction']
        self.rotationStyle = tokens["rotationStyle"]
        self.visible = tokens["visible"]
        self.generator = JavaSpriteClassGenerator()
        
    def construct(self):
        if 'scripts' in self.tokens:
            #print(self.tokens['scripts'])
            for i in range(len(self.tokens['scripts'])):
                script = self.tokens['scripts'][i]
                print(str(script))
                try:
                    self.scripts.append(Hat.createHatBlock(script[2], i))
                    self.scripts[-1].construct()
                except ValueError:
                    print(str(script) + " does not start with a valid hat, skipping...")
    
    def genCode(self):
        return self.generator.genCode()

    

        
                


def constructAst():
    global scratch_dir
    global stage
    # Now, (finally!), open the project.json file and start processing it.
    with open(os.path.join(scratch_dir, "project.json"), encoding = "utf_8") as data_file:
        data = json.load(data_file)
    
    stage = Stage(data)
    stage.construct()
    
gfEntryVar = None
scrEntryVar = None
def setup():
    global SCRATCH_FILE
    global PROJECT_DIR
    global SCRATCH_PROJ_DIR
    
    global scratch_dir
    global imagesDir 
    global soundsDir 
    global stage
    global gfEntryVar
    global scrEntryVar
    global worldClassName
    worldClassName = makeJavaId(os.path.basename(PROJECT_DIR).replace(" ", ""), True) + "World"
    #SCRATCH_FILE = r'C:\Users\jld73\Documents\ScratchFoot\Tests\hatblocks.sb2'
    #PROJECT_DIR = r'C:\Users\jld73\Documents\ScratchFoot\Tests\testh'
    SCRATCH_PROJ_DIR = 'Scratch_Code'
    scratch_dir = os.path.join(PROJECT_DIR, SCRATCH_PROJ_DIR)
    def findScratchFile():
        global scrEntryVar, SCRATCH_FILE
        SCRATCH_FILE=filedialog.askopenfilename(initialdir=SCRATCH_FILE,
                                                filetypes = [('Scratch files', '.sb2'), ('All files', '.*')])
        scrEntryVar.set(SCRATCH_FILE)
            
    def findGfDir():
        global gfEntryVar, PROJECT_DIR
        PROJECT_DIR = filedialog.askdirectory(initialdir=PROJECT_DIR)
        gfEntryVar.set(PROJECT_DIR)
    
    def exitTk():
        sys.exit(0)
    
    root = Tk()
    root.title("Convert Scratch to Greenfoot")
    root.protocol('WM_DELETE_WINDOW', exitTk)
    
    entryFrame = Frame(root)
    entryFrame.pack(side = TOP)
    scratchFrame = Frame(entryFrame)
    scratchFrame.pack(side = LEFT)
    scratchLabel = Label(scratchFrame, text="Scratch File")
    scratchLabel.pack(side = TOP)
    scrEntryVar = StringVar()
    scrEntryVar.set(SCRATCH_FILE)
    scratchEntry = Entry(scratchFrame, textvariable=scrEntryVar, width=len(SCRATCH_FILE))
    scratchEntry.pack(side = TOP)
    Button(scratchFrame, text="Find file", command=findScratchFile).pack(side=TOP)
    
    
    gfFrame = Frame(entryFrame)
    gfFrame.pack(side = RIGHT)
    gfLabel = Label(gfFrame, text = "Greenfoot Project Directory")
    gfLabel.pack(side = TOP)
    gfEntryVar = StringVar()
    gfEntryVar.set(PROJECT_DIR)
    gfEntry = Entry(gfFrame, textvariable=gfEntryVar, width=len(PROJECT_DIR))
    gfEntry.pack(side = TOP)
    Button(gfFrame, text="Find directory", command=findGfDir).pack(side=TOP)

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
        
    convertButton = Button(root, text = "Convert", command = convertButtonCb)
    convertButton.pack(side = BOTTOM)
    root.mainloop()
    
    imagesDir = os.path.join(PROJECT_DIR, "images")
    soundsDir = os.path.join(PROJECT_DIR, "sounds")
    
    if not os.path.exists(SCRATCH_FILE):
        print("Scratch download file " + SCRATCH_FILE + " not found.")
        sys.exit(1)
    if not os.path.exists(PROJECT_DIR):
        if useGui:
            if (messagebox.askokcancel("Make New Directory", "Greenfoot directory not found, generate it?")):
                print("Generating new project directory...")
                os.makedirs(PROJECT_DIR)
            else:
                system.exit(1)
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
        width, height = size.split("x")     # got the width and height, as strings
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
    
def execOrDie(cmd, descr):
    try:
        print("Executing shell command: " + cmd)
        retcode = call(cmd, shell=True)
        if retcode < 0:
            print("Command to " + descr + " was terminated by signal", -retcode, \
#                  file=sys.stderr)
            sys.exit(1)
        else:
            print("Command to " + descr + " succeeded")
    except OSError as e:
        print("Command to " + descr + ": Execution failed:", e, \
#              file=sys.stderr)
        sys.exit(1)
        
def convert():
    constructAst()
    print("Done creating AST")
    files = stage.genCode()
    
    for file in files.keys():
        print(PROJECT_DIR + os.sep + file + '.java')
        outFile = open(PROJECT_DIR + os.sep + file + '.java', 'w')
        outFile.write(files[file])
    
    
print("Beginning main code")
setup()

        