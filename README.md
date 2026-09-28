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

## Docker lab

T1082 is declared Linux-only, so `--target local` fails on a non-Linux
development host (e.g. Windows) by design. The Docker lab provides an
isolated Linux target so the simulation can actually execute end to end.

Requirements: Docker Desktop (or another Docker engine) installed and running.

```powershell
purplelab lab build          # build the PurpleLab lab image (one-time / after changes)
purplelab lab status         # check Docker + lab image readiness
purplelab run T1082 --target docker
```

`--target local` runs the simulation directly in the current Python process.
`--target docker` runs it inside a disposable, isolated Linux container built
from `docker/target/`. Each run:

- passes only the simulation's known technique ID to the container (never an
  arbitrary command)
- runs with no published ports, no host mounts, no host networking, no
  privileged mode, dropped Linux capabilities, and `no-new-privileges`
- is removed automatically (`--rm`) after producing its result
- has a fixed internal timeout so a stuck container cannot hang PurpleLab

## Testing

```powershell
pytest
```

