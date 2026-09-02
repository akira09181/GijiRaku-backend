"""Probe official city council pages for external record systems."""

from __future__ import annotations

import re

import requests

CHECKS = [
    ("minato-ward", "https://www.city.minato.tokyo.jp/shigikai/"),
    ("taito-ward", "https://www.city.taito.lg.jp/shigikai/"),
    ("meguro-ward", "https://www.city.meguro.lg.jp/shigikai/"),
    ("ota-ward", "https://www.city.ota.tokyo.jp/shigikai/"),
    ("suginami-ward", "https://www.city.suginami.lg.jp/shigikai/"),
    ("toshima-ward", "https://www.city.toshima.lg.jp/shigikai/"),
    ("itabashi-ward", "https://www.city.itabashi.tokyo.jp/shigikai/"),
    ("katsushika-ward", "https://www.city.katsushika.lg.jp/shigikai/"),
    ("edogawa-ward", "https://www.city.edogawa.tokyo.jp/shigikai/"),
    ("chofu-city", "https://www.city.chofu.tokyo.jp/shigikai/"),
    ("higashimurayama-city", "https://www.city.higashimurayama.tokyo.jp/shigikai/"),
]


def main() -> None:
    for assembly_id, url in CHECKS:
        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
        except requests.RequestException as error:
            print(f"{assembly_id}\tERR\t{error}")
            continue
        text = response.text
        lowered = text.lower()
        hints = []
        if response.status_code == 200:
            hints.append("200")
        if "kaigiroku" in lowered:
            hints.append("kaigiroku")
        if "dbsr" in lowered:
            hints.append("dbsr")
        if "会議録" in text:
            hints.append("minutes")
        links = re.findall(r'href="([^"]+)"', text)
        external = [
            link
            for link in links
            if any(token in link for token in ("kaigiroku", "dbsr", "gikai", "kugi"))
        ][:3]
        print(f"{assembly_id}\t{response.status_code}\t{response.url[:80]}\t{'/'.join(hints)}\t{external}")


if __name__ == "__main__":
    main()
