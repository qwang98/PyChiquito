from typing import TypeVar, Generic, List, Dict, List
from chiquito_ast import InternalSignal, ForwardSignal, SharedSignal, FixedSignal
from expr import Expr

class Queriable:
    def __init__(self, variant: str):
        if variant not in ["Internal", "Forward", "Shared", "Fixed", "StepTypeNext"]:
            raise ValueError("Invalid variant for Queriable.")
        self.variant = variant
        self.data: Dict = {}
        self.data['internal']: InternalSignal = None
        self.data['forward']: ForwardSignal = None
        self.data['shared']: SharedSignal = None
        self.data['fixed']: FixedSignal = None
        self.data['step_type_next']: StepTypeHandler = None
        self.data['rotation']: int = 0

    def next(self) -> Queriable:
        if self.variant == "Forward":
            if self.data['rotation'] > 0:
                raise ValueError("Cannot rotate forward signal twice")
            else:
                self.data['rotation'] += 1
                return self
        if self.variant in ["Shared", "Fixed"]:
            self.data['rotation'] += 1
            return self
        else:
            raise ValueError("Can only call `next` on a forward, shared, or fixed signal.")

    def prev(self) -> Queriable:
        if self.variant in ["Shared", "Fixed"]:
            self.data['rotation'] -= 1
            return self
        else:
            raise ValueError("Can only call `prev` on a shared or fixed signal.")
    
    def rot(self, rotation: int) -> Queriable:
        if self.variant in ["Shared", "Fixed"]:
            self.data['rotation'] += rotation
            return self
        else:
            raise ValueError("Can only call `rot` on a shared or fixed signal.")

    def uuid(self) -> int:
        if self.variant == "Internal":
            return self.data['internal'].id
        elif self.variant == "Forward":
            return self.data['forward'].id
        elif self.variant == "Shared":
            return self.data['shared'].id
        elif self.variant == "Fixed":
            return self.data['fixed'].id
        elif self.variant == "StepTypeNext":
            return self.data['step_type_next'].id
        else:
            raise ValueError("Invalid variant for Queriable.")
    
    def annotation(self) -> str:
        if self.variant == "Internal":
            return self.data['internal'].annotation
        elif self.variant == "Forward":
            if self.data['rotation'] == 0:
                return self.data['forward'].annotation
            elif self.data['rotation'] == 1:
                return f"next({self.data['forward'].annotation})"
            else:
                raise ValueError("Invalid rotation value for forward signal.")
        elif self.variant == "Shared":
            if self.data['rotation'] != 0:
                return f"{self.data['shared'].annotation}(rot {self.data['rotation']})"
            else:
                return self.data['shared'].annotation
        elif self.variant == "Fixed":
            if self.data['rotation'] != 0:
                return f"{self.data['fixed'].annotation}(rot {self.data['rotation']})"
            else:
                return self.data['fixed'].annotation
        elif self.variant == "StepTypeNext":
            return self.data['step_type_next'].annotation
        else:
            raise ValueError("Invalid variant for Queriable.")

    def expr(self) -> Expr:
        out = Expr("Query")
        out.data["queriable"] = self
        return out

    def __add__(self, rhs: Expr):
        return self.expr() + rhs

    def __sub__(self, rhs: Expr):
        return self.expr() - rhs
    
    def __mul__(self, rhs: Expr):
        return self.expr() * rhs
    
    def __neg__(self):
        return -self.expr()
