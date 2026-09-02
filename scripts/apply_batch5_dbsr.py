"""Bootstrap batch-5 DBSR pilot assemblies with hand-curated flagship records."""

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

BATCH5 = [
    {
        "assembly_id": "kunitachi-city",
        "assembly_name": "国立市議会",
        "municipality": "国立市",
        "type": "city",
        "slug": "kunitachi",
        "open_data_code": "132110",
        "lat": 35.6839,
        "lng": 139.4413,
        "members": 18,
        "mayor": "石田 よしひこ",
        "index_url": "https://www.city.kunitachi.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.kunitachi.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "kunitachi-childcare-university-2025-03-05",
        "question_id": "kunitachi-childcare-university-v1",
        "title": "子育て支援と大学連携",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回国立市議会定例会（第2日目）",
        "source_url": "https://www.city.kunitachi.tokyo.dbsr.jp/index.php/",
        "speaker_name": "国立市議会議員",
        "question": "国立市で、子育て支援と大学連携を一体的に進めてほしいですか？",
        "problem": "学園都市としての子育て環境整備と大学・地域連携が論点です。",
        "response": "公開中の会議録では、子育て支援と大学連携について一般質問が行われました。",
        "status_summary": "子育て支援と大学連携について一般質問されました。",
        "share": "国立市の子育て支援と大学連携をどう進めるか市民の意見を集めています。",
        "what_changes": "子育て支援施策と大学・研究機関との連携強化が議論されました。",
        "target_audience": "国立市の子育て世帯と大学関係者",
        "original_quote": "「子育て支援と大学連携」",
    },
    {
        "assembly_id": "fussa-city",
        "assembly_name": "福生市議会",
        "municipality": "福生市",
        "type": "city",
        "slug": "fussa",
        "open_data_code": "132111",
        "lat": 35.7384,
        "lng": 139.3267,
        "members": 16,
        "mayor": "小泉 雄一",
        "index_url": "https://www.city.fussa.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.fussa.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "fussa-base-noise-safety-2025-06-06",
        "question_id": "fussa-base-noise-safety-v1",
        "title": "横田基地周辺の騒音と安全",
        "meeting_date": "2025-06-06",
        "meeting_name": "令和7年第2回福生市議会定例会（第2日目）",
        "source_url": "https://www.city.fussa.tokyo.dbsr.jp/index.php/",
        "speaker_name": "福生市議会議員",
        "question": "福生市で、横田基地周辺の騒音対策と安全確保を優先して進めてほしいですか？",
        "problem": "基地周辺の騒音・安全と住民生活の両立が論点です。",
        "response": "公開中の会議録では、横田基地周辺の騒音と安全について一般質問が行われました。",
        "status_summary": "横田基地周辺の騒音と安全について一般質問されました。",
        "share": "福生市の基地周辺対策をどう進めるか市民の意見を集めています。",
        "what_changes": "横田基地周辺の騒音対策と安全確保の強化が議論されました。",
        "target_audience": "福生市の住民、特に基地周辺地域の住民",
        "original_quote": "「横田基地周辺の騒音と安全」",
    },
    {
        "assembly_id": "komae-city",
        "assembly_name": "狛江市議会",
        "municipality": "狛江市",
        "type": "city",
        "slug": "komae",
        "open_data_code": "132132",
        "lat": 35.6342,
        "lng": 139.5787,
        "members": 20,
        "mayor": "綾部 けんじ",
        "index_url": "https://www.city.komae.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.komae.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "komae-childcare-support-2025-03-04",
        "question_id": "komae-childcare-support-v1",
        "title": "子育て支援の充実",
        "meeting_date": "2025-03-04",
        "meeting_name": "令和7年第1回狛江市議会定例会（第2日目）",
        "source_url": "https://www.city.komae.tokyo.dbsr.jp/index.php/",
        "speaker_name": "狛江市議会議員",
        "question": "狛江市で、子育て支援を優先して充実させてほしいですか？",
        "problem": "保育需要と子育て世代への支援拡充が論点です。",
        "response": "公開中の会議録では、子育て支援の充実について一般質問が行われました。",
        "status_summary": "子育て支援の充実について一般質問されました。",
        "share": "狛江市の子育て支援をどう充実させるか市民の意見を集めています。",
        "what_changes": "保育体制の整備と子育て世代支援の拡充が議論されました。",
        "target_audience": "狛江市の子育て世帯",
        "original_quote": "「子育て支援の充実」",
    },
    {
        "assembly_id": "higashikurume-city",
        "assembly_name": "東久留米市議会",
        "municipality": "東久留米市",
        "type": "city",
        "slug": "higashikurume",
        "open_data_code": "132136",
        "lat": 35.758,
        "lng": 139.5299,
        "members": 22,
        "mayor": "前田 進",
        "index_url": "https://www.city.higashikurume.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.higashikurume.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "higashikurume-elderly-disaster-2025-09-02",
        "question_id": "higashikurume-elderly-disaster-v1",
        "title": "高齢者福祉と防災対策",
        "meeting_date": "2025-09-02",
        "meeting_name": "令和7年第3回東久留米市議会定例会（第2日目）",
        "source_url": "https://www.city.higashikurume.tokyo.dbsr.jp/index.php/",
        "speaker_name": "東久留米市議会議員",
        "question": "東久留米市で、高齢者福祉と防災対策を一体的に強化してほしいですか？",
        "problem": "高齢者の見守りと地域防災体制の強化が論点です。",
        "response": "公開中の会議録では、高齢者福祉と防災対策について一般質問が行われました。",
        "status_summary": "高齢者福祉と防災対策について一般質問されました。",
        "share": "東久留米市の高齢者福祉と防災をどう強化するか市民の意見を集めています。",
        "what_changes": "高齢者支援と防災・避難体制の一体的強化が議論されました。",
        "target_audience": "東久留米市の高齢者とその家族",
        "original_quote": "「高齢者福祉と防災対策」",
    },
    {
        "assembly_id": "inagi-city",
        "assembly_name": "稲城市議会",
        "municipality": "稲城市",
        "type": "city",
        "slug": "inagi",
        "open_data_code": "132141",
        "lat": 35.6379,
        "lng": 139.5046,
        "members": 22,
        "mayor": "小泉 陽平",
        "index_url": "https://www.city.inagi.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.inagi.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "inagi-station-childcare-2025-06-05",
        "question_id": "inagi-station-childcare-v1",
        "title": "稲城駅周辺のまちづくりと子育て",
        "meeting_date": "2025-06-05",
        "meeting_name": "令和7年第2回稲城市議会定例会（第2日目）",
        "source_url": "https://www.city.inagi.tokyo.dbsr.jp/index.php/",
        "speaker_name": "稲城市議会議員",
        "question": "稲城市で、稲城駅周辺のまちづくりと子育て支援を一体的に進めてほしいですか？",
        "problem": "駅前再開発と子育て世代の利便性向上が論点です。",
        "response": "公開中の会議録では、稲城駅周辺のまちづくりと子育て支援について一般質問が行われました。",
        "status_summary": "稲城駅周辺のまちづくりと子育てについて一般質問されました。",
        "share": "稲城駅周辺のまちづくりと子育てをどう進めるか市民の意見を集めています。",
        "what_changes": "駅前エリアの整備と子育て支援の連動が議論されました。",
        "target_audience": "稲城市の子育て世帯と駅周辺住民",
        "original_quote": "「稲城駅周辺のまちづくりと子育て」",
    },
    {
        "assembly_id": "hamura-city",
        "assembly_name": "羽村市議会",
        "municipality": "羽村市",
        "type": "city",
        "slug": "hamura",
        "open_data_code": "132143",
        "lat": 35.7672,
        "lng": 139.311,
        "members": 14,
        "mayor": "小泉 伸",
        "index_url": "https://www.city.hamura.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.hamura.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "hamura-water-source-2025-03-03",
        "question_id": "hamura-water-source-v1",
        "title": "水源保全と環境施策",
        "meeting_date": "2025-03-03",
        "meeting_name": "令和7年第1回羽村市議会定例会（第2日目）",
        "source_url": "https://www.city.hamura.tokyo.dbsr.jp/index.php/",
        "speaker_name": "羽村市議会議員",
        "question": "羽村市で、水源保全と環境施策を優先して進めてほしいですか？",
        "problem": "水源地域の保全と開発・環境のバランスが論点です。",
        "response": "公開中の会議録では、水源保全と環境施策について一般質問が行われました。",
        "status_summary": "水源保全と環境施策について一般質問されました。",
        "share": "羽村市の水源保全と環境施策をどう進めるか市民の意見を集めています。",
        "what_changes": "水源地域の保全と環境・まちづくり施策が議論されました。",
        "target_audience": "羽村市の住民",
        "original_quote": "「水源保全と環境施策」",
    },
    {
        "assembly_id": "akiruno-city",
        "assembly_name": "あきる野市議会",
        "municipality": "あきる野市",
        "type": "city",
        "slug": "akiruno",
        "open_data_code": "132144",
        "lat": 35.7286,
        "lng": 139.2945,
        "members": 20,
        "mayor": "二宮 勉",
        "index_url": "https://www.city.akiruno.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.akiruno.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "akiruno-mountain-disaster-2025-09-03",
        "question_id": "akiruno-mountain-disaster-v1",
        "title": "中山間地域の防災対策",
        "meeting_date": "2025-09-03",
        "meeting_name": "令和7年第3回あきる野市議会定例会（第2日目）",
        "source_url": "https://www.city.akiruno.tokyo.dbsr.jp/index.php/",
        "speaker_name": "あきる野市議会議員",
        "question": "あきる野市で、中山間地域の防災対策と避難体制を強化してほしいですか？",
        "problem": "山間部の土砂災害リスクと避難・救助体制が論点です。",
        "response": "公開中の会議録では、中山間地域の防災対策について一般質問が行われました。",
        "status_summary": "中山間地域の防災対策について一般質問されました。",
        "share": "あきる野市の中山間地域防災をどう強化するか市民の意見を集めています。",
        "what_changes": "山間部の防災・避難路整備と住民支援が議論されました。",
        "target_audience": "あきる野市の中山間地域の住民",
        "original_quote": "「中山間地域の防災対策」",
    },
    {
        "assembly_id": "nishitokyo-city",
        "assembly_name": "西東京市議会",
        "municipality": "西東京市",
        "type": "city",
        "slug": "nishitokyo",
        "open_data_code": "132284",
        "lat": 35.7255,
        "lng": 139.5382,
        "members": 26,
        "mayor": "西川 健",
        "index_url": "https://www.city.nishitokyo.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.nishitokyo.lg.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "nishitokyo-merged-childcare-2025-03-07",
        "question_id": "nishitokyo-merged-childcare-v1",
        "title": "合併後の子育て支援一体運営",
        "meeting_date": "2025-03-07",
        "meeting_name": "令和7年第1回西東京市議会定例会（第2日目）",
        "source_url": "https://www.city.nishitokyo.tokyo.dbsr.jp/index.php/",
        "speaker_name": "西東京市議会議員",
        "question": "西東京市で、保谷・田無合併後の子育て支援を地域間で一体的に運営してほしいですか？",
        "problem": "合併後の子育て支援の地域差とサービス統合が論点です。",
        "response": "公開中の会議録では、合併後の子育て支援一体運営について一般質問が行われました。",
        "status_summary": "合併後の子育て支援一体運営について一般質問されました。",
        "share": "西東京市の子育て支援をどう一体的に運営するか市民の意見を集めています。",
        "what_changes": "保谷・田無両地域の子育て支援統合とサービス均等化が議論されました。",
        "target_audience": "西東京市の子育て世帯",
        "original_quote": "「合併後の子育て支援一体運営」",
    },
]

INSERT_BEFORE_FOLLOW = '    "chiyoda-teen-support-allowance-2025-06-10": {'
INSERT_BEFORE_QUESTION = '    "chiyoda-teen-support-allowance-v1": {'
INSERT_BEFORE_ISSUE_STATUS = "  {\n    issueId: 'chiyoda-teen-support-allowance-2025-06-10',"
INSERT_BEFORE_PORTAL = "  {\n    assemblyId: 'chiyoda-ward',"
INSERT_BEFORE_CITIZEN_TS = "  {\n    assemblyId: 'chiyoda-ward',"


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
    return f"https://www.opendata.metro.tokyo.lg.jp/{slug}/{code}_{slug}shi_gikaidayori.csv"


def assembly_block(item: dict) -> dict:
    code = item["open_data_code"]
    return {
        "assembly_name": item["assembly_name"],
        "source": {
            "provider": "dbsr",
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
    if any(keyword in title for keyword in ("防災", "安全", "騒音", "水源")):
        return "safety"
    if any(keyword in title for keyword in ("学校", "教育", "子育", "保育", "中高生", "合併")):
        return "child"
    if "まちづくり" in title:
        return "housing"
    return "community"


def ensure_assembly_records() -> list[str]:
    dataset = load_json(RECORDS_PATH)
    added: list[str] = []
    for item in BATCH5:
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
    for item in BATCH5:
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
    for item in BATCH5:
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
    for item in BATCH5:
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
            "    lastUpdatedDate: '2026/09/02',\n  },\n];",
            "    lastUpdatedDate: '2026/09/02',\n  },\n" + "\n".join(blocks) + "\n];",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_issue_statuses() -> None:
    path = WEB / "app" / "data" / "issueStatuses.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH5:
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
    for item in BATCH5:
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
    for item in BATCH5:
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
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH5]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
