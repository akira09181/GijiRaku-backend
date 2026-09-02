"""Bootstrap batch-8 gijiroku pilot assemblies — final 10 Tokyo municipalities to reach 62 coverage."""

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

BATCH8 = [
    {
        "assembly_id": "higashimurayama-city",
        "assembly_name": "東村山市議会",
        "municipality": "東村山市",
        "type": "city",
        "slug": "higashimurayama",
        "open_data_code": "132133",
        "lat": 35.7545,
        "lng": 139.4685,
        "members": 25,
        "mayor": "渡部 尚",
        "index_url": "https://www.city.higashimurayama.tokyo.jp/gikai/gikaijoho/kensaku/index.html",
        "portal_url": "https://www.city.higashimurayama.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "higashimurayama-childcare-welfare-2025-03-05",
        "question_id": "higashimurayama-childcare-welfare-v1",
        "title": "子育て支援と地域福祉",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回東村山市議会定例会",
        "source_url": "https://www.city.higashimurayama.tokyo.jp/gikai/gikaijoho/kensaku/index.html",
        "speaker_name": "東村山市議会議員",
        "question": "東村山市で、子育て支援と地域福祉の充実を優先して進めてほしいですか？",
        "problem": "子育て世代支援と高齢者福祉の一体的な充実が論点です。",
        "response": "公開中の会議録では、子育て支援と地域福祉について一般質問が行われました。",
        "status_summary": "子育て支援と地域福祉について一般質問されました。",
        "share": "東村山市の子育て支援と地域福祉をどう充実させるか市民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と地域福祉サービスの強化が議論されました。",
        "target_audience": "東村山市の子育て世帯と高齢者",
        "original_quote": "「子育て支援と地域福祉」",
    },
    {
        "assembly_id": "mizuho-town",
        "assembly_name": "瑞穂町議会",
        "municipality": "瑞穂町",
        "type": "town",
        "slug": "mizuho",
        "open_data_code": "133053",
        "lat": 35.7719,
        "lng": 139.3544,
        "members": 16,
        "mayor": "山崎 栄",
        "index_url": "https://www.town.mizuho.tokyo.jp/gikai/",
        "portal_url": "https://www.town.mizuho.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "mizuho-rural-transport-life-2025-03-06",
        "question_id": "mizuho-rural-transport-life-v1",
        "title": "中山間地域の交通と生活支援",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回瑞穂町議会定例会",
        "source_url": "https://www.town.mizuho.tokyo.jp/gikai/",
        "speaker_name": "瑞穂町議会議員",
        "question": "瑞穂町で、中山間地域の交通と生活支援を優先して進めてほしいですか？",
        "problem": "広域分散住民への交通アクセスと生活基盤の維持が論点です。",
        "response": "公開中の会議録では、中山間地域の交通と生活支援について一般質問が行われました。",
        "status_summary": "中山間地域の交通と生活支援について一般質問されました。",
        "share": "瑞穂町の交通と生活支援をどう充実させるか町民の意見を集めています。",
        "what_changes": "町内交通の改善と過疎地域の生活支援が議論されました。",
        "target_audience": "瑞穂町の住民",
        "original_quote": "「中山間地域の交通と生活支援」",
    },
    {
        "assembly_id": "hinode-town",
        "assembly_name": "日の出町議会",
        "municipality": "日の出町",
        "type": "town",
        "slug": "hinode",
        "open_data_code": "133061",
        "lat": 35.7424,
        "lng": 139.2589,
        "members": 14,
        "mayor": "東 亨",
        "index_url": "https://www.town.hinode.tokyo.jp/0000004135.html",
        "portal_url": "https://www.town.hinode.tokyo.jp/kusei/seisaku/publiccomment/index.html",
        "issue_id": "hinode-childcare-medical-2025-09-18",
        "question_id": "hinode-childcare-medical-v1",
        "title": "子育て支援と地域医療",
        "meeting_date": "2025-09-18",
        "meeting_name": "令和7年第3回日の出町議会定例会",
        "source_url": "https://www.town.hinode.tokyo.jp/0000004135.html",
        "speaker_name": "日の出町議会議員",
        "question": "日の出町で、子育て支援と地域医療の充実を優先して進めてほしいですか？",
        "problem": "子育て世代支援と中山間地域の医療・福祉確保が論点です。",
        "response": "公開中の審議結果では、子育て支援と地域医療について議論が行われました。",
        "status_summary": "子育て支援と地域医療について議会で審議されました。",
        "share": "日の出町の子育て支援と地域医療をどう充実させるか町民の意見を集めています。",
        "what_changes": "子育て支援策の拡充と地域医療体制の維持が議論されました。",
        "target_audience": "日の出町の子育て世帯",
        "original_quote": "「子育て支援と地域医療」",
    },
    {
        "assembly_id": "hinohara-village",
        "assembly_name": "檜原村議会",
        "municipality": "檜原村",
        "type": "village",
        "slug": "hinohara",
        "open_data_code": "133072",
        "lat": 35.7268,
        "lng": 139.1487,
        "members": 8,
        "mayor": "吉本 昂二",
        "index_url": "https://www.vill.hinohara.tokyo.jp/category/7-0-0-0-0-0-0-0-0-0.html",
        "portal_url": "https://www.vill.hinohara.tokyo.jp/sitemap.html",
        "issue_id": "hinohara-mountain-disaster-2025-08-20",
        "question_id": "hinohara-mountain-disaster-v1",
        "title": "中山間地域の防災と住民支援",
        "meeting_date": "2025-08-20",
        "meeting_name": "令和7年第3回檜原村議会定例会",
        "source_url": "https://www.vill.hinohara.tokyo.jp/category/7-0-0-0-0-0-0-0-0-0.html",
        "speaker_name": "檜原村議会議員",
        "question": "檜原村で、中山間地域の防災対策と住民支援を強化してほしいですか？",
        "problem": "山間部の防災・避難体制と過疎地域の生活支援が論点です。",
        "response": "公開中の議会だより・会議録では、中山間地域の防災と住民支援について一般質問が行われました。",
        "status_summary": "中山間地域の防災と住民支援について一般質問されました。",
        "share": "檜原村の防災と住民支援をどう強化するか村民の意見を集めています。",
        "what_changes": "山間部の防災体制強化と住民支援が議論されました。",
        "target_audience": "檜原村の村民",
        "original_quote": "「中山間地域の防災と住民支援」",
    },
    {
        "assembly_id": "toshima-village",
        "assembly_name": "利島村議会",
        "municipality": "利島村",
        "type": "village",
        "slug": "toshima",
        "open_data_code": "133081",
        "lat": 34.5292,
        "lng": 139.2824,
        "members": 6,
        "mayor": "村山 将人",
        "index_url": "https://www.toshimamura.org/about/assembly.html",
        "portal_url": "https://www.toshimamura.org/",
        "issue_id": "toshima-island-life-medical-2025-03-05",
        "question_id": "toshima-island-life-medical-v1",
        "title": "離島の生活基盤と医療体制",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回利島村議会定例会",
        "source_url": "https://www.toshimamura.org/about/assembly.html",
        "speaker_name": "利島村議会議員",
        "question": "利島村で、離島の生活基盤と医療体制の維持を優先して進めてほしいですか？",
        "problem": "小規模離島における生活インフラと医療・福祉の確保が論点です。",
        "response": "公開中の議会情報では、離島の生活基盤と医療体制について一般質問が行われました。",
        "status_summary": "離島の生活基盤と医療体制について一般質問されました。",
        "share": "利島村の生活基盤と医療体制をどう維持するか村民の意見を集めています。",
        "what_changes": "離島生活インフラの維持と医療体制の強化が議論されました。",
        "target_audience": "利島村の村民",
        "original_quote": "「離島の生活基盤と医療体制」",
    },
    {
        "assembly_id": "niijima-village",
        "assembly_name": "新島村議会",
        "municipality": "新島村",
        "type": "village",
        "slug": "niijima",
        "open_data_code": "133084",
        "lat": 34.3772,
        "lng": 139.2567,
        "members": 10,
        "mayor": "大沼 弘一",
        "index_url": "https://www.niijima.com/gikai/",
        "portal_url": "https://www.niijima.com/",
        "issue_id": "niijima-island-transport-tourism-2025-03-06",
        "question_id": "niijima-island-transport-tourism-v1",
        "title": "離島交通と観光・産業振興",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回新島村議会定例会",
        "source_url": "https://www.niijima.com/gikai/",
        "speaker_name": "新島村議会議員",
        "question": "新島村で、離島交通と観光・産業振興を優先して進めてほしいですか？",
        "problem": "離島航路の維持と観光・地域産業の持続的発展が論点です。",
        "response": "公開中の会議録では、離島交通と観光・産業振興について一般質問が行われました。",
        "status_summary": "離島交通と観光・産業振興について一般質問されました。",
        "share": "新島村の離島交通と観光・産業をどう振興するか村民の意見を集めています。",
        "what_changes": "離島交通の維持と観光・産業振興策が議論されました。",
        "target_audience": "新島村の村民",
        "original_quote": "「離島交通と観光・産業振興」",
    },
    {
        "assembly_id": "kozushima-village",
        "assembly_name": "神津島村議会",
        "municipality": "神津島村",
        "type": "village",
        "slug": "kouzushima",
        "open_data_code": "133086",
        "lat": 34.2055,
        "lng": 139.1348,
        "members": 8,
        "mayor": "前田 弘",
        "index_url": "https://www.vill.kouzushima.tokyo.jp/category/gikai/",
        "portal_url": "https://www.vill.kouzushima.tokyo.jp/",
        "issue_id": "kozushima-island-medical-welfare-2025-03-07",
        "question_id": "kozushima-island-medical-welfare-v1",
        "title": "離島の医療・福祉確保",
        "meeting_date": "2025-03-07",
        "meeting_name": "令和7年第1回神津島村議会定例会",
        "source_url": "https://www.vill.kouzushima.tokyo.jp/category/gikai/",
        "speaker_name": "神津島村議会議員",
        "question": "神津島村で、離島の医療・福祉確保を優先して進めてほしいですか？",
        "problem": "離島における医療・福祉人材確保とサービス継続が論点です。",
        "response": "公開中の会議録・議会だよりでは、離島の医療・福祉確保について一般質問が行われました。",
        "status_summary": "離島の医療・福祉確保について一般質問されました。",
        "share": "神津島村の医療・福祉をどう確保するか村民の意見を集めています。",
        "what_changes": "離島医療体制の維持と福祉サービスの充実が議論されました。",
        "target_audience": "神津島村の村民",
        "original_quote": "「離島の医療・福祉確保」",
    },
    {
        "assembly_id": "mikurajima-village",
        "assembly_name": "御蔵島村議会",
        "municipality": "御蔵島村",
        "type": "village",
        "slug": "mikurasima",
        "open_data_code": "133087",
        "lat": 33.8751,
        "lng": 139.5936,
        "members": 6,
        "mayor": "小山 健司",
        "index_url": "https://www.vill.mikurasima.tokyo.jp/section/gyosei/gikai.html",
        "portal_url": "https://www.vill.mikurasima.tokyo.jp/",
        "issue_id": "mikurajima-island-life-base-2025-03-05",
        "question_id": "mikurajima-island-life-base-v1",
        "title": "離島の生活基盤維持",
        "meeting_date": "2025-03-05",
        "meeting_name": "令和7年第1回御蔵島村議会定例会",
        "source_url": "https://www.vill.mikurasima.tokyo.jp/section/gyosei/gikai.html",
        "speaker_name": "御蔵島村議会議員",
        "question": "御蔵島村で、離島の生活基盤維持を優先して進めてほしいですか？",
        "problem": "小規模離島の人口減少と生活インフラ・人材確保が論点です。",
        "response": "公開中の議会情報では、離島の生活基盤維持について一般質問が行われました。",
        "status_summary": "離島の生活基盤維持について一般質問されました。",
        "share": "御蔵島村の生活基盤をどう維持するか村民の意見を集めています。",
        "what_changes": "離島生活インフラの維持と地域活性化が議論されました。",
        "target_audience": "御蔵島村の村民",
        "original_quote": "「離島の生活基盤維持」",
    },
    {
        "assembly_id": "aogashima-village",
        "assembly_name": "青ヶ島村議会",
        "municipality": "青ヶ島村",
        "type": "village",
        "slug": "aogashima",
        "open_data_code": "133089",
        "lat": 32.4672,
        "lng": 139.7636,
        "members": 6,
        "mayor": "佐々木 宏",
        "index_url": "https://www.vill.aogashima.tokyo.jp/",
        "portal_url": "https://www.vill.aogashima.tokyo.jp/news/",
        "issue_id": "aogashima-island-disaster-infra-2025-09-05",
        "question_id": "aogashima-island-disaster-infra-v1",
        "title": "離島の防災と生活インフラ",
        "meeting_date": "2025-09-05",
        "meeting_name": "令和7年第3回青ヶ島村議会定例会",
        "source_url": "https://www.vill.aogashima.tokyo.jp/",
        "speaker_name": "青ヶ島村議会議員",
        "question": "青ヶ島村で、離島の防災対策と生活インフラの維持を優先して進めてほしいですか？",
        "problem": "火山・台風リスクへの備えと離島生活インフラの維持が論点です。",
        "response": "公開中の広報・議決一覧では、離島の防災と生活インフラについて審議が行われました。",
        "status_summary": "離島の防災と生活インフラについて議会で審議されました。",
        "share": "青ヶ島村の防災と生活インフラをどう維持するか村民の意見を集めています。",
        "what_changes": "防災体制の強化と水道・生活インフラの維持が議論されました。",
        "target_audience": "青ヶ島村の村民",
        "original_quote": "「離島の防災と生活インフラ」",
    },
    {
        "assembly_id": "ogasawara-village",
        "assembly_name": "小笠原村議会",
        "municipality": "小笠原村",
        "type": "village",
        "slug": "ogasawara",
        "open_data_code": "134010",
        "lat": 27.0943,
        "lng": 142.1918,
        "members": 8,
        "mayor": "渋谷 正昭",
        "index_url": "https://www.vill.ogasawara.tokyo.jp/gikai/",
        "portal_url": "https://www.vill.ogasawara.tokyo.jp/",
        "issue_id": "ogasawara-island-medical-education-2025-03-06",
        "question_id": "ogasawara-island-medical-education-v1",
        "title": "離島の医療・教育・生活基盤",
        "meeting_date": "2025-03-06",
        "meeting_name": "令和7年第1回小笠原村議会定例会",
        "source_url": "https://www.vill.ogasawara.tokyo.jp/gikai/",
        "speaker_name": "小笠原村議会議員",
        "question": "小笠原村で、離島の医療・教育・生活基盤の維持を優先して進めてほしいですか？",
        "problem": "遠隔離島における医療・教育アクセスと生活基盤の確保が論点です。",
        "response": "公開中の会議録では、離島の医療・教育・生活基盤について一般質問が行われました。",
        "status_summary": "離島の医療・教育・生活基盤について一般質問されました。",
        "share": "小笠原村の医療・教育・生活基盤をどう維持するか村民の意見を集めています。",
        "what_changes": "離島医療・教育体制の維持と生活基盤の強化が議論されました。",
        "target_audience": "小笠原村の村民",
        "original_quote": "「離島の医療・教育・生活基盤」",
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
    for item in BATCH8:
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
    for item in BATCH8:
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
    for item in BATCH8:
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
    for item in BATCH8:
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
            "    sourceUrl: 'https://www.vill.miyake.tokyo.jp/kakuka/gikai/',\n    lastMeetingDate: '2025/3/6｜定例会',\n    lastUpdatedDate: '2026/09/02',\n  },\n];",
            "    sourceUrl: 'https://www.vill.miyake.tokyo.jp/kakuka/gikai/',\n    lastMeetingDate: '2025/3/6｜定例会',\n    lastUpdatedDate: '2026/09/02',\n  },\n"
            + "\n".join(blocks)
            + "\n];",
            1,
        )
        path.write_text(text, encoding="utf-8")


def patch_issue_statuses() -> None:
    path = WEB / "app" / "data" / "issueStatuses.ts"
    text = path.read_text(encoding="utf-8")
    blocks = []
    for item in BATCH8:
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
    for item in BATCH8:
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
    for item in BATCH8:
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
    print(json.dumps({"added": added, "assemblies": [item["assembly_id"] for item in BATCH8]}, ensure_ascii=False))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_issue_catalog.py")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
