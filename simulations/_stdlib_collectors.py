"""Stdlib-only Discovery collection logic shared by local and Docker execution.

Every function here must avoid third-party imports so this exact module can
be copied unmodified into the minimal PurpleLab Docker lab image and
imported by `docker/target/runner.py` with no dependency on `purplelab`,
`pydantic`, or `typer`.

All collection here is intentionally read-only and bounded:

- no process termination, injection, or memory inspection (T1057)
- no credential, password, hash, or secret material (T1087)
- no scanning, probing, or contact with any other host (T1016)
"""

from __future__ import annotations

import os
import platform
import socket

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX platforms (e.g. Windows dev host)
    pwd = None  # type: ignore[assignment]

_MAX_SAMPLE_ITEMS = 10
_MAX_ITEM_LENGTH = 64


def _bounded_sample(items: list[str], limit: int = _MAX_SAMPLE_ITEMS) -> str:
    """Join a truncated, bounded sample of `items` into a display-safe string."""
    trimmed = [item[:_MAX_ITEM_LENGTH] for item in items[:limit]]
    return ", ".join(trimmed) if trimmed else "none"


def collect_system_information() -> dict[str, str]:
    """T1082: basic OS/kernel/architecture info."""
    return {
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }


def collect_process_information() -> dict[str, str]:
    """T1057: bounded, read-only process enumeration via /proc.

    Uses the /proc filesystem directly rather than spawning `ps`, so no
    subprocess or external command is ever invoked.
    """
    names: list[str] = []
    proc_dir = "/proc"

    try:
        entries = sorted(os.listdir(proc_dir))
    except OSError:
        entries = []

    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"{proc_dir}/{entry}/comm", encoding="utf-8") as handle:
                names.append(handle.read().strip())
        except OSError:
            continue

    return {
        "process_count": str(len(names)),
        "sample_process_names": _bounded_sample(names),
    }


def collect_account_information() -> dict[str, str]:
    """T1087: current user and local account names only -- never credentials."""
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"

    local_accounts: list[str] = []
    if pwd is not None:
        try:
            local_accounts = sorted(entry.pw_name for entry in pwd.getpwall())
        except OSError:
            local_accounts = []

    return {
        "current_user": user,
        "local_account_count": str(len(local_accounts)),
        "sample_local_accounts": _bounded_sample(local_accounts),
    }


def collect_network_configuration() -> dict[str, str]:
    """T1016: this host's own hostname/IP/interfaces -- never external scanning."""
    hostname = socket.gethostname()

    try:
        local_ip = socket.gethostbyname(hostname)
    except OSError:
        local_ip = "unknown"

    interfaces: list[str] = []
    net_dir = "/sys/class/net"
    if os.path.isdir(net_dir):
        try:
            interfaces = sorted(os.listdir(net_dir))
        except OSError:
            interfaces = []

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "interface_count": str(len(interfaces)),
        "sample_interfaces": _bounded_sample(interfaces),
    }
