#!/bin/sh
set -eu

instructions="${HOME}/.codex/AGENTS.md"
skills_root="${HOME}/.agents/skills"
designer_skill="${skills_root}/tooling-designer-interaction-shaping/SKILL.md"
javascript_skill="${skills_root}/coding-javascript/SKILL.md"
react_skill="${skills_root}/coding-javascript-react/SKILL.md"
brainstorming_skill="${skills_root}/tooling-product-brainstorming/SKILL.md"

if [ ! -f "${instructions}" ]; then
    echo "designer smoke: missing Codex instructions at ${instructions}" >&2
    exit 1
fi
if ! rg -Fq "## designer - Product shaping." "${instructions}"; then
    echo "designer smoke: Codex instructions omit the designer role heading" >&2
    exit 1
fi
if ! rg -Fq "You are a designer." "${instructions}"; then
    echo "designer smoke: Codex instructions omit the designer briefing" >&2
    exit 1
fi
if [ ! -f "${designer_skill}" ]; then
    echo "designer smoke: selected composed skill was not promoted to SKILL.md" >&2
    exit 1
fi
if [ ! -f "${javascript_skill}" ] || [ ! -f "${react_skill}" ]; then
    echo "designer smoke: frontend coding skills were not promoted" >&2
    exit 1
fi
if [ ! -f "${brainstorming_skill}" ]; then
    echo "designer smoke: product brainstorming was not promoted" >&2
    exit 1
fi
frontend_count=0
for coding_skill in "${skills_root}"/coding-*; do
    [ -e "${coding_skill}" ] || continue
    case "${coding_skill##*/}" in
        coding-javascript | coding-javascript-react)
            frontend_count=$((frontend_count + 1))
            ;;
        *)
            echo "designer smoke: non-frontend coding skill leaked into the catalog" >&2
            exit 1
            ;;
    esac
done
if [ "${frontend_count}" -ne 2 ] ||
    [ -e "${skills_root}/tooling-qa-adversarial-verification" ]; then
    echo "designer smoke: another role's composed skill leaked into the catalog" >&2
    exit 1
fi
if rg --files "${skills_root}" | rg -q '(^|/)COMPOSED\.md$'; then
    echo "designer smoke: an unpromoted COMPOSED.md leaked into the catalog" >&2
    exit 1
fi

echo "ok: designer Codex home carries its role briefing and frontend skill slice"
