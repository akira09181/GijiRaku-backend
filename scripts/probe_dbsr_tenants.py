"""Probe Tokyo municipalities for DBSR council record portals."""

from __future__ import annotations

import re

import requests

CANDIDATES = [
    ("koto-ward", "koto"),
    ("mitaka-city", "mitaka"),
    ("musashino-city", "musashino"),
    ("fuchu-city", "fuchu"),
    ("kokubunji-city", "kokubunji"),
    ("chiyoda-ward", "chiyoda"),
    ("bunkyo-ward", "bunkyo"),
    ("koganei-city", "koganei"),
    ("hino-city", "hino"),
    ("tama-city", "tama"),
]


def main() -> None:
    for assembly_id, slug in CANDIDATES:
        index_url = f"https://www.city.{slug}.tokyo.dbsr.jp/index.php/"
        response = requests.get(index_url, timeout=20)
        if response.status_code != 200:
            print(f"{assembly_id}\tNO_INDEX\t{response.status_code}")
            continue
        links = re.findall(r'href="([^"]+)"', response.text)
        docs = [
            link
            for link in links
            if "Template=document" in link or re.search(r"[?&]Id=\d+", link)
        ]
        print(f"{assembly_id}\tOK\t{index_url}\t{len(docs)} doc links")
        for link in docs[:2]:
            if link.startswith("/"):
                link = f"https://www.city.{slug}.tokyo.dbsr.jp{link}"
            elif not link.startswith("http"):
                link = index_url + link.lstrip("/")
            print(f"  sample: {link[:120]}")


if __name__ == "__main__":
    main()
