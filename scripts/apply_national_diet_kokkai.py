"""Bootstrap national-diet pilot assembly via NDL Kokkai speech API."""

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

DIET = {
    "assembly_id": "national-diet",
    "assembly_name": "国会",
    "municipality": "日本国",
    "type": "national",
    "lat": 35.6759,
    "lng": 139.7449,
    "members": 713,
    "leader": "内閣総理大臣",
    "index_url": "https://kokkai.ndl.go.jp/",
    "portal_url": "https://kokkai.ndl.go.jp/",
    "issue_id": "diet-medical-cost-burden-2025-03-13",
    "question_id": "diet-medical-cost-burden-v1",
    "title": "物価高と医療費負担の見直し",
    "meeting_date": "2025-03-13",
    "meeting_name": "衆議院予算委員会（第20号）",
    "source_url": "https://kokkai.ndl.go.jp/txt/121705261X02020250313/2",
    "speaker_name": "枝野幸男",
    "question": "物価高の中で、高額療養費制度の見直しを優先して進めてほしいですか？",
    "problem": "物価高により医療費負担が増え、高額療養費制度の自己負担上限が実態に追いついていないことが論点です。",
    "response": "国会会議録では、高額療養費制度の見直しと社会保障の持続可能性について質疑が行われました。",
    "status_summary": "物価高と医療費負担の見直しについて国会で質疑されました。",
    "share": "物価高の中での医療費負担をどう見直すか、国民の意見を集めています。",
    "what_changes": "高額療養費制度の見直しと社会保障の負担配分が議論されました。",
    "target_audience": "医療費負担に関心のある国民",
    "original_quote": "「物価高と医療費負担の見直し」",
}

INSERT_BEFORE_FOLLOW = '    "tokyo-app-2026-06-16": {'
INSERT_BEFORE_QUESTION = '    "tokyo-app-one-stop-services-v1": {'
INSERT_BEFORE_ISSUE_STATUS = "  {\n    issueId: 'tokyo-app-2026-06-16',"
INSERT_BEFORE_PORTAL = "  {\n    assemblyId: 'tokyo-metropolitan',"
INSERT_BEFORE_CITIZEN_TS = "  {\n    assemblyId: 'tokyo-metropolitan',"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(path)


def assembly_block() -> dict:
    return {
        "assembly_name": DIET["assembly_name"],
        "source": {
            "provider": "kokkai-ndl",
            "index_url": DIET["index_url"],
            "open_data": {
                "title": "国会会議録検索システム",
                "catalog_url": "https://kokkai.ndl.go.jp/",
                "resource_url": "https://kokkai.ndl.go.jp/api/speech",
                "format": "JSON",
                "license_id": "government-work",
                "license_url": "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0",
                "usage": "国会会議録の発言単位検索と原文URLの確認",
            },
        },
        "records": [],
    }


def record_block() -> dict:
    year, month, day = DIET["meeting_date"].split("-")
    stage_date = f"{year}年{int(month)}月{int(day)}日"
    return {
        "discussion_id": DIET["issue_id"],
        "meeting_date": DIET["meeting_date"],
        "meeting_name": DIET["meeting_name"],
        "source_url": DIET["source_url"],
        "topic": DIET["title"],
        "what_changes": DIET["what_changes"],
        "target_audience": DIET["target_audience"],
        "current_stage": f"{stage_date}の衆議院予算委員会で質疑済み",
        "budget_info": "予算・数値はリンク先の国会会議録原文を参照",
        "original_quote": DIET["original_quote"],
        "publication_status": "published",
        "statements": [
            {
                "statement_id": "diet-2025-03-13-medical-cost-question",
                "speaker_name": DIET["speaker_name"],
                "speaker_role": "衆議院議員",
                "committee_name": "予算委員会",
                "stance_label": "課題提起",
                "summary_quote": f"{DIET['title']}について質疑しました。",
                "full_summary": DIET["problem"],
                "source_excerpt": DIET["original_quote"],
                "question_type": "質疑",
                "avatar_color": "sky",
            }
        ],
    }


def ensure_assembly_records() -> bool:
    dataset = load_json(RECORDS_PATH)
    assembly_id = DIET["assembly_id"]
    added = False
    if assembly_id not in dataset["assemblies"]:
        dataset["assemblies"][assembly_id] = assembly_block()
        added = True
    records = dataset["assemblies"][assembly_id].setdefault("records", [])
    if not any(record.get("discussion_id") == DIET["issue_id"] for record in records):
        records.append(record_block())
        added = True
    dataset["updated_at"] = datetime.now(JST).replace(microsecond=0).isoformat()
    write_json(RECORDS_PATH, dataset)
    return added


def patch_follow_store() -> None:
    path = ROOT / "follow_store.py"
    text = path.read_text(encoding="utf-8")
    if DIET["issue_id"] in text:
        return
    block = f'''    "{DIET["issue_id"]}": {{
        "question_id": "{DIET["question_id"]}",
        "assembly_id": "{DIET["assembly_id"]}",
        "municipality": "{DIET["municipality"]}",
        "title": "{DIET["title"]}",
        "current_status": "国会で質疑済み",
        "status_summary": "{DIET["status_summary"]}",
        "status_updated_at": "{DIET["meeting_date"]}T00:00:00+09:00",
        "status_checked_at": "2026-09-02T23:10:00+09:00",
        "problem_summary": "{DIET["problem"]}",
        "government_response_summary": "{DIET["response"]}",
        "share_summary": "{DIET["share"]}",
        "source_url": "{DIET["source_url"]}",
    }},
'''
    text = text.replace(INSERT_BEFORE_FOLLOW, block + INSERT_BEFORE_FOLLOW, 1)
    path.write_text(text, encoding="utf-8")


def patch_citizen_question_store() -> None:
    path = ROOT / "citizen_question_store.py"
    text = path.read_text(encoding="utf-8")
    if f'"{DIET["question_id"]}"' in text:
        return
    block = f'''    "{DIET["question_id"]}": {{
        "issue_id": "{DIET["issue_id"]}",
        "question": "{DIET["question"]}",
        "answers": [
            {{"id": "prioritize", "label": "優先して進めてほしい"}},
            {{"id": "steady_progress", "label": "慎重に段階的に進めてほしい"}},
            {{"id": "need_more_information", "label": "判断材料が足りない"}},
        ],
        "reasons": [
            {{"id": "resident_need", "label": "生活実感として必要"}},
            {{"id": "implementation", "label": "具体策や財源が気になる"}},
            {{"id": "info_hard_to_find", "label": "情報が分かりにくい"}},
            {{"id": "fiscal_priority", "label": "財源や優先順位が気になる"}},
            {{"id": "no_direct_experience", "label": "直接の利用経験がない"}},
            {{"id": "other", "label": "その他"}},
        ],
        "municipality": "{DIET["municipality"]}",
        "theme": "{DIET["title"]}",
    }},
'''
    text = text.replace(INSERT_BEFORE_QUESTION, block + INSERT_BEFORE_QUESTION, 1)
    path.write_text(text, encoding="utf-8")


def _meeting_label(meeting_date: str) -> str:
    year, month, day = meeting_date.split("-")
    return f"{int(year)}/{int(month)}/{int(day)}｜予算委員会"


def patch_home_page() -> None:
    path = WEB / "app" / "home-page.tsx"
    text = path.read_text(encoding="utf-8")
    if f"id: '{DIET['assembly_id']}'" in text:
        return
    block = f"""  {{
    id: '{DIET["assembly_id"]}',
    name: '{DIET["assembly_name"]}',
    type: 'national',
    lat: {DIET["lat"]},
    lng: {DIET["lng"]},
    membersCount: {DIET["members"]},
    mayorName: '{DIET["leader"]}',
    openDataStatus: 'ready',
    totalMinutesCount: 1,
    featuredDiscussionId: '{DIET["issue_id"]}',
    hotTopic: '{DIET["title"]}',
    mainIssues: [
      {{ theme: 'health', label: '{DIET["title"]}', count: 1 }},
    ],
    sourceUrl: '{DIET["source_url"]}',
    lastMeetingDate: '{_meeting_label(DIET["meeting_date"])}',
    lastUpdatedDate: '2026/09/02',
  }},
"""
    text = text.replace(
        "const TOKYO_ASSEMBLIES: readonly Assembly[] = [\n  {\n    id: 'tokyo-metropolitan',",
        "const TOKYO_ASSEMBLIES: readonly Assembly[] = [\n" + block + "  {\n    id: 'tokyo-metropolitan',",
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_issue_statuses() -> None:
    path = WEB / "app" / "data" / "issueStatuses.ts"
    text = path.read_text(encoding="utf-8")
    if DIET["issue_id"] in text:
        return
    block = f"""  {{
    issueId: '{DIET["issue_id"]}',
    problemSummary: '{DIET["problem"]}',
    governmentResponseSummary: '{DIET["response"]}',
    currentStatus: '国会で質疑済み',
    statusSummary: '{DIET["status_summary"]}',
    statusUpdatedAt: '{DIET["meeting_date"]}T00:00:00+09:00',
    statusCheckedAt: '2026-09-02T23:10:00+09:00',
    sourceUrl: '{DIET["source_url"]}',
  }},
"""
    text = text.replace(INSERT_BEFORE_ISSUE_STATUS, block + INSERT_BEFORE_ISSUE_STATUS, 1)
    path.write_text(text, encoding="utf-8")


def patch_public_comment_portals() -> None:
    path = WEB / "app" / "data" / "publicCommentPortals.ts"
    text = path.read_text(encoding="utf-8")
    if f"assemblyId: '{DIET['assembly_id']}'" in text:
        return
    block = f"""  {{
    assemblyId: '{DIET["assembly_id"]}',
    municipality: '{DIET["municipality"]}',
    portalLabel: '国会会議録検索',
    portalUrl: '{DIET["portal_url"]}',
    guidance: '国会議案や法案に関する意見提出は、所管省庁のパブリックコメント募集ページから行ってください。会議録原文は国会会議録検索システムで確認できます。',
  }},
"""
    text = text.replace(INSERT_BEFORE_PORTAL, block + INSERT_BEFORE_PORTAL, 1)
    path.write_text(text, encoding="utf-8")


def patch_citizen_questions_ts() -> None:
    path = WEB / "app" / "data" / "citizenQuestions.ts"
    text = path.read_text(encoding="utf-8")
    if DIET["issue_id"] in text:
        return
    slug = DIET["question_id"].replace("-v1", "")
    block = f"""  {{
    assemblyId: '{DIET["assembly_id"]}',
    issueId: '{DIET["issue_id"]}',
    questionId: '{DIET["question_id"]}',
    municipality: '{DIET["municipality"]}',
    theme: '{DIET["title"]}',
    question: '{DIET["question"]}',
    statusCheckedAt: '2026/09/02',
    answers: [
      {{ id: 'prioritize', label: '優先して進めてほしい' }},
      {{ id: 'steady_progress', label: '慎重に段階的に進めてほしい' }},
      {{ id: 'need_more_information', label: '判断材料が足りない' }},
    ],
    reasons: [
      {{ id: 'resident_need', label: '生活実感として必要' }},
      {{ id: 'implementation', label: '具体策や財源が気になる' }},
      {{ id: 'info_hard_to_find', label: '情報が分かりにくい' }},
      {{ id: 'fiscal_priority', label: '財源や優先順位が気になる' }},
      {{ id: 'no_direct_experience', label: '直接の利用経験がない' }},
      {{ id: 'other', label: 'その他' }},
    ],
    draft: {{
      templateId: '{slug}-opinion-v1',
      answerStatements: {{
        prioritize: '物価高の中での医療費負担見直しを優先して進めてほしいです。',
        steady_progress: '医療費負担の見直しは、慎重に段階的に進めてほしいです。',
        need_more_information: '高額療養費制度の見直しは、具体策を示してから判断したいです。',
      }},
      reasonClauses: {{
        resident_need: '生活実感として必要なこと',
        implementation: '具体策や財源が気になること',
        info_hard_to_find: '情報が分かりにくいこと',
        fiscal_priority: '財源や優先順位が気になること',
        no_direct_experience: '直接の利用経験がないこと',
        other: 'ほかにも考慮したい点があること',
      }},
    }},
  }},
"""
    text = text.replace(INSERT_BEFORE_CITIZEN_TS, block + INSERT_BEFORE_CITIZEN_TS, 1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    added = ensure_assembly_records()
    patch_follow_store()
    patch_citizen_question_store()
    patch_home_page()
    patch_issue_statuses()
    patch_public_comment_portals()
    patch_citizen_questions_ts()
    print(json.dumps({"added": added, "assembly_id": DIET["assembly_id"]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
