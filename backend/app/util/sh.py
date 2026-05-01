"""The ONLY subprocess wrapper. All shell-out goes through `run`.

Direct `import subprocess` outside this file is banned (see
tests/test_no_raw_subprocess.py). Guarantees: shell=False, list-form args,
timeout enforced, args validated against shell-metachar regex unless trusted.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

_METACHAR_RE = re.compile(r"[;&|`$<>\\\n\r]")
DEFAULT_TIMEOUT_S = 30


class CommandRejected(ValueError):
    """Arg failed validation (shell metachar in untrusted arg, or wrong type)."""


@dataclass(frozen=True)
class CompletedCommand:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(
    cmd: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    check: bool = False,
    input: str | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    trust_args: bool = False,
) -> CompletedCommand:
    """Run a command safely. cmd MUST be a list. shell is always False.

    trust_args: skip metachar validation. Use ONLY when args are fixed strings
    or already validated against a strict allowlist (enums, regex'd identifiers).
    """
    if not isinstance(cmd, list) or not cmd:
        raise CommandRejected("cmd must be a non-empty list")
    for i, arg in enumerate(cmd):
        if not isinstance(arg, str):
            raise CommandRejected(f"cmd[{i}] is not a string: {arg!r}")
        if not trust_args and _METACHAR_RE.search(arg):
            raise CommandRejected(f"cmd[{i}] contains shell metachars: {arg!r}")

    proc = subprocess.run(  # noqa: S603
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        input=input,
        cwd=cwd,
        env=env,
    )
    return CompletedCommand(
        cmd=cmd, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr,
    )
