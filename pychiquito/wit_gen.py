from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any
import json

from query import Queriable, Fixed
from util import F, CustomEncoder

# Commented out to avoid circular reference
# from dsl import Circuit, StepType

###########
# wit_gen #
###########


@dataclass
class StepInstance:
    step_type_uuid: int = 0
    assignments: Dict[Queriable, F] = field(default_factory=dict)

    def new(step_type_uuid: int) -> StepInstance:
        return StepInstance(step_type_uuid, {})

    def assign(self: StepInstance, lhs: Queriable, rhs: F):
        self.assignments[lhs] = rhs

    def __str__(self: StepInstance):
        assignments_str = (
            "\n\t\t\t\t"
            + ",\n\t\t\t\t".join(
                f"{str(lhs)} = {rhs}" for (lhs, rhs) in self.assignments.items()
            )
            + "\n\t\t\t"
            if self.assignments
            else ""
        )
        return (
            f"StepInstance(\n"
            f"\t\t\tstep_type_uuid={self.step_type_uuid},\n"
            f"\t\t\tassignments={{{assignments_str}}},\n"
            f"\t\t)"
        )

    # For assignments, return "uuid: F" rather than "Queriable: F", because JSON doesn't accept Dict as key.
    def __json__(self: StepInstance):
        return {
            "step_type_uuid": self.step_type_uuid,
            "assignments": {
                lhs.uuid(): [lhs, rhs] for (lhs, rhs) in self.assignments.items()
            },
        }


Witness = List[StepInstance]


@dataclass
class TraceWitness:
    step_instances: Witness = field(default_factory=list)
    height: int = 0

    def __str__(self: TraceWitness):
        step_instances_str = (
            "\n\t\t"
            + ",\n\t\t".join(
                str(step_instance) for step_instance in self.step_instances
            )
            + "\n\t"
            if self.step_instances
            else ""
        )
        return (
            f"TraceWitness(\n"
            f"\tstep_instances={{{step_instances_str}}},\n"
            f"\theight={self.height},\n"
            f")"
        )

    def __json__(self: TraceWitness):
        return {
            "step_instances": [
                step_instance.__json__() for step_instance in self.step_instances
            ],
            "height": self.height,
        }

    def get_witness_json(self: TraceWitness) -> str:
        return json.dumps(self, cls=CustomEncoder, indent=4)


FixedAssigment = Dict[Queriable, List[F]]


@dataclass
class FixedGenContext:
    assignments: FixedAssigment = field(default_factory=dict)
    num_steps: int = 0

    def new(num_steps: int) -> FixedGenContext:
        return FixedGenContext({}, num_steps)

    def assign(self: FixedGenContext, offset: int, lhs: Queriable, rhs: F):
        if not FixedGenContext.is_fixed_queriable(lhs):
            raise ValueError(f"Cannot assign to non-fixed signal.")
        if lhs in self.assignments.keys():
            self.assignments[lhs][offset] = rhs
        else:
            self.assignments[lhs] = [F.zero()] * self.num_steps
            self.assignments[lhs][offset] = rhs

    def is_fixed_queriable(q: Queriable) -> bool:
        match q.enum:
            case Fixed(_, _):  # Ignored Halo2FixedQuery enum type.
                return True
            case _:
                return False
