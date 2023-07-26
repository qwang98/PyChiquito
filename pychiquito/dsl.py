from __future__ import annotations
from enum import Enum
from typing import Callable, Any
from dataclasses import dataclass

from chiquito_ast import ASTCircuit, ASTStepType, ExposeOffset, ForwardSignal, SharedSignal
from query import Internal, Forward, Queriable, Shared, Fixed
from wit_gen import FixedGenContext, TraceContext
from cb import Constraint, Typing, ToConstraint, to_constraint


#######
# dsl #
#######


class Circuit:
    def __init__(self):
        self.circuit = ASTCircuit()

    def forward(self: Circuit, name: str) -> Forward:
        return Forward(self.circuit.add_forward(name, 0), False)

    def forward_with_phase(self: Circuit, name: str, phase: int) -> Forward:
        return Forward(self.circuit.add_forward(name, phase), False)

    def shared(self: Circuit, name: str) -> Shared:
        return Shared(self.circuit.add_shared(name, 0), 0)

    def shared_with_phase(self: Circuit, name: str, phase: int) -> Shared:
        return Shared(self.circuit.add_shared(name, phase), 0)

    def fixed(self: Circuit, name: str) -> Fixed:
        return Fixed(self.circuit.add_fixed(name), 0)

    def expose(self: Circuit, signal: Queriable, offset: ExposeOffset):
        if isinstance(signal, (Forward, Shared)):
            self.circuit.expose(signal, offset)
        else:
            raise TypeError(f"Can only expose ForwardSignal or SharedSignal.")

    # import_halo2_advice and import_halo2_fixed are ignored.

    def step_type(
        self: Circuit, step_type_context: StepType
    ) -> StepType:
        self.circuit.add_step_type(
            step_type_context.step_type, step_type_context.step_type.name
        )
        return step_type_context

    def step_type_def(self: StepType) -> StepType:
        self.circuit.add_step_type_def()

    def trace(
        self: Circuit, trace_def: Callable[[TraceContext, Any], None]
    ):  # TraceArgs are Any.
        self.circuit.set_trace(trace_def)

    def fixed_gen(
        self: Circuit, fixed_gen_def: Callable[[FixedGenContext], None]
    ):
        self.circuit.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(
        self: Circuit, step_type_context: StepType
    ) -> None:
        self.circuit.first_step = step_type_context.step_type.id
        print(f"first step id: {step_type_context.step_type.id}")

    def pragma_last_step(
        self: Circuit, step_type_context: StepType
    ) -> None:
        self.circuit.last_step = step_type_context.step_type.id
        print(f"last step id: {step_type_context.step_type.id}")

    def pragma_num_steps(self: Circuit, num_steps: int) -> None:
        self.circuit.num_steps = num_steps

    def pragma_disable_q_enable(self: Circuit) -> None:
        self.circuit.q_enable = False


class StepTypeMode(Enum):
    NoMode = 0
    SETUP = 1
    WG = 2


class StepType:

    def __init__(self: StepType, circuit, step_type_name: str, ):
        self.step_type = ASTStepType.new(step_type_name)
        self.circuit = circuit
        self.mode = StepTypeMode.SETUP
        self.setup()
        self.mode = StepTypeMode.NoMode

    def internal(self: StepType, name: str) -> Internal:
        assert (self.mode == StepTypeMode.SETUP)

        return Internal(self.step_type.add_signal(name))

    def wg(
        self: StepType, wg_def: Callable[[TraceContext, Any], None]
    ):  # Args are Any.
        self.step_type.set_wg(wg_def)

    def constr(self: StepType, constraint: ToConstraint):
        assert (self.mode == StepTypeMode.SETUP)

        constraint = to_constraint(constraint)
        StepType.enforce_constraint_typing(constraint)
        self.step_type.add_constr(constraint.annotation, constraint.expr)

    def transition(self: StepType, constraint: ToConstraint):
        assert (self.mode == StepTypeMode.SETUP)

        constraint = to_constraint(constraint)
        StepType.enforce_constraint_typing(constraint)
        self.step_type.add_transition(constraint.annotation, constraint.expr)

    def enforce_constraint_typing(constraint: Constraint):
        if constraint.typing != Typing.AntiBooly:
            raise ValueError(
                f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})"
            )


def circuit(
    name: str, circuit_context_def: Callable[[Circuit], None]
) -> ASTCircuit:
    ctx = Circuit()
    circuit_context_def(ctx)
    return ctx.circuit
