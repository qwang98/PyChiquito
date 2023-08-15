from __future__ import annotations
from typing import Tuple
from chiquito_ast import Last

from dsl import Circuit, StepType
from cb import eq
from query import Queriable
from util import F
import rust_chiquito


# class Fibonacci(Circuit):
#     def setup(self: Fibonacci):
#         self.a: Queriable = self.forward("a")
#         self.b: Queriable = self.forward("b")

#         self.fibo_step = self.step_type(FiboStep(self, "fibo_step"))
#         self.fibo_last_step = self.step_type(FiboLastStep(self, "fibo_last_step"))

#         self.pragma_first_step(self.fibo_step)
#         self.pragma_last_step(self.fibo_last_step)
#         self.pragma_num_steps(11)
#         # self.pragma_disable_q_enable()

#         # self.expose(self.b, First())
#         # self.expose(self.a, Last())
#         # self.expose(self.a, Step(1))

#     def trace(self: Fibonacci, args: Any):
#         self.add(self.fibo_step, (1, 1))
#         a = 1
#         b = 2
#         for i in range(1, 10):
#             self.add(self.fibo_step, (a, b))
#             prev_a = a
#             a = b
#             b += prev_a
#         self.add(self.fibo_last_step, (a, b))


# class FiboStep(StepType):
#     def setup(self: FiboStep):
#         self.c = self.internal("c")
#         self.constr(eq(self.circuit.a + self.circuit.b, self.c))
#         self.transition(eq(self.circuit.b, self.circuit.a.next()))
#         self.transition(eq(self.c, self.circuit.b.next()))

#     def wg(self: FiboStep, args: Tuple[int, int]):
#         a_value, b_value = args
#         self.assign(self.circuit.a, F(a_value))
#         self.assign(self.circuit.b, F(b_value))
#         self.assign(self.c, F(a_value + b_value))


# class FiboLastStep(StepType):
#     def setup(self: FiboLastStep):
#         self.c = self.internal("c")
#         self.constr(eq(self.circuit.a + self.circuit.b, self.c))

#     def wg(self: FiboLastStep, values=Tuple[int, int]):
#         a_value, b_value = values
#         self.assign(self.circuit.a, F(a_value))
#         self.assign(self.circuit.b, F(b_value))
#         self.assign(self.c, F(a_value + b_value))


# fibo = Fibonacci()
# fibo_witness = fibo.gen_witness(None)
# fibo.halo2_mock_prover(fibo_witness)

class FiboFirstStep(StepType):
    def setup(self):
        self.c = self.internal("c")
        self.constr(eq(self.circuit.a, 1))
        self.constr(eq(self.circuit.b, 1))
        self.constr(eq(self.circuit.a + self.circuit.b, self.c))
        self.transition(eq(self.circuit.b, self.circuit.a.next()))
        self.transition(eq(self.c, self.circuit.b.next()))

    def wg(self, args):
        a_value, b_value = args
        self.assign(self.circuit.a, F(a_value))
        self.assign(self.circuit.b, F(b_value))
        self.assign(self.c, F(a_value + b_value))

class FiboStep(StepType):
    def setup(self):
        self.c = self.internal("c")
        self.constr(eq(self.circuit.a + self.circuit.b, self.c))
        self.transition(eq(self.circuit.b, self.circuit.a.next()))
        self.transition(eq(self.c, self.circuit.b.next()))

    def wg(self, args):
        a_value, b_value = args
        self.assign(self.circuit.a, F(a_value))
        self.assign(self.circuit.b, F(b_value))
        self.assign(self.c, F(a_value + b_value))

class Padding(StepType):
    def setup(self):
        self.transition(eq(self.circuit.a, self.circuit.a.next()))

    def wg(self, a_value):
        self.assign(self.circuit.a, F(a_value))


class Fibonacci(Circuit):
    def setup(self):
        self.a = self.forward("a")
        self.b = self.forward("b")
        
        self.fibo_first_step = self.step_type(FiboFirstStep(self, "fibo_first_step"))
        self.fibo_step = self.step_type(FiboStep(self, "fibo_step"))
        self.padding = self.step_type(Padding(self, "padding"))

        self.pragma_num_steps(100)
        self.pragma_first_step(self.fibo_first_step)
        self.pragma_last_step(self.padding)

        self.expose(self.a, Last())
        
    def trace(self, n):
        self.add(self.fibo_first_step, (1, 1))
        a = 1
        b = 2
        for i in range(1, n):
            self.add(self.fibo_step, (a, b))
            prev_a = a
            a = b
            b += prev_a
        while(self.needs_padding()):
            self.add(self.padding, prev_a)

fibo = Fibonacci()
# print(fibo.get_ast_json())

# success
fibo_witness = fibo.gen_witness(30)
# print(fibo_witness)
fibo.halo2_mock_prover(fibo_witness)

# fails
# evil_witness = fibo_witness.evil_witness_test(step_instance_indices=[0, 0, 1, 1, 2, 2, 3, 3, 3], assignment_indices=[0, 1, 0, 2, 1, 2, 0, 1, 2], rhs=[F(0), F(2), F(2), F(4), F(4), F(6), F(4), F(6), F(10)])
# fibo.halo2_mock_prover(evil_witness)
