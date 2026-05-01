"""User account management on the host. All write ops use nsenter to run in
host namespaces so /etc/passwd, /etc/shadow, home dirs, and group membership
behave correctly. SSH key installation writes through /host bind-mount and
re-chowns via nsenter so the host's name resolution applies."""
from __future__ import annotations

import os
import re
from pathlib import Path

from app.config import settings
from app.util.nsenter import nsenter
from app.util.sh import run

USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
FULLNAME_RE = re.compile(r"^[A-Za-z0-9 .,_'-]{0,128}$")
SSH_KEY_RE = re.compile(
    r"^(ssh-rsa|ssh-ed25519|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|"
    r"ecdsa-sha2-nistp521|ssh-dss|sk-ssh-ed25519@openssh\.com|"
    r"sk-ecdsa-sha2-nistp256@openssh\.com) [A-Za-z0-9+/=]+( [^\n\r]*)?$"
)
ALLOWED_SHELLS = frozenset({
    "/bin/bash", "/bin/sh", "/bin/zsh", "/usr/bin/zsh",
    "/usr/sbin/nologin", "/sbin/nologin", "/bin/false",
})

HOST_ROOT = Path(settings.host_root)


class UserError(ValueError):
    pass


def _validate_username(name: str) -> None:
    if not isinstance(name, str) or not USERNAME_RE.match(name):
        raise UserError(f"invalid username: {name!r}")


def list_users() -> list[dict]:
    """Parse /host/etc/passwd. Each entry annotates is_system (uid < 1000, root excepted)."""
    passwd = HOST_ROOT / "etc" / "passwd"
    if not passwd.exists():
        return []
    out: list[dict] = []
    for line in passwd.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 7:
            continue
        name, _, uid_s, gid_s, gecos, home, shell = parts[:7]
        try:
            uid = int(uid_s)
        except ValueError:
            continue
        out.append({
            "username": name,
            "uid": uid,
            "gid": int(gid_s) if gid_s.isdigit() else 0,
            "gecos": gecos,
            "home": home,
            "shell": shell,
            "is_system": uid < 1000 and name != "root",
        })
    return out


def _detect_sudo_group() -> str:
    """`sudo` on Debian/Ubuntu, `wheel` on RHEL family. Probe /etc/group."""
    group = HOST_ROOT / "etc" / "group"
    if not group.exists():
        return "sudo"
    text = group.read_text()
    if any(line.startswith("wheel:") for line in text.splitlines()):
        return "wheel"
    return "sudo"


def create_user(
    username: str,
    *,
    fullname: str | None = None,
    sudo: bool = False,
    password: str | None = None,
    ssh_public_key: str | None = None,
    shell: str = "/bin/bash",
) -> dict:
    """Create a Linux user via useradd; optional sudo group, password (chpasswd
    via stdin), and authorized_keys entry."""
    _validate_username(username)
    if shell not in ALLOWED_SHELLS:
        raise UserError(f"shell not allowed: {shell}")
    if fullname is not None and not FULLNAME_RE.match(fullname):
        raise UserError("invalid fullname")
    if ssh_public_key is not None and not SSH_KEY_RE.match(ssh_public_key.strip()):
        raise UserError("ssh_public_key is not a valid OpenSSH public key")

    if any(u["username"] == username for u in list_users()):
        return {"ok": False, "error": f"user {username} already exists"}

    cmd = ["useradd", "-m", "-s", shell]
    if fullname:
        cmd += ["-c", fullname]
    cmd.append(username)
    r = run(nsenter(cmd))
    if not r.ok:
        return {"ok": False, "error": "useradd failed", "stderr": r.stderr.strip()}

    if sudo:
        sg = _detect_sudo_group()
        r2 = run(nsenter(["usermod", "-aG", sg, username]))
        if not r2.ok:
            return {"ok": False, "error": f"usermod -aG {sg} failed", "stderr": r2.stderr.strip()}

    if password is not None:
        if not (4 <= len(password) <= 256):
            raise UserError("password length must be 4-256 chars")
        # Pipe via stdin so the password never appears in argv / process list.
        r3 = run(nsenter(["chpasswd"]), input=f"{username}:{password}\n")
        if not r3.ok:
            return {"ok": False, "error": "chpasswd failed", "stderr": r3.stderr.strip()}

    if ssh_public_key:
        try:
            add_ssh_key(username, ssh_public_key.strip())
        except Exception as e:
            return {"ok": False, "error": f"user created but ssh key install failed: {e!r}"}

    return {
        "ok": True,
        "username": username,
        "sudo": sudo,
        "password_set": password is not None,
        "ssh_key_installed": bool(ssh_public_key),
    }


def add_ssh_key(username: str, public_key: str) -> dict:
    """Append public_key to ~user/.ssh/authorized_keys (idempotent — skips if
    the same line is already present). Creates the dir/file with strict perms."""
    _validate_username(username)
    public_key = public_key.strip()
    if not SSH_KEY_RE.match(public_key):
        raise UserError("not a valid OpenSSH public key")

    users = {u["username"]: u for u in list_users()}
    if username not in users:
        raise UserError(f"user {username} does not exist")
    home = users[username]["home"]
    if not home.startswith("/"):
        raise UserError(f"unexpected home dir: {home}")

    host_home = HOST_ROOT / home.lstrip("/")
    if not host_home.exists():
        raise UserError(f"home directory {home} does not exist on host")
    ssh_dir = host_home / ".ssh"
    auth = ssh_dir / "authorized_keys"

    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    if not auth.exists():
        auth.touch(mode=0o600)

    existing = auth.read_text() if auth.exists() else ""
    if public_key in existing:
        return {"ok": True, "added": False, "reason": "key already present"}

    with auth.open("a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(public_key + "\n")

    # Re-chown the entire .ssh tree via nsenter so host name resolution applies.
    run(nsenter(["chown", "-R", f"{username}:{username}",
                 str(Path("/") / home.lstrip("/") / ".ssh")]))
    os.chmod(ssh_dir, 0o700)
    os.chmod(auth, 0o600)

    return {"ok": True, "added": True, "user": username, "authorized_keys_path": str(auth)}


def list_ssh_keys(username: str) -> dict:
    """Return the lines of ~user/.ssh/authorized_keys. Comments/blank stripped."""
    _validate_username(username)
    users = {u["username"]: u for u in list_users()}
    if username not in users:
        raise UserError(f"user {username} does not exist")
    home = users[username]["home"]
    auth = HOST_ROOT / home.lstrip("/") / ".ssh" / "authorized_keys"
    if not auth.exists():
        return {"user": username, "keys": []}
    keys: list[dict] = []
    for line in auth.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Best-effort: extract type + comment
        parts = s.split(None, 2)
        keys.append({
            "type": parts[0] if parts else "",
            "fingerprint_preview": parts[1][:16] + "…" if len(parts) > 1 else "",
            "comment": parts[2] if len(parts) > 2 else "",
        })
    return {"user": username, "keys": keys}


def lock_user(username: str) -> dict:
    _validate_username(username)
    if username == "root":
        raise UserError("refusing to lock root")
    r = run(nsenter(["usermod", "--lock", username]))
    return {"ok": r.ok, "stderr": r.stderr.strip()}


def unlock_user(username: str) -> dict:
    _validate_username(username)
    r = run(nsenter(["usermod", "--unlock", username]))
    return {"ok": r.ok, "stderr": r.stderr.strip()}


def set_password(username: str, password: str) -> dict:
    _validate_username(username)
    if not (4 <= len(password) <= 256):
        raise UserError("password length must be 4-256 chars")
    r = run(nsenter(["chpasswd"]), input=f"{username}:{password}\n")
    return {"ok": r.ok, "stderr": r.stderr.strip()}
