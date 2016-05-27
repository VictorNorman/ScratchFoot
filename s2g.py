#!/bin/env python3

import json
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
            return resStr + "LEFT_RIGHT);\n"
        elif arg == "don't rotate":
            return resStr + "DONT_ROTATE);\n"
        elif arg == "all around":
            return resStr + "ALL_AROUND);\n"
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
    'doForever': ["Generate ForeverLoop code... calling genCode recursively",
                  doForever], # rest of list is the code in the forever loop.
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
    words = sprite.split()
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
    outFile.write(code)
    outFile.write(genIndent(1) + "}\n");

def genCallbacks(outFile, codes):
    """Generate code for the callbacks.
    """
    for code in codes:
        outFile.write(code)
    

# ----------------- main -------------------

# TODO: make file name a command-line arg
with open("simple1/project.json") as data_file:
    data = json.load(data_file)

sprites = data['children']

for spr in sprites:
    if 'objName' in spr:
        spriteName = spr['objName']

        # TODO: need to handle sprites with names that are illegal Java identifiers.
        # E.g., the sprite could be called "1", but we cannot create a "class 1".
        
        print("\n----------- Sprite: {} ----------------".format(spriteName))

        ctorCode = ""
        cbCode = []

        # The value of the 'scripts' key is the list of the scripts.  It may be a
        # list of 1 or of many.
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

            # TODO: filter out script that are "leftover" -- don't start
            # with whenGreenFlag, etc. 


	# Open file with correct name and generate code into there.
        filename = convertSpriteToFileName(spriteName)
        outFile = open(filename, "w")
        genHeaderCode(outFile, spriteName)

        genConstructorCode(outFile, spriteName, ctorCode)
        genCallbacks(outFile, cbCode)

	# TODO: process the outer block different than other blocks, because it
        # can contain "garbage" scripts that don't start with whenGreenFlag or
        # onKeyPress, etc. -- just stuff left in the background -- that shouldn't
        # be converted to Java -- or should be converted specially, e.g., put into
        # comment blocks.
        # outFile.write(block(0, script))
        outFile.write("}\n")
        outFile.close()

    else:
        print("\n----------- Not a sprite --------------");
        print(spr)
        
    


# NOTES:
# o Motion commands are done, except for glide.
# o Operators commands are done.
# 
