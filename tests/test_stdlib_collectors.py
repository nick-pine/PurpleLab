"""Tests for PurpleLab's shared, stdlib-only Discovery collectors (Milestone 6).

These exercise the real bounding/formatting logic. OS interactions are
mocked so results don't depend on the developer's actual machine state.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from simulations import _stdlib_collectors as collectors


class _FakeFile:
    """A minimal, real context manager for mocking `open()` reads in tests."""

    def __init__(self, content: str) -> None:
        self._content = content

    def __enter__(self) -> "_FakeFile":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> str:
        return self._content


def test_collect_system_information_reports_platform_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(collectors.platform, "system", lambda: "Linux")
    monkeypatch.setattr(collectors.platform, "release", lambda: "6.8.0")
    monkeypatch.setattr(collectors.platform, "machine", lambda: "x86_64")

    result = collectors.collect_system_information()

    assert result == {"os": "Linux", "release": "6.8.0", "architecture": "x86_64"}


def test_collect_process_information_counts_and_samples_process_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pids = ["1", "2", "not-a-pid", "3"]
    comm_by_pid = {"1": "bash\n", "2": "sshd\n", "3": "cron\n"}

    def _fake_listdir(path: str) -> list[str]:
        assert path == "/proc"
        return pids

    def _fake_open(path: str, encoding: str = "utf-8") -> _FakeFile:
        pid = path.split("/")[2]
        return _FakeFile(comm_by_pid[pid])

    monkeypatch.setattr(collectors.os, "listdir", _fake_listdir)
    monkeypatch.setattr(collectors, "open", _fake_open, raising=False)

    result = collectors.collect_process_information()

    assert result["process_count"] == "3"
    assert "bash" in result["sample_process_names"]
    assert "sshd" in result["sample_process_names"]
    assert "cron" in result["sample_process_names"]


def test_collect_process_information_bounds_the_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pids = [str(pid) for pid in range(1, 21)]

    def _fake_listdir(path: str) -> list[str]:
        return pids

    def _fake_open(path: str, encoding: str = "utf-8") -> _FakeFile:
        pid = path.split("/")[2]
        return _FakeFile(f"proc{pid}\n")

    monkeypatch.setattr(collectors.os, "listdir", _fake_listdir)
    monkeypatch.setattr(collectors, "open", _fake_open, raising=False)

    result = collectors.collect_process_information()

    assert result["process_count"] == "20"
    assert len(result["sample_process_names"].split(", ")) == collectors._MAX_SAMPLE_ITEMS


def test_collect_process_information_handles_unreadable_proc_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(path: str) -> list[str]:
        raise OSError("no such directory")

    monkeypatch.setattr(collectors.os, "listdir", _raise)

    result = collectors.collect_process_information()

    assert result == {"process_count": "0", "sample_process_names": "none"}


def test_collect_account_information_reports_current_user_and_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_entries = [SimpleNamespace(pw_name=name) for name in ("root", "alice", "bob")]
    fake_pwd = SimpleNamespace(getpwall=lambda: fake_entries)

    monkeypatch.setattr(collectors, "pwd", fake_pwd)
    monkeypatch.setattr(collectors.os, "environ", {"USER": "alice"})

    result = collectors.collect_account_information()

    assert result["current_user"] == "alice"
    assert result["local_account_count"] == "3"
    assert "alice" in result["sample_local_accounts"]


def test_collect_account_information_never_touches_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The result must never contain password/hash-shaped data."""
    fake_entries = [SimpleNamespace(pw_name="root")]
    fake_pwd = SimpleNamespace(getpwall=lambda: fake_entries)

    monkeypatch.setattr(collectors, "pwd", fake_pwd)
    monkeypatch.setattr(collectors.os, "environ", {"USER": "root"})

    result = collectors.collect_account_information()

    assert "password" not in result
    assert "hash" not in result
    assert set(result) == {"current_user", "local_account_count", "sample_local_accounts"}


def test_collect_account_information_degrades_gracefully_without_pwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(collectors, "pwd", None)
    monkeypatch.setattr(collectors.os, "environ", {})

    result = collectors.collect_account_information()

    assert result == {
        "current_user": "unknown",
        "local_account_count": "0",
        "sample_local_accounts": "none",
    }


def test_collect_network_configuration_reports_hostname_ip_and_interfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(collectors.socket, "gethostname", lambda: "lab-target")
    monkeypatch.setattr(collectors.socket, "gethostbyname", lambda host: "172.17.0.2")
    monkeypatch.setattr(collectors.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(collectors.os, "listdir", lambda path: ["eth0", "lo"])

    result = collectors.collect_network_configuration()

    assert result["hostname"] == "lab-target"
    assert result["local_ip"] == "172.17.0.2"
    assert result["interface_count"] == "2"
    assert "eth0" in result["sample_interfaces"]


def test_collect_network_configuration_does_not_require_external_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A DNS/resolution failure degrades gracefully instead of raising."""
    monkeypatch.setattr(collectors.socket, "gethostname", lambda: "lab-target")

    def _raise(host: str) -> str:
        raise OSError("name resolution failed")

    monkeypatch.setattr(collectors.socket, "gethostbyname", _raise)
    monkeypatch.setattr(collectors.os.path, "isdir", lambda path: False)

    result = collectors.collect_network_configuration()

    assert result["local_ip"] == "unknown"
    assert result["interface_count"] == "0"
