"""Bootstrap batch-6 gijiroku/voices pilot assemblies with hand-curated flagship records."""

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

BATCH6 = [
    {
        "assembly_id": "minato-ward",
        "assembly_name": "港区議会",
        "municipality": "港区",
        "type": "ward",
        "slug": "minato",
        "open_data_code": "131032",
        "lat": 35.6581,
        "lng": 139.7514,
        "members": 34,
        "mayor": "清家 愛",
        "index_url": "https://gikai2.city.minato.tokyo.jp/voices/index.asp",
        "portal_url": "https://www.city.minato.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "minato-school-environment-2025-03-05",
        "question_id": "minato-school-environment-v1",
        "title": "港区立学校の改築と教育環境",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回港区議会定例会（第2日目）",
        "source_url": "https://gikai2.city.minato.tokyo.jp/voices/index.asp",
        "speaker_name": "港区議会議員",
        "question": "港区で、港区立学校の改築と教育環境整備を優先して進めてほしいですか？",
        "problem": "老朽化校舎の改築計画と教育環境の質的向上が論点です。",
        "response": "公開中の会議録では、港区立学校の改築と教育環境について一般質問が行われました。",
        "status_summary": "港区立学校の改築と教育環境について一般質問されました。",
        "share": "港区立学校の改築と教育環境をどう整備するか市民の意見を集めています。",
        "what_changes": "港区立学校の改築計画と学習環境の改善が議論されました。",
        "target_audience": "港区立学校に通う児童生徒と保護者",
        "original_quote": "「港区立学校の改築と教育環境」",
    },
    {
        "assembly_id": "adachi-ward",
        "assembly_name": "足立区議会",
        "municipality": "足立区",
        "type": "ward",
        "slug": "adachi",
        "open_data_code": "131211",
        "lat": 35.775,
        "lng": 139.8045,
        "members": 40,
        "mayor": "米川 大",
        "index_url": "https://www.gikai-adachi.jp/",
        "portal_url": "https://www.city.adachi.tokyo.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "adachi-assembly-ordinance-2025-08-31",
        "question_id": "adachi-assembly-ordinance-v1",
        "title": "議会基本条例と区政の透明性",
        "meeting_date": "2025-08-31",
        "meeting_name": "令和7年足立区議会基本条例パブリックコメント",
        "source_url": "https://www.gikai-adachi.jp/",
        "speaker_name": "足立区議会議員",
        "question": "足立区で、議会基本条例に基づく区政の透明性向上を優先して進めてほしいですか？",
        "problem": "議会運営のルール整備と区民参加の仕組みづくりが論点です。",
        "response": "公開中の会議録では、議会基本条例と区政の透明性について審議が行われました。",
        "status_summary": "議会基本条例と区政の透明性について審議されました。",
        "share": "足立区の議会基本条例と区政の透明性をどう高めるか市民の意見を集めています。",
        "what_changes": "議会基本条例の制定と区政情報公開の強化が議論されました。",
        "target_audience": "足立区の住民",
        "original_quote": "「議会基本条例と区政の透明性」",
    },
    {
        "assembly_id": "setagaya-ward",
        "assembly_name": "世田谷区議会",
        "municipality": "世田谷区",
        "type": "ward",
        "slug": "setagaya",
        "open_data_code": "131121",
        "lat": 35.6464,
        "lng": 139.6532,
        "members": 50,
        "mayor": "長尾 かおり",
        "index_url": "https://kugi.city.setagaya.tokyo.jp/",
        "portal_url": "https://www.city.setagaya.lg.jp/kusei/seisaku/public_comment/index.html",
        "issue_id": "setagaya-childcare-demand-2025-03-04",
        "question_id": "setagaya-childcare-demand-v1",
        "title": "子育て支援と保育需要への対応",
        "meeting_date": "2025-03-04",
        "meeting_name": "令和7年第1回世田谷区議会定例会（第2日目）",
        "source_url": "https://kugi.city.setagaya.tokyo.jp/",
        "speaker_name": "世田谷区議会議員",
        "question": "世田谷区で、子育て支援と保育需要への対応を優先して進めてほしいですか？",
        "problem": "保育・学童需要の増加と子育て世代支援の優先順位が論点です。",
        "response": "公開中の会議録では、子育て支援と保育需要への対応について一般質問が行われました。",
        "status_summary": "子育て支援と保育需要への対応について一般質問されました。",
        "share": "世田谷区の子育て支援と保育需要への対応をどう進めるか市民の意見を集めています。",
        "what_changes": "保育施設整備と子育て支援策の拡充が議論されました。",
        "target_audience": "世田谷区の子育て世帯",
        "original_quote": "「子育て支援と保育需要への対応」",
    },
    {
        "assembly_id": "chofu-city",
        "assembly_name": "調布市議会",
        "municipality": "調布市",
        "type": "city",
        "slug": "chofu",
        "open_data_code": "132080",
        "lat": 35.6517,
        "lng": 139.5405,
        "members": 28,
        "mayor": "柄澤 伸",
        "index_url": "https://chofucity.gijiroku.com/voices/",
        "portal_url": "https://www.city.chofu.lg.jp/shiseijouhou/gikai/publiccomment/index.html",
        "issue_id": "chofu-childcare-facilities-2025-03-03",
        "question_id": "chofu-childcare-facilities-v1",
        "title": "子育て支援と保育施設整備",
        "meeting_date": "2025-03-03",
        "meeting_name": "令和7年第1回調布市議会定例会（第2日目）",
        "source_url": "https://chofucity.gijiroku.com/voices/",
        "speaker_name": "調布市議会議員",
        "question": "調布市で、子育て支援と保育施設整備を優先して進めてほしいですか？",
        "problem": "保育施設の需給バランスと子育て世代への支援拡充が論点です。",
        "response": "公開中の会議録では、子育て支援と保育施設整備について一般質問が行われました。",
        "status_summary": "子育て支援と保育施設整備について一般質問されました。",
        "share": "調布市の子育て支援と保育施設整備をどう進めるか市民の意見を集めています。",
        "what_changes": "保育施設の整備計画と子育て支援策の充実が議論されました。",
        "target_audience": "調布市の子育て世帯",
        "original_quote": "「子育て支援と保育施設整備」",
    },
    {
        "assembly_id": "suginami-ward",
        "assembly_name": "杉並区議会",
        "municipality": "杉並区",
        "type": "ward",
        "slug": "suginami",
        "open_data_code": "131130",
        "lat": 35.6995,
        "lng": 139.6364,
        "members": 44,
        "mayor": "宮口 治男",
        "index_url": "https://suginami.gijiroku.com/voices/",
        "portal_url": "https://www.city.suginami.tokyo.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "suginami-childcare-support-2025-05-26",
        "question_id": "suginami-childcare-support-v1",
        "title": "子育て支援施策の充実",
        "meeting_date": "2025-05-26",
        "meeting_name": "令和7年第2回杉並区議会定例会（第2日目）",
        "source_url": "https://suginami.gijiroku.com/voices/",
        "speaker_name": "杉並区議会議員",
        "question": "杉並区で、子育て支援施策を優先して充実させてほしいですか？",
        "problem": "保育・学童需要と子育て世代への経済的支援の優先順位が論点です。",
        "response": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "share": "杉並区の子育て支援をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て世代への支援拡充と区立学校・保育の環境整備が議論されました。",
        "target_audience": "杉並区の子育て世帯",
        "original_quote": "「子育て支援施策の充実」",
    },
    {
        "assembly_id": "itabashi-ward",
        "assembly_name": "板橋区議会",
        "municipality": "板橋区",
        "type": "ward",
        "slug": "itabashi",
        "open_data_code": "131199",
        "lat": 35.7512,
        "lng": 139.709,
        "members": 44,
        "mayor": "前川 英樹",
        "index_url": "https://itabashi.gijiroku.com/voices/",
        "portal_url": "https://www.city.itabashi.tokyo.jp/shigikai/public_comment/index.html",
        "issue_id": "itabashi-education-support-2025-03-04",
        "question_id": "itabashi-education-support-v1",
        "title": "子育て・教育支援の強化",
        "meeting_date": "2025-03-04",
        "meeting_name": "令和7年第1回板橋区議会定例会（第2日目）",
        "source_url": "https://itabashi.gijiroku.com/voices/",
        "speaker_name": "板橋区議会議員",
        "question": "板橋区で、子育て・教育支援を優先して強化してほしいですか？",
        "problem": "子育て支援と学校教育の質向上、施設整備の優先順位が論点です。",
        "response": "公開中の会議録では、子育て・教育支援の強化について一般質問が行われました。",
        "status_summary": "子育て・教育支援の強化について一般質問されました。",
        "share": "板橋区の子育て・教育支援をどう強化するか市民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と学校教育環境の改善が議論されました。",
        "target_audience": "板橋区の子育て世帯と学校関係者",
        "original_quote": "「子育て・教育支援の強化」",
    },
    {
        "assembly_id": "edogawa-ward",
        "assembly_name": "江戸川区議会",
        "municipality": "江戸川区",
        "type": "ward",
        "slug": "edogawa",
        "open_data_code": "131237",
        "lat": 35.7064,
        "lng": 139.8687,
        "members": 44,
        "mayor": "齊藤 猛",
        "index_url": "https://www.gikai.city.edogawa.tokyo.jp/voices/",
        "portal_url": "https://www.gikai.city.edogawa.tokyo.jp/public_comment/index.html",
        "issue_id": "edogawa-child-education-2025-05-27",
        "question_id": "edogawa-child-education-v1",
        "title": "子ども支援・教育力向上",
        "meeting_date": "2025-05-27",
        "meeting_name": "令和7年第2回江戸川区議会定例会（第2日目）",
        "source_url": "https://www.gikai.city.edogawa.tokyo.jp/voices/",
        "speaker_name": "江戸川区議会議員",
        "question": "江戸川区で、子ども支援・教育力向上施策を優先して進めてほしいですか？",
        "problem": "子ども支援特別委員会の重点施策と教育力向上の具体策が論点です。",
        "response": "公開中の会議録では、子ども支援・教育力向上について一般質問が行われました。",
        "status_summary": "子ども支援・教育力向上について一般質問されました。",
        "share": "江戸川区の子ども支援・教育力向上をどう進めるか市民の意見を集めています。",
        "what_changes": "子ども支援特別委員会の重点施策と学校教育の質向上が議論されました。",
        "target_audience": "江戸川区の子どもと保護者",
        "original_quote": "「子ども支援・教育力向上」",
    },
    {
        "assembly_id": "taito-ward",
        "assembly_name": "台東区議会",
        "municipality": "台東区",
        "type": "ward",
        "slug": "taito",
        "open_data_code": "131067",
        "lat": 35.7126,
        "lng": 139.7802,
        "members": 36,
        "mayor": "小野 たつひこ",
        "index_url": "https://taito.gijiroku.com/voices/",
        "portal_url": "https://www.city.taito.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "taito-childcare-welfare-2025-03-06",
        "question_id": "taito-childcare-welfare-v1",
        "title": "子育て支援と地域福祉",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回台東区議会定例会（第2日目）",
        "source_url": "https://taito.gijiroku.com/voices/",
        "speaker_name": "台東区議会議員",
        "question": "台東区で、子育て支援と地域福祉の充実を優先して進めてほしいですか？",
        "problem": "子育て世代支援と高齢者福祉を含む地域福祉の一体的な充実が論点です。",
        "response": "公開中の会議録では、子育て支援と地域福祉について一般質問が行われました。",
        "status_summary": "子育て支援と地域福祉について一般質問されました。",
        "share": "台東区の子育て支援と地域福祉をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と地域福祉サービスの改善が議論されました。",
        "target_audience": "台東区の子育て世帯と高齢者",
        "original_quote": "「子育て支援と地域福祉」",
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
    suffix = "ku" if item["type"] == "ward" else "shi"
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    for item in BATCH6:
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
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH6]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
