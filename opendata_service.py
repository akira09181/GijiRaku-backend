import json
import requests
import pandas as pd
from typing import List, Dict, Any

TOKYO_CATALOG_SEARCH_URL = "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_search?q=%E8%AD%B0%E4%BC%9A&rows=10"

ASSEMBLIES_MASTER: List[Dict[str, Any]] = [
    {
        "id": "tokyo-metropolitan",
        "name": "東京都議会",
        "org_name": "東京都",
        "lat": 35.6895,
        "lng": 139.6917,
        "badge": "都庁・本庁",
        "hot_topic": "デジタルDX・子育て支援・築地再開発",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/gikai/130001_tokyoto_gikaidayori.csv",
        "avatar_theme": "blue"
    },
    {
        "id": "chiyoda-ku",
        "name": "千代田区議会",
        "org_name": "千代田区",
        "lat": 35.6940,
        "lng": 139.7536,
        "badge": "千代田区役所",
        "hot_topic": "皇居周辺環境・高齢者福祉・景観保護",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/chiyoda/131016_chiyodaku_gikaidayori.csv",
        "avatar_theme": "emerald"
    },
    {
        "id": "chuo-ku",
        "name": "中央区議会",
        "org_name": "中央区",
        "lat": 35.6707,
        "lng": 139.7719,
        "badge": "中央区役所",
        "hot_topic": "晴海フラッグ交通・給食無償化・臨海地下鉄",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/chuo/131024_chuoku_gikaidayori.csv",
        "avatar_theme": "indigo"
    },
    {
        "id": "koto-ku",
        "name": "江東区議会",
        "org_name": "江東区",
        "lat": 35.6727,
        "lng": 139.8174,
        "badge": "江東区役所",
        "hot_topic": "防災強化・地下鉄8号線延伸・豊洲スマートシティ",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/koto/131083_kotoku_gikaidayori.csv",
        "avatar_theme": "purple"
    },
    {
        "id": "katsushika-ku",
        "name": "葛飾区議会",
        "org_name": "葛飾区",
        "lat": 35.7432,
        "lng": 139.8472,
        "badge": "葛飾区役所",
        "hot_topic": "下町商店街活性化・水害タイムライン・交通補正",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/katsushika/131229_katsushikaku_gikaidayori.csv",
        "avatar_theme": "amber"
    },
    {
        "id": "ota-ku",
        "name": "大田区議会",
        "org_name": "大田区",
        "lat": 35.5612,
        "lng": 139.7161,
        "badge": "大田区役所",
        "hot_topic": "羽田空港連携・町工場DX・スタートアップ支援",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/ota/131113_otaku_gikaidayori.csv",
        "avatar_theme": "rose"
    },
    {
        "id": "machida-shi",
        "name": "町田市議会",
        "org_name": "町田市",
        "lat": 35.5467,
        "lng": 139.4386,
        "badge": "町田市役所",
        "hot_topic": "モノレール構想・公共交通",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/machida/132098_machidashi_gikaidayori.csv",
        "avatar_theme": "teal"
    },
    {
        "id": "nakano-ku",
        "name": "中野区議会",
        "org_name": "中野区",
        "lat": 35.7074,
        "lng": 139.6638,
        "badge": "中野区役所",
        "hot_topic": "中野サンプラザ跡地再開発・サブカルチャー支援・新庁舎移転",
        "dataset_url": "https://www2.wagmap.jp/nakanodatamap/nakanodatamap/opendatafile/map_1/CSV/opendata_57001289.csv",
        "avatar_theme": "cyan"
    },
    {
        "id": "koganei-shi",
        "name": "小金井市議会",
        "org_name": "小金井市",
        "lat": 35.7008,
        "lng": 139.5033,
        "badge": "小金井市役所",
        "hot_topic": "玉川上水緑地保全・ゴミ完全有料化検証・公園リノベ",
        "dataset_url": "https://www.opendata.metro.tokyo.lg.jp/koganei/132101_gikaidayori.csv",
        "avatar_theme": "green"
    }
]

# 最新定例会（市民投票・賛否データ付き）
CHAT_SAMPLE_DATABASE = {
    "tokyo-metropolitan": [
        {
            "id": "msg-1",
            "date": "2026年8月10日 (第2回定例会)",
            "timestamp": "10:15",
            "category": "💻 デジタル・DX",
            "speaker": "佐藤たかし 議員",
            "role": "都民ファーストの会",
            "avatar_type": "politician_male",
            "plain_text": "【デジタル改革について】都庁の行政手続き、スマホで完結できるように進んでる？ペーパーレス化の進捗を教えて！",
            "original_quote": "「本都における行政手続のデジタル化およびペーパーレス化推進の取り組み状況、並びに都民の利便性向上に向けた今後のロードマップについて伺う。」",
            "agree_count": 84,
            "disagree_count": 12,
            "comments": [
                {"user": "都民Aさん", "text": "役所に行かずにスマホで手続きできるのは本当に助かります！高齢者向けのサポート窓口も残してほしい。"},
                {"user": "子育てママさん", "text": "パスポートや保育園申請の完全オンライン化を早く実現してほしい！"}
            ]
        },
        {
            "id": "msg-2",
            "date": "2026年8月10日 (第2回定例会)",
            "timestamp": "10:18",
            "category": "💻 デジタル・DX",
            "speaker": "小池百合子 知事",
            "role": "答弁者 (東京都知事)",
            "avatar_type": "governor_female",
            "plain_text": "【要するに：今年度中に主要手続きの95%をオンライン化完了します！】\n都庁のパスポート申請や各種給付金の手続きはスマホ対応を急ピッチで完了させます！紙を無くして『待ち時間ゼロ』を実現します！",
            "original_quote": "「都民の皆様が役所に来ずとも完結する『デジタル都庁』の実現に向け、本年度末までに主要行政手続の95%以上をキャッシュレスおよびオンライン対応へ移行すべく全力で取り組んでおります。」",
            "agree_count": 142,
            "disagree_count": 18,
            "comments": [
                {"user": "IT系会社員", "text": "95%オンライン化は素晴らしい数値目標！期待しています。"}
            ]
        },
        {
            "id": "msg-3",
            "date": "2026年8月10日 (第2回定例会)",
            "timestamp": "10:30",
            "category": "👶 子育て・教育",
            "speaker": "鈴木えみ 議員",
            "role": "公明党",
            "avatar_type": "politician_female",
            "plain_text": "【子育て・給食助成】小中学校の給食費完全無償化と、任意ワクチンの助成範囲をもっと広げられないの？",
            "original_quote": "「子育て世代への経済的支援の抜本的強化として、都内小中学校の学校給食費全額公費負担化および任意予防接種への都独自助成の制度化を強く要望する。」",
            "agree_count": 185,
            "disagree_count": 15,
            "comments": [
                {"user": "2児の父", "text": "物価高で毎月の給食費負担が重かったので完全無償化は超ありがたい！"}
            ]
        },
        {
            "id": "msg-4",
            "date": "2026年8月10日 (第2回定例会)",
            "timestamp": "10:35",
            "category": "👶 子育て・教育",
            "speaker": "福祉保健局長",
            "role": "答弁者 (局長)",
            "avatar_type": "bureaucrat_male",
            "plain_text": "【要するに：区市町村へ半額補助を行い、全域での無償化を全面バックアップします！】\n都として区市町村の給食費助成を支援する予算を計上し、子育て負担の軽減を図っています。",
            "original_quote": "「学校給食費の無償化につきましては、区市町村への財政支援制度を創設し、都内全域での実施に向け全面的にバックアップしてまいります。」",
            "agree_count": 160,
            "disagree_count": 9,
            "comments": []
        }
    ],
    "chuo-ku": [
        {
            "id": "msg-ck-1",
            "date": "2026年8月9日 (第2回定例会)",
            "timestamp": "13:05",
            "category": "👶 子育て・教育",
            "speaker": "田中広一 議員",
            "role": "中央区議会公明党",
            "avatar_type": "politician_male",
            "plain_text": "【子育て支援】分かりやすい広報や、おむつ替え・授乳コーナーの整備、任意接種ワクチンへの助成をお願いしたい！",
            "original_quote": "「子育て支援策について分かりやすい広報や、おむつ替え・授乳コーナーの整備、小児用肺炎球菌ワクチン等の任意接種への公費助成を求める。」",
            "agree_count": 92,
            "disagree_count": 5,
            "comments": [
                {"user": "晴海在住ママ", "text": "勝どき・晴海エリアは授乳室が混むので商業施設への拡大をぜひ実現してください！"}
            ]
        },
        {
            "id": "msg-ck-2",
            "date": "2026年8月9日 (第2回定例会)",
            "timestamp": "13:10",
            "category": "👶 子育て・教育",
            "speaker": "山本区長",
            "role": "答弁者 (中央区長)",
            "avatar_type": "mayor_male",
            "plain_text": "【要するに：授乳室は民間に働きかけて増やします！ワクチン助成も流通を見極めて進めます】\n授乳コーナーは区の施設だけでなく商業施設にも拡大します。ワクチン無料化も前向きに対応します！",
            "agree_count": 115,
            "disagree_count": 8,
            "comments": []
        }
    ]
}

PAST_HISTORICAL_SESSIONS = [
    {
        "date": "2025年12月15日 (令和7年第4回定例会)",
        "items": [
            {
                "id": "past-2025-1",
                "date": "2025年12月15日 (令和7年第4回定例会)",
                "timestamp": "11:00",
                "category": "👶 子育て・教育",
                "speaker": "野口まゆみ 議員",
                "role": "無所属",
                "avatar_type": "politician_female",
                "plain_text": "【病児保育の拡充】共働き世帯からの切実な声！急な発熱時の病児・病後児保育の受け入れ枠は拡大できる？",
                "original_quote": "「病児・病後児保育事業における広域利用協定の促進並びに予約システムのオンライン化について伺う。」",
                "agree_count": 78,
                "disagree_count": 4,
                "comments": []
            }
        ]
    }
]

def fetch_tokyo_catalog_datasets() -> List[Dict[str, Any]]:
    try:
        res = requests.get(TOKYO_CATALOG_SEARCH_URL, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("result", {}).get("results", [])
            output = []
            for item in results:
                title = item.get("title", "")
                org = item.get("organization", {}).get("title", "")
                resources = item.get("resources", [])
                csv_resources = [r for r in resources if "CSV" in r.get("format", "").upper()]
                output.append({
                    "title": title,
                    "organization": org,
                    "csv_urls": [r.get("url") for r in csv_resources]
                })
            return output
    except Exception as e:
        print(f"カタログAPI取得スキップ: {e}")
    return []

def get_all_assemblies() -> List[Dict[str, Any]]:
    return ASSEMBLIES_MASTER

def get_assembly_chat_dialogue(assembly_id: str, page: int = 1) -> List[Dict[str, Any]]:
    base_messages = CHAT_SAMPLE_DATABASE.get(assembly_id, [])
    if not base_messages:
        assembly_info = next((a for a in ASSEMBLIES_MASTER if a["id"] == assembly_id), None)
        name = assembly_info["name"] if assembly_info else "自治体議会"
        base_messages = [
            {
                "id": f"msg-{assembly_id}-1",
                "date": "2026年8月8日 (第2回定例会)",
                "timestamp": "10:00",
                "category": "👶 子育て・教育",
                "speaker": "山田たろう 議員",
                "role": "市民の会",
                "avatar_type": "politician_male",
                "plain_text": f"【{name}質問】学校給食の全額無償化と、学童保育の待機児童ゼロに向けた進捗を教えてください！",
                "original_quote": f"「{name}における小中学校給食費の無償化推進並びに放課後児童健全育成事業の待機児童解消策について伺う。」",
                "agree_count": 65,
                "disagree_count": 3,
                "comments": []
            }
        ]
    
    result = list(base_messages)
    if page >= 2:
        for idx in range(min(page - 1, len(PAST_HISTORICAL_SESSIONS))):
            past_session = PAST_HISTORICAL_SESSIONS[idx]
            result = past_session["items"] + result

    return result

def record_user_opinion(assembly_id: str, message_id: str, opinion_type: str, comment_text: str = None) -> Dict[str, Any]:
    """市民の投票（賛成/懸念）およびコメント意見投稿を記録"""
    messages = CHAT_SAMPLE_DATABASE.get(assembly_id, [])
    target_msg = next((m for m in messages if m["id"] == message_id), None)
    
    if target_msg:
        if opinion_type == "agree":
            target_msg["agree_count"] = target_msg.get("agree_count", 0) + 1
        elif opinion_type == "disagree":
            target_msg["disagree_count"] = target_msg.get("disagree_count", 0) + 1
            
        if comment_text and comment_text.strip():
            if "comments" not in target_msg:
                target_msg["comments"] = []
            target_msg["comments"].append({
                "user": "市民ユーザー",
                "text": comment_text.strip()
            })
        return {"status": "success", "message": target_msg}
    
    return {"status": "error", "reason": "Message not found"}
