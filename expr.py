from typing import TypeVar, Generic, List, Dict, List
from cb import Constraint

F = TypeVar('F')  # Type variable representing the generic type used in Expr

class Expr:
    def __init__(self, variant: str):
        # Ignore Halo2 types
        # Pow variant isn't really used
        if variant not in ["Const", "Sum", "Mul", "Neg", "Pow", "Query"]:
            raise ValueError("Invalid variant for Expr.")
        self.variant = variant
        self.data: Dict = {}
        self.data['value']: int = None # TODO: make this a field element
        self.data['expr']: List[Expr] = []
        self.data['pow']: int = None 
        self.data['queriable']: Queriable = None

    def __repr__(self):
        if self.variant == "Const":
            return self.data['expr']
        elif self.variant == "Sum":
            expr_reprs = [repr(expr) for expr in self.data['expr']]
            return "(" + " + ".join(expr_reprs) + ")"
        elif self.variant == "Mul":
            expr_reprs = [repr(expr) for expr in self.data['expr']]
            return "(" + " * ".join(expr_reprs) + ")"
        elif self.variant == "Neg":
            return "-" + repr(self.data['expr'][0])
        elif self.variant == "Pow":
            return "(" + repr(self.data['expr'][0]) + ")^" + str(self.data['pow'])
        elif self.variant == "Query":
            return repr(self.data['queriable'])
        else:
            raise ValueError("Invalid variant for Expr.")

    def __add__(self, rhs: Expr):
        if self.variant == "Sum":
            self.data["expr"].append(rhs)
            return self
        else:
            out = Expr("Sum")
            out.data["expr"].extend([self, rhs])
            return out
    
    def __sub__(self, rhs: Expr):
        neg = Expr("Neg")
        neg.data["expr"].append(rhs)
        if self.variant == "Sum":
            self.data["expr"].append(neg)
            return self
        else:
            out = Expr("Sum")
            out.data["expr"].extend([self, rhs])
            return out
    
    def __mul__(self, rhs: Expr):
        if self.variant == "Mul":
            self.data["expr"].append(rhs)
            return self
        else:
            out = Expr("Mul")
            out.data["expr"].extend([self, rhs])
            return out
        
    def __neg__(self):
        if self.variant == "Neg":
            return self.data["expr"][0]
        else:
            out = Expr("Neg")
            out.data["expr"].append(self)
            return out
        
    
