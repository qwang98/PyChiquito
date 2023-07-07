from __future__ import annotations
import pprint
from typing import Any, Tuple
from py_ecc import bn128

from pychiquito import (
    CircuitContext,
    StepTypeContext,
    StepTypeSetupContext,
    StepTypeWGHandler,
    StepTypeHandler,
    Constraint,
    Queriable,
    TraceContext,
    StepInstance,
    TraceGenerator,
)

F = bn128.FQ


class Fibonacci(CircuitContext):
    def __init__(self: Fibonacci):
        super().__init__()
        self.a: Queriable = self.forward(
            "a"
        )  # `self.a` is required instead of `a`, because steps need to access `circuit.a`.
        self.b: Queriable = self.forward("b")

        fibo_step: StepTypeHandler = self.step_type("fibo_step")
        fibo_last_step: StepTypeHandler = self.step_type("fibo_last_step")

        self.pragma_first_step(fibo_step)
        self.pragma_last_step(fibo_last_step)

        self.fibo_step: StepTypeWGHandler = self.step_type_def(
            FiboStep(self, fibo_step)
        )
        self.fibo_last_step: StepTypeWGHandler = self.step_type_def(
            FiboLastStep(self, fibo_last_step)
        )

    def trace(self: Fibonacci):
        def trace_def(ctx: TraceContext, _: Any):  # Any instead of TraceArgs
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
        super().__init__(
            handler
        )  # Pass the id and annotation of handler to a new StepTypeContext instance.
        self.c = self.internal(
            "c"
        )  # `self.c` is required instead of `c`, because wg needs to access `self.c`.

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(Constraint.eq(circuit.a + circuit.b, self.c))
            ctx.transition(Constraint.eq(circuit.b, circuit.a.next()))
            ctx.transition(Constraint.eq(self.c, circuit.b.next()))

        self.setup(setup_def)

    def wg(self: FiboStep, circuit: Fibonacci) -> StepTypeWGHandler:
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
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
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
            a_value, b_value = values
            print(f"fib last step wg: {a_value}, {b_value}, {a_value + b_value}\n")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))

        return super().wg(wg_def)


fibo = Fibonacci()
# pprint.pprint(fibo.circuit)
print(fibo.circuit)  # Print ast::Circuit.
fibo.trace()
trace_generator = TraceGenerator(fibo.circuit.trace)
print(trace_generator.generate(None))  # Print TraceWitness

# ast::Circuit output:

# Circuit(
#         step_types={
#                 3: StepType(
#                         id=3,
#                         name='fibo_step',
#                         signals=[
#                                 InternalSignal(id=5, annotation='c')
#                         ],
#                         constraints=[
#                                 Constraint(
#                                         annotation='((a + b) == c)',
#                                         expr=(a + b - c)
#                                 )
#                         ],
#                         transition_constraints=[
#                                 TransitionConstraint((b == next(a))),
#                                 TransitionConstraint((c == next(b)))
#                         ],
#                         annotations={
#                                 5: c
#                         }
#                 ),
#                 4: StepType(
#                         id=4,
#                         name='fibo_last_step',
#                         signals=[
#                                 InternalSignal(id=6, annotation='c')
#                         ],
#                         constraints=[
#                                 Constraint(
#                                         annotation='((a + b) == c)',
#                                         expr=(a + b - c)
#                                 )
#                         ],
#                         transition_constraints=[],
#                         annotations={
#                                 6: c
#                         }
#                 )
#         },
#         forward_signals=[
#                 ForwardSignal(id=1, phase=0, annotation='a'),
#                 ForwardSignal(id=2, phase=0, annotation='b')
#         ],
#         shared_signals=[],
#         fixed_signals=[],
#         exposed=[],
#         annotations={
#                 1: a,
#                 2: b,
#                 3: fibo_step,
#                 4: fibo_last_step
#         },
#         trace=None,
#         fixed_gen=None,
#         first_step=3,
#         last_step=4,
#         num_steps=0
# )

# TraceWitness output:

# TraceWitness(
#         step_instances={
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 1,
#                                 b = 1,
#                                 c = 2
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 1,
#                                 b = 2,
#                                 c = 3
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 2,
#                                 b = 3,
#                                 c = 5
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 3,
#                                 b = 5,
#                                 c = 8
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 5,
#                                 b = 8,
#                                 c = 13
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 8,
#                                 b = 13,
#                                 c = 21
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 13,
#                                 b = 21,
#                                 c = 34
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 21,
#                                 b = 34,
#                                 c = 55
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 34,
#                                 b = 55,
#                                 c = 89
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=3,
#                         assignments={
#                                 a = 55,
#                                 b = 89,
#                                 c = 144
#                         },
#                 ),
#                 StepInstance(
#                         step_type_uuid=4,
#                         assignments={
#                                 a = 89,
#                                 b = 144,
#                                 c = 233
#                         },
#                 )
#         },
#         height=0,
# )
