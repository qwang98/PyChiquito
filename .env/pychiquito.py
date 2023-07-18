from __future__ import annotations
from typing import Callable, List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from py_ecc import bn128
import json

from util import uuid

F = bn128.FQ

# Monkey patching for __json__ method that doesn't exist in F.
# Returns the n: int field of super class FQ.
F.__json__ = lambda self: self.n

#######
# dsl #
#######


class CircuitContext:
    def __init__(self):
        self.circuit = Circuit()

    def forward(self: CircuitContext, name: str) -> Forward:
        return Forward(self.circuit.add_forward(name, 0), False)

    def forward_with_phase(self: CircuitContext, name: str, phase: int) -> Forward:
        return Forward(self.circuit.add_forward(name, phase), False)

    def shared(self: CircuitContext, name: str) -> Shared:
        return Shared(self.circuit.add_shared(name, 0), 0)

    def shared_with_phase(self: CircuitContext, name: str, phase: int) -> Shared:
        return Shared(self.circuit.add_shared(name, phase), 0)

    def fixed(self: CircuitContext, name: str) -> Fixed:
        return Fixed(self.circuit.add_fixed(name), 0)

    def expose(self: CircuitContext, forward: Queriable):
        if isinstance(forward, Forward):
            self.circuit.expose(forward.signal)
        else:
            raise ValueError("Can only expose a forward signal.")

    # TODO: Implement import_halo2_advice and import_halo2_fixed. Currently we ignore imported types.

    def step_type(
        self: CircuitContext, step_type_context: StepTypeContext
    ) -> StepTypeContext:
        self.circuit.add_step_type(
            step_type_context.step_type, step_type_context.step_type.name
        )
        return step_type_context

    def step_type_def(self: StepTypeContext) -> StepTypeContext:
        self.circuit.add_step_type_def()

    def trace(
        self: CircuitContext, trace_def: Callable[[TraceContext, Any], None]
    ):  # Any instead of TraceArgs
        self.circuit.set_trace(trace_def)

    def fixed_gen(
        self: CircuitContext, fixed_gen_def: Callable[[FixedGenContext], None]
    ):
        self.circuit.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(
        self: CircuitContext, step_type_context: StepTypeContext
    ) -> None:
        self.circuit.first_step = step_type_context.step_type.id

    def pragma_last_step(self, step_type_context: StepTypeContext) -> None:
        self.circuit.last_step = step_type_context.step_type.id

    def pragma_num_steps(self, num_steps: int) -> None:
        self.circuit.num_steps = num_steps


class StepTypeContext:
    def __init__(self: StepTypeContext, step_type_name: str):
        self.step_type = StepType.new(step_type_name)

    def internal(self: StepTypeContext, name: str) -> Internal:
        return Internal(self.step_type.add_signal(name))

    def setup(
        self: StepTypeContext, setup_def: Callable[[StepTypeSetupContext], None]
    ) -> None:  # def is a keyword in python
        ctx = StepTypeSetupContext(self.step_type)
        setup_def(ctx)
        print("setup called")

    def wg(
        self: StepTypeContext, wg_def: Callable[[TraceContext, Any], None]
    ):  # Any instead of Args
        self.step_type.set_wg(wg_def)


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
            raise ValueError(
                f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})"
            )

    # TODO: Implement add_lookup after lookup abstraction PR is merged.


def circuit(
    name: str, circuit_context_def: Callable[[CircuitContext], None]
) -> Circuit:
    ctx = CircuitContext()
    circuit_context_def(ctx)
    return ctx.circuit


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

    def from_expr(expr: Expr) -> Constraint:  # `from` is a reserved keyword in Python
        annotation: str = str(expr)
        if isinstance(expr, StepTypeNext):
            return Constraint(annotation, expr, Typing.Boolean)
        else:
            return Constraint(annotation, expr, Typing.Unknown)

    def __str__(self: Constraint) -> str:
        return self.annotation

    def cb_and(
        inputs: List[ToConstraint],
    ) -> Constraint:  # `and` is a reserved keyword in Python
        inputs = [to_constraint(input) for input in inputs]
        annotations: List[str] = []
        expr = Expr(Const(F(1)))
        for constraint in inputs:
            if (
                constraint.typing == Typing.Boolean
                or constraint.typing == Typing.Unknown
            ):
                annotations.append(constraint.annotation)
                expr = expr * constraint.expr
            else:
                raise ValueError(
                    f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})"
                )
        return Constraint(f"({' AND '.join(annotations)})", expr, Typing.Boolean)

    def cb_or(
        inputs: List[ToConstraint],
    ) -> Constraint:  # `or` is a reserved keyword in Python
        inputs = [to_constraint(input) for input in inputs]
        annotations: List[str] = []
        exprs: List[Expr] = []
        for constraint in inputs:
            if (
                constraint.typing == Typing.Boolean
                or constraint.typing == Typing.Unknown
            ):
                annotations.append(constraint.annotation)
                exprs.append(constraint.expr)
            else:
                raise ValueError(
                    f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})"
                )
        result: Constraint = Constraint.cb_not(
            Constraint.cb_and([Constraint.cb_not(expr) for expr in exprs])
        )
        return Constraint(f"({' OR '.join(annotations)})", result.expr, Typing.Boolean)

    def xor(lhs: ToConstraint, rhs: ToConstraint) -> Constraint:
        (lhs, rhs) = (to_constraint(lhs), to_constraint(rhs))
        if (lhs.typing == Typing.Boolean or lhs.typing == Typing.Unknown) and (
            rhs.typing == Typing.Boolean or rhs.typing == Typing.Unknown
        ):
            return Constraint(
                f"({lhs.annotation} XOR {rhs.annotation})",
                lhs.expr + rhs.expr - F(2) * lhs.expr * rhs.expr,
                Typing.Boolean,
            )
        else:
            raise ValueError(
                f"Expected Boolean or Unknown constraints, got AntiBooly in one of lhs or rhs constraints (lhs constraint: {lhs.annotation}) (rhs constraint: {rhs.annotation})"
            )

    def eq(lhs: ToConstraint, rhs: ToConstraint) -> Constraint:
        (lhs, rhs) = (to_constraint(lhs), to_constraint(rhs))
        return Constraint(
            f"({lhs.annotation} == {rhs.annotation})",
            lhs.expr - rhs.expr,
            Typing.AntiBooly,
        )

    def select(
        selector: ToConstraint, when_true: ToConstraint, when_false: ToConstraint
    ) -> Constraint:
        (selector, when_true, when_false) = (
            to_constraint(selector),
            to_constraint(when_true),
            to_constraint(when_false),
        )
        if selector.typing == Typing.AntiBooly:
            raise ValueError(
                f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})"
            )
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})else({when_false.annotation})",
            selector.expr * when_true.expr + (F(1) - selector.expr) * when_false.expr,
            when_true.typing
            if when_true.typing == when_false.typing
            else Typing.Unknown,
        )

    def when(selector: ToConstraint, when_true: ToConstraint) -> Constraint:
        (selector, when_true) = (to_constraint(selector), to_constraint(when_true))
        if selector.typing == Typing.AntiBooly:
            raise ValueError(
                f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})"
            )
        return Constraint(
            f"if({selector.annotation})then({when_true.annotation})",
            selector.expr * when_true.expr,
            when_true.typing,
        )

    def unless(selector: ToConstraint, when_false: ToConstraint) -> Constraint:
        (selector, when_false) = (to_constraint(selector), to_constraint(when_false))
        if selector.typing == Typing.AntiBooly:
            raise ValueError(
                f"Expected Boolean or Unknown selector, got AntiBooly (selector: {selector.annotation})"
            )
        return Constraint(
            f"unless({selector.annotation})then({when_false.annotation})",
            (F(1) - selector.expr) * when_false.expr,
            when_false.typing,
        )

    def cb_not(
        constraint: ToConstraint,
    ) -> Constraint:  # `not` is a reserved keyword in Python
        constraint = to_constraint(constraint)
        if constraint.typing == Typing.AntiBooly:
            raise ValueError(
                f"Expected Boolean or Unknown constraint, got AntiBooly (constraint: {constraint.annotation})"
            )
        return Constraint(
            f"NOT({constraint.annotation})", F(1) - constraint.expr, Typing.Boolean
        )

    def isz(constraint: ToConstraint) -> Constraint:
        constraint = to_constraint(constraint)
        return Constraint(
            f"0 == {constraint.annotation}", constraint.expr, Typing.AntiBooly
        )

    def if_next_step(step_type: StepType, constraint: ToConstraint) -> Constraint:
        constraint = to_constraint(constraint)
        return Constraint(
            f"if(next step is {step_type.annotation})then({constraint.annotation})",
            step_type.next()
            * constraint.expr,  # TODO: implement StepTypeHandler and its `next` method
            constraint.typing,
        )

    def next_step_must_be(step_type: StepType) -> Constraint:
        return Constraint(
            f"next step must be {step_type.annotation}",
            Constraint.cb_not(
                step_type.next()
            ),  # TODO: implement StepTypeHandler and its `next` method
            Typing.AntiBooly,
        )

    def next_step_must_not_be(step_type: StepType) -> Constraint:
        return Constraint(
            f"next step must not be {step_type.annotation}",
            step_type.next(),  # TODO: implement StepTypeHandler and its `next` method
            Typing.AntiBooly,
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


#######
# ast #
#######

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
    step_types: Dict[int, StepType] = field(default_factory=dict)
    forward_signals: List[ForwardSignal] = field(default_factory=list)
    shared_signals: List[SharedSignal] = field(default_factory=list)
    fixed_signals: List[FixedSignal] = field(default_factory=list)
    # halo2_advice: List[ImportedHalo2Advice] = field(default_factory=list)
    # halo2_fixed: List[ImportedHalo2Fixed] = field(default_factory=list)
    exposed: List[ForwardSignal] = field(default_factory=list)
    annotations: Dict[int, str] = field(default_factory=dict)
    trace: Optional[Callable[[TraceContext, Any], None]] = None
    fixed_gen: Optional[Callable] = None
    first_step: Optional[int] = None
    last_step: Optional[int] = None
    num_steps: int = 0
    id: int = uuid()

    def __str__(self: Circuit):
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
            "\n\t\t" + ",\n\t\t ".join(str(e) for e in self.exposed) + "\n\t"
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
            f"Circuit(\n"
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
            f")"
        )

    def __json__(self: Circuit):
        return {
            "step_types": {k: v.__json__() for k, v in self.step_types.items()},
            "forward_signals": [x.__json__() for x in self.forward_signals],
            "shared_signals": [x.__json__() for x in self.shared_signals],
            "fixed_signals": [x.__json__() for x in self.fixed_signals],
            "exposed": [x.__json__() for x in self.exposed],
            "annotations": self.annotations,
            "first_step": self.first_step,
            "last_step": self.last_step,
            "num_steps": self.num_steps,
            "id": self.id,
        }

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

    def add_step_type(self: Circuit, step_type: StepType, name: str):
        self.annotations[step_type.id] = name
        self.step_types[step_type.id] = step_type

    def set_trace(
        self: Circuit, trace_def: Callable[[TraceContext, Any], None]
    ):  # Any instead of TraceArgs
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
    constraints: List[ASTConstraint]
    transition_constraints: List[TransitionConstraint]
    annotations: Dict[int, str]
    wg: Optional[
        Callable[[StepInstance, Any], None]
    ]  # Any instead of Args. Not passed to Rust Chiquito.

    def new(name: str) -> StepType:
        return StepType(uuid(), name, [], [], [], {}, None)

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
            f"StepType(\n"
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

    def add_signal(self: StepType, name: str) -> InternalSignal:
        signal = InternalSignal(name)
        self.signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_constr(self: StepType, annotation: str, expr: Expr):
        condition = ASTConstraint(annotation, expr)
        self.constraints.append(condition)

    def add_transition(self: StepType, annotation: str, expr: Expr):
        condition = TransitionConstraint(annotation, expr)
        self.transition_constraints.append(condition)

    def set_wg(
        self, wg_def: Callable[[StepInstance, Any], None]
    ):  # Any instead of Args
        self.wg = wg_def

    def next(self: StepType) -> StepTypeNext:
        return StepTypeNext(self)

    def __eq__(self: StepType, other: StepType) -> bool:
        if isinstance(self, StepType) and isinstance(other, StepType):
            return self.id == other.id
        return False

    def __req__(other: StepType, self: StepType) -> bool:
        return StepType.__eq__(self, other)

    def __hash__(self: StepType):
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


############
# ast/expr #
############

# pub enum Expr<F> {
#     Const(F),
#     Sum(Vec<Expr<F>>),
#     Mul(Vec<Expr<F>>),
#     Neg(Box<Expr<F>>),
#     Pow(Box<Expr<F>>, u32),
#     Query(Queriable<F>),
#     Halo2Expr(Expression<F>),
# }


@dataclass
class Expr:
    def __neg__(self: Expr) -> Neg:
        return Neg(self)

    def __add__(self: Expr, rhs: ToExpr) -> Sum:
        rhs = to_expr(rhs)
        return Sum([self, rhs])

    def __radd__(self: Expr, lhs: ToExpr) -> Sum:
        return Expr.__add__(lhs, self)

    def __sub__(self: Expr, rhs: ToExpr) -> Sum:
        rhs = to_expr(rhs)
        return Sum([self, Neg(rhs)])

    def __rsub__(self: Expr, lhs: ToExpr) -> Sum:
        return Expr.__sub__(lhs, self)

    def __mul__(self: Expr, rhs: ToExpr) -> Mul:
        rhs = to_expr(rhs)
        return Mul([self, rhs])

    def __rmul__(self: Expr, lhs: ToExpr) -> Mul:
        return Expr.__mul__(lhs, self)

    def __pow__(self: Expr, rhs: int) -> Pow:
        return Pow(self, rhs)


@dataclass
class Const(Expr):
    value: F

    def __str__(self: Const) -> str:
        return str(self.value)

    def __json__(self):
        return {"Const": self.value}


@dataclass
class Sum(Expr):
    exprs: List[Expr]

    def __str__(self: Sum) -> str:
        result = "("
        for i, expr in enumerate(self.exprs):
            if type(expr) is Neg:
                if i == 0:
                    result += "-"
                else:
                    result += " - "
            else:
                if i > 0:
                    result += " + "
            result += str(expr)
        result += ")"
        return result

    def __json__(self):
        return {"Sum": [expr.__json__() for expr in self.exprs]}

    def __add__(self: Sum, rhs: ToExpr) -> Sum:
        rhs = to_expr(rhs)
        return Sum(self.exprs + [rhs])

    def __radd__(self: Sum, lhs: ToExpr) -> Sum:
        return Sum.__add__(lhs, self)

    def __sub__(self: Sum, rhs: ToExpr) -> Sum:
        rhs = to_expr(rhs)
        return Sum(self.exprs + [Neg(rhs)])

    def __rsub__(self: Sum, lhs: ToExpr) -> Sum:
        return Sum.__sub__(lhs, self)


@dataclass
class Mul(Expr):
    exprs: List[Expr]

    def __str__(self: Mul) -> str:
        return "*".join([str(expr) for expr in self.exprs])

    def __json__(self):
        return {"Mul": [expr.__json__() for expr in self.exprs]}

    def __mul__(self: Mul, rhs: ToExpr) -> Mul:
        rhs = to_expr(rhs)
        return Mul(self.exprs + [rhs])

    def __rmul__(self: Mul, lhs: ToExpr) -> Mul:
        return Mul.__mul__(lhs, self)


@dataclass
class Neg(Expr):
    expr: Expr

    def __str__(self: Neg) -> str:
        return "(-" + str(self.expr) + ")"

    def __json__(self):
        return {"Neg": self.expr.__json__()}

    def __neg__(self: Neg) -> Expr:
        return self.expr


@dataclass
class Pow(Expr):
    expr: Expr
    pow: int

    def __str__(self: Pow) -> str:
        return str(self.expr) + "^" + str(self.pow)

    def __json__(self):
        return {"Pow": [self.expr.__json__(), self.pow]}


# Ignored Expr::Halo2Expr.

######################
# ast/expr/queriable #
######################

# pub enum Queriable<F> {
#     Internal(InternalSignal),
#     Forward(ForwardSignal, bool),
#     Shared(SharedSignal, i32),
#     Fixed(FixedSignal, i32),
#     StepTypeNext(StepTypeHandler),
#     Halo2AdviceQuery(ImportedHalo2Advice, i32),
#     Halo2FixedQuery(ImportedHalo2Fixed, i32),
#     #[allow(non_camel_case_types)]
#     _unaccessible(PhantomData<F>),
# }


class Queriable(Expr):
    # __hash__ method is required, because Queriable is used as a key in the assignment dictionary.
    def __hash__(self: Queriable):
        return hash(self.uuid())

    # Implemented in all children classes, and only children instances will ever be created for Queriable.
    def uuid(self: Queriable) -> int:
        pass


# Not defined as @dataclass, because inherited __hash__ will be set to None.
class Internal(Queriable):
    def __init__(self: Internal, signal: InternalSignal):
        self.signal = signal

    def uuid(self: Internal) -> int:
        return self.signal.id

    def __str__(self: Internal) -> str:
        return self.signal.annotation

    def __json__(self):
        return {"Internal": self.signal.__json__()}


class Forward(Queriable):
    def __init__(self: Forward, signal: ForwardSignal, rotation: bool):
        self.signal = signal
        self.rotation = rotation

    def next(self: Forward) -> Forward:
        if self.rotation:
            raise ValueError("Cannot rotate Forward twice.")
        else:
            return Forward(self.signal, True)

    def uuid(self: Forward) -> int:
        return self.signal.id

    def __str__(self: Forward) -> str:
        if not self.rotation:
            return self.signal.annotation
        else:
            return f"next({self.signal.annotation})"

    def __json__(self):
        return {"Forward": [self.signal.__json__(), self.rotation]}


class Shared(Queriable):
    def __init__(self: Shared, signal: SharedSignal, rotation: int):
        self.signal = signal
        self.rotation = rotation

    def next(self: Shared) -> Shared:
        return Shared(self.signal, self.rotation + 1)

    def prev(self: Shared) -> Shared:
        return Shared(self.signal, self.rotation - 1)

    def rot(self: Shared, rotation: int) -> Shared:
        return Shared(self.signal, self.rotation + rotation)

    def uuid(self: Shared) -> int:
        return self.signal.id

    def __str__(self: Shared) -> str:
        if self.rotation == 0:
            return self.signal.annotation
        else:
            return f"{self.signal.annotation}(rot {self.rotation})"

    def __json__(self):
        return {"Shared": [self.signal.__json__(), self.rotation]}


class Fixed(Queriable):
    def __init__(self: Fixed, signal: FixedSignal, rotation: int):
        self.signal = signal
        self.rotation = rotation

    def next(self: Fixed) -> Fixed:
        return Fixed(self.signal, self.rotation + 1)

    def prev(self: Fixed) -> Fixed:
        return Fixed(self.signal, self.rotation - 1)

    def rot(self: Fixed, rotation: int) -> Fixed:
        return Fixed(self.signal, self.rotation + rotation)

    def uuid(self: Fixed) -> int:
        return self.signal.id

    def __str__(self: Fixed) -> str:
        if self.rotation == 0:
            return self.signal.annotation
        else:
            return f"{self.signal.annotation}(rot {self.rotation})"

    def __json__(self):
        return {"Fixed": [self.signal.__json__(), self.rotation]}


class StepTypeNext(Queriable):
    def __init__(self: StepTypeNext, step_type: StepType):
        self.step_type = step_type

    def uuid(self: StepType) -> int:
        return self.id

    def __str__(self: StepType) -> str:
        return self.name

    def __json__(self):
        return {
            "StepTypeNext": {"id": self.step_type.id, "annotation": self.step_type.name}
        }


# Ignored Queriable::Halo2AdviceQuery and Queriable::Halo2FixedQuery


################
# helper types #
################

ToExpr = Expr | int | F | Constraint


def to_expr(v: ToExpr) -> Expr:
    if isinstance(v, Expr):
        return v
    elif isinstance(v, int):
        if v >= 0:
            return Const(F(v))
        else:
            return Neg(Const(F(-v)))
    elif isinstance(v, F):
        return Const(v)
    elif isinstance(v, Constraint):
        return v.expr
    else:
        raise TypeError(
            f"Type {type(v)} is not ToExpr (one of Expr, int, F, or Constraint)."
        )


ToConstraint = Constraint | Expr | int | F


def to_constraint(v: ToConstraint) -> Constraint:
    if isinstance(v, Constraint):
        return v
    elif isinstance(v, Expr):
        if isinstance(v, StepTypeNext):
            return Constraint(str(v), v, Typing.Boolean)
        else:
            return Constraint(str(v), v, Typing.Unknown)
    elif isinstance(v, int):
        if v >= 0:
            return to_constraint(Const(F(v)))
        else:
            return to_constraint(Neg(Const(F(-v))))
    elif isinstance(v, F):
        return to_constraint(Const(v))
    else:
        raise TypeError(
            f"Type `{type(v)}` is not ToConstraint (one of Constraint, Expr, int, or F)."
        )


###########
# wit_gen #
###########


@dataclass
class StepInstance:
    step_type_uuid: int = 0
    assignments: Dict[Queriable, F] = field(default_factory=dict)

    def new(step_type_uuid: int) -> StepInstance:
        return StepInstance(step_type_uuid, {})

    def assign(self: StepInstance, lhs: Queriable, rhs: F):
        self.assignments[lhs] = rhs

    def __str__(self: StepInstance):
        assignments_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(
                f"{str(lhs)} = {rhs}" for (lhs, rhs) in self.assignments.items()
            )
            + "\n\t\t\t"
            if self.assignments
            else ""
        )
        return (
            f"StepInstance(\n"
            f"\t\t\tstep_type_uuid={self.step_type_uuid},\n"
            f"\t\t\tassignments={{{assignments_str}}},\n"
            f"\t\t)"
        )

    # For assignments, return "uuid: F" rather than "Queriable: F", because JSON doesn't accept Dict as key.
    def __json__(self: StepInstance):
        return {
            "step_type_uuid": self.step_type_uuid,
            "assignments": {lhs.uuid(): rhs for (lhs, rhs) in self.assignments.items()},
        }


Witness = List[StepInstance]


@dataclass
class TraceWitness:
    step_instances: Witness = field(default_factory=list)
    height: int = 0

    def __str__(self: TraceWitness):
        step_instances_str = (
            "\n\t\t"
            + ",\n\t\t".join(
                str(step_instance) for step_instance in self.step_instances
            )
            + "\n\t"
            if self.step_instances
            else ""
        )
        return (
            f"TraceWitness(\n"
            f"\tstep_instances={{{step_instances_str}}},\n"
            f"\theight={self.height},\n"
            f")"
        )

    def __json__(self: TraceWitness):
        return {
            "step_instances": [
                step_instance.__json__() for step_instance in self.step_instances
            ],
            "height": self.height,
        }


@dataclass
class TraceContext:
    witness: TraceWitness = field(default_factory=TraceWitness)

    def add(
        self: TraceContext, circuit: CircuitContext, step: StepTypeContext, args: Any
    ):  # StepTypeContext instead of StepTypeWGHandler, because StepTypeContext contains step type id and `wg` method that returns witness generation function
        witness = StepInstance.new(step.step_type.id)
        step.wg(circuit)
        if step.step_type.wg is None:
            raise ValueError(
                f"Step type {step.step_type.name} does not have a witness generator."
            )
        step.step_type.wg(witness, args)
        self.witness.step_instances.append(witness)

    def set_height(self: TraceContext, height: int):
        self.witness.height = height


Trace = Callable[[TraceContext, Any], None]  # Any instead of TraceArgs


@dataclass
class TraceGenerator:
    trace: Trace

    def generate(
        self: TraceGenerator, args: Any
    ) -> TraceWitness:  # Any instead of TraceArgs
        ctx = TraceContext()
        self.trace(ctx, args)
        return ctx.witness


FixedAssigment = Dict[Queriable, List[F]]


@dataclass
class FixedGenContext:
    assignments: FixedAssigment = field(default_factory=dict)
    num_steps: int = 0

    def new(num_steps: int) -> FixedGenContext:
        return FixedGenContext({}, num_steps)

    def assign(self: FixedGenContext, offset: int, lhs: Queriable, rhs: F):
        if not FixedGenContext.is_fixed_queriable(lhs):
            raise ValueError(f"Cannot assign to non-fixed signal.")
        if lhs in self.assignments.keys():
            self.assignments[lhs][offset] = rhs
        else:
            self.assignments[lhs] = [F.zero()] * self.num_steps
            self.assignments[lhs][offset] = rhs

    def is_fixed_queriable(q: Queriable) -> bool:
        match q.enum:
            case Fixed(_, _):  # Ignored Halo2FixedQuery enum type.
                return True
            case _:
                return False


########
# test #
########
# print(Internal(InternalSignal("a")).__json__())
# print(Forward(ForwardSignal(1, "a"), True).__json__())
# print(Shared(SharedSignal(0, "a"), 2).__json__())
# print(Fixed(FixedSignal("a"), 2).__json__())
# print(StepTypeNext(StepType.new("fibo")).__json__())
# print(ASTConstraint("constraint", Sum([Const(1), Mul([Internal(InternalSignal("a")), Const(3)])])).__json__())
# print(TransitionConstraint("trans", Sum([Const(1), Mul([Internal(InternalSignal("a")), Const(3)])])).__json__())
print(
    StepType(
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

# class StepType:
#     id: int
#     name: str
#     signals: List[InternalSignal]
#     constraints: List[ASTConstraint]
#     transition_constraints: List[TransitionConstraint]
#     annotations: Dict[int, str]
