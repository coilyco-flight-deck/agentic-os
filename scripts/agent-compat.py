#!/usr/bin/env python3
"""Daily unittest smoke checks for local agent harness compatibility.

The roster - which harnesses exist and what they are named - is **ward's**, not
this script's. aos is the consumer here: it reads ward's embedded fleet roster
from `ward agents list --json` (ward#417) and never maintains a parallel copy.
`HARNESS_CASES` below holds only the per-harness probe *logic* (how to smoke-test
each), keyed by ward's agent name; `tests/test_agent_compat.py` pins its key set
to `ward agents list --json` so the two can never drift (aos#310 issue 5, the
leak aos#308 flagged). The runtime default set is read live from ward.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a project dependency under ward.
    yaml = None


TIMEOUT_SECONDS = 15
HOME = Path.home()
AGENT_COMPOSE_CONFIG = HOME / ".config" / "agent-compose" / "agent-compose.yaml"
AGENT_COMPOSE_DIR = HOME / ".config" / "agent-compose"
GOOSE_CONFIG = HOME / ".config" / "goose" / "config.yaml"


class WardRosterUnavailable(RuntimeError):
    """`ward agents list --json` could not be read (ward missing, too old, or non-JSON)."""


def run_command(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        env=env,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def ward_roster() -> dict:
    """Return ward's embedded fleet roster from `ward agents list --json` (ward#417).

    This is the single source of truth for which harnesses exist. Raises
    WardRosterUnavailable when the ward binary is absent or predates the
    `agents list --json` surface, so callers can skip or fall back deliberately
    rather than silently shadow a roster.
    """
    if command_path("ward") is None:
        raise WardRosterUnavailable("ward is not on PATH")
    try:
        proc = run_command(["ward", "agents", "list", "--json"])
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - defensive.
        raise WardRosterUnavailable(f"ward agents list --json timed out after {exc.timeout}s") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        raise WardRosterUnavailable(
            "ward agents list --json exited "
            f"{proc.returncode}: {detail[0] if detail else 'no output'}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise WardRosterUnavailable(f"ward agents list --json emitted non-JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("agents"), list):
        raise WardRosterUnavailable("ward agents list --json lacks an agents[] array")
    return data


def ward_roster_names() -> list[str]:
    """The agent names ward embeds, in fleet-KDL source order."""
    return [str(agent.get("name", "")) for agent in ward_roster()["agents"] if agent.get("name")]


def merged_env(updates: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update({k: v for k, v in updates.items() if v})
    return env


def command_path(command: str) -> str | None:
    return shutil.which(command)


def load_yaml(path: Path) -> dict:
    if yaml is None or not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def ollama_env() -> dict[str, str]:
    """Ambient ollama route: env first, then Goose's configured host/model.

    Goose's config doubles as the host-local ollama route on these machines, so
    it is the route source for any harness that talks to ollama (Goose itself and
    opencode, whose backing model is qwen3-coder on the same ollama endpoint).
    """
    config = load_yaml(GOOSE_CONFIG)
    return {
        "OLLAMA_HOST": os.environ.get("OLLAMA_HOST") or str(config.get("OLLAMA_HOST", "")),
        "GOOSE_MODEL": os.environ.get("GOOSE_MODEL") or str(config.get("GOOSE_MODEL", "")),
    }


# Back-compat alias: goose_env() was the pre-repoint name for ollama_env().
goose_env = ollama_env


def load_point_for(harness: str) -> tuple[Path, Path]:
    defaults = {
        "claude": HOME / ".claude" / "CLAUDE.md",
        "codex": HOME / ".codex" / "AGENTS.md",
        "opencode": HOME / ".config" / "opencode" / "AGENTS.md",
    }
    composed = AGENT_COMPOSE_DIR / f"COMPOSED.{harness}.md"
    return defaults[harness], composed


class CompatCase(unittest.TestCase):
    command: str
    version_args: list[str]

    def assert_cli_available(self) -> None:
        path = command_path(self.command)
        self.assertIsNotNone(path, f"{self.command} is not on PATH")

    def assert_command_succeeds(self, args: list[str], env: dict[str, str] | None = None) -> None:
        try:
            proc = run_command(args, env=env)
        except subprocess.TimeoutExpired as exc:
            self.fail(f"{args[0]} timed out after {exc.timeout}s")
        self.assertEqual(
            proc.returncode,
            0,
            f"{args[0]} exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()}",
        )

    def assert_version_succeeds(self) -> None:
        self.assert_command_succeeds([self.command, *self.version_args])


class AgentComposeCase(CompatCase):
    harness: str

    def test_agent_compose_load_point_is_current(self) -> None:
        if not AGENT_COMPOSE_CONFIG.exists():
            self.skipTest("agent-compose is not configured on this host")
        load_point, composed = load_point_for(self.harness)
        self.assertTrue(composed.is_file(), f"missing composed context for {self.harness}")
        self.assertTrue(load_point.exists(), f"missing load point for {self.harness}")
        self.assertTrue(load_point.is_symlink(), f"{load_point} is not a symlink")
        self.assertEqual(load_point.resolve(), composed.resolve())


class ClaudeCompat(AgentComposeCase):
    command = "claude"
    version_args = ["--version"]
    harness = "claude"

    def test_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()


class CodexCompat(AgentComposeCase):
    command = "codex"
    version_args = ["--version"]
    harness = "codex"

    def test_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()


class OpenCodeCompat(AgentComposeCase):
    command = "opencode"
    version_args = ["--version"]
    harness = "opencode"

    def test_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()

    def test_backing_model_inventory_is_reachable(self) -> None:
        # opencode's backing model is qwen3-coder on ollama, so its inventory
        # probe rides opencode - not a shadow "qwen" entry (see docs/agent-compat.md).
        if command_path("ollama") is None:
            self.skipTest("ollama is not on PATH")
        env = merged_env(ollama_env())
        try:
            proc = run_command(["ollama", "list"], env=env)
        except subprocess.TimeoutExpired as exc:
            self.fail(f"ollama list timed out after {exc.timeout}s")
        self.assertEqual(proc.returncode, 0, "ollama model inventory is not reachable")
        self.assertIn("qwen", proc.stdout.lower(), "ollama model inventory has no qwen model")


class GooseCompat(CompatCase):
    command = "goose"
    version_args = ["--version"]

    def test_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()

    def test_config_names_model(self) -> None:
        config = load_yaml(GOOSE_CONFIG)
        model = os.environ.get("GOOSE_MODEL") or config.get("GOOSE_MODEL")
        self.assertTrue(model, "GOOSE_MODEL is not set in env or Goose config")


# Per-harness probe logic keyed by ward's agent name (aos's own code). Its key
# set is NOT a private roster: tests/ pins it to `ward agents list --json`.
HARNESS_CASES: dict[str, type[unittest.TestCase]] = {
    "claude": ClaudeCompat,
    "codex": CodexCompat,
    "opencode": OpenCodeCompat,
    "goose": GooseCompat,
}


def resolve_default_roster() -> list[str]:
    """The harnesses to run by default: ward's live roster, filtered to probes we ship.

    Reads `ward agents list --json` so the default set is ward's, not ours. Falls
    back to the shipped probe keys (pinned == ward by test) when ward is absent or
    too old, and warns to stderr for any ward agent lacking a probe here instead
    of silently dropping it.
    """
    try:
        names = ward_roster_names()
    except WardRosterUnavailable as exc:
        print(
            f"agent-compat: ward roster unavailable ({exc}); using built-in probe set",
            file=sys.stderr,
        )
        return sorted(HARNESS_CASES)
    known = [name for name in names if name in HARNESS_CASES]
    missing = [name for name in names if name not in HARNESS_CASES]
    if missing:
        print(
            "agent-compat: no probe for ward agent(s) "
            f"{', '.join(missing)}; add one to HARNESS_CASES in scripts/agent-compat.py",
            file=sys.stderr,
        )
    return known


def build_suite(harnesses: list[str]) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for harness in harnesses:
        suite.addTests(loader.loadTestsFromTestCase(HARNESS_CASES[harness]))
    return suite


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--harness",
        action="append",
        choices=sorted(HARNESS_CASES),
        help="Run one harness check. Repeat to select several. Defaults to ward's roster.",
    )
    parser.add_argument("--list", action="store_true", help="List harness names and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.list:
        for name in sorted(HARNESS_CASES):
            print(name)
        return 0

    harnesses = args.harness or resolve_default_roster()
    suite = build_suite(harnesses)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
