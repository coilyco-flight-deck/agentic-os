"""Small YAML-frontmatter helpers shared by AOS inspection tools."""

from __future__ import annotations

import yaml


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Split a leading fenced YAML mapping from its Markdown body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for index in range(1, len(lines)):
        if lines[index].strip() != "---":
            continue
        try:
            metadata = yaml.safe_load("\n".join(lines[1:index])) or {}
        except yaml.YAMLError:
            metadata = {}
        body = "\n".join(lines[index + 1 :])
        if not isinstance(metadata, dict):
            metadata = {}
        return metadata, body
    return {}, text
