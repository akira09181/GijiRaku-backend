from typing import Dict, Any, List

def get_assembly_analytics(assembly_id: str) -> Dict[str, Any]:
    """議会ごとの政党別テーマ注力度・議員発言スコアリング分析・議員向けEBPM民意データを生成"""
    
    # 議会ごとのテーマ構成比
    topic_distribution = [
        {"name": "👶 おむつ代補助・給食費無償化", "ratio": 32, "color": "#06C755"},
        {"name": "💻 スマホ行政手続95%化", "ratio": 24, "color": "#3B82F6"},
        {"name": "🏗️ 街づくり・多摩モノレール", "ratio": 20, "color": "#F59E0B"},
        {"name": "🛡️ 防災・避難所Wi-Fi", "ratio": 14, "color": "#EF4444"},
        {"name": "🏥 医療・病児保育予約", "ratio": 10, "color": "#EC4899"},
    ]

    # 議員・行政向けEBPM民意分析データ (B2Gマネタイズ用)
    ebpm_citizen_data = {
        "youth_uninterested_rate": 84.8,  # オープンデータ（町田市意識調査）の数値
        "total_votes_recorded": 1420,
        "age_demographics": [
            {"group": "10代・20代 (若者)", "support_ratio": 91, "top_issue": "おむつ代補助電子クーポン・給食ゼロ"},
            {"group": "30代 (子育て層)", "support_ratio": 88, "top_issue": "病児保育当日スマホ予約・学童枠拡大"},
            {"group": "40代・50代 (現役層)", "support_ratio": 82, "top_issue": "多摩モノレール町田延伸・無電柱化"},
            {"group": "60代以上 (シニア層)", "support_ratio": 79, "top_issue": "対面サポート窓口併設・エアコン補助"}
        ],
        "ebpm_ai_recommendations": [
            {
                "rank": 1,
                "title": "若者・子育て世代の89%が賛同: 『紙おむつデジタルクーポン支給』",
                "action": "次回定例会にてスマホアプリ決済による電子クーポン予算枠の拡大提言を推奨。"
            },
            {
                "rank": 2,
                "title": "20代〜30代の84%が要望: 『病児保育の即時LINE予約システム統一』",
                "action": "広域利用協定の早期締結および予約システム共通化を行政側へ要望することを推奨。"
            }
        ]
    }

    # 政党ごとの注力テーマ分析
    party_analytics = [
        {
            "party_name": "町田市民の会 / 都民ファースト",
            "members_count": 31,
            "top_category": "👶 おむつ代補助・給食費無償化",
            "ai_stance_summary": "0歳〜2歳児へ『年間最大3万円のおむつ電子クーポン』および都内小中学校給食費全額公費負担を最優先で推進。",
            "category_breakdown": [
                {"category": "おむつ・子育て", "percent": 50},
                {"category": "デジタルDX", "percent": 30},
                {"category": "街づくり", "percent": 20},
            ]
        },
        {
            "party_name": "自由民主党",
            "members_count": 29,
            "top_category": "🏗️ 多摩モノレール延伸・都市整備",
            "ai_stance_summary": "多摩都市モノレール町田延伸手続き・道路無電柱化・築地スタジアムMICEなど大型インフラ投資を強力推進。",
            "category_breakdown": [
                {"category": "モノレール・街づくり", "percent": 55},
                {"category": "経済・産業", "percent": 25},
                {"category": "防災", "percent": 20},
            ]
        },
        {
            "party_name": "公明党",
            "members_count": 23,
            "top_category": "👶 給食費全額無償化・授乳室拡大",
            "ai_stance_summary": "小中学校の給食費全額無償化・商業施設への授乳室設置支援・任意予防接種全域助成に集中。",
            "category_breakdown": [
                {"category": "給食無償化・子育て", "percent": 60},
                {"category": "医療福祉", "percent": 25},
                {"category": "デジタル", "percent": 15},
            ]
        }
    ]

    # 議員個別スコアリング
    member_scorecards = [
        {
            "id": "mem-mc-1",
            "name": "高橋 りえ",
            "title": "市議会議員",
            "party": "町田市民の会",
            "avatar_type": "politician_female",
            "total_statements": 38,
            "activity_score": 96,
            "main_focus": "おむつ代補助・乳幼児電子クーポン",
            "ai_eval": "物価高に悩む子育て世代の切実な声を取り上げ、おむつ代の具体的な電子クーポン（3万円分）支給を市長から引き出す高い答弁引き出し力を発揮。"
        },
        {
            "id": "mem-1",
            "name": "小池 百合子",
            "title": "東京都知事",
            "party": "執行部 (都知事)",
            "avatar_type": "governor_female",
            "total_statements": 48,
            "activity_score": 98,
            "main_focus": "スマホ行政手続95%化・デジタル都庁",
            "ai_eval": "「待ち時間ゼロの行政」を掲げ、全庁的なデジタルシフトを強力にリード。具体数値（95%）を明示して答弁。"
        }
    ]

    return {
        "assembly_id": assembly_id,
        "topic_distribution": topic_distribution,
        "ebpm_citizen_data": ebpm_citizen_data,
        "party_analytics": party_analytics,
        "member_scorecards": member_scorecards
    }
