from __future__ import annotations
from typing import Callable, List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from py_ecc import bn128

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
    
    # StepTypeContext is generated by initialising a custom-defined step type class.
    # The step type class should have a wg function that returns a StepTypeWGHandler.
    def step_type_def(self: CircuitContext, context: StepTypeContext) -> StepTypeWGHandler:
        self.circuit.add_step_type_def(context.step_type)
        return context.wg()

    # def step_type_def(self: CircuitContext, step: StepTypeDefInput, step_type_func: Callable[[StepTypeContext], StepTypeWGHandler]) -> StepTypeWGHandler:
    #     match step:
    #         case StepTypeDefInput(Handler(h)):
    #             handler = h
    #         case StepTypeDefInput(String(name)):
    #             handler = StepTypeHandler.new(name)
    #             self.circuit.add_step_type(handler, name)
    #         case _:
    #             raise ValueError("Invalid StepTypeDefInput enum type.")
    #     context = StepTypeContext.new(handler.id, handler.annotation)
    #     result = step_type_func(context)
    #     self.circuit.add_step_type_def(context.step_type)
    #     return result
    
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

class StepTypeContext:
    def __init__(self: StepTypeContext, handler: StepTypeHandler):
        self.step_type: StepType = StepType(handler.id, handler.annotation)
    
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
    trace: Optional[Callable] = None
    fixed_gen: Optional[Callable] = None
    first_step: Optional[int] = None
    last_step: Optional[int] = None
    num_steps: int = 0

    def __str__(self):
        step_types_str = "\n\t\t" + ',\n\t\t'.join(f'{k}: {v}' for k, v in self.step_types.items()) + "\n\t" if self.step_types else ""
        forward_signals_str = "\n\t\t" + ',\n\t\t'.join(str(fs) for fs in self.forward_signals) + "\n\t" if self.forward_signals else ""
        shared_signals_str = "\n\t\t" + ',\n\t\t'.join(str(ss) for ss in self.shared_signals) + "\n\t" if self.shared_signals else ""
        fixed_signals_str = "\n\t\t" + ',\n\t\t'.join(str(fs) for fs in self.fixed_signals) + "\n\t" if self.fixed_signals else ""
        exposed_str = "\n\t\t" + ',\n\t\t '.join(str(e) for e in self.exposed) + "\n\t" if self.exposed else ""
        annotations_str = "\n\t\t" + ',\n\t\t'.join(f'{k}: {v}' for k, v in self.annotations.items()) + "\n\t" if self.annotations else ""

        return (f"Circuit(\n"
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
                f")")

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

class StepType:
    def __init__(self: StepType, id: int, name: str):
        self.id = id
        self.name = name
        self.signals: List[InternalSignal] = []
        self.constraints: List[ASTConstraint] = []
        self.transition_constraints: List[TransitionConstraint] = []
        self.annotations: Dict[int, str] = {}

    def __str__(self):
        signals_str = "\n\t\t\t\t" + ',\n\t\t\t\t'.join(str(signal) for signal in self.signals) + "\n\t\t\t" if self.signals else ""
        constraints_str = "\n\t\t\t\t" + ',\n\t\t\t\t'.join(str(constraint) for constraint in self.constraints) + "\n\t\t\t" if self.constraints else ""
        transition_constraints_str = "\n\t\t\t\t" + ',\n\t\t\t\t'.join(str(tc) for tc in self.transition_constraints) + "\n\t\t\t" if self.transition_constraints else ""
        annotations_str = "\n\t\t\t\t" + ',\n\t\t\t\t'.join(f'{k}: {v}' for k, v in self.annotations.items()) + "\n\t\t\t" if self.annotations else ""

        return (f"StepType(\n"
                f"\t\t\tid={self.id},\n"
                f"\t\t\tname='{self.name}',\n"
                f"\t\t\tsignals=[{signals_str}],\n"
                f"\t\t\tconstraints=[{constraints_str}],\n"
                f"\t\t\ttransition_constraints=[{transition_constraints_str}],\n"
                f"\t\t\tannotations={{{annotations_str}}}\n"
                f"\t\t)")

    def add_signal(self: StepType, name: str) -> InternalSignal:
        signal = InternalSignal(name)
        self.signals.append(signal)
        self.annotations[signal.id] = name
        return signal

    def add_constr(self: StepType, annotation: str, expr: Expr):
        condition = ASTConstraint(annotation, expr)
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
class ASTConstraint:
    annotation: str
    expr: Expr

    def __str__(self):
        return (f"Constraint(\n"
                f"\t\t\t\t\tannotation='{self.annotation}',\n"
                f"\t\t\t\t\texpr={self.expr}\n"
                f"\t\t\t\t)")

@dataclass
class TransitionConstraint:
    annotation: str
    expr: Expr

    def __str__(self):
        return (f"TransitionConstraint({self.annotation})")

@dataclass
class ForwardSignal:
    id: int
    phase: int
    annotation: str

    def __init__(self, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation

    def __str__(self):
        return f"ForwardSignal(id={self.id}, phase={self.phase}, annotation='{self.annotation}')"    

@dataclass
class SharedSignal:
    id: int
    phase: int
    anotation: str

    def __init__(self: SharedSignal, phase: int, annotation: str):
        self.id: int = uuid()
        self.phase = phase
        self.annotation = annotation
   
    def __str__(self):
        return f"SharedSignal(id={self.id}, phase={self.phase}, annotation='{self.annotation}')"

@dataclass
class FixedSignal:
    id: int
    annotation: str

    def __init__(self: FixedSignal, annotation: str):
        self.id: int = uuid()
        self.annotation = annotation
    
    def __str__(self):
        return f"FixedSignal(id={self.id}, annotation='{self.annotation}')"

@dataclass
class InternalSignal:
    id: int
    annotation: str

    def __init__(self, annotation: str):
        self.id = uuid()
        self.annotation = annotation

    def __str__(self):
        return f"InternalSignal(id={self.id}, annotation='{self.annotation}')"

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
        match self.enum:
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
                            if i > 0:
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
                return queriable.annotation()
            case _:
                raise ValueError("Invalid Expr enum type.")
             
    def __neg__(self: Expr) -> Expr:
        match self.enum:
            case Neg(e):
                return e
            case _:
                return Expr(Neg(self))

    def __add__(self: Expr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [rhs]))
            case (_, Sum(exprs)):
                return Expr(Sum([lhs] + exprs))
            case _:
                return Expr(Sum([lhs, rhs]))
    
    def __radd__(self: Expr, lhs: ToExpr) -> Expr:
        return Expr.__add__(lhs, self)
                
    def __sub__(self: Expr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [Expr(Neg(rhs))]))
            case _:
                return Expr(Sum([lhs, Expr(Neg(rhs))]))
    
    def __rsub__(self: Expr, lhs: ToExpr) -> Expr:
        return Expr.__sub__(lhs, self)

    def __mul__(self: Expr, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Mul(exprs), _):
                return Expr(Mul(exprs + [rhs]))
            case (_, Mul(exprs)):
                return Expr(Mul([lhs] + exprs))
            case _:
                return Expr(Mul([lhs, rhs]))

    def __rmul__(self: Expr, lhs: ToExpr) -> Expr:
        return Expr.__mul__(lhs, self)
  
    def __pow__(self: Expr, rhs: int) -> Expr:
        lhs = to_expr(self)
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
            
    def __neg__(self: Queriable) -> Expr:
        match self.enum:
            case Neg(e):
                return e
            case _:
                return Expr(Neg(self))

    def __add__(self: Queriable, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [rhs]))
            case (_, Sum(exprs)):
                return Expr(Sum([lhs] + exprs))
            case _:
                return Expr(Sum([lhs, rhs]))
    
    def __radd__(self: Queriable, lhs: ToExpr) -> Expr:
        return Expr.__add__(lhs, self)
                
    def __sub__(self: Queriable, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Sum(exprs), _):
                return Expr(Sum(exprs + [Expr(Neg(rhs))]))
            case _:
                return Expr(Sum([lhs, Expr(Neg(rhs))]))
    
    def __rsub__(self: Queriable, lhs: ToExpr) -> Expr:
        return Expr.__sub__(lhs, self)

    def __mul__(self: Queriable, rhs: ToExpr) -> Expr:
        (lhs, rhs) = (to_expr(self), to_expr(rhs))
        match (lhs.enum, rhs.enum):
            case (Mul(exprs), _):
                return Expr(Mul(exprs + [rhs]))
            case (_, Mul(exprs)):
                return Expr(Mul([lhs] + exprs))
            case _:
                return Expr(Mul([lhs, rhs]))

    def __rmul__(self: Queriable, lhs: ToExpr) -> Expr:
        return Expr.__mul__(lhs, self)
  
    def __pow__(self: Queriable, rhs: int) -> Expr:
        lhs = to_expr(self)
        return Expr(Pow(lhs, rhs))

################
# helper types #
################

ToExpr = Expr | int | F | Queriable | Constraint

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
        raise TypeError(f"Type {type(v)} is not ToExpr (one of Expr, str, int, F, Queriable, or Constraint).")

ToConstraint = Constraint | Expr | int | F | Queriable

def to_constraint(v: ToConstraint) -> Constraint:
    if isinstance(v, Constraint):
        return v
    elif isinstance(v, Expr):
        match v:
            case Expr(Query(Queriable(StepTypeNext(_)))):
                return Constraint(str(v), v, Typing.Boolean)
            case _:
                return Constraint(str(v), v, Typing.Unknown)
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
