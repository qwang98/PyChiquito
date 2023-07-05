from typing import Callable, List, Dict, Optional
# from collections import defaultdict
# from weakref import ref
from PyChiquito.util import uuid
from expr import Expr
from dsl import StepTypeHandler

class SharedSignal:
    def __init__(self, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

class FixedSignal:
    def __init__(self, annotation: str):
        self.id: int = uuid()
        self.annotation = annotation

class ForwardSignal:
    def __init__(self, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

class InternalSignal:
    def __init__(self, annotation: str):
        self.id = uuid()
        self.annotation = annotation

class StepType:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.signals: List[InternalSignal] = []
        self.constraints: List[Constraint] = []
        self.transition_constraints: List[TransitionConstraint] = []
        # self.lookups: List[Lookup] = []
        self.annotations: Dict[int, str] = {}
        # self.wg: StepWitnessGen = StepWitnessGen(F, Args)
        self.first_step: Optional[int] = None
        self.last_step: Optional[int] = None
        self.num_steps: int = None

    def add_signal(self, name: str) -> InternalSignal:
        signal = InternalSignal(name)
        self.signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_constr(self, annotation: str, expr: Expr):
        condition = Constraint(annotation, expr)
        self.constraints.append(condition)

    def add_transition(self, annotation: str, expr: Expr):
        condition = TransitionConstraint(annotation, expr)
        self.transition_constraints.append(condition)

    # def set_wg(self, defn):
    #     self.wg = defn

    def __eq__(self, other):
        if isinstance(other, StepType):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

class Constraint:
    def __init__(self, annotation: str, expr: Expr):
        self.annotation = annotation
        self.expr = expr

class TransitionConstraint:
    def __init__(self, annotation: str, expr: Expr):
        self.annotation = annotation
        self.expr = expr

class Circuit:
    def __init__(self):
        self.forward_signals: List[ForwardSignal] = []
        self.shared_signals: List[SharedSignal] = []
        self.fixed_signals: List[FixedSignal] = []
        self.exposed: List[ForwardSignal] = []
        # self.halo2_advice: List[ImportedHalo2Advice] = []
        # self.halo2_fixed: List[ImportedHalo2Fixed] = []
        self.step_types: Dict[int, StepType] = {}
        self.trace: Optional[callable] = None
        self.fixed_gen: Optional[callable] = None 
        self.annotations: Dict[int, str] = {}
        # self.first_step: Optional[StepTypeHandler] = None
        # self.last_step: Optional[StepTypeHandler] = None

    def add_forward(self, name: str, phase: int) -> ForwardSignal:
        signal = ForwardSignal(id=phase, annotation=name)
        self.forward_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_shared(self, name: str, phase: int) -> SharedSignal:
        signal = SharedSignal(id=phase, annotation=name)
        self.shared_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_fixed(self, name: str) -> FixedSignal:
        signal = FixedSignal(annotation=name)
        self.fixed_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def expose(self, forward_signal: ForwardSignal):
        self.exposed.append(forward_signal)

    # The following two functions are commented out as ImportedHalo2Advice and ImportedHalo2Fixed are not defined in Python
    # def add_halo2_advice(self, name: str, column: Halo2Column) -> ImportedHalo2Advice:
    #     advice = ImportedHalo2Advice(column, name)
    #     self.halo2_advice.append(advice)
    #     self.annotations[advice.uuid] = name
    #     return advice

    # def add_halo2_fixed(self, name: str, column: Halo2Column) -> ImportedHalo2Fixed:
    #     fixed = ImportedHalo2Fixed(column, name)
    #     self.halo2_fixed.append(fixed)
    #     self.annotations[fixed.uuid] = name
    #     return fixed

    def add_step_type(self, handler: StepTypeHandler, name: str):
        self.annotations[handler.id] = name

    def add_step_type_def(self, step: StepType) -> int:
        self.step_types[step.id] = step
        return step.id

    def set_trace(self, func: Callable[[TraceContext, TraceArgs], None]):
        if self.trace is not None:
            raise Exception("Circuit cannot have more than one trace generator.")
        else: 
            self.trace = func

    def set_fixed_gen(self, func: Callable[[FixedGenContext], None]):
        if self.fixed_gen is not None:
            raise Exception("Circuit cannot have more than one fixed generator.")
        else: 
            self.fixed_gen = func

    def get_step_type(self, uuid: int) -> StepType:
        if uuid in self.step_types:
            return self.step_types[uuid]
        else:
            raise ValueError("step type not found")
