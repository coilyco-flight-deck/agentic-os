"""Human annotation loop. One sample per screen, one keystroke per decision.

Annotations are appended after every decision, so an interrupted session keeps
everything already annotated.
"""

from __future__ import annotations

import sys
import termios
import time
import tty
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aos_eval.io import save_annotations
from aos_eval.schema import (
    AGENT_COMPOSE,
    DEDUCTIONS,
    LABEL_SETS,
    Annotation,
    DatasetEntry,
    Fit,
    Profile,
    Verdict,
    annotation_order,
    pair_results,
)

LABEL_HELP = {
    Verdict.PASS: "pass",
    Verdict.FAIL: "fail",
    Fit.FIT: "fit",
    Fit.UNDECIDED: "undecided",
    Fit.NO_FIT: "does not fit",
}

TYPE_STYLES = ("bright_cyan", "bright_magenta", "bright_yellow", "bright_green")


def read_key() -> str:
    """Single keypress without a newline, so annotation stays one stroke."""
    if not sys.stdin.isatty():
        return sys.stdin.read(1) or "q"
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def style_for(profile: Profile, test_type: str) -> str:
    return TYPE_STYLES[profile.rank(test_type) % len(TYPE_STYLES)]


def role_header(console: Console, roster: dict[str, Any], role: str) -> None:
    """Printed once per group, so the charter is loaded rather than implied."""
    spec = roster.get("roles", {}).get(role)
    if not spec:
        return
    lines = [f"[bold]{spec.get('display_name', role)}[/bold]  {spec.get('purpose', '')}"]
    owned = [
        name
        for name, boundary in roster.get("boundaries", {}).items()
        if boundary.get("owner") == role
    ]
    if owned:
        lines.append("owns: " + ", ".join(owned))
    if spec.get("boundaries"):
        lines.append("defers: " + ", ".join(spec["boundaries"]))
    if spec.get("personalities"):
        lines.append("personalities: " + ", ".join(spec["personalities"]))
    for adjacent in spec.get("adjacents", []):
        lines.append(f"adjacent {adjacent['role']}: {adjacent['reason']}")
    console.print(Panel("\n".join(lines), border_style="bright_white", title="role"))


def render(
    console: Console,
    entry: DatasetEntry,
    position: int,
    total: int,
    started: float,
    profile: Profile,
    roster: dict[str, Any] | None = None,
) -> None:
    sample = entry.sample
    style = style_for(profile, sample.test_type)
    console.clear()
    if roster:
        role_header(console, roster, sample.role)

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold")
    header.add_column()
    header.add_row("sample", f"[bold]{sample.id}[/bold]")
    header.add_row("role", sample.role)
    header.add_row("test type", f"[{style}]{sample.test_type}[/]")
    if sample.boundary:
        header.add_row("boundary", f"{sample.boundary} ({sample.half.value if sample.half else ''})")
    if sample.against:
        header.add_row("against", sample.against)
    if sample.trait:
        header.add_row("trait", sample.trait)
    header.add_row("progress", progress(position, total, started))
    console.print(header)
    console.print()

    console.print(Panel(sample.prompt, title="prompt", border_style="dim"))
    words = len(entry.output.split())
    console.print(
        Panel(
            entry.output,
            title=f"output ({words} words, cap {sample.word_cap(profile)})",
            border_style=style,
        )
    )
    console.print(Panel(sample.target, title="target", border_style="green"))

    keys = LABEL_SETS[sample.label_set(profile)]
    hints = "    ".join(f"[bold]{key}[/bold] {LABEL_HELP[label]}" for key, label in keys.items())
    console.print(f"{hints}    [bold]s[/bold] skip    [bold]q[/bold] quit")


def ask(console: Console, label: str, hint: str) -> str:
    """Styled prompt printed first, then a bare readline.

    console.input hands readline a prompt carrying ANSI colour codes, readline
    miscounts the cursor column, and an answer long enough to wrap overwrites
    itself. An empty prompt leaves readline nothing to miscount.
    """
    console.print(f"[bold]{label}[/bold] ({hint})")
    return input("> ").strip()


def collect_evidence(console: Console, output: str) -> tuple[str, str]:
    """RULERS anchors a deduction to a verbatim span, verified against the output."""
    critique = ask(console, "critique", "what it did wrong")
    while True:
        evidence = ask(console, "evidence", "verbatim quote, blank to skip")
        if not evidence or evidence.lower() in output.lower():
            return critique, evidence
        console.print("[red]not found verbatim in the output[/red]")


def annotate_session(
    dataset: list[DatasetEntry],
    annotations: dict[str, Annotation],
    out: Path,
    profile: Profile = AGENT_COMPOSE,
    roster: dict[str, Any] | None = None,
) -> bool:
    """Returns False when the annotator quit before finishing."""
    console = Console()
    group_order = list(roster.get("role_order", [])) if roster else None
    pending = [
        entry
        for entry in annotation_order(dataset, profile, group_order)
        if entry.id not in annotations
    ]
    started = time.monotonic()

    for index, entry in enumerate(pending, start=1):
        keys = LABEL_SETS[entry.sample.label_set(profile)]
        while True:
            render(console, entry, index, len(pending), started, profile, roster)
            key = read_key().lower()
            if key == "q":
                return False
            if key == "s":
                break
            if key in keys:
                label = keys[key]
                critique, evidence = "", ""
                if label in DEDUCTIONS:
                    console.print()
                    critique, evidence = collect_evidence(console, entry.output)
                annotations[entry.id] = Annotation(
                    id=entry.id, label=label, critique=critique, evidence=evidence
                )
                save_annotations(out, annotations)
                break
    return True


def summarize(
    console: Console, dataset: list[DatasetEntry], annotations: dict[str, Annotation]
) -> None:
    pairs = pair_results(dataset, annotations)
    if pairs:
        table = Table(title="boundary pairs, the scoring unit")
        for column in ("pair", "role", "boundary", "result"):
            table.add_column(column)
        for pair in pairs:
            if not pair.complete:
                result = "[yellow]incomplete[/yellow]"
            elif pair.passed:
                result = "[green]pass[/green]"
            else:
                result = "[red]fail[/red]"
            table.add_row(pair.pair_id, pair.role, pair.boundary, result)
        console.print(table)

    # Only this dataset's ids. An annotations file outlives a case rename, so
    # counting the whole file reports more grades than there are cases.
    ids = {entry.id for entry in dataset}
    current = {key: value for key, value in annotations.items() if key in ids}
    counts: dict[str, int] = {}
    for annotation in current.values():
        counts[annotation.label.value] = counts.get(annotation.label.value, 0) + 1
    console.print(
        f"\nannotated {len(current)} of {len(dataset)}: "
        + ", ".join(f"{value} {key}" for key, value in sorted(counts.items()))
    )
    if stale := len(annotations) - len(current):
        console.print(f"[yellow]{stale} annotations are for ids not in this dataset[/yellow]")


def progress(position: int, total: int, started: float) -> str:
    elapsed = time.monotonic() - started
    if position <= 1:
        return f"{position}/{total}"
    rate = elapsed / (position - 1)
    remaining = rate * (total - position + 1)
    return f"{position}/{total}  {elapsed / 60:.0f}m elapsed  ~{remaining / 60:.0f}m left"
