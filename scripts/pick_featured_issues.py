"""Pick flagship auto-records for newly ingested assemblies."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_ASSEMBLIES = [
    "chuo-ward",
    "kodaira-city",
    "akishima-city",
    "ome-city",
    "higashiyamato-city",
    "kiyose-city",
    "musashimurayama-city",
]
KEYWORDS = (
    "子育て",
    "保育",
    "防災",
    "高齢",
    "福祉",
    "教育",
    "物価",
    "空き家",
    "交通",
    "デジタル",
    "AI",
    "予算",
)


def score(record: dict) -> tuple[int, str]:
    topic = str(record.get("topic") or "")
    blob = topic + str(record.get("original_quote") or "")
    statements = record.get("statements") or []
    text = blob + " ".join(str(s.get("source_excerpt") or "") for s in statements)
    points = 0
    if "答弁" in text or "区長" in text or "市長" in text or "部長" in text:
        points += 5
    if any(role in text for role in ("答弁", "質問")):
        points += 2
    for keyword in KEYWORDS:
        if keyword in text:
            points += 3
            break
    if len(topic) >= 8 and "議案" not in topic[:6]:
        points += 1
    cleaned = re.sub(r"^[◆◎○△▲●\s\d]+", "", topic).strip()
    cleaned = re.sub(r"議員.*?(?=について|に関)", "", cleaned).strip()
    if len(cleaned) > 48:
        cleaned = cleaned[:47] + "…"
    title = cleaned or topic[:48]
    return points, title


def main() -> None:
    data = json.loads((ROOT / "data" / "assembly_records.json").read_text(encoding="utf-8"))
    for assembly_id in NEW_ASSEMBLIES:
        records = data["assemblies"][assembly_id]["records"]
        best = max(records, key=lambda record: (score(record)[0], record.get("meeting_date", "")))
        points, title = score(best)
        print(
            json.dumps(
                {
                    "assembly_id": assembly_id,
                    "issue_id": best["discussion_id"],
                    "title": title,
                    "score": points,
                    "meeting_date": best.get("meeting_date"),
                    "source_url": best.get("source_url"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
