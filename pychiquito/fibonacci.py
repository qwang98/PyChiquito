from __future__ import annotations
from typing import Tuple

from dsl import Circuit, StepType
from cb import eq
from query import Queriable
from util import F


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

    def trace(self: Fibonacci, args: Any):
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
        self.c = self.internal("c")
        self.constr(eq(self.circuit.a + self.circuit.b, self.c))
        self.transition(eq(self.circuit.b, self.circuit.a.next()))
        self.transition(eq(self.c, self.circuit.b.next()))

    def wg(self: FiboStep, args: Tuple[int, int]):
        a_value, b_value = args
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
fibo_witness = fibo.gen_witness(None)
fibo.ast_to_halo2()
fibo.verify_proof(fibo_witness)
