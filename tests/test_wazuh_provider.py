"""Tests for the Wazuh telemetry provider (Milestone 7).

All HTTP interactions are mocked at the `httpx.post` boundary -- these tests
must never make a real network request or require a real Wazuh deployment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from purplelab.integrations.wazuh import WazuhConfig, WazuhTelemetryProvider
from purplelab.telemetry import (
    TelemetryAuthenticationError,
    TelemetryMalformedResponseError,
    TelemetryProviderError,
    TelemetryQuery,
    TelemetryUnavailableError,
)


def _query() -> TelemetryQuery:
    now = datetime.now(timezone.utc)
    return TelemetryQuery(
        execution_id="exec-1",
        simulation_id="t1082-system-information-discovery",
        technique_id="T1082",
        window_start=now,
        window_end=now,
    )


def _config(**overrides: object) -> WazuhConfig:
    base = {
        "base_url": "https://wazuh-indexer.local:9200",
        "username": "purplelab",
        "password": "fake-password-for-tests",
    }
    base.update(overrides)
    return WazuhConfig(**base)  # type: ignore[arg-type]


def _response(status_code: int = 200, json_body: object | None = None) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_body if json_body is not None else {}
    return response


def test_config_from_env_requires_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PURPLELAB_WAZUH_URL", raising=False)
    monkeypatch.delenv("PURPLELAB_WAZUH_USERNAME", raising=False)
    monkeypatch.delenv("PURPLELAB_WAZUH_PASSWORD", raising=False)

    with pytest.raises(TelemetryProviderError):
        WazuhConfig.from_env()


def test_config_from_env_builds_config_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PURPLELAB_WAZUH_URL", "https://wazuh:9200/")
    monkeypatch.setenv("PURPLELAB_WAZUH_USERNAME", "purplelab")
    monkeypatch.setenv("PURPLELAB_WAZUH_PASSWORD", "fake-password-for-tests")

    config = WazuhConfig.from_env()

    assert config.base_url == "https://wazuh:9200"
    assert config.verify_tls is True


def test_config_from_env_warns_when_tls_verification_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PURPLELAB_WAZUH_URL", "https://wazuh:9200")
    monkeypatch.setenv("PURPLELAB_WAZUH_USERNAME", "purplelab")
    monkeypatch.setenv("PURPLELAB_WAZUH_PASSWORD", "fake-password-for-tests")
    monkeypatch.setenv("PURPLELAB_WAZUH_VERIFY_TLS", "false")

    with pytest.warns(UserWarning):
        config = WazuhConfig.from_env()

    assert config.verify_tls is False


def test_collect_builds_request_with_no_shell_and_finite_timeout() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"hits": {"hits": []}})

        provider.collect(_query())

    args, kwargs = mock_post.call_args
    assert kwargs["auth"] == ("purplelab", "fake-password-for-tests")
    assert kwargs["timeout"] > 0
    assert kwargs["verify"] is True
    assert "wazuh-alerts-*" in args[0]


def test_collect_returns_empty_tuple_on_zero_matches() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"hits": {"hits": []}})

        events = provider.collect(_query())

    assert events == ()


def test_collect_returns_events_on_matches() -> None:
    provider = WazuhTelemetryProvider(_config())
    hit = {
        "_id": "abc123",
        "_source": {
            "@timestamp": "2024-01-01T00:00:00.000Z",
            "agent": {"name": "lab-target"},
            "rule": {"id": "5501", "description": "Login session opened", "level": 3},
            "full_log": "Jan 1 00:00:00 lab-target sshd: session opened",
        },
    }

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"hits": {"hits": [hit]}})

        events = provider.collect(_query())

    assert len(events) == 1
    event = events[0]
    assert event.provider == "wazuh"
    assert event.source == "lab-target"
    assert event.rule_id == "5501"
    assert event.severity == 3


def test_collect_raises_on_authentication_failure() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(status_code=401)

        with pytest.raises(TelemetryAuthenticationError):
            provider.collect(_query())


def test_collect_raises_on_generic_http_error() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(status_code=500)

        with pytest.raises(TelemetryProviderError):
            provider.collect(_query())


def test_collect_raises_on_connection_error() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch(
        "purplelab.integrations.wazuh.httpx.post",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(TelemetryUnavailableError):
            provider.collect(_query())


def test_collect_raises_on_timeout() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch(
        "purplelab.integrations.wazuh.httpx.post",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        with pytest.raises(TelemetryUnavailableError):
            provider.collect(_query())


def test_collect_raises_on_malformed_json() -> None:
    provider = WazuhTelemetryProvider(_config())
    response = _response(status_code=200)
    response.json.side_effect = ValueError("not json")

    with patch("purplelab.integrations.wazuh.httpx.post", return_value=response):
        with pytest.raises(TelemetryMalformedResponseError):
            provider.collect(_query())


def test_collect_raises_on_unexpected_response_shape() -> None:
    provider = WazuhTelemetryProvider(_config())

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"unexpected": "shape"})

        with pytest.raises(TelemetryMalformedResponseError):
            provider.collect(_query())


def test_collect_raises_on_malformed_hit() -> None:
    provider = WazuhTelemetryProvider(_config())
    hit = {"_id": "abc", "_source": {"agent": {"name": "lab-target"}}}  # missing @timestamp

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"hits": {"hits": [hit]}})

        with pytest.raises(TelemetryMalformedResponseError):
            provider.collect(_query())


def test_collect_bounds_number_of_returned_events() -> None:
    provider = WazuhTelemetryProvider(_config())
    hit = {
        "_id": "abc",
        "_source": {
            "@timestamp": "2024-01-01T00:00:00.000Z",
            "agent": {"name": "lab-target"},
            "rule": {"id": "1", "description": "test", "level": 1},
        },
    }
    many_hits = [hit] * 200

    with patch("purplelab.integrations.wazuh.httpx.post") as mock_post:
        mock_post.return_value = _response(json_body={"hits": {"hits": many_hits}})

        events = provider.collect(_query())

    assert len(events) <= 50
