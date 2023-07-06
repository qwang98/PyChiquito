from __future__ import annotations
from typing import List
from cb import Constraint
from py_ecc import bn128
from dataclasses import dataclass
from query import Queriable

F = bn128.FQ

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
