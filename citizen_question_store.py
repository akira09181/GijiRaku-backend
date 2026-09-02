"""Firestore persistence for issue-specific citizen question responses."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from reaction_store import (
    ReactionStoreError,
    STORAGE_BACKEND,
    _execute_transaction,
    get_firestore_client,
)


RESPONSES_COLLECTION = "citizen_question_responses"
AGGREGATES_COLLECTION = "citizen_question_aggregates"

SHINJUKU_ISSUE_ID = "shinjuku-sick-child-care-2026-06-10"
SHINJUKU_QUESTION_ID = "shinjuku-sick-child-care-realtime-booking-v1"
SHINJUKU_E2E_QUESTION_ID = "shinjuku-sick-child-care-realtime-booking-public-e2e-v1"

QUESTION_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    SHINJUKU_QUESTION_ID: {
        "issue_id": SHINJUKU_ISSUE_ID,
        "question": "病児保育の空き状況をリアルタイムで確認・予約できる仕組みが必要だと思いますか？",
        "answers": [
            {"id": "needed", "label": "必要だと思う"},
            {"id": "current_is_enough", "label": "現状の案内で十分"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "availability_unknown", "label": "空き状況が分からず困る"},
            {"id": "same_day_booking_unknown", "label": "当日予約できるか分からない"},
            {"id": "capacity_shortage", "label": "施設や定員が足りない"},
            {"id": "criteria_unclear", "label": "症状別の受入基準が分かりにくい"},
            {"id": "never_used", "label": "利用したことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "新宿区",
        "theme": "病児保育の利用拒否と予約・空き状況の改善",
    },
    "diet-medical-cost-burden-v1": {
        "issue_id": "diet-medical-cost-burden-2025-03-13",
        "question": "物価高の中で、高額療養費制度の見直しを優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "生活実感として必要"},
            {"id": "implementation", "label": "具体策や財源が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "日本国",
        "theme": "物価高と医療費負担の見直し",
    },
    "tokyo-app-one-stop-services-v1": {
        "issue_id": "tokyo-app-2026-06-16",
        "question": "東京アプリで、子育て・介護など自分に必要な支援情報と行政手続をワンストップで確認・利用できる機能を優先して整備してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して整備してほしい"},
            {"id": "limited_rollout", "label": "機能を限定して慎重に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "support_is_hard_to_find", "label": "自分に必要な支援情報を探しにくい"},
            {"id": "simpler_login_and_procedures", "label": "ログインや行政手続を簡単にしてほしい"},
            {"id": "points_and_digital_id", "label": "東京ポイントやデジタル都民証が便利そう"},
            {"id": "privacy_and_security", "label": "個人情報やセキュリティが心配"},
            {"id": "never_used", "label": "東京アプリを利用したことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "東京都",
        "theme": "東京アプリの機能強化",
    },
    "machida-regional-transport-model-v1": {
        "issue_id": "machida-regional-transport-2026-03-26",
        "question": "交通不便地域で、予約型乗合交通など地域の実情に合う新しい移動手段を導入してほしいですか？",
        "answers": [
            {"id": "introduce", "label": "導入してほしい"},
            {"id": "improve_existing", "label": "まず既存のバス・交通を改善してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "stops_are_far", "label": "駅やバス停まで遠く移動しにくい"},
            {"id": "non_drivers_need_options", "label": "高齢者や車を運転しない人の移動手段が必要"},
            {"id": "booking_and_schedule", "label": "予約方法や運行時間が使いやすいか気になる"},
            {"id": "fare_and_sustainability", "label": "運賃や継続的な運行費用が気になる"},
            {"id": "never_used", "label": "予約型・乗合交通を利用したことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "町田市",
        "theme": "交通不便地域の新しい地域交通モデル",
    },
    "shinagawa-school-support-and-dx-v1": {
        "issue_id": "shinagawa-inclusive-education-2026-02-19",
        "question": "教員の負担を減らしながら多様な子どもの学びを支えるため、支援人材の増員と教育DXを優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize_both", "label": "支援人材と教育DXを進めてほしい"},
            {"id": "prioritize_people", "label": "まず支援人材の充実を優先してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "teacher_workload", "label": "教員の業務負担が大きい"},
            {"id": "individual_support", "label": "一人ひとりに合う学習・特別支援が必要"},
            {"id": "information_sharing", "label": "教育データや支援情報の共有を改善してほしい"},
            {"id": "dx_may_add_work", "label": "教育DXがかえって負担を増やさないか心配"},
            {"id": "never_experienced", "label": "区立学校に通学・勤務した経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "品川区",
        "theme": "深い学び・多様性の包摂と教員負担軽減",
    },
    "shibuya-inflation-benefit-balance-v1": {
        "issue_id": "shibuya-inflation-support-2026-01-16",
        "question": "物価高騰支援は、全区民への一律給付と子育て世帯への上乗せ給付を組み合わせる方法が適切だと思いますか？",
        "answers": [
            {"id": "balanced_support", "label": "この組み合わせが適切だと思う"},
            {"id": "more_targeted", "label": "困窮度に応じた重点支援を優先してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "living_costs", "label": "食費や光熱費の上昇が家計に響いている"},
            {"id": "childcare_costs", "label": "子育て世帯の負担が特に大きい"},
            {"id": "simple_and_fast", "label": "一律給付は分かりやすく早く届く"},
            {"id": "amount_or_target", "label": "給付額や対象の決め方を見直してほしい"},
            {"id": "never_received", "label": "同様の給付を受けたことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "渋谷区",
        "theme": "物価高騰緊急支援給付金と子育て応援手当",
    },
    "arakawa-budget-priorities-and-results-v1": {
        "issue_id": "arakawa-ward-auto-2026-03-17-685-6-267",
        "question": "令和8年度予算は、防災・子育て・福祉・地域活性化の事業ごとに目標と成果を公開し、区民の声で優先順位を見直せるようにしてほしいですか？",
        "answers": [
            {"id": "publish_and_review", "label": "目標と成果を公開して見直してほしい"},
            {"id": "current_explanation_enough", "label": "現在の予算説明で十分だと思う"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "priorities_unclear", "label": "何を優先した予算か分かりにくい"},
            {"id": "outcomes_needed", "label": "事業の成果や費用対効果を確認したい"},
            {"id": "resident_feedback", "label": "区民の声を次年度予算に反映してほしい"},
            {"id": "administrative_cost", "label": "公開や検証にかかる行政コストが気になる"},
            {"id": "never_checked", "label": "区の予算資料を見たことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "荒川区",
        "theme": "令和8年度当初予算の重点施策",
    },
    "hachioji-rag-ai-safeguarded-rollout-v1": {
        "issue_id": "hachioji-rag-ai-2026-06-11",
        "question": "庁内文書を参照する検索拡張生成AIを、回答根拠の表示と職員の確認を条件に行政業務へ広げてほしいですか？",
        "answers": [
            {"id": "expand_with_safeguards", "label": "安全対策を条件に広げてほしい"},
            {"id": "limited_pilot", "label": "対象業務を限った試行にとどめてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "faster_search", "label": "職員の情報検索や文書作成を速くしてほしい"},
            {"id": "service_quality", "label": "問い合わせ対応の質を高めてほしい"},
            {"id": "source_traceability", "label": "回答の根拠となる庁内文書を確認できることが重要"},
            {"id": "accuracy_and_data", "label": "誤回答や機密情報の扱いが心配"},
            {"id": "never_used", "label": "生成AIを利用したことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "八王子市",
        "theme": "検索拡張生成AIの行政利用",
    },
    "nerima-elderly-support-v1": {
        "issue_id": "nerima-ward-auto-2024-03-15-5227-9-275",
        "question": "高齢者いきいき健康事業の対象拡大や地域包括支援センター増設など、高齢者対策を強化してほしいですか？",
        "answers": [
            {"id": "strengthen", "label": "強化してほしい"},
            {"id": "current_is_enough", "label": "現状の支援で十分"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "health_program", "label": "健康事業の対象や内容が狭い"},
            {"id": "support_center", "label": "相談・支援体制を充実してほしい"},
            {"id": "housing_cost", "label": "家賃など生活費の負担が大きい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "not_applicable", "label": "高齢者支援の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "練馬区",
        "theme": "高齢者対策の強化",
    },
    "nakano-childcare-support-v1": {
        "issue_id": "nakano-ward-auto-2024-03-06-197-4-196",
        "question": "待機児童対策や保育施設の整備など、中野区の子育て支援を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "waiting_lists", "label": "保育園の空きや待機が心配"},
            {"id": "facility_access", "label": "施設の場所や利用時間が合わない"},
            {"id": "cost_burden", "label": "保育料や学童などの費用が負担"},
            {"id": "info_hard_to_find", "label": "支援制度の情報が分かりにくい"},
            {"id": "no_childcare_need", "label": "現在子育て支援を利用していない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "中野区",
        "theme": "子育て支援",
    },
    "kita-child-rights-ordinance-v1": {
        "issue_id": "kita-ward-auto-2024-06-07-653-2-8",
        "question": "子どもの権利と幸せを定める条例に基づき、北区の子育て支援と防災対策を一体的に進めてほしいですか？",
        "answers": [
            {"id": "advance_together", "label": "一体的に進めてほしい"},
            {"id": "childcare_first", "label": "まず子育て支援を優先してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "child_ordinance", "label": "子ども条例の実効性が重要"},
            {"id": "disaster_safety", "label": "能登地震を踏まえた防災が必要"},
            {"id": "metro_collaboration", "label": "東京都との連携事項が気になる"},
            {"id": "implementation_cost", "label": "条例運用の費用や体制が心配"},
            {"id": "no_direct_experience", "label": "区立学校・保育の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "北区",
        "theme": "子育て支援策",
    },
    "sumida-hr-strategy-v1": {
        "issue_id": "sumida-ward-auto-2024-06-12-555-2-150",
        "question": "墨田区版総合的人事戦略で、職員の確保・育成・定着を進め、質の高い行政サービスを維持してほしいですか？",
        "answers": [
            {"id": "support_strategy", "label": "戦略を進めてほしい"},
            {"id": "efficiency_first", "label": "まず業務効率化を優先してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "service_quality", "label": "行政サービスの質維持が重要"},
            {"id": "recruitment", "label": "職員採用の確保が課題"},
            {"id": "retention", "label": "若手・ベテランの定着が心配"},
            {"id": "resident_contact", "label": "窓口対応の質が気になる"},
            {"id": "no_visibility", "label": "区役所の人事施策を知らない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "墨田区",
        "theme": "職員の人材育成",
    },
    "chuo-afterschool-care-v1": {
        "issue_id": "chuo-ward-auto-2023-06-19-109-3-64",
        "question": "共働き世帯向けに、いつでも児童を預けられる場所と学童保育を拡充してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "中央区",
        "theme": "学童保育と預かり場所の確保",
    },
    "kodaira-nursery-staff-v1": {
        "issue_id": "kodaira-city-auto-2024-02-26-1458-2-432",
        "question": "小平市の市立保育園で、保育士の確保と安定した保育体制を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "小平市",
        "theme": "市立保育園の保育士確保",
    },
    "akishima-working-parents-v1": {
        "issue_id": "akishima-city-auto-2024-03-05-2203-10-30",
        "question": "昭島市で、子育て世代が働きやすい環境づくりを優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "昭島市",
        "theme": "子育て世代が働きやすいまち",
    },
    "ome-childcare-environment-v1": {
        "issue_id": "ome-city-auto-2024-03-05-1269-3-117",
        "question": "青梅市で、人口減少対策と子育てしやすい環境づくりを一体的に進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "青梅市",
        "theme": "人口減少対策と子育て環境",
    },
    "higashiyamato-family-support-v1": {
        "issue_id": "higashiyamato-city-auto-2024-02-27-33-4-95",
        "question": "東大和市で、妊産婦や子育て家庭への支援を優先して充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "東大和市",
        "theme": "妊産婦や子育て家庭への支援",
    },
    "kiyose-disaster-preparedness-v1": {
        "issue_id": "kiyose-city-auto-2024-03-06-495-5-5",
        "question": "能登半島地震の教訓を踏まえ、清瀬市の防災対策を強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "清瀬市",
        "theme": "清瀬市の防災対策",
    },
    "kunitachi-childcare-university-v1": {
        "issue_id": "kunitachi-childcare-university-2025-03-05",
        "question": "国立市で、子育て支援と大学連携を一体的に進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "国立市",
        "theme": "子育て支援と大学連携",
    },
    "fussa-base-noise-safety-v1": {
        "issue_id": "fussa-base-noise-safety-2025-06-06",
        "question": "福生市で、横田基地周辺の騒音対策と安全確保を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "福生市",
        "theme": "横田基地周辺の騒音と安全",
    },
    "komae-childcare-support-v1": {
        "issue_id": "komae-childcare-support-2025-03-04",
        "question": "狛江市で、子育て支援を優先して充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "狛江市",
        "theme": "子育て支援の充実",
    },
    "higashikurume-elderly-disaster-v1": {
        "issue_id": "higashikurume-elderly-disaster-2025-09-02",
        "question": "東久留米市で、高齢者福祉と防災対策を一体的に強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "東久留米市",
        "theme": "高齢者福祉と防災対策",
    },
    "inagi-station-childcare-v1": {
        "issue_id": "inagi-station-childcare-2025-06-05",
        "question": "稲城市で、稲城駅周辺のまちづくりと子育て支援を一体的に進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "稲城市",
        "theme": "稲城駅周辺のまちづくりと子育て",
    },
    "hamura-water-source-v1": {
        "issue_id": "hamura-water-source-2025-03-03",
        "question": "羽村市で、水源保全と環境施策を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "羽村市",
        "theme": "水源保全と環境施策",
    },
    "akiruno-mountain-disaster-v1": {
        "issue_id": "akiruno-mountain-disaster-2025-09-03",
        "question": "あきる野市で、中山間地域の防災対策と避難体制を強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "あきる野市",
        "theme": "中山間地域の防災対策",
    },
    "minato-school-environment-v1": {
        "issue_id": "minato-school-environment-2025-03-05",
        "question": "港区で、港区立学校の改築と教育環境整備を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "港区",
        "theme": "港区立学校の改築と教育環境",
    },
    "adachi-assembly-ordinance-v1": {
        "issue_id": "adachi-assembly-ordinance-2025-08-31",
        "question": "足立区で、議会基本条例に基づく区政の透明性向上を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "足立区",
        "theme": "議会基本条例と区政の透明性",
    },
    "setagaya-childcare-demand-v1": {
        "issue_id": "setagaya-childcare-demand-2025-03-04",
        "question": "世田谷区で、子育て支援と保育需要への対応を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "世田谷区",
        "theme": "子育て支援と保育需要への対応",
    },
    "chofu-childcare-facilities-v1": {
        "issue_id": "chofu-childcare-facilities-2025-03-03",
        "question": "調布市で、子育て支援と保育施設整備を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "調布市",
        "theme": "子育て支援と保育施設整備",
    },
    "suginami-childcare-support-v1": {
        "issue_id": "suginami-childcare-support-2025-05-26",
        "question": "杉並区で、子育て支援施策を優先して充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "杉並区",
        "theme": "子育て支援施策の充実",
    },
    "itabashi-education-support-v1": {
        "issue_id": "itabashi-education-support-2025-03-04",
        "question": "板橋区で、子育て・教育支援を優先して強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "板橋区",
        "theme": "子育て・教育支援の強化",
    },
    "edogawa-child-education-v1": {
        "issue_id": "edogawa-child-education-2025-05-27",
        "question": "江戸川区で、子ども支援・教育力向上施策を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "江戸川区",
        "theme": "子ども支援・教育力向上",
    },
    "taito-childcare-welfare-v1": {
        "issue_id": "taito-childcare-welfare-2025-03-06",
        "question": "台東区で、子育て支援と地域福祉の充実を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "台東区",
        "theme": "子育て支援と地域福祉",
    },
    "meguro-childcare-demand-v1": {
        "issue_id": "meguro-childcare-demand-2025-03-05",
        "question": "目黒区で、子育て支援と保育需要への対応を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "目黒区",
        "theme": "子育て支援と保育需要",
    },
    "ota-childcare-medical-v1": {
        "issue_id": "ota-childcare-medical-2025-03-04",
        "question": "大田区で、子育て支援と地域医療の充実を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "大田区",
        "theme": "子育て支援と地域医療",
    },
    "toshima-childcare-support-v1": {
        "issue_id": "toshima-childcare-support-2025-03-06",
        "question": "豊島区で、子育て支援施策を優先して充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "豊島区",
        "theme": "子育て支援施策の充実",
    },
    "katsushika-education-support-v1": {
        "issue_id": "katsushika-education-support-2025-03-05",
        "question": "葛飾区で、子育て・教育支援を優先して強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "葛飾区",
        "theme": "子育て・教育支援の強化",
    },
    "okutama-mountain-disaster-v1": {
        "issue_id": "okutama-mountain-disaster-2025-03-05",
        "question": "奥多摩町で、中山間地域の防災対策と住民支援を強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "奥多摩町",
        "theme": "中山間地域の防災と住民支援",
    },
    "oshima-island-transport-medical-v1": {
        "issue_id": "oshima-island-transport-medical-2025-06-12",
        "question": "大島町で、離島交通と医療・福祉体制の充実を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "大島町",
        "theme": "離島交通と医療・福祉体制",
    },
    "hachijo-island-medical-welfare-v1": {
        "issue_id": "hachijo-island-medical-welfare-2025-03-07",
        "question": "八丈町で、離島の医療・福祉確保を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "八丈町",
        "theme": "離島の医療・福祉確保",
    },
    "miyake-island-disaster-life-v1": {
        "issue_id": "miyake-island-disaster-life-2025-03-06",
        "question": "三宅村で、離島の防災対策と生活基盤の維持を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "三宅村",
        "theme": "離島の防災と生活基盤",
    },
    "higashimurayama-childcare-welfare-v1": {
        "issue_id": "higashimurayama-childcare-welfare-2025-03-05",
        "question": "東村山市で、子育て支援と地域福祉の充実を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "東村山市",
        "theme": "子育て支援と地域福祉",
    },
    "mizuho-rural-transport-life-v1": {
        "issue_id": "mizuho-rural-transport-life-2025-03-06",
        "question": "瑞穂町で、中山間地域の交通と生活支援を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "瑞穂町",
        "theme": "中山間地域の交通と生活支援",
    },
    "hinode-childcare-medical-v1": {
        "issue_id": "hinode-childcare-medical-2025-09-18",
        "question": "日の出町で、子育て支援と地域医療の充実を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "日の出町",
        "theme": "子育て支援と地域医療",
    },
    "hinohara-mountain-disaster-v1": {
        "issue_id": "hinohara-mountain-disaster-2025-08-20",
        "question": "檜原村で、中山間地域の防災対策と住民支援を強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "檜原村",
        "theme": "中山間地域の防災と住民支援",
    },
    "toshima-island-life-medical-v1": {
        "issue_id": "toshima-island-life-medical-2025-03-05",
        "question": "利島村で、離島の生活基盤と医療体制の維持を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "利島村",
        "theme": "離島の生活基盤と医療体制",
    },
    "niijima-island-transport-tourism-v1": {
        "issue_id": "niijima-island-transport-tourism-2025-03-06",
        "question": "新島村で、離島交通と観光・産業振興を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "新島村",
        "theme": "離島交通と観光・産業振興",
    },
    "kozushima-island-medical-welfare-v1": {
        "issue_id": "kozushima-island-medical-welfare-2025-03-07",
        "question": "神津島村で、離島の医療・福祉確保を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "神津島村",
        "theme": "離島の医療・福祉確保",
    },
    "mikurajima-island-life-base-v1": {
        "issue_id": "mikurajima-island-life-base-2025-03-05",
        "question": "御蔵島村で、離島の生活基盤維持を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "御蔵島村",
        "theme": "離島の生活基盤維持",
    },
    "aogashima-island-disaster-infra-v1": {
        "issue_id": "aogashima-island-disaster-infra-2025-09-05",
        "question": "青ヶ島村で、離島の防災対策と生活インフラの維持を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "青ヶ島村",
        "theme": "離島の防災と生活インフラ",
    },
    "ogasawara-island-medical-education-v1": {
        "issue_id": "ogasawara-island-medical-education-2025-03-06",
        "question": "小笠原村で、離島の医療・教育・生活基盤の維持を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "小笠原村",
        "theme": "離島の医療・教育・生活基盤",
    },
    "nishitokyo-merged-childcare-v1": {
        "issue_id": "nishitokyo-merged-childcare-2025-03-07",
        "question": "西東京市で、保谷・田無合併後の子育て支援を地域間で一体的に運営してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "西東京市",
        "theme": "合併後の子育て支援一体運営",
    },
    "chiyoda-teen-support-allowance-v1": {
        "issue_id": "chiyoda-teen-support-allowance-2025-06-10",
        "question": "千代田区の中高生世代応援手当を、子育て支援の柱として優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "千代田区",
        "theme": "中高生世代応援手当",
    },
    "bunkyo-childcare-support-v1": {
        "issue_id": "bunkyo-childcare-support-2025-03-06",
        "question": "文京区で、子育て支援施策を優先して充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "文京区",
        "theme": "子育て支援施策の充実",
    },
    "koganei-nursery-safety-v1": {
        "issue_id": "koganei-nursery-safety-2025-02-28",
        "question": "小金井市で、保育施設の指定管理者選定と安全確保を優先して見直してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "小金井市",
        "theme": "保育施設の指定管理者と安全",
    },
    "hino-station-barrier-free-v1": {
        "issue_id": "hino-station-barrier-free-2025-03-04",
        "question": "日野駅のバリアフリー化と転落事故対策を優先して進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "日野市",
        "theme": "日野駅のバリアフリー改善",
    },
    "tama-school-safety-bullying-v1": {
        "issue_id": "tama-school-safety-bullying-2025-09-01",
        "question": "多摩市で、いじめ問題から学校生活の安全を確保する取組みを優先してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "多摩市",
        "theme": "学校生活の安全といじめ対策",
    },
    "koto-disaster-townplan-v1": {
        "issue_id": "koto-disaster-townplan-2025-06-12",
        "question": "能登半島地震の教訓を踏まえ、江東区の防災・まちづくり対策を強化してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "江東区",
        "theme": "防災・まちづくり対策の強化",
    },
    "musashino-school-rebuild-v1": {
        "issue_id": "musashino-school-rebuild-2025-12-04",
        "question": "武蔵野市で、学校改築と小・中学校の適正規模を踏まえた教育環境整備を進めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "武蔵野市",
        "theme": "学校改築と小・中学校の適正規模",
    },
    "fuchu-base-redevelopment-v1": {
        "issue_id": "fuchu-base-redevelopment-2025-09-03",
        "question": "府中基地跡地を、市民にとって使いやすい公共施設やまちづくりに活用してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "府中市",
        "theme": "府中基地跡地の活用",
    },
    "mitaka-inclusive-disaster-v1": {
        "issue_id": "mitaka-inclusive-disaster-2024-02-27",
        "question": "三鷹市で、高齢者や障がいのある方を取り残さないインクルーシブ防災を徹底してほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "三鷹市",
        "theme": "インクルーシブ防災の徹底",
    },
    "kokubunji-peace-education-v1": {
        "issue_id": "kokubunji-peace-education-2025-02-28",
        "question": "国分寺市で、公立中学校の平和教育と校外学習の政治的中立性・安全確保を求めてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "国分寺市",
        "theme": "平和教育と校外学習の中立性",
    },
    "musashimurayama-elderly-depression-v1": {
        "issue_id": "musashimurayama-city-auto-2024-03-01-1250-4-12",
        "question": "武蔵村山市で、高齢者のうつ病予防と相談・支援体制を充実させてほしいですか？",
        "answers": [
            {"id": "prioritize", "label": "優先して進めてほしい"},
            {"id": "steady_progress", "label": "慎重に段階的に進めてほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "resident_need", "label": "地域のニーズが高い"},
            {"id": "implementation", "label": "具体策や費用が気になる"},
            {"id": "info_hard_to_find", "label": "情報が分かりにくい"},
            {"id": "fiscal_priority", "label": "財源や優先順位が気になる"},
            {"id": "no_direct_experience", "label": "直接の利用経験がない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "武蔵村山市",
        "theme": "高齢者のうつ病対策",
    },
    "tachikawa-education-support-plans-v1": {
        "issue_id": "tachikawa-city-auto-2024-02-27-2629-4-62",
        "question": "特別な支援を必要とする児童生徒について、個別の教育支援計画・指導計画を保護者の意向も踏まえて作成・引き継ぎしてほしいですか？",
        "answers": [
            {"id": "ensure_plans", "label": "作成と引き継ぎを徹底してほしい"},
            {"id": "school_discretion", "label": "学校の判断を尊重してほしい"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "support_continuity", "label": "進学時の支援引き継ぎが重要"},
            {"id": "parent_voice", "label": "保護者の意向を反映してほしい"},
            {"id": "plan_criteria", "label": "作成基準や学校間格差が気になる"},
            {"id": "teacher_burden", "label": "教員の負担増が心配"},
            {"id": "no_school_child", "label": "市内の学校に通う子どもがいない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "立川市",
        "theme": "個別の教育支援計画と個別の指導計画",
    },
}
QUESTION_DEFINITIONS[SHINJUKU_E2E_QUESTION_ID] = {
    **QUESTION_DEFINITIONS[SHINJUKU_QUESTION_ID],
    "test_only": True,
}

logger = logging.getLogger(__name__)


def _document_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _response_document_id(question_id: str, anonymous_user_id: str) -> str:
    return _document_id(question_id, anonymous_user_id)


def _aggregate_document_id(issue_id: str, question_id: str) -> str:
    return _document_id(issue_id, question_id)


def _definition(issue_id: str, question_id: str) -> Dict[str, Any]:
    definition = QUESTION_DEFINITIONS.get(question_id)
    if definition is None or definition["issue_id"] != issue_id:
        raise ValueError("Unsupported issue_id or question_id")
    return definition


def _allowed_ids(items: Iterable[Dict[str, str]]) -> tuple[str, ...]:
    return tuple(item["id"] for item in items)


def _normalize_reasons(
    selected_reasons: Iterable[str], allowed_reasons: tuple[str, ...]
) -> list[str]:
    selected = set(selected_reasons)
    unsupported = selected.difference(allowed_reasons)
    if unsupported:
        raise ValueError("Unsupported selected reason")
    return [reason_id for reason_id in allowed_reasons if reason_id in selected]


def _normalized_counts(value: Any, keys: Iterable[str]) -> Dict[str, int]:
    source = value if isinstance(value, dict) else {}
    result: Dict[str, int] = {}
    for key in keys:
        try:
            result[key] = max(0, int(source.get(key, 0)))
        except (TypeError, ValueError):
            result[key] = 0
    return result


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _public_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "issue_id": data.get("issue_id"),
        "question_id": data.get("question_id"),
        "selected_answer": data.get("selected_answer"),
        "selected_reasons": list(data.get("selected_reasons") or []),
        "free_text": str(data.get("free_text") or ""),
        "created_at": _isoformat(data.get("created_at")),
        "updated_at": _isoformat(data.get("updated_at")),
    }


def _aggregate_payload(
    definition: Dict[str, Any], aggregate_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    data = aggregate_data or {}
    answer_ids = _allowed_ids(definition["answers"])
    reason_ids = _allowed_ids(definition["reasons"])
    answer_counts = _normalized_counts(data.get("answer_counts"), answer_ids)
    reason_counts = _normalized_counts(data.get("reason_counts"), reason_ids)
    total_responses = max(0, int(data.get("total_responses", 0) or 0))
    answers = [
        {
            **answer,
            "count": answer_counts[answer["id"]],
            "percentage": (
                round(answer_counts[answer["id"]] * 100 / total_responses, 1)
                if total_responses
                else 0.0
            ),
        }
        for answer in definition["answers"]
    ]
    reasons = [
        {**reason, "count": reason_counts[reason["id"]]}
        for reason in definition["reasons"]
    ]
    top_reasons = sorted(
        (reason for reason in reasons if reason["count"] > 0),
        key=lambda reason: (-reason["count"], reason["label"]),
    )
    return {
        "total_responses": total_responses,
        "answers": answers,
        "reasons": reasons,
        "top_reasons": top_reasons,
        "updated_at": _isoformat(data.get("updated_at")),
    }


def _flat_aggregate_fields(
    question_id: str, aggregate: Dict[str, Any]
) -> Dict[str, Any]:
    """Expose the stable, compact aggregate shape used by public clients."""
    if aggregate["total_responses"] == 0:
        answer_counts: Dict[str, int] = {}
        reason_counts: Dict[str, int] = {}
    else:
        answer_counts = {
            answer["id"]: answer["count"] for answer in aggregate["answers"]
        }
        reason_counts = {
            reason["id"]: reason["count"] for reason in aggregate["reasons"]
        }
    return {
        "question_id": question_id,
        "total": aggregate["total_responses"],
        "answers": answer_counts,
        "reasons": reason_counts,
    }


def put_citizen_question_response(
    *,
    issue_id: str,
    question_id: str,
    anonymous_user_id: str,
    selected_answer: str,
    selected_reasons: Iterable[str],
    free_text: str,
) -> Dict[str, Any]:
    """Create or overwrite one anonymous user's answer and aggregate atomically."""
    definition = _definition(issue_id, question_id)
    allowed_answers = _allowed_ids(definition["answers"])
    allowed_reasons = _allowed_ids(definition["reasons"])
    if selected_answer not in allowed_answers:
        raise ValueError("Unsupported selected answer")
    reasons = _normalize_reasons(selected_reasons, allowed_reasons)
    if not reasons:
        raise ValueError("At least one selected reason is required")
    normalized_text = free_text.strip()
    if len(normalized_text) > 500:
        raise ValueError("free_text must be at most 500 characters")

    client = get_firestore_client()
    response_ref = client.collection(RESPONSES_COLLECTION).document(
        _response_document_id(question_id, anonymous_user_id)
    )
    aggregate_ref = client.collection(AGGREGATES_COLLECTION).document(
        _aggregate_document_id(issue_id, question_id)
    )
    transaction = client.transaction()

    def apply_response(transaction: Any) -> Dict[str, Any]:
        response_snapshot = response_ref.get(transaction=transaction)
        aggregate_snapshot = aggregate_ref.get(transaction=transaction)
        previous = response_snapshot.to_dict() if response_snapshot.exists else {}
        aggregate_data = (
            aggregate_snapshot.to_dict() if aggregate_snapshot.exists else {}
        )
        previous_answer = previous.get("selected_answer")
        previous_reasons = set(previous.get("selected_reasons") or [])
        answer_counts = _normalized_counts(
            aggregate_data.get("answer_counts"), allowed_answers
        )
        reason_counts = _normalized_counts(
            aggregate_data.get("reason_counts"), allowed_reasons
        )
        total_responses = max(
            0, int(aggregate_data.get("total_responses", 0) or 0)
        )
        if not response_snapshot.exists:
            total_responses += 1
        elif previous_answer in allowed_answers and previous_answer != selected_answer:
            answer_counts[previous_answer] = max(
                0, answer_counts[previous_answer] - 1
            )
        if not response_snapshot.exists or previous_answer != selected_answer:
            answer_counts[selected_answer] += 1

        next_reasons = set(reasons)
        for removed_reason in previous_reasons.difference(next_reasons):
            if removed_reason in reason_counts:
                reason_counts[removed_reason] = max(
                    0, reason_counts[removed_reason] - 1
                )
        for added_reason in next_reasons.difference(previous_reasons):
            reason_counts[added_reason] += 1

        now = datetime.now(timezone.utc)
        created_at = previous.get("created_at") or now
        response_payload = {
            "issue_id": issue_id,
            "question_id": question_id,
            "anonymous_user_id": anonymous_user_id,
            "selected_answer": selected_answer,
            "selected_reasons": reasons,
            "free_text": normalized_text,
            "created_at": created_at,
            "updated_at": now,
        }
        aggregate_payload = {
            "issue_id": issue_id,
            "question_id": question_id,
            "municipality": definition["municipality"],
            "theme": definition["theme"],
            "answer_counts": answer_counts,
            "reason_counts": reason_counts,
            "total_responses": total_responses,
            "created_at": aggregate_data.get("created_at") or now,
            "updated_at": now,
        }
        transaction.set(response_ref, response_payload)
        transaction.set(aggregate_ref, aggregate_payload)
        return {
            "my_response": _public_response(response_payload),
            "aggregate": _aggregate_payload(definition, aggregate_payload),
            "created": not response_snapshot.exists,
        }

    try:
        result = _execute_transaction(transaction, apply_response)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception(
            "Firestore citizen response transaction failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise ReactionStoreError(
            "Firestore citizen response transaction failed"
        ) from exc

    aggregate = result["aggregate"]
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "question": definition,
        **_flat_aggregate_fields(question_id, aggregate),
        **result,
    }


def get_citizen_question_snapshot(
    *, issue_id: str, question_id: str, anonymous_user_id: Optional[str]
) -> Dict[str, Any]:
    """Read aggregate and optional current-user response as separate documents."""
    definition = _definition(issue_id, question_id)
    client = get_firestore_client()
    aggregate_ref = client.collection(AGGREGATES_COLLECTION).document(
        _aggregate_document_id(issue_id, question_id)
    )
    response_ref = (
        client.collection(RESPONSES_COLLECTION).document(
            _response_document_id(question_id, anonymous_user_id)
        )
        if anonymous_user_id
        else None
    )
    try:
        aggregate_snapshot = aggregate_ref.get()
        response_snapshot = response_ref.get() if response_ref is not None else None
    except Exception as exc:
        logger.exception(
            "Firestore citizen response GET failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise ReactionStoreError("Firestore citizen response GET failed") from exc

    aggregate_data = (
        aggregate_snapshot.to_dict() if aggregate_snapshot.exists else None
    )
    response_data = (
        response_snapshot.to_dict()
        if response_snapshot is not None and response_snapshot.exists
        else None
    )
    aggregate = _aggregate_payload(definition, aggregate_data)
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "question": definition,
        "my_response": _public_response(response_data) if response_data else None,
        "aggregate": aggregate,
        **_flat_aggregate_fields(question_id, aggregate),
    }


def get_citizen_question_user_response(
    *,
    issue_id: str,
    question_id: str,
    anonymous_user_id: str,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Read one user's structured response without loading the global aggregate."""
    _definition(issue_id, question_id)
    firestore_client = client or get_firestore_client()
    reference = firestore_client.collection(RESPONSES_COLLECTION).document(
        _response_document_id(question_id, anonymous_user_id)
    )
    try:
        snapshot = reference.get()
    except Exception as exc:
        logger.exception(
            "Firestore citizen user response GET failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise ReactionStoreError("Firestore citizen user response GET failed") from exc
    return _public_response(snapshot.to_dict() or {}) if snapshot.exists else None


def _response_query(client: Any, question_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(RESPONSES_COLLECTION)
        .where(filter=FieldFilter("question_id", "==", question_id))
        .stream()
    )


def get_citizen_question_admin_results(
    *, issue_id: str, question_id: str
) -> Dict[str, Any]:
    """Return aggregate and anonymized response details for analysis screens."""
    definition = _definition(issue_id, question_id)
    snapshot = get_citizen_question_snapshot(
        issue_id=issue_id,
        question_id=question_id,
        anonymous_user_id=None,
    )
    client = get_firestore_client()
    try:
        response_snapshots = list(_response_query(client, question_id))
    except Exception as exc:
        logger.exception(
            "Firestore citizen response admin query failed (question_id=%s)",
            question_id,
        )
        raise ReactionStoreError(
            "Firestore citizen response admin query failed"
        ) from exc

    responses = []
    for response_snapshot in response_snapshots:
        data = response_snapshot.to_dict() or {}
        if data.get("issue_id") != issue_id:
            continue
        public = _public_response(data)
        responses.append(
            {
                "selected_answer": public["selected_answer"],
                "selected_reasons": public["selected_reasons"],
                "free_text": public["free_text"],
                "created_at": public["created_at"],
                "updated_at": public["updated_at"],
            }
        )
    responses.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        **snapshot,
        "municipality": definition["municipality"],
        "theme": definition["theme"],
        "responses": responses,
    }
