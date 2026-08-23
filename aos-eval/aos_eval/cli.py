"""The `aos-eval` command surface.

Documentation follows the five-tier model in the tooling-agent-workflows skill:
the skill carries description and body, `intro` is pushed on every real run,
`aos-eval help` is the pulled long form, and each command ends with one
next-action outro. Intro stays short because it is charged to every run.
"""

from __future__ import annotations

import json
import sys
from importlib import metadata
from pathlib import Path

import click

from aos_eval import annotate as annotate_mod
from aos_eval import boundaries as boundaries_mod
from aos_eval import dataset as dataset_mod
from aos_eval import taxonomy as taxonomy_mod
from aos_eval.export import ExportRefusedError, export_run_dir
from aos_eval.io import (
    dump_yaml,
    load_annotations,
    load_dataset,
    load_profile,
    read_yaml,
)
from aos_eval.schema import pair_results

INTRO = """aos-eval: the grading half. Committed YAML in, human decisions and one-way
display payloads out. No runner and no model client live here.
Run `aos-eval help` for the full reference."""

HELP = """aos-eval - shared eval grading for agent-compose and sirens-echo

WHAT IT IS
  The schema, pairing rule, human grading loop, failure taxonomy, and display
  export that two eval runners were each implementing separately. The runners
  stay in their own repos: agent-compose calls a composed prompt through Agent
  Proxy, sirens-echo drives a live harness against a real tool roster. Both
  emit this shape and both grade through this command.

WHAT IT REFUSES TO DO
  Certify. `boundaries check` reports missing cases rather than a coverage
  percentage, `export` stops instead of scrubbing, and nothing here scores a
  challenge. A number this command prints can come back negative.

THE PAIRING RULE
  A boundary is scored as a pair, never as a half. The in-half proves the rule
  fires. The out-half proves it does not fire on the neighbouring case that
  must still be served. A pair passes only when both halves pass, so a
  deployment that refuses everything scores zero rather than fifty percent.

PROFILES
  Test types, their label sets, word caps, and required fields are per
  deployment, declared in a profile YAML and passed with --profile. Without one
  the built-in agent-compose profile applies: boundary and role-fit take the
  binary pass/fail label set at a 50-word cap, personality takes the
  fit/undecided/does-not-fit set at 100.

COMMANDS
  annotate    Grade a dataset by hand. One challenge per screen, one keystroke per
              decision, saved after every decision so an interrupted session
              keeps its work. A deduction requires a critique and accepts a
              verbatim evidence span, checked against the output.
  boundaries  derive turns a declaration into the unwritten challenges the board
              must contain. check compares those to what a dataset authored,
              and names every missing case, half-authored pair, and boundary
              case no declaration derived.
  pairs       Print pair results for a graded dataset.
  taxonomy    Axial coding. Groups deductions by structural axis and shared
              critique terms into a ranked failure taxonomy.
  validate    Check a dataset against a profile's required fields.
  export      Project a committed run into a display payload. One way, never
              back. Refuses rather than scrubs when a record looks like it
              carries a secret, because the display target is public. Critique
              and evidence are written for the grader and stay out unless
              --include-private asks for them.

FILE SHAPES
  dataset.yaml      {dataset: [{id, role, test_type, prompt, target, output, ...}]}
  annotations.yaml  {annotations: [{id, label, critique, evidence}]}
  boundaries.yaml   {schema, boundaries: [{id, rule, inside, outside, origin, seed}]}
  profile.yaml      {name, test_types: [{name, label_set, word_cap, requires}], ...}

EXIT CODES
  0 success. 1 a refusal or a failed check, with the reasons on stderr."""


def version() -> str:
    try:
        return metadata.version("aos-eval")
    except metadata.PackageNotFoundError:
        return "0.0.0+source"


def intro(context: click.Context) -> None:
    """Pushed on a real run, never on help or version."""
    if not context.obj.get("quiet"):
        click.echo(INTRO, err=True)


def outro(message: str) -> None:
    click.echo(f"next: {message}", err=True)


def write_out(text: str, out: Path | None) -> None:
    if out:
        out.write_text(text if text.endswith("\n") else text + "\n")
        click.echo(f"wrote {out}")
    else:
        click.echo(text)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--quiet", is_flag=True, help="Suppress the pushed intro line.")
@click.version_option(version=version(), prog_name="aos-eval")
@click.pass_context
def main(context: click.Context, quiet: bool) -> None:
    """Shared eval grading: schema, pairing, annotation, taxonomy, export."""
    context.ensure_object(dict)
    context.obj["quiet"] = quiet


@main.command(name="help")
def help_command() -> None:
    """The exhaustive reference, safe to read and free of side effects."""
    click.echo(HELP)


@main.command()
@click.option("--dataset", "dataset_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--out", type=click.Path(path_type=Path), required=True, help="annotations.yaml")
@click.option("--profile", "profile_path", type=click.Path(exists=True, path_type=Path))
@click.option("--roster", type=click.Path(exists=True, path_type=Path), help="person.json")
@click.option("--role", "roles", multiple=True, help="grade only these groups")
@click.option("--summary", is_flag=True, help="print results and exit without grading")
@click.pass_context
def annotate(
    context: click.Context,
    dataset_path: Path,
    out: Path,
    profile_path: Path | None,
    roster: Path | None,
    roles: tuple[str, ...],
    summary: bool,
) -> None:
    """Grade a dataset by hand, one keystroke per decision."""
    intro(context)
    profile = load_profile(profile_path)
    entries = load_dataset(dataset_path)
    if roles:
        entries = [entry for entry in entries if entry.challenge.role in set(roles)]
    annotations = load_annotations(out)
    roster_data = json.loads(roster.read_text()) if roster else None
    console = annotate_mod.Console()

    if not summary and not annotate_mod.annotate_session(
        entries, annotations, out, profile, roster_data
    ):
        console.print("\n[yellow]stopped early, annotations saved[/yellow]")

    annotate_mod.summarize(console, entries, annotations)
    outro(f"aos-eval taxonomy --dataset {dataset_path} --annotations {out}")


@main.group()
def boundaries() -> None:
    """Declare boundaries once, derive the cases the board must contain."""


@boundaries.command(name="derive")
@click.argument("declaration", type=click.Path(exists=True, path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
@click.option("--test-type", default=boundaries_mod.DEFAULT_TEST_TYPE, show_default=True)
@click.pass_context
def boundaries_derive(
    context: click.Context, declaration: Path, out: Path | None, test_type: str
) -> None:
    """Turn a declaration into the paired challenges a dataset must write."""
    intro(context)
    try:
        declared = boundaries_mod.load_declaration(read_yaml(declaration))
    except boundaries_mod.DeclarationError as broken:
        click.echo(f"aos-eval boundaries: {broken}", err=True)
        raise SystemExit(1) from broken

    derived = boundaries_mod.derive_challenges(declared, test_type)
    payload = [c.model_dump(mode="json", exclude_none=True) for c in derived]
    write_out(dump_yaml({"challenges": payload}), out)
    outro(f"write a prompt into each of the {len(derived)} challenges, then `boundaries check`")


@boundaries.command(name="check")
@click.argument("declaration", type=click.Path(exists=True, path_type=Path))
@click.option("--dataset", "dataset_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--test-type", default=boundaries_mod.DEFAULT_TEST_TYPE, show_default=True)
@click.pass_context
def boundaries_check(
    context: click.Context, declaration: Path, dataset_path: Path, test_type: str
) -> None:
    """Compare the derived challenges to what the dataset actually wrote."""
    intro(context)
    try:
        declared = boundaries_mod.load_declaration(read_yaml(declaration))
    except boundaries_mod.DeclarationError as broken:
        click.echo(f"aos-eval boundaries: {broken}", err=True)
        raise SystemExit(1) from broken

    derived = boundaries_mod.derive_challenges(declared, test_type)
    report = boundaries_mod.check_coverage(derived, load_dataset(dataset_path))
    if report.ok:
        click.echo(f"every one of the {len(derived)} derived challenges is written and paired")
        return
    for line in report.lines():
        click.echo(line, err=True)
    raise SystemExit(1)


@main.command()
@click.option("--dataset", "dataset_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--annotations", "annotations_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.pass_context
def pairs(context: click.Context, dataset_path: Path, annotations_path: Path) -> None:
    """Print pair results. The pair is the scoring unit, never the half."""
    intro(context)
    results = pair_results(load_dataset(dataset_path), load_annotations(annotations_path))
    for pair in results:
        state = "pass" if pair.passed else ("incomplete" if not pair.complete else "fail")
        click.echo(f"{pair.pair_id}  {pair.role}  {pair.boundary}  {state}")
    passed = sum(1 for pair in results if pair.passed)
    click.echo(f"{passed}/{len(results)} pairs passed")


@main.command()
@click.option("--dataset", "dataset_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--annotations", "annotations_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--format", "output_format", type=click.Choice(("text", "yaml")), default="text")
@click.option("--out", type=click.Path(path_type=Path))
@click.pass_context
def taxonomy(
    context: click.Context,
    dataset_path: Path,
    annotations_path: Path,
    output_format: str,
    out: Path | None,
) -> None:
    """Cluster deductions into a ranked failure taxonomy."""
    intro(context)
    entries = load_dataset(dataset_path)
    modes = taxonomy_mod.build(entries, load_annotations(annotations_path))
    rendered = (
        dump_yaml({"failure_taxonomy": [mode.to_dict() for mode in modes]})
        if output_format == "yaml"
        else taxonomy_mod.render(modes, len(entries))
    )
    write_out(rendered, out)


@main.command()
@click.option("--dataset", "dataset_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--profile", "profile_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def validate(context: click.Context, dataset_path: Path, profile_path: Path | None) -> None:
    """Check a dataset against a profile's required fields."""
    intro(context)
    entries = load_dataset(dataset_path)
    problems = dataset_mod.validate([entry.challenge for entry in entries], load_profile(profile_path))
    if not problems:
        click.echo(f"{len(entries)} challenges match the profile")
        return
    for problem in problems:
        click.echo(problem, err=True)
    raise SystemExit(1)


@main.command()
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", type=click.Path(path_type=Path))
@click.option(
    "--include-private",
    is_flag=True,
    help="also export critique and evidence, written for the grader rather than an audience",
)
@click.option("--format", "output_format", type=click.Choice(("json", "yaml")), default="json")
@click.pass_context
def export(
    context: click.Context,
    run_dir: Path,
    out: Path | None,
    include_private: bool,
    output_format: str,
) -> None:
    """Project a committed run into a display payload. One way, never back."""
    intro(context)
    try:
        run = export_run_dir(run_dir, include_private)
    except ExportRefusedError as refusal:
        click.echo(f"aos-eval export: {refusal}", err=True)
        raise SystemExit(1) from refusal

    payload = run.to_dict()
    text = (
        json.dumps(payload, indent=2, sort_keys=False)
        if output_format == "json"
        else dump_yaml(payload)
    )
    write_out(text, out)
    counts = run.counts()
    outro(f"{counts['cases']} cases and {counts['pairs']} pairs are ready for the display surface")


if __name__ == "__main__":
    sys.exit(main())
