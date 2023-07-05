from chiquito_ast import Circuit, StepType
from typing import Callable
from query import Queriable
from expr import Expr
from util import uuid
from cb import Constraint

class CircuitContext:
    def __init__(self):
        self.circuit = Circuit()

    def forward(self, name: str) -> Queriable:
        out = Queriable("Forward")
        forward_signal = self.circuit.add_forward(name, 0)
        out.data['forward'] = forward_signal
        out.data['rotation'] = 0
        return out

    def forward_with_phase(self, name: str, phase: int) -> Queriable:
        out = Queriable("Forward")
        forward_signal = self.circuit.add_forward(name, phase)
        out.data['forward'] = forward_signal
        out.data['rotation'] = 0
        return out
    
    def shared(self, name: str) -> Queriable:
        out = Queriable("Shared")
        shared_signal = self.circuit.add_shared(name, 0)
        out.data['shared'] = shared_signal
        out.data['rotation'] = 0
        return out
    
    def shared_with_phase(self, name: str, phase: int) -> Queriable:
        out = Queriable("Shared")
        shared_signal = self.circuit.add_shared(name, phase)
        out.data['shared'] = shared_signal
        out.data['rotation'] = 0
        return out
    
    def fixed(self, name: str) -> Queriable:
        out = Queriable("Fixed")
        fixed_signal = self.circuit.add_fixed(name)
        out.data['fixed'] = fixed_signal
        out.data['rotation'] = 0
        return out
    
    def expose(self, forward: Queriable) -> None:
        if forward.variant != "Forward":
            raise ValueError("Can only expose a forward signal.")
        else: 
            self.circuit.expose(forward.data['forward'])

    # TODO: Implement import_halo2_advice and import_halo2_fixed. Currently we ignore imported query types

    def step_type(self, name: str) -> 'StepTypeHandler':
        handler = StepTypeHandler.new(name)
        self.circuit.add_step_type(handler, name)
        return handler
    
    def step_type_def(self, step: 'StepTypeDefInput', func: Callable[['StepTypeContext'], 'StepTypeWGHandler']) -> 'StepTypeWGHandler':
        if step.variant == "Handler":
            handler = step.data['handler']
        elif step.variant == "String":
            handler = StepTypeHandler.new(step.data['string'])
            self.circuit.add_step_type(handler, step.data['string'])
        else:
            raise ValueError("Invalid StepTypeDefInput variant.")
        context = StepTypeContext.new(handler.uuid(), handler.annotation)
        result = func(context)
        self.circuit.add_step_type_def(context.step_type)
        return result
    
    def trace(self, func: Callable[['TraceContext', 'TraceArgs'], None]) -> None:
        self.circuit.set_trace(func)

    def pragma_first_step(self, step_type: 'StepTypeHandler') -> None:
        self.circuit.first_step = step_type.uuid()

    def pragma_last_step(self, step_type: 'StepTypeHandler') -> None:
        self.circuit.last_step = step_type.uuid()
    
    def pragma_num_steps(self, num_steps: int) -> None:
        self.circuit.num_steps = num_steps

class StepTypeDefInput:
    def __init__(self, variant: str):
        if variant not in ['Handler', 'String']:
            raise ValueError("Invalid StepTypeDefInput variant.")
        self.variant = variant
        self.data = {}
        self.data['step_type_handler']: StepTypeHandler = None
        self.data['string']: str = None
    
    def from_handler(h: 'StepTypeHandler') -> 'StepTypeDefInput':
        out = StepTypeDefInput('Handler')
        out.data['step_type_handler'] = h
        return out
    
    def from_string(s: str) -> 'StepTypeDefInput':
        out = StepTypeDefInput('String')
        out.data['string'] = s
        return out

class StepTypeContext:
    def __init__(self, step_type: StepType):
        self.step_type = step_type
    
    def new(id: int, name: str) -> 'StepTypeContext':
        return StepTypeContext(StepType(id, name))

    def setup(self, func: Callable[['StepTypeSetupContext'], None]) -> None: # def is a keyword in python
        ctx = StepTypeSetupContext(self.step_type)
        func(ctx)
    
    def wg(self, func: Callable[['StepInstance', 'Args'], None]) -> 'StepTypeWGHandler':
        handler = StepTypeWGHandler(
            self.step_type.uuid(), 
            self.step_type.name,
            func
            )
        return handler

class StepTypeSetupContext:
    def __init__(self, step_type: StepType):
        self.step_type = step_type

    def constr(self, constraint: Constraint) -> None:
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_constr(constraint.annotation, constraint.expr)

    def transition(self, constraint: Constraint):
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_transition(constraint.annotation, constraint.expr)

    def enforce_constraint_typing(constraint: Constraint):
        if constraint.typing != "AntiBooly":
            raise ValueError(f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})")

    # TODO: implement add_lookup after lookup abstraction PR is merged.

class StepTypeHandler:
    def __init__(self, id: int, annotation: str):
        self.id = id
        self.annotation = annotation

    def new(annotation: str) -> 'StepTypeHandler':
        return StepTypeHandler(uuid(), annotation)

    def uuid(self) -> int:
        return self.id
    
    def next(self) -> Queriable:
        out = Queriable("StepTypeNext")
        out.data['step_type_next'] = self
        return out
    
# impl<F, Args, D: Fn(&mut StepInstance<F>, Args) + 'static> From<&StepTypeWGHandler<F, Args, D>>
#     for StepTypeHandler
# {
#     fn from(h: &StepTypeWGHandler<F, Args, D>) -> Self {
#         StepTypeHandler {
#             id: h.id,
#             annotation: h.annotation,
#         }
#     }
# }

class StepTypeWGHandler:
    def __init__(self, id: int, annotation: str, wg: Callable[['StepInstance', 'Args'], None]):
        self.id = id
        self.annotation = annotation
        self.wg = wg
    
    def uuid(self) -> int:
        return self.id

def circuit(name: str, circuit_context_lambda: Callable[[CircuitContext], None]) -> Circuit:
    ctx = CircuitContext()
    circuit_context_lambda(ctx)
    return ctx.circuit
