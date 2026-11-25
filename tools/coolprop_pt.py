"""Writes coolprop-pt.json: saturation pressure (psia) every 5 °F for the refrigerants whose open-data rows are
computed with CoolProp (MIT licence) instead of being copied from a published table.

Run by hand when the list or the ranges change (needs `pip install CoolProp`):  python3 tools/coolprop_pt.py
The build itself only reads the JSON file, so it needs no CoolProp. Ranges are the chart ranges in build.PT.
"""
import json
import sys
from pathlib import Path

import CoolProp
from CoolProp.CoolProp import PropsSI

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import build as b  # noqa: E402

FLUIDS = {"R-290": "n-Propane", "R-600a": "IsoButane", "R-744": "CarbonDioxide", "R-717": "Ammonia", "R-12": "R12"}
PA_PER_PSI = 6894.757

out = {"coolprop_version": CoolProp.__version__, "fluids": FLUIDS, "psia": {}}
for rid, fluid in FLUIDS.items():
    bub = b.PT[rid]["bubble"]
    out["psia"][rid] = {
        str(bub["startF"] + 5 * i): round(PropsSI("P", "T", (bub["startF"] + 5 * i - 32) * 5 / 9 + 273.15, "Q", 0, fluid) / PA_PER_PSI, 3)
        for i in range(len(bub["psig"]))}
(HERE / "coolprop-pt.json").write_text(json.dumps(out, indent=1) + "\n")
print("coolprop-pt.json:", {k: len(v) for k, v in out["psia"].items()})
