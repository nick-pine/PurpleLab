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

## Testing

```powershell
pytest
```

