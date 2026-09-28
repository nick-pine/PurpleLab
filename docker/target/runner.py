"""Fixed, constrained simulation runner executed inside the PurpleLab lab
container.

Only known PurpleLab technique IDs are accepted. This script never
executes an arbitrary command supplied by a caller -- it looks up the
technique ID in a fixed table of known collection functions.
"""

from __future__ import annotations

import json
import platform
import sys


def _t1082() -> dict[str, str]:
    """Collect basic OS/kernel/architecture info from inside this container."""
    return {
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }


_SIMULATIONS = {
    "T1082": _t1082,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: runner.py <TECHNIQUE_ID>", file=sys.stderr)
        return 2

    technique_id = argv[0].upper()
    collect = _SIMULATIONS.get(technique_id)
    if collect is None:
        print(f"Unknown PurpleLab simulation: {technique_id}", file=sys.stderr)
        return 3

    print(json.dumps(collect()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
