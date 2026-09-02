"""Extra URL probes for batch 8 municipalities."""

from __future__ import annotations

import re
import urllib.request

URLS = [
    ("higashi-ssp", "https://ssp.kaigiroku.net/tenant/higashi/pg/index.html"),
    ("higashi-city", "https://www.city.higashimurayama.tokyo.jp/gikai/gikaijoho/kensaku/index.html"),
    ("hinohara-home", "https://www.vill.hinohara.tokyo.jp/"),
    ("aogashima-home", "https://www.vill.aogashima.tokyo.jp/"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status, response.read(120_000).decode("utf-8", "replace")


def main() -> None:
    for name, url in URLS:
        try:
            status, html = fetch(url)
            print(name, status, url)
            if "home" in name:
                links = re.findall(r'href="([^"]+)"', html)
                gikai_links = sorted(
                    {
                        link
                        for link in links
                        if "gikai" in link.lower()
                        or "shigikai" in link.lower()
                        or "議会" in link
                        or "kaigiroku" in link.lower()
                        or "shingi" in link.lower()
                    }
                )
                for link in gikai_links[:20]:
                    print(" ", link)
        except Exception as error:  # noqa: BLE001
            print(name, "ERR", error)


if __name__ == "__main__":
    main()
