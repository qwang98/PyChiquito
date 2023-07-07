from __future__ import annotations
import pprint

from pychiquito import CircuitContext, StepTypeContext, StepTypeSetupContext, StepTypeWGHandler, StepTypeHandler, Constraint, Queriable

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
        def trace_def(ctx: TraceContext, values: TraceArgs): # TODO: Complete wit_gen.py and update.
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
        c = self.internal("c")

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(Constraint.eq(circuit.a + circuit.b, c))
            ctx.transition(Constraint.eq(circuit.b, circuit.a.next()))
            ctx.transition(Constraint.eq(c, circuit.b.next()))
        self.setup(setup_def)

    def wg(self: FiboStep) -> StepTypeWGHandler:
        def wg_def(ctx: StepInstance, values: Args):
            # TODO: Implement after wit_gen.py is completed.
            pass
        return super().wg(wg_def)
        
class FiboLastStep(StepTypeContext):
    def __init__(self: FiboStep, circuit: Fibonacci, handler: StepTypeHandler):
        super().__init__(handler)
        c = self.internal("c")

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(Constraint.eq(circuit.a + circuit.b, c))
        self.setup(setup_def)
        
    def wg(self: FiboLastStep) -> StepTypeWGHandler:
        def wg_def(ctx: StepInstance, values: Args):
            # TODO: Implement after wit_gen.py is completed.
            pass
        return super().wg(wg_def)   

fibo = Fibonacci()
# pprint.pprint(fibo.circuit)
print(fibo.circuit) # Print ast::Circuit.