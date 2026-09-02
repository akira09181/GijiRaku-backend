"""Probe known alternate council record domains for remaining municipalities."""

from __future__ import annotations

import requests

CHECKS = [
    ("minato-ward", "https://gikai2.city.minato.tokyo.jp/voices/index.asp"),
    ("taito-ward", "https://gikai2.city.taito.lg.jp/voices/index.asp"),
    ("meguro-ward", "https://gikai2.city.meguro.tokyo.jp/voices/index.asp"),
    ("ota-ward", "https://gikai2.city.ota.tokyo.jp/voices/index.asp"),
    ("setagaya-ward", "https://kugi.city.setagaya.tokyo.jp/"),
    ("suginami-ward", "https://gikai2.city.suginami.tokyo.jp/voices/index.asp"),
    ("toshima-ward", "https://gikai2.city.toshima.lg.jp/voices/index.asp"),
    ("itabashi-ward", "https://gikai2.city.itabashi.tokyo.jp/voices/index.asp"),
    ("adachi-ward", "https://www.gikai-adachi.jp/"),
    ("katsushika-ward", "https://gikai2.city.katsushika.lg.jp/voices/index.asp"),
    ("edogawa-ward", "https://gikai2.city.edogawa.tokyo.jp/voices/index.asp"),
    ("chofu-city", "https://chofucity.gijiroku.com/voices/"),
    ("higashimurayama-city", "https://higashimurayamacity.gijiroku.com/voices/"),
    ("higashimurayama-city-alt", "https://www.city.higashimurayama.tokyo.jp/shigikai/kaigiroku/index.html"),
]


def main() -> None:
    for assembly_id, url in CHECKS:
        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
        except requests.RequestException as error:
            print(f"{assembly_id}\tERR\t{error}")
            continue
        text = response.text
        hints = [str(response.status_code)]
        if "会議録" in text or "議会" in text:
            hints.append("gikai")
        if "kaigiroku" in text.lower() or "gijiroku" in text.lower():
            hints.append("records")
        print(f"{assembly_id}\t{response.url[:90]}\t{'/'.join(hints)}")


if __name__ == "__main__":
    main()
