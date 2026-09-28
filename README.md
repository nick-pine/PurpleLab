# PurpleLab

A local adversary-emulation and detection-validation platform.

PurpleLab safely reproduces selected adversary behaviors inside systems you
own and control, collects the resulting telemetry, and determines whether
defensive security tooling detected those behaviors.

> **Status:** Early development WIP

## Installation (development)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Usage

```powershell
purplelab --version
purplelab list
purplelab info T1082
purplelab run T1082 --target local
```

## Built-in simulations

PurpleLab currently ships four intentionally low-risk, read-only Discovery
simulations. Each executes only locally or inside the controlled Docker lab
(never against arbitrary or remote systems):

| Technique | Name                                       | Notes |
|-----------|---------------------------------------------|-------|
| T1082     | System Information Discovery                 | OS, kernel release, architecture |
| T1057     | Process Discovery                             | Bounded, read-only process names via `/proc` -- never terminates/inspects/injects |
| T1087     | Account Discovery                             | Current user + local account names -- never passwords, hashes, or `/etc/shadow` |
| T1016     | System Network Configuration Discovery        | The target's own hostname/IP/interfaces -- never scans or contacts other hosts |

All four are Linux-only for now; the Docker lab is PurpleLab's controlled
Linux execution environment.

## Docker lab

These simulations are declared Linux-only, so `--target local` fails on a
non-Linux development host (e.g. Windows) by design. The Docker lab provides
an isolated Linux target so simulations can actually execute end to end.

Requirements: Docker Desktop (or another Docker engine) installed and running.

```powershell
purplelab lab build          # build the PurpleLab lab image (one-time / after changes)
purplelab lab status         # check Docker + lab image readiness
purplelab run T1082 --target docker
```

`--target local` runs the simulation directly in the current Python process.
`--target docker` runs it inside a disposable, isolated Linux container built
from `docker/target/` (using the shared, stdlib-only collectors in
`simulations/_stdlib_collectors.py`, so container and local behavior cannot
drift apart). Each run:

- passes only the simulation's known technique ID to the container (never an
  arbitrary command)
- runs with no published ports, no host mounts, no host networking, no
  privileged mode, dropped Linux capabilities, a read-only filesystem, and
  `no-new-privileges`
- is removed automatically (`--rm`) after producing its result
- has a fixed internal timeout so a stuck container cannot hang PurpleLab

> **Note:** Docker has not been installed on the primary development
> machine used to build this project, so real Docker execution has been
> verified only through mocked unit/CLI tests, not a live integration run.

## Wazuh telemetry

PurpleLab can optionally query Wazuh for telemetry observed during a
simulation's execution window:

```powershell
purplelab run T1082 --target docker --telemetry
```

Important distinctions:

- **Expected telemetry** (`purplelab info <TECHNIQUE>`) is metadata describing
  what a simulation is conceptually expected to produce. It is never
  confirmed evidence.
- **Observed telemetry** (`--telemetry`) is real evidence retrieved from
  Wazuh for one specific execution. PurpleLab never overwrites one with the
  other.

How it works: each execution gets a unique `execution_id`, and a bounded
telemetry query is built from that execution's start/finish timestamps (plus
a few seconds of padding) -- never an open-ended historical query. Alerts are
retrieved from the **Wazuh indexer** (its OpenSearch-compatible `_search` API
over the `wazuh-alerts-*` index), not the separate Wazuh manager/server API,
which manages agents/rules rather than searching alert data. Results are
capped at 50 events and mapped into PurpleLab's own bounded `TelemetryEvent`
model -- the rest of PurpleLab never sees raw Wazuh JSON.

Configuration (see `.env.example`) is read only from the environment:

```
PURPLELAB_WAZUH_URL=https://localhost:9200
PURPLELAB_WAZUH_USERNAME=admin
PURPLELAB_WAZUH_PASSWORD=changeme
```

TLS certificate verification is **on by default**; disabling it
(`PURPLELAB_WAZUH_VERIFY_TLS=false`) is an explicit opt-in for local
self-signed labs and prints a warning. Real credentials are never committed,
logged, or printed in CLI output.

A "zero events observed" result is always distinguishable from a Wazuh
outage/authentication failure -- the former prints
`No telemetry events observed in the query window.`, the latter prints a
clean, controlled error with a non-zero exit code.

> **Note:** Wazuh has not been installed/tested against a real deployment on
> this development machine. The Wazuh client (`purplelab/integrations/wazuh.py`)
> is fully unit-tested with the HTTP boundary mocked, but end-to-end
> `simulation → Docker → Wazuh → telemetry` integration remains unverified.
> This does not implement detection pass/fail validation -- that is a later
> milestone.

## Testing

```powershell
pytest
```

