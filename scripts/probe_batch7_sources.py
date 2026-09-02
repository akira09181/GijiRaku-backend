"""Probe batch-7 remaining municipalities for council record portals."""

from __future__ import annotations

import re

import requests

REMAINING = [
    ("meguro-ward", "meguro", "ward"),
    ("ota-ward", "ota", "ward"),
    ("toshima-ward", "toshima", "ward"),
    ("katsushika-ward", "katsushika", "ward"),
    ("higashimurayama-city", "higashimurayama", "city"),
    ("mizuho-town", "mizuho", "town"),
    ("hinode-town", "hinode", "town"),
    ("hinohara-village", "hinohara", "village"),
    ("okutama-town", "okutama", "town"),
    ("oshima-town", "oshima", "town"),
    ("toshima-village", "toshima", "village"),
    ("niijima-village", "niijima", "village"),
    ("kozushima-village", "kozushima", "village"),
    ("miyake-village", "miyake", "village"),
    ("mikurajima-village", "mikurajima", "village"),
    ("hachijo-town", "hachijo", "town"),
    ("aogashima-village", "aogashima", "village"),
    ("ogasawara-village", "ogasawara", "village"),
]


def candidate_urls(assembly_id: str, slug: str, kind: str) -> list[str]:
    urls = [
        f"https://{slug}.gijiroku.com/voices/",
        f"https://gikai2.city.{slug}.tokyo.jp/voices/index.asp",
        f"https://www.gikai.city.{slug}.tokyo.jp/voices/",
        f"https://www.gikai-{slug}.jp/",
        f"https://{slug}city.gijiroku.com/voices/",
        f"https://www.city.{slug}.tokyo.dbsr.jp/index.php/",
    ]
    if kind == "ward":
        urls.extend(
            [
                f"https://www.city.{slug}.tokyo.jp/shigikai/",
                f"https://www.city.{slug}.lg.jp/shigikai/",
            ]
        )
    elif kind == "city":
        urls.extend(
            [
                f"https://www.city.{slug}.tokyo.jp/shigikai/",
                f"https://www.city.{slug}.lg.jp/shigikai/kaigiroku/",
            ]
        )
    elif kind == "town":
        urls.extend(
            [
                f"https://www.town.{slug}.tokyo.jp/shigikai/",
                f"https://www.city.{slug}.tokyo.jp/shigikai/",
            ]
        )
    elif kind == "village":
        urls.extend(
            [
                f"https://www.village.{slug}.tokyo.jp/shigikai/",
                f"https://www.city.{slug}.tokyo.jp/shigikai/",
            ]
        )
    if assembly_id == "toshima-village":
        urls.insert(0, "https://toshimamura.gijiroku.com/voices/")
    if assembly_id == "niijima-village":
        urls.insert(0, "https://niijimamura.gijiroku.com/voices/")
    if assembly_id == "ogasawara-village":
        urls.insert(0, "https://www.vill.ogasawara.tokyo.jp/shigikai/")
    return urls


def looks_like_records(response: requests.Response) -> bool:
    if response.status_code != 200:
        return False
    text = response.text
    lowered = text.lower()
    if len(text) < 300:
        return False
    if any(token in lowered for token in ("gijiroku", "dbsr", "kaigiroku", "voices")):
        return True
    return "会議録" in text or "議会" in text


def main() -> None:
    for assembly_id, slug, kind in REMAINING:
        found = False
        for url in candidate_urls(assembly_id, slug, kind):
            try:
                response = requests.get(url, timeout=15, allow_redirects=True)
            except requests.RequestException:
                continue
            if not looks_like_records(response):
                continue
            links = re.findall(r'href="([^"]+)"', response.text)
            docs = [
                link
                for link in links
                if any(token in link for token in ("Template=document", "voices/", "kaigiroku", "gijiroku"))
            ]
            print(f"{assembly_id}\tOK\t{response.url[:100]}\t{len(docs)} links")
            found = True
            break
        if not found:
            print(f"{assembly_id}\tNO")


if __name__ == "__main__":
    main()
