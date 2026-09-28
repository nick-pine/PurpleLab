"""Fixed, constrained simulation runner executed inside the PurpleLab lab
container.

Only known PurpleLab technique IDs are accepted. This script never
executes an arbitrary command supplied by a caller -- it looks up the
technique ID in a fixed table of known collection functions, which live in
`_stdlib_collectors.py` (the same module the host-side simulations use, so
container and local behavior cannot drift apart).
"""

from __future__ import annotations

import json
import sys

try:
    # Inside the built image, this file sits next to runner.py (flat layout).
    from _stdlib_collectors import (
        collect_account_information,
        collect_network_configuration,
        collect_process_information,
        collect_system_information,
    )
except ImportError:  # pragma: no cover - fallback when tested from the repo root
    from simulations._stdlib_collectors import (
        collect_account_information,
        collect_network_configuration,
        collect_process_information,
        collect_system_information,
    )

_SIMULATIONS = {
    "T1082": collect_system_information,
    "T1057": collect_process_information,
    "T1087": collect_account_information,
    "T1016": collect_network_configuration,
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

