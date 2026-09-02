"""Scan planned Tokyo assemblies for SSP tenant.js availability."""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
PLANNED = [
    "chiyoda-ward", "chuo-ward", "minato-ward", "bunkyo-ward", "taito-ward",
    "sumida-ward", "koto-ward", "meguro-ward", "ota-ward", "setagaya-ward",
    "nakano-ward", "suginami-ward", "toshima-ward", "kita-ward", "itabashi-ward",
    "nerima-ward", "adachi-ward", "katsushika-ward", "edogawa-ward",
    "tachikawa-city", "musashino-city", "mitaka-city", "ome-city", "fuchu-city",
    "akishima-city", "chofu-city", "koganei-city", "kodaira-city", "hino-city",
    "higashimurayama-city", "kokubunji-city", "kunitachi-city", "fussa-city",
    "komae-city", "higashiyamato-city", "kiyose-city", "higashikurume-city",
    "musashimurayama-city", "tama-city", "inagi-city", "hamura-city",
    "akiruno-city", "nishitokyo-city",
]
READY = {
    "tokyo-metropolitan", "shinjuku-ward", "machida-city", "shinagawa-ward",
    "shibuya-ward", "arakawa-ward", "hachioji-city", "nerima-ward",
    "nakano-ward", "kita-ward", "sumida-ward", "tachikawa-city",
    "chuo-ward", "kodaira-city", "akishima-city", "ome-city",
    "higashiyamato-city", "kiyose-city", "musashimurayama-city",
}


def tenant_slug(assembly_id: str) -> str:
    return assembly_id.removesuffix("-ward").removesuffix("-city").removesuffix("-town").removesuffix("-village")


def main() -> None:
    records = load_json(ROOT / "data" / "assembly_records.json")
    existing = set(records["assemblies"])
    found = []
    for assembly_id in PLANNED:
        if assembly_id in READY:
            continue
        tenant = tenant_slug(assembly_id)
        response = requests.get(
            f"https://ssp.kaigiroku.net/tenant/{tenant}/js/tenant.js",
            timeout=12,
        )
        if response.status_code != 200:
            continue
        match = re.search(r"tenant_id\s*=\s*(\d+)", response.text)
        if not match:
            continue
        found.append((assembly_id, tenant, int(match.group(1))))
    for assembly_id, tenant, tenant_id in sorted(found, key=lambda item: item[0]):
        print(f"{assembly_id}\t{tenant}\t{tenant_id}")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


if __name__ == "__main__":
    main()
