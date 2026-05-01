"""Audit /host/etc/ssh/sshd_config for risky directives."""
from __future__ import annotations

import hashlib
import time

from app.audits import register
from app.schemas import AuditReport, Finding, Severity
from app.util.paths import SSHD_CONFIG

# OpenSSH directive parsing: case-insensitive key, last-occurrence wins. Comments
# (`#` at line start, possibly preceded by whitespace) are ignored.
_WEAK_CIPHERS: tuple[str, ...] = ("arcfour", "3des-cbc", "blowfish", "cast128-cbc")
_WEAK_MACS: tuple[str, ...] = ("hmac-md5", "hmac-sha1")


def _fid(check: str, evidence: str) -> str:
    """Deterministic Finding.id keyed on check + evidence string."""
    return f"ssh.{check}.{hashlib.sha1(evidence.encode()).hexdigest()[:10]}"


def _parse(text: str) -> dict[str, tuple[str, int]]:
    """Last-occurrence-wins map of lower-cased key -> (raw value, 1-based line number)."""
    out: dict[str, tuple[str, int]] = {}
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # `Key value...` — split once on whitespace; OpenSSH treats remainder as value.
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        key, value = parts[0].lower(), parts[1].strip()
        out[key] = (value, i)
    return out


def _comma_tokens(value: str) -> list[str]:
    """Split a comma-separated SSH list (Ciphers/MACs) into trimmed lower-case tokens."""
    return [t.strip().lower() for t in value.split(",") if t.strip()]


def _now() -> float:
    return time.time()


@register("ssh")
async def audit_ssh_config() -> AuditReport:
    """Parse sshd_config and emit findings for risky settings."""
    findings: list[Finding] = []

    if not SSHD_CONFIG.exists():
        ev = "sshd_config-missing"
        findings.append(Finding(
            id=_fid("not_installed", ev),
            category="ssh",
            severity="info",
            title="SSH server not installed",
            description=(
                "No /etc/ssh/sshd_config was found on the host. SSH is not "
                "configured here, so SSH-based remote access is unavailable. "
                "If this host is intended to allow SSH login, install openssh-server."
            ),
            evidence={"path": str(SSHD_CONFIG)},
            fix_id=None,
            status="open",
            created_at=_now(),
        ))
        return AuditReport(name="ssh", findings=findings)

    try:
        text = SSHD_CONFIG.read_text(errors="replace")
    except OSError as e:
        ev = f"sshd_config-read-error:{e}"
        findings.append(Finding(
            id=_fid("read_error", ev),
            category="ssh",
            severity="info",
            title="Could not read sshd_config",
            description=(
                "An error prevented Beacon from reading /etc/ssh/sshd_config; "
                "fix the file permissions or ownership so the audit can run."
            ),
            evidence={"path": str(SSHD_CONFIG), "error": str(e)},
            fix_id=None,
            status="open",
            created_at=_now(),
        ))
        return AuditReport(name="ssh", findings=findings)

    cfg = _parse(text)
    now = _now()

    # PermitRootLogin yes / without-password
    val_line = cfg.get("permitrootlogin")
    if val_line is not None:
        value, lineno = val_line
        v = value.lower()
        if v in ("yes", "without-password"):
            ev = f"PermitRootLogin {value}@{lineno}"
            findings.append(Finding(
                id=_fid("permit_root_login", ev),
                category="ssh",
                severity="high",
                title="SSH permits direct root login",
                description=(
                    "PermitRootLogin is set to '" + value + "'. This allows "
                    "interactive SSH sessions for the root account, expanding "
                    "the blast radius of any leaked or brute-forced credential. "
                    "The fix sets PermitRootLogin to 'no' so admins must log in "
                    "as a normal user and escalate via sudo."
                ),
                evidence={"key": "PermitRootLogin", "value": value, "line_number": lineno},
                fix_id="ssh.permit_root_login",
                status="open",
                created_at=now,
            ))

    # PasswordAuthentication yes (and KbdInteractiveAuthentication yes amplifies)
    val_line = cfg.get("passwordauthentication")
    if val_line is not None and val_line[0].lower() == "yes":
        value, lineno = val_line
        kbd = cfg.get("kbdinteractiveauthentication") or cfg.get("challengeresponseauthentication")
        kbd_yes = bool(kbd and kbd[0].lower() == "yes")
        ev = f"PasswordAuthentication yes@{lineno}|kbd={kbd_yes}"
        findings.append(Finding(
            id=_fid("password_authentication", ev),
            category="ssh",
            severity="medium",
            title="SSH allows password authentication",
            description=(
                "PasswordAuthentication is enabled, so SSH accepts username + "
                "password logins in addition to keys. That exposes the host to "
                "credential-stuffing and brute-force attacks. The fix turns "
                "password auth off in favor of public-key authentication; "
                "ensure your authorized_keys is in place before applying."
                + (" KbdInteractiveAuthentication is also yes, which provides a "
                   "second password-style path that the fix will also disable."
                   if kbd_yes else "")
            ),
            evidence={
                "key": "PasswordAuthentication",
                "value": value,
                "line_number": lineno,
                "kbd_interactive_yes": kbd_yes,
            },
            fix_id="ssh.password_authentication",
            status="open",
            created_at=now,
        ))

    # PermitEmptyPasswords yes
    val_line = cfg.get("permitemptypasswords")
    if val_line is not None and val_line[0].lower() == "yes":
        value, lineno = val_line
        ev = f"PermitEmptyPasswords yes@{lineno}"
        findings.append(Finding(
            id=_fid("permit_empty_passwords", ev),
            category="ssh",
            severity="critical",
            title="SSH permits accounts with empty passwords",
            description=(
                "PermitEmptyPasswords is yes. Any local account with a blank "
                "password becomes a remote login over SSH. The fix sets the "
                "directive to 'no' immediately."
            ),
            evidence={"key": "PermitEmptyPasswords", "value": value, "line_number": lineno},
            fix_id="ssh.permit_empty_passwords",
            status="open",
            created_at=now,
        ))

    # Protocol 1 (legacy)
    val_line = cfg.get("protocol")
    if val_line is not None and "1" in {t.strip() for t in val_line[0].split(",")}:
        value, lineno = val_line
        ev = f"Protocol {value}@{lineno}"
        findings.append(Finding(
            id=_fid("protocol_1", ev),
            category="ssh",
            severity="high",
            title="SSH protocol 1 enabled",
            description=(
                "SSH protocol 1 is cryptographically broken and was removed "
                "from OpenSSH years ago. Set 'Protocol 2' (or remove the line) "
                "and restart sshd."
            ),
            evidence={"key": "Protocol", "value": value, "line_number": lineno},
            fix_id=None,
            status="open",
            created_at=now,
        ))

    # Port 22 (advisory)
    val_line = cfg.get("port")
    if val_line is not None and val_line[0].strip() == "22":
        value, lineno = val_line
        ev = f"Port 22@{lineno}"
        findings.append(Finding(
            id=_fid("default_port", ev),
            category="ssh",
            severity="info",
            title="SSH listening on default port 22",
            description=(
                "SSH is bound to port 22, the default that automated scanners "
                "target first. This is informational only — moving the port is "
                "obscurity, not security, but combined with key-only auth and "
                "fail2ban it can reduce log noise."
            ),
            evidence={"key": "Port", "value": value, "line_number": lineno},
            fix_id=None,
            status="open",
            created_at=now,
        ))

    # X11Forwarding yes
    val_line = cfg.get("x11forwarding")
    if val_line is not None and val_line[0].lower() == "yes":
        value, lineno = val_line
        ev = f"X11Forwarding yes@{lineno}"
        findings.append(Finding(
            id=_fid("x11_forwarding", ev),
            category="ssh",
            severity="low",
            title="X11 forwarding enabled",
            description=(
                "X11Forwarding is enabled. Unless you actively need to tunnel "
                "GUI applications over SSH, disabling this reduces the attack "
                "surface from a compromised client running malicious X clients."
            ),
            evidence={"key": "X11Forwarding", "value": value, "line_number": lineno},
            fix_id=None,
            status="open",
            created_at=now,
        ))

    # Weak ciphers
    val_line = cfg.get("ciphers")
    if val_line is not None:
        value, lineno = val_line
        toks = _comma_tokens(value)
        weak = [t for t in toks if any(w in t for w in _WEAK_CIPHERS)]
        if weak:
            ev = f"Ciphers weak={','.join(weak)}@{lineno}"
            findings.append(Finding(
                id=_fid("weak_ciphers", ev),
                category="ssh",
                severity="medium",
                title="SSH offers weak ciphers",
                description=(
                    "The Ciphers directive lists algorithms that are deprecated "
                    "or known-broken (" + ", ".join(weak) + "). Trim them out "
                    "and rely on modern AEAD ciphers like chacha20-poly1305 and "
                    "aes256-gcm."
                ),
                evidence={
                    "key": "Ciphers",
                    "value": value,
                    "line_number": lineno,
                    "weak": weak,
                },
                fix_id=None,
                status="open",
                created_at=now,
            ))

    # Weak MACs (hmac-sha1 without -etm is the risky form; -etm variants are OK)
    val_line = cfg.get("macs")
    if val_line is not None:
        value, lineno = val_line
        toks = _comma_tokens(value)
        weak: list[str] = []
        for t in toks:
            if "etm" in t:
                continue
            if any(w in t for w in _WEAK_MACS):
                weak.append(t)
        if weak:
            ev = f"MACs weak={','.join(weak)}@{lineno}"
            findings.append(Finding(
                id=_fid("weak_macs", ev),
                category="ssh",
                severity="medium",
                title="SSH offers weak MAC algorithms",
                description=(
                    "The MACs directive lists weak message-authentication "
                    "algorithms (" + ", ".join(weak) + "). Replace them with "
                    "modern -etm variants (e.g. hmac-sha2-256-etm@openssh.com)."
                ),
                evidence={
                    "key": "MACs",
                    "value": value,
                    "line_number": lineno,
                    "weak": weak,
                },
                fix_id=None,
                status="open",
                created_at=now,
            ))

    return AuditReport(name="ssh", findings=findings)
