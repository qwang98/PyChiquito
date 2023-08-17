from __future__ import annotations
from enum import Enum
from typing import Callable, Any
import json

from chiquito.chiquito_ast import ASTCircuit, ASTStepType, ExposeOffset
from chiquito.query import Internal, Forward, Queriable, Shared, Fixed
from chiquito.wit_gen import FixedGenContext, StepInstance, TraceWitness
from chiquito.cb import Constraint, Typing, ToConstraint, to_constraint
from chiquito.util import CustomEncoder, F
from chiquito.rust_chiquito import ast_to_halo2, halo2_mock_prover


class CircuitMode(Enum):
    NoMode = 0
    SETUP = 1
    Trace = 2


class Circuit:
    def __init__(self: Circuit):
        self.ast = ASTCircuit()
        self.witness = TraceWitness()
        self.rust_ast_id = 0
        self.num_step_instances = 0
        self.mode = CircuitMode.SETUP
        self.setup()

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

    def step_type(self: Circuit, step_type: StepType) -> StepType:
        assert self.mode == CircuitMode.SETUP
        self.ast.add_step_type(step_type.step_type, step_type.step_type.name)
        return step_type

    def step_type_def(self: StepType) -> StepType:
        assert self.mode == CircuitMode.SETUP
        self.ast.add_step_type_def()

    def fixed_gen(self: Circuit, fixed_gen_def: Callable[[FixedGenContext], None]):
        self.ast.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(self: Circuit, step_type: StepType) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.first_step = step_type.step_type.id

    def pragma_last_step(self: Circuit, step_type: StepType) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.last_step = step_type.step_type.id

    def pragma_num_steps(self: Circuit, num_steps: int) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.num_steps = num_steps

    def pragma_disable_q_enable(self: Circuit) -> None:
        assert self.mode == CircuitMode.SETUP
        self.ast.q_enable = False

    def add(self: Circuit, step_type: StepType, args: Any):
        assert self.mode == CircuitMode.Trace
        if self.num_step_instances >= self.ast.num_steps:
            raise ValueError(f"Number of step instances exceeds {self.ast.num_steps}")
        self.num_step_instances += 1
        step_instance: StepInstance = step_type.gen_step_instance(args)
        self.witness.step_instances.append(step_instance)

    def needs_padding(self: Circuit) -> bool:
        return self.num_step_instances < self.ast.num_steps

    def padding(self: Circuit, step_type: StepType, args: Any):
        while self.needs_padding():
            self.add(step_type, args)

    def gen_witness(self: Circuit, args: Any) -> TraceWitness:
        self.num_step_instances = 0
        self.mode = CircuitMode.Trace
        self.witness = TraceWitness()
        self.trace(args)
        self.mode = CircuitMode.NoMode
        witness = self.witness
        del self.witness
        return witness

    def get_ast_json(self: Circuit) -> str:
        return json.dumps(self.ast, cls=CustomEncoder, indent=4)

    def halo2_mock_prover(self: Circuit, witness: TraceWitness):
        if self.rust_ast_id == 0:
            ast_json: str = self.get_ast_json()
            self.rust_ast_id: int = ast_to_halo2(ast_json)
        witness_json: str = witness.get_witness_json()
        halo2_mock_prover(witness_json, self.rust_ast_id)

    def __str__(self: Circuit) -> str:
        return self.ast.__str__()


class StepTypeMode(Enum):
    NoMode = 0
    SETUP = 1
    WG = 2


class StepType:
    def __init__(self: StepType, circuit: Circuit, step_type_name: str):
        self.step_type = ASTStepType.new(step_type_name)
        self.circuit = circuit
        self.mode = StepTypeMode.SETUP
        self.setup()

    def gen_step_instance(self: StepType, args: Any) -> StepInstance:
        self.mode = StepTypeMode.WG
        self.step_instance = StepInstance.new(self.step_type.id)
        self.wg(args)
        self.mode = StepTypeMode.NoMode
        step_instance = self.step_instance
        del self.step_instance
        return step_instance

    def internal(self: StepType, name: str) -> Internal:
        assert self.mode == StepTypeMode.SETUP

        return Internal(self.step_type.add_signal(name))

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
