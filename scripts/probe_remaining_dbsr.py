"""Probe remaining Tokyo municipalities for DBSR council record portals."""

from __future__ import annotations

import re

import requests

CANDIDATES = [
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
    ("mizuho-town", "mizuho"),
    ("hinode-town", "hinode"),
    ("hinohara-village", "hinohara"),
    ("okutama-town", "okutama"),
    ("oshima-town", "oshima"),
    ("toshima-village", "toshima"),
    ("niijima-village", "niijima"),
    ("kozushima-village", "kozushima"),
    ("miyake-village", "miyake"),
    ("mikurajima-village", "mikurajima"),
    ("hachijo-town", "hachijo"),
    ("aogashima-village", "aogashima"),
    ("ogasawara-village", "ogasawara"),
]


def probe(assembly_id: str, slug: str) -> None:
    patterns = [
        f"https://www.city.{slug}.tokyo.dbsr.jp/index.php/",
        f"https://www.town.{slug}.tokyo.jp.dbsr.jp/index.php/",
        f"https://www.village.{slug}.tokyo.jp.dbsr.jp/index.php/",
        f"https://www.city.{slug}.lg.jp/dbsr/index.php/",
    ]
    for url in patterns:
        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        links = re.findall(r'href="([^"]+)"', response.text)
        docs = [
            link
            for link in links
            if "Template=document" in link or re.search(r"[?&]Id=\d+", link)
        ]
        if docs or "dbsr" in response.text.lower():
            print(f"{assembly_id}\tOK\t{url}\t{len(docs)} docs")
            return
    print(f"{assembly_id}\tNO")


def main() -> None:
    for assembly_id, slug in CANDIDATES:
        probe(assembly_id, slug)


if __name__ == "__main__":
    main()
