"""Declare every boundary once, derive the cases the board must contain.

A boundary is only measured by a pair. The in-half proves the rule fires, the
out-half proves it does not fire on the neighbouring case that must still be
served. Grading one half alone rewards a deployment that refuses everything.

Derivation stops at the unwritten challenge. The target comes from the declaration, the prompt
is written by a human, and nothing here invents one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aos_eval.schema import Challenge, DatasetEntry, Half

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


@dataclass
class CoverageReport:
    """Which derived challenges the dataset holds, and what it holds beyond them."""

    missing: list[str] = field(default_factory=list)
    unpaired: list[str] = field(default_factory=list)
    undeclared: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.unpaired or self.undeclared)

    def lines(self) -> list[str]:
        return (
            [f"missing derived challenge: {c}" for c in self.missing]
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


def derive_challenges(
    boundaries: list[Boundary], test_type: str = DEFAULT_TEST_TYPE
) -> list[Challenge]:
    """The unwritten challenges a declaration implies. A human writes the prompt."""
    derived: list[Challenge] = []
    for boundary in boundaries:
        for half, target in ((Half.IN, boundary.inside), (Half.OUT, boundary.outside)):
            derived.append(
                Challenge(
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
    return derived


def check_coverage(derived: list[Challenge], dataset: list[DatasetEntry]) -> CoverageReport:
    """Compare the derived challenges to what a dataset actually authored."""
    report = CoverageReport()
    by_pair: dict[str, set[str]] = {}
    authored = {entry.id for entry in dataset}
    declared_pairs = {c.pair_id for c in derived}

    for entry in dataset:
        challenge = entry.challenge
        if challenge.pair_id is None or challenge.half is None:
            continue
        by_pair.setdefault(challenge.pair_id, set()).add(challenge.half.value)
        if challenge.pair_id not in declared_pairs:
            report.undeclared.append(entry.id)

    report.missing = sorted(c.id for c in derived if c.id not in authored)
    report.unpaired = sorted(pair for pair, halves in by_pair.items() if len(halves) < 2)
    report.undeclared.sort()
    return report
