from chiquito_ast import Circuit
from typing import Callable

class CircuitContext:
    def __init__(self):
        self.circuit = Circuit()

    def forward(self, name: str) -> Queriable:
        

def circuit(name: str, circuit_context_lambda: Callable[[CircuitContext], None]) -> Circuit:
    ctx = CircuitContext()
    circuit_context_lambda(ctx)
    return ctx.circuit