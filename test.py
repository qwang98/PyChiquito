# from enum import Enum
# from dataclasses import dataclass

# class Queriable(Enum):
#     Internal = 1
#     Forward = 2
#     Shared = 3
#     Fixed = 4
#     StepTypeNext = 5
#     Halo2AdviceQuery = 6
#     Halo2FixedQuery = 7
#     _unaccessible = 8

# class InternalSignal: pass
# class ForwardSignal: pass
# class SharedSignal: pass
# class FixedSignal: pass
# class StepTypeHandler: pass
# class ImportedHalo2Advice: pass
# class ImportedHalo2Fixed: pass
# class PhantomData: pass

# @dataclass
# class Internal:
#     value: InternalSignal

# @dataclass
# class Forward:
#     signal: ForwardSignal
#     value: bool

# @dataclass
# class Shared:
#     signal: SharedSignal
#     value: int

# @dataclass
# class Fixed:
#     signal: FixedSignal
#     value: int

# @dataclass
# class StepTypeNext:
#     handler: StepTypeHandler

# @dataclass
# class Halo2AdviceQuery:
#     advice: ImportedHalo2Advice
#     value: int

# @dataclass
# class Halo2FixedQuery:
#     fixed: ImportedHalo2Fixed
#     value: int

# @dataclass
# class _unaccessible:
#     phantom: PhantomData

# Queriable.Forward.signal = Internal

from dataclasses import dataclass
from typing import List
@dataclass
class Expr:
    value: int

    @dataclass
    class Const:
        value: int
    
    @dataclass
    class Sum:
        exprs: List['Expr']

    def test():
        Expr.Sum([Expr.Const(1), Expr.Const(2)])
    
    def __add__(self, rhs: 'Expr'):
        if isinstance(self, Expr.Sum):
            self.exprs.append(rhs)
            return self
        else:
            return Expr.Sum([self, rhs])
            
print(Expr(1) + Expr(1))
print(Expr.Sum([Expr(1)]) + Expr.Sum([Expr(1)]))


# pub enum Expr<F> {
#     Const(F),
#     Sum(Vec<Expr<F>>),
#     Mul(Vec<Expr<F>>),
#     Neg(Box<Expr<F>>),
#     Pow(Box<Expr<F>>, u32),
#     Query(Queriable<F>),
#     Halo2Expr(Expression<F>),
# }