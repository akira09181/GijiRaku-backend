"""Fetch a UTF-8 Kokkai API sample for national-diet curation."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

QUERY = {
    "from": "2025-03-13",
    "until": "2025-03-13",
    "nameOfHouse": "衆議院",
    "nameOfMeeting": "予算委員会",
    "maximumRecords": 30,
    "recordPacking": "json",
}

url = "https://kokkai.ndl.go.jp/api/speech?" + urllib.parse.urlencode(QUERY)
request = urllib.request.Request(url, headers={"User-Agent": "GijiRaku/1.0"})
with urllib.request.urlopen(request, timeout=30) as response:
    payload = json.loads(response.read().decode("utf-8"))

samples = []
for record in payload["speechRecord"]:
    speech = record.get("speech", "")
    if record.get("speechOrder", 0) <= 0 or len(speech) < 120:
        continue
    if not any(keyword in speech for keyword in ("物価", "医療", "子育て", "社会保障")):
        continue
    samples.append(
        {
            "date": record["date"],
            "speaker": record["speaker"],
            "meeting": record["nameOfMeeting"],
            "issue": record.get("issue"),
            "speechURL": record.get("speechURL"),
            "meetingURL": record.get("meetingURL"),
            "excerpt": speech[:400],
        }
    )

print(json.dumps(samples[:5], ensure_ascii=False, indent=2))
