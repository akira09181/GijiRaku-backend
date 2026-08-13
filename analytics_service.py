from typing import Dict, Any, List

def get_assembly_analytics(assembly_id: str) -> Dict[str, Any]:
    """議会ごとの政党別テーマ注力度・議員発言スコアリング分析データを生成"""
    
    # 議会ごとのテーマ構成比
    topic_distribution = [
        {"name": "👶 子育て・教育", "ratio": 28, "color": "#06C755"},
        {"name": "💻 デジタル・行政DX", "ratio": 24, "color": "#3B82F6"},
        {"name": "🏗️ 街づくり・交通", "ratio": 20, "color": "#F59E0B"},
        {"name": "🛡️ 防災・安全対策", "ratio": 16, "color": "#EF4444"},
        {"name": "🏥 医療・高齢者福祉", "ratio": 12, "color": "#EC4899"},
    ]

    # 政党ごとの注力テーマ分析
    party_analytics = [
        {
            "party_name": "都民ファーストの会",
            "members_count": 31,
            "top_category": "💻 デジタル・行政DX",
            "ai_stance_summary": "都庁手続きの100%オンライン化・キャッシュレス決済およびペーパーレス化を最優先で強力推進。",
            "category_breakdown": [
                {"category": "デジタルDX", "percent": 45},
                {"category": "街づくり", "percent": 30},
                {"category": "子育て", "percent": 25},
            ]
        },
        {
            "party_name": "自由民主党",
            "members_count": 29,
            "top_category": "🏗️ 街づくり・都市再開発",
            "ai_stance_summary": "築地跡地スタジアムMICE整備・首都高地下化・道路インファ不燃化など大型インフラ投資を推進。",
            "category_breakdown": [
                {"category": "街づくり", "percent": 50},
                {"category": "経済・産業", "percent": 30},
                {"category": "防災", "percent": 20},
            ]
        },
        {
            "party_name": "公明党",
            "members_count": 23,
            "top_category": "👶 給食無償化・子育て支援",
            "ai_stance_summary": "小中学校の給食費全額公費負担・任意予防接種全域助成・授乳室拡充など生活密着支援に集中。",
            "category_breakdown": [
                {"category": "子育て教育", "percent": 55},
                {"category": "医療福祉", "percent": 25},
                {"category": "デジタル", "percent": 20},
            ]
        },
        {
            "party_name": "日本共産党",
            "members_count": 19,
            "top_category": "🏥 医療福祉・エアコン助成",
            "ai_stance_summary": "猛暑対策の高齢者エアコン購入・設置緊急補助金や、生活困窮者支援・平和文化事業を主張。",
            "category_breakdown": [
                {"category": "医療福祉", "percent": 45},
                {"category": "猛暑対策", "percent": 35},
                {"category": "教育", "percent": 20},
            ]
        },
        {
            "party_name": "立憲民主党",
            "members_count": 15,
            "top_category": "🛡️ 木密不燃化・避難所Wi-Fi",
            "ai_stance_summary": "首都直下地震を見据えた避難所通信インフラ（スターリンク）配備と木造密集地域の防災強化を提言。",
            "category_breakdown": [
                {"category": "防災安全", "percent": 40},
                {"category": "子育て", "percent": 35},
                {"category": "デジタル", "percent": 25},
            ]
        }
    ]

    # 議員個別スコアリング＆プロファイル
    member_scorecards = [
        {
            "id": "mem-1",
            "name": "小池 百合子",
            "title": "東京都知事",
            "party": "執行部 (都知事)",
            "avatar_type": "governor_female",
            "total_statements": 48,
            "activity_score": 98,
            "main_focus": "デジタル都庁・主要手続95%オンライン化",
            "ai_eval": "「待ち時間ゼロの行政」を掲げ、全庁的なデジタルシフトを強力にリード。具体的な達成数値（95%）を明示して答弁する姿勢が高評価。"
        },
        {
            "id": "mem-2",
            "name": "佐藤 たかし",
            "title": "都議会議員",
            "party": "都民ファーストの会",
            "avatar_type": "politician_male",
            "total_statements": 34,
            "activity_score": 92,
            "main_focus": "ペーパーレス化・スマホ申請完結",
            "ai_eval": "行政手続のスマホ完結や電子申請の進捗について定期的に質疑。市民利便性向上にフォーカスした提言が多い。"
        },
        {
            "id": "mem-3",
            "name": "鈴木 えみ",
            "title": "都議会議員",
            "party": "公明党",
            "avatar_type": "politician_female",
            "total_statements": 39,
            "activity_score": 95,
            "main_focus": "給食費無償化・小児ワクチン全域助成",
            "ai_eval": "子育て世代の家計負担軽減を最優先とし、給食費無償化および予防接種助成の予算拡充を粘り強く要望。"
        },
        {
            "id": "mem-4",
            "name": "高橋 けんじ",
            "title": "都議会議員",
            "party": "自由民主党",
            "avatar_type": "politician_male",
            "total_statements": 31,
            "activity_score": 88,
            "main_focus": "築地再開発・5万人スタジアムMICE",
            "ai_eval": "東京の国際競争力強化と経済活性化に向け、築地跡地再開発のスケジュールとMICE施設収益性を集中的に議論。"
        },
        {
            "id": "mem-5",
            "name": "渡辺 さゆり",
            "title": "都議会議員",
            "party": "日本共産党",
            "avatar_type": "politician_female",
            "total_statements": 28,
            "activity_score": 86,
            "main_focus": "異常猛暑対策・エアコン即時補助",
            "ai_eval": "気候変動・猛暑による熱中症予防のため、高齢世帯・困窮世帯へのエアコン設置補助金拡充を強く主張。"
        },
        {
            "id": "mem-6",
            "name": "山本 だいすけ",
            "title": "都議会議員",
            "party": "立憲民主党",
            "avatar_type": "politician_male",
            "total_statements": 26,
            "activity_score": 84,
            "main_focus": "避難所スターリンク通信・木密特区",
            "ai_eval": "首都直下地震対策として避難所の通信・電源インフラ整備および木密不燃化の即時実施を質疑。"
        }
    ]

    return {
        "assembly_id": assembly_id,
        "topic_distribution": topic_distribution,
        "party_analytics": party_analytics,
        "member_scorecards": member_scorecards
    }
