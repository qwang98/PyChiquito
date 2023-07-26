from chiquito_ast import (
    ASTStepType,
    ASTConstraint,
    TransitionConstraint,
    InternalSignal,
    ForwardSignal,
    SharedSignal,
    FixedSignal,
)
from query import Internal, Forward, Shared, Fixed
from expr import Const, Sum, Mul

########
# test #
########
# print(Internal(InternalSignal("a")).__json__())
# print(Forward(ForwardSignal(1, "a"), True).__json__())
# print(Shared(SharedSignal(0, "a"), 2).__json__())
# print(Fixed(FixedSignal("a"), 2).__json__())
# print(StepTypeNext(ASTStepType.new("fibo")).__json__())
# print(ASTConstraint("constraint", Sum([Const(1), Mul([Internal(InternalSignal("a")), Const(3)])])).__json__())
# print(TransitionConstraint("trans", Sum([Const(1), Mul([Internal(InternalSignal("a")), Const(3)])])).__json__())
print(
    ASTStepType(
        1,
        "fibo",
        [InternalSignal("a"), InternalSignal("b")],
        [
            ASTConstraint(
                "constraint",
                Sum([Const(1), Mul([Internal(InternalSignal("c")), Const(3)])]),
            ),
            ASTConstraint(
                "constraint",
                Sum([Const(1), Mul([Shared(SharedSignal(2, "d"), 1), Const(3)])]),
            ),
        ],
        [
            TransitionConstraint(
                "trans",
                Sum([Const(1), Mul([Forward(ForwardSignal(1, "e"), True), Const(3)])]),
            ),
            TransitionConstraint(
                "trans", Sum([Const(1), Mul([Fixed(FixedSignal("e"), 2), Const(3)])])
            ),
        ],
        {5: "a", 6: "b", 7: "c"},
        None,
    ).__json__()
)
