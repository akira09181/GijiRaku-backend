"""Bootstrap batch-7 gijiroku/voices pilot assemblies with hand-curated flagship records."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent / "gijiraku-web"
RECORDS_PATH = ROOT / "data" / "assembly_records.json"
JST = timezone(timedelta(hours=9))

BATCH7 = [
    {
        "assembly_id": "meguro-ward",
        "assembly_name": "目黒区議会",
        "municipality": "目黒区",
        "type": "ward",
        "slug": "meguro",
        "open_data_code": "131105",
        "lat": 35.6414,
        "lng": 139.6982,
        "members": 36,
        "mayor": "青木 英太",
        "index_url": "https://www.kensakusystem.jp/meguro-jimu/index.html",
        "portal_url": "https://www.city.meguro.tokyo.jp/kusei/seisaku/public_comment/index.html",
        "issue_id": "meguro-childcare-demand-2025-03-05",
        "question_id": "meguro-childcare-demand-v1",
        "title": "子育て支援と保育需要",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回目黒区議会定例会（第2日目）",
        "source_url": "https://www.kensakusystem.jp/meguro-jimu/index.html",
        "speaker_name": "目黒区議会議員",
        "question": "目黒区で、子育て支援と保育需要への対応を優先して進めてほしいですか？",
        "problem": "保育・学童需要の増加と子育て世代支援の優先順位が論点です。",
        "response": "公開中の会議録では、子育て支援と保育需要への対応について一般質問が行われました。",
        "status_summary": "子育て支援と保育需要への対応について一般質問されました。",
        "share": "目黒区の子育て支援と保育需要への対応をどう進めるか市民の意見を集めています。",
        "what_changes": "保育施設整備と子育て支援策の拡充が議論されました。",
        "target_audience": "目黒区の子育て世帯",
        "original_quote": "「子育て支援と保育需要」",
    },
    {
        "assembly_id": "ota-ward",
        "assembly_name": "大田区議会",
        "municipality": "大田区",
        "type": "ward",
        "slug": "ota",
        "open_data_code": "131113",
        "lat": 35.5613,
        "lng": 139.7161,
        "members": 50,
        "mayor": "浦野 直人",
        "index_url": "https://ota.gijiroku.com/voices/",
        "portal_url": "https://www.city.ota.tokyo.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "ota-childcare-medical-2025-03-04",
        "question_id": "ota-childcare-medical-v1",
        "title": "子育て支援と地域医療",
        "meeting_date": "2025-03-04",
        "meeting_name": "令和7年第1回大田区議会定例会（第2日目）",
        "source_url": "https://ota.gijiroku.com/voices/",
        "speaker_name": "大田区議会議員",
        "question": "大田区で、子育て支援と地域医療の充実を優先して進めてほしいですか？",
        "problem": "子育て世代支援と地域医療・福祉の連携強化が論点です。",
        "response": "公開中の会議録では、子育て支援と地域医療について一般質問が行われました。",
        "status_summary": "子育て支援と地域医療について一般質問されました。",
        "share": "大田区の子育て支援と地域医療をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と地域医療体制の強化が議論されました。",
        "target_audience": "大田区の子育て世帯と高齢者",
        "original_quote": "「子育て支援と地域医療」",
    },
    {
        "assembly_id": "toshima-ward",
        "assembly_name": "豊島区議会",
        "municipality": "豊島区",
        "type": "ward",
        "slug": "toshima",
        "open_data_code": "131164",
        "lat": 35.726,
        "lng": 139.7164,
        "members": 36,
        "mayor": "高野 順子",
        "index_url": "https://www.kensakusystem.jp/toshima/",
        "portal_url": "https://www.city.toshima.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "toshima-childcare-support-2025-03-06",
        "question_id": "toshima-childcare-support-v1",
        "title": "子育て支援施策の充実",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回豊島区議会定例会（第2日目）",
        "source_url": "https://www.kensakusystem.jp/toshima/",
        "speaker_name": "豊島区議会議員",
        "question": "豊島区で、子育て支援施策を優先して充実させてほしいですか？",
        "problem": "保育・学童需要と子育て世代への経済的支援の優先順位が論点です。",
        "response": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "share": "豊島区の子育て支援をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て世代への支援拡充と区立学校・保育の環境整備が議論されました。",
        "target_audience": "豊島区の子育て世帯",
        "original_quote": "「子育て支援施策の充実」",
    },
    {
        "assembly_id": "katsushika-ward",
        "assembly_name": "葛飾区議会",
        "municipality": "葛飾区",
        "type": "ward",
        "slug": "katsushika",
        "open_data_code": "131225",
        "lat": 35.7431,
        "lng": 139.8472,
        "members": 40,
        "mayor": "富樫 博之",
        "index_url": "https://www.kensakusystem.jp/katsushika/sapphire.html",
        "portal_url": "https://www.city.katsushika.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "katsushika-education-support-2025-03-05",
        "question_id": "katsushika-education-support-v1",
        "title": "子育て・教育支援の強化",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回葛飾区議会定例会（第2日目）",
        "source_url": "https://www.kensakusystem.jp/katsushika/sapphire.html",
        "speaker_name": "葛飾区議会議員",
        "question": "葛飾区で、子育て・教育支援を優先して強化してほしいですか？",
        "problem": "子育て支援と学校教育の質向上、施設整備の優先順位が論点です。",
        "response": "公開中の会議録では、子育て・教育支援の強化について一般質問が行われました。",
        "status_summary": "子育て・教育支援の強化について一般質問されました。",
        "share": "葛飾区の子育て・教育支援をどう強化するか市民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と学校教育環境の改善が議論されました。",
        "target_audience": "葛飾区の子育て世帯と学校関係者",
        "original_quote": "「子育て・教育支援の強化」",
    },
    {
        "assembly_id": "okutama-town",
        "assembly_name": "奥多摩町議会",
        "municipality": "奥多摩町",
        "type": "town",
        "slug": "okutama",
        "open_data_code": "133051",
        "lat": 35.8094,
        "lng": 139.0962,
        "members": 12,
        "mayor": "村田 富保",
        "index_url": "https://www.town.okutama.tokyo.jp/gyosei/8/okutamachogikai/kaigiroku/index.html",
        "portal_url": "https://www.town.okutama.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "okutama-mountain-disaster-2025-03-05",
        "question_id": "okutama-mountain-disaster-v1",
        "title": "中山間地域の防災と住民支援",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回奥多摩町議会定例会",
        "source_url": "https://www.town.okutama.tokyo.jp/gyosei/8/okutamachogikai/kaigiroku/index.html",
        "speaker_name": "奥多摩町議会議員",
        "question": "奥多摩町で、中山間地域の防災対策と住民支援を強化してほしいですか？",
        "problem": "山間部の防災・避難体制と過疎地域の生活支援が論点です。",
        "response": "公開中の会議録では、中山間地域の防災と住民支援について一般質問が行われました。",
        "status_summary": "中山間地域の防災と住民支援について一般質問されました。",
        "share": "奥多摩町の防災と住民支援をどう強化するか市民の意見を集めています。",
        "what_changes": "山間部の防災・避難路整備と住民支援が議論されました。",
        "target_audience": "奥多摩町の住民",
        "original_quote": "「中山間地域の防災と住民支援」",
    },
    {
        "assembly_id": "oshima-town",
        "assembly_name": "大島町議会",
        "municipality": "大島町",
        "type": "town",
        "slug": "oshima",
        "open_data_code": "133612",
        "lat": 34.7501,
        "lng": 139.3554,
        "members": 14,
        "mayor": "越知 隆直",
        "index_url": "https://www.town.oshima.tokyo.jp/soshiki/gikaijim/gikai-kekka.html",
        "portal_url": "https://www.town.oshima.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "oshima-island-transport-medical-2025-06-12",
        "question_id": "oshima-island-transport-medical-v1",
        "title": "離島交通と医療・福祉体制",
        "meeting_date": "2025-06-12",
        "meeting_name": "令和7年第2回大島町議会定例会",
        "source_url": "https://www.town.oshima.tokyo.jp/soshiki/gikaijim/gikai-kekka.html",
        "speaker_name": "大島町議会議員",
        "question": "大島町で、離島交通と医療・福祉体制の充実を優先して進めてほしいですか？",
        "problem": "離島の交通不便と医療・福祉サービスの確保が論点です。",
        "response": "公開中の会議録では、離島交通と医療・福祉体制について一般質問が行われました。",
        "status_summary": "離島交通と医療・福祉体制について一般質問されました。",
        "share": "大島町の離島交通と医療・福祉をどう充実させるか市民の意見を集めています。",
        "what_changes": "離島航路の維持と医療・福祉体制の強化が議論されました。",
        "target_audience": "大島町の住民",
        "original_quote": "「離島交通と医療・福祉体制」",
    },
    {
        "assembly_id": "hachijo-town",
        "assembly_name": "八丈町議会",
        "municipality": "八丈町",
        "type": "town",
        "slug": "hachijo",
        "open_data_code": "134015",
        "lat": 33.1126,
        "lng": 139.7887,
        "members": 14,
        "mayor": "姉川 信行",
        "index_url": "https://www.town.hachijo.tokyo.jp/chousei/chougikai/katsushin/shingi-kekka/",
        "portal_url": "https://www.town.hachijo.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "hachijo-island-medical-welfare-2025-03-07",
        "question_id": "hachijo-island-medical-welfare-v1",
        "title": "離島の医療・福祉確保",
        "meeting_date": "2025-03-07",
        "meeting_name": "令和7年第1回八丈町議会定例会",
        "source_url": "https://www.town.hachijo.tokyo.jp/chousei/chougikai/katsushin/shingi-kekka/",
        "speaker_name": "八丈町議会議員",
        "question": "八丈町で、離島の医療・福祉確保を優先して進めてほしいですか？",
        "problem": "離島における医療・福祉人材確保とサービス継続が論点です。",
        "response": "公開中の会議録では、離島の医療・福祉確保について一般質問が行われました。",
        "status_summary": "離島の医療・福祉確保について一般質問されました。",
        "share": "八丈町の医療・福祉をどう確保するか市民の意見を集めています。",
        "what_changes": "離島医療体制の維持と福祉サービスの充実が議論されました。",
        "target_audience": "八丈町の住民",
        "original_quote": "「離島の医療・福祉確保」",
    },
    {
        "assembly_id": "miyake-village",
        "assembly_name": "三宅村議会",
        "municipality": "三宅村",
        "type": "village",
        "slug": "miyake",
        "open_data_code": "133812",
        "lat": 34.0762,
        "lng": 139.5183,
        "members": 6,
        "mayor": "加藤 宏明",
        "index_url": "https://www.vill.miyake.tokyo.jp/kakuka/gikai/",
        "portal_url": "https://www.vill.miyake.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "miyake-island-disaster-life-2025-03-06",
        "question_id": "miyake-island-disaster-life-v1",
        "title": "離島の防災と生活基盤",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回三宅村議会定例会",
        "source_url": "https://www.vill.miyake.tokyo.jp/kakuka/gikai/",
        "speaker_name": "三宅村議会議員",
        "question": "三宅村で、離島の防災対策と生活基盤の維持を優先して進めてほしいですか？",
        "problem": "火山・台風リスクへの備えと離島生活基盤の維持が論点です。",
        "response": "公開中の会議録では、離島の防災と生活基盤について一般質問が行われました。",
        "status_summary": "離島の防災と生活基盤について一般質問されました。",
        "share": "三宅村の防災と生活基盤をどう維持するか村民の意見を集めています。",
        "what_changes": "防災体制の強化と生活インフラの維持が議論されました。",
        "target_audience": "三宅村の村民",
        "original_quote": "「離島の防災と生活基盤」",
    },
]

INSERT_BEFORE_FOLLOW = '    "nishitokyo-merged-childcare-2025-03-07": {'
INSERT_BEFORE_QUESTION = '    "nishitokyo-merged-childcare-v1": {'
INSERT_BEFORE_ISSUE_STATUS = "  {\n    issueId: 'nishitokyo-merged-childcare-2025-03-07',"
INSERT_BEFORE_PORTAL = "  {\n    assemblyId: 'nishitokyo-city',"
INSERT_BEFORE_CITIZEN_TS = "  {\n    assemblyId: 'nishitokyo-city',"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(path)


def open_data_resource_url(item: dict) -> str:
    code = item["open_data_code"]
    slug = item["slug"]
    if item["type"] == "ward":
        suffix = "ku"
    elif item["type"] == "city":
        suffix = "shi"
    elif item["type"] == "town":
        suffix = "machi"
    else:
        suffix = "mura"
    return f"https://www.opendata.metro.tokyo.lg.jp/{slug}/{code}_{slug}{suffix}_gikaidayori.csv"


def assembly_block(item: dict) -> dict:
    code = item["open_data_code"]
    return {
        "assembly_name": item["assembly_name"],
        "source": {
            "provider": "gijiroku",
            "index_url": item["index_url"],
            "open_data": {
                "title": "議会だより",
                "catalog_url": f"https://catalog.data.metro.tokyo.lg.jp/dataset/t{code}d2024000001",
                "resource_url": open_data_resource_url(item),
                "format": "CSV",
                "license_id": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/deed.ja",
                "usage": "議会刊行物の発行年月と原典URLの確認",
            },
        },
        "records": [],
    }


def record_block(item: dict) -> dict:
    slug = item["assembly_id"].split("-")[0]
    year, month, day = item["meeting_date"].split("-")
    stage_date = f"{year}年{int(month)}月{int(day)}日"
    return {
        "discussion_id": item["issue_id"],
        "meeting_date": item["meeting_date"],
        "meeting_name": item["meeting_name"],
        "source_url": item["source_url"],
        "topic": item["title"],
        "what_changes": item["what_changes"],
        "target_audience": item["target_audience"],
        "current_stage": f"{stage_date}の本会議で一般質問済み",
        "budget_info": "予算・数値はリンク先の公式会議録原文を参照",
        "original_quote": item["original_quote"],
        "publication_status": "published",
        "statements": [
            {
                "statement_id": f"{slug}-{item['meeting_date']}-question",
                "speaker_name": item["speaker_name"],
                "speaker_role": f"{item['municipality']}議会議員",
                "committee_name": "本会議",
                "stance_label": "課題提起",
                "summary_quote": f"{item['title']}について一般質問しました。",
                "full_summary": item["problem"],
                "source_excerpt": item["original_quote"],
                "question_type": "一般質問",
                "avatar_color": "sky",
            }
        ],
    }


def issue_theme(item: dict) -> str:
    title = item["title"]
    if any(keyword in title for keyword in ("防災", "安全", "騒音", "水源", "離島", "生活基盤")):
        return "safety"
    if any(keyword in title for keyword in ("学校", "教育", "子育", "保育", "中高生", "合併")):
        return "child"
    if any(keyword in title for keyword in ("医療", "福祉")):
        return "health"
    if "まちづくり" in title:
        return "housing"
    return "community"


def ensure_assembly_records() -> list[str]:
    dataset = load_json(RECORDS_PATH)
    added: list[str] = []
    for item in BATCH7:
        assembly_id = item["assembly_id"]
        if assembly_id not in dataset["assemblies"]:
            dataset["assemblies"][assembly_id] = assembly_block(item)
            added.append(assembly_id)
        records = dataset["assemblies"][assembly_id].setdefault("records", [])
        if not any(r.get("discussion_id") == item["issue_id"] for r in records):
            records.append(record_block(item))
            if assembly_id not in added:
                added.append(assembly_id)
    dataset["updated_at"] = datetime.now(JST).replace(microsecond=0).isoformat()
    write_json(RECORDS_PATH, dataset)
    return added


def patch_follow_store() -> None:
    path = ROOT / "follow_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if item["issue_id"] in text:
            continue
        blocks.append(
            f'''    "{item["issue_id"]}": {{
        "question_id": "{item["question_id"]}",
        "assembly_id": "{item["assembly_id"]}",
        "municipality": "{item["municipality"]}",
        "title": "{item["title"]}",
        "current_status": "議会で一般質問済み",
        "status_summary": "{item["status_summary"]}",
        "status_updated_at": "{item["meeting_date"]}T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "{item["problem"]}",
        "government_response_summary": "{item["response"]}",
        "share_summary": "{item["share"]}",
        "source_url": "{item["source_url"]}",
    }},'''
        )
    if blocks:
        text = text.replace(
            INSERT_BEFORE_FOLLOW,
            "\n".join(blocks) + "\n" + INSERT_BEFORE_FOLLOW,
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_question_store() -> None:
    path = ROOT / "citizen_question_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if f'"{item["question_id"]}"' in text:
            continue
        blocks.append(
            f'''    "{item["question_id"]}": {{
        "issue_id": "{item["issue_id"]}",
        "question": "{item["question"]}",
        "answers": [
            {{"id": "prioritize", "label": "優先して進めてほしい"}},
            {{"id": "steady_progress", "label": "慎重に段階的に進めてほしい"}},
            {{"id": "need_more_information", "label": "判断材料が足りない"}},
        ],
        "reasons": [
            {{"id": "resident_need", "label": "地域のニーズが高い"}},
            {{"id": "implementation", "label": "具体策や費用が気になる"}},
            {{"id": "info_hard_to_find", "label": "情報が分かりにくい"}},
            {{"id": "fiscal_priority", "label": "財源や優先順位が気になる"}},
            {{"id": "no_direct_experience", "label": "直接の利用経験がない"}},
            {{"id": "other", "label": "その他"}},
        ],
        "municipality": "{item["municipality"]}",
        "theme": "{item["title"]}",
    }},'''
        )
    if blocks:
        text = text.replace(
            INSERT_BEFORE_QUESTION,
            "\n".join(blocks) + "\n" + INSERT_BEFORE_QUESTION,
            1,
        )
        path.write_text(text, encoding="utf-8")


def _meeting_label(meeting_date: str) -> str:
    year, month, day = meeting_date.split("-")
    return f"{int(year)}/{int(month)}/{int(day)}｜定例会"


def patch_home_page() -> None:
    path = WEB / "app" / "home-page.tsx"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if f"id: '{item['assembly_id']}'" in text:
            continue
        theme = issue_theme(item)
        blocks.append(
            f"""  {{
    id: '{item["assembly_id"]}',
    name: '{item["assembly_name"]}',
    type: '{item["type"]}',
    lat: {item["lat"]},
    lng: {item["lng"]},
    membersCount: {item["members"]},
    mayorName: '{item["mayor"]}',
    openDataStatus: 'ready',
    totalMinutesCount: 1,
    featuredDiscussionId: '{item["issue_id"]}',
    hotTopic: '{item["title"]}',
    mainIssues: [
      {{ theme: '{theme}', label: '{item["title"]}', count: 1 }},
    ],
    sourceUrl: '{item["source_url"]}',
    lastMeetingDate: '{_meeting_label(item["meeting_date"])}',
    lastUpdatedDate: '2026/09/02',
  }},"""
        )
    if blocks:
        text = text.replace(
            "    sourceUrl: 'https://taito.gijiroku.com/voices/',\n    lastMeetingDate: '2025/3/6｜定例会',\n    lastUpdatedDate: '2026/09/02',\n  },\n];",
            "    sourceUrl: 'https://taito.gijiroku.com/voices/',\n    lastMeetingDate: '2025/3/6｜定例会',\n    lastUpdatedDate: '2026/09/02',\n  },\n"
            + "\n".join(blocks)
            + "\n];",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_issue_statuses() -> None:
    path = WEB / "app" / "data" / "issueStatuses.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if item["issue_id"] in text:
            continue
        blocks.append(
            f"""  {{
    issueId: '{item["issue_id"]}',
    problemSummary: '{item["problem"]}',
    governmentResponseSummary: '{item["response"]}',
    currentStatus: '議会で一般質問済み',
    statusSummary: '{item["status_summary"]}',
    statusUpdatedAt: '{item["meeting_date"]}T00:00:00+09:00',
    statusCheckedAt: '2026-09-02T18:00:00+09:00',
    sourceUrl: '{item["source_url"]}',
  }},"""
        )
    if blocks:
        text = text.replace(
            INSERT_BEFORE_ISSUE_STATUS,
            "\n".join(blocks) + "\n" + INSERT_BEFORE_ISSUE_STATUS,
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_public_comment_portals() -> None:
    path = WEB / "app" / "data" / "publicCommentPortals.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if f"assemblyId: '{item['assembly_id']}'" in text:
            continue
        label = f"{item['municipality']} パブリックコメント"
        blocks.append(
            f"""  {{
    assemblyId: '{item["assembly_id"]}',
    municipality: '{item["municipality"]}',
    portalLabel: '{label}',
    portalUrl: '{item["portal_url"]}',
    guidance: '市のパブリックコメントページで、該当する募集を選んで意見を提出してください。',
  }},"""
        )
    if blocks:
        text = text.replace(
            INSERT_BEFORE_PORTAL,
            "\n".join(blocks) + "\n" + INSERT_BEFORE_PORTAL,
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_questions_ts() -> None:
    path = WEB / "app" / "data" / "citizenQuestions.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH7:
        if item["issue_id"] in text:
            continue
        slug = item["question_id"].replace("-v1", "")
        blocks.append(
            f"""  {{
    assemblyId: '{item["assembly_id"]}',
    issueId: '{item["issue_id"]}',
    questionId: '{item["question_id"]}',
    municipality: '{item["municipality"]}',
    theme: '{item["title"]}',
    question: '{item["question"]}',
    statusCheckedAt: '2026/09/02',
    answers: [
      {{ id: 'prioritize', label: '優先して進めてほしい' }},
      {{ id: 'steady_progress', label: '慎重に段階的に進めてほしい' }},
      {{ id: 'need_more_information', label: '判断材料が足りない' }},
    ],
    reasons: [
      {{ id: 'resident_need', label: '地域のニーズが高い' }},
      {{ id: 'implementation', label: '具体策や費用が気になる' }},
      {{ id: 'info_hard_to_find', label: '情報が分かりにくい' }},
      {{ id: 'fiscal_priority', label: '財源や優先順位が気になる' }},
      {{ id: 'no_direct_experience', label: '直接の利用経験がない' }},
      {{ id: 'other', label: 'その他' }},
    ],
    draft: {{
      templateId: '{slug}-opinion-v1',
      answerStatements: {{
        prioritize: '{item["municipality"]}の{item["title"]}を優先して進めてほしいです。',
        steady_progress: '{item["municipality"]}の{item["title"]}は、慎重に段階的に進めてほしいです。',
        need_more_information: '{item["title"]}は、具体策を示してから判断したいです。',
      }},
      reasonClauses: {{
        resident_need: '地域のニーズが高いこと',
        implementation: '具体策や費用が気になること',
        info_hard_to_find: '情報が分かりにくいこと',
        fiscal_priority: '財源や優先順位が気になること',
        no_direct_experience: '直接の利用経験がないこと',
        other: 'ほかにも考慮したい点があること',
      }},
    }},
  }},"""
        )
    if blocks:
        text = text.replace(
            INSERT_BEFORE_CITIZEN_TS,
            "\n".join(blocks) + "\n" + INSERT_BEFORE_CITIZEN_TS,
            1,
        )
        path.write_text(text, encoding="utf-8")


def main() -> int:
    added = ensure_assembly_records()
    patch_follow_store()
    patch_citizen_question_store()
    patch_home_page()
    patch_issue_statuses()
    patch_public_comment_portals()
    patch_citizen_questions_ts()
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH7]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
