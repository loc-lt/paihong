#!/usr/bin/env python3
"""Complete part workflow steps through BUILD_GRID (ready for step 10)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwMjcxNjI1LCJpYXQiOjE3OTAyNjgwMjUs"
    "Imp0aSI6Ijc1NWFkZTk1MDhjZjQ2MjdiNDYyYjk2ZDdiNTAzMGI1IiwidXNlcl9pZCI6IjU0ZmRk"
    "MGZkLWI5MDAtNDdmMi1iZjQ3LTU1N2RlODgxYTRkNyIsInRva2VuX3ZlcnNpb24iOiJjYzJkNzIz"
    "ZC03NDM0LTQzMDctYmU5ZC00MzFlYTM2YzFiZmYifQ."
    "pw5f2OGCA9mw-oIMgx2RvNduPY_ajscwd6XVTQx-1DY"
)
BASE = "http://localhost:82/api/v1"
PART_ID = sys.argv[1] if len(sys.argv) > 1 else "c31c8d85-c3a5-48ba-b821-557e7b910a48"

STEPS = [
    ("PICK_UPPER", {"selected_candidate_index": 0, "rotation": 0, "candidates": []}),
    ("ROTATE_STRIP_TEXT", {}),
    ("REMOVE_AUX_LINES", {}),
    (
        "FIX_LINES_BY_ANCHOR",
        {"anchors": [{"x": 0, "y": 0}], "snap_distance": 1, "tolerance": 1},
    ),
    ("CHECK_COLORS", {"layers": {}, "frame_expansion_mm": 0}),
    (
        "CANVAS_FRAME_MEASURE",
        {
            "canvas": {"width_mm": 220, "height_mm": 160},
            "origin": {"x": 0, "y": 0},
            "scale": 1,
        },
    ),
    (
        "ENTER_SPECS",
        {
            "needle_density": 10,
            "cos_number": 10,
            "course_per_pixel": 1,
            "grid_pixels": {"width": 220, "height": 160},
        },
    ),
    ("BUILD_GRID", {"grid": {"width": 220, "height": 160}}),
]


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        raise SystemExit(f"{method} {path} -> HTTP {exc.code}: {payload}") from exc


def main() -> None:
    for code, settings in STEPS:
        print(f"Completing {code}...")
        result = api(
            "POST",
            f"/parts/{PART_ID}/steps/{code}/complete",
            {"settings": settings},
        )
        if not result.get("status"):
            raise SystemExit(json.dumps(result, indent=2))
        data = result.get("data") or {}
        rev = data.get("revision") or data
        print(f"  OK revision={rev.get('id')}")
        ns = data.get("next_step_settings")
        if ns:
            print(f"  next_step={ns.get('step_code')}")

    summary = api("GET", f"/parts/{PART_ID}/steps")
    steps = summary["data"]["steps"]
    print("\nStep status:")
    for step in steps:
        print(
            f"  {step['step']['sequence']:2} {step['step']['code']:22} status={step['status']}"
        )
    print(
        f"\nCompleted {summary['data']['completed_steps']}/{summary['data']['total_steps']}"
    )

    ws = api("GET", f"/parts/{PART_ID}/steps/START_DESIGNING/workspace")
    files = ws["data"]["files"]
    print(f"\nWorkspace product_code={ws['data'].get('product_code')}")
    print(f"Design files ({len(files)}):")
    for f in files:
        print(f"  {f['file_type']:4} {f.get('display_name')}")


if __name__ == "__main__":
    main()
