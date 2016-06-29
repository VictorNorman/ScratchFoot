#!/bin/env python3

import glob
import json
import os, os.path
import platform
from pprint import pprint
import shutil
from subprocess import call, getstatusoutput
import sys

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


# A global dictionary mapping (spriteName, variableName) --> variableType.
# We need this so we can generate code that calls the correct
# functions to generate the correct type of results.
# E.g., if a variable is boolean, we'll call boolExpr()
# from setVariables(), not mathExpr().
varTypes = {}

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


def block(level, stmtList):
    """Handle block: a list of statements wrapped in { }."""

    if debug:
        print("block: stmtList = ")
        pprint(stmtList)
    return genIndent(level) + "{\n" + stmts(level, stmtList) + \
           genIndent(level) + "}\n"


def stmts(level, stmtList):
    """Generate code for the list of statements, by repeatedly calling stmt()"""
    if stmtList is None:
        return ""
    retStr = ""
    for aStmt in stmtList:
        # Call stmt to generate the statement, appending the result to the
        # overall resulting string.
        retStr += stmt(level + 1, aStmt)
    return retStr


def stmt(level, tokenList):
    """Handle a statement, which is a <cmd> followed by expressions.
    The stmt might be something like [doForever [<stmts>]].
    """

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
        resStr += "(" + mathExpr(tokenList[1])
        if firstOp == '<':
            resStr += " < "
        elif firstOp == '>':
            resStr += " > "
        else: 	# must be ' = '
            resStr += " == "
        resStr += mathExpr(tokenList[2]) + ")"
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
        resStr += "(isTouchingColor(new java.awt.Color(" + mathExpr(tokenList[1]) + ")))"
    elif firstOp == 'keyPressed:':
        resStr += handleKeyPressed(tokenList[1])
    elif firstOp == 'mousePressed':
        resStr += "(isMouseDown())"
    elif firstOp == 'readVariable':
        resStr += readVariable(tokenList[1])
    elif firstOp == False:
        resStr += "false"
    else:
        raise ValueError(firstOp)
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


def strExpr(tokenOrList):
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
        else:
            raise ValueError("Unknown string operator " + op)
    if len(tokenOrList) == 3:
        op, tok1, tok2 = tokenOrList	
        if op == "concatenate:with:":
            # This is a little strange because I know you can join a string
            # with an integer literal or expression result in Scratch.
            return "join(" + strExpr(tok1) + ", " + strExpr(tok2) + ")"
        elif op == "letter:of:":
            return "letterNOf(" + strExpr(tok2) + ", " + mathExpr(tok1) + ")"
        else:
            raise ValueError("Unknown string operator " + op)
    raise ValueError("Unknown string operator " + tokenOrList[0])

def mathExpr(tokenOrList):

    if isinstance(tokenOrList, str):
        # We have a literal value that is a string.  We should convert it
        # to an integer, if possible.
        # This is to cover cases like if you have (in Scratch) x position <
        # 0: Scratch give us "0" in the json.
        # (Convert to str() because everything we return is a str.)
        return str(int(tokenOrList))

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
            return "Math.round((float) " + mathExpr(tok1) + ")"
        elif op == "stringLength:":
            return "lengthOf(" + strExpr(tok1) + ")"
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
            return readVariable(tok1)
        else:
            raise ValueError("Unknown operation " + op)

    assert len(tokenOrList) == 3	# Bad assumption?
    op, tok1, tok2 = tokenOrList	

    # Handle special cases before doing the basic ones which are inorder
    # ops (value op value).
    if op == 'randomFrom:to:':
        # tok1 and tok2 may be math expressions.
        return "pickRandom(" + mathExpr(tok1) + ", " + mathExpr(tok2) + ")"
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
        return op2Func[tok1] + mathExpr(tok2) + ")"
    elif op == "getAttribute:of:":
        return getAttributeOf(tok1, tok2)
    else:
        assert op in ('+', '-', '*', '/', '%')

    resStr = "(" + mathExpr(tok1)
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
    resStr += mathExpr(tok2) + ")"
    return resStr


def getAttributeOf(tok1, tok2):
    """Return code to handle the various getAttributeOf calls
    from the sensing block.
    """
    mapping = { 'x position': 'xPositionOf',
                'y position': 'yPositionOf',
                'direction': 'directionOf',
                'costume #': 'costumeNumberOf',
                'costume name': 'costumeNameOf',   # TODO: implement this.
                'size': 'sizeOf',
                }
    if tok1 in mapping:
        return mapping[tok1] + '("' + tok2 + '")'
    elif tok1 ==  'backdrop name':
        return 'backdropName()'
    else:   # volumeOf, backdropNumberOf
        return 'NOTIMPLEMENTED()'

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

    # Generate callback code, into the codeObj's cbCode string.
    # Add two blank lines before each method definition.
    cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                    "(Sequence s)\n"
    cbStr += block(level, tokens) + "\n"  # add blank line after defn.
    codeObj.addToCbCode(cbStr)


def whenSpriteClicked(codeObj, tokens):
    """Generate code to handle the whenClicked block.
    All code in tokens goes into a callback.
    """
    scriptNum = codeObj.getNextScriptId()
    # Build a name like whenSpriteClickedCb0 
    cbName = 'whenSpriteClickedCb' + str(scriptNum)

    # Code in the constructor is always level 2.
    codeObj.addToCode(genIndent(2) + 'whenSpriteClicked("' + cbName + '");\n')

    level = 1    # all callbacks are at level 1.

    # Generate callback code, into the codeObj's cbCode string.
    # Add two blank lines before each method definition.
    cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
                    "(Sequence s)\n"
    cbStr += block(level, tokens) + "\n"  # add blank line after defn.
    codeObj.addToCbCode(cbStr)


def whenSpriteCloned(codeObj, tokens):
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
    cbStr += block(1, tokens) + "\n"  # add blank line after defn.
    codeObj.addToCbCode(cbStr)

    # Generate a copy constructor too.
    cbStr = "\n\n" + genIndent(1) + "// copy constructor, required for cloning\n"
    cbStr += genIndent(1) + "public " + spriteName + "(" + \
             spriteName + " other, int x, int y) {\n"
    cbStr += genIndent(2) + "super(other, x, y);\n"
    cbStr += genIndent(2) + "// add code here to copy any instance variables'\n"
    cbStr += genIndent(2) + "// values from other to this.\n"
    cbStr += genIndent(1) + "}\n\n"
    codeObj.addToCbCode(cbStr)


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

    # Generate callback code, into the codeObj's cbCode string.
    # Add two blank lines before each method definition.
    cbStr = "\n\n" + genIndent(level) + "public void " + cbName + \
            "(Sequence s)\n"
    cbStr += block(level, tokens) + "\n"  # add blank line after defn.

    codeObj.addToCbCode(cbStr)


def whenIReceive(codeObj, message, tokens):
    """Generate code to handle the whenIReceive block.  message is
    the message to wait for, and tokens is the list of stmts to be put
    into a callback to be called when that message is received.
    """
    scriptNum = codeObj.getNextScriptId()

    # Build a name like whenIReceiveMessage1Cb0
    # TODO: convert key to a legal java identifier: no spaces, etc.

    # This code converts the first letter to uppercase only.
    messageId = message[0].upper() + message[1:]
    cbName = 'whenIReceive' + messageId + 'Cb' + str(scriptNum)

    # Code in the constructor is always level 2.
    codeObj.addToCode(genIndent(2) + 'whenRecvMessage("' +
                      message + '", "' + cbName + '");\n')

    # Generate callback code, into the codeObj's cbCode string.
    # Add two blank lines before each method definition.
    # All cb code is at level 1
    cbStr = "\n\n" + genIndent(1) + "public void " + cbName + "(Sequence s)\n"
    cbStr += block(1, tokens) + "\n"  # add blank line after defn.
    codeObj.addToCbCode(cbStr) 


def doForever(level, tokens):
    """Generate doForever code.  tokens is a list of comments.
    forever loop is turned into a while (true) loop, with the last
    operation being a yield(s) call.
    """
    retStr = genIndent(level) + "while (true)\t\t// forever loop\n"
    retStr += genIndent(level) + "{\n"
    retStr += stmts(level, tokens[1])
    retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
    return retStr + genIndent(level) + "}\n"


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


def motion0Arg(level, tokens):
    """Generate code to handle Motion blocks with 0 arguments"""
    assert len(tokens) == 1
    cmd = tokens[0]
    if cmd == "bounceOffEdge":
        return genIndent(level) + "ifOnEdgeBounce();\n"
    else:
        raise ValueError(cmd)

def motion1Arg(level, tokens):
    """Generate code to handle Motion blocks with 1 argument:
    forward:, turnLeft:, turnRight:, etc."""
    assert len(tokens) == 2
    cmd, arg = tokens
    if cmd == "forward:":
        return genIndent(level) + "move(" + mathExpr(arg) + ");\n"
    elif cmd == "turnRight:":
        return genIndent(level) + "turnRightDegrees((int) " + mathExpr(arg) + ");\n"
        # TODO: be nice to get rid of the (int)
        # but would require knowing if mathExpr is
        # returning an int type or float...
        # OR, add turnRightDegrees(float) and convert it.
    elif cmd == "turnLeft:":
        return genIndent(level) + "turnLeftDegrees((int) " + mathExpr(arg) + ");\n"
        # TODO: be nice to get rid of the (int)
        # but would require knowing if mathExpr is
        # returning an int type or float...
    elif cmd == "heading:":
        return genIndent(level) + "pointInDirection((int) " + mathExpr(arg) + ");\n"
    elif cmd == "gotoSpriteOrMouse:":
        if arg == "_mouse_":
            return genIndent(level) + "goToMouse();\n"
        else:
            return genIndent(level) + "// goToSprite(): not implemented yet.\n"
        # TODO: Looks like there is something new: gotoRandomPosition()
    elif cmd == "changeXposBy:":
        return genIndent(level) + "changeXBy((int) " + mathExpr(arg) + ");\n"
    elif cmd == "xpos:":
        return genIndent(level) + "setXTo((int) " + mathExpr(arg) + ");\n" 
    elif cmd == "changeYposBy:":
        return genIndent(level) + "changeYBy((int) " + mathExpr(arg) + ");\n"
    elif cmd == "ypos:":
        return genIndent(level) + "setYTo((int) " + mathExpr(arg) + ");\n"
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
        return genIndent(level) + "goTo((int) " + mathExpr(arg1) + \
               ", (int) " + mathExpr(arg2) + ");\n"
    else:
        raise ValueError(cmd)

def pointTowards(level, tokens):
    """Generate code to turn the sprite to point to something.
    """
    cmd, arg1 = tokens
    if arg1 == '_mouse_':
        return genIndent(level) + "pointTowardMouse();\n"
    else:
        # TODO
        return "NOT IMPLEMENTED YET"

def sayForSecs(level, tokens):
    """Generate code to handle say <str> for <n> seconds.
    """
    cmd, arg1, arg2 = tokens
    assert cmd == 'say:duration:elapsed:from:'
    return genIndent(level) + "sayForNSeconds(s, " + strExpr(arg1) + ", (double)" + \
           mathExpr(arg2) + ");\n"

def say(level, tokens):
    """Generate code to handle say <str>.
    """
    cmd, arg1 = tokens
    assert cmd == "say:"
    return genIndent(level) + "say(" + strExpr(arg1) + ");\n"

def show(level, tokens):
    """Generate code for the show block.
    """
    assert tokens[0] == "show"
    return genIndent(level) + "show();\n"

def hide(level, tokens):
    """Generate code for the show block.
    """
    assert tokens[0] == "hide"
    return genIndent(level) + "hide();\n"

def switchCostumeTo(level, tokens):
    """Generate code for the switch costume block.
    """
    cmd, arg1 = tokens
    assert cmd == "lookLike:"
    # TODO:
    # It seems like you can put a math expression as arg1 and scratch
    # interprets that as the # of the costume to switch to...
    # We aren't handling that now.
    return genIndent(level) + "switchToCostume(" + strExpr(arg1) + ");\n"

def nextCostume(level, tokens):
    """Generate code for the next costume block.
    """
    assert tokens[0] == "nextCostume"
    return genIndent(level) + "nextCostume();\n"

def switchBackdropTo(level, tokens):
    """Generate code to switch the backdrop.
    """
    cmd, arg1 = tokens
    assert cmd == "startScene"
    return genIndent(level) + "getWorld().switchBackdropTo(" + strExpr(arg1) + ");\n"

def nextBackdrop(level, tokens):
    """Generate code to switch to the next backdrop.
    """
    return genIndent(level) + "getWorld().nextBackdrop();\n"

def changeSizeBy(level, tokens):
    """Generate code to change the size of the sprite
    """
    cmd, arg1 = tokens
    assert cmd == "changeSizeBy"
    return genIndent(level) + "changeSizeBy((int) " + mathExpr(arg1) + ");\n"

def setSizeTo(level, tokens):
    """Generate code to change the size of the sprite to a certain percentage
    """
    cmd, arg1 = tokens
    assert cmd == "setSizeTo:"
    return genIndent(level) + "setSizeTo((int) " + mathExpr(arg1) + ");\n"

def goToFront(level, tokens):
    """Generate code to move the sprite to the front
    """
    assert tokens[0] == "comeToFront"
    return genIndent(level) + "goToFront();\n"

def goBackNLayers(level, tokens):
    """Generate code to move the sprite back 1 layer in the paint order
    """
    cmd, arg1 = tokens
    assert cmd == "goBackByLayers:"
    return genIndent(level) + "goBackNLayers((int) " + mathExpr(arg1) + ");\n"


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
        resStr += "java.awt.Color color = new java.awt.Color((int) " + mathExpr(arg) + ");\n"
        return resStr + genIndent(level) + "setPenColor(color);\n"
    elif cmd == "changePenHueBy:":
        return resStr + "changePenColorBy(" + mathExpr(arg) + ");\n"
    elif cmd == "setPenHueTo:":
        return resStr + "setPenColor(" + mathExpr(arg) + ");\n"
    else:
        raise ValueError(cmd)

def getTypeAndLocalGlobal(varTok):
    """Look up the token representing a variable name in the varTypes
    dictionary.  If it is found, return the type and whether it
    is a local variable or global.  Global is known if it is found
    in GLOBAL object.  Raise ValueError if it isn't found
    in the dictionary.
    """
    global spriteName
    
    isGlobal = False
    varType = varTypes.get((spriteName, varTok))
    if varType is None:
        varType = varTypes.get(("GLOBAL", varTok))
        if varType is None:
            raise ValueError("Sprite " + spriteName + " variable " +
                         varTok + " unknown.")
        else:
            isGlobal = True
    return (varType, isGlobal)

def setVariable(level, tokens):
    """Set a variable's value from within the code.
    Generate code like this:
    var.set(value)
    tokens is: ["setVar:to:", "varName", [expression]]

    The variable may be sprite-specific or global.  We have to check
    both dictionaries to figure it out.
    """

    global spriteName, worldClassName
    global varTypes

    varType, isGlobal = getTypeAndLocalGlobal(tokens[1])
    if varType == 'Boolean':
        val = boolExpr(tokens[2])
    elif varType in ('Int', 'Double'):
        val = mathExpr(tokens[2])
    else:
        val = strExpr(tokens[2])

    if isGlobal:
        # Something like: ((AWorld)getWorld()).counter.set(0);
        return genIndent(level) + "((%s)getWorld()).%s.set(%s);\n" % \
               (worldClassName, tokens[1], val)
    else:
        return genIndent(level) + tokens[1] + ".set(" + val + ");\n"


def readVariable(varname):
    """Get a variable's value from within the code.
    Generate code like this:
    var.get() or
    ((ScratchWorld)getWorld()).varname.get()

    The variable may be sprite-specific or global.  We have to check
    both dictionaries to figure it out.
    """

    global spriteName, worldClassName
    global varTypes

    varType, isGlobal = getTypeAndLocalGlobal(varname)
    if isGlobal:
        # Something like: ((AWorld)getWorld()).counter.get();
        return "((%s)getWorld()).%s.get()" % (worldClassName, varname)
    else:
        return varname + ".get()"


def hideVariable(level, tokens):
    """Generate code to hide a variable.
    """
    varType, isGlobal = getTypeAndLocalGlobal(tokens[1])
    if isGlobal:
        # Something like: ((AWorld)getWorld()).counter.hide();
        return genIndent(level) + "((%s)getWorld()).%s.hide();\n" % \
               (worldClassName, tokens[1])
    else:
        return genIndent(level) + tokens[1] + ".hide();\n"


def showVariable(level, tokens):
    """Generate code to hide a variable.
    """
    varType, isGlobal = getTypeAndLocalGlobal(tokens[1])
    if isGlobal:
        # Something like: ((AWorld)getWorld()).counter.show();
        return genIndent(level) + "((%s)getWorld()).%s.show();\n" % \
               (worldClassName, tokens[1])
    else:
        return genIndent(level) + tokens[1] + ".show();\n"


def changeVarBy(level, tokens):
    """Generate code to change the value of a variable.
    Code will be like this:
    aVar.set(aVar.get() + 3);
    """
    varType, isGlobal = getTypeAndLocalGlobal(tokens[1])
    if isGlobal:
        # Something like:
        # ((AWorld)getWorld()).counter.set(((AWorld)getWorld()).counter.get() + 1);
        return genIndent(level) + \
               "((%s)getWorld()).%s.set(((%s)getWorld()).%s.get() + %s);\n" % \
               (worldClassName, tokens[1],
                worldClassName, tokens[1], mathExpr(tokens[2]))
    else:
        return genIndent(level) + tokens[1] + ".set(" + \
               tokens[1] + ".get() + " + mathExpr(tokens[2]) + ");\n"

def broadcast(level, tokens):
    """Generate code to handle sending a broacast message.
    """
    cmd, arg1 = tokens
    assert cmd == "broadcast:"
    return genIndent(level) + "broadcast( " + strExpr(arg1) + ");\n"


def broadcastAndWait(level, tokens):
    """Generate code to handle sending a broacast message and
    waiting until all the handlers have completed.
    """
    cmd, arg1 = tokens
    assert cmd == "doBroadcastAndWait"
    return genIndent(level) + "// TODO: broadcastAndWait() not implemented yet.);\n"


def doAsk(level, tokens):
    """Generate code to ask the user for input.  Returns the resulting String."""

    assert len(tokens) == 2 and tokens[0] == "doAsk"
    quest = tokens[1]
    return genIndent(level) + "String answer = askStringAndWait(" + \
           strExpr(quest) + ")\t\t// may want to replace variable\n"


def doWait(level, tokens):
    """Generate a wait call."""
    assert len(tokens) == 2 and tokens[0] == "wait:elapsed:from:"
    return genIndent(level) + "wait(s, " + mathExpr(tokens[1]) + ");\n"


def doRepeat(level, tokens):
    """Generate a repeat <n> times loop.
    """
    assert len(tokens) == 3 and tokens[0] == "doRepeat"

    retStr = genIndent(level) + "for (int i = 0; i < " + \
             mathExpr(tokens[1]) + "; i++)\n"
    retStr += genIndent(level) + "{\n"
    retStr += stmts(level, tokens[2])
    retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
    return retStr + genIndent(level) + "}\n"


def doWaitUntil(level, tokens):
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
    retStr += genIndent(level + 1) + "if (" + boolExpr(tokens[1]) + ")\n"
    retStr += genIndent(level + 2) + "break;\n"
    retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
    return retStr + genIndent(level) + "}\n"


def repeatUntil(level, tokens):
    """Generate doUntil code, which translates to this:
       while (! condition)
       {
           stmts
           yield(s);
       }
    """
    assert len(tokens) == 3 and tokens[0] == "doUntil"

    retStr =  genIndent(level) + "// repeat until code\n"
    retStr += genIndent(level) + "while (! " + boolExpr(tokens[1]) + ")\n"
    retStr += genIndent(level) + "{\n"
    retStr += stmts(level, tokens[2])
    retStr += genIndent(level + 1) + "yield(s);   // allow other sequences to run\n"
    return retStr + genIndent(level) + "}\n"


def stopScripts(level, tokens):
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


def createCloneOf(level, tokens):
    """Create a clone of the sprite itself or of the given sprite.
    """
    assert len(tokens) == 2 and tokens[0] == "createCloneOf"
    if tokens[1] == "_myself_":
        return genIndent(level) + "createCloneOfMyself();\n"

    return genIndent(level) + "createCloneOf(" + \
           'getWorld().getActorByName("' + tokens[1] + '"));\n'


def deleteThisClone(level, tokens):
    """Delete this sprite.
    """
    assert len(tokens) == 1 and tokens[0] == "deleteClone"
    return genIndent(level) + "deleteThisClone();\n"


def resetTimer(level, tokens):
    return genIndent(level) + "resetTimer();\n"


def genProcDefCode(codeObj, tokens):
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

    # Now, scanning through %? and words, which we'll drop for now.
    while idx < len(blockAndParamTypes):
        # TODO: rewrite this with str.find() or str.index().
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

    codeObj.addToCbCode(genIndent(1) + "private void " + blockName + "(")

    for i in range(len(paramTypes)):
        codeObj.addToCbCode(paramTypes[i] + " " + paramNames[i])
        # Add following ", " if not add end of list.
        if i < len(paramTypes) - 1:
            codeObj.addToCbCode(", ")

    codeObj.addToCbCode(")\n")
    codeObj.addToCbCode(block(1, code))
    codeObj.addToCbCode("\n")	# add blank line after function defn.
    return codeObj


def callABlock(level, tokens):
    """Generate a call to a custom-defined block.
    Format of tokens is: ["call", "blockToCall", param code]
    blockToCall has the param type specs in it: "blockToCall %n %s %b"
    We need to strip these out.
    """
    func2Call = tokens[1]
    firstPercent = func2Call.find("%")
    if firstPercent == -1:
        assert len(tokens) == 2    # just "call" and "blockToCall"
        return genIndent(level) + func2Call + "();\n"
    func2Call = func2Call[0:firstPercent]
    func2Call = func2Call.strip()	# remove trailing blanks.

    resStr = genIndent(level) + func2Call + "("
    for i in range(2, len(tokens) - 1):
        resStr += mathExpr(tokens[i]) + ", "
    resStr += mathExpr(tokens[-1]) + ");\n"
    return resStr


scratchStmt2genCode = {
    'doIf': doIf,
    'doIfElse': doIfElse,

    # Motion commands
    'forward:': motion1Arg,
    'turnLeft:': motion1Arg,
    'turnRight:': motion1Arg,
    'heading:': motion1Arg,
    'gotoX:y:': motion2Arg,
    'gotoSpriteOrMouse:': motion1Arg,
    'changeXposBy:': motion1Arg,
    'xpos:': motion1Arg,
    'changeYposBy:': motion1Arg,
    'ypos:': motion1Arg,
    'bounceOffEdge': motion0Arg,    # TODO
    'setRotationStyle': motion1Arg,
    'pointTowards:': pointTowards,

    # Looks commands
    'say:duration:elapsed:from:': sayForSecs,
    'say:': say,
    'show': show,
    'hide': hide,
    'lookLike:': switchCostumeTo,
    'nextCostume': nextCostume,
    'startScene': switchBackdropTo,
    'changeSizeBy': changeSizeBy,
    'setSizeTo:': setSizeTo,
    'comeToFront': goToFront,
    'goBackByLayers:': goBackNLayers,
    'nextScene': nextBackdrop,

    # Pen commands
    'clearPenTrails': pen0Arg,
    'stampCostume': pen0Arg,
    'putPenDown': pen0Arg,
    'putPenUp': pen0Arg,
    'penColor:': pen1Arg,
    'changePenHueBy:': pen1Arg,
    'setPenHueTo:': pen1Arg,

    # Data commands
    'setVar:to:': setVariable,
    'hideVariable:': hideVariable,
    'showVariable:': showVariable,
    'changeVar:by:': changeVarBy,

    # Events commands
    'broadcast:': broadcast,
    'doBroadcastAndWait': broadcastAndWait,

    # Control commands
    'doForever': doForever,
    'wait:elapsed:from:': doWait,
    'doRepeat': doRepeat,
    'doWaitUntil': doWaitUntil,
    'doUntil': repeatUntil,
    'stopScripts': stopScripts,
    'createCloneOf': createCloneOf,
    'deleteClone': deleteThisClone,

    # Sensing commands
    'doAsk': doAsk,
    'timerReset': resetTimer,

    # Blocks commands
    'call': callABlock,

    }

def convertSpriteToFileName(sprite):
    """Make the filename with all words from sprite capitalized and
    joined, with no spaces between."""
    words = sprite.split()
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

def genLoadCostumesCode(costumes, isBackdrop=False):
    """Generate code to load costumes from files for a sprite.
    """
    # print("genLoadCC: costumes ->" + str(costumes) + "<-")
    resStr = ""
    imagesDir = os.path.join(PROJECT_DIR, "images")
    for cos in costumes:
        # costume's filename is the baseLayerID (which is a small integer
        # (1, 2, 3, etc.)) plus ".png"
        fname = str(cos['baseLayerID']) + ".png"
        if isBackdrop:
            resStr += genIndent(2) + 'addBackdrop("' + fname + \
                      '", "' + cos['costumeName'] + '");\n'
        else:
            resStr += genIndent(2) + 'addCostume("' + fname + \
                      '", "' + cos['costumeName'] + '");\n'
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
    resStr += genIndent(2) + 'pointInDirection((int) ' + str(spr['direction']) + ');\n';
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


def genVariablesDefnCode(listOfVars, spriteName, allChildren):
    """Generate code to define instance variables for this sprite.
    The listOfVars is a list of dictionaries, one per variable (see below).
    The spriteName is the sprite we are generating "local" variables for.
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

    def deriveType(val):
        if isinstance(val, str):
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
    if spriteName == "Stage":
        initCode = "\n" + genIndent(2) + "// Variable initializations.\n"
    else:
        initCode =  "\n" + genIndent(1) + "public void addedToWorld(World world)\n"
        initCode += genIndent(1) + "{\n"
        initCode += genIndent(2) + "// Variable initializations.\n"

    for var in listOfVars:  # var is a dictionary.
        name = var['name']
        value = var['value']
        # return the varType and the value converted to a java equivalent
        # for that type. (e.g., False --> false)
        # varType is one of 'Boolean', 'Double', 'Int', 'String'
        value, varType = deriveType(value)

        for aDict in allChildren:
            if aDict.get('cmd') == 'getVar:' and \
               aDict.get('param') == name and \
               aDict.get('target') == spriteName:
                varInfo = aDict
                break
        else:
            raise ValueError("No variable definition dictionary found in script json")
        label = varInfo['label']
        x = varInfo['x']    # Not used at this time.
        y = varInfo['y']    # Not used at this time.
        visible = varInfo['visible']

        # Record this variable in the global variables dictionary.
        # We need this so we can generate code that calls the correct
        # functions to generate the correct type of results.
        # E.g., if a variable is boolean, we'll call boolExpr()
        # from setVariables(), not mathExpr().

        # If the spriteName is "GLOBAL" then it is a global variable.
        # However, we store global variable in the World, so we'll use
        # "GLOBAL" instead.
        if spriteName == "Stage":
            varTypes[("GLOBAL", name)] = varType
        else:
            varTypes[(spriteName, name)] = varType
        if debug:
            print("Adding entry for", spriteName, ",", name,
                  "to dict with value", varType)

        # Something like "Scratch.IntVar score; or ScratchWorld.IntVar score;"
        if spriteName == "Stage":
            # Code is going into the World
            defnCode += genIndent(1) + "ScratchWorld.%sVar %s;\n" % (varType, name)
            initCode += '%s%s = create%sVariable("%s", %s);\n' % \
                        (genIndent(2), name, varType, label, str(value))
        else:
            defnCode += genIndent(1) + "Scratch.%sVar %s;\n" % (varType, name)
            # Something like "score = createIntVariable((MyWorld) world, "score", 0);
            initCode += '%s%s = create%sVariable((%s) world, "%s", %s);\n' % \
                        (genIndent(2), name, varType, worldClassName, label, str(value))

        # initCode += genIndent(2) + name + " = create" + varType + \
        #            'Variable("' + label + '", ' + str(value) + ");\n"
        if not visible:
            initCode += genIndent(2) + name + ".hide();\n"

    # Add blank line after variable definitions.
    defnCode += "\n"
    # Add blank line after variable initializations.
    initCode += "\n"

    if spriteName != "Stage":
        # Close the addedToWorld() method definition.
        initCode += genIndent(1) + "}\n"
        
    return defnCode, initCode

          
def genScriptCode(script, scrName):
    """Generate code (and callback code) for the given script, which may be
    associated with a sprite or the main stage.
    """

    codeObj = CodeAndCb()	# Holds all the code that is generated.

    # Add a comment to each section of code indicating where
    # the code came from -- if we aren't generating code for a
    # custom block.
    if not (isinstance(script[0], list) and script[0][0] == 'procDef'):
        codeObj.code += genIndent(2) + "// Code from Script " + str(scrNum) + "\n"

    # script is a list of these: [[cmd] [arg] [arg]...]
    # The script starts with whenGreenFlag, whenSpriteClicked, etc. --
    # the "hat" blocks.
    if script[0] == ['whenGreenFlag']:
        whenFlagClicked(codeObj, script[1:])
    elif script[0] == ['whenCloned']:
        whenSpriteCloned(codeObj, script[1:])
    elif script[0] == ['whenClicked']:
        whenSpriteClicked(codeObj, script[1:])
    elif isinstance(script[0], list) and script[0][0] == 'whenKeyPressed':
        whenKeyPressed(codeObj, script[0][1], script[1:])
    elif isinstance(script[0], list) and script[0][0] == 'whenIReceive':
        whenIReceive(codeObj, script[0][1], script[1:])
    elif isinstance(script[0], list) and script[0][0] == 'procDef':
        # Defining a procedure in Scratch.
        genProcDefCode(codeObj, script)
    else:
        raise ValueError(script[0])


    # TODO: need to implement whenSwitchToBackdrop in
    # Scratch.java and add code here to handle it.
    # TODO: need to handle scripts for the stage, not a sprite.


    # TODO: filter out scripts that are "left over" -- don't start
    # with whenGreenFlag, etc.
    return codeObj


# ---------------------------------------------------------------------------
#                ----------------- main -------------------
# ---------------------------------------------------------------------------

usage = 'Usage: python3 s2g.py <scratchFile.sb2> <GreenfootProjDir>'

if len(sys.argv) != 3:
    print(usage)
    sys.exit(1)

SCRATCH_FILE = sys.argv[1].strip()
# Take off spaces and a possible trailing "/"
PROJECT_DIR = sys.argv[2].strip().rstrip("/")

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

# Unzip the .sb2 file into the project/scratch_code directory.
print("Unpacking Scratch download file.")
shutil.unpack_archive(SCRATCH_FILE, scratch_dir, "zip")

# Copy png image files to images dir.
imagesDir = os.path.join(PROJECT_DIR, "images")
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
        shutil.copy2(f, imagesDir)

# Convert svg images files to png files in the images dir.
files2Copy = glob.glob(os.path.join(scratch_dir, "*.svg"))
for f in files2Copy:
    # fname is just the file name -- all directories removed.
    fname = os.path.basename(f)
    dest = os.path.join(imagesDir, fname)
    dest = os.path.splitext(dest)[0] + ".png"  # remove extension and add .png
    execOrDie("convert -background None " + f + " " + dest,
              "convert svg file to png")


# TODO: move sounds files.


# Now, (finally!), open the project.json file and start processing it.
with open(os.path.join(scratch_dir, "project.json")) as data_file:
    data = json.load(data_file)

sprites = data['children']

# We'll need to write configuration "code" to the greenfoot.project file.  Store
# the lines to write out in this variable.
projectFileCode = ""

# Code to be written into the World.java file.
worldCtorCode = ""

# Determine the name of the ScratchWorld subclass.  This variable below
# is used in some code above to generate casts.  I know this is a very bad
# idea, but hey, what are you going to do...
# Take the last component of the PROJECT_DIR, remove all spaces, then add World
# to end.
worldClassName = os.path.basename(PROJECT_DIR).replace(" ", "") + "World"


# If there are global variables, they are defined in the outermost part
# of the json data, and more info about each is defined in objects labeled
# with "target": "Stage" in 'childen'.
# These need to be processed before we process any Sprite-specific code
# which may reference these global variables.
spriteName = "Stage"

worldDefnCode = ""
if 'variables' in data:
    worldDefnCode, initCode = genVariablesDefnCode(data['variables'], "Stage",
                                                   data['children'])
    worldCtorCode += initCode


# ---------------------------------------------------------------------------
# Start processing each sprite's info: scripts, costumes, variables, etc.
# ---------------------------------------------------------------------------
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
        worldCtorCode += genIndent(2) + 'addSprite("' + spriteName + \
                         '", ' + str(spr['scratchX']) + ', ' + \
                         str(spr['scratchY']) + ');\n'

        ctorCode = ""
        cbCode = []
        defnCode = ""		# code for defining Scratch variables.

        costumeCode = genLoadCostumesCode(spr['costumes'])
        if debug:
            print("CostumeCode is ", costumeCode)

	# Like location, direction, shown or hidden, etc.
        initSettingsCode = genInitialSettingsCode(spr)
        if debug:
            print("Initial Settings Code is ", initSettingsCode)

	# Generate a line to the project.greenfoot file to set the image
        # file, like this: 
        #     class.Sprite1.image=1.png
        projectFileCode += "class." + spriteName + ".image=" + \
                           str(spr['costumes'][0]['baseLayerID']) + ".png\n"

        ctorCode += costumeCode + initSettingsCode

      	# Handle variables defined for this sprite.  This has to be done
        # before handling the scripts, as the scripts may refer will the
        # variables.
        # Variable initializations have to be done in a method called
        # addedToWorld(), which is not necessary if no variable defns exist.
        addedToWorldCode = ""
        if 'variables' in spr:
            defnCode, addedToWorldCode = \
                      genVariablesDefnCode(spr['variables'], spriteName,
                                           data['children'])

        # The value of the 'scripts' key is the list of the scripts.  It may be a
        # list of 1 or of many.
        if 'scripts' in spr:
            for scrNum in range(len(spr['scripts'])):
                # items 0 and 1 in the sublist are the location on the
                # screen of the script. 
                # We don't care about that, obviously.  Item 2 is the actual code.
                script = spr['scripts'][scrNum][2]
                scrName = "Script" + str(scrNum)
                if debug:
                    print(scrName + ":", script)

                codeObj = genScriptCode(script, scrName)
                ctorCode += codeObj.code
                if codeObj.cbCode != "":
                    # The script generate callback code.
                    cbCode.append(codeObj.cbCode)

	# Open file with correct name and generate code into there.
        filename = os.path.join(PROJECT_DIR, convertSpriteToFileName(spriteName))
        print("Writing code to " + filename + ".")
        outFile = open(filename, "w")
        genHeaderCode(outFile, spriteName)

        outFile.write(defnCode)   # variable definitions

        genConstructorCode(outFile, spriteName, ctorCode)

        outFile.write(addedToWorldCode)

        for code in cbCode:
            outFile.write(code)

        outFile.write("}\n")
        outFile.close()

    else:
        if debug:
            print("\n----------- Not a sprite --------------");
            print(spr)



# --------- handle the Stage stuff --------------

# Because the stage can have script in it much like any sprite,
# we have to process it similarly.  So, lots of repeated code here
# from above -- although small parts are different enough.

spriteName = "Stage"

# Write out a line to the project.greenfoot file to indicate that this
# sprite is a subclass of the Scratch class.
projectFileCode += "class." + spriteName + ".superclass=Scratch\n"

# Create the special Stage sprite.
worldCtorCode += genIndent(2) + 'addSprite("' + spriteName + '", 0, 0);\n'

ctorCode = ""
cbCode = []

# The value of the 'scripts' key is the list of the scripts.  It may be
# a list of 1 or of many.
if 'scripts' in data:
    stageScrs = data['scripts']

    for scrNum in range(len(stageScrs)):
        # items 0 and 1 in the sublist are the location on the screen of the script.
        # We don't care about that, obviously.  Item 2 is the actual code.
        script = stageScrs[scrNum][2]
        scrName = "Script" + str(scrNum)
        if debug:
            print(scrName + ":", script)

        codeObj = genScriptCode(script, scrName)
        ctorCode += codeObj.code
        if codeObj.cbCode != "":
            # The script generate callback code.
            cbCode.append(codeObj.cbCode)


# Open file with correct name and generate code into there.
filename = os.path.join(PROJECT_DIR, spriteName + ".java")
print("Writing code to " + filename + ".")
outFile = open(filename, "w")
genHeaderCode(outFile, spriteName)

# Set the image for the Stage to nothing.  Backdrops are
# part of the World in Greenfoot, not the Stage object.
ctorCode = genIndent(2) + "setImage((GreenfootImage) null);\t\t// No image for the stage.\n" + ctorCode
genConstructorCode(outFile, spriteName, ctorCode)
for code in cbCode:
    outFile.write(code)

outFile.write("}\n")
outFile.close()


# ----------------------- Create subclass of World ------------------------------



#
# Now, to make the *World file -- a subclass of ScratchWorld.
#
filename = os.path.join(PROJECT_DIR, worldClassName + ".java")
outFile = open(filename, "w")
print("Writing code to " + filename + ".")

worldCode = genWorldHeaderCode(worldClassName)
worldCode += worldDefnCode
worldCode += genWorldCtorHeader(worldClassName)
worldCode += worldCtorCode

# Adding the backdrops will be done in the World constructor, not
# the stage constructor because backdrops (backgrounds) are a property
# of the World in Greenfoot.
addBackdropsCode = genLoadCostumesCode(data['costumes'], isBackdrop=True)
if debug:
    print("CostumeCode is ", addBackdropsCode)

addBackdropsCode += genIndent(2) + 'setBackdropNumber(' + \
                    str(data['currentCostumeIndex']) + ');\n'

worldCode += addBackdropsCode
worldCode += genIndent(1) + "}\n"
worldCode += "}\n"

outFile.write(worldCode)
outFile.close()

projectFileCode += "class." + worldClassName + ".superclass=ScratchWorld\n"
projectFileCode += "world.lastInstantiated=" + worldClassName + "\n"


# ---------------------------------------------------------------------------
# Now, add configuration information to the project.greenfoot file.

# Open in append mode, since we'll be writing lines to the end.
with open(os.path.join(os.path.join(PROJECT_DIR, "project.greenfoot")), "a") as projF:
    projF.write("class.Scratch.superclass=greenfoot.Actor\n")
    projF.write("class.ScratchWorld.superclass=greenfoot.World\n")
    projF.write(projectFileCode)


# ---------------------------------------------------------------------------
# END
# ---------------------------------------------------------------------------


# TODO: if a user runs s2g.py multiple times, it will add repeated lines to
# the project.greenfoot file.  That's bad, I imagine.
# One solution is to back up the project.greenfoot file before editing and
# then always use that when editing.


# NOTES:
# o Motion commands are done, except for glide.
# o Operators commands are done.
# o Looks commands are done.
# o Pen commands are done.
# o Events done, except broadcastAndWait and when loudness/timer/video > <n>
# o Control commands are done.
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


# What to do about mathExpr() vs. boolExpr() vs. strExpr().
# 
# Some Scratch blocks obviously require numbers, strings, or bools in
# certain places.  In that case, call the appropriate functions.
#   o what if you require a strExpr() but the value is an expression?
#


# Need a dispatcher to call the appropriate method for the operators:
# "join" --> call strExpr() on each param.
# "say" --> ditto
# "+", etc. --> call mathExpr() on each.
# etc.

# What if in strExpr(), the param is a method that returns an integer?
#  o how do we know? We are generating code, so we always get a string
#    back.  If the value generated by the code will be an int, then we should
#    wrap it in a String constructor...
#  o Implies we shoudl return not only a string of code to generate the
#    value, but also the expected type of value.

