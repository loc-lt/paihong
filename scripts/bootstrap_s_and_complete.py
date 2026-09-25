#!/usr/bin/env python3
"""Backfill file S revision (GET workspace) then complete S for a part."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwMzEwNjEzLCJpYXQiOjE3OTAzMDcwMTMs"
    "Imp0aSI6ImNhZjRiMDhlMzljZDRlZjI4MGFlMDk0ODAxNmU1NjZiIiwidXNlcl9pZCI6IjU0ZmRk"
    "MGZkLWI5MDAtNDdmMi1iZjQ3LTU1N2RlODgxYTRkNyIsInRva2VuX3ZlcnNpb24iOiJjYzJkNzIz"
    "ZC03NDM0LTQzMDctYmU5ZC00MzFlYTM2YzFiZmYifQ."
    "UHzPE4CxpVEmjU4_87YVBtxplYn1HlaSAzReDyvEs5Q"
)
BASE = "http://localhost:82/api/v1"
PART_ID = sys.argv[1] if len(sys.argv) > 1 else "c31c8d85-c3a5-48ba-b821-557e7b910a48"


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
    ws = api("GET", f"/parts/{PART_ID}/steps/START_DESIGNING/workspace")
    files = {f["file_type"]: f for f in ws["data"]["files"]}
    s = files.get("S") or {}
    print(f"S latest_revision before: {s.get('latest_revision')}")
    print(f"progress: {ws['data']['settings'].get('progress')}")

    if not s.get("latest_revision"):
        raise SystemExit(
            "S still has no revision — restart revision service with latest code, then retry."
        )

    result = api(
        "POST",
        f"/parts/{PART_ID}/steps/START_DESIGNING/files/S/complete",
    )
    print(json.dumps(result, indent=2))

    ws2 = api("GET", f"/parts/{PART_ID}/steps/START_DESIGNING/workspace")
    print(f"\nprogress after: {ws2['data']['settings'].get('progress')}")


if __name__ == "__main__":
    main()
