"""Resolve SSP tenant_id from a tenant slug using the councils/index endpoint."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
KNOWN_TENANTS: dict[str, int] = {
    "shinjuku": 211,
    "shibuya": 394,
    "arakawa": 577,
}


def resolve_tenant_id(tenant: str) -> int | None:
    response = requests.get(
        f"https://ssp.kaigiroku.net/tenant/{tenant}/js/tenant.js",
        timeout=20,
    )
    if response.status_code != 200:
        return None
    match = re.search(r"tenant_id\s*=\s*(\d+)", response.text)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tenants", nargs="+", help="SSP tenant slug(s), e.g. nerima edogawa")
    args = parser.parse_args()
    results = {}
    for tenant in args.tenants:
        tenant_id = resolve_tenant_id(tenant)
        results[tenant] = tenant_id
        print(f"{tenant}: {tenant_id if tenant_id is not None else 'NOT_FOUND'}")
    return 0 if all(value is not None for value in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
