"""Safety invariant: only app/util/sh.py imports the subprocess module.

Every other file must shell out via `app.util.sh.run`, which enforces list
args, shell=False, timeout, and metachar rejection. This walk-the-tree test
prevents regressions where someone reaches for `subprocess.run` directly.
"""
from __future__ import annotations

import re
from pathlib import Path


def test_no_raw_subprocess_outside_sh() -> None:
    root = Path(__file__).resolve().parent.parent / "app"
    pattern = re.compile(r"^\s*(import subprocess|from subprocess)", re.MULTILINE)
    bad: list[str] = []
    for p in root.rglob("*.py"):
        if p.relative_to(root).as_posix() == "util/sh.py":
            continue
        if pattern.search(p.read_text()):
            bad.append(str(p.relative_to(root)))
    assert not bad, f"Raw subprocess import found in: {bad}"
