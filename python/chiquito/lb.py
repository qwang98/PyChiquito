from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional

from util import F, uuid
from expr import Expr, Const, Neg, to_expr, ToExpr
from query import StepTypeNext
from chiquito_ast import ASTStepType, Lookup
from cb import ToConstraint, to_constraint, Constraint

# from dsl import Circuit, StepType


@dataclass
class LookupTableRegistry:
    tables: Dict[int, LookupTable] = field(default_factory=dict)

    def add(self: LookupTableRegistry, table: LookupTable):
        self.tables[table.uuid] = table

    def get(self: LookupTableRegistry, uuid: int) -> LookupTable:
        return self.tables[uuid]


@dataclass
class LookupTable:
    uuid: int = 0
    dest: List[Expr] = field(default_factory=list)

    def __init__(self: LookupTable):
        self.uuid: int = uuid()

    def add(self: LookupTable, expr: ToExpr) -> LookupTable:
        self.dest.append(to_expr(expr))
        return self

    def apply(self: LookupTable, constraint: ToConstraint) -> LookupTableBuilder:
        return LookupTableBuilder(self.uuid).apply(constraint)

    def when(self: LookupTable, enable: ToConstraint) -> LookupTableBuilder:
        return LookupTableBuilder(self.uuid).when(enable)


@dataclass
class LookupTableBuilder:
    uuid: int
    src: List[Constraint] = field(default_factory=list)
    enable: Optional[Constraint] = None

    def __init__(self: LookupTableBuilder, uuid: int):
        self.uuid: int = uuid

    def apply(self: LookupTableBuilder, constraint: ToConstraint) -> LookupTableBuilder:
        self.src.append(to_constraint(constraint))
        return self

    def when(self: LookupTableBuilder, enable: ToConstraint) -> LookupTableBuilder:
        if self.enable is not None:
            raise ValueError("LookupTableBuilder: when() can only be called once.")
        self.enable = to_constraint(enable)
        return self

    def build(self: LookupTableBuilder, step_type: StepType) -> Lookup:
        table = step_type.tables.get(self.id)
        if self.src.len() != table.dest.len():
            raise ValueError(
                "LookupTableBuilder: build() has different number of source columns and destination columns."
            )

        lookup = Lookup()

        if self.enable is not None:
            lookup.enable(self.enable.annotation, self.enable.expr)

        for i in range(self.src.len()):
            lookup.add(self.src[i].annotation, self.src[i].expr, table.dest[i])

        return lookup


@dataclass
class InPlaceLookupBuilder:
    lookup: Lookup = field(default_factory=Lookup)

    def build(self: InPlaceLookupBuilder, _: StepType) -> Lookup:
        return self.lookup

    def add(
        self: InPlaceLookupBuilder, constraint: ToConstraint, expression: ToExpr
    ) -> InPlaceLookupBuilder:
        constraint = to_constraint(constraint)
        self.lookup.add(constraint.annotation, constraint.expr, to_expr(expression))
        return self

    def enable(
        self: InPlaceLookupBuilder, enable: ToConstraint
    ) -> InPlaceLookupBuilder:
        enable = to_constraint(enable)
        self.lookup.enable(enable.annotation, enable.expr)
        return self
