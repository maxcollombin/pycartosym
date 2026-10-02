# Generated from vendor/cartosymcss-grammar/CartoSymCSSGrammar.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .CartoSymCSSGrammar import CartoSymCSSGrammar
else:
    from CartoSymCSSGrammar import CartoSymCSSGrammar

# This class defines a complete listener for a parse tree produced by CartoSymCSSGrammar.
class CartoSymCSSGrammarListener(ParseTreeListener):

    # Enter a parse tree produced by CartoSymCSSGrammar#styleSheet.
    def enterStyleSheet(self, ctx:CartoSymCSSGrammar.StyleSheetContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#styleSheet.
    def exitStyleSheet(self, ctx:CartoSymCSSGrammar.StyleSheetContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#variable.
    def enterVariable(self, ctx:CartoSymCSSGrammar.VariableContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#variable.
    def exitVariable(self, ctx:CartoSymCSSGrammar.VariableContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#variableDef.
    def enterVariableDef(self, ctx:CartoSymCSSGrammar.VariableDefContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#variableDef.
    def exitVariableDef(self, ctx:CartoSymCSSGrammar.VariableDefContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#metadata.
    def enterMetadata(self, ctx:CartoSymCSSGrammar.MetadataContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#metadata.
    def exitMetadata(self, ctx:CartoSymCSSGrammar.MetadataContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#stylingRuleName.
    def enterStylingRuleName(self, ctx:CartoSymCSSGrammar.StylingRuleNameContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#stylingRuleName.
    def exitStylingRuleName(self, ctx:CartoSymCSSGrammar.StylingRuleNameContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#stylingRuleList.
    def enterStylingRuleList(self, ctx:CartoSymCSSGrammar.StylingRuleListContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#stylingRuleList.
    def exitStylingRuleList(self, ctx:CartoSymCSSGrammar.StylingRuleListContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#stylingRule.
    def enterStylingRule(self, ctx:CartoSymCSSGrammar.StylingRuleContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#stylingRule.
    def exitStylingRule(self, ctx:CartoSymCSSGrammar.StylingRuleContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#selector.
    def enterSelector(self, ctx:CartoSymCSSGrammar.SelectorContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#selector.
    def exitSelector(self, ctx:CartoSymCSSGrammar.SelectorContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#tuple.
    def enterTuple(self, ctx:CartoSymCSSGrammar.TupleContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#tuple.
    def exitTuple(self, ctx:CartoSymCSSGrammar.TupleContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#MulExpr.
    def enterMulExpr(self, ctx:CartoSymCSSGrammar.MulExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#MulExpr.
    def exitMulExpr(self, ctx:CartoSymCSSGrammar.MulExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#StringExpr.
    def enterStringExpr(self, ctx:CartoSymCSSGrammar.StringExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#StringExpr.
    def exitStringExpr(self, ctx:CartoSymCSSGrammar.StringExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#InstanceExpr.
    def enterInstanceExpr(self, ctx:CartoSymCSSGrammar.InstanceExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#InstanceExpr.
    def exitInstanceExpr(self, ctx:CartoSymCSSGrammar.InstanceExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#BetweenExpr.
    def enterBetweenExpr(self, ctx:CartoSymCSSGrammar.BetweenExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#BetweenExpr.
    def exitBetweenExpr(self, ctx:CartoSymCSSGrammar.BetweenExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#PowExpr.
    def enterPowExpr(self, ctx:CartoSymCSSGrammar.PowExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#PowExpr.
    def exitPowExpr(self, ctx:CartoSymCSSGrammar.PowExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#AddExpr.
    def enterAddExpr(self, ctx:CartoSymCSSGrammar.AddExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#AddExpr.
    def exitAddExpr(self, ctx:CartoSymCSSGrammar.AddExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#RelationalExpr.
    def enterRelationalExpr(self, ctx:CartoSymCSSGrammar.RelationalExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#RelationalExpr.
    def exitRelationalExpr(self, ctx:CartoSymCSSGrammar.RelationalExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#ConditionalExpr.
    def enterConditionalExpr(self, ctx:CartoSymCSSGrammar.ConditionalExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#ConditionalExpr.
    def exitConditionalExpr(self, ctx:CartoSymCSSGrammar.ConditionalExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#TupleExpr.
    def enterTupleExpr(self, ctx:CartoSymCSSGrammar.TupleExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#TupleExpr.
    def exitTupleExpr(self, ctx:CartoSymCSSGrammar.TupleExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#IndexExpr.
    def enterIndexExpr(self, ctx:CartoSymCSSGrammar.IndexExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#IndexExpr.
    def exitIndexExpr(self, ctx:CartoSymCSSGrammar.IndexExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#ArrayExpr.
    def enterArrayExpr(self, ctx:CartoSymCSSGrammar.ArrayExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#ArrayExpr.
    def exitArrayExpr(self, ctx:CartoSymCSSGrammar.ArrayExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#PrimaryExpr.
    def enterPrimaryExpr(self, ctx:CartoSymCSSGrammar.PrimaryExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#PrimaryExpr.
    def exitPrimaryExpr(self, ctx:CartoSymCSSGrammar.PrimaryExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#CallExpr.
    def enterCallExpr(self, ctx:CartoSymCSSGrammar.CallExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#CallExpr.
    def exitCallExpr(self, ctx:CartoSymCSSGrammar.CallExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#VariableExpr.
    def enterVariableExpr(self, ctx:CartoSymCSSGrammar.VariableExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#VariableExpr.
    def exitVariableExpr(self, ctx:CartoSymCSSGrammar.VariableExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#ParenExpr.
    def enterParenExpr(self, ctx:CartoSymCSSGrammar.ParenExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#ParenExpr.
    def exitParenExpr(self, ctx:CartoSymCSSGrammar.ParenExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#UnaryLogicalExpr.
    def enterUnaryLogicalExpr(self, ctx:CartoSymCSSGrammar.UnaryLogicalExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#UnaryLogicalExpr.
    def exitUnaryLogicalExpr(self, ctx:CartoSymCSSGrammar.UnaryLogicalExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#MemberAccessExpr.
    def enterMemberAccessExpr(self, ctx:CartoSymCSSGrammar.MemberAccessExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#MemberAccessExpr.
    def exitMemberAccessExpr(self, ctx:CartoSymCSSGrammar.MemberAccessExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#UnaryArithExpr.
    def enterUnaryArithExpr(self, ctx:CartoSymCSSGrammar.UnaryArithExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#UnaryArithExpr.
    def exitUnaryArithExpr(self, ctx:CartoSymCSSGrammar.UnaryArithExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#LogicalExpr.
    def enterLogicalExpr(self, ctx:CartoSymCSSGrammar.LogicalExprContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#LogicalExpr.
    def exitLogicalExpr(self, ctx:CartoSymCSSGrammar.LogicalExprContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#expInstance.
    def enterExpInstance(self, ctx:CartoSymCSSGrammar.ExpInstanceContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#expInstance.
    def exitExpInstance(self, ctx:CartoSymCSSGrammar.ExpInstanceContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#lhValue.
    def enterLhValue(self, ctx:CartoSymCSSGrammar.LhValueContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#lhValue.
    def exitLhValue(self, ctx:CartoSymCSSGrammar.LhValueContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#propertyAssignment.
    def enterPropertyAssignment(self, ctx:CartoSymCSSGrammar.PropertyAssignmentContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#propertyAssignment.
    def exitPropertyAssignment(self, ctx:CartoSymCSSGrammar.PropertyAssignmentContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#propertyAssignmentList.
    def enterPropertyAssignmentList(self, ctx:CartoSymCSSGrammar.PropertyAssignmentListContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#propertyAssignmentList.
    def exitPropertyAssignmentList(self, ctx:CartoSymCSSGrammar.PropertyAssignmentListContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#propertyAssignmentInferred.
    def enterPropertyAssignmentInferred(self, ctx:CartoSymCSSGrammar.PropertyAssignmentInferredContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#propertyAssignmentInferred.
    def exitPropertyAssignmentInferred(self, ctx:CartoSymCSSGrammar.PropertyAssignmentInferredContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#propertyAssignmentInferredList.
    def enterPropertyAssignmentInferredList(self, ctx:CartoSymCSSGrammar.PropertyAssignmentInferredListContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#propertyAssignmentInferredList.
    def exitPropertyAssignmentInferredList(self, ctx:CartoSymCSSGrammar.PropertyAssignmentInferredListContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#idOrConstant.
    def enterIdOrConstant(self, ctx:CartoSymCSSGrammar.IdOrConstantContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#idOrConstant.
    def exitIdOrConstant(self, ctx:CartoSymCSSGrammar.IdOrConstantContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#expConstant.
    def enterExpConstant(self, ctx:CartoSymCSSGrammar.ExpConstantContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#expConstant.
    def exitExpConstant(self, ctx:CartoSymCSSGrammar.ExpConstantContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#expString.
    def enterExpString(self, ctx:CartoSymCSSGrammar.ExpStringContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#expString.
    def exitExpString(self, ctx:CartoSymCSSGrammar.ExpStringContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#expArray.
    def enterExpArray(self, ctx:CartoSymCSSGrammar.ExpArrayContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#expArray.
    def exitExpArray(self, ctx:CartoSymCSSGrammar.ExpArrayContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#arrayElements.
    def enterArrayElements(self, ctx:CartoSymCSSGrammar.ArrayElementsContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#arrayElements.
    def exitArrayElements(self, ctx:CartoSymCSSGrammar.ArrayElementsContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#expCall.
    def enterExpCall(self, ctx:CartoSymCSSGrammar.ExpCallContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#expCall.
    def exitExpCall(self, ctx:CartoSymCSSGrammar.ExpCallContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#arguments.
    def enterArguments(self, ctx:CartoSymCSSGrammar.ArgumentsContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#arguments.
    def exitArguments(self, ctx:CartoSymCSSGrammar.ArgumentsContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#unaryLogicalOperator.
    def enterUnaryLogicalOperator(self, ctx:CartoSymCSSGrammar.UnaryLogicalOperatorContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#unaryLogicalOperator.
    def exitUnaryLogicalOperator(self, ctx:CartoSymCSSGrammar.UnaryLogicalOperatorContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#unaryArithmeticOperator.
    def enterUnaryArithmeticOperator(self, ctx:CartoSymCSSGrammar.UnaryArithmeticOperatorContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#unaryArithmeticOperator.
    def exitUnaryArithmeticOperator(self, ctx:CartoSymCSSGrammar.UnaryArithmeticOperatorContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorExp.
    def enterArithmeticOperatorExp(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorExpContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorExp.
    def exitArithmeticOperatorExp(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorExpContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorMul.
    def enterArithmeticOperatorMul(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorMulContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorMul.
    def exitArithmeticOperatorMul(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorMulContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorAdd.
    def enterArithmeticOperatorAdd(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorAddContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#arithmeticOperatorAdd.
    def exitArithmeticOperatorAdd(self, ctx:CartoSymCSSGrammar.ArithmeticOperatorAddContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#relationalOperator.
    def enterRelationalOperator(self, ctx:CartoSymCSSGrammar.RelationalOperatorContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#relationalOperator.
    def exitRelationalOperator(self, ctx:CartoSymCSSGrammar.RelationalOperatorContext):
        pass


    # Enter a parse tree produced by CartoSymCSSGrammar#betweenOperator.
    def enterBetweenOperator(self, ctx:CartoSymCSSGrammar.BetweenOperatorContext):
        pass

    # Exit a parse tree produced by CartoSymCSSGrammar#betweenOperator.
    def exitBetweenOperator(self, ctx:CartoSymCSSGrammar.BetweenOperatorContext):
        pass



del CartoSymCSSGrammar