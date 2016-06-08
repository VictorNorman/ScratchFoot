#!/bin/env python3

import json
import os, os.path
import sys
from subprocess import call
from pprint import pprint

# TODO: make debug on/off a command-line arg
debug = False

NUM_SPACES_PER_LEVEL = 4

# Just print out the sprites.
# if debug:
#     for ch in data['children']:
#         print("-" * 75)
#         pprint(ch)

#
# Syntax diagrams:
#
# block        ::= [list of <stmt>]
# stmt         ::= [<cmd>, <expr>, <expr>, ... ]   # may be 0 expressions.  Is in a list.
# cmd          ::= <defined-cmd>        ??? 
# defined-cmd  ::= <doForever> | 'gotoX:y:' | etc., etc., etc.
# doIf         ::= ['doIf', <boolExpr>, <block>]
# doIfElse     ::= ['doIfElse', <boolExpr>, <block>, <block>]
# doForever    ::= ['doForever', <block>]
# boolExpr     ::= [<cmp>, <expr>, <expr>]
# expr         ::= <literal> | <func> | [operator, value, value]
# func         ::= [<I think a func is in a list>]
# 
# LOTS more!

# Expressions:
# "&" used for "and", "|" for "or"
# All values to "=", "<", ">" are strings.
# "*" for multiplication: values are numbers, not strings.


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
    # def addToInitCode(self, code):
    #     self.varInitCode += code


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

def block(level, codeObj, stmtList):
    """Handle block: a list of statements wrapped in { }."""

    if debug:
        print("block: stmtList = ")
        pprint(stmtList)
    codeObj.addToCode(genIndent(level) + "{\n")
    stmts(level, codeObj, stmtList)
    codeObj.addToCode(genIndent(level) + "}\n")

def stmts(level, codeObj, stmtList):
    """Generate code for the list of statements, by repeatedly calling stmt()"""
    if stmtList is None:
        return	# nothing to add to codeObj
    for aStmt in stmtList:
        # Call stmt to generate the statement, appending the result to the
        # overall resulting string.
        stmt(level + 1, codeObj, aStmt)

def stmt(level, codeObj, tokenList):
    """Handle a statement, which is a <cmd> followed by expressions.
    The stmt might be something like [doForever [<stmts>]].
    """

    if debug:
        print("stmt: tokenList = ")
        pprint(tokenList)

    cmd = tokenList[0]

    # Handle special stmts that may need code generated into multiple
    # outputs.
    if cmd == 'doForever':
        foreverCode = CodeAndCb()
        doForever(level, foreverCode, tokenList)
        codeObj.addToCode(foreverCode.code)
        codeObj.addToCbCode(foreverCode.cbCode)
        return
    
    if cmd in scratchStmt2genCode:
        genCodeDescr, genCodeFunc = scratchStmt2genCode[cmd]
        # Print out a description (for now).
        # codeObj.addToCode(genIndent(level) + "// " + genCodeDescr + "\n")
        # Call the function to generate the code, passing in the rest of
        # the tokens. 
        codeObj.addToCode(genCodeFunc(level, tokenList))
    else:
        return "Unimplemented stmt\n"


def boolExpr(tokenList):
    """Generate code for a boolean expression.
    It will have the format
    [<boolOp>, <boolExpr>, <boolExpr>], where boolOp is one of "&", "|"     or
    ['not', <boolExpr>]                                                     or
    [<cmpOp>, <mathExpr>, <mathExpr>], where <cmpOp> is one of "<", ">", or "="  or
    ['isTouching:' <val>], etc.						    or
    False	when the boolean expression was left empty in Scratch
    """
    resStr = ""
    firstOp = tokenList[0]
    if firstOp in ('&', '|'):
        assert len(tokenList) == 3
        resStr += "(" + boolExpr(tokenList[1])
        if firstOp == '&':
            resStr += " && "
        else:
            resStr += " || "
        resStr += boolExpr(tokenList[2]) + ")"
    elif firstOp == 'not':
        assert len(tokenList) == 2
        resStr += "! " + boolExpr(tokenList[1])
    elif firstOp in ('<', '>', '='):
        assert len(tokenList) == 3
        resStr += cmpOp(firstOp, tokenList[1], tokenList[2])
    elif firstOp == 'touching:':
        arg = tokenList[1]
        if arg == "_mouse_":
            resStr += "(isTouchingMouse())"
        elif arg == "_edge_":
            resStr += "(isTouchingEdge())"
        else:
            raise ValueError(firstOp)
    elif firstOp == 'touchingColor:':
        # TODO: this may not work if value from scratch is not compatible with java.
        resStr += "(isTouchingColor(new Color(" + mathOp(tokenList[1]) + ")))"
    elif firstOp == 'keyPressed:':
        resStr += handleKeyPressed(tokenList[1])
    elif firstOp == False:
        resStr += "false"
    else:
        raise ValueError()
    return resStr

def convertKeyPressName(keyname):
    # Single letter/number keynames in Scratch and Greenfoot are identical.
    # Keyname "space" is the same in each.
    # Scratch does not have keynames for F1, F2, ..., Control, Backspace, etc.
    # 4 arrow keys in Scratch are called "left arrow", "right arrow", etc.
    # In Greenfoot, they are just "left", "right", etc.
    if "arrow" in keyname:
        keyname = keyname.rstrip(" arrow")
    return keyname
    
def handleKeyPressed(keyname):
    """Generate call to isKeyPressed()"""
    return '(isKeyPressed("' + convertKeyPressName(keyname) + '"))'


def convertToNumber(tok):
    try:
        val = int(tok)
    except ValueError:
        try:
            val = float(tok)
        except ValueError:
            raise
    return val

def strExpr(tokenOrList):
    if debug:
        print("strExpr: tokenOrList is", tokenOrList)
    if not isinstance(tokenOrList, list):
        # Print it out as a Java string with double quotes.
        return '"' + str(tokenOrList) + '"'
    else:
        # TODO: ??? Not sure about this...
        return mathOp(tokenOrList) + '"' + str(res) + '"'

def mathOp(tokenOrList):

    if not isinstance(tokenOrList, list):
        # TODO: get rid of convertToNumber totally?
        return str(convertToNumber(tokenOrList))

    # It is a list, so it is a math expression.

    if len(tokenOrList) == 1:
        # Handle cases of operations that take 0 arguments, which
        # means it is a built-in command, like xpos:.
        op = tokenOrList[0]
        if op == "xpos":
            return "getX()"
        elif op == "ypos":
            return "getY()"
        elif op == "heading":
            return "getDirection()"
        else:
            return "NOT IMPL"
            
    if len(tokenOrList) == 2:
        # Handle cases of operations that take 1 argument.
        op, tok1 = tokenOrList
        if op == "rounded":
            return "Math.round((float) " + mathOp(tok1) + ")"
        elif op == "stringLength:":
            return "lengthOf(" + strExpr(tok1) + ")"
        else:
            return "NOT IMPL2"

    assert len(tokenOrList) == 3	# Bad assumption?
    op, tok1, tok2 = tokenOrList	

    # Handle special cases before doing the basic ones which are inorder
    # ops (value op value).
    if op == 'randomFrom:to:':
        # tok1 and tok2 may be math expressions.
        return "pickRandom(" + mathOp(tok1) + ", " + mathOp(tok2) + ")"
    elif op == "letter:of:":
        return "letterNOf(" + strExpr(tok2) + ", " + mathOp(tok1) + ")"
    elif op == "concatenate:with:":
        return "join(" + strExpr(tok1) + ", " + strExpr(tok2) + ")"
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
        return op2Func[tok1] + mathOp(tok2) + ")"
    else:
        raise ValueError(op)
        

    resStr = "(" + mathOp(tok1)
    if op == '+':
        resStr += " + "
    elif op == '-':
        resStr += " - "
    elif op == '*':
        resStr += " * "
    elif op == '/':
        resStr += " / "		# TODO: handle floating pt/int div.
    elif op == '%':
        resStr += " % "
    else:
        raise ValueError(op)
    resStr += mathOp(tok2) + ")"
    return resStr


def cmpOp(op, tok1, tok2):
    """Generate code for boolean comparisons: <, >, =."""

    if debug:
        print("cmpOp: op is ", op, "tok1", tok1, "tok2", tok2)

    resStr = "(" + mathOp(tok1)
    if op == '<':
        resStr += " < "
    elif op == '>':
        resStr += " > "
    elif op == '=':
        resStr += " == "
    else:
        raise ValueError(op)
    return resStr + mathOp(tok2) + ")"

def whenFlagClicked(codeObj, tokens):
    """Generate code to handle the whenFlagClicked block.
    All code in tokens goes into a callback.
    """
    scriptNum = codeObj.getNextScriptId()
    # Build a name like whenFlagClickedCb0 
    cbName = 'whenFlagClickedCb' + str(scriptNum)

    # Code in the constructor is always level 2.
    codeObj.addToCode(genIndent(2) + 'whenFlagClicked("' + cbName + '");\n')

    level = 1    # all callbacks are at level 1.

    # Create a new cbObj, which block() will generate code into.  Then, we'll
    # copy it out into the original codeObj's cbCode.
    cbObj = CodeAndCb()
    # Add two blank lines before each method definition.
    cbObj.addToCode("\n\n" + genIndent(level) + "public void " + cbName +
                    "(Sequence s)\n")
    block(level, cbObj, tokens)
    codeObj.addToCbCode(cbObj.code)

def whenSpriteClicked(codeObj, tokens):
    """Generate code to handle the whenClicked block.
    All code in tokens goes into a callback.
    """
    scriptNum = codeObj.getNextScriptId()
    # Build a name like whenFlagClickedCb0 
    cbName = 'whenSpriteClickedCb' + str(scriptNum)

    # Code in the constructor is always level 2.
    codeObj.addToCode(genIndent(2) + 'whenSpriteClicked("' + cbName + '");\n')

    level = 1    # all callbacks are at level 1.

    # Create a new cbObj, which block() will generate code into.  Then, we'll
    # copy it out into the original codeObj's cbCode.
    cbObj = CodeAndCb()
    # Add two blank lines before each method definition.
    cbObj.addToCode("\n\n" + genIndent(level) + "public void " + cbName +
                    "(Sequence s)\n")
    block(level, cbObj, tokens)
    codeObj.addToCbCode(cbObj.code)


def whenKeyPressed(codeObj, key, tokens):
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

    # Create a new cbObj, which block() will generate code into.  Then, we'll
    # copy it out into the original codeObj's cbCode.
    cbObj = CodeAndCb()
    # Add two blank lines before each method definition.
    cbObj.addToCode("\n\n" + genIndent(level) + "public void " + cbName +
                    "(Sequence s)\n")
    block(level, cbObj, tokens)

    # TODO: handle foreverloop in whenKeyPressed Cb code...

    codeObj.addToCbCode(cbObj.code)

    
def doForever(level, codeObj, tokens):
    """Generate doForever code.  tokens is a list of comments.
    forever loop is turned into a while (true) loop, with the last
    operation being a yield(s) call.
    """
    codeObj.addToCode(genIndent(level) + "while (true)\n")
    codeObj.addToCode(genIndent(level) + "{\n")
    stmts(level, codeObj, tokens[1])
    codeObj.addToCode(genIndent(level + 1) + "yield(s);\n")
    codeObj.addToCode(genIndent(level) + "}\n")

def doIf(level, tokens):
    """Generate code for if <test> : <block>.  Format of tokens is
    'doIf' [test expression] [true-block]
    """
    assert len(tokens) == 3 and tokens[0] == "doIf"

    # Handle the boolean expression
    # We don't generate parens around the boolExpr as it will put them there.
    resStr = genIndent(level) + "if "
    resStr += boolExpr(tokens[1])
    resStr += block(level, tokens[2])
    return resStr


def doIfElse(tokens, level):
    """Generate code for if <test> : <block> else: <block>.  Format of tokens is
    'doIfElse' [test expression] [true-block] [else-block]
    """
    assert len(tokens) == 4 and tokens[0] == 'doIfElse'

    # TODO: if bool expression was left empty, then it will contain False

    resStr = genIndent(level) + "if "
    resStr += boolExpr(tokens[1])

    resStr += block(level, tokens[2])
    resStr += genIndent(level) + "else\n"
    resStr += block(level, tokens[3])
    return resStr
    
    
def bogusFunc(level, tokens):
    return ""

def motion0Arg(level, tokens):
    """Generate code to handle Motion blocks with 0 arguments"""
    assert len(tokens) == 1
    cmd = tokens[0]
    if cmd == "bounceOffEdge":
        prindent(level)
        print("ifOnEdgeBounce();")
    else:
        raise ValueError(cmd)

def motion1Arg(level, tokens):
    """Generate code to handle Motion blocks with 1 argument:
    forward:, turnLeft:, turnRight:, etc."""
    assert len(tokens) == 2
    cmd, arg = tokens
    if cmd == "forward:":
        return genIndent(level) + "move(" + mathOp(arg) + ");\n"
    elif cmd == "turnRight:":
        return genIndent(level) + "turnRightDegrees((int) " + mathOp(arg) + ");\n"
        # TODO: be nice to get rid of the (int)
        # but would require knowing if mathOp is
        # returning an int type or float...
        # OR, add turnRightDegrees(float) and convert it.
    elif cmd == "turnLeft:":
        return genIndent(level) + "turnLeftDegrees((int) " + mathOp(arg) + ");\n"
        # TODO: be nice to get rid of the (int)
        # but would require knowing if mathOp is
        # returning an int type or float...
    elif cmd == "heading:":
        return genIndent(level) + "pointInDirection((int) " + mathOp(arg) + ");\n"
    elif cmd == "gotoSpriteOrMouse:":
        if arg == "_mouse_":
            return genIndent(level) + "goToMouse();\n"
        else:
            return genIndent(level) + "// goToSprite(): not implemented yet.\n"
        # TODO: Looks like there is something new: gotoRandomPosition()
    elif cmd == "changeXposBy:":
        return genIndent(level) + "changeXBy((int) " + mathOp(arg) + ");\n"
    elif cmd == "xpos:":
        return genIndent(level) + "setXTo((int) " + mathOp(arg) + ");\n" 
    elif cmd == "changeYposBy:":
        return genIndent(level) + "changeYBy((int) " + mathOp(arg) + ");\n"
    elif cmd == "ypos:":
        return genIndent(level) + "setYTo((int) " + mathOp(arg) + ");\n"
    elif cmd == "setRotationStyle":
        resStr = genIndent(level) + "setRotationStyle("
        if arg == "left-right":
            return resStr + "RotationStyle.LEFT_RIGHT);\n"
        elif arg == "don't rotate":
            return resStr + "RotationStyle.DONT_ROTATE);\n"
        elif arg in ("all around", "normal"):
            return resStr + "RotationStyle.ALL_AROUND);\n"
        else:
            raise ValueError(cmd)
    else:
        raise ValueError(cmd)

def motion2Arg(level, tokens):
    """Generate code to handle Motion blocks with 2 arguments:
    gotoX:y:, etc."""
    cmd, arg1, arg2 = tokens
    if cmd == "gotoX:y:":
        return genIndent(level) + "goto((int) " + mathOp(arg1) + ", (int) " + mathOp(arg2) + ");\n"
    else:
        raise ValueError(cmd)

def pen0Arg(level, tokens):
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

def pen1Arg(level, tokens):
    """Generate code to handle Pen blocks with 1 argument."""
    
    assert len(tokens) == 2
    cmd, arg = tokens
    resStr = genIndent(level)
    if cmd == "penColor:":
        # arg is an integer representing a color.  
        # TODO: need to add code to import java.awt.Color  ??
        # NOTE: the order of colors in the value from scratch may not be
        # correct for Color().
        # NOTE: we also will have problems here if we have to create
        # multiple variables in the same block.  They cannot both be named
        # "color".  If the order of rgb in the number from scratch is
        # correct, we can inline the creation of the color object to solve
        # this problem. 
        resStr += "java.awt.Color color = new Color((int) " + mathOp(arg) + ");\n"
        return resStr + genIndent(level) + "setPenColor(color);\n"
    elif cmd == "changePenHueBy:":
        return resStr + "changePenColorBy(" + mathOp(arg) + ");\n"
    elif cmd == "setPenHueTo:":
        return resStr + "setPenColor(" + mathOp(arg) + ");\n"
    else:
        raise ValueError(cmd)

def doAsk(level, tokens):
    """Generate code to ask the user for input.  Returns the resulting String."""

    assert len(tokens) == 2 and tokens[0] == "doAsk"
    quest = tokens[1]
    return genIndent(level) + "String answer = askStringAndWait(" + \
           strExpr(quest) + ")\t\t// may want to replace variable\n"

def doWait(level, tokens):
    """Generate a wait call."""
    assert len(tokens) == 2 and tokens[0] == "wait:elapsed:from:"
    return genIndent(level) + "wait(s, " + mathOp(tokens[1]) + ");\n"


scratchStmt2genCode = {
    # 'whenGreenFlag': ["Generate greenFlag code", bogusFunc],
    # 'doForever': ["Generate ForeverLoop code... calling genCode recursively",
    #              doForever], # rest of list is the code in the forever loop.
    'doIf': ["Generate if clause code", doIf],
    'doIfElse': ["Generate if-else code", doIfElse],
    'setVar:to:': ["Generate variable creation or setting variable value", bogusFunc],
    'whenIReceive': ["Generate whenIreceive code", bogusFunc],
    'hide': ["Generate hide() call", bogusFunc],
    'readVariable': ["Generate code to read variable", bogusFunc],
    'show': ["Generate show() call", bogusFunc],
    'doUntil': ["Generate do-until call", bogusFunc],

    # Motion commands
    'forward:': ["Generate moveForward func call", motion1Arg],
    'turnLeft:': ["Generate turnLeft() code", motion1Arg],
    'turnRight:': ["Generate turnRight() code", motion1Arg],
    'heading:': ["Generate set Heading code", motion1Arg],  
    'gotoX:y:': ["Generate goto(x, y)", motion2Arg],
    'gotoSpriteOrMouse:': ["Generate gotoSpriteOrMouse code", motion1Arg],
    'changeXposBy:': ["Generate changeXposBy code", motion1Arg],
    'xpos:': ["Generate setXto code", motion1Arg],
    'changeYposBy:': ["Generate changeYposBy code", motion1Arg],
    'ypos:': ["Generate setYto code", motion1Arg],
    'bounceOffEdge': ["Generate bounce off edge code", motion0Arg],    # TODO
    'setRotationStyle': ["Generate Set rotation style code", motion1Arg],

    # Pen commands
    'clearPenTrails': ["Generate code to clear screen", pen0Arg],
    'stampCostume': ["Generate code to stamp", pen0Arg],
    'putPenDown': ["Generate code to put pen down", pen0Arg],
    'putPenUp': ["Generate code to put pen up", pen0Arg],
    'penColor:': ["Generate code to set pen color", pen1Arg],
    'changePenHueBy:': ["Generate code to change pen color", pen1Arg],
    'setPenHueTo:': ["Generate code to set pen color", pen1Arg],

    # Sensing commands
    'doAsk': ['Generate code to ask for input', doAsk],

    'lookLike:': ["Generate setCostume func call (I think)", bogusFunc],
    'changeVar:by:': ["Generate code to change variable value", bogusFunc],
    'broadcast': ["Generate broadcast() call", bogusFunc],
    'wait:elapsed:from:': ["Generate wait() call", doWait],
    }

def convertSpriteToFileName(sprite):
    """Make the filename with all words from sprite capitalized and
    joined, with no spaces between."""
    words = [w.capitalize() for w in sprite.split()]
    return ''.join(words) + ".java"
    

def genHeaderCode(outFile, spriteName):
    """Generate code at the top of the output file -- imports, public class ..., etc."""
    outFile.write("import greenfoot.*;\n\n")
    outFile.write("/**\n * Write a description of class " + spriteName + " here.\n")
    outFile.write(" *\n * @author (your name)\n * @version (a version number or a date)\n")
    outFile.write(" */\n")
    outFile.write("public class " + spriteName + " extends Scratch\n{\n")


def genConstructorCode(outFile, spriteName, code):
    """Generate code for the constructor.
    This code will include calls to initialize data, etc., followed by code
    to register callbacks for whenFlagClicked,
    whenKeyPressed, etc.
    """

    outFile.write(genIndent(1) + "public " + spriteName + "()\n")
    outFile.write(genIndent(1) + "{\n")
    # Write out the code that registers the callbacks.
    outFile.write(code)
    outFile.write(genIndent(1) + "}\n");

def genLoadCostumesCode(costumes):
    """Generate code to load costumes from files for a sprite.
    """

    print("genLoadCC: costumes ->" + str(costumes) + "<-")
    resStr = ""
    imagesDir = os.path.join(PROJECT_DIR, "images")
    for cos in costumes:
        # costume's filename is the baseLayerID (which is a small integer (1, 2, 3, etc.) plus ".svg" 
        filename = str(cos['baseLayerID'])
        # convert it with rsvg-convert -- TODO: fix this to work for Windoze, etc.
        dest = filename + ".jpg"
        execOrDie("rsvg-convert " + os.path.join(imagesDir, filename + ".svg") + \
                  " -o " + os.path.join(imagesDir, dest),
                  "convert svg file to jpg")
        resStr += genIndent(2) + 'addCostume("' + dest + '", "' + cos['costumeName'] + '");\n'
    return resStr

def genInitialSettingsCode(spr):
    """Generate code to set the sprite's initial settings, like its
    location on the screen, the direction it is facing, whether shown
    or hidden, etc.
    """
    resStr = ""

    # Set the initial costume (NOTE: could use the name of the costume instead of index...)
    resStr = genIndent(2) + 'switchToCostume(' + str(spr['currentCostumeIndex']) + ');\n'
    if not spr['visible']:
        resStr += genIndent(2) + 'hide();\n';
    resStr += genIndent(2) + 'pointInDirection(' + str(spr['direction']) + ');\n';
    # TODO: need to test this!
    resStr += motion1Arg(2, ['setRotationStyle', spr['rotationStyle']])
    return resStr

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
    public %s()
    {
        // To change world size, pass in width, height values to super() below.
        super();
"""
    # TODO: we could add parameters to the super() call above to make the
    # size of the screen be 480x360, just like a Scratch screen, but I
    # think one of the main limitations of Scratch is this small screen
    # size. 
    return boilerplate % (classname, classname, classname)



# ----------------- main -------------------

# TODO: make file name a command-line arg

usage = 'Usage: python3 s2g.py <scratchFile.sb2> <GreenfootProjDir>'

if len(sys.argv) != 3:
    print(usage)
    sys.exit(1)

SCRATCH_FILE = sys.argv[1].strip()
PROJECT_DIR = sys.argv[2].strip()

SCRATCH_PROJ_DIR = "scratch_code"

if not os.path.exists(SCRATCH_FILE):
    print("Scratch download file " + SCRATCH_FILE + " not found.")
    sys.exit(1)
if not os.path.exists(PROJECT_DIR):
    print("Greenfoot folder " + PROJECT_DIR + " not found.")
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

execOrDie("unzip -ou " + SCRATCH_FILE + " -d " + scratch_dir,
          "unzip scratch download file")

# Copy image files to images dir.
execOrDie("cp " + os.path.join(scratch_dir, "*.{svg,png}") + " " + \
          os.path.join(PROJECT_DIR, "images"),
          "move image files to Greenfoot images directory")
      

# TODO: move sounds files.  NOTE: this won't work on Windows.  Use os.rename().


# Now, (finally!), open the project.json file and start processing it.
with open(os.path.join(scratch_dir, "project.json")) as data_file:
    data = json.load(data_file)

sprites = data['children']

# We'll need to write configuration "code" to the greenfoot.project file.  Store
# the lines to write out in this variable.
projectFileCode = ""

# Code to be written into the World.java file.
worldCode = ""

for spr in sprites:
    if 'objName' in spr:
        spriteName = spr['objName']

        # TODO: need to handle sprites with names that are illegal Java identifiers.
        # E.g., the sprite could be called "1", but we cannot create a "class 1".
        
        print("\n----------- Sprite: {} ----------------".format(spriteName))

        # Write out a line to the project.greenfoot file to indicate that this
        # sprite is a subclass of the Scratch class.
        projectFileCode += "class." + spriteName + ".superclass=Scratch\n"


        # Extract the last position of the sprite and pass to addSprite() call.
        worldCode += genIndent(2) + 'addSprite("' + spriteName + '", ' + \
                     str(spr['scratchX']) + ', ' + str(spr['scratchY']) + ');\n'

        ctorCode = ""
        cbCode = []

        costumeCode = genLoadCostumesCode(spr['costumes'])
        if debug: print("CostumeCode is ", costumeCode)

	# Like location, direction, shown or hidden, etc.
        initSettingsCode = genInitialSettingsCode(spr)
        if debug: print("Initial Settings Code is ", initSettingsCode)

	# Generate a line to the project.greenfoot file to set the image file, like this:
        #     class.Sprite1.image=1.jpg
        projectFileCode += "class." + spriteName + ".image=" + str(spr['costumes'][0]['baseLayerID']) + ".jpg\n"

        ctorCode += costumeCode + initSettingsCode

        # The value of the 'scripts' key is the list of the scripts.  It may be a
        # list of 1 or of many.
        if 'scripts' in spr:
            for scrNum in range(len(spr['scripts'])):
                # items 0 and 1 in the sublist are the location on the screen of the script.
                # We don't care about that, obviously.  Item 2 is the actual code.
                script = spr['scripts'][scrNum][2]
                print("Script" + str(scrNum) + ":", script)

                codeObj = CodeAndCb()	# Holds all the code that is generated.

                # script is a list of these: [[cmd] [arg] [arg]...]
                # If script starts with whenGreenFlag, generate code into
                # whenFlagClicked callback.
                if script[0] == ['whenGreenFlag']:
                    print("Calling stmts with ", script[1:])

                    # Add a comment to each section of code indicating where
                    # the code came from.
                    codeObj.code += genIndent(2) + "// Code from Script " + str(scrNum) + "\n"
                    whenFlagClicked(codeObj, script[1:])
                    ctorCode += codeObj.code
                    if codeObj.cbCode != "":
                        print("main: stmts() called generated this cb code:\n" +
                              codeObj.cbCode)
                        # the stmts() generated code to be put into a callback
                        # in the java class.
                        cbCode.append(codeObj.cbCode)
                elif script[0] == ['whenClicked']:
                    # Add a comment to each section of code indicating where
                    # the code came from.
                    codeObj.code += genIndent(2) + "// Code from Script " + str(scrNum) + "\n"
                    whenSpriteClicked(codeObj, script[1:])
                    ctorCode += codeObj.code
                    if codeObj.cbCode != "":
                        print("main: stmts() called generated this cb code:\n" +
                              codeObj.cbCode)
                        # the stmts() generated code to be put into a callback
                        # in the java class.
                        cbCode.append(codeObj.cbCode)
                elif isinstance(script[0], list) and script[0][0] == 'whenKeyPressed':
                    # pass in the key that we are waiting for, and the code to run
                    # Add a comment to each section of code indicating where
                    # the code came from.
                    codeObj.code += genIndent(2) + "// Code from Script " + str(scrNum) + "\n"
                    whenKeyPressed(codeObj, script[0][1], script[1:])
                    ctorCode += codeObj.code

                    if codeObj.cbCode != "":
                        print("main: stmts() called generated this cb code:\n" +
                              codeObj.cbCode)
                        # the stmts() generated code to be put into a callback
                        # in the java class.
                        cbCode.append(codeObj.cbCode)

                # TODO: filter out scripts that are "left over" -- don't start
                # with whenGreenFlag, etc. 


	# Open file with correct name and generate code into there.
        filename = os.path.join(PROJECT_DIR, convertSpriteToFileName(spriteName))
        print("Writing code to " + filename + ".")
        outFile = open(filename, "w")
        genHeaderCode(outFile, spriteName)
        genConstructorCode(outFile, spriteName, ctorCode)
        for code in cbCode:
            outFile.write(code)

        outFile.write("}\n")
        outFile.close()

    else:
        print("\n----------- Not a sprite --------------");
        print(spr)

#
# Now, have to make the World file -- a subclass of ScratchWorld.
#

# Make first letter capitalized and remove all spaces, then add World.java
# to end. 
classname = PROJECT_DIR.capitalize().replace(" ", "") + "World"
filename = os.path.join(PROJECT_DIR, classname + ".java")
outFile = open(filename, "w")
print("Writing code to " + filename + ".")
worldCode = genWorldHeaderCode(classname) + worldCode + genIndent(1) + "}\n}\n"		# fix last part here.
outFile.write(worldCode)
outFile.close()

projectFileCode += "class." + classname + "superclass=ScratchWorld\n"
projectFileCode += "world.lastInstantiated=" + classname + "\n"

# Now, add configuration information to the project.greenfoot file.

# Open in append mode, since we'll be writing lines to the end.
with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "a") as projF:
    projF.write("class.Scratch.superclass=greenfoot.Actor\n")
    projF.write("class.ScratchWorld.superclass=greenfoot.World\n")
    projF.write(projectFileCode)
    
# TODO: if a user runs s2g.py multiple times, it will add repeated lines to
# the project.greenfoot file.  That's bad, I imagine.
# One solution is to back up the project.greenfoot file before editing and
# then always use that when editing.


# NOTES:
# o Motion commands are done, except for glide.
# o Operators commands are done.
# 

# If you create a new (empty) Scenario, then copy ScratchWorld.java and
# Scratch.java to the folder and edit the project.greenfoot and add these
# lines to it (without the #s)
# class.Scratch.superclass=greenfoot.Actor
# class.ScratchWorld.superclass=greenfoot.World

# then, if you restart Greenfoot and load the Scenario, the classes show
# up.

# Could probably run s2g.py


# User downloads Scratch project to directory above where they want the
# Greenfoot project to exist, say ~/snowman.sb2, and want to make a
# grenfoot project in ~/Snowman/
# Put scratchfoot.gfar in ~ and open it with Greenfoot:
#  o it creates ~/scratchfoot/... with all the greenfoot stuff in it.
# Exit Greenfoot.
# change name of scratchfoot/ to Snowman/
# Run s2g.py snowman.sb2 Snowman
#  o s2g.py unzips snowman.sb2 into Snowman/scratch_code/
#  o s2g.py then creates Greenfoot .java files in Snowman/
#  o s2g.py then edits Snowman/project.greenfoot to add the new files to
#    the project.
# Restart Greenfoot and your project should be ready to compile and run.


