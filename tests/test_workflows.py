"""Tests for the GitHub Actions workflows.

Branch filters and checkout refs must name a branch that actually exists.
Git resolves them by exact name under ``refs/heads`` and does not follow the
redirect that GitHub applies to ``blob/<branch>`` web links, so a stale name
silently disables a workflow.

See https://github.com/Textualize/rich/issues/4240
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"

_LIST_ITEM = re.compile(r"^\s*-\s*(?P<value>.+?)\s*$")
_GLOB_CHARS = set("*?[]{}")
_COMMIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _literal_branches(workflow: str) -> set[str]:
    """Return the literal branch names referenced by a workflow source.

    Reads ``branches:`` filters and ``ref:`` keys. Expressions, glob patterns
    and commit SHAs are skipped because they don't name a branch directly.
    """
    branches: set[str] = set()
    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        key, _, value = line.strip().partition(":")
        value = value.strip()
        if key == "branches":
            if value.startswith("["):
                # Flow sequence: branches: [ 'main', 'release/*' ]
                branches.update(value.strip("[]").split(","))
            else:
                # Block sequence, as "- main" lines following the key.
                for following in lines[index + 1 :]:
                    item = _LIST_ITEM.match(following)
                    if item:
                        branches.add(item.group("value"))
                    elif following.strip() and not following.strip().startswith("#"):
                        break
        elif key == "ref":
            branches.add(value)

    return {
        branch.strip().strip("'\"")
        for branch in branches
        if "${{" not in branch
        and not _GLOB_CHARS.intersection(branch)
        and not _COMMIT_SHA.match(branch.strip().strip("'\""))
    }


def _known_branches() -> set[str]:
    """Return the branch names available in this checkout."""
    branches = {
        value
        for env in ("GITHUB_BASE_REF", "GITHUB_HEAD_REF", "GITHUB_REF_NAME")
        if (value := os.environ.get(env))
    }
    try:
        output = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname)",
                "refs/heads",
                "refs/remotes",
            ],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        output = ""
    for ref in output.split():
        name = ref.removeprefix("refs/heads/").removeprefix("refs/remotes/")
        name = name.removeprefix("origin/")
        if name and name != "HEAD" and not name.endswith("/HEAD"):
            branches.add(name)
    return branches


def test_literal_branches():
    """Only literal branch names are extracted from a workflow."""
    workflow = """
on:
  push:
    branches: [ 'main', 'release/*' ]
  pull_request:
    branches:
      - main
      - ${{ github.head_ref }}
  issues:
jobs:
  test:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
      - uses: actions/checkout@v4
        with:
          ref: 0123456789abcdef0123456789abcdef01234567
"""
    assert _literal_branches(workflow) == {"main"}


def test_workflow_branches_exist():
    """Every branch named by a workflow exists in the repository."""
    known_branches = _known_branches()
    if not known_branches:
        pytest.skip("No branch information available in this checkout")

    missing_branches = {
        path.name: sorted(_literal_branches(path.read_text("utf-8")) - known_branches)
        for path in sorted(WORKFLOWS_DIR.glob("*.yml"))
    }
    missing_branches = {
        name: missing for name, missing in missing_branches.items() if missing
    }

    assert (
        not missing_branches
    ), f"Workflows reference missing branches: {missing_branches}"
