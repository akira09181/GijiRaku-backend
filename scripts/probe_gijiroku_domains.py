"""Probe gijiroku.com and gikai subdomain patterns."""

from __future__ import annotations

import requests

CHECKS = [
    ("taito-ward", "https://taito.gijiroku.com/voices/"),
    ("meguro-ward", "https://meguro.gijiroku.com/voices/"),
    ("ota-ward", "https://ota.gijiroku.com/voices/"),
    ("suginami-ward", "https://suginami.gijiroku.com/voices/"),
    ("toshima-ward", "https://toshima.gijiroku.com/voices/"),
    ("itabashi-ward", "https://itabashi.gijiroku.com/voices/"),
    ("katsushika-ward", "https://katsushika.gijiroku.com/voices/"),
    ("edogawa-ward", "https://www.gikai.city.edogawa.tokyo.jp/voices/"),
    ("higashimurayama-city", "https://higashimurayama.gijiroku.com/voices/"),
    ("higashimurayama-city-alt", "https://higashimurayamacity.gijiroku.com/voices/"),
]


def main() -> None:
    for assembly_id, url in CHECKS:
        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
        except requests.RequestException as error:
            print(f"{assembly_id}\tERR\t{error}")
            continue
        ok = response.status_code == 200 and (
            "会議録" in response.text or "議会" in response.text
        )
        print(f"{assembly_id}\t{response.status_code}\t{response.url[:80]}\t{'OK' if ok else 'NO'}")


if __name__ == "__main__":
    main()
