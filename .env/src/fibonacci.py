from __future__ import annotations
from typing import Any, Tuple
from py_ecc import bn128
import json
import rust_chiquito  # rust bindings

from dsl import CircuitContext, StepTypeContext, StepTypeSetupContext
from chiquito_ast import StepType
from cb import eq
from query import Queriable
from wit_gen import TraceContext, StepInstance, TraceGenerator

F = bn128.FQ


class Fibonacci(CircuitContext):
    def __init__(self: Fibonacci):
        super().__init__()
        self.a: Queriable = self.forward(
            "a"
        )  # `self.a` is required instead of `a`, because steps need to access `circuit.a`.
        self.b: Queriable = self.forward("b")

        self.fibo_step: StepTypeContext = self.step_type(FiboStep(self, "fibo_step"))
        self.fibo_last_step: StepTypeContext = self.step_type(
            FiboLastStep(self, "fibo_last_step")
        )

        self.pragma_first_step(self.fibo_step)
        # self.pragma_last_step(self.fibo_last_step)

    def trace(self: Fibonacci):
        def trace_def(ctx: TraceContext, _: Any):  # Any instead of TraceArgs
            ctx.add(self, self.fibo_step, (1, 1))
            a = 1
            b = 2
            for i in range(1, 10):
                ctx.add(self, self.fibo_step, (a, b))
                prev_a = a
                a = b
                b += prev_a
            ctx.add(self, self.fibo_last_step, (a, b))

        super().trace(trace_def)


class FiboStep(StepTypeContext):
    def __init__(self: FiboStep, circuit: Fibonacci, step_type_name: str):
        super().__init__(
            step_type_name
        )  # Pass the id and annotation of handler to a new StepTypeContext instance.
        self.c = self.internal(
            "c"
        )  # `self.c` is required instead of `c`, because wg needs to access `self.c`.

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(eq(circuit.a + circuit.b, self.c))
            ctx.transition(eq(circuit.b, circuit.a.next()))
            ctx.transition(eq(self.c, circuit.b.next()))

        self.setup(setup_def)

    def wg(self: FiboStep, circuit: Fibonacci):
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
            a_value, b_value = values
            # print(f"fib step wg: {a_value}, {b_value}, {a_value + b_value}")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))

        super().wg(wg_def)


class FiboLastStep(StepTypeContext):
    def __init__(self: FiboStep, circuit: Fibonacci, step_type: StepType):
        super().__init__(step_type)
        self.c = self.internal("c")

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(eq(circuit.a + circuit.b, self.c))

        self.setup(setup_def)

    def wg(self: FiboLastStep, circuit: Fibonacci):
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
            a_value, b_value = values
            print(f"fib last step wg: {a_value}, {b_value}, {a_value + b_value}\n")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))

        super().wg(wg_def)


# Print Circuit
fibo = Fibonacci()
fibo.trace()
print("Print Circuit using custom __str__ method in python:")
print(fibo.circuit)
print("Print Circuit using __json__ method in python:")


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        return super().default(obj)


circuit_json = json.dumps(fibo.circuit, cls=CustomEncoder, indent=4)
print(circuit_json)

# Print TraceWitness
trace_generator = TraceGenerator(fibo.circuit.trace)
trace_witness = trace_generator.generate(None)
print("Print TraceWitness using custom __str__ method in python:")
print(trace_witness)
print("Print TraceWitness using __json__ method in python:")
trace_witness_json = json.dumps(trace_witness, cls=CustomEncoder, indent=4)
print(trace_witness_json)

# Rust bindings for Circuit
print("Call rust bindings, parse json to Chiquito ast, and print using Debug trait:")
rust_chiquito.convert_and_print_ast(circuit_json)
