"""Join authored samples to what a runner returned, and record every drop.

There is no mechanical scorer here. On agent-compose's first graded board a
regex tier disagreed with the human on every case where either deviated from a
pass, so it was removed rather than tuned. Selection is structural only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from aos_eval.schema import AGENT_COMPOSE, DatasetEntry, Profile, Response, Sample


@dataclass(frozen=True)
class Dropped:
    sample_id: str
    reason: str


@dataclass
class DatasetReport:
    """Silent truncation reads as full coverage, so every drop is recorded."""

    kept: list[DatasetEntry] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return f"{len(self.kept)} kept, {len(self.dropped)} dropped"


def build(samples: list[Sample], responses: list[Response], epoch: int = 1) -> DatasetReport:
    """One entry per sample, carrying the named epoch's text for annotation.

    The other epochs stay in the runner's own log as evidence a reader can open.
    """
    by_sample: dict[str, list[Response]] = defaultdict(list)
    for response in responses:
        by_sample[response.sample_id].append(response)

    report = DatasetReport()
    for sample in samples:
        runs = sorted(by_sample[sample.id], key=lambda run: run.epoch)
        if not runs:
            report.dropped.append(Dropped(sample.id, "no subject runs"))
            continue
        chosen = next((run for run in runs if run.epoch == epoch), runs[0])
        report.kept.append(DatasetEntry(sample=sample, output=chosen.text))
    return report


def validate(samples: list[Sample], profile: Profile = AGENT_COMPOSE) -> list[str]:
    """Profile-level shape for a whole sample list, in one pass."""
    problems: list[str] = []
    for sample in samples:
        problems.extend(sample.check_against(profile))
    return problems
