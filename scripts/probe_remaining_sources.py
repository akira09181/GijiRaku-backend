"""Probe remaining municipalities for SSP, DBSR, and alternate council portals."""

from __future__ import annotations

import re

import requests

REMAINING = [
    ("minato-ward", "minato"),
    ("taito-ward", "taito"),
    ("meguro-ward", "meguro"),
    ("ota-ward", "ota"),
    ("setagaya-ward", "setagaya"),
    ("suginami-ward", "suginami"),
    ("toshima-ward", "toshima"),
    ("itabashi-ward", "itabashi"),
    ("adachi-ward", "adachi"),
    ("katsushika-ward", "katsushika"),
    ("edogawa-ward", "edogawa"),
    ("chofu-city", "chofu"),
    ("higashimurayama-city", "higashimurayama"),
]


def probe(assembly_id: str, slug: str) -> None:
    ssp = requests.get(
        f"https://ssp.kaigiroku.net/tenant/{slug}/js/tenant.js",
        timeout=12,
    )
    if ssp.status_code == 200:
        match = re.search(r"tenant_id\s*=\s*(\d+)", ssp.text)
        if match:
            print(f"{assembly_id}\tSSP\t{match.group(1)}")
            return

    urls = [
        f"https://www.city.{slug}.tokyo.dbsr.jp/index.php/",
        f"https://gikai.city.{slug}.tokyo.jp/",
        f"https://www.gikai-{slug}.jp/",
        f"https://kugi.city.{slug}.tokyo.jp/",
        f"https://www.city.{slug}.lg.jp/shigikai/index.html",
        f"https://www.city.{slug}.tokyo.jp/shigikai/index.html",
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=12)
        except requests.RequestException:
            continue
        if response.status_code != 200 or len(response.text) < 500:
            continue
        hints = []
        lowered = response.text.lower()
        if "dbsr" in lowered:
            hints.append("dbsr")
        if "kaigiroku" in lowered:
            hints.append("kaigiroku")
        if "議会" in response.text or "会議録" in response.text:
            hints.append("gikai")
        if hints:
            print(f"{assembly_id}\tALT\t{url}\t{'/'.join(hints)}")
            return
    print(f"{assembly_id}\tNONE")


def main() -> None:
    for assembly_id, slug in REMAINING:
        probe(assembly_id, slug)


if __name__ == "__main__":
    main()
