"""Project agent-compose role personalities into an AOS alignment artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTION_PATH = Path("aos-cli") / "role-personalities.json"
DEFAULT_OUTPUT = REPO_ROOT / PROJECTION_PATH
DEFAULT_ROLE_SCOPE = REPO_ROOT / ".agents" / "harness-launch-profiles.yaml"
DEFAULT_PERSON_SNAPSHOT = (
    Path.home() / ".agent-compose" / "sources" / "personality" / "person.json"
)
FORMAT = "agentic-os.role-personality-board.v1"
PERSON_SNAPSHOT_FORMAT = "agent-compose.person-snapshot.v3"
PERSON_SNAPSHOT_SCHEMA_VERSION = 3
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class RolePersonalitySyncError(RuntimeError):
    """An agent-compose person snapshot or AOS alignment board is invalid."""


@dataclass(frozen=True)
class RolePersonalities:
    role: str
    personalities: tuple[str, ...]


@dataclass(frozen=True)
class PersonSnapshot:
    roles: tuple[RolePersonalities, ...]
    skills: tuple[tuple[str, str], ...]


def personality_skill_id(personality: str) -> str:
    return f"personality-{personality}"


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise RolePersonalitySyncError(f"{label} must be a string-keyed mapping")
    return value


def _slug(value: object, label: str) -> str:
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise RolePersonalitySyncError(f"{label} must be a lowercase slug")
    return value


def load_person_snapshot(path: Path) -> PersonSnapshot:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RolePersonalitySyncError(f"read {path}: {exc}") from exc
    if (
        not isinstance(document, dict)
        or document.get("format") != PERSON_SNAPSHOT_FORMAT
        or document.get("schema_version") != PERSON_SNAPSHOT_SCHEMA_VERSION
    ):
        raise RolePersonalitySyncError(
            f"{path}: expected {PERSON_SNAPSHOT_FORMAT} schema "
            f"{PERSON_SNAPSHOT_SCHEMA_VERSION}"
        )

    role_order = document.get("role_order")
    raw_roles = _mapping(document.get("roles"), f"{path}: roles")
    raw_personalities = _mapping(
        document.get("personalities"), f"{path}: personalities"
    )
    if (
        not isinstance(role_order, list)
        or not role_order
        or not all(isinstance(role, str) for role in role_order)
    ):
        raise RolePersonalitySyncError(f"{path}: role_order is malformed")
    ordered_roles = tuple(
        _slug(role, f"{path}: role_order entry") for role in role_order
    )
    if (
        len(set(ordered_roles)) != len(ordered_roles)
        or set(ordered_roles) != set(raw_roles)
    ):
        raise RolePersonalitySyncError(
            f"{path}: role_order does not cover roles exactly"
        )

    roles: list[RolePersonalities] = []
    selected: list[str] = []
    selected_set: set[str] = set()
    for role in ordered_roles:
        raw_role = _mapping(raw_roles[role], f"{path}: role {role}")
        raw_meld = raw_role.get("personalities")
        if (
            not isinstance(raw_meld, list)
            or not 2 <= len(raw_meld) <= 4
            or not all(isinstance(value, str) for value in raw_meld)
        ):
            raise RolePersonalitySyncError(
                f"{path}: role {role} personalities are malformed"
            )
        meld = tuple(
            _slug(value, f"{path}: role {role} personality")
            for value in raw_meld
        )
        if len(set(meld)) != len(meld):
            raise RolePersonalitySyncError(
                f"{path}: role {role} repeats a personality"
            )
        roles.append(RolePersonalities(role=role, personalities=meld))
        for personality in meld:
            if personality not in selected_set:
                selected.append(personality)
                selected_set.add(personality)

    personality_slugs = {
        _slug(personality, f"{path}: personality key")
        for personality in raw_personalities
    }
    if personality_slugs != selected_set:
        raise RolePersonalitySyncError(
            f"{path}: personality catalog does not match role selections"
        )
    skills: list[tuple[str, str]] = []
    for personality in selected:
        raw_personality = _mapping(
            raw_personalities[personality],
            f"{path}: personality {personality}",
        )
        skill = raw_personality.get("skill")
        if skill != personality_skill_id(personality):
            raise RolePersonalitySyncError(
                f"{path}: personality {personality} has invalid skill binding"
            )
        skills.append((personality, skill))
    return PersonSnapshot(roles=tuple(roles), skills=tuple(skills))


def load_role_scope(path: Path) -> tuple[str, ...]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RolePersonalitySyncError(f"read role scope {path}: {exc}") from exc
    roles: list[str] = []
    in_roles = False
    for line_number, line in enumerate(raw.splitlines(), start=1):
        body = line.split("#", 1)[0].rstrip()
        if not body:
            continue
        indent = len(body) - len(body.lstrip(" "))
        stripped = body.strip()
        if indent == 0:
            in_roles = stripped == "roles:"
            continue
        if not in_roles:
            continue
        if indent == 2 and stripped.endswith(":"):
            roles.append(_slug(stripped[:-1], f"{path}:{line_number}: role"))
            continue
        if indent <= 2:
            raise RolePersonalitySyncError(
                f"{path}:{line_number}: roles must use plain nested mapping keys"
            )
    if not roles:
        raise RolePersonalitySyncError(f"{path}: roles are empty")
    if len(set(roles)) != len(roles):
        raise RolePersonalitySyncError(f"{path}: roles repeat a role")
    return tuple(roles)


def scope_snapshot(snapshot: PersonSnapshot, roles: tuple[str, ...]) -> PersonSnapshot:
    indexed = {role.role: role for role in snapshot.roles}
    missing = [role for role in roles if role not in indexed]
    if missing:
        raise RolePersonalitySyncError(
            "role scope contains roles absent from agent-compose snapshot: "
            + ", ".join(missing)
        )
    selected_roles = tuple(indexed[role] for role in roles)
    selected_personalities = {
        personality
        for role in selected_roles
        for personality in role.personalities
    }
    return PersonSnapshot(
        roles=selected_roles,
        skills=tuple(
            (personality, skill)
            for personality, skill in snapshot.skills
            if personality in selected_personalities
        ),
    )


def render_projection(snapshot: PersonSnapshot) -> str:
    payload = {
        "format": FORMAT,
        "role_count": len(snapshot.roles),
        "personality_count": len(snapshot.skills),
        "roles": [
            {
                "role": role.role,
                "personalities": list(role.personalities),
            }
            for role in snapshot.roles
        ],
        "skills": [
            {
                "personality": personality,
                "skill": skill,
            }
            for personality, skill in snapshot.skills
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def load_projection(path: Path) -> dict[str, tuple[str, ...]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RolePersonalitySyncError(f"read {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise RolePersonalitySyncError(f"{path}: unsupported projection format")
    roles = document.get("roles")
    skills = document.get("skills")
    if not isinstance(roles, list) or not isinstance(skills, list):
        raise RolePersonalitySyncError(
            f"{path}: roles and skills must be lists"
        )

    role_map: dict[str, tuple[str, ...]] = {}
    selected: set[str] = set()
    for index, raw_role in enumerate(roles):
        if not isinstance(raw_role, dict) or set(raw_role) != {
            "role",
            "personalities",
        }:
            raise RolePersonalitySyncError(f"{path}: roles[{index}] is malformed")
        role = raw_role["role"]
        personalities = raw_role["personalities"]
        if (
            not isinstance(role, str)
            or not SLUG_RE.fullmatch(role)
            or role in role_map
            or not isinstance(personalities, list)
            or not personalities
            or not all(
                isinstance(value, str) and SLUG_RE.fullmatch(value)
                for value in personalities
            )
            or len(set(personalities)) != len(personalities)
        ):
            raise RolePersonalitySyncError(f"{path}: roles[{index}] is malformed")
        role_map[role] = tuple(personalities)
        selected.update(personalities)

    bindings: dict[str, str] = {}
    for index, raw_binding in enumerate(skills):
        if not isinstance(raw_binding, dict) or set(raw_binding) != {
            "personality",
            "skill",
        }:
            raise RolePersonalitySyncError(f"{path}: skills[{index}] is malformed")
        personality = raw_binding["personality"]
        skill = raw_binding["skill"]
        if (
            not isinstance(personality, str)
            or not SLUG_RE.fullmatch(personality)
            or personality in bindings
            or not isinstance(skill, str)
            or skill != personality_skill_id(personality)
        ):
            raise RolePersonalitySyncError(f"{path}: skills[{index}] is malformed")
        bindings[personality] = skill

    if set(bindings) != selected:
        raise RolePersonalitySyncError(
            f"{path}: personality bindings do not match role selections"
        )
    if document.get("role_count") != len(role_map):
        raise RolePersonalitySyncError(f"{path}: role_count is inconsistent")
    if document.get("personality_count") != len(bindings):
        raise RolePersonalitySyncError(
            f"{path}: personality_count is inconsistent"
        )
    return role_map


def run(
    person_snapshot: Path,
    output: Path,
    *,
    check: bool,
    role_scope: Path | None = None,
) -> int:
    snapshot = load_person_snapshot(person_snapshot)
    if role_scope is not None:
        snapshot = scope_snapshot(snapshot, load_role_scope(role_scope))
    expected = render_projection(snapshot)
    try:
        current = output.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = ""
    except OSError as exc:
        raise RolePersonalitySyncError(f"read {output}: {exc}") from exc
    if current == expected:
        print(
            "ok: AOS role personalities match agent-compose "
            f"({len(snapshot.roles)} roles, {len(snapshot.skills)} personalities)"
        )
        return 0
    if check:
        print(
            f"drift: {output} does not match {person_snapshot}",
            file=sys.stderr,
        )
        print(
            "run `ward exec sync-role-personalities` from the AOS checkout",
            file=sys.stderr,
        )
        return 1

    try:
        output.write_text(expected, encoding="utf-8")
    except OSError as exc:
        raise RolePersonalitySyncError(f"write {output}: {exc}") from exc
    print(f"updated {output} from {person_snapshot}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without changing the projection",
    )
    parser.add_argument(
        "--if-present",
        action="store_true",
        help="skip when the default agent-compose person snapshot is absent",
    )
    parser.add_argument(
        "--person-snapshot",
        type=Path,
        default=DEFAULT_PERSON_SNAPSHOT,
    )
    parser.add_argument(
        "--role-scope",
        type=Path,
        default=DEFAULT_ROLE_SCOPE,
        help="YAML launch profile whose roles scope the AOS projection",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if args.if_present and not args.person_snapshot.exists():
        print(
            "skip: agent-compose person snapshot is absent at "
            f"{args.person_snapshot}"
        )
        return 0
    try:
        return run(
            args.person_snapshot,
            args.output,
            check=args.check,
            role_scope=args.role_scope,
        )
    except RolePersonalitySyncError as exc:
        print(f"role-personality-sync: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
