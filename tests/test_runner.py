"""Tests for the container-side runner's fixed dispatch table (Milestone 6).

These import `docker/target/runner.py` directly by file path -- no Docker
daemon is required.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

RUNNER_PATH = (
    Path(__file__).resolve().parent.parent / "docker" / "target" / "runner.py"
)


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("purplelab_lab_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dispatch_table_supports_exactly_the_known_techniques() -> None:
    """The container only ever knows how to run these four fixed simulations."""
    runner = _load_runner()

    assert set(runner._SIMULATIONS) == {"T1082", "T1057", "T1087", "T1016"}


def test_unknown_technique_id_is_rejected() -> None:
    """An unrecognized technique ID is refused with a non-zero exit code."""
    runner = _load_runner()

    exit_code = runner.main(["T9999"])

    assert exit_code == 3


def test_missing_argument_is_rejected() -> None:
    """Calling the runner with no technique ID argument is refused."""
    runner = _load_runner()

    exit_code = runner.main([])

    assert exit_code == 2


def test_known_technique_prints_json_compatible_result() -> None:
    """A known technique ID prints a single JSON object to stdout."""
    runner = _load_runner()

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = runner.main(["T1082"])

    assert exit_code == 0
    data = json.loads(stdout.getvalue())
    assert isinstance(data, dict)
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in data.items())
