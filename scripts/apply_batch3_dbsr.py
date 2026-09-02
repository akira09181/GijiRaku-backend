"""Bootstrap batch-3 DBSR pilot assemblies with hand-curated flagship records."""

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

BATCH3 = [
    {
        "assembly_id": "koto-ward",
        "assembly_name": "江東区議会",
        "municipality": "江東区",
        "type": "ward",
        "slug": "koto",
        "open_data_code": "131083",
        "lat": 35.6731,
        "lng": 139.817,
        "members": 44,
        "mayor": "石川 雅",
        "index_url": "https://www.city.koto.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.koto.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "koto-disaster-townplan-2025-06-12",
        "question_id": "koto-disaster-townplan-v1",
        "title": "防災・まちづくり対策の強化",
        "meeting_date": "2025-06-12",
        "meeting_name": "令和7年第2回江東区議会定例会（第2日目）",
        "source_url": "https://www.city.koto.tokyo.dbsr.jp/index.php/",
        "speaker_name": "江東区議会議員",
        "question": "能登半島地震の教訓を踏まえ、江東区の防災・まちづくり対策を強化してほしいですか？",
        "problem": "大規模災害への備えと臨海部を含む地域防災体制が論点です。",
        "response": "公開中の会議録では、防災・まちづくり対策特別委員会等で防災施策が審議されました。",
        "status_summary": "防災・まちづくり対策について本会議で質問されました。",
        "share": "江東区の防災・まちづくり対策をどう強化するか市民の意見を集めています。",
        "what_changes": "臨海部の防災体制と地域のまちづくりを一体的に進める必要性が議論されました。",
        "target_audience": "江東区の住民、特に臨海部・高層集住宅地域の住民",
        "original_quote": "「防災・まちづくり対策特別委員会」",
    },
    {
        "assembly_id": "musashino-city",
        "assembly_name": "武蔵野市議会",
        "municipality": "武蔵野市",
        "type": "city",
        "slug": "musashino",
        "open_data_code": "132044",
        "lat": 35.7178,
        "lng": 139.5661,
        "members": 26,
        "mayor": "藤井 直幸",
        "index_url": "https://www.city.musashino.tokyo.dbsr.jp/",
        "portal_url": "https://www.city.musashino.lg.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "musashino-school-rebuild-2025-12-04",
        "question_id": "musashino-school-rebuild-v1",
        "title": "学校改築と小・中学校の適正規模",
        "meeting_date": "2025-12-04",
        "meeting_name": "令和7年第4回武蔵野市議会定例会（第2日目）",
        "source_url": "https://www.city.musashino.tokyo.dbsr.jp/",
        "speaker_name": "菅 源太郎",
        "question": "武蔵野市で、学校改築と小・中学校の適正規模を踏まえた教育環境整備を進めてほしいですか？",
        "problem": "老朽化校舎の改築と適正規模化、仮設校舎期間中の課題が論点です。",
        "response": "公開中の会議録では、学校改築と小・中学校の適正規模について一般質問が行われました。",
        "status_summary": "学校改築と適正規模について一般質問されました。",
        "share": "武蔵野市の学校改築と適正規模をどう進めるか市民の意見を集めています。",
        "what_changes": "学校施設の改築計画と小・中学校の適正規模化が議論されました。",
        "target_audience": "武蔵野市立学校に通う児童生徒と保護者",
        "original_quote": "「学校改築と小・中学校の適正規模等について」",
    },
    {
        "assembly_id": "fuchu-city",
        "assembly_name": "府中市議会",
        "municipality": "府中市",
        "type": "city",
        "slug": "fuchu",
        "open_data_code": "132062",
        "lat": 35.6689,
        "lng": 139.4777,
        "members": 28,
        "mayor": "小柳 敏文",
        "index_url": "https://www.city.fuchu.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.fuchu.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "fuchu-base-redevelopment-2025-09-03",
        "question_id": "fuchu-base-redevelopment-v1",
        "title": "府中基地跡地の活用",
        "meeting_date": "2025-09-03",
        "meeting_name": "令和7年第3回府中市議会定例会（第2日目）",
        "source_url": "https://www.city.fuchu.tokyo.dbsr.jp/index.php/",
        "speaker_name": "府中市議会議員",
        "question": "府中基地跡地を、市民にとって使いやすい公共施設やまちづくりに活用してほしいですか？",
        "problem": "基地跡地の解体工事と今後の土地利用、市民への説明が論点です。",
        "response": "公開中の会議録では、府中基地跡地の今後の予定について一般質問が行われました。",
        "status_summary": "府中基地跡地の活用について一般質問されました。",
        "share": "府中基地跡地をどう活用するか市民の意見を集めています。",
        "what_changes": "府中基地跡地の解体後の土地利用と市民への開放が議論されました。",
        "target_audience": "府中市の住民、特に基地跡地周辺の住民",
        "original_quote": "「府中基地跡地の今後の予定」",
    },
    {
        "assembly_id": "mitaka-city",
        "assembly_name": "三鷹市議会",
        "municipality": "三鷹市",
        "type": "city",
        "slug": "mitaka",
        "open_data_code": "132039",
        "lat": 35.6835,
        "lng": 139.5596,
        "members": 28,
        "mayor": "河村 孝",
        "index_url": "https://www.city.mitaka.tokyo.dbsr.jp/",
        "portal_url": "https://www.city.mitaka.lg.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "mitaka-inclusive-disaster-2024-02-27",
        "question_id": "mitaka-inclusive-disaster-v1",
        "title": "インクルーシブ防災の徹底",
        "meeting_date": "2024-02-27",
        "meeting_name": "令和6年第1回三鷹市議会定例会（第2日目）",
        "source_url": "https://www.gikai.city.mitaka.tokyo.jp/reference/2024/custom1/no4_text.html",
        "speaker_name": "石井 れいこ",
        "question": "三鷹市で、高齢者や障がいのある方を取り残さないインクルーシブ防災を徹底してほしいですか？",
        "problem": "福祉避難所の整備と、誰一人取り残さない防災体制が論点です。",
        "response": "公開中の会議録では、インクルーシブ防災について一般質問が行われました。",
        "status_summary": "インクルーシブ防災の徹底について一般質問されました。",
        "share": "三鷹市のインクルーシブ防災をどう進めるか市民の意見を集めています。",
        "what_changes": "高齢者・障がい者を含む福祉避難所体制と防災対策が議論されました。",
        "target_audience": "三鷹市の住民、特に要支援者とその家族",
        "original_quote": "「誰一人取り残さない命を守るインクルーシブ防災の徹底を」",
    },
    {
        "assembly_id": "kokubunji-city",
        "assembly_name": "国分寺市議会",
        "municipality": "国分寺市",
        "type": "city",
        "slug": "kokubunji",
        "open_data_code": "132109",
        "lat": 35.7103,
        "lng": 139.4622,
        "members": 22,
        "mayor": "堀内 伸",
        "index_url": "https://www.city.kokubunji.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.kokubunji.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "kokubunji-peace-education-2025-02-28",
        "question_id": "kokubunji-peace-education-v1",
        "title": "平和教育と校外学習の中立性",
        "meeting_date": "2025-02-28",
        "meeting_name": "令和7年第1回国分寺市議会定例会",
        "source_url": "https://www.city.kokubunji.tokyo.dbsr.jp/index.php/",
        "speaker_name": "国分寺市議会議員",
        "question": "国分寺市で、公立中学校の平和教育と校外学習の政治的中立性・安全確保を求めてほしいですか？",
        "problem": "校外学習の内容と学校施設のイベント利用の公平性が論点です。",
        "response": "公開中の会議録では、平和教育と校外学習の在り方について陳情・審議が行われました。",
        "status_summary": "平和教育と校外学習の政治的中立性について審議されました。",
        "share": "国分寺市の平和教育と校外学習をどう進めるか市民の意見を集めています。",
        "what_changes": "中学校における平和教育と校外学習の政治的中立性が議論されました。",
        "target_audience": "国分寺市立中学校に通う児童生徒と保護者",
        "original_quote": "「公立中学校における平和教育及び校外学習の政治的中立性と安全確保を求める陳情書」",
    },
]


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(path)


def assembly_block(item: dict) -> dict:
    code = item["open_data_code"]
    slug = item["slug"]
    return {
        "assembly_name": item["assembly_name"],
        "source": {
            "provider": "dbsr",
            "index_url": item["index_url"],
            "open_data": {
                "title": "議会だより",
                "catalog_url": f"https://catalog.data.metro.tokyo.lg.jp/dataset/t{code}d2024000001",
                "resource_url": f"https://www.opendata.metro.tokyo.lg.jp/{slug}/{code}_kotoku_gikaidayori.csv"
                if item["assembly_id"] == "koto-ward"
                else f"https://www.opendata.metro.tokyo.lg.jp/{slug}/{code}_{slug}shi_gikaidayori.csv",
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


def ensure_assembly_records() -> list[str]:
    dataset = load_json(RECORDS_PATH)
    added: list[str] = []
    for item in BATCH3:
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
    for item in BATCH3:
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
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "{item["problem"]}",
        "government_response_summary": "{item["response"]}",
        "share_summary": "{item["share"]}",
        "source_url": "{item["source_url"]}",
    }},'''
        )
    if blocks:
        text = text.replace(
            '    "musashimurayama-city-auto-2024-03-01-1250-4-12": {',
            "\n".join(blocks) + '\n    "musashimurayama-city-auto-2024-03-01-1250-4-12": {',
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_question_store() -> None:
    path = ROOT / "citizen_question_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH3:
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
            '    "musashimurayama-elderly-depression-v1": {',
            "\n".join(blocks) + '\n    "musashimurayama-elderly-depression-v1": {',
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
    for item in BATCH3:
        if f"id: '{item['assembly_id']}'" in text:
            continue
        theme = "safety" if "防災" in item["title"] else "child" if "学校" in item["title"] or "教育" in item["title"] else "housing"
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
    for item in BATCH3:
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
    statusCheckedAt: '2026-09-02T16:00:00+09:00',
    sourceUrl: '{item["source_url"]}',
  }},"""
        )
    if blocks:
        text = text.replace(
            "    sourceUrl: 'https://ssp.kaigiroku.net/tenant/musashimurayama/SpMinuteView.html?council_id=1250&schedule_id=4',\n  },\n] as const;",
            "    sourceUrl: 'https://ssp.kaigiroku.net/tenant/musashimurayama/SpMinuteView.html?council_id=1250&schedule_id=4',\n  },\n"
            + "\n".join(blocks)
            + "\n] as const;",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_public_comment_portals() -> None:
    path = WEB / "app" / "data" / "publicCommentPortals.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH3:
        if f"assemblyId: '{item['assembly_id']}'" in text:
            continue
        label = f"{item['municipality']} 意見公募" if item["type"] == "ward" else f"{item['municipality']} パブリックコメント"
        guidance = (
            "区の意見公募ページから、該当するテーマを選んで意見を送ってください。"
            if item["type"] == "ward"
            else "市のパブリックコメントページで、該当する募集を選んで意見を提出してください。"
        )
        blocks.append(
            f"""  {{
    assemblyId: '{item["assembly_id"]}',
    municipality: '{item["municipality"]}',
    portalLabel: '{label}',
    portalUrl: '{item["portal_url"]}',
    guidance: '{guidance}',
  }},"""
        )
    if blocks:
        text = text.replace(
            "    guidance: '市のパブリックコメントページで、該当する募集を選んで意見を提出してください。',\n  },\n] as const;",
            "    guidance: '市のパブリックコメントページで、該当する募集を選んで意見を提出してください。',\n  },\n"
            + "\n".join(blocks)
            + "\n] as const;",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_questions_ts() -> None:
    path = WEB / "app" / "data" / "citizenQuestions.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH3:
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
            "      },\n    },\n  },\n] as const;\n\nexport const SHINJUKU_SICK_CHILD_CARE_QUESTION",
            "      },\n    },\n  },\n"
            + "\n".join(blocks)
            + "\n] as const;\n\nexport const SHINJUKU_SICK_CHILD_CARE_QUESTION",
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
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH3]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
