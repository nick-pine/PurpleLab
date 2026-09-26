# PurpleLab

A local adversary-emulation and detection-validation platform.

PurpleLab safely reproduces selected adversary behaviors inside systems you
own and control, collects the resulting telemetry, and determines whether
defensive security tooling detected those behaviors.

> **Status:** Early development 

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
```

## Testing

```powershell
pytest
```
