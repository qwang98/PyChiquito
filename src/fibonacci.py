from __future__ import annotations
import pprint
from typing import Any, Tuple
from py_ecc import bn128

from pychiquito import CircuitContext, StepTypeContext, StepTypeSetupContext, StepTypeWGHandler, StepTypeHandler, Constraint, Queriable, TraceContext, StepInstance, TraceGenerator

F = bn128.FQ

class Fibonacci(CircuitContext):
    def __init__(self: Fibonacci):
        super().__init__()
        self.a: Queriable = self.forward("a") # `self.a` is required instead of `a`, because steps need to access `circuit.a`.
        self.b: Queriable = self.forward("b")

        fibo_step: StepTypeHandler = self.step_type("fibo_step")
        fibo_last_step: StepTypeHandler = self.step_type("fibo_last_step")

        self.pragma_first_step(fibo_step)
        self.pragma_last_step(fibo_last_step)
        
        self.fibo_step: StepTypeWGHandler = self.step_type_def(FiboStep(self, fibo_step))
        self.fibo_last_step: StepTypeWGHandler = self.step_type_def(FiboLastStep(self, fibo_last_step))

    def trace(self: Fibonacci):
        def trace_def(ctx: TraceContext, _: Any): # Any instead of TraceArgs
            ctx.add(self.fibo_step, (1, 1))
            a = 1
            b = 2
            for i in range(1, 10):
                ctx.add(self.fibo_step, (a, b))
                prev_a = a
                a = b
                b += prev_a
            ctx.add(self.fibo_last_step, (a, b))
        super().trace(trace_def)

class FiboStep(StepTypeContext):
    def __init__(self: FiboStep, circuit: Fibonacci, handler: StepTypeHandler):
        super().__init__(handler) # Pass the id and annotation of handler to a new StepTypeContext instance.
        self.c = self.internal("c") # `self.c` is required instead of `c`, because wg needs to access `self.c`.

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(Constraint.eq(circuit.a + circuit.b, self.c))
            ctx.transition(Constraint.eq(circuit.b, circuit.a.next()))
            ctx.transition(Constraint.eq(self.c, circuit.b.next()))
        self.setup(setup_def)

    def wg(self: FiboStep, circuit: Fibonacci) -> StepTypeWGHandler:
        def wg_def(ctx: StepInstance, values: Tuple[int, int]): # Any instead of Args
            a_value, b_value = values
            print(f"fib step wg: {a_value}, {b_value}, {a_value + b_value}")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))
        return super().wg(wg_def)
        
class FiboLastStep(StepTypeContext):
    def __init__(self: FiboStep, circuit: Fibonacci, handler: StepTypeHandler):
        super().__init__(handler)
        self.c = self.internal("c")

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(Constraint.eq(circuit.a + circuit.b, self.c))
        self.setup(setup_def)
        
    def wg(self: FiboLastStep, circuit: Fibonacci) -> StepTypeWGHandler:
        def wg_def(ctx: StepInstance, values: Tuple[int, int]): # Any instead of Args
            a_value, b_value = values
            print(f"fib last step wg: {a_value}, {b_value}, {a_value + b_value}\n")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))
        return super().wg(wg_def)

fibo = Fibonacci()
# pprint.pprint(fibo.circuit)
print(fibo.circuit) # Print ast::Circuit.
fibo.trace()
trace_generator = TraceGenerator(fibo.circuit.trace)
print(trace_generator.generate(None)) # Print TraceWitness
