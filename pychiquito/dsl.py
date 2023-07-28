from __future__ import annotations
from enum import Enum
from typing import Callable, Any
from dataclasses import dataclass
import rust_chiquito  # rust bindings
import json

from chiquito_ast import ASTCircuit, ASTStepType, ExposeOffset
from query import Internal, Forward, Queriable, Shared, Fixed
from wit_gen import FixedGenContext, TraceContext, StepInstance
from cb import Constraint, Typing, ToConstraint, to_constraint
from util import CustomEncoder, F


#######
# dsl #
#######


class CircuitMode(Enum):
    NoMode = 0
    SETUP = 1
    Trace = 2


class Circuit:
    def __init__(self: Circuit):
        self.ast = ASTCircuit()
        self.trace_context = TraceContext()
        self.rust_ast_id = 0
        self.mode = CircuitMode.SETUP
        self.setup()
        self.mode = CircuitMode.Trace
        self.ast.set_trace(self.trace)
        self.trace()
        # self.mode = CircuitMode.NoMode

    def forward(self: Circuit, name: str) -> Forward:
        assert self.mode == CircuitMode.SETUP
        return Forward(self.ast.add_forward(name, 0), False)

    def forward_with_phase(self: Circuit, name: str, phase: int) -> Forward:
        assert self.mode == CircuitMode.SETUP
        return Forward(self.ast.add_forward(name, phase), False)

    def shared(self: Circuit, name: str) -> Shared:
        assert self.mode == CircuitMode.SETUP
        return Shared(self.ast.add_shared(name, 0), 0)

    def shared_with_phase(self: Circuit, name: str, phase: int) -> Shared:
        assert self.mode == CircuitMode.SETUP
        return Shared(self.ast.add_shared(name, phase), 0)

    def fixed(self: Circuit, name: str) -> Fixed:
        assert self.mode == CircuitMode.SETUP
        return Fixed(self.ast.add_fixed(name), 0)

    def expose(self: Circuit, signal: Queriable, offset: ExposeOffset):
        assert self.mode == CircuitMode.SETUP
        if isinstance(signal, (Forward, Shared)):
            self.ast.expose(signal, offset)
        else:
            raise TypeError(f"Can only expose ForwardSignal or SharedSignal.")

    # import_halo2_advice and import_halo2_fixed are ignored.

    def step_type(self: Circuit, step_type: StepType) -> StepType:
        assert self.mode == CircuitMode.SETUP
        self.ast.add_step_type(step_type.step_type, step_type.step_type.name)
        return step_type

    def step_type_def(self: StepType) -> StepType:
        assert self.mode == CircuitMode.SETUP
        self.ast.add_step_type_def()

    # def trace(
    #     self: Circuit, trace_def: Callable[[TraceContext, Any], None]
    # ):  # TraceArgs are Any.
    #     self.ast.set_trace(trace_def)

    def fixed_gen(self: Circuit, fixed_gen_def: Callable[[FixedGenContext], None]):
        self.ast.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(self: Circuit, step_type: StepType) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.first_step = step_type.step_type.id
        print(f"first step id: {step_type.step_type.id}")

    def pragma_last_step(self: Circuit, step_type: StepType) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.last_step = step_type.step_type.id
        print(f"last step id: {step_type.step_type.id}")

    def pragma_num_steps(self: Circuit, num_steps: int) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.num_steps = num_steps

    def pragma_disable_q_enable(self: Circuit) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.q_enable = False

    def add(self: Circuit, step_type: StepType, args: Any):
        print(self)
        print(step_type)
        print(args)
        assert self.mode == CircuitMode.Trace
        self.trace_context.add(self, step_type, args)

    def print_ast(self: Circuit):
        print("Print ASTCircuit using custom __str__ method in python:")
        print(self.ast)

    def get_ast_json(self: Circuit, print_json=False) -> str:
        ast_json: str = json.dumps(self.ast, cls=CustomEncoder, indent=4)
        if print_json:
            print("Print ASTCircuit using __json__ method in python:")
            print(ast_json)
        return ast_json

    def print_witness(self: Circuit):
        print("Print TraceWitness using custom __str__ method in python:")
        print(self.trace_context.witness)

    def get_witness_json(self: Circuit, print_json=False) -> str:
        witness_json: str = json.dumps(
            self.trace_context.witness, cls=CustomEncoder, indent=4
        )
        if print_json:
            print("Print TraceWitness using __json__ method in python:")
            print(witness_json)
        return witness_json

    def convert_and_print_ast(self: Circuit, print_ast=False):
        ast_json: str = self.get_ast_json()
        if print_ast:
            print(
                "Call rust bindings, parse json to Chiquito ASTCircuit, and print using Debug trait:"
            )
            print(rust_chiquito.convert_and_print_ast(ast_json))

    def convert_and_print_witness(self: Circuit, print_witness=False):
        witness_json: str = self.get_witness_json()
        if print_witness:
            print(
                "Call rust bindings, parse json to Chiquito TraceWitness, and print using Debug trait:"
            )
            print(rust_chiquito.convert_and_print_trace_witness(witness_json))

    def ast_to_halo2(self: Circuit, print_ast_id=False):
        ast_json: str = self.get_ast_json()
        self.rust_ast_id: int = rust_chiquito.ast_to_halo2(ast_json)
        if print_ast_id:
            print("Parse json to Chiquito Halo2, and obtain UUID:")
            print(self.rust_ast_id)

    def verify_proof(self: Circuit, print_inputs=False):
        if self.rust_ast_id == 0:
            self.rust_ast_id = self.ast_to_halo2()
        witness_json: str = self.get_witness_json()
        if print_inputs:
            print("Rust AST UUID:")
            print(self.rust_ast_id)
            print("Print TraceWitness using __json__ method in python:")
            print(witness_json)
            print("Verify ciruit with AST uuid and witness json:")
        rust_chiquito.verify_proof(witness_json, self.rust_ast_id)


class StepTypeMode(Enum):
    NoMode = 0
    SETUP = 1
    WG = 2


class StepType:
    def __init__(self: StepType, circuit: Circuit, step_type_name: str):
        self.step_type = ASTStepType.new(step_type_name)
        self.circuit = circuit
        self.step_instance = StepInstance.new(self.step_type.id)
        self.mode = StepTypeMode.SETUP
        self.setup()
        self.mode = StepTypeMode.WG
        self.step_type.set_wg(self.wg)
        # self.mode = StepTypeMode.NoMode

    def internal(self: StepType, name: str) -> Internal:
        assert self.mode == StepTypeMode.SETUP

        return Internal(self.step_type.add_signal(name))

    # def wg(
    #     self: StepType, wg_def: Callable[[TraceContext, Any], None]
    # ):  # Args are Any.
    #     self.step_type.set_wg(wg_def)

    def constr(self: StepType, constraint: ToConstraint):
        assert self.mode == StepTypeMode.SETUP

        constraint = to_constraint(constraint)
        StepType.enforce_constraint_typing(constraint)
        self.step_type.add_constr(constraint.annotation, constraint.expr)

    def transition(self: StepType, constraint: ToConstraint):
        assert self.mode == StepTypeMode.SETUP

        constraint = to_constraint(constraint)
        StepType.enforce_constraint_typing(constraint)
        self.step_type.add_transition(constraint.annotation, constraint.expr)

    def enforce_constraint_typing(constraint: Constraint):
        if constraint.typing != Typing.AntiBooly:
            raise ValueError(
                f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})"
            )

    def assign(self: StepType, lhs: Queriable, rhs: F):
        assert self.mode == StepTypeMode.WG

        self.step_instance.assign(lhs, rhs)

    # TODO: Implement add_lookup after lookup abstraction PR is merged.
