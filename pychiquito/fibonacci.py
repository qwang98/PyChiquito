from __future__ import annotations
from typing import Any, Tuple
from py_ecc import bn128
import json

from dsl import Circuit, StepType
from chiquito_ast import ASTStepType, First, Last, Step
from cb import eq
from query import Queriable
from wit_gen import TraceContext, StepInstance, TraceGenerator
from util import CustomEncoder, F

F = bn128.FQ


class Fibonacci(Circuit):
    def setup(self: Fibonacci):
        self.a: Queriable = self.forward("a")
        self.b: Queriable = self.forward("b")

        self.fibo_step = self.step_type(FiboStep(self, "fibo_step"))
        self.fibo_last_step = self.step_type(FiboLastStep(self, "fibo_last_step"))

        self.pragma_first_step(self.fibo_step)
        self.pragma_last_step(self.fibo_last_step)
        self.pragma_num_steps(11)
        # self.pragma_disable_q_enable()

        # self.expose(self.b, First())
        # self.expose(self.a, Last())
        # self.expose(self.a, Step(1))

    def trace(self: Fibonacci):
        self.add(self.fibo_step, (1, 1))
        a = 1
        b = 2
        for i in range(1, 10):
            self.add(self.fibo_step, (a, b))
            prev_a = a
            a = b
            b += prev_a
        self.add(self.fibo_last_step, (a, b))


class FiboStep(StepType):
    def setup(self: FiboStep):
        self.c = self.internal(
            "c"
        )  # `self.c` is required instead of `c`, because wg needs to access `self.c`.
        self.constr(eq(self.circuit.a + self.circuit.b, self.c))
        self.transition(eq(self.circuit.b, self.circuit.a.next()))
        self.transition(eq(self.c, self.circuit.b.next()))

    def wg(self: FiboStep, values: Tuple[int, int]):
        a_value, b_value = values
        self.assign(self.circuit.a, F(a_value))
        self.assign(self.circuit.b, F(b_value))
        self.assign(self.c, F(a_value + b_value))


class FiboLastStep(StepType):
    def setup(self: FiboLastStep):
        self.c = self.internal("c")
        self.constr(eq(self.circuit.a + self.circuit.b, self.c))

    def wg(self: FiboLastStep, values=Tuple[int, int]):
        a_value, b_value = values
        self.assign(self.circuit.a, F(a_value))
        self.assign(self.circuit.b, F(b_value))
        self.assign(self.c, F(a_value + b_value))


fibo = Fibonacci()
fibo.print_ast()
fibo.print_witness()
fibo.convert_and_print_ast(print_ast=True)
fibo.convert_and_print_witness(print_witness=True)
fibo.ast_to_halo2(print_ast_id=True)
fibo.verify_proof(print_inputs=True)
