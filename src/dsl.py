from __future__ import annotations
from typing import Callable, List
from dataclasses import dataclass
from enum import Enum, auto
from py_ecc import bn128

from chiquito_ast import Circuit, StepType, Queriable, Forward, Internal, Shared, Fixed, StepTypeNext, Const, Neg, ToExpr, to_expr, Expr, Query
from util import uuid

F = bn128.FQ

#######
# dsl #
#######

class CircuitContext:
    def __init__(self):
        self.circuit = Circuit()

    def forward(self: CircuitContext, name: str) -> Queriable:
        return Queriable(Forward(self.circuit.add_forward(name, 0), False))

    def forward_with_phase(self: CircuitContext, name: str, phase: int) -> Queriable:
        return Queriable(Forward(self.circuit.add_forward(name, phase), False))
    
    def shared(self: CircuitContext, name: str) -> Queriable:
        return Queriable(Shared(self.circuit.add_shared(name, 0), 0))
    
    def shared_with_phase(self: CircuitContext, name: str, phase: int) -> Queriable:
        return Queriable(Shared(self.circuit.add_shared(name, phase), 0))

    def fixed(self: CircuitContext, name: str) -> Queriable:
        return Queriable(Fixed(self.circuit.add_fixed(name), 0))
    
    def expose(self: CircuitContext, forward: Queriable):
        match forward:
            case Queriable(Forward(forward_signal, _)):
                self.circuit.expose(forward_signal)
            case _:
                raise ValueError("Can only expose a forward signal.")
            
    # TODO: Implement import_halo2_advice and import_halo2_fixed. Currently we ignore imported query types.

    def step_type(self: CircuitContext, name: str) -> StepTypeHandler:
        handler = StepTypeHandler.new(name)
        self.circuit.add_step_type(handler, name)
        return handler
    
    def step_type_def(self: CircuitContext, step: StepTypeDefInput, step_type_func: Callable[[StepTypeContext], StepTypeWGHandler]) -> StepTypeWGHandler:
        match step:
            case StepTypeDefInput(Handler(h)):
                handler = h
            case StepTypeDefInput(String(name)):
                handler = StepTypeHandler.new(name)
                self.circuit.add_step_type(handler, name)
            case _:
                raise ValueError("Invalid StepTypeDefInput enum type.")
        context = StepTypeContext.new(handler.id, handler.annotation)
        result = step_type_func(context)
        self.circuit.add_step_type_def(context.step_type)
        return result
    
    def trace(self: CircuitContext, trace_def: Callable[[TraceContext, TraceArgs], None]):
        self.circuit.set_trace(trace_def)

    def fixed_gen(self: CircuitContext, fixed_gen_def: Callable[[FixedGenContext], None]):
        self.circuit.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(self: CircuitContext, step_type: StepTypeHandler) -> None: # TODO: define and use ToStepTypeHandler instead
        self.circuit.first_step = step_type.id

    def pragma_last_step(self, step_type: StepTypeHandler) -> None:
        self.circuit.last_step = step_type.id
    
    def pragma_num_steps(self, num_steps: int) -> None:
        self.circuit.num_steps = num_steps

@dataclass
class StepTypeDefInput:
    enum: Handler | String
    
    def from_handler(h: StepTypeHandler) -> StepTypeDefInput:
        return StepTypeDefInput(Handler(h))
    
    def from_string(s: str) -> StepTypeDefInput:
        return StepTypeDefInput(String(s))

@dataclass
class StepTypeContext:
    step_type: StepType
    
    def new(id: int, name: str) -> StepTypeContext:
        return StepTypeContext(StepType(id, name))
    
    def internal(self: StepTypeContext, name: str) -> Queriable:
        return Queriable(Internal(self.step_type.add_signal(name)))

    def setup(self: StepTypeContext, setup_def: Callable[[StepTypeSetupContext], None]) -> None: # def is a keyword in python
        ctx = StepTypeSetupContext(self.step_type)
        setup_def(ctx)
    
    def wg(self, wg_def: Callable[[StepInstance, Args], None]) -> StepTypeWGHandler:
        return StepTypeWGHandler(
            self.step_type.id, 
            self.step_type.name,
            wg_def
        )

@dataclass
class StepTypeSetupContext:
    step_type: StepType

    def constr(self: StepTypeSetupContext, constraint: ToConstraint):
        constraint = to_constraint(constraint)
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_constr(constraint.annotation, constraint.expr)

    def transition(self: StepTypeSetupContext, constraint: ToConstraint):
        constraint = to_constraint(constraint)
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_transition(constraint.annotation, constraint.expr)

    def enforce_constraint_typing(constraint: Constraint):
        if constraint.typing != Typing.AntiBooly:
            raise ValueError(f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})")

    # TODO: Implement add_lookup after lookup abstraction PR is merged.

@dataclass
class StepTypeHandler:
    id: int
    annotation: str

    def new(annotation: str) -> StepTypeHandler:
        return StepTypeHandler(uuid(), annotation)
    
    def next(self: StepTypeHandler) -> Queriable:
        return Queriable(StepTypeNext(self))
    
    def from_wg_handler(wg_handler: StepTypeWGHandler) -> StepTypeHandler:
        return StepTypeHandler(wg_handler.id, wg_handler.annotation)

@dataclass
class StepTypeWGHandler:
    id: int
    annotation: str
    wg: Callable[[StepInstance, Args], None]

def circuit(name: str, circuit_context_def: Callable[[CircuitContext], None]) -> Circuit:
    ctx = CircuitContext()
    circuit_context_def(ctx)
    return ctx.circuit

ToStepTypeDefInput = StepTypeHandler | str

@dataclass
class Handler:
    handler: StepTypeHandler

@dataclass
class String:
    string: str

##########
# dsl/cb #
##########

class Typing(Enum):
    Unknown = auto()
    Boolean = auto()
    AntiBooly = auto()

@dataclass
class Constraint:
    annotation: str
    expr: Expr
    typing: Typing

    def from_expr(expr: Expr) -> Constraint: # `from` is a reserved keyword in Python
        annotation: str = str(expr)
        match expr.enum:
            case Query(Queriable(StepTypeNext(_))):
                return Constraint(annotation, expr, Typing.Boolean)
            case _:
                return Constraint(annotation, expr, Typing.Unknown)

    def from_queriable(query: Queriable) -> Constraint:
        expr = Expr(Query(query))
        match query.enum:
            case StepTypeNext(_):
                return Constraint(query.annotation(), expr, Typing.Boolean)
            case _:
                return Constraint(query.annotation(), expr, Typing.Unknown)
        
    def __str__(self: Constraint) -> str:
        return self.annotation
    
    def cb_and(inputs: List[ToConstraint]) -> Constraint: # `and` is a reserved keyword in Python
        inputs = [to_constraint(input) for input in inputs]
        annotations: List[str] = []
        expr = Expr(Const(F(1)))
        for constraint in inputs:
            if constraint.typing == Typing.Boolean or constraint.typing == Typing.Unknown:
                annotations.append(constraint.annotation)
                expr = expr * constraint.expr
            else:
                raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        return Constraint(f"({' AND '.join(annotations)})", expr, Typing.Boolean)
    
    def cb_or(inputs: List[ToConstraint]) -> Constraint: # `or` is a reserved keyword in Python
        inputs = [to_constraint(input) for input in inputs]
        annotations: List[str] = []
        exprs: List[Expr] = []
        for constraint in inputs:
            if constraint.typing == Typing.Boolean or constraint.typing == Typing.Unknown:
                annotations.append(constraint.annotation)
                exprs.append(constraint.expr)
            else:
                raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        result: Constraint = Constraint.cb_not(Constraint.cb_and([Constraint.cb_not(expr) for expr in exprs]))
        return Constraint(f"({' OR '.join(annotations)})", result.expr, Typing.Boolean)
    
    def xor(lhs: ToConstraint, rhs: ToConstraint) -> Constraint:
        (lhs, rhs) = (to_constraint(lhs), to_constraint(rhs))
        if (lhs.typing == Typing.Boolean or lhs.typing == Typing.Unknown) and (rhs.typing == Typing.Boolean or rhs.typing == Typing.Unknown):
            return Constraint(
                f"({lhs.annotation} XOR {rhs.annotation})", 
                lhs.expr + rhs.expr - F(2) * lhs.expr * rhs.expr,
                Typing.Boolean
                )
        else:
            raise ValueError(f"Expected Boolean or Unknown constraints, got AntiBooly in one of lhs or rhs constraints (lhs constraint: {lhs.annotation}) (rhs constraint: {rhs.annotation})")

    def eq(lhs: ToConstraint, rhs: ToConstraint) -> Constraint:
        (lhs, rhs) = (to_constraint(lhs), to_constraint(rhs))
        return Constraint(
            f"({lhs.annotation} == {rhs.annotation})", 
            lhs.expr - rhs.expr,
            Typing.AntiBooly
            )

    def select(selector: ToConstraint, when_true: ToConstraint, when_false: ToConstraint) -> Constraint:
        (selector, when_true, when_false) = (to_constraint(selector), to_constraint(when_true), to_constraint(when_false))
        if selector.typing == Typing.AntiBooly:
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})else({when_false.annotation})",
            selector.expr * when_true.expr + (F(1) - selector.expr) * when_false.expr,
            when_true.typing if when_true.typing == when_false.typing else Typing.Unknown
        )

    def when(selector: ToConstraint, when_true: ToConstraint) -> Constraint:
        (selector, when_true) = (to_constraint(selector), to_constraint(when_true))
        if selector.typing == Typing.AntiBooly:
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})",
            selector.expr * when_true.expr,
            when_true.typing
        )
    
    def unless(selector: ToConstraint, when_false: ToConstraint) -> Constraint:
        (selector, when_false) = (to_constraint(selector), to_constraint(when_false))
        if selector.typing == Typing.AntiBooly:
            raise ValueError(f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})")
        return Constraint(
            f"unless({selector.annotation})then({when_false.annotation})",
            (F(1) - selector.expr) * when_false.expr,
            when_false.typing
        )

    def cb_not(constraint: ToConstraint) -> Constraint: # `not` is a reserved keyword in Python
        constraint = to_constraint(constraint)
        if constraint.typing == Typing.AntiBooly:
            raise ValueError(f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})")
        return Constraint(
            f"NOT({constraint.annotation})",
            F(1) - constraint.expr,
            Typing.Boolean
        )

    def isz(constraint: ToConstraint) -> Constraint:
        constraint = to_constraint(constraint)
        return Constraint(
            f"0 == {constraint.annotation}",
            constraint.expr,
            Typing.AntiBooly
        )
    
    def if_next_step(step_type: StepTypeHandler, constraint: ToConstraint) -> Constraint: # TODO: define and use ToStepTypeHandler instead
        constraint = to_constraint(constraint)
        return Constraint(
            f"if(next step is {step_type.annotation})then({constraint.annotation})",
            step_type.next() * constraint.expr, # TODO: implement StepTypeHandler and its `next` method
            constraint.typing
        )

    def next_step_must_be(step_type: StepTypeHandler) -> Constraint:
        return Constraint(
            f"next step must be {step_type.annotation}",
            Constraint.cb_not(step_type.next()), # TODO: implement StepTypeHandler and its `next` method
            Typing.AntiBooly
        )

    def next_step_must_not_be(step_type: StepTypeHandler) -> Constraint:
        return Constraint(
            f"next step must not be {step_type.annotation}",
            step_type.next(), # TODO: implement StepTypeHandler and its `next` method
            Typing.AntiBooly
        )

    def rlc(exprs: List[ToExpr], randomness: Expr) -> Expr:
        if len(exprs) > 0:
            exprs: List[Expr] = [to_expr(expr) for expr in exprs].reverse()
            init: Expr = exprs[0]
            for expr in exprs[1:]:
                init = init * randomness + expr
            return init
        else:
            return Expr(Const(F(0)))

    # TODO: Implement lookup table after the lookup abstraction pr is merged.

ToConstraint = Constraint | Expr | int | F | Queriable

def to_constraint(v: ToConstraint) -> Constraint:
    if isinstance(v, Constraint):
        return v
    elif isinstance(v, Expr):
        match v:
            case Expr(Query(Queriable(StepTypeNext(_)))):
                return Constraint(v, str(v), Typing.Boolean)
            case _:
                return Constraint(v, str(v), Typing.Unknown)
    elif isinstance(v, int):
        if v >= 0:
            return to_constraint(Expr(Const(F(v))))
        else:
            return to_constraint(Expr(Neg(Expr(Const(F(-v))))))
    elif isinstance(v, F):
        return to_constraint(Expr(Const(v)))
    elif isinstance(v, Queriable):
        match v:
            case Queriable(StepTypeNext(_)):
                return Constraint(v.annotation(), Expr(Query(v)), Typing.Boolean)
            case _:
                return Constraint(v.annotation(), Expr(Query(v)), Typing.Unknown)
    else:
        raise TypeError(f"Type `{type(v)}` is not ToConstraint (one of Constraint, Expr, int, F, or Queriable).")
