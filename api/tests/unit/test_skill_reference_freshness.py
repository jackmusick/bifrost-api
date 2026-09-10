"""Manifest coverage for the bifrost-build skill's curated reference docs.

This test keeps references/sources.yaml aligned with the checked-in reference
files without requiring git metadata in the Docker pytest runner. Hard generated
appendix freshness remains covered by tests/unit/test_skill_appendix_fresh.py.
Codex mirror parity and public plugin skill naming are enforced host-side by
scripts/check_skill_mirrors.py through test.sh repository_ci_checks and CI.
"""

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[3]  # api/tests/unit → repo root
_SKILL_ROOT = _REPO / ".claude" / "skills" / "bifrost-build"
_MANIFEST = _SKILL_ROOT / "references" / "sources.yaml"
_REFS_DIR = _SKILL_ROOT / "references"


def _load_manifest() -> list[dict]:
    """Load references/sources.yaml and return the list under 'references'."""
    assert _MANIFEST.exists(), f"sources.yaml not found: {_MANIFEST}"
    with _MANIFEST.open() as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict) and "references" in data, (
        "sources.yaml must have a top-level 'references' key"
    )
    return data["references"]


def test_manifest_covers_all_reference_files() -> None:
    """Every references/*.md on disk has a manifest entry, and vice versa."""
    entries = _load_manifest()
    manifest_files = {e["file"] for e in entries}

    disk_files = {f"references/{p.name}" for p in _REFS_DIR.glob("*.md")}

    missing_from_manifest = disk_files - manifest_files
    assert not missing_from_manifest, (
        "Reference files on disk but missing from sources.yaml:\n  "
        + "\n  ".join(sorted(missing_from_manifest))
        + "\nAdd an entry to .claude/skills/bifrost-build/references/sources.yaml."
    )

    extra_in_manifest = manifest_files - disk_files
    assert not extra_in_manifest, (
        "sources.yaml entries that don't correspond to a file on disk:\n  "
        + "\n  ".join(sorted(extra_in_manifest))
        + "\nRemove the stale entry or create the missing file."
    )

    for entry in entries:
        for key in ("file", "source_globs", "verified_at_sha"):
            assert key in entry, (
                f"Entry for {entry.get('file', '?')} is missing key '{key}'"
            )
