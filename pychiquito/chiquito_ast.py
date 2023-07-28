from __future__ import annotations
from typing import Callable, List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

from wit_gen import TraceContext, FixedGenContext, StepInstance
from expr import Expr
from util import uuid
from query import Queriable

#######
# ast #
#######

# pub struct ASTCircuit<F, TraceArgs> {
#     pub step_types: HashMap<u32, Rc<ASTStepType<F>>>,

#     pub forward_signals: Vec<ForwardSignal>,
#     pub shared_signals: Vec<SharedSignal>,
#     pub fixed_signals: Vec<FixedSignal>,
#     pub halo2_advice: Vec<ImportedHalo2Advice>,
#     pub halo2_fixed: Vec<ImportedHalo2Fixed>,
#     pub exposed: Vec<ForwardSignal>,

#     pub annotations: HashMap<u32, String>,

#     pub trace: Option<Rc<Trace<F, TraceArgs>>>,
#     pub fixed_gen: Option<Rc<FixedGen<F>>>,

#     pub first_step: Option<ASTStepTypeUUID>,
#     pub last_step: Option<ASTStepTypeUUID>,
#     pub num_steps: usize,
# }


@dataclass
class ASTCircuit:
    step_types: Dict[int, ASTStepType] = field(default_factory=dict)
    forward_signals: List[ForwardSignal] = field(default_factory=list)
    shared_signals: List[SharedSignal] = field(default_factory=list)
    fixed_signals: List[FixedSignal] = field(default_factory=list)
    exposed: List[Tuple[Queriable, ExposeOffset]] = field(default_factory=list)
    annotations: Dict[int, str] = field(default_factory=dict)
    trace: Optional[Callable[[TraceContext, Any], None]] = None
    fixed_gen: Optional[Callable] = None
    first_step: Optional[int] = None
    last_step: Optional[int] = None
    num_steps: int = 0
    q_enable: bool = True
    id: int = uuid()

    def __str__(self: ASTCircuit):
        step_types_str = (
            "\n\t\t"
            + ",\n\t\t".join(f"{k}: {v}" for k, v in self.step_types.items())
            + "\n\t"
            if self.step_types
            else ""
        )
        forward_signals_str = (
            "\n\t\t" + ",\n\t\t".join(str(fs) for fs in self.forward_signals) + "\n\t"
            if self.forward_signals
            else ""
        )
        shared_signals_str = (
            "\n\t\t" + ",\n\t\t".join(str(ss) for ss in self.shared_signals) + "\n\t"
            if self.shared_signals
            else ""
        )
        fixed_signals_str = (
            "\n\t\t" + ",\n\t\t".join(str(fs) for fs in self.fixed_signals) + "\n\t"
            if self.fixed_signals
            else ""
        )
        exposed_str = (
            "\n\t\t"
            + ",\n\t\t".join(f"({str(lhs)}, {str(rhs)})" for (lhs, rhs) in self.exposed)
            + "\n\t"
            if self.exposed
            else ""
        )
        annotations_str = (
            "\n\t\t"
            + ",\n\t\t".join(f"{k}: {v}" for k, v in self.annotations.items())
            + "\n\t"
            if self.annotations
            else ""
        )

        return (
            f"ASTCircuit(\n"
            f"\tstep_types={{{step_types_str}}},\n"
            f"\tforward_signals=[{forward_signals_str}],\n"
            f"\tshared_signals=[{shared_signals_str}],\n"
            f"\tfixed_signals=[{fixed_signals_str}],\n"
            f"\texposed=[{exposed_str}],\n"
            f"\tannotations={{{annotations_str}}},\n"
            f"\ttrace={self.trace},\n"
            f"\tfixed_gen={self.fixed_gen},\n"
            f"\tfirst_step={self.first_step},\n"
            f"\tlast_step={self.last_step},\n"
            f"\tnum_steps={self.num_steps}\n"
            f"\tq_enable={self.q_enable}\n"
            f")"
        )

    def __json__(self: ASTCircuit):
        return {
            "step_types": {k: v.__json__() for k, v in self.step_types.items()},
            "forward_signals": [x.__json__() for x in self.forward_signals],
            "shared_signals": [x.__json__() for x in self.shared_signals],
            "fixed_signals": [x.__json__() for x in self.fixed_signals],
            "exposed": [
                [queriable.__json__(), offset.__json__()]
                for (queriable, offset) in self.exposed
            ],
            "annotations": self.annotations,
            "first_step": self.first_step,
            "last_step": self.last_step,
            "num_steps": self.num_steps,
            "q_enable": self.q_enable,
            "id": self.id,
        }

    def add_forward(self: ASTCircuit, name: str, phase: int) -> ForwardSignal:
        signal = ForwardSignal(phase, name)
        self.forward_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_shared(self: ASTCircuit, name: str, phase: int) -> SharedSignal:
        signal = SharedSignal(phase, name)
        self.shared_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_fixed(self: ASTCircuit, name: str) -> FixedSignal:
        signal = FixedSignal(name)
        self.fixed_signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def expose(self: ASTCircuit, signal: Queriable, offset: ExposeOffset):
        self.exposed.append((signal, offset))

    def add_step_type(self: ASTCircuit, step_type: ASTStepType, name: str):
        self.annotations[step_type.id] = name
        self.step_types[step_type.id] = step_type

    def set_trace(
        self: ASTCircuit, trace_def: Callable[[TraceContext, Any], None]
    ):  # TraceArgs are Any.
        if self.trace is not None:
            raise Exception("ASTCircuit cannot have more than one trace generator.")
        else:
            self.trace = trace_def

    def set_fixed_gen(self, fixed_gen_def: Callable[[FixedGenContext], None]):
        if self.fixed_gen is not None:
            raise Exception("ASTCircuit cannot have more than one fixed generator.")
        else:
            self.fixed_gen = fixed_gen_def

    def get_step_type(self, uuid: int) -> ASTStepType:
        if uuid in self.step_types.keys():
            return self.step_types[uuid]
        else:
            raise ValueError("ASTStepType not found.")


# pub struct ASTStepType<F> {
#     id: StepTypeUUID,

#     pub name: String,
#     pub signals: Vec<InternalSignal>,
#     pub constraints: Vec<Constraint<F>>,
#     pub transition_constraints: Vec<TransitionConstraint<F>>,
#     pub lookups: Vec<Lookup<F>>,
#     pub annotations: HashMap<u32, String>,
# }


@dataclass
class ASTStepType:
    id: int
    name: str
    signals: List[InternalSignal]
    constraints: List[ASTConstraint]
    transition_constraints: List[TransitionConstraint]
    annotations: Dict[int, str]
    wg: Optional[
        Callable[[StepInstance, Any], None]
    ]  # Args are Any. Not passed to Rust Chiquito.

    def new(name: str) -> ASTStepType:
        return ASTStepType(uuid(), name, [], [], [], {}, None)

    def __str__(self):
        signals_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(str(signal) for signal in self.signals)
            + "\n\t\t\t"
            if self.signals
            else ""
        )
        constraints_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(str(constraint) for constraint in self.constraints)
            + "\n\t\t\t"
            if self.constraints
            else ""
        )
        transition_constraints_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(str(tc) for tc in self.transition_constraints)
            + "\n\t\t\t"
            if self.transition_constraints
            else ""
        )
        annotations_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(f"{k}: {v}" for k, v in self.annotations.items())
            + "\n\t\t\t"
            if self.annotations
            else ""
        )

        return (
            f"ASTStepType(\n"
            f"\t\t\tid={self.id},\n"
            f"\t\t\tname='{self.name}',\n"
            f"\t\t\tsignals=[{signals_str}],\n"
            f"\t\t\tconstraints=[{constraints_str}],\n"
            f"\t\t\ttransition_constraints=[{transition_constraints_str}],\n"
            f"\t\t\tannotations={{{annotations_str}}}\n"
            f"\t\t)"
        )

    def __json__(self):
        return {
            "id": self.id,
            "name": self.name,
            "signals": [x.__json__() for x in self.signals],
            "constraints": [x.__json__() for x in self.constraints],
            "transition_constraints": [
                x.__json__() for x in self.transition_constraints
            ],
            "annotations": self.annotations,
        }

    def add_signal(self: ASTStepType, name: str) -> InternalSignal:
        signal = InternalSignal(name)
        self.signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_constr(self: ASTStepType, annotation: str, expr: Expr):
        condition = ASTConstraint(annotation, expr)
        self.constraints.append(condition)

    def add_transition(self: ASTStepType, annotation: str, expr: Expr):
        condition = TransitionConstraint(annotation, expr)
        self.transition_constraints.append(condition)

    # Args are Any.
    def set_wg(self, wg_def: Callable[[StepInstance, Any], None]):
        self.wg = wg_def

    def __eq__(self: ASTStepType, other: ASTStepType) -> bool:
        if isinstance(self, ASTStepType) and isinstance(other, ASTStepType):
            return self.id == other.id
        return False

    def __req__(other: ASTStepType, self: ASTStepType) -> bool:
        return ASTStepType.__eq__(self, other)

    def __hash__(self: ASTStepType):
        return hash(self.id)


@dataclass
class ASTConstraint:
    annotation: str
    expr: Expr

    def __str__(self: ASTConstraint):
        return (
            f"Constraint(\n"
            f"\t\t\t\t\tannotation='{self.annotation}',\n"
            f"\t\t\t\t\texpr={self.expr}\n"
            f"\t\t\t\t)"
        )

    def __json__(self: ASTConstraint):
        return {"annotation": self.annotation, "expr": self.expr.__json__()}


@dataclass
class TransitionConstraint:
    annotation: str
    expr: Expr

    def __str__(self: TransitionConstraint):
        return f"TransitionConstraint({self.annotation})"

    def __json__(self: TransitionConstraint):
        return {"annotation": self.annotation, "expr": self.expr.__json__()}


@dataclass
class ForwardSignal:
    id: int
    phase: int
    annotation: str

    def __init__(self: ForwardSignal, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

    def __str__(self: ForwardSignal):
        return f"ForwardSignal(id={self.id}, phase={self.phase}, annotation='{self.annotation}')"

    def __json__(self: ForwardSignal):
        return asdict(self)


@dataclass
class SharedSignal:
    id: int
    phase: int
    annotation: str

    def __init__(self: SharedSignal, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

    def __str__(self: SharedSignal):
        return f"SharedSignal(id={self.id}, phase={self.phase}, annotation='{self.annotation}')"

    def __json__(self: SharedSignal):
        return asdict(self)


class ExposeOffset:
    pass


class First(ExposeOffset):
    def __str__(self: First):
        return "First"

    def __json__(self: First):
        return {"First": 0}


class Last(ExposeOffset):
    def __str__(self: Last):
        return "Last"

    def __json__(self: Last):
        return {"Last": -1}


@dataclass
class Step(ExposeOffset):
    offset: int

    def __str__(self: Step):
        return f"Step({self.offset})"

    def __json__(self: Step):
        return {"Step": self.offset}


@dataclass
class FixedSignal:
    id: int
    annotation: str

    def __init__(self: FixedSignal, annotation: str):
        self.id: int = uuid()
        self.annotation = annotation

    def __str__(self: FixedSignal):
        return f"FixedSignal(id={self.id}, annotation='{self.annotation}')"

    def __json__(self: FixedSignal):
        return asdict(self)


@dataclass
class InternalSignal:
    id: int
    annotation: str

    def __init__(self: InternalSignal, annotation: str):
        self.id = uuid()
        self.annotation = annotation

    def __str__(self: InternalSignal):
        return f"InternalSignal(id={self.id}, annotation='{self.annotation}')"

    def __json__(self: InternalSignal):
        return asdict(self)
