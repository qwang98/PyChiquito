from __future__ import annotations
from typing import Callable, Any
from dataclasses import dataclass

from chiquito_ast import Circuit, StepType, ExposeOffset, ForwardSignal, SharedSignal
from query import Internal, Forward, Queriable, Shared, Fixed
from wit_gen import FixedGenContext, TraceContext
from cb import Constraint, Typing, ToConstraint, to_constraint


#######
# dsl #
#######


class CircuitContext:
    def __init__(self):
        self.circuit = Circuit()

    def forward(self: CircuitContext, name: str) -> Forward:
        return Forward(self.circuit.add_forward(name, 0), False)

    def forward_with_phase(self: CircuitContext, name: str, phase: int) -> Forward:
        return Forward(self.circuit.add_forward(name, phase), False)

    def shared(self: CircuitContext, name: str) -> Shared:
        return Shared(self.circuit.add_shared(name, 0), 0)

    def shared_with_phase(self: CircuitContext, name: str, phase: int) -> Shared:
        return Shared(self.circuit.add_shared(name, phase), 0)

    def fixed(self: CircuitContext, name: str) -> Fixed:
        return Fixed(self.circuit.add_fixed(name), 0)

    def expose(self: CircuitContext, signal: Queriable, offset: ExposeOffset):
        if isinstance(signal, (Forward, Shared)):
            self.circuit.expose(signal, offset)
        else:
            raise TypeError(f"Can only expose ForwardSignal or SharedSignal.")

    # import_halo2_advice and import_halo2_fixed are ignored.

    def step_type(
        self: CircuitContext, step_type_context: StepTypeContext
    ) -> StepTypeContext:
        self.circuit.add_step_type(
            step_type_context.step_type, step_type_context.step_type.name
        )
        return step_type_context

    def step_type_def(self: StepTypeContext) -> StepTypeContext:
        self.circuit.add_step_type_def()

    def trace(
        self: CircuitContext, trace_def: Callable[[TraceContext, Any], None]
    ):  # TraceArgs are Any.
        self.circuit.set_trace(trace_def)

    def fixed_gen(
        self: CircuitContext, fixed_gen_def: Callable[[FixedGenContext], None]
    ):
        self.circuit.set_fixed_gen(fixed_gen_def)

    def pragma_first_step(
        self: CircuitContext, step_type_context: StepTypeContext
    ) -> None:
        self.circuit.first_step = step_type_context.step_type.id

    def pragma_last_step(self: CircuitContext, step_type_context: StepTypeContext) -> None:
        self.circuit.last_step = step_type_context.step_type.id

    def pragma_num_steps(self: CircuitContext, num_steps: int) -> None:
        self.circuit.num_steps = num_steps

    def pragma_disable_q_enable(self: CircuitContext) -> None:
        self.circuit.q_enable = False


class StepTypeContext:
    def __init__(self: StepTypeContext, step_type_name: str):
        self.step_type = StepType.new(step_type_name)

    def internal(self: StepTypeContext, name: str) -> Internal:
        return Internal(self.step_type.add_signal(name))

    def setup(
        self: StepTypeContext, setup_def: Callable[[StepTypeSetupContext], None]
    ) -> None:
        ctx = StepTypeSetupContext(self.step_type)
        setup_def(ctx)
        print("setup called")

    def wg(
        self: StepTypeContext, wg_def: Callable[[TraceContext, Any], None]
    ):  # Args are Any.
        self.step_type.set_wg(wg_def)


@dataclass
class StepTypeSetupContext:
    step_type: StepType

    def constr(self: StepTypeSetupContext, constraint: ToConstraint):
        constraint = to_constraint(constraint)
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_constr(constraint.annotation, constraint.expr)

    def transition(self: StepTypeSetupContext, constraint: ToConstraint):
        constraint = to_constraint(constraint)
        StepTypeSetupContext.enforce_constraint_typing(constraint)
        self.step_type.add_transition(constraint.annotation, constraint.expr)

    def enforce_constraint_typing(constraint: Constraint):
        if constraint.typing != Typing.AntiBooly:
            raise ValueError(
                f"Expected AntiBooly constraint, got {constraint.typing} (constraint: {constraint.annotation})"
            )

    # TODO: Implement add_lookup after lookup abstraction PR is merged.


def circuit(
    name: str, circuit_context_def: Callable[[CircuitContext], None]
) -> Circuit:
    ctx = CircuitContext()
    circuit_context_def(ctx)
    return ctx.circuit
