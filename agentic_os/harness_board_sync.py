"""Project AOSH's role-intent harness board into AOS's Ward profile and launcher."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AOSH_ROOT = REPO_ROOT.parents[1] / "coilyco-bridge" / "agentic-os-hardware"
DEFAULT_ROLES = REPO_ROOT / ".agents" / "roles.kdl"
DEFAULT_OUTPUT = REPO_ROOT / "aos" / "role-harnesses.json"
DEFAULT_WARD_ROLES = REPO_ROOT / ".ward" / "roles.kdl"
ROLES_PATH = Path("roles.yaml")
SELECTIONS_PATH = Path("agent-selections.yaml")
HARNESSES_PATH = Path("harnesses.yaml")
FORMAT = "agentic-os.role-harness-board.v1"
EXPECTED_ROLE_COUNT = 10
EXPECTED_LANE_COUNT = 16
UNATTENDED_INTENT = "autonomous-coding"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ROLE_RE = re.compile(r"(?m)^\s*role\s+([a-z0-9][a-z0-9-]*)\s+\{$")
KDL_BEGIN = "// BEGIN generated role-intent harness board"
KDL_END = "// END generated role-intent harness board"


class BoardSyncError(RuntimeError):
    """An AOSH source or AOS projection invariant is invalid."""


@dataclass(frozen=True)
class Lane:
    intent: str
    harness: str


@dataclass(frozen=True)
class RoleRoute:
    role: str
    lanes: tuple[Lane, ...]


@dataclass(frozen=True)
class HarnessBoard:
    role_source: str
    roles: tuple[RoleRoute, ...]

    @property
    def lane_count(self) -> int:
        return sum(len(route.lanes) for route in self.roles)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise BoardSyncError(f"read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BoardSyncError(f"{path}: expected a YAML mapping")
    return value


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BoardSyncError(f"{label} must be a mapping")
    return value


def _slug(value: object, label: str) -> str:
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise BoardSyncError(f"{label} must be a lowercase hyphenated slug")
    return value


def load_canonical_roles(path: Path = DEFAULT_ROLES) -> tuple[str, ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BoardSyncError(f"read {path}: {exc}") from exc
    roles = tuple(ROLE_RE.findall(text))
    if len(roles) != EXPECTED_ROLE_COUNT or len(set(roles)) != len(roles):
        raise BoardSyncError(
            f"{path}: expected {EXPECTED_ROLE_COUNT} unique canonical roles, found {len(roles)}"
        )
    return roles


def _check_keys(actual: object, expected: set[str], label: str) -> None:
    if not isinstance(actual, dict):
        raise BoardSyncError(f"{label} must be a mapping")
    if not all(isinstance(key, str) for key in actual):
        raise BoardSyncError(f"{label} keys must be strings")
    actual_keys = set(actual)
    unknown = sorted(actual_keys - expected)
    missing = sorted(expected - actual_keys)
    if unknown or missing:
        raise BoardSyncError(f"{label} mismatch, unknown={unknown}, missing={missing}")


def load_board(
    aosh_root: Path, *, roles_path: Path = DEFAULT_ROLES
) -> HarnessBoard:
    roles_file = aosh_root / ROLES_PATH
    selections_file = aosh_root / SELECTIONS_PATH
    harnesses_file = aosh_root / HARNESSES_PATH
    role_document = _load_yaml(roles_file)
    selection_document = _load_yaml(selections_file)
    harness_document = _load_yaml(harnesses_file)

    role_source = role_document.get("role_source")
    if not isinstance(role_source, str) or not role_source.strip():
        raise BoardSyncError(f"{roles_file}: role_source must be non-empty text")
    roles = _mapping(role_document.get("roles"), f"{roles_file}: roles")
    selections = _mapping(
        selection_document.get("selections"), f"{selections_file}: selections"
    )
    harnesses = _mapping(
        harness_document.get("harnesses"), f"{harnesses_file}: harnesses"
    )
    canonical_roles = load_canonical_roles(roles_path)
    _check_keys(roles, set(canonical_roles), f"{roles_file}: roles")
    _check_keys(selections, set(canonical_roles), f"{selections_file}: selections")

    routes: list[RoleRoute] = []
    unattended_roles: set[str] = set()
    for role in canonical_roles:
        role_spec = _mapping(roles[role], f"{roles_file}: {role}")
        raw_intents = role_spec.get("intents")
        if not isinstance(raw_intents, list) or not 1 <= len(raw_intents) <= 2:
            raise BoardSyncError(f"{roles_file}: {role} must declare one or two intents")
        intents = tuple(
            _slug(value, f"{roles_file}: {role}.intents entry")
            for value in raw_intents
        )
        if len(set(intents)) != len(intents):
            raise BoardSyncError(f"{roles_file}: {role} repeats an intent")
        if UNATTENDED_INTENT in intents:
            unattended_roles.add(role)

        role_selections = _mapping(
            selections[role], f"{selections_file}: {role} selections"
        )
        _check_keys(
            role_selections,
            set(intents),
            f"{selections_file}: {role} selections",
        )
        lanes: list[Lane] = []
        for intent in intents:
            selection = _mapping(
                role_selections[intent],
                f"{selections_file}: {role}/{intent} selection",
            )
            _check_keys(
                selection,
                {"agent"},
                f"{selections_file}: {role}/{intent} selection",
            )
            harness = _slug(
                selection["agent"],
                f"{selections_file}: {role}/{intent}.agent",
            )
            harness_spec = _mapping(
                harnesses.get(harness),
                f"{harnesses_file}: selected harness {harness}",
            )
            supported = harness_spec.get("intents")
            if not isinstance(supported, list) or intent not in supported:
                raise BoardSyncError(
                    f"{harnesses_file}: {harness} does not declare intent {intent}"
                )
            lanes.append(Lane(intent=intent, harness=harness))
        routes.append(RoleRoute(role=role, lanes=tuple(lanes)))

    board = HarnessBoard(role_source=role_source.strip(), roles=tuple(routes))
    if unattended_roles != {"engineer"}:
        raise BoardSyncError(
            f"{roles_file}: {UNATTENDED_INTENT} must belong exclusively to engineer"
        )
    engineer = next(route for route in board.roles if route.role == "engineer")
    if tuple(lane.intent for lane in engineer.lanes) != (UNATTENDED_INTENT,):
        raise BoardSyncError(
            f"{roles_file}: engineer must declare only {UNATTENDED_INTENT}"
        )
    if board.lane_count != EXPECTED_LANE_COUNT:
        raise BoardSyncError(
            f"{roles_file}: expected {EXPECTED_LANE_COUNT} lanes, found {board.lane_count}"
        )
    return board


def render_board(board: HarnessBoard) -> str:
    payload = {
        "format": FORMAT,
        "role_source": board.role_source,
        "role_count": len(board.roles),
        "lane_count": board.lane_count,
        "roles": [
            {
                "role": route.role,
                "intents": [
                    {"intent": lane.intent, "harness": lane.harness}
                    for lane in route.lanes
                ],
            }
            for route in board.roles
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def render_ward_board(board: HarnessBoard) -> str:
    lines = [
        KDL_BEGIN,
        "role-harnesses {",
        f'    format {json.dumps(FORMAT)}',
        f'    role-source {json.dumps(board.role_source)}',
        f"    role-count {len(board.roles)}",
        f"    lane-count {board.lane_count}",
    ]
    for route in board.roles:
        lines.append(f"    role {route.role} {{")
        for lane in route.lanes:
            lines.extend(
                (
                    f"        intent {lane.intent} {{",
                    f"            harness {lane.harness}",
                    "        }",
                )
            )
        lines.append("    }")
    lines.extend(("}", KDL_END))
    return "\n".join(lines) + "\n"


def merge_ward_board(current: str, rendered: str, path: Path) -> str:
    begin_count = current.count(KDL_BEGIN)
    end_count = current.count(KDL_END)
    if begin_count == 0 and end_count == 0:
        return current.rstrip() + "\n\n" + rendered
    if begin_count != 1 or end_count != 1:
        raise BoardSyncError(
            f"{path}: expected one matched generated board marker pair, "
            f"found begin={begin_count}, end={end_count}"
        )
    begin = current.index(KDL_BEGIN)
    end_start = current.index(KDL_END)
    if end_start < begin:
        raise BoardSyncError(f"{path}: generated board markers are out of order")
    end = end_start + len(KDL_END)
    return current[:begin] + rendered.rstrip("\n") + current[end:]


def run(
    aosh_root: Path,
    output: Path,
    *,
    roles_path: Path = DEFAULT_ROLES,
    ward_roles_path: Path = DEFAULT_WARD_ROLES,
    check: bool,
) -> int:
    board = load_board(aosh_root, roles_path=roles_path)
    expected_output = render_board(board)
    try:
        current_output = output.read_text(encoding="utf-8")
    except FileNotFoundError:
        current_output = ""
    except OSError as exc:
        raise BoardSyncError(f"read {output}: {exc}") from exc
    try:
        current_ward_roles = ward_roles_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BoardSyncError(f"read {ward_roles_path}: {exc}") from exc
    expected_ward_roles = merge_ward_board(
        current_ward_roles,
        render_ward_board(board),
        ward_roles_path,
    )

    drift = [
        path
        for path, current, expected in (
            (output, current_output, expected_output),
            (ward_roles_path, current_ward_roles, expected_ward_roles),
        )
        if current != expected
    ]
    if not drift:
        print(
            "ok: AOS role-intent harness defaults match AOSH "
            f"({len(board.roles)} roles, {board.lane_count} lanes)"
        )
        return 0
    if check:
        for path in drift:
            print(
                f"drift: {path} does not match {aosh_root / SELECTIONS_PATH}",
                file=sys.stderr,
            )
        print("run `ward exec sync-harness-board` from the AOS checkout", file=sys.stderr)
        return 1

    try:
        ward_roles_path.write_text(expected_ward_roles, encoding="utf-8")
        output.write_text(expected_output, encoding="utf-8")
    except OSError as exc:
        raise BoardSyncError(f"write harness-board projection: {exc}") from exc
    print(
        f"updated {ward_roles_path} and {output} from "
        f"{aosh_root / SELECTIONS_PATH}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report drift without changing the projection"
    )
    parser.add_argument(
        "--if-present",
        action="store_true",
        help="skip when the default sibling AOSH checkout is absent",
    )
    parser.add_argument("--aosh-root", type=Path, default=DEFAULT_AOSH_ROOT)
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ward-roles", type=Path, default=DEFAULT_WARD_ROLES)
    args = parser.parse_args(argv)

    if args.if_present and not args.aosh_root.exists():
        print(f"skip: AOSH checkout is absent at {args.aosh_root}")
        return 0
    try:
        return run(
            args.aosh_root,
            args.output,
            roles_path=args.roles,
            ward_roles_path=args.ward_roles,
            check=args.check,
        )
    except BoardSyncError as exc:
        print(f"harness-board-sync: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
