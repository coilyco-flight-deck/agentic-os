"""Declare every boundary once, derive the cases the board must contain.

A boundary is only measured by a pair. The in-half proves the rule fires, the
out-half proves it does not fire on the neighbouring case that must still be
served. Grading one half alone rewards a deployment that refuses everything.

Derivation stops at the slot. The target comes from the declaration, the prompt
is written by a human, and nothing here invents one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aos_eval.schema import DatasetEntry, Half

BOUNDARIES_SCHEMA = "aos-eval.boundaries.v1"
DEFAULT_TEST_TYPE = "boundary"


@dataclass(frozen=True)
class Boundary:
    """One rule, plus the two behaviours that bracket it."""

    id: str
    rule: str
    inside: str
    outside: str
    role: str = ""
    # Where the rule actually lives. A boundary restated here rather than
    # derived from its source drifts the moment the source changes.
    origin: str = ""
    derived: bool = False
    seed: str = ""


@dataclass(frozen=True)
class Slot:
    """One case the dataset must contain, before anyone authors it."""

    id: str
    role: str
    test_type: str
    boundary: str
    half: Half
    pair_id: str
    target: str
    seed: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "role": self.role,
            "test_type": self.test_type,
            "boundary": self.boundary,
            "half": self.half.value,
            "pair_id": self.pair_id,
            "target": self.target,
        }
        if self.seed:
            payload["seed"] = self.seed
        return payload


@dataclass
class CoverageReport:
    """Which derived slots the dataset holds, and what it holds beyond them."""

    missing: list[str] = field(default_factory=list)
    unpaired: list[str] = field(default_factory=list)
    undeclared: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.unpaired or self.undeclared)

    def lines(self) -> list[str]:
        return (
            [f"missing derived case: {slot}" for slot in self.missing]
            + [f"pair has one half only: {pair}" for pair in self.unpaired]
            + [f"boundary case not derived from any declaration: {case}" for case in self.undeclared]
        )


class DeclarationError(Exception):
    """Raised on a declaration that cannot be read as boundaries."""


def load_declaration(raw: dict[str, Any]) -> list[Boundary]:
    schema = str(raw.get("schema", ""))
    if schema and schema != BOUNDARIES_SCHEMA and not schema.endswith(".boundaries.v1"):
        raise DeclarationError(f"{schema} is not a boundaries declaration")

    default_role = str(raw.get("role", ""))
    boundaries: list[Boundary] = []
    for entry in raw.get("boundaries", []):
        missing = [key for key in ("id", "rule", "inside", "outside") if not entry.get(key)]
        if missing:
            raise DeclarationError(f"{entry.get('id', '<no id>')}: missing {', '.join(missing)}")
        boundaries.append(
            Boundary(
                id=str(entry["id"]),
                rule=str(entry["rule"]),
                inside=str(entry["inside"]),
                outside=str(entry["outside"]),
                role=str(entry.get("role", default_role)),
                origin=str(entry.get("origin", "")),
                derived=bool(entry.get("derived", False)),
                seed=str(entry.get("seed", "")),
            )
        )
    if not boundaries:
        raise DeclarationError("declaration holds no boundaries")
    return boundaries


def derive_slots(boundaries: list[Boundary], test_type: str = DEFAULT_TEST_TYPE) -> list[Slot]:
    slots: list[Slot] = []
    for boundary in boundaries:
        for half, target in ((Half.IN, boundary.inside), (Half.OUT, boundary.outside)):
            slots.append(
                Slot(
                    id=f"{boundary.id}-{half.value}",
                    role=boundary.role,
                    test_type=test_type,
                    boundary=boundary.id,
                    half=half,
                    pair_id=boundary.id,
                    target=target,
                    seed=boundary.seed,
                )
            )
    return slots


def check_coverage(slots: list[Slot], dataset: list[DatasetEntry]) -> CoverageReport:
    """Compare a derived slot list to what a dataset actually authored."""
    report = CoverageReport()
    by_pair: dict[str, set[str]] = {}
    authored = {entry.id for entry in dataset}
    declared_pairs = {slot.pair_id for slot in slots}

    for entry in dataset:
        sample = entry.sample
        if sample.pair_id is None or sample.half is None:
            continue
        by_pair.setdefault(sample.pair_id, set()).add(sample.half.value)
        if sample.pair_id not in declared_pairs:
            report.undeclared.append(entry.id)

    report.missing = sorted(slot.id for slot in slots if slot.id not in authored)
    report.unpaired = sorted(pair for pair, halves in by_pair.items() if len(halves) < 2)
    report.undeclared.sort()
    return report
