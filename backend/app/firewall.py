"""UFW (Uncomplicated Firewall) wrapper.

All commands run via ``nsenter`` so ufw operates in the host's namespaces and
sees the host's kernel netfilter state. Every user-controlled string is regex
validated before reaching ``run()``; ``trust_args=True`` is used only when the
remaining args are fixed ufw subcommand tokens.
"""
from __future__ import annotations

import re

from app.util.nsenter import nsenter
from app.util.sh import CommandRejected, run

_ACTIONS: frozenset[str] = frozenset({"allow", "deny", "reject", "limit"})
_PROTOS: frozenset[str] = frozenset({"tcp", "udp"})

# Service-style port aliases (e.g. "ssh", "apache2", "OpenSSH"). Keep generous
# enough to cover the typical /etc/services + ufw application profiles.
_SERVICE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
_SOURCE_RE = re.compile(r"^(any|[0-9a-fA-F:./]+)$")
_COMMENT_RE = re.compile(r"^[A-Za-z0-9 _.,:/@+\-]{1,120}$")
_ACTION_LINE_RE = re.compile(
    # ufw status verbose splits the rule into:
    #   <to>  <action>[(v6)?]  <from>  [# <comment>]
    # The "to" and "from" fields can themselves contain spaces (e.g. "Anywhere
    # on eth0"), so split on the action keyword.
    r"^(?P<to>.+?)\s+(?P<action>ALLOW|DENY|REJECT|LIMIT)(?:\s+IN| OUT)?(?:\s*\(v6\))?\s+(?P<from>.+?)(?:\s*#\s*(?P<comment>.*))?$",
)
_PROTO_TAG_RE = re.compile(r"/(tcp|udp)\b", re.IGNORECASE)


class FirewallError(RuntimeError):
    """ufw failed in a way that should surface to the caller."""


def _validate_action(action: str) -> str:
    a = (action or "").strip().lower()
    if a not in _ACTIONS:
        raise ValueError(f"invalid action: {action!r}")
    return a


def _validate_proto(proto: str | None) -> str | None:
    if proto is None:
        return None
    p = proto.strip().lower()
    if p in ("", "any"):
        return None
    if p not in _PROTOS:
        raise ValueError(f"invalid proto: {proto!r}")
    return p


def _validate_port(port: int | str) -> str:
    """Return the canonical token to pass to ufw (numeric string or service name)."""
    if isinstance(port, bool):  # bool is an int subclass — reject explicitly
        raise ValueError(f"invalid port: {port!r}")
    if isinstance(port, int):
        if not 1 <= port <= 65535:
            raise ValueError(f"port out of range: {port}")
        return str(port)
    if isinstance(port, str):
        s = port.strip()
        if s.isdigit():
            n = int(s)
            if not 1 <= n <= 65535:
                raise ValueError(f"port out of range: {s}")
            return str(n)
        if _SERVICE_RE.match(s):
            return s
        raise ValueError(f"invalid port/service: {port!r}")
    raise ValueError(f"invalid port type: {type(port).__name__}")


def _validate_source(source: str | None) -> str | None:
    if source is None:
        return None
    s = source.strip()
    if not s or s.lower() == "any":
        return None
    if not _SOURCE_RE.match(s) or len(s) > 64:
        raise ValueError(f"invalid source: {source!r}")
    return s


def _validate_comment(comment: str | None) -> str | None:
    if comment is None:
        return None
    s = comment.strip()
    if not s:
        return None
    if not _COMMENT_RE.match(s):
        raise ValueError("invalid comment (allowed: letters, digits, spaces, .,:/@+_-)")
    return s


def _ufw(args: list[str], *, timeout: float = 30) -> tuple[int, str, str]:
    cmd = nsenter(["ufw", *args])
    try:
        # ufw subcommand tokens are fixed strings; user-controlled fields are
        # regex-validated upstream, so trusting args here is safe.
        cc = run(cmd, timeout=timeout, trust_args=True)
    except CommandRejected as e:
        raise FirewallError(f"ufw command rejected: {e}") from e
    return cc.returncode, cc.stdout, cc.stderr


def _is_not_installed(rc: int, stdout: str, stderr: str) -> bool:
    haystack = (stdout + "\n" + stderr).lower()
    if rc != 0 and (
        "command not found" in haystack
        or "no such file" in haystack
        or "ufw: not found" in haystack
        or "executable file not found" in haystack
    ):
        return True
    return False


def _parse_status(stdout: str) -> dict:
    """Parse `ufw status verbose` output into a structured dict."""
    active = False
    default_in = "deny"
    default_out = "allow"
    rules: list[dict] = []

    in_rules = False
    for raw in stdout.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        low = s.lower()

        if low.startswith("status:"):
            active = "active" in low
            continue
        if low.startswith("default:"):
            # "Default: deny (incoming), allow (outgoing), disabled (routed)"
            for chunk in s.split(":", 1)[1].split(","):
                c = chunk.strip()
                if "(incoming)" in c:
                    default_in = c.split()[0].lower()
                elif "(outgoing)" in c:
                    default_out = c.split()[0].lower()
            continue

        if low.startswith("to ") and " action " in low:
            in_rules = True
            continue
        # Skip the dashed separator line under the header.
        if set(s) <= {"-", " "}:
            continue
        if not in_rules:
            continue
        # Skip rule-number prefix like "[ 1] ".
        cleaned = re.sub(r"^\[\s*\d+\s*\]\s*", "", s)
        m = _ACTION_LINE_RE.match(cleaned)
        if not m:
            continue
        to = m.group("to").strip()
        action = m.group("action").upper()
        from_ = m.group("from").strip()
        comment = (m.group("comment") or "").strip() or None
        proto: str | None = None
        proto_match = _PROTO_TAG_RE.search(to)
        if proto_match:
            proto = proto_match.group(1).lower()
        rules.append({
            "to": to,
            "action": action,
            "from": from_,
            "proto": proto,
            "comment": comment,
        })

    return {
        "installed": True,
        "active": active,
        "default_incoming": default_in,
        "default_outgoing": default_out,
        "rules": rules,
    }


def status() -> dict:
    """Return parsed ufw status. ``{"installed": False}`` if ufw is missing."""
    rc, out, err = _ufw(["status", "verbose"], timeout=20)
    if _is_not_installed(rc, out, err):
        return {"installed": False}
    if rc != 0 and not out:
        raise FirewallError((err or "ufw status failed").strip())
    return _parse_status(out)


def list_rules() -> list[dict]:
    """Return just the rules list from ``status()``."""
    s = status()
    if not s.get("installed", False):
        return []
    return s.get("rules", [])


def add_rule(
    action: str,
    port: int | str,
    proto: str | None = None,
    source: str | None = None,
    comment: str | None = None,
) -> dict:
    """Append a ufw rule. Returns ``{"ok", "output"}``.

    Examples:
        add_rule("allow", 22, "tcp")
        add_rule("deny", "ssh", source="10.0.0.0/8")
    """
    a = _validate_action(action)
    p_token = _validate_port(port)
    proto_v = _validate_proto(proto)
    src = _validate_source(source)
    cmt = _validate_comment(comment)

    args: list[str] = [a]
    if src:
        args += ["from", src, "to", "any", "port", p_token]
        if proto_v:
            args += ["proto", proto_v]
    else:
        args += [p_token + "/" + proto_v] if proto_v else [p_token]
    if cmt:
        args += ["comment", cmt]

    rc, out, err = _ufw(args, timeout=20)
    combined = (out + err).strip()
    return {"ok": rc == 0, "output": combined}


def delete_rule(rule_number: int) -> dict:
    """Delete the rule at the given 1-based position."""
    if not isinstance(rule_number, int) or isinstance(rule_number, bool):
        raise ValueError(f"invalid rule_number: {rule_number!r}")
    if not 1 <= rule_number <= 999:
        raise ValueError(f"rule_number out of range: {rule_number}")
    rc, out, err = _ufw(["--force", "delete", str(rule_number)], timeout=20)
    combined = (out + err).strip()
    return {"ok": rc == 0, "output": combined}


def enable() -> dict:
    """Activate ufw."""
    rc, out, err = _ufw(["--force", "enable"], timeout=20)
    return {"ok": rc == 0, "output": (out + err).strip()}


def disable() -> dict:
    """Deactivate ufw."""
    rc, out, err = _ufw(["--force", "disable"], timeout=20)
    return {"ok": rc == 0, "output": (out + err).strip()}
