#!/usr/bin/env python3
"""Host-side guard for Codex skill mirrors.

The Docker pytest runner intentionally does not mount the whole repository or a
usable .git directory, so mirror hygiene belongs in the host repository checks.
This script regenerates the mirrors from .claude/skills and fails if either
mirror changed, and it enforces the public plugin skill naming contract.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MIRRORS = ("plugins/bifrost/skills", ".codex/skills")
SYNC_SCRIPT = REPO / "scripts" / "sync-codex-skills.sh"
PUBLIC_ROOT = REPO / "plugins" / "bifrost" / "skills"


def _tree_digest(root: Path) -> str:
    """Stable hash of every file path + content under root."""
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            h.update(str(path.relative_to(root)).encode())
            h.update(b"\0")
            h.update(path.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def _check_mirror_sync() -> list[str]:
    errors: list[str] = []
    if not SYNC_SCRIPT.exists():
        return [f"sync script not found: {SYNC_SCRIPT}"]

    missing = [mirror for mirror in MIRRORS if not (REPO / mirror).exists()]
    if missing:
        return ["mirror dirs missing: " + ", ".join(missing)]

    before = {mirror: _tree_digest(REPO / mirror) for mirror in MIRRORS}
    result = subprocess.run(
        ["bash", str(SYNC_SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [
            f"sync script failed with exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        ]

    after = {mirror: _tree_digest(REPO / mirror) for mirror in MIRRORS}
    stale = [mirror for mirror in MIRRORS if before[mirror] != after[mirror]]
    if stale:
        errors.append(
            "Codex skill mirrors are out of sync with .claude/skills/: "
            + ", ".join(stale)
            + ". Run scripts/sync-codex-skills.sh and commit the result."
        )
    return errors


def _check_public_skill_names() -> list[str]:
    errors: list[str] = []
    skill_files = sorted(PUBLIC_ROOT.glob("*/SKILL.md"))
    if not skill_files:
        return [f"no public plugin skills found under {PUBLIC_ROOT}"]

    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*(\S+)\s*$", text, flags=re.MULTILINE)
        if match is None:
            errors.append(f"{skill_file} has no name frontmatter")
            continue
        if match.group(1).startswith("bifrost:"):
            errors.append(
                f"{skill_file} repeats the plugin namespace in skill name "
                f"{match.group(1)!r}"
            )
    return errors


def main() -> int:
    errors = [*_check_mirror_sync(), *_check_public_skill_names()]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Codex skill mirrors are fresh and public plugin skill names are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
