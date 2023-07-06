from __future__ import annotations
from typing import Callable, List, Dict, Optional
from util import uuid
from expr import Expr
from dsl import StepTypeHandler
from dataclasses import dataclass

# pub struct Circuit<F, TraceArgs> {
#     pub step_types: HashMap<u32, Rc<StepType<F>>>,

#     pub forward_signals: Vec<ForwardSignal>,
#     pub shared_signals: Vec<SharedSignal>,
#     pub fixed_signals: Vec<FixedSignal>,
#     pub halo2_advice: Vec<ImportedHalo2Advice>,
#     pub halo2_fixed: Vec<ImportedHalo2Fixed>,
#     pub exposed: Vec<ForwardSignal>,

#     pub annotations: HashMap<u32, String>,

#     pub trace: Option<Rc<Trace<F, TraceArgs>>>,
#     pub fixed_gen: Option<Rc<FixedGen<F>>>,

#     pub first_step: Option<StepTypeUUID>,
#     pub last_step: Option<StepTypeUUID>,
#     pub num_steps: usize,
# }

@dataclass
class Circuit:
    step_types: Dict[int, StepType]
    
    forward_signals: List[ForwardSignal]
    shared_signals: List[SharedSignal]
    fixed_signals: List[FixedSignal]
    # halo2_advice: List[ImportedHalo2Advice]
    # halo2_fixed: List[ImportedHalo2Fixed]
    exposed: List[ForwardSignal]

    annotations: Dict[int, str]

    trace: Optional[callable]
    fixed_gen: Optional[callable]

    first_step: Optional[int]
    last_step: Optional[int]
    num_steps: int

    # TODO: __str__ (low priority as it's only used for debugging)

    def add_forward(self: Circuit, name: str, phase: int) -> ForwardSignal:
        signal = ForwardSignal(phase, name)
        self.forward_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_shared(self: Circuit, name: str, phase: int) -> SharedSignal:
        signal = SharedSignal(phase, name)
        self.shared_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_fixed(self: Circuit, name: str) -> FixedSignal:
        signal = FixedSignal(name)
        self.fixed_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def expose(self: Circuit, forward_signal: ForwardSignal):
        self.exposed.append(forward_signal)

    def add_step_type(self: Circuit, handler: StepTypeHandler, name: str):
        self.annotations[handler.id] = name

    def add_step_type_def(self, step: StepType) -> int:
        self.step_types[step.id] = step
        return step.id

    def set_trace(self, trace_def: Callable[[TraceContext, TraceArgs], None]):
        if self.trace is not None:
            raise Exception("Circuit cannot have more than one trace generator.")
        else: 
            self.trace = trace_def

    def set_fixed_gen(self, fixed_gen_def: Callable[[FixedGenContext], None]):
        if self.fixed_gen is not None:
            raise Exception("Circuit cannot have more than one fixed generator.")
        else: 
            self.fixed_gen = fixed_gen_def

    def get_step_type(self, uuid: int) -> StepType:
        if uuid in self.step_types.keys():
            return self.step_types[uuid]
        else:
            raise ValueError("StepType not found.")

# pub struct StepType<F> {
#     id: StepTypeUUID,

#     pub name: String,
#     pub signals: Vec<InternalSignal>,
#     pub constraints: Vec<Constraint<F>>,
#     pub transition_constraints: Vec<TransitionConstraint<F>>,
#     pub lookups: Vec<Lookup<F>>,
#     pub annotations: HashMap<u32, String>,
# }

@dataclass
class StepType:
    id: int

    name: str
    signals: List[InternalSignal]
    constraints: List[Constraint]
    transition_constraints: List[TransitionConstraint]
    # lookups: List[Lookup]
    annotations: Dict[int, str]

    # TODO: __str__ (low priority as it's only used for debugging)

    def __init__(self: StepType, id: int, name: str):
        self.id = id
        self.name = name
        self.signals: List[InternalSignal] = []
        self.constraints: List[Constraint] = []
        self.transition_constraints: List[TransitionConstraint] = []
        self.annotations: Dict[int, str] = {}

    def add_signal(self: StepType, name: str) -> InternalSignal:
        signal = InternalSignal(name)
        self.signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_constr(self: StepType, annotation: str, expr: Expr):
        condition = Constraint(annotation, expr)
        self.constraints.append(condition)

    def add_transition(self, annotation: str, expr: Expr):
        condition = TransitionConstraint(annotation, expr)
        self.transition_constraints.append(condition)

    def __eq__(self: StepType, other: StepType) -> bool:
        if isinstance(self, StepType) and isinstance(other, StepType):
            return self.id == other.id
        return False
    
    def __req__(other: StepType, self: StepType) -> bool:
        return StepType.__eq__(self, other)

    def __hash__(self: StepType):
        return hash(self.id)

@dataclass
class Constraint:
    annotation: str
    expr: Expr

@dataclass
class TransitionConstraint:
    annotation: str
    expr: Expr

@dataclass
class ForwardSignal:
    id: int
    phase: int
    annotation: str

    def __init__(self, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

@dataclass
class SharedSignal:
    id: int
    phase: int
    anotation: str

    def __init__(self: SharedSignal, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

@dataclass
class FixedSignal:
    id: int
    annotation: str

    def __init__(self: FixedSignal, annotation: str):
        self.id: int = uuid()
        self.annotation = annotation

@dataclass
class InternalSignal:
    id: int
    annotation: str

    def __init__(self, annotation: str):
        self.id = uuid()
        self.annotation = annotation
