"""Apply batch-2 featured issue metadata across API + web files."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent / "gijiraku-web"

FEATURED = [
    {
        "assembly_id": "chuo-ward",
        "assembly_name": "中央区議会",
        "municipality": "中央区",
        "type": "ward",
        "lat": 35.6706,
        "lng": 139.772,
        "members": 30,
        "mayor": "長谷川 健一",
        "issue_id": "chuo-ward-auto-2023-06-19-109-3-64",
        "question_id": "chuo-afterschool-care-v1",
        "title": "学童保育と預かり場所の確保",
        "hot_topic": "学童保育と預かり場所の確保",
        "meeting_date": "2023-06-19",
        "source_url": "https://ssp.kaigiroku.net/tenant/chuo/SpMinuteView.html?council_id=109&schedule_id=3",
        "portal_url": "https://www.city.chuo.lg.jp/kusei/seisaku/publiccomment/index.html",
        "question": "共働き世帯向けに、いつでも児童を預けられる場所と学童保育を拡充してほしいですか？",
        "problem": "学童保育の待機と、共働き世帯の預かり場所不足が論点です。",
        "response": "公開中の会議録では、学童保育設置と待機児童について質問・答弁が行われました。",
        "status_summary": "学童保育の設置と待機児童への対応について質問・答弁されました。",
        "share": "中央区の学童保育と預かり場所をどう拡充するか市民の意見を集めています。",
    },
    {
        "assembly_id": "kodaira-city",
        "assembly_name": "小平市議会",
        "municipality": "小平市",
        "type": "city",
        "lat": 35.7284,
        "lng": 139.4777,
        "members": 28,
        "mayor": "白石 幸男",
        "issue_id": "kodaira-city-auto-2024-02-26-1458-2-432",
        "question_id": "kodaira-nursery-staff-v1",
        "title": "市立保育園の保育士確保",
        "hot_topic": "市立保育園の保育士確保",
        "meeting_date": "2024-02-26",
        "source_url": "https://ssp.kaigiroku.net/tenant/kodaira/SpMinuteView.html?council_id=1458&schedule_id=2",
        "portal_url": "https://www.city.kodaira.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "question": "小平市の市立保育園で、保育士の確保と安定した保育体制を優先して進めてほしいですか？",
        "problem": "保育需要の増加と保育士確保が論点です。",
        "response": "公開中の会議録では、市立保育園の保育士体制について質問・答弁が行われました。",
        "status_summary": "市立保育園における保育士確保について質問・答弁されました。",
        "share": "小平市の市立保育園で保育士をどう確保するか市民の意見を集めています。",
    },
    {
        "assembly_id": "akishima-city",
        "assembly_name": "昭島市議会",
        "municipality": "昭島市",
        "type": "city",
        "lat": 35.7058,
        "lng": 139.3539,
        "members": 24,
        "mayor": "佐々木 綾子",
        "issue_id": "akishima-city-auto-2024-03-05-2203-10-30",
        "question_id": "akishima-working-parents-v1",
        "title": "子育て世代が働きやすいまち",
        "hot_topic": "子育て世代が働きやすいまち",
        "meeting_date": "2024-03-05",
        "source_url": "https://ssp.kaigiroku.net/tenant/akishima/SpMinuteView.html?council_id=2203&schedule_id=10",
        "portal_url": "https://www.city.akishima.lg.jp/kusei/seisaku/publiccomment/index.html",
        "question": "昭島市で、子育て世代が働きやすい環境づくりを優先して進めてほしいですか？",
        "problem": "若者・子育て世代支援と地域の活力維持が論点です。",
        "response": "公開中の会議録では、子育て世代が働きやすいまちづくりについて質問・答弁が行われました。",
        "status_summary": "子育て世代が働きやすいまちづくりについて質問・答弁されました。",
        "share": "昭島市で子育て世代が働きやすい環境をどう整えるか市民の意見を集めています。",
    },
    {
        "assembly_id": "ome-city",
        "assembly_name": "青梅市議会",
        "municipality": "青梅市",
        "type": "city",
        "lat": 35.7879,
        "lng": 139.2756,
        "members": 24,
        "mayor": "加藤 健一",
        "issue_id": "ome-city-auto-2024-03-05-1269-3-117",
        "question_id": "ome-childcare-environment-v1",
        "title": "人口減少対策と子育て環境",
        "hot_topic": "人口減少対策と子育て環境",
        "meeting_date": "2024-03-05",
        "source_url": "https://ssp.kaigiroku.net/tenant/ome/SpMinuteView.html?council_id=1269&schedule_id=3",
        "portal_url": "https://www.city.ome.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "question": "青梅市で、人口減少対策と子育てしやすい環境づくりを一体的に進めてほしいですか？",
        "problem": "出生数減少と子育てしやすい環境整備が論点です。",
        "response": "公開中の会議録では、人口減少対策と子育て環境づくりについて質問・答弁が行われました。",
        "status_summary": "人口減少対策と子育てしやすい環境づくりについて質問・答弁されました。",
        "share": "青梅市の人口減少対策と子育て環境をどう進めるか市民の意見を集めています。",
    },
    {
        "assembly_id": "higashiyamato-city",
        "assembly_name": "東大和市議会",
        "municipality": "東大和市",
        "type": "city",
        "lat": 35.7454,
        "lng": 139.4266,
        "members": 22,
        "mayor": "岸本 礼子",
        "issue_id": "higashiyamato-city-auto-2024-02-27-33-4-95",
        "question_id": "higashiyamato-family-support-v1",
        "title": "妊産婦や子育て家庭への支援",
        "hot_topic": "妊産婦や子育て家庭への支援",
        "meeting_date": "2024-02-27",
        "source_url": "https://ssp.kaigiroku.net/tenant/higashiyamato/SpMinuteView.html?council_id=33&schedule_id=4",
        "portal_url": "https://www.city.higashiyamato.lg.jp/kusei/seisaku/publiccomment/index.html",
        "question": "東大和市で、妊産婦や子育て家庭への支援を優先して充実させてほしいですか？",
        "problem": "妊産婦・子育て家庭支援と保育体制が論点です。",
        "response": "公開中の会議録では、妊産婦や子育て家庭への支援について質問・答弁が行われました。",
        "status_summary": "妊産婦や子育て家庭への支援について質問・答弁されました。",
        "share": "東大和市の妊産婦・子育て家庭支援をどう充実させるか市民の意見を集めています。",
    },
    {
        "assembly_id": "kiyose-city",
        "assembly_name": "清瀬市議会",
        "municipality": "清瀬市",
        "type": "city",
        "lat": 35.7854,
        "lng": 139.5268,
        "members": 22,
        "mayor": "小久保 令子",
        "issue_id": "kiyose-city-auto-2024-03-06-495-5-5",
        "question_id": "kiyose-disaster-preparedness-v1",
        "title": "清瀬市の防災対策",
        "hot_topic": "清瀬市の防災対策",
        "meeting_date": "2024-03-06",
        "source_url": "https://ssp.kaigiroku.net/tenant/kiyose/SpMinuteView.html?council_id=495&schedule_id=5",
        "portal_url": "https://www.city.kiyose.lg.jp/kusei/seisaku/publiccomment/index.html",
        "question": "能登半島地震の教訓を踏まえ、清瀬市の防災対策を強化してほしいですか？",
        "problem": "大規模災害への備えと地域防災体制が論点です。",
        "response": "公開中の会議録では、清瀬市の防災対策について質問・答弁が行われました。",
        "status_summary": "清瀬市の防災対策について質問・答弁されました。",
        "share": "清瀬市の防災対策をどう強化するか市民の意見を集めています。",
    },
    {
        "assembly_id": "musashimurayama-city",
        "assembly_name": "武蔵村山市議会",
        "municipality": "武蔵村山市",
        "type": "city",
        "lat": 35.754,
        "lng": 139.3874,
        "members": 20,
        "mayor": "成塚 豊",
        "issue_id": "musashimurayama-city-auto-2024-03-01-1250-4-12",
        "question_id": "musashimurayama-elderly-depression-v1",
        "title": "高齢者のうつ病対策",
        "hot_topic": "高齢者のうつ病対策",
        "meeting_date": "2024-03-01",
        "source_url": "https://ssp.kaigiroku.net/tenant/musashimurayama/SpMinuteView.html?council_id=1250&schedule_id=4",
        "portal_url": "https://www.city.musashimurayama.lg.jp/kusei/seisaku/publiccomment/index.html",
        "question": "武蔵村山市で、高齢者のうつ病予防と相談・支援体制を充実させてほしいですか？",
        "problem": "高齢者のメンタルヘルスと予防支援が論点です。",
        "response": "公開中の会議録では、高齢者のうつ病対策について質問・答弁が行われました。",
        "status_summary": "高齢者のうつ病対策について質問・答弁されました。",
        "share": "武蔵村山市の高齢者うつ病対策をどう進めるか市民の意見を集めています。",
    },
]


def patch_catalog_metadata() -> None:
    path = ROOT / "catalog_metadata.py"
    text = path.read_text(encoding="utf-8")
    missing_ids = [item["issue_id"] for item in FEATURED if item["issue_id"] not in text]
    if missing_ids:
        id_lines = "".join(f'    "{issue_id}",\n' for issue_id in missing_ids)
        text = text.replace(
            '    "tachikawa-city-auto-2024-02-27-2629-4-62",\n}',
            f'    "tachikawa-city-auto-2024-02-27-2629-4-62",\n{id_lines}}}',
        )
    missing_titles = [
        item for item in FEATURED if f'"{item["issue_id"]}":' not in text.split("PUBLIC_TITLE_OVERRIDES", 1)[1]
    ]
    if missing_titles:
        title_lines = "".join(
            f'    "{item["issue_id"]}": "{item["title"]}",\n' for item in missing_titles
        )
        text = text.replace(
            '    "tachikawa-city-auto-2024-02-27-2629-4-62": "個別の教育支援計画と個別の指導計画",\n}',
            f'    "tachikawa-city-auto-2024-02-27-2629-4-62": "個別の教育支援計画と個別の指導計画",\n{title_lines}}}',
        )
    path.write_text(text, encoding="utf-8")


def patch_follow_store() -> None:
    path = ROOT / "follow_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in FEATURED:
        if item["issue_id"] in text:
            continue
        blocks.append(
            f'''    "{item["issue_id"]}": {{
        "question_id": "{item["question_id"]}",
        "assembly_id": "{item["assembly_id"]}",
        "municipality": "{item["municipality"]}",
        "title": "{item["title"]}",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "{item["status_summary"]}",
        "status_updated_at": "{item["meeting_date"]}T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "{item["problem"]}",
        "government_response_summary": "{item["response"]}",
        "share_summary": "{item["share"]}",
        "source_url": "{item["source_url"]}",
    }},'''
        )
    if blocks:
        text = text.replace(
            '    "tachikawa-city-auto-2024-02-27-2629-4-62": {',
            "\n".join(blocks) + '\n    "tachikawa-city-auto-2024-02-27-2629-4-62": {',
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_citizen_question_store() -> None:
    path = ROOT / "citizen_question_store.py"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in FEATURED:
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
            '    "tachikawa-education-support-plans-v1": {',
            "\n".join(blocks) + '\n    "tachikawa-education-support-plans-v1": {',
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
    for item in FEATURED:
        if f"id: '{item['assembly_id']}'" in text:
            continue
        issue_theme = "safety" if "防災" in item["title"] else "health" if "高齢" in item["title"] else "child"
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
    totalMinutesCount: 40,
    featuredDiscussionId: '{item["issue_id"]}',
    hotTopic: '{item["hot_topic"]}',
    mainIssues: [
      {{ theme: '{issue_theme}', label: '{item["title"]}', count: 1 }},
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
    for item in FEATURED:
        if item["issue_id"] in text:
            continue
        blocks.append(
            f"""  {{
    issueId: '{item["issue_id"]}',
    problemSummary: '{item["problem"]}',
    governmentResponseSummary: '{item["response"]}',
    currentStatus: '議会で質問・答弁済み',
    statusSummary: '{item["status_summary"]}',
    statusUpdatedAt: '{item["meeting_date"]}T00:00:00+09:00',
    statusCheckedAt: '2026-09-02T15:00:00+09:00',
    sourceUrl: '{item["source_url"]}',
  }},"""
        )
    if blocks:
        text = text.replace(
            "    sourceUrl: 'https://ssp.kaigiroku.net/tenant/tachikawa/SpMinuteView.html?council_id=2629&schedule_id=4',\n  },\n] as const;",
            "    sourceUrl: 'https://ssp.kaigiroku.net/tenant/tachikawa/SpMinuteView.html?council_id=2629&schedule_id=4',\n  },\n"
            + "\n".join(blocks)
            + "\n] as const;",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_public_comment_portals() -> None:
    path = WEB / "app" / "data" / "publicCommentPortals.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in FEATURED:
        if f"assemblyId: '{item['assembly_id']}'" in text:
            continue
        label = f"{item['municipality']} パブリックコメント"
        if item["type"] == "ward":
            label = f"{item['municipality']} 意見公募"
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
    for item in FEATURED:
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


def main() -> None:
    patch_catalog_metadata()
    patch_follow_store()
    patch_citizen_question_store()
    patch_home_page()
    patch_issue_statuses()
    patch_public_comment_portals()
    patch_citizen_questions_ts()
    print(json.dumps([item["assembly_id"] for item in FEATURED], ensure_ascii=False))


if __name__ == "__main__":
    main()
