from typing import TypeVar, Generic, List, Dict, List

F = TypeVar('F')  # Type variable representing the generic type used in Expr

class Expr:
    def __init__(self, variant: str):
        # Ignore Halo2 types
        if variant not in ["Const", "Sum", "Mul", "Neg", "Pow", "Query"]:
            print("Invalid variant for Expr")
            # TODO: panic
        self.variant = variant
        self.data: Dict = {}
        self.data['expr']: List[Expr] = []
        self.data['pow']: int = None
        self.data['queriable']: Queriable = None

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
        
    
