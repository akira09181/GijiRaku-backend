"""Inspect SSP tenant pages for embedded tenant_id values."""

from __future__ import annotations

import re
import sys

import requests


def inspect(tenant: str) -> None:
    url = f"https://ssp.kaigiroku.net/tenant/{tenant}/SpTop.html"
    response = requests.get(url, timeout=20)
    print(f"{tenant}: status={response.status_code}")
    if response.status_code != 200:
        return
    for pattern in (
        r"tenant_id['\"]?\s*[:=]\s*(\d+)",
        r"tenantId['\"]?\s*[:=]\s*(\d+)",
        r"tenant_id=(\d+)",
    ):
        matches = re.findall(pattern, response.text)
        if matches:
            print(f"  matches {pattern}: {matches[:5]}")
    scripts = re.findall(r'src="([^"]+)"', response.text)
    for script in scripts:
        if "tenant" in script.lower() or "config" in script.lower():
            print(f"  script: {script}")


if __name__ == "__main__":
    for slug in sys.argv[1:] or ["nerima", "edogawa", "ota", "itabashi"]:
        inspect(slug)
        print()
