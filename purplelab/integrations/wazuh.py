"""Wazuh telemetry provider.

Wazuh version/API assumption: Wazuh 4.x. Alerts are retrieved from the Wazuh
**indexer** (an OpenSearch-compatible search API over the `wazuh-alerts-*`
index pattern) -- NOT the separate Wazuh manager/server REST API on port
55000. The manager API manages agents/rules/cluster state (JWT-based auth
via `POST /security/user/authenticate`) and has no general alert-search
endpoint; alert data is indexed for search in the indexer layer, which is
the officially documented component for this purpose. This module only
implements that one, deliberately chosen path.

Authentication uses HTTP Basic Auth against the indexer's `_search` API,
matching OpenSearch's standard security model.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass

import httpx

from purplelab.telemetry import (
    MAX_EVENTS_RETURNED,
    TelemetryAuthenticationError,
    TelemetryEvent,
    TelemetryMalformedResponseError,
    TelemetryProviderError,
    TelemetryQuery,
    TelemetryUnavailableError,
)

DEFAULT_INDEX_PATTERN = "wazuh-alerts-*"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class WazuhConfig:
    """Connection settings for the Wazuh indexer, sourced from the environment.

    PurpleLab never hardcodes or commits real Wazuh credentials -- these
    values must come from the environment (see `.env.example`).
    """

    base_url: str
    username: str
    password: str
    verify_tls: bool = True
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    index_pattern: str = DEFAULT_INDEX_PATTERN

    @classmethod
    def from_env(cls) -> "WazuhConfig":
        """Build configuration strictly from environment variables."""
        base_url = os.environ.get("PURPLELAB_WAZUH_URL")
        username = os.environ.get("PURPLELAB_WAZUH_USERNAME")
        password = os.environ.get("PURPLELAB_WAZUH_PASSWORD")

        if not base_url or not username or not password:
            raise TelemetryProviderError(
                "Wazuh is not configured. Set PURPLELAB_WAZUH_URL, "
                "PURPLELAB_WAZUH_USERNAME, and PURPLELAB_WAZUH_PASSWORD."
            )

        verify_tls = os.environ.get("PURPLELAB_WAZUH_VERIFY_TLS", "true").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        if not verify_tls:
            warnings.warn(
                "PURPLELAB_WAZUH_VERIFY_TLS is disabled -- TLS certificate verification "
                "is OFF. Only use this for local development against self-signed labs.",
                stacklevel=2,
            )

        timeout_raw = os.environ.get("PURPLELAB_WAZUH_TIMEOUT_SECONDS")
        timeout_seconds = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT_SECONDS
        index_pattern = os.environ.get("PURPLELAB_WAZUH_INDEX_PATTERN", DEFAULT_INDEX_PATTERN)

        return cls(
            base_url=base_url.rstrip("/"),
            username=username,
            password=password,
            verify_tls=verify_tls,
            timeout_seconds=timeout_seconds,
            index_pattern=index_pattern,
        )


class WazuhTelemetryProvider:
    """Retrieves bounded alert evidence from the Wazuh indexer for one execution."""

    def __init__(self, config: WazuhConfig) -> None:
        self._config = config

    def collect(self, query: TelemetryQuery) -> tuple[TelemetryEvent, ...]:
        """Query the indexer for alerts within `query`'s bounded, padded window."""
        body = self._build_search_body(query)
        url = f"{self._config.base_url}/{self._config.index_pattern}/_search"

        try:
            response = httpx.post(
                url,
                json=body,
                auth=(self._config.username, self._config.password),
                timeout=self._config.timeout_seconds,
                verify=self._config.verify_tls,
            )
        except httpx.TimeoutException as error:
            raise TelemetryUnavailableError(
                "Timed out while querying the Wazuh indexer."
            ) from error
        except httpx.RequestError as error:
            raise TelemetryUnavailableError("Could not reach the Wazuh indexer.") from error

        if response.status_code in (401, 403):
            raise TelemetryAuthenticationError(
                "The Wazuh indexer rejected PurpleLab's credentials."
            )
        if response.status_code >= 400:
            raise TelemetryProviderError(
                f"The Wazuh indexer returned an unexpected error (HTTP {response.status_code})."
            )

        return self._parse_response(response)

    def _build_search_body(self, query: TelemetryQuery) -> dict[str, object]:
        """Construct a fixed, bounded query body -- never derived from user input."""
        must: list[dict[str, object]] = [
            {
                "range": {
                    "@timestamp": {
                        "gte": query.padded_start.isoformat(),
                        "lte": query.padded_end.isoformat(),
                    }
                }
            }
        ]
        if query.agent_identity:
            must.append({"term": {"agent.name": query.agent_identity}})

        return {
            "size": MAX_EVENTS_RETURNED,
            "sort": [{"@timestamp": "asc"}],
            "query": {"bool": {"must": must}},
        }

    def _parse_response(self, response: httpx.Response) -> tuple[TelemetryEvent, ...]:
        try:
            payload = response.json()
            hits = payload["hits"]["hits"]
        except (ValueError, KeyError, TypeError) as error:
            raise TelemetryMalformedResponseError(
                "The Wazuh indexer returned an unexpected response structure."
            ) from error

        if not isinstance(hits, list):
            raise TelemetryMalformedResponseError(
                "The Wazuh indexer returned an unexpected response structure."
            )

        events = []
        for hit in hits[:MAX_EVENTS_RETURNED]:
            try:
                events.append(self._to_telemetry_event(hit))
            except (KeyError, TypeError, ValueError) as error:
                raise TelemetryMalformedResponseError(
                    "A Wazuh alert document had an unexpected shape."
                ) from error

        return tuple(events)

    def _to_telemetry_event(self, hit: dict[str, object]) -> TelemetryEvent:
        source = hit["_source"]
        if not isinstance(source, dict):
            raise TypeError("hit._source must be an object")

        rule = source.get("rule") or {}
        agent = source.get("agent") or {}

        return TelemetryEvent(
            provider="wazuh",
            observed_at=source["@timestamp"],
            source=str(agent.get("name") or agent.get("id") or "unknown"),
            event_id=str(hit["_id"]) if hit.get("_id") is not None else None,
            rule_id=str(rule.get("id")) if rule.get("id") is not None else None,
            rule_description=rule.get("description"),
            severity=rule.get("level"),
            summary=str(source.get("full_log") or rule.get("description") or ""),
        )
