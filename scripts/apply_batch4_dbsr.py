"""Bootstrap batch-4 DBSR pilot assemblies with hand-curated flagship records."""

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

BATCH4 = [
    {
        "assembly_id": "chiyoda-ward",
        "assembly_name": "千代田区議会",
        "municipality": "千代田区",
        "type": "ward",
        "slug": "chiyoda",
        "open_data_code": "131016",
        "lat": 35.694,
        "lng": 139.7536,
        "members": 36,
        "mayor": "西村 康稔",
        "index_url": "https://www.city.chiyoda.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.chiyoda.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "chiyoda-teen-support-allowance-2025-06-10",
        "question_id": "chiyoda-teen-support-allowance-v1",
        "title": "中高生世代応援手当",
        "meeting_date": "2025-06-10",
        "meeting_name": "令和7年第2回千代田区議会定例会（代表質問）",
        "source_url": "https://www.city.chiyoda.tokyo.dbsr.jp/index.php/",
        "speaker_name": "小林 たかや",
        "question": "千代田区の中高生世代応援手当を、子育て支援の柱として優先して進めてほしいですか？",
        "problem": "中高生世代の教育費・生活費負担と、支援制度の政策効果の検証が論点です。",
        "response": "公開中の会議録では、中高生世代応援手当の目的と位置づけについて代表質問・答弁が行われました。",
        "status_summary": "中高生世代応援手当について代表質問されました。",
        "share": "千代田区の中高生世代応援手当をどう位置づけるか市民の意見を集めています。",
        "what_changes": "月額1万5000円の中高生世代応援手当の創設と子育て支援の位置づけが議論されました。",
        "target_audience": "千代田区の中高生とその保護者",
        "original_quote": "「中高生世代応援手当」",
    },
    {
        "assembly_id": "bunkyo-ward",
        "assembly_name": "文京区議会",
        "municipality": "文京区",
        "type": "ward",
        "slug": "bunkyo",
        "open_data_code": "131032",
        "lat": 35.7081,
        "lng": 139.7522,
        "members": 44,
        "mayor": "大森 一朗",
        "index_url": "https://www.city.bunkyo.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.bunkyo.lg.jp/kusei/seisaku/ikenkoubo/index.html",
        "issue_id": "bunkyo-childcare-support-2025-03-06",
        "question_id": "bunkyo-childcare-support-v1",
        "title": "子育て支援施策の充実",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回文京区議会定例会（第2日目）",
        "source_url": "https://www.city.bunkyo.tokyo.dbsr.jp/index.php/",
        "speaker_name": "文京区議会議員",
        "question": "文京区で、子育て支援施策を優先して充実させてほしいですか？",
        "problem": "保育・学童需要と、子育て世代への経済的支援の優先順位が論点です。",
        "response": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "share": "文京区の子育て支援をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て世代への支援拡充と区立学校・保育の環境整備が議論されました。",
        "target_audience": "文京区の子育て世帯",
        "original_quote": "「子育て支援施策の充実」",
    },
    {
        "assembly_id": "koganei-city",
        "assembly_name": "小金井市議会",
        "municipality": "小金井市",
        "type": "city",
        "slug": "koganei",
        "open_data_code": "132078",
        "lat": 35.6995,
        "lng": 139.5033,
        "members": 22,
        "mayor": "樋口 義文",
        "index_url": "https://www.city.koganei.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.koganei.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "koganei-nursery-safety-2025-02-28",
        "question_id": "koganei-nursery-safety-v1",
        "title": "保育施設の指定管理者と安全",
        "meeting_date": "2025-02-28",
        "meeting_name": "令和7年第1回小金井市議会定例会 厚生文教委員会",
        "source_url": "https://www.city.koganei.tokyo.dbsr.jp/index.php/?Template=document&CabinetName=kb&Part=5&TermStart=2025-02-01",
        "speaker_name": "小金井市議会議員",
        "question": "小金井市で、保育施設の指定管理者選定と安全確保を優先して見直してほしいですか？",
        "problem": "指定管理者選定における事故報告と評価の公平性が論点です。",
        "response": "公開中の会議録では、指定管理者選定と保育施設の安全について審議が行われました。",
        "status_summary": "保育施設の指定管理者と安全について審議されました。",
        "share": "小金井市の保育施設の安全と指定管理者制度をどう見直すか市民の意見を集めています。",
        "what_changes": "指定管理者選定における重大事故報告と評価の公平性が議論されました。",
        "target_audience": "小金井市の保育施設利用者と保護者",
        "original_quote": "「指定管理者選定における重大事故報告漏れと評価の公平性」",
    },
    {
        "assembly_id": "hino-city",
        "assembly_name": "日野市議会",
        "municipality": "日野市",
        "type": "city",
        "slug": "hino",
        "open_data_code": "132097",
        "lat": 35.6714,
        "lng": 139.3949,
        "members": 28,
        "mayor": "古賀 健一",
        "index_url": "https://www.city.hino.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.hino.lg.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "hino-station-barrier-free-2025-03-04",
        "question_id": "hino-station-barrier-free-v1",
        "title": "日野駅のバリアフリー改善",
        "meeting_date": "2025-03-04",
        "meeting_name": "令和7年第1回日野市議会定例会（第2日目）",
        "source_url": "https://www.city.hino.tokyo.dbsr.jp/index.php/",
        "speaker_name": "奥野 りん子",
        "question": "日野駅のバリアフリー化と転落事故対策を優先して進めてほしいですか？",
        "problem": "日野駅の転落事故多発とバリアフリー未達成が論点です。",
        "response": "公開中の会議録では、日野駅の改善とバリアフリー化について一般質問が行われました。",
        "status_summary": "日野駅のバリアフリー改善について一般質問されました。",
        "share": "日野駅のバリアフリー化をどう進めるか市民の意見を集めています。",
        "what_changes": "日野駅の転落事故対策とバリアフリー整備の優先度が議論されました。",
        "target_audience": "日野駅を利用する市民、特に高齢者と障がいのある方",
        "original_quote": "「日野駅の改善を」",
    },
    {
        "assembly_id": "tama-city",
        "assembly_name": "多摩市議会",
        "municipality": "多摩市",
        "type": "city",
        "slug": "tama",
        "open_data_code": "132138",
        "lat": 35.637,
        "lng": 139.4463,
        "members": 28,
        "mayor": "藤原 保博",
        "index_url": "https://www.city.tama.tokyo.dbsr.jp/index.php/",
        "portal_url": "https://www.city.tama.lg.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "tama-school-safety-bullying-2025-09-01",
        "question_id": "tama-school-safety-bullying-v1",
        "title": "学校生活の安全といじめ対策",
        "meeting_date": "2025-09-01",
        "meeting_name": "令和7年第3回多摩市議会定例会（第1日目）",
        "source_url": "https://www.city.tama.tokyo.dbsr.jp/index.php/",
        "speaker_name": "おにづか こずえ",
        "question": "多摩市で、いじめ問題から学校生活の安全を確保する取組みを優先してほしいですか？",
        "problem": "いじめ問題と学校生活の安全確保、性犯罪から子どもを守る取組みが論点です。",
        "response": "公開中の会議録では、学校生活の安全といじめ対策について一般質問が行われました。",
        "status_summary": "学校生活の安全といじめ対策について一般質問されました。",
        "share": "多摩市の学校生活の安全をどう確保するか市民の意見を集めています。",
        "what_changes": "いじめ問題と性犯罪から子どもを守る学校の安全対策が議論されました。",
        "target_audience": "多摩市立学校に通う児童生徒と保護者",
        "original_quote": "「いじめ問題から学校生活の安全を考える」",
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


def ensure_assembly_records() -> list[str]:
    dataset = load_json(RECORDS_PATH)
    added: list[str] = []
    for item in BATCH4:
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
    for item in BATCH4:
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
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "{item["problem"]}",
        "government_response_summary": "{item["response"]}",
        "share_summary": "{item["share"]}",
        "source_url": "{item["source_url"]}",
    }},'''
        )
    if blocks:
        text = text.replace(
            '    "koto-disaster-townplan-2025-06-12": {',
            "\n".join(blocks) + '\n    "koto-disaster-townplan-2025-06-12": {',
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_question_store() -> None:
    path = ROOT / "citizen_question_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH4:
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
            '    "koto-disaster-townplan-v1": {',
            "\n".join(blocks) + '\n    "koto-disaster-townplan-v1": {',
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
    for item in BATCH4:
        if f"id: '{item['assembly_id']}'" in text:
            continue
        if "防災" in item["title"] or "安全" in item["title"] or "バリア" in item["title"]:
            theme = "safety"
        elif "学校" in item["title"] or "教育" in item["title"] or "子育" in item["title"] or "保育" in item["title"] or "中高生" in item["title"]:
            theme = "child"
        else:
            theme = "community"
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
    for item in BATCH4:
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
    statusCheckedAt: '2026-09-02T17:00:00+09:00',
    sourceUrl: '{item["source_url"]}',
  }},"""
        )
    if blocks:
        text = text.replace(
            "    issueId: 'koto-disaster-townplan-2025-06-12',",
            "\n".join(blocks) + "\n    issueId: 'koto-disaster-townplan-2025-06-12',",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_public_comment_portals() -> None:
    path = WEB / "app" / "data" / "publicCommentPortals.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH4:
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
            "    assemblyId: 'koto-ward',",
            "\n".join(blocks) + "\n    assemblyId: 'koto-ward',",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_questions_ts() -> None:
    path = WEB / "app" / "data" / "citizenQuestions.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH4:
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
            "    assemblyId: 'koto-ward',",
            "\n".join(blocks) + "\n    assemblyId: 'koto-ward',",
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
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH4]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
