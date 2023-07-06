from __future__ import annotations
from chiquito_ast import Circuit, StepType
from typing import Callable
from query import Queriable, Forward, Internal, Shared, Fixed, StepTypeNext
from expr import Expr
from util import uuid
from cb import Constraint, ToConstraint, to_constraint, Typing
from dataclasses import dataclass

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
class Handler:
    handler: StepTypeHandler

@dataclass
class String:
    string: str

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

    def setup(self, setup_def: Callable[[StepTypeSetupContext], None]) -> None: # def is a keyword in python
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
