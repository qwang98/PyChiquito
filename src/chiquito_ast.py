from __future__ import annotations
from typing import Callable, List, Dict, Optional
from dataclasses import dataclass
from py_ecc import bn128

from util import uuid
from dsl import StepTypeHandler, Constraint

F = bn128.FQ

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
class Const:
    value: F

@dataclass
class Sum:
    exprs: List[Expr]

@dataclass
class Mul:
    exprs: List[Expr]

@dataclass
class Neg:
    expr: Expr

@dataclass
class Pow:
    expr: Expr
    pow: int

@dataclass
class Query:
    queriable: Queriable

# Ignored Expr::Halo2Expr.

@dataclass
class Expr:
    enum: Const | Sum | Mul | Neg | Pow | Query

    def __str__(self: Expr) -> str:
        match expr.enum:
            case Const(value):
                return str(value)
            case Sum(exprs):
                result = "("
                for i, expr in enumerate(exprs):
                    match expr.enum:
                        case Neg(expr):
                            if i == 0:
                                result += "-"
                            else:
                                result += " - "
                        case _:
                            result += " + "
                    result += str(expr)
                result += ")"
                return result
            case Mul(exprs):
                return "*".join([str(expr) for expr in exprs])
            case Neg(expr):
                return "(-" + str(expr) + ")"
            case Pow(expr, pow):
                return str(expr) + "^" + str(pow)
            case Query(queriable):
                return str(queriable)
            case _:
                raise ValueError("Invalid Expr enum type.")
             
    def __neg__(self: Expr) -> Expr:
        match self.enum:
            case Neg(e):
                return e
            case _:
                return Expr(Neg(self))

    def __add__(lhs: ToExpr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(lhs), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [rhs]))
            case (_, Sum(exprs)):
                return Expr(Sum([lhs] + exprs))
            case _:
                return Expr(Sum([lhs, rhs]))
    
    def __radd__(rhs: ToExpr, lhs: ToExpr) -> Expr:
        return Expr.__add__(lhs, rhs)
                
    def __sub__(lhs: ToExpr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(lhs), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [Expr(Neg(rhs))]))
            case _:
                return Expr(Sum([lhs, Expr(Neg(rhs))]))
    
    def __rsub__(rhs: ToExpr, lhs: ToExpr) -> Expr:
        return Expr.__sub__(lhs, rhs)

    def __mul__(lhs: ToExpr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(lhs), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Mul(exprs), _):
                return Expr(Mul(exprs + [rhs]))
            case (_, Mul(exprs)):
                return Expr(Mul([lhs] + exprs))
            case _:
                return Expr(Mul([lhs, rhs]))

    def __rmul__(rhs: ToExpr, lhs: ToExpr) -> Expr:
        return Expr.__mul__(lhs, rhs)
  
    def __pow__(lhs: ToExpr, rhs: int) -> Expr:
        lhs = to_expr(lhs)
        return Expr(Pow(lhs, rhs))

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

@dataclass
class Internal:
    signal: InternalSignal

@dataclass
class Forward:
    signal: ForwardSignal
    rotation: bool

@dataclass
class Shared:
    signal: SharedSignal
    rotation: int

@dataclass
class Fixed:
    signal: FixedSignal
    rotation: int

@dataclass
class StepTypeNext:
    handler: StepTypeHandler

# Ignored Queriable::Halo2AdviceQuery and Queriable::Halo2FixedQuery

@dataclass
class Queriable:
    enum: Internal | Forward | Shared | Fixed | StepTypeNext

    def next(self: Queriable) -> Queriable:
        match self.enum:
            case Forward(signal, rotation):
                if rotation:
                    raise ValueError("Cannot rotate Forward twice.")
                else:
                    return Queriable(Forward(signal, True))
            case Shared(signal, rotation):
                return Queriable(Shared(signal, rotation + 1))
            case Fixed(signal, rotation):
                return Queriable(Fixed(signal, rotation + 1))
            case _:
                raise ValueError("Can only call `next` on Forward, Shared, or Fixed.")
    
    def prev(self: Queriable) -> Queriable:
        match self.enum:
            case Shared(signal, rotation):
                return Queriable(Shared(signal, rotation - 1))
            case Fixed(signal, rotation):
                return Queriable(Fixed(signal, rotation - 1))
            case _:
                raise ValueError("Can only call `prev` on Shared or Fixed.")

    def rot(self: Queriable, rotation: int) -> Queriable:
        match self.enum:
            case Shared(signal, rot):
                return Queriable(Shared(signal, rot + rotation))
            case Fixed(signal, rot):
                return Queriable(Fixed(signal, rot + rotation))
            case _:
                raise ValueError("Can only call `rot` on Shared or Fixed.")
    
    def uuid(self: Queriable) -> int:
        match self.enum:
            case Internal(signal):
                return signal.id
            case Forward(signal, _):
                return signal.id
            case Shared(signal, _):
                return signal.id
            case Fixed(signal, _):
                return signal.id
            case StepTypeNext(handler):
                return handler.id
            case _:
                raise ValueError("Invalid Queriable enum type.")

    def annotation(self: Queriable) -> str:
        match self.enum:
            case Internal(signal):
                return signal.annotation
            case Forward(signal, rotation):
                if not rotation:
                    return signal.annotation
                else:
                    return f"next({signal.annotation})"
            case Shared(signal, rotation):
                if rotation == 0:
                    return signal.annotation
                else:
                    return f"{signal.annotation}(rot {rotation})"
            case Fixed(signal, rotation):
                if rotation == 0:
                    return signal.annotation
                else:
                    return f"{signal.annotation}(rot {rotation})"
            case StepTypeNext(handler):
                return handler.annotation
            case _:
                raise ValueError("Invalid Queriable enum type.")

ToExpr = Expr | str | int | F | Queriable | Constraint

def to_expr(v: ToExpr) -> Expr:
    if isinstance(v, Expr):
        return v
    elif isinstance(v, F):
        return Expr(Const(v))
    elif isinstance(v, int):
        if v >= 0:
            return Expr(Const(F(v)))
        else:
            return Expr(Neg(Expr(Const(F(-v)))))
    elif isinstance(v, Queriable):
        return Expr(Query(v))
    elif isinstance(v, Constraint):
        return v.expr
    else:
        raise TypeError(f"Type `{type(v)}` is not ToExpr (one of Expr, str, int, F, Queriable, or Constraint).")
