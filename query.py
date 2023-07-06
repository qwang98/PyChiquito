from __future__ import annotations
from typing import TypeVar, Generic, List, Dict, List
from chiquito_ast import InternalSignal, ForwardSignal, SharedSignal, FixedSignal
from expr import Expr, Query
from dataclasses import dataclass
from dsl import StepTypeHandler

F = bn128.FQ

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
