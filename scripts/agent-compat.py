#!/usr/bin/env python3
"""Daily unittest smoke checks for local agent harness compatibility."""
from __future__ import annotations

import argparse
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


def run_command(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        env=env,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


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


def goose_env() -> dict[str, str]:
    config = load_yaml(GOOSE_CONFIG)
    return {
        "OLLAMA_HOST": os.environ.get("OLLAMA_HOST") or str(config.get("OLLAMA_HOST", "")),
        "GOOSE_MODEL": os.environ.get("GOOSE_MODEL") or str(config.get("GOOSE_MODEL", "")),
    }


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


class AiderCompat(CompatCase):
    command = "aider"
    version_args = ["--version"]

    def test_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()


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


class QwenCompat(CompatCase):
    command = "ollama"
    version_args = ["--version"]

    def test_ollama_cli_version_runs(self) -> None:
        self.assert_cli_available()
        self.assert_version_succeeds()

    def test_qwen_model_inventory_is_reachable(self) -> None:
        self.assert_cli_available()
        env = merged_env(goose_env())
        try:
            proc = run_command(["ollama", "list"], env=env)
        except subprocess.TimeoutExpired as exc:
            self.fail(f"ollama list timed out after {exc.timeout}s")
        self.assertEqual(proc.returncode, 0, "ollama model inventory is not reachable")
        self.assertIn("qwen", proc.stdout.lower(), "ollama model inventory has no qwen model")


HARNESS_CASES: dict[str, type[unittest.TestCase]] = {
    "claude": ClaudeCompat,
    "codex": CodexCompat,
    "goose": GooseCompat,
    "aider": AiderCompat,
    "opencode": OpenCodeCompat,
    "qwen": QwenCompat,
}


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
        help="Run one harness check. Repeat to select several. Defaults to all.",
    )
    parser.add_argument("--list", action="store_true", help="List harness names and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.list:
        for name in sorted(HARNESS_CASES):
            print(name)
        return 0

    harnesses = args.harness or sorted(HARNESS_CASES)
    suite = build_suite(harnesses)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
