#!/usr/bin/env python3
"""Seed this worktree's running debug stack, retaining resources for UI review.

Uses debug.sh's isolated login in child-process memory. No credentials are
written to disk, printed, or placed in command arguments. The output is a
non-secret JSON review index; redirect it to the desired local report file.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="design-review")
    parser.add_argument("--artifacts", help="Exercise the owned form/webhook and capture Home/execution screenshots here")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    status = subprocess.run(
        ["./debug.sh", "status"], cwd=root, capture_output=True, text=True, check=True
    )
    clean = re.sub(r"\x1b\[[0-9;]*m", "", status.stdout)
    url = re.search(r"^Open:\s+(https?://\S+)", clean, re.M)
    login = re.search(r"^Login:\s+(.+?) / (.+)$", clean, re.M)
    if not (url and login):
        raise SystemExit("Running debug URL/login not found; no resources changed.")
    client = root / "client"
    result = subprocess.run(
        [str(client / "node_modules/.bin/jiti"), "e2e/support/seed-review-pack.ts"],
        cwd=client, text=True,
        input=json.dumps({"url": url[1], "email": login[1], "password": login[2],
                          "namespace": args.namespace,
                          "artifacts": str(Path(args.artifacts).resolve()) if args.artifacts else None}),
        capture_output=True,
    )
    if result.returncode:
        # Never relay unreviewed runtime errors that may contain auth call arguments.
        stages = {"sign in", "ensure connected resources", "verify repeatable resource identities", "execute review form", "deliver local webhook", "review Home layouts"}
        stage = next((value for value in stages if f"Review seeding failed during: {value}." in result.stderr), "start runner")
        print(f"Review seeding failed during: {stage}. Existing resources were preserved; no credentials printed.")
        return result.returncode
    report = json.loads(result.stdout)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
