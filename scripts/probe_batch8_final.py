"""Probe final 10 municipalities for council record portals."""

from __future__ import annotations

import re

import requests

REMAINING = [
    ("higashimurayama-city", "higashimurayama", "city", [
        "https://www.city.higashimurayama.tokyo.jp/gikai/gikaijoho/kensaku/index.html",
        "https://higashimurayama.gijiroku.com/voices/",
        "https://www.gikai-higashimurayama.jp/",
        "https://www.city.higashimurayama.lg.jp/shigikai/",
    ]),
    ("mizuho-town", "mizuho", "town", [
        "https://www.town.mizuho.tokyo.jp/gikai/",
        "https://www.town.mizuho.tokyo.jp/gikai/kaigiroku/",
    ]),
    ("hinode-town", "hinode", "town", [
        "https://www.town.hinode.tokyo.jp/shigikai/",
        "https://www.town.hinode.tokyo.jp/gikai/",
    ]),
    ("hinohara-village", "hinohara", "village", [
        "https://www.vill.hinohara.tokyo.jp/shigikai/",
        "https://www.vill.hinohara.tokyo.jp/gikai/",
    ]),
    ("toshima-village", "toshima", "village", [
        "https://www.toshimamura.tokyo.jp/shigikai/",
        "https://www.village.toshima.tokyo.jp/shigikai/",
        "https://toshimamura.gijiroku.com/voices/",
    ]),
    ("niijima-village", "niijima", "village", [
        "https://www.niijima.com/gikai/",
        "https://www.vill.niijima.tokyo.jp/shigikai/",
        "https://niijimamura.gijiroku.com/voices/",
    ]),
    ("kozushima-village", "kozushima", "village", [
        "https://www.vill.kozushima.tokyo.jp/shigikai/",
        "https://www.town.kozushima.tokyo.jp/shigikai/",
    ]),
    ("mikurajima-village", "mikurajima", "village", [
        "https://www.vill.mikurajima.tokyo.jp/shigikai/",
        "https://www.vill.mikurajima.tokyo.jp/gikai/",
    ]),
    ("aogashima-village", "aogashima", "village", [
        "https://www.vill.aogashima.tokyo.jp/shigikai/",
        "https://www.vill.aogashima.tokyo.jp/gikai/",
    ]),
    ("ogasawara-village", "ogasawara", "village", [
        "https://www.vill.ogasawara.tokyo.jp/shigikai/",
        "https://www.vill.ogasawara.tokyo.jp/gikai/",
        "https://www.vill.ogasawara.tokyo.jp/shigikai/index.html",
    ]),
]


def main() -> None:
    for assembly_id, slug, kind, urls in REMAINING:
        found = False
        for url in urls:
            try:
                response = requests.get(url, timeout=15, allow_redirects=True)
            except requests.RequestException as error:
                print(f"{assembly_id}\tERR\t{url[:60]}\t{error}")
                continue
            text = response.text
            if response.status_code == 200 and len(text) > 400:
                hints = []
                if "会議録" in text or "議会" in text or "審議" in text:
                    hints.append("gikai")
                if "gijiroku" in text.lower() or "kaigiroku" in text.lower():
                    hints.append("records")
                print(f"{assembly_id}\t{response.status_code}\t{response.url[:90]}\t{'/'.join(hints) or 'page'}")
                found = True
                break
        if not found:
            print(f"{assembly_id}\tNO")


if __name__ == "__main__":
    main()
