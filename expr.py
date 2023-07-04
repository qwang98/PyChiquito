from typing import TypeVar, Generic, List

F = TypeVar('F')  # Type variable representing the generic type used in Expr

class Expr(Generic[F]):
    def __init__(self, value: F):
        self.value = value

class Sum(Expr[F]):
    def __init__(self, expressions: List[Expr[F]]):
        self.expressions = expressions

class Mul(Expr[F]):
    def __init__(self, expressions: List[Expr[F]]):
        self.expressions = expressions

class Neg(Expr[F]):
    def __init__(self, expression: Expr[F]):
        self.expression = expression

class Pow(Expr[F]):
    def __init__(self, expression: Expr[F], power: int):
        self.expression = expression
        self.power = power

class Query(Expr[F]):
    def __init__(self, queriable: Queriable[F]):
        self.queriable = queriable

class Halo2Expr(Expr[F]):
    def __init__(self, expression: Expression[F]):
        self.expression = expression

