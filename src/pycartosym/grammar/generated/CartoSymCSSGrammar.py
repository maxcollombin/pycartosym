# Generated from vendor/cartosymcss-grammar/CartoSymCSSGrammar.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,43,365,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,1,0,5,0,62,8,0,10,0,12,0,65,9,0,1,
        0,5,0,68,8,0,10,0,12,0,71,9,0,1,0,3,0,74,8,0,1,1,1,1,1,1,1,2,1,2,
        1,2,1,2,1,2,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,
        5,5,97,8,5,10,5,12,5,100,9,5,1,6,5,6,103,8,6,10,6,12,6,106,9,6,1,
        6,1,6,3,6,110,8,6,1,6,1,6,1,6,3,6,115,8,6,1,6,3,6,118,8,6,1,6,1,
        6,1,7,1,7,1,7,1,7,1,7,3,7,127,8,7,1,8,1,8,1,8,1,8,1,8,1,8,5,8,135,
        8,8,10,8,12,8,138,9,8,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,3,9,158,8,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,9,1,
        9,1,9,1,9,1,9,1,9,5,9,202,8,9,10,9,12,9,205,9,9,1,10,3,10,208,8,
        10,1,10,1,10,3,10,212,8,10,1,10,3,10,215,8,10,1,10,1,10,1,10,1,10,
        3,10,221,8,10,1,10,3,10,224,8,10,1,10,3,10,227,8,10,1,11,1,11,1,
        11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,5,11,240,8,11,10,11,12,
        11,243,9,11,1,12,1,12,1,12,1,12,1,13,1,13,1,13,1,13,1,13,1,13,5,
        13,255,8,13,10,13,12,13,258,9,13,1,14,1,14,3,14,262,8,14,1,15,1,
        15,1,15,1,15,1,15,1,15,1,15,1,15,1,15,5,15,273,8,15,10,15,12,15,
        276,9,15,1,16,1,16,1,16,1,16,1,16,3,16,283,8,16,1,17,1,17,3,17,287,
        8,17,1,17,3,17,290,8,17,1,18,1,18,1,19,1,19,3,19,296,8,19,1,19,1,
        19,1,19,3,19,301,8,19,1,19,3,19,304,8,19,1,20,1,20,1,20,1,20,1,20,
        1,20,5,20,312,8,20,10,20,12,20,315,9,20,1,21,1,21,1,21,1,21,1,21,
        1,22,1,22,1,22,1,22,1,22,1,22,5,22,328,8,22,10,22,12,22,331,9,22,
        1,23,1,23,1,24,1,24,1,25,1,25,1,26,1,26,1,27,1,27,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,1,28,3,28,
        358,8,28,1,29,1,29,1,29,3,29,363,8,29,1,29,0,8,10,16,18,22,26,30,
        40,44,30,0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,
        40,42,44,46,48,50,52,54,56,58,0,2,1,0,33,34,1,0,28,31,398,0,63,1,
        0,0,0,2,75,1,0,0,0,4,78,1,0,0,0,6,83,1,0,0,0,8,87,1,0,0,0,10,91,
        1,0,0,0,12,104,1,0,0,0,14,126,1,0,0,0,16,128,1,0,0,0,18,157,1,0,
        0,0,20,226,1,0,0,0,22,228,1,0,0,0,24,244,1,0,0,0,26,248,1,0,0,0,
        28,261,1,0,0,0,30,263,1,0,0,0,32,282,1,0,0,0,34,289,1,0,0,0,36,291,
        1,0,0,0,38,303,1,0,0,0,40,305,1,0,0,0,42,316,1,0,0,0,44,321,1,0,
        0,0,46,332,1,0,0,0,48,334,1,0,0,0,50,336,1,0,0,0,52,338,1,0,0,0,
        54,340,1,0,0,0,56,357,1,0,0,0,58,362,1,0,0,0,60,62,3,6,3,0,61,60,
        1,0,0,0,62,65,1,0,0,0,63,61,1,0,0,0,63,64,1,0,0,0,64,69,1,0,0,0,
        65,63,1,0,0,0,66,68,3,4,2,0,67,66,1,0,0,0,68,71,1,0,0,0,69,67,1,
        0,0,0,69,70,1,0,0,0,70,73,1,0,0,0,71,69,1,0,0,0,72,74,3,10,5,0,73,
        72,1,0,0,0,73,74,1,0,0,0,74,1,1,0,0,0,75,76,5,40,0,0,76,77,5,39,
        0,0,77,3,1,0,0,0,78,79,3,2,1,0,79,80,5,10,0,0,80,81,3,18,9,0,81,
        82,5,4,0,0,82,5,1,0,0,0,83,84,5,3,0,0,84,85,5,39,0,0,85,86,5,38,
        0,0,86,7,1,0,0,0,87,88,5,3,0,0,88,89,5,39,0,0,89,90,5,38,0,0,90,
        9,1,0,0,0,91,92,6,5,-1,0,92,93,3,12,6,0,93,98,1,0,0,0,94,95,10,1,
        0,0,95,97,3,12,6,0,96,94,1,0,0,0,97,100,1,0,0,0,98,96,1,0,0,0,98,
        99,1,0,0,0,99,11,1,0,0,0,100,98,1,0,0,0,101,103,3,14,7,0,102,101,
        1,0,0,0,103,106,1,0,0,0,104,102,1,0,0,0,104,105,1,0,0,0,105,107,
        1,0,0,0,106,104,1,0,0,0,107,109,5,1,0,0,108,110,3,8,4,0,109,108,
        1,0,0,0,109,110,1,0,0,0,110,114,1,0,0,0,111,112,3,26,13,0,112,113,
        5,4,0,0,113,115,1,0,0,0,114,111,1,0,0,0,114,115,1,0,0,0,115,117,
        1,0,0,0,116,118,3,10,5,0,117,116,1,0,0,0,117,118,1,0,0,0,118,119,
        1,0,0,0,119,120,5,2,0,0,120,13,1,0,0,0,121,127,5,39,0,0,122,123,
        5,5,0,0,123,124,3,18,9,0,124,125,5,6,0,0,125,127,1,0,0,0,126,121,
        1,0,0,0,126,122,1,0,0,0,127,15,1,0,0,0,128,129,6,8,-1,0,129,130,
        3,32,16,0,130,131,3,32,16,0,131,136,1,0,0,0,132,133,10,1,0,0,133,
        135,3,32,16,0,134,132,1,0,0,0,135,138,1,0,0,0,136,134,1,0,0,0,136,
        137,1,0,0,0,137,17,1,0,0,0,138,136,1,0,0,0,139,140,6,9,-1,0,140,
        158,3,32,16,0,141,158,3,36,18,0,142,158,3,42,21,0,143,158,3,38,19,
        0,144,158,3,20,10,0,145,146,5,7,0,0,146,147,3,18,9,0,147,148,5,8,
        0,0,148,158,1,0,0,0,149,150,3,48,24,0,150,151,3,18,9,11,151,158,
        1,0,0,0,152,153,3,46,23,0,153,154,3,18,9,6,154,158,1,0,0,0,155,158,
        3,16,8,0,156,158,3,2,1,0,157,139,1,0,0,0,157,141,1,0,0,0,157,142,
        1,0,0,0,157,143,1,0,0,0,157,144,1,0,0,0,157,145,1,0,0,0,157,149,
        1,0,0,0,157,152,1,0,0,0,157,155,1,0,0,0,157,156,1,0,0,0,158,203,
        1,0,0,0,159,160,10,12,0,0,160,161,3,50,25,0,161,162,3,18,9,13,162,
        202,1,0,0,0,163,164,10,10,0,0,164,165,3,52,26,0,165,166,3,18,9,11,
        166,202,1,0,0,0,167,168,10,9,0,0,168,169,3,54,27,0,169,170,3,18,
        9,10,170,202,1,0,0,0,171,172,10,8,0,0,172,173,3,56,28,0,173,174,
        3,18,9,9,174,202,1,0,0,0,175,176,10,7,0,0,176,177,3,58,29,0,177,
        178,3,18,9,0,178,179,5,26,0,0,179,180,3,18,9,8,180,202,1,0,0,0,181,
        182,10,5,0,0,182,183,5,26,0,0,183,202,3,18,9,6,184,185,10,4,0,0,
        185,186,5,27,0,0,186,202,3,18,9,5,187,188,10,3,0,0,188,189,5,24,
        0,0,189,190,3,18,9,0,190,191,5,25,0,0,191,192,3,18,9,4,192,202,1,
        0,0,0,193,194,10,19,0,0,194,195,5,3,0,0,195,202,5,39,0,0,196,197,
        10,13,0,0,197,198,5,5,0,0,198,199,3,34,17,0,199,200,5,6,0,0,200,
        202,1,0,0,0,201,159,1,0,0,0,201,163,1,0,0,0,201,167,1,0,0,0,201,
        171,1,0,0,0,201,175,1,0,0,0,201,181,1,0,0,0,201,184,1,0,0,0,201,
        187,1,0,0,0,201,193,1,0,0,0,201,196,1,0,0,0,202,205,1,0,0,0,203,
        201,1,0,0,0,203,204,1,0,0,0,204,19,1,0,0,0,205,203,1,0,0,0,206,208,
        5,39,0,0,207,206,1,0,0,0,207,208,1,0,0,0,208,209,1,0,0,0,209,211,
        5,1,0,0,210,212,3,30,15,0,211,210,1,0,0,0,211,212,1,0,0,0,212,214,
        1,0,0,0,213,215,5,4,0,0,214,213,1,0,0,0,214,215,1,0,0,0,215,216,
        1,0,0,0,216,227,5,2,0,0,217,218,5,39,0,0,218,220,5,7,0,0,219,221,
        3,30,15,0,220,219,1,0,0,0,220,221,1,0,0,0,221,223,1,0,0,0,222,224,
        5,4,0,0,223,222,1,0,0,0,223,224,1,0,0,0,224,225,1,0,0,0,225,227,
        5,8,0,0,226,207,1,0,0,0,226,217,1,0,0,0,227,21,1,0,0,0,228,229,6,
        11,-1,0,229,230,5,39,0,0,230,241,1,0,0,0,231,232,10,2,0,0,232,233,
        5,3,0,0,233,240,5,39,0,0,234,235,10,1,0,0,235,236,5,5,0,0,236,237,
        3,34,17,0,237,238,5,6,0,0,238,240,1,0,0,0,239,231,1,0,0,0,239,234,
        1,0,0,0,240,243,1,0,0,0,241,239,1,0,0,0,241,242,1,0,0,0,242,23,1,
        0,0,0,243,241,1,0,0,0,244,245,3,22,11,0,245,246,5,25,0,0,246,247,
        3,18,9,0,247,25,1,0,0,0,248,249,6,13,-1,0,249,250,3,24,12,0,250,
        256,1,0,0,0,251,252,10,1,0,0,252,253,5,4,0,0,253,255,3,24,12,0,254,
        251,1,0,0,0,255,258,1,0,0,0,256,254,1,0,0,0,256,257,1,0,0,0,257,
        27,1,0,0,0,258,256,1,0,0,0,259,262,3,24,12,0,260,262,3,18,9,0,261,
        259,1,0,0,0,261,260,1,0,0,0,262,29,1,0,0,0,263,264,6,15,-1,0,264,
        265,3,28,14,0,265,274,1,0,0,0,266,267,10,2,0,0,267,268,5,4,0,0,268,
        273,3,28,14,0,269,270,10,1,0,0,270,271,5,9,0,0,271,273,3,28,14,0,
        272,266,1,0,0,0,272,269,1,0,0,0,273,276,1,0,0,0,274,272,1,0,0,0,
        274,275,1,0,0,0,275,31,1,0,0,0,276,274,1,0,0,0,277,283,5,39,0,0,
        278,283,3,34,17,0,279,283,5,22,0,0,280,283,5,23,0,0,281,283,5,21,
        0,0,282,277,1,0,0,0,282,278,1,0,0,0,282,279,1,0,0,0,282,280,1,0,
        0,0,282,281,1,0,0,0,283,33,1,0,0,0,284,286,5,37,0,0,285,287,5,35,
        0,0,286,285,1,0,0,0,286,287,1,0,0,0,287,290,1,0,0,0,288,290,5,36,
        0,0,289,284,1,0,0,0,289,288,1,0,0,0,290,35,1,0,0,0,291,292,5,38,
        0,0,292,37,1,0,0,0,293,295,5,5,0,0,294,296,3,40,20,0,295,294,1,0,
        0,0,295,296,1,0,0,0,296,297,1,0,0,0,297,304,5,6,0,0,298,300,5,7,
        0,0,299,301,3,40,20,0,300,299,1,0,0,0,300,301,1,0,0,0,301,302,1,
        0,0,0,302,304,5,8,0,0,303,293,1,0,0,0,303,298,1,0,0,0,304,39,1,0,
        0,0,305,306,6,20,-1,0,306,307,3,18,9,0,307,313,1,0,0,0,308,309,10,
        1,0,0,309,310,5,9,0,0,310,312,3,18,9,0,311,308,1,0,0,0,312,315,1,
        0,0,0,313,311,1,0,0,0,313,314,1,0,0,0,314,41,1,0,0,0,315,313,1,0,
        0,0,316,317,5,39,0,0,317,318,5,7,0,0,318,319,3,44,22,0,319,320,5,
        8,0,0,320,43,1,0,0,0,321,322,6,22,-1,0,322,323,3,18,9,0,323,329,
        1,0,0,0,324,325,10,1,0,0,325,326,5,9,0,0,326,328,3,18,9,0,327,324,
        1,0,0,0,328,331,1,0,0,0,329,327,1,0,0,0,329,330,1,0,0,0,330,45,1,
        0,0,0,331,329,1,0,0,0,332,333,5,17,0,0,333,47,1,0,0,0,334,335,7,
        0,0,0,335,49,1,0,0,0,336,337,5,32,0,0,337,51,1,0,0,0,338,339,7,1,
        0,0,339,53,1,0,0,0,340,341,7,0,0,0,341,55,1,0,0,0,342,358,5,10,0,
        0,343,358,5,11,0,0,344,358,5,12,0,0,345,358,5,13,0,0,346,358,5,14,
        0,0,347,358,5,15,0,0,348,358,5,16,0,0,349,350,5,17,0,0,350,358,5,
        16,0,0,351,358,5,18,0,0,352,353,5,18,0,0,353,358,5,17,0,0,354,358,
        5,19,0,0,355,356,5,17,0,0,356,358,5,19,0,0,357,342,1,0,0,0,357,343,
        1,0,0,0,357,344,1,0,0,0,357,345,1,0,0,0,357,346,1,0,0,0,357,347,
        1,0,0,0,357,348,1,0,0,0,357,349,1,0,0,0,357,351,1,0,0,0,357,352,
        1,0,0,0,357,354,1,0,0,0,357,355,1,0,0,0,358,57,1,0,0,0,359,363,5,
        20,0,0,360,361,5,17,0,0,361,363,5,20,0,0,362,359,1,0,0,0,362,360,
        1,0,0,0,363,59,1,0,0,0,35,63,69,73,98,104,109,114,117,126,136,157,
        201,203,207,211,214,220,223,226,239,241,256,261,272,274,282,286,
        289,295,300,303,313,329,357,362
    ]

class CartoSymCSSGrammar ( Parser ):

    grammarFileName = "CartoSymCSSGrammar.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'{'", "'}'", "'.'", "';'", "'['", "']'", 
                     "'('", "')'", "','", "'='", "'<>'", "'<'", "'<='", 
                     "'>'", "'>='", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "'?'", "':'", "<INVALID>", "<INVALID>", 
                     "'*'", "'/'", "<INVALID>", "'%'", "'^'", "'-'", "'+'", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "'@'" ]

    symbolicNames = [ "<INVALID>", "LCBR", "RCBR", "DOT", "SEMI", "LSBR", 
                      "RSBR", "LPAR", "RPAR", "COMMA", "EQ", "NEQ", "LT", 
                      "LTEQ", "GT", "GTEQ", "IN", "NOT", "IS", "LIKE", "BETWEEN", 
                      "NULL", "TRUE", "FALSE", "QUESTION", "COLON", "AND", 
                      "OR", "MUL", "DIV", "IDIV", "MOD", "POW", "MINUS", 
                      "PLUS", "UNIT", "HEX_LITERAL", "NUMERIC_LITERAL", 
                      "CHARACTER_LITERAL", "IDENTIFIER", "AT_SIGN", "COMMENT", 
                      "LINE_COMMENT", "WS" ]

    RULE_styleSheet = 0
    RULE_variable = 1
    RULE_variableDef = 2
    RULE_metadata = 3
    RULE_stylingRuleName = 4
    RULE_stylingRuleList = 5
    RULE_stylingRule = 6
    RULE_selector = 7
    RULE_tuple = 8
    RULE_expression = 9
    RULE_expInstance = 10
    RULE_lhValue = 11
    RULE_propertyAssignment = 12
    RULE_propertyAssignmentList = 13
    RULE_propertyAssignmentInferred = 14
    RULE_propertyAssignmentInferredList = 15
    RULE_idOrConstant = 16
    RULE_expConstant = 17
    RULE_expString = 18
    RULE_expArray = 19
    RULE_arrayElements = 20
    RULE_expCall = 21
    RULE_arguments = 22
    RULE_unaryLogicalOperator = 23
    RULE_unaryArithmeticOperator = 24
    RULE_arithmeticOperatorExp = 25
    RULE_arithmeticOperatorMul = 26
    RULE_arithmeticOperatorAdd = 27
    RULE_relationalOperator = 28
    RULE_betweenOperator = 29

    ruleNames =  [ "styleSheet", "variable", "variableDef", "metadata", 
                   "stylingRuleName", "stylingRuleList", "stylingRule", 
                   "selector", "tuple", "expression", "expInstance", "lhValue", 
                   "propertyAssignment", "propertyAssignmentList", "propertyAssignmentInferred", 
                   "propertyAssignmentInferredList", "idOrConstant", "expConstant", 
                   "expString", "expArray", "arrayElements", "expCall", 
                   "arguments", "unaryLogicalOperator", "unaryArithmeticOperator", 
                   "arithmeticOperatorExp", "arithmeticOperatorMul", "arithmeticOperatorAdd", 
                   "relationalOperator", "betweenOperator" ]

    EOF = Token.EOF
    LCBR=1
    RCBR=2
    DOT=3
    SEMI=4
    LSBR=5
    RSBR=6
    LPAR=7
    RPAR=8
    COMMA=9
    EQ=10
    NEQ=11
    LT=12
    LTEQ=13
    GT=14
    GTEQ=15
    IN=16
    NOT=17
    IS=18
    LIKE=19
    BETWEEN=20
    NULL=21
    TRUE=22
    FALSE=23
    QUESTION=24
    COLON=25
    AND=26
    OR=27
    MUL=28
    DIV=29
    IDIV=30
    MOD=31
    POW=32
    MINUS=33
    PLUS=34
    UNIT=35
    HEX_LITERAL=36
    NUMERIC_LITERAL=37
    CHARACTER_LITERAL=38
    IDENTIFIER=39
    AT_SIGN=40
    COMMENT=41
    LINE_COMMENT=42
    WS=43

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class StyleSheetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def metadata(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.MetadataContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.MetadataContext,i)


        def variableDef(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.VariableDefContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.VariableDefContext,i)


        def stylingRuleList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.StylingRuleListContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_styleSheet

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStyleSheet" ):
                listener.enterStyleSheet(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStyleSheet" ):
                listener.exitStyleSheet(self)




    def styleSheet(self):

        localctx = CartoSymCSSGrammar.StyleSheetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_styleSheet)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 63
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==3:
                self.state = 60
                self.metadata()
                self.state = 65
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 69
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==40:
                self.state = 66
                self.variableDef()
                self.state = 71
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 73
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 549755813922) != 0):
                self.state = 72
                self.stylingRuleList(0)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VariableContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def AT_SIGN(self):
            return self.getToken(CartoSymCSSGrammar.AT_SIGN, 0)

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_variable

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVariable" ):
                listener.enterVariable(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVariable" ):
                listener.exitVariable(self)




    def variable(self):

        localctx = CartoSymCSSGrammar.VariableContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_variable)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 75
            self.match(CartoSymCSSGrammar.AT_SIGN)
            self.state = 76
            self.match(CartoSymCSSGrammar.IDENTIFIER)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VariableDefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def variable(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.VariableContext,0)


        def EQ(self):
            return self.getToken(CartoSymCSSGrammar.EQ, 0)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def SEMI(self):
            return self.getToken(CartoSymCSSGrammar.SEMI, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_variableDef

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVariableDef" ):
                listener.enterVariableDef(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVariableDef" ):
                listener.exitVariableDef(self)




    def variableDef(self):

        localctx = CartoSymCSSGrammar.VariableDefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_variableDef)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 78
            self.variable()
            self.state = 79
            self.match(CartoSymCSSGrammar.EQ)
            self.state = 80
            self.expression(0)
            self.state = 81
            self.match(CartoSymCSSGrammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MetadataContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DOT(self):
            return self.getToken(CartoSymCSSGrammar.DOT, 0)

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def CHARACTER_LITERAL(self):
            return self.getToken(CartoSymCSSGrammar.CHARACTER_LITERAL, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_metadata

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMetadata" ):
                listener.enterMetadata(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMetadata" ):
                listener.exitMetadata(self)




    def metadata(self):

        localctx = CartoSymCSSGrammar.MetadataContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_metadata)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 83
            self.match(CartoSymCSSGrammar.DOT)
            self.state = 84
            self.match(CartoSymCSSGrammar.IDENTIFIER)
            self.state = 85
            self.match(CartoSymCSSGrammar.CHARACTER_LITERAL)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StylingRuleNameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DOT(self):
            return self.getToken(CartoSymCSSGrammar.DOT, 0)

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def CHARACTER_LITERAL(self):
            return self.getToken(CartoSymCSSGrammar.CHARACTER_LITERAL, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_stylingRuleName

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStylingRuleName" ):
                listener.enterStylingRuleName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStylingRuleName" ):
                listener.exitStylingRuleName(self)




    def stylingRuleName(self):

        localctx = CartoSymCSSGrammar.StylingRuleNameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_stylingRuleName)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 87
            self.match(CartoSymCSSGrammar.DOT)
            self.state = 88
            self.match(CartoSymCSSGrammar.IDENTIFIER)
            self.state = 89
            self.match(CartoSymCSSGrammar.CHARACTER_LITERAL)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StylingRuleListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def stylingRule(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.StylingRuleContext,0)


        def stylingRuleList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.StylingRuleListContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_stylingRuleList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStylingRuleList" ):
                listener.enterStylingRuleList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStylingRuleList" ):
                listener.exitStylingRuleList(self)



    def stylingRuleList(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.StylingRuleListContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 10
        self.enterRecursionRule(localctx, 10, self.RULE_stylingRuleList, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 92
            self.stylingRule()
            self._ctx.stop = self._input.LT(-1)
            self.state = 98
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,3,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = CartoSymCSSGrammar.StylingRuleListContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_stylingRuleList)
                    self.state = 94
                    if not self.precpred(self._ctx, 1):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                    self.state = 95
                    self.stylingRule() 
                self.state = 100
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class StylingRuleContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LCBR(self):
            return self.getToken(CartoSymCSSGrammar.LCBR, 0)

        def RCBR(self):
            return self.getToken(CartoSymCSSGrammar.RCBR, 0)

        def selector(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.SelectorContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.SelectorContext,i)


        def stylingRuleName(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.StylingRuleNameContext,0)


        def propertyAssignmentList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentListContext,0)


        def SEMI(self):
            return self.getToken(CartoSymCSSGrammar.SEMI, 0)

        def stylingRuleList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.StylingRuleListContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_stylingRule

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStylingRule" ):
                listener.enterStylingRule(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStylingRule" ):
                listener.exitStylingRule(self)




    def stylingRule(self):

        localctx = CartoSymCSSGrammar.StylingRuleContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_stylingRule)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 104
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==5 or _la==39:
                self.state = 101
                self.selector()
                self.state = 106
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 107
            self.match(CartoSymCSSGrammar.LCBR)
            self.state = 109
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==3:
                self.state = 108
                self.stylingRuleName()


            self.state = 114
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                self.state = 111
                self.propertyAssignmentList(0)
                self.state = 112
                self.match(CartoSymCSSGrammar.SEMI)


            self.state = 117
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 549755813922) != 0):
                self.state = 116
                self.stylingRuleList(0)


            self.state = 119
            self.match(CartoSymCSSGrammar.RCBR)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SelectorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def LSBR(self):
            return self.getToken(CartoSymCSSGrammar.LSBR, 0)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def RSBR(self):
            return self.getToken(CartoSymCSSGrammar.RSBR, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_selector

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSelector" ):
                listener.enterSelector(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSelector" ):
                listener.exitSelector(self)




    def selector(self):

        localctx = CartoSymCSSGrammar.SelectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_selector)
        try:
            self.state = 126
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [39]:
                self.enterOuterAlt(localctx, 1)
                self.state = 121
                self.match(CartoSymCSSGrammar.IDENTIFIER)
                pass
            elif token in [5]:
                self.enterOuterAlt(localctx, 2)
                self.state = 122
                self.match(CartoSymCSSGrammar.LSBR)
                self.state = 123
                self.expression(0)
                self.state = 124
                self.match(CartoSymCSSGrammar.RSBR)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TupleContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def idOrConstant(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.IdOrConstantContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.IdOrConstantContext,i)


        def tuple_(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.TupleContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_tuple

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTuple" ):
                listener.enterTuple(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTuple" ):
                listener.exitTuple(self)



    def tuple_(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.TupleContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 16
        self.enterRecursionRule(localctx, 16, self.RULE_tuple, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 129
            self.idOrConstant()
            self.state = 130
            self.idOrConstant()
            self._ctx.stop = self._input.LT(-1)
            self.state = 136
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,9,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = CartoSymCSSGrammar.TupleContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_tuple)
                    self.state = 132
                    if not self.precpred(self._ctx, 1):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                    self.state = 133
                    self.idOrConstant() 
                self.state = 138
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,9,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expression

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class MulExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def arithmeticOperatorMul(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArithmeticOperatorMulContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMulExpr" ):
                listener.enterMulExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMulExpr" ):
                listener.exitMulExpr(self)


    class StringExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expString(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpStringContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStringExpr" ):
                listener.enterStringExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStringExpr" ):
                listener.exitStringExpr(self)


    class InstanceExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expInstance(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpInstanceContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInstanceExpr" ):
                listener.enterInstanceExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInstanceExpr" ):
                listener.exitInstanceExpr(self)


    class BetweenExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def betweenOperator(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.BetweenOperatorContext,0)

        def AND(self):
            return self.getToken(CartoSymCSSGrammar.AND, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBetweenExpr" ):
                listener.enterBetweenExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBetweenExpr" ):
                listener.exitBetweenExpr(self)


    class PowExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def arithmeticOperatorExp(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArithmeticOperatorExpContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPowExpr" ):
                listener.enterPowExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPowExpr" ):
                listener.exitPowExpr(self)


    class AddExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def arithmeticOperatorAdd(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArithmeticOperatorAddContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAddExpr" ):
                listener.enterAddExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAddExpr" ):
                listener.exitAddExpr(self)


    class RelationalExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def relationalOperator(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.RelationalOperatorContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelationalExpr" ):
                listener.enterRelationalExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelationalExpr" ):
                listener.exitRelationalExpr(self)


    class ConditionalExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def QUESTION(self):
            return self.getToken(CartoSymCSSGrammar.QUESTION, 0)
        def COLON(self):
            return self.getToken(CartoSymCSSGrammar.COLON, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConditionalExpr" ):
                listener.enterConditionalExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConditionalExpr" ):
                listener.exitConditionalExpr(self)


    class TupleExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def tuple_(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.TupleContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTupleExpr" ):
                listener.enterTupleExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTupleExpr" ):
                listener.exitTupleExpr(self)


    class IndexExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)

        def LSBR(self):
            return self.getToken(CartoSymCSSGrammar.LSBR, 0)
        def expConstant(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpConstantContext,0)

        def RSBR(self):
            return self.getToken(CartoSymCSSGrammar.RSBR, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIndexExpr" ):
                listener.enterIndexExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIndexExpr" ):
                listener.exitIndexExpr(self)


    class ArrayExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expArray(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpArrayContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArrayExpr" ):
                listener.enterArrayExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArrayExpr" ):
                listener.exitArrayExpr(self)


    class PrimaryExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def idOrConstant(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.IdOrConstantContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPrimaryExpr" ):
                listener.enterPrimaryExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPrimaryExpr" ):
                listener.exitPrimaryExpr(self)


    class CallExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expCall(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpCallContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterCallExpr" ):
                listener.enterCallExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitCallExpr" ):
                listener.exitCallExpr(self)


    class VariableExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def variable(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.VariableContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterVariableExpr" ):
                listener.enterVariableExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitVariableExpr" ):
                listener.exitVariableExpr(self)


    class ParenExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAR(self):
            return self.getToken(CartoSymCSSGrammar.LPAR, 0)
        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)

        def RPAR(self):
            return self.getToken(CartoSymCSSGrammar.RPAR, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParenExpr" ):
                listener.enterParenExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParenExpr" ):
                listener.exitParenExpr(self)


    class UnaryLogicalExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def unaryLogicalOperator(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.UnaryLogicalOperatorContext,0)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnaryLogicalExpr" ):
                listener.enterUnaryLogicalExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnaryLogicalExpr" ):
                listener.exitUnaryLogicalExpr(self)


    class MemberAccessExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)

        def DOT(self):
            return self.getToken(CartoSymCSSGrammar.DOT, 0)
        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMemberAccessExpr" ):
                listener.enterMemberAccessExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMemberAccessExpr" ):
                listener.exitMemberAccessExpr(self)


    class UnaryArithExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def unaryArithmeticOperator(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.UnaryArithmeticOperatorContext,0)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnaryArithExpr" ):
                listener.enterUnaryArithExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnaryArithExpr" ):
                listener.exitUnaryArithExpr(self)


    class LogicalExprContext(ExpressionContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a CartoSymCSSGrammar.ExpressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expression(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CartoSymCSSGrammar.ExpressionContext)
            else:
                return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,i)

        def AND(self):
            return self.getToken(CartoSymCSSGrammar.AND, 0)
        def OR(self):
            return self.getToken(CartoSymCSSGrammar.OR, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLogicalExpr" ):
                listener.enterLogicalExpr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLogicalExpr" ):
                listener.exitLogicalExpr(self)



    def expression(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.ExpressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 18
        self.enterRecursionRule(localctx, 18, self.RULE_expression, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 157
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,10,self._ctx)
            if la_ == 1:
                localctx = CartoSymCSSGrammar.PrimaryExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 140
                self.idOrConstant()
                pass

            elif la_ == 2:
                localctx = CartoSymCSSGrammar.StringExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 141
                self.expString()
                pass

            elif la_ == 3:
                localctx = CartoSymCSSGrammar.CallExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 142
                self.expCall()
                pass

            elif la_ == 4:
                localctx = CartoSymCSSGrammar.ArrayExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 143
                self.expArray()
                pass

            elif la_ == 5:
                localctx = CartoSymCSSGrammar.InstanceExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 144
                self.expInstance()
                pass

            elif la_ == 6:
                localctx = CartoSymCSSGrammar.ParenExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 145
                self.match(CartoSymCSSGrammar.LPAR)
                self.state = 146
                self.expression(0)
                self.state = 147
                self.match(CartoSymCSSGrammar.RPAR)
                pass

            elif la_ == 7:
                localctx = CartoSymCSSGrammar.UnaryArithExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 149
                self.unaryArithmeticOperator()
                self.state = 150
                self.expression(11)
                pass

            elif la_ == 8:
                localctx = CartoSymCSSGrammar.UnaryLogicalExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 152
                self.unaryLogicalOperator()
                self.state = 153
                self.expression(6)
                pass

            elif la_ == 9:
                localctx = CartoSymCSSGrammar.TupleExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 155
                self.tuple_(0)
                pass

            elif la_ == 10:
                localctx = CartoSymCSSGrammar.VariableExprContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 156
                self.variable()
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 203
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,12,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 201
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,11,self._ctx)
                    if la_ == 1:
                        localctx = CartoSymCSSGrammar.PowExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 159
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 12)")
                        self.state = 160
                        self.arithmeticOperatorExp()
                        self.state = 161
                        self.expression(13)
                        pass

                    elif la_ == 2:
                        localctx = CartoSymCSSGrammar.MulExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 163
                        if not self.precpred(self._ctx, 10):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 10)")
                        self.state = 164
                        self.arithmeticOperatorMul()
                        self.state = 165
                        self.expression(11)
                        pass

                    elif la_ == 3:
                        localctx = CartoSymCSSGrammar.AddExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 167
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 9)")
                        self.state = 168
                        self.arithmeticOperatorAdd()
                        self.state = 169
                        self.expression(10)
                        pass

                    elif la_ == 4:
                        localctx = CartoSymCSSGrammar.RelationalExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 171
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 8)")
                        self.state = 172
                        self.relationalOperator()
                        self.state = 173
                        self.expression(9)
                        pass

                    elif la_ == 5:
                        localctx = CartoSymCSSGrammar.BetweenExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 175
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 176
                        self.betweenOperator()
                        self.state = 177
                        self.expression(0)
                        self.state = 178
                        self.match(CartoSymCSSGrammar.AND)
                        self.state = 179
                        self.expression(8)
                        pass

                    elif la_ == 6:
                        localctx = CartoSymCSSGrammar.LogicalExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 181
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 182
                        self.match(CartoSymCSSGrammar.AND)
                        self.state = 183
                        self.expression(6)
                        pass

                    elif la_ == 7:
                        localctx = CartoSymCSSGrammar.LogicalExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 184
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 185
                        self.match(CartoSymCSSGrammar.OR)
                        self.state = 186
                        self.expression(5)
                        pass

                    elif la_ == 8:
                        localctx = CartoSymCSSGrammar.ConditionalExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 187
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 188
                        self.match(CartoSymCSSGrammar.QUESTION)
                        self.state = 189
                        self.expression(0)
                        self.state = 190
                        self.match(CartoSymCSSGrammar.COLON)
                        self.state = 191
                        self.expression(4)
                        pass

                    elif la_ == 9:
                        localctx = CartoSymCSSGrammar.MemberAccessExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 193
                        if not self.precpred(self._ctx, 19):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 19)")
                        self.state = 194
                        self.match(CartoSymCSSGrammar.DOT)
                        self.state = 195
                        self.match(CartoSymCSSGrammar.IDENTIFIER)
                        pass

                    elif la_ == 10:
                        localctx = CartoSymCSSGrammar.IndexExprContext(self, CartoSymCSSGrammar.ExpressionContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expression)
                        self.state = 196
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 13)")
                        self.state = 197
                        self.match(CartoSymCSSGrammar.LSBR)
                        self.state = 198
                        self.expConstant()
                        self.state = 199
                        self.match(CartoSymCSSGrammar.RSBR)
                        pass

             
                self.state = 205
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,12,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ExpInstanceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LCBR(self):
            return self.getToken(CartoSymCSSGrammar.LCBR, 0)

        def RCBR(self):
            return self.getToken(CartoSymCSSGrammar.RCBR, 0)

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def propertyAssignmentInferredList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentInferredListContext,0)


        def SEMI(self):
            return self.getToken(CartoSymCSSGrammar.SEMI, 0)

        def LPAR(self):
            return self.getToken(CartoSymCSSGrammar.LPAR, 0)

        def RPAR(self):
            return self.getToken(CartoSymCSSGrammar.RPAR, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expInstance

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpInstance" ):
                listener.enterExpInstance(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpInstance" ):
                listener.exitExpInstance(self)




    def expInstance(self):

        localctx = CartoSymCSSGrammar.ExpInstanceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_expInstance)
        self._la = 0 # Token type
        try:
            self.state = 226
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,18,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 207
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==39:
                    self.state = 206
                    self.match(CartoSymCSSGrammar.IDENTIFIER)


                self.state = 209
                self.match(CartoSymCSSGrammar.LCBR)
                self.state = 211
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2156088393890) != 0):
                    self.state = 210
                    self.propertyAssignmentInferredList(0)


                self.state = 214
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 213
                    self.match(CartoSymCSSGrammar.SEMI)


                self.state = 216
                self.match(CartoSymCSSGrammar.RCBR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 217
                self.match(CartoSymCSSGrammar.IDENTIFIER)
                self.state = 218
                self.match(CartoSymCSSGrammar.LPAR)
                self.state = 220
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2156088393890) != 0):
                    self.state = 219
                    self.propertyAssignmentInferredList(0)


                self.state = 223
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==4:
                    self.state = 222
                    self.match(CartoSymCSSGrammar.SEMI)


                self.state = 225
                self.match(CartoSymCSSGrammar.RPAR)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LhValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def lhValue(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.LhValueContext,0)


        def DOT(self):
            return self.getToken(CartoSymCSSGrammar.DOT, 0)

        def LSBR(self):
            return self.getToken(CartoSymCSSGrammar.LSBR, 0)

        def expConstant(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpConstantContext,0)


        def RSBR(self):
            return self.getToken(CartoSymCSSGrammar.RSBR, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_lhValue

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLhValue" ):
                listener.enterLhValue(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLhValue" ):
                listener.exitLhValue(self)



    def lhValue(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.LhValueContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 22
        self.enterRecursionRule(localctx, 22, self.RULE_lhValue, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 229
            self.match(CartoSymCSSGrammar.IDENTIFIER)
            self._ctx.stop = self._input.LT(-1)
            self.state = 241
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,20,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 239
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,19,self._ctx)
                    if la_ == 1:
                        localctx = CartoSymCSSGrammar.LhValueContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_lhValue)
                        self.state = 231
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 232
                        self.match(CartoSymCSSGrammar.DOT)
                        self.state = 233
                        self.match(CartoSymCSSGrammar.IDENTIFIER)
                        pass

                    elif la_ == 2:
                        localctx = CartoSymCSSGrammar.LhValueContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_lhValue)
                        self.state = 234
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 235
                        self.match(CartoSymCSSGrammar.LSBR)
                        self.state = 236
                        self.expConstant()
                        self.state = 237
                        self.match(CartoSymCSSGrammar.RSBR)
                        pass

             
                self.state = 243
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,20,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class PropertyAssignmentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def lhValue(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.LhValueContext,0)


        def COLON(self):
            return self.getToken(CartoSymCSSGrammar.COLON, 0)

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_propertyAssignment

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyAssignment" ):
                listener.enterPropertyAssignment(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyAssignment" ):
                listener.exitPropertyAssignment(self)




    def propertyAssignment(self):

        localctx = CartoSymCSSGrammar.PropertyAssignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_propertyAssignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 244
            self.lhValue(0)
            self.state = 245
            self.match(CartoSymCSSGrammar.COLON)
            self.state = 246
            self.expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertyAssignmentListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyAssignment(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentContext,0)


        def propertyAssignmentList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentListContext,0)


        def SEMI(self):
            return self.getToken(CartoSymCSSGrammar.SEMI, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_propertyAssignmentList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyAssignmentList" ):
                listener.enterPropertyAssignmentList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyAssignmentList" ):
                listener.exitPropertyAssignmentList(self)



    def propertyAssignmentList(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.PropertyAssignmentListContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 26
        self.enterRecursionRule(localctx, 26, self.RULE_propertyAssignmentList, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 249
            self.propertyAssignment()
            self._ctx.stop = self._input.LT(-1)
            self.state = 256
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,21,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = CartoSymCSSGrammar.PropertyAssignmentListContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_propertyAssignmentList)
                    self.state = 251
                    if not self.precpred(self._ctx, 1):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                    self.state = 252
                    self.match(CartoSymCSSGrammar.SEMI)
                    self.state = 253
                    self.propertyAssignment() 
                self.state = 258
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,21,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class PropertyAssignmentInferredContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyAssignment(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentContext,0)


        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_propertyAssignmentInferred

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyAssignmentInferred" ):
                listener.enterPropertyAssignmentInferred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyAssignmentInferred" ):
                listener.exitPropertyAssignmentInferred(self)




    def propertyAssignmentInferred(self):

        localctx = CartoSymCSSGrammar.PropertyAssignmentInferredContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_propertyAssignmentInferred)
        try:
            self.state = 261
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,22,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 259
                self.propertyAssignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 260
                self.expression(0)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PropertyAssignmentInferredListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def propertyAssignmentInferred(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentInferredContext,0)


        def propertyAssignmentInferredList(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.PropertyAssignmentInferredListContext,0)


        def SEMI(self):
            return self.getToken(CartoSymCSSGrammar.SEMI, 0)

        def COMMA(self):
            return self.getToken(CartoSymCSSGrammar.COMMA, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_propertyAssignmentInferredList

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPropertyAssignmentInferredList" ):
                listener.enterPropertyAssignmentInferredList(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPropertyAssignmentInferredList" ):
                listener.exitPropertyAssignmentInferredList(self)



    def propertyAssignmentInferredList(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.PropertyAssignmentInferredListContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 30
        self.enterRecursionRule(localctx, 30, self.RULE_propertyAssignmentInferredList, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 264
            self.propertyAssignmentInferred()
            self._ctx.stop = self._input.LT(-1)
            self.state = 274
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,24,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 272
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,23,self._ctx)
                    if la_ == 1:
                        localctx = CartoSymCSSGrammar.PropertyAssignmentInferredListContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_propertyAssignmentInferredList)
                        self.state = 266
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
                        self.state = 267
                        self.match(CartoSymCSSGrammar.SEMI)
                        self.state = 268
                        self.propertyAssignmentInferred()
                        pass

                    elif la_ == 2:
                        localctx = CartoSymCSSGrammar.PropertyAssignmentInferredListContext(self, _parentctx, _parentState)
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_propertyAssignmentInferredList)
                        self.state = 269
                        if not self.precpred(self._ctx, 1):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                        self.state = 270
                        self.match(CartoSymCSSGrammar.COMMA)
                        self.state = 271
                        self.propertyAssignmentInferred()
                        pass

             
                self.state = 276
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,24,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class IdOrConstantContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def expConstant(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpConstantContext,0)


        def TRUE(self):
            return self.getToken(CartoSymCSSGrammar.TRUE, 0)

        def FALSE(self):
            return self.getToken(CartoSymCSSGrammar.FALSE, 0)

        def NULL(self):
            return self.getToken(CartoSymCSSGrammar.NULL, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_idOrConstant

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterIdOrConstant" ):
                listener.enterIdOrConstant(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitIdOrConstant" ):
                listener.exitIdOrConstant(self)




    def idOrConstant(self):

        localctx = CartoSymCSSGrammar.IdOrConstantContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_idOrConstant)
        try:
            self.state = 282
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [39]:
                self.enterOuterAlt(localctx, 1)
                self.state = 277
                self.match(CartoSymCSSGrammar.IDENTIFIER)
                pass
            elif token in [36, 37]:
                self.enterOuterAlt(localctx, 2)
                self.state = 278
                self.expConstant()
                pass
            elif token in [22]:
                self.enterOuterAlt(localctx, 3)
                self.state = 279
                self.match(CartoSymCSSGrammar.TRUE)
                pass
            elif token in [23]:
                self.enterOuterAlt(localctx, 4)
                self.state = 280
                self.match(CartoSymCSSGrammar.FALSE)
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 5)
                self.state = 281
                self.match(CartoSymCSSGrammar.NULL)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpConstantContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMERIC_LITERAL(self):
            return self.getToken(CartoSymCSSGrammar.NUMERIC_LITERAL, 0)

        def UNIT(self):
            return self.getToken(CartoSymCSSGrammar.UNIT, 0)

        def HEX_LITERAL(self):
            return self.getToken(CartoSymCSSGrammar.HEX_LITERAL, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expConstant

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpConstant" ):
                listener.enterExpConstant(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpConstant" ):
                listener.exitExpConstant(self)




    def expConstant(self):

        localctx = CartoSymCSSGrammar.ExpConstantContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_expConstant)
        try:
            self.state = 289
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [37]:
                self.enterOuterAlt(localctx, 1)
                self.state = 284
                self.match(CartoSymCSSGrammar.NUMERIC_LITERAL)
                self.state = 286
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,26,self._ctx)
                if la_ == 1:
                    self.state = 285
                    self.match(CartoSymCSSGrammar.UNIT)


                pass
            elif token in [36]:
                self.enterOuterAlt(localctx, 2)
                self.state = 288
                self.match(CartoSymCSSGrammar.HEX_LITERAL)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpStringContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CHARACTER_LITERAL(self):
            return self.getToken(CartoSymCSSGrammar.CHARACTER_LITERAL, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expString

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpString" ):
                listener.enterExpString(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpString" ):
                listener.exitExpString(self)




    def expString(self):

        localctx = CartoSymCSSGrammar.ExpStringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_expString)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 291
            self.match(CartoSymCSSGrammar.CHARACTER_LITERAL)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpArrayContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LSBR(self):
            return self.getToken(CartoSymCSSGrammar.LSBR, 0)

        def RSBR(self):
            return self.getToken(CartoSymCSSGrammar.RSBR, 0)

        def arrayElements(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArrayElementsContext,0)


        def LPAR(self):
            return self.getToken(CartoSymCSSGrammar.LPAR, 0)

        def RPAR(self):
            return self.getToken(CartoSymCSSGrammar.RPAR, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expArray

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpArray" ):
                listener.enterExpArray(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpArray" ):
                listener.exitExpArray(self)




    def expArray(self):

        localctx = CartoSymCSSGrammar.ExpArrayContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_expArray)
        self._la = 0 # Token type
        try:
            self.state = 303
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [5]:
                self.enterOuterAlt(localctx, 1)
                self.state = 293
                self.match(CartoSymCSSGrammar.LSBR)
                self.state = 295
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2156088393890) != 0):
                    self.state = 294
                    self.arrayElements(0)


                self.state = 297
                self.match(CartoSymCSSGrammar.RSBR)
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 2)
                self.state = 298
                self.match(CartoSymCSSGrammar.LPAR)
                self.state = 300
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 2156088393890) != 0):
                    self.state = 299
                    self.arrayElements(0)


                self.state = 302
                self.match(CartoSymCSSGrammar.RPAR)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArrayElementsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def arrayElements(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArrayElementsContext,0)


        def COMMA(self):
            return self.getToken(CartoSymCSSGrammar.COMMA, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_arrayElements

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArrayElements" ):
                listener.enterArrayElements(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArrayElements" ):
                listener.exitArrayElements(self)



    def arrayElements(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.ArrayElementsContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 40
        self.enterRecursionRule(localctx, 40, self.RULE_arrayElements, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 306
            self.expression(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 313
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,31,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = CartoSymCSSGrammar.ArrayElementsContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arrayElements)
                    self.state = 308
                    if not self.precpred(self._ctx, 1):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                    self.state = 309
                    self.match(CartoSymCSSGrammar.COMMA)
                    self.state = 310
                    self.expression(0) 
                self.state = 315
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,31,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class ExpCallContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENTIFIER(self):
            return self.getToken(CartoSymCSSGrammar.IDENTIFIER, 0)

        def LPAR(self):
            return self.getToken(CartoSymCSSGrammar.LPAR, 0)

        def arguments(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArgumentsContext,0)


        def RPAR(self):
            return self.getToken(CartoSymCSSGrammar.RPAR, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_expCall

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpCall" ):
                listener.enterExpCall(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpCall" ):
                listener.exitExpCall(self)




    def expCall(self):

        localctx = CartoSymCSSGrammar.ExpCallContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_expCall)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 316
            self.match(CartoSymCSSGrammar.IDENTIFIER)
            self.state = 317
            self.match(CartoSymCSSGrammar.LPAR)
            self.state = 318
            self.arguments(0)
            self.state = 319
            self.match(CartoSymCSSGrammar.RPAR)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArgumentsContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ExpressionContext,0)


        def arguments(self):
            return self.getTypedRuleContext(CartoSymCSSGrammar.ArgumentsContext,0)


        def COMMA(self):
            return self.getToken(CartoSymCSSGrammar.COMMA, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_arguments

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArguments" ):
                listener.enterArguments(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArguments" ):
                listener.exitArguments(self)



    def arguments(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = CartoSymCSSGrammar.ArgumentsContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 44
        self.enterRecursionRule(localctx, 44, self.RULE_arguments, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 322
            self.expression(0)
            self._ctx.stop = self._input.LT(-1)
            self.state = 329
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,32,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = CartoSymCSSGrammar.ArgumentsContext(self, _parentctx, _parentState)
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_arguments)
                    self.state = 324
                    if not self.precpred(self._ctx, 1):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 1)")
                    self.state = 325
                    self.match(CartoSymCSSGrammar.COMMA)
                    self.state = 326
                    self.expression(0) 
                self.state = 331
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,32,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class UnaryLogicalOperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NOT(self):
            return self.getToken(CartoSymCSSGrammar.NOT, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_unaryLogicalOperator

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnaryLogicalOperator" ):
                listener.enterUnaryLogicalOperator(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnaryLogicalOperator" ):
                listener.exitUnaryLogicalOperator(self)




    def unaryLogicalOperator(self):

        localctx = CartoSymCSSGrammar.UnaryLogicalOperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_unaryLogicalOperator)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 332
            self.match(CartoSymCSSGrammar.NOT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnaryArithmeticOperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PLUS(self):
            return self.getToken(CartoSymCSSGrammar.PLUS, 0)

        def MINUS(self):
            return self.getToken(CartoSymCSSGrammar.MINUS, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_unaryArithmeticOperator

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterUnaryArithmeticOperator" ):
                listener.enterUnaryArithmeticOperator(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitUnaryArithmeticOperator" ):
                listener.exitUnaryArithmeticOperator(self)




    def unaryArithmeticOperator(self):

        localctx = CartoSymCSSGrammar.UnaryArithmeticOperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_unaryArithmeticOperator)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 334
            _la = self._input.LA(1)
            if not(_la==33 or _la==34):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithmeticOperatorExpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def POW(self):
            return self.getToken(CartoSymCSSGrammar.POW, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_arithmeticOperatorExp

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArithmeticOperatorExp" ):
                listener.enterArithmeticOperatorExp(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArithmeticOperatorExp" ):
                listener.exitArithmeticOperatorExp(self)




    def arithmeticOperatorExp(self):

        localctx = CartoSymCSSGrammar.ArithmeticOperatorExpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_arithmeticOperatorExp)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 336
            self.match(CartoSymCSSGrammar.POW)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithmeticOperatorMulContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MUL(self):
            return self.getToken(CartoSymCSSGrammar.MUL, 0)

        def DIV(self):
            return self.getToken(CartoSymCSSGrammar.DIV, 0)

        def IDIV(self):
            return self.getToken(CartoSymCSSGrammar.IDIV, 0)

        def MOD(self):
            return self.getToken(CartoSymCSSGrammar.MOD, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_arithmeticOperatorMul

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArithmeticOperatorMul" ):
                listener.enterArithmeticOperatorMul(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArithmeticOperatorMul" ):
                listener.exitArithmeticOperatorMul(self)




    def arithmeticOperatorMul(self):

        localctx = CartoSymCSSGrammar.ArithmeticOperatorMulContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_arithmeticOperatorMul)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 338
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 4026531840) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArithmeticOperatorAddContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MINUS(self):
            return self.getToken(CartoSymCSSGrammar.MINUS, 0)

        def PLUS(self):
            return self.getToken(CartoSymCSSGrammar.PLUS, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_arithmeticOperatorAdd

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterArithmeticOperatorAdd" ):
                listener.enterArithmeticOperatorAdd(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitArithmeticOperatorAdd" ):
                listener.exitArithmeticOperatorAdd(self)




    def arithmeticOperatorAdd(self):

        localctx = CartoSymCSSGrammar.ArithmeticOperatorAddContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_arithmeticOperatorAdd)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 340
            _la = self._input.LA(1)
            if not(_la==33 or _la==34):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RelationalOperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EQ(self):
            return self.getToken(CartoSymCSSGrammar.EQ, 0)

        def NEQ(self):
            return self.getToken(CartoSymCSSGrammar.NEQ, 0)

        def LT(self):
            return self.getToken(CartoSymCSSGrammar.LT, 0)

        def LTEQ(self):
            return self.getToken(CartoSymCSSGrammar.LTEQ, 0)

        def GT(self):
            return self.getToken(CartoSymCSSGrammar.GT, 0)

        def GTEQ(self):
            return self.getToken(CartoSymCSSGrammar.GTEQ, 0)

        def IN(self):
            return self.getToken(CartoSymCSSGrammar.IN, 0)

        def NOT(self):
            return self.getToken(CartoSymCSSGrammar.NOT, 0)

        def IS(self):
            return self.getToken(CartoSymCSSGrammar.IS, 0)

        def LIKE(self):
            return self.getToken(CartoSymCSSGrammar.LIKE, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_relationalOperator

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRelationalOperator" ):
                listener.enterRelationalOperator(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRelationalOperator" ):
                listener.exitRelationalOperator(self)




    def relationalOperator(self):

        localctx = CartoSymCSSGrammar.RelationalOperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_relationalOperator)
        try:
            self.state = 357
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,33,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 342
                self.match(CartoSymCSSGrammar.EQ)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 343
                self.match(CartoSymCSSGrammar.NEQ)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 344
                self.match(CartoSymCSSGrammar.LT)
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 345
                self.match(CartoSymCSSGrammar.LTEQ)
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 346
                self.match(CartoSymCSSGrammar.GT)
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 347
                self.match(CartoSymCSSGrammar.GTEQ)
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 348
                self.match(CartoSymCSSGrammar.IN)
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 349
                self.match(CartoSymCSSGrammar.NOT)
                self.state = 350
                self.match(CartoSymCSSGrammar.IN)
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 351
                self.match(CartoSymCSSGrammar.IS)
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 352
                self.match(CartoSymCSSGrammar.IS)
                self.state = 353
                self.match(CartoSymCSSGrammar.NOT)
                pass

            elif la_ == 11:
                self.enterOuterAlt(localctx, 11)
                self.state = 354
                self.match(CartoSymCSSGrammar.LIKE)
                pass

            elif la_ == 12:
                self.enterOuterAlt(localctx, 12)
                self.state = 355
                self.match(CartoSymCSSGrammar.NOT)
                self.state = 356
                self.match(CartoSymCSSGrammar.LIKE)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BetweenOperatorContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def BETWEEN(self):
            return self.getToken(CartoSymCSSGrammar.BETWEEN, 0)

        def NOT(self):
            return self.getToken(CartoSymCSSGrammar.NOT, 0)

        def getRuleIndex(self):
            return CartoSymCSSGrammar.RULE_betweenOperator

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBetweenOperator" ):
                listener.enterBetweenOperator(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBetweenOperator" ):
                listener.exitBetweenOperator(self)




    def betweenOperator(self):

        localctx = CartoSymCSSGrammar.BetweenOperatorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_betweenOperator)
        try:
            self.state = 362
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [20]:
                self.enterOuterAlt(localctx, 1)
                self.state = 359
                self.match(CartoSymCSSGrammar.BETWEEN)
                pass
            elif token in [17]:
                self.enterOuterAlt(localctx, 2)
                self.state = 360
                self.match(CartoSymCSSGrammar.NOT)
                self.state = 361
                self.match(CartoSymCSSGrammar.BETWEEN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[5] = self.stylingRuleList_sempred
        self._predicates[8] = self.tuple_sempred
        self._predicates[9] = self.expression_sempred
        self._predicates[11] = self.lhValue_sempred
        self._predicates[13] = self.propertyAssignmentList_sempred
        self._predicates[15] = self.propertyAssignmentInferredList_sempred
        self._predicates[20] = self.arrayElements_sempred
        self._predicates[22] = self.arguments_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def stylingRuleList_sempred(self, localctx:StylingRuleListContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 1)
         

    def tuple_sempred(self, localctx:TupleContext, predIndex:int):
            if predIndex == 1:
                return self.precpred(self._ctx, 1)
         

    def expression_sempred(self, localctx:ExpressionContext, predIndex:int):
            if predIndex == 2:
                return self.precpred(self._ctx, 12)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 10)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 9)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 8)
         

            if predIndex == 6:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 7:
                return self.precpred(self._ctx, 5)
         

            if predIndex == 8:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 9:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 10:
                return self.precpred(self._ctx, 19)
         

            if predIndex == 11:
                return self.precpred(self._ctx, 13)
         

    def lhValue_sempred(self, localctx:LhValueContext, predIndex:int):
            if predIndex == 12:
                return self.precpred(self._ctx, 2)
         

            if predIndex == 13:
                return self.precpred(self._ctx, 1)
         

    def propertyAssignmentList_sempred(self, localctx:PropertyAssignmentListContext, predIndex:int):
            if predIndex == 14:
                return self.precpred(self._ctx, 1)
         

    def propertyAssignmentInferredList_sempred(self, localctx:PropertyAssignmentInferredListContext, predIndex:int):
            if predIndex == 15:
                return self.precpred(self._ctx, 2)
         

            if predIndex == 16:
                return self.precpred(self._ctx, 1)
         

    def arrayElements_sempred(self, localctx:ArrayElementsContext, predIndex:int):
            if predIndex == 17:
                return self.precpred(self._ctx, 1)
         

    def arguments_sempred(self, localctx:ArgumentsContext, predIndex:int):
            if predIndex == 18:
                return self.precpred(self._ctx, 1)
         




