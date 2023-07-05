from typing import Any, TypeVar, Generic, List, Dict, List
from chiquito_ast import InternalSignal, ForwardSignal, SharedSignal, FixedSignal
from expr import Expr
from query import Queriable

class Constraint:
    def __init__(self, annotation: str, expr: Expr, typing: str):
        self.annotation = annotation
        self.expr = expr
        if typing not in ["Unknown", "Boolean", "AntiBooly"]:
            raise ValueError("Invalid typing for Constraint.")
        self.typing = typing
    
    def from_expr(expr: Expr) -> 'Constraint': # `from` is a reserved keyword in Python
        if not isinstance(expr, Queriable):
            raise TypeError("Can only call `from_expr` on an `Expr`.")
        annotation: str = expr.__repr__()
        if expr.variant == "Query":
            return Constraint(annotation, expr, "Boolean")
        else:
            return Constraint(annotation, expr, "Unknown")

    def from_queriable(query: Queriable): # `from` is a reserved keyword in Python
        if not isinstance(query, Queriable):
            raise TypeError("Can only call `from_queriable` on a `Queriable`.")
        expr = Expr("Query")
        expr.data['query'] = query
        if query.variant == "StepTypeNext":
            return Constraint(query.annotation(), expr, "Boolean")
        else:
            return Constraint(query.annotation(), expr, "Unknown")
        
    def __repr__(self):
        return self.annotation
    
    def cb_and(inputs: List['Constraint']) -> 'Constraint':
        annotations: List[str] = []
        expr = Expr("Const")
        expr.data['value'] = 1
        for constraint in inputs:
            if constraint.typing == "Boolean" or constraint.typing == "Unknown":
                annotations.append(constraint.annotation)
                expr = expr * constraint.expr
            else:
                raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        return Constraint(f"({' AND '.join(annotations)})", expr, "Boolean")
    
    def cb_or(inputs: List['Constraint']) -> 'Constraint':
        annotations: List[str] = []
        exprs: List[Expr] = []
        for constraint in inputs:
            if constraint.typing == "Boolean" or constraint.typing == "Unknown":
                annotations.append(constraint.annotation)
                exprs.append(constraint.expr)
            else:
                raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        result: Constraint = Constraint.cb_not(Constraint.cb_and([Constraint.cb_not(expr) for expr in exprs]))
        return Constraint(f"({' OR '.join(annotations)})", result.expr, "Boolean")
    
    def cb_xor(lhs: 'Constraint', rhs: 'Constraint') -> 'Constraint':
        if (lhs.typing == "Boolean" or lhs.typing == "Unknown") and (rhs.typing == "Boolean" or rhs.typing == "Unknown"):
            return Constraint(
                f"({lhs.annotation} XOR {rhs.annotation})", 
                lhs.expr + rhs.expr - 2 * lhs.expr * rhs.expr, # TODO: convert 2 to expr
                "Boolean"
                )
        else:
            raise ValueError(f"Expected Boolean or Unknown constraints, got AntiBooly in one of lhs or rhs constraints (lhs constraint: {lhs.annotation}) (rhs constraint: {rhs.annotation})")

    def eq(lhs: 'Constraint', rhs: 'Constraint') -> 'Constraint':
        return Constraint(
            f"({lhs.annotation} == {rhs.annotation})", 
            lhs.expr - rhs.expr,
            "AntiBooly"
            )

    def select(selector: 'Constraint', when_true: 'Constraint', when_false: 'Constraint') -> 'Constraint':
        if selector.typing == "AntiBooly":
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})else({when_false.annotation})",
            selector.expr * when_true.expr + (1 - selector.expr) * when_false.expr, # TODO: convert 1 to expr
            when_true.typing if when_true.typing == when_false.typing else "Unknown"
        )

    def when(selector: 'Constraint', when_true: 'Constraint') -> 'Constraint':
        if selector.typing == "AntiBooly":
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})",
            selector.expr * when_true.expr,
            when_true.typing
        )
    
    def unless(selector: 'Constraint', when_false: 'Constraint') -> 'Constraint':
        if selector.typing == "AntiBooly":
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"unless({selector.annotation})then({when_false.annotation})",
            (1 - selector.expr) * when_false.expr, # TODO: convert 1 to expr
            when_false.typing
        )

    def cb_not(constraint: 'Constraint') -> 'Constraint':
        if constraint.typing == "AntiBooly":
            raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        return Constraint(
            f"NOT({constraint.annotation})",
            1 - constraint.expr,
            "Boolean"
        )

    def isz(constraint: 'Constraint') -> 'Constraint':
        return Constraint(
            f"0 == {constraint.annotation}",
            constraint.expr,
            "AntiBooly"
        )
    
    def if_next_step(step_type: StepTypeHandler, constraint: 'Constraint') -> 'Constraint': 
        return Constraint(
            f"if(next step is {step_type.annotation})then({constraint.annotation})",
            step_type.next() * constraint.expr, # TODO: implement StepTypeHandler and its `next` method
            constraint.typing
        )

    def next_step_must_be(step_type: StepTypeHandler) -> 'Constraint':
        return Constraint(
            f"next step must be {step_type.annotation}",
            Constraint.cb_not(step_type.next()), # TODO: implement StepTypeHandler and its `next` method
            "AntiBooly"
        )

    def next_step_must_not_be(step_type: StepTypeHandler) -> 'Constraint':
        return Constraint(
            f"next step must not be {step_type.annotation}",
            step_type.next(), # TODO: implement StepTypeHandler and its `next` method
            "AntiBooly"
        )

    # TODO: might need the `annotate` function
    # /// Takes a string annotation and an expression, and returns a new constraint with the given
    # /// annotation and expression.
    # pub fn annotate<F, E: Into<Expr<F>>>(annotation: String, expr: E, typing: Typing) -> Constraint<F> {
    #     Constraint {
    #         annotation,
    #         expr: expr.into(),
    #         typing,
    #     }
    # }

    def rlc(exprs: List[Expr], randomness: Expr) -> Expr:
        if len(exprs) > 0:
            exprs = exprs.reverse()
            init: Expr = exprs[0]
            for expr in exprs[1:]:
                init = init * randomness + expr
            return init
        else:
            return 0 # TODO: convert 0 to expr

    # TODO: implement lookup table after the lookup abstraction pr is merged
