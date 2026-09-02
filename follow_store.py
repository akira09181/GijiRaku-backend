"""Firestore persistence and verified status metadata for followed issues."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from citizen_question_store import get_citizen_question_snapshot
from notification_store import create_notification, _user_document_id
from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client


FOLLOWS_COLLECTION = "issue_follows"
ISSUES_COLLECTION = "issues"

ISSUE_STATUSES: Dict[str, Dict[str, str]] = {
    "tokyo-app-2026-06-16": {
        "question_id": "tokyo-app-one-stop-services-v1",
        "assembly_id": "tokyo-metropolitan",
        "municipality": "東京都",
        "title": "東京アプリの機能強化",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "支援情報の配信、ログイン簡素化、デジタル都民証、生成AI案内機能を進める方針が答弁されました。",
        "status_updated_at": "2026-06-16T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "必要な支援情報や行政手続へ素早く到達できるかが論点です。",
        "government_response_summary": "東京都はライフステージ別配信やログイン簡素化などを進めると答弁しました。",
        "share_summary": "東京アプリで支援情報と行政手続をワンストップで利用できる機能について、市民の意見を集めています。",
        "source_url": "https://www.gikai.metro.tokyo.lg.jp/record/proceedings/2026-2/02-01.html",
    },
    "shinjuku-sick-child-care-2026-06-10": {
        "question_id": "shinjuku-sick-child-care-realtime-booking-v1",
        "assembly_id": "shinjuku-ward",
        "municipality": "新宿区",
        "title": "病児保育の利用拒否と予約・空き状況の改善",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "受入体制を検討し、空き状況や予約に使えるICTツールを研究すると答弁されました。新しい対応状況は未確認です。",
        "status_updated_at": "2026-06-10T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "病児保育を利用できない事例と、空き状況・予約方法の分かりにくさが論点です。",
        "government_response_summary": "新宿区は受入体制の検討とICTツールの研究を進めると答弁しました。",
        "share_summary": "新宿区の病児保育について、空き状況を確認・予約できる仕組みが必要か市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/shinjuku/SpMinuteView.html?council_id=3193&schedule_id=2",
    },
    "machida-regional-transport-2026-03-26": {
        "question_id": "machida-regional-transport-model-v1",
        "assembly_id": "machida-city",
        "municipality": "町田市",
        "title": "交通不便地域の新しい地域交通モデル",
        "current_status": "議会で質問済み",
        "status_summary": "交通不便地域に地域特性に応じた移動手段を整える考え方が質問されました。新しい対応状況は未確認です。",
        "status_updated_at": "2026-03-26T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "既存公共交通だけでは移動が難しい地域の移動手段が論点です。",
        "government_response_summary": "公開中の会議録では新しい地域交通モデルの構築方法が質問されています。",
        "share_summary": "町田市の交通不便地域に、地域に合う新しい移動手段が必要か市民の意見を集めています。",
        "source_url": "https://www.gikai-machida.jp/g07_Shitsumon.asp?KAIGI=174&Sflg=2",
    },
    "shinagawa-inclusive-education-2026-02-19": {
        "question_id": "shinagawa-school-support-and-dx-v1",
        "assembly_id": "shinagawa-ward",
        "municipality": "品川区",
        "title": "深い学び・多様性の包摂と教員負担軽減",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "学校支援人材と教育DXを活用し、教員負担の軽減と特別支援を進める方針が答弁されました。",
        "status_updated_at": "2026-02-19T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "多様な学びを支えながら教員負担を減らす体制が論点です。",
        "government_response_summary": "品川区は支援人材の充実と教育データの活用を進めると答弁しました。",
        "share_summary": "品川区の学校で、支援人材と教育DXをどう進めるか市民の意見を集めています。",
        "source_url": "https://kaigiroku.city.shinagawa.tokyo.jp/100000?QueryType=New&Template=document&VoiceExpand1=r08-0219_002",
    },
    "shibuya-inflation-support-2026-01-16": {
        "question_id": "shibuya-inflation-benefit-balance-v1",
        "assembly_id": "shibuya-ward",
        "municipality": "渋谷区",
        "title": "物価高騰緊急支援給付金と子育て応援手当",
        "current_status": "補正予算を可決",
        "status_summary": "全区民への1人5,000円給付と、子ども1人当たり2万円の応援手当を含む補正予算が可決されました。",
        "status_updated_at": "2026-01-16T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "物価高騰への支援を一律給付と重点支援でどう配分するかが論点です。",
        "government_response_summary": "渋谷区は全区民給付と子育て世帯への上乗せ手当を実施する補正予算を提案しました。",
        "share_summary": "渋谷区の物価高騰支援で、一律給付と子育て世帯への上乗せをどう組み合わせるか意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/shibuya/SpMinuteView.html?council_id=2494&schedule_id=2",
    },
    "arakawa-ward-auto-2026-03-17-685-6-267": {
        "question_id": "arakawa-budget-priorities-and-results-v1",
        "assembly_id": "arakawa-ward",
        "municipality": "荒川区",
        "title": "令和8年度当初予算の重点施策",
        "current_status": "予算案について討論済み",
        "status_summary": "防災、子育て、福祉、地域活性化などを含む令和8年度一般会計予算案について賛成討論が行われました。",
        "status_updated_at": "2026-03-17T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "当初予算の重点分野と、区民の声をどう事業へ反映するかが論点です。",
        "government_response_summary": "公開中の会議録では令和8年度一般会計予算案について討論されています。",
        "share_summary": "荒川区の令和8年度予算で、事業の目標と成果をどう公開するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/arakawa/SpMinuteView.html?council_id=685&schedule_id=2",
    },
    "hachioji-rag-ai-2026-06-11": {
        "question_id": "hachioji-rag-ai-safeguarded-rollout-v1",
        "assembly_id": "hachioji-city",
        "municipality": "八王子市",
        "title": "検索拡張生成AIの行政利用",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "2026年度の利用職員50％を目標に、庁内共通業務から段階的に導入する方針が答弁されました。",
        "status_updated_at": "2026-06-11T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "行政業務で生成AIを使う際の効率、精度、安全性が論点です。",
        "government_response_summary": "八王子市は研修と資料の段階的な取込みでAI活用を定着させる方針を示しました。",
        "share_summary": "八王子市の検索拡張生成AIを、安全対策を条件に行政業務へ広げるか意見を集めています。",
        "source_url": "https://www.city.hachioji.tokyo.dbsr.jp/index.php/611167?Template=document&Id=6213",
    },
    "nerima-ward-auto-2024-03-15-5227-9-275": {
        "question_id": "nerima-elderly-support-v1",
        "assembly_id": "nerima-ward",
        "municipality": "練馬区",
        "title": "高齢者対策の強化",
        "current_status": "議会で討論済み",
        "status_summary": "高齢者いきいき健康事業の対象拡大や支援体制強化が議論されました。",
        "status_updated_at": "2024-03-15T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "高齢者健康事業の対象や支援体制、生活費負担が論点です。",
        "government_response_summary": "公開中の会議録では、高齢者対策強化の陳情について賛成討論が行われました。",
        "share_summary": "練馬区の高齢者対策を、健康事業や支援体制の面からどう強化するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/nerima/SpMinuteView.html?council_id=5227&schedule_id=9",
    },
    "nakano-ward-auto-2024-03-06-197-4-196": {
        "question_id": "nakano-childcare-support-v1",
        "assembly_id": "nakano-ward",
        "municipality": "中野区",
        "title": "子育て支援",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "子育て支援策について質問・答弁が行われました。",
        "status_updated_at": "2024-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "保育施設の整備や待機児童対策など子育て支援の優先度が論点です。",
        "government_response_summary": "公開中の会議録では、中野区の子育て支援について質疑が行われました。",
        "share_summary": "中野区の子育て支援をどう優先して進めるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/nakano/SpMinuteView.html?council_id=197&schedule_id=4",
    },
    "kita-ward-auto-2024-06-07-653-2-8": {
        "question_id": "kita-child-rights-ordinance-v1",
        "assembly_id": "kita-ward",
        "municipality": "北区",
        "title": "子育て支援策",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "子育て支援策と防災・安全なまちづくりについて質問されました。",
        "status_updated_at": "2024-06-07T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "子ども条例の実効性と、子育て支援・防災対策の一体推進が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援策と防災対策について質問・答弁が行われました。",
        "share_summary": "北区の子育て支援と防災対策を一体的に進めるべきか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/kita/SpMinuteView.html?council_id=653&schedule_id=2",
    },
    "sumida-ward-auto-2024-06-12-555-2-150": {
        "question_id": "sumida-hr-strategy-v1",
        "assembly_id": "sumida-ward",
        "municipality": "墨田区",
        "title": "職員の人材育成",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "職員の人材育成と総合的人事戦略について質問されました。",
        "status_updated_at": "2024-06-12T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "職員確保・育成・定着と、行政サービスの持続可能性が論点です。",
        "government_response_summary": "公開中の会議録では、墨田区版総合的人事戦略について質問・答弁が行われました。",
        "share_summary": "墨田区の職員確保・育成をどう進めるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/sumida/SpMinuteView.html?council_id=555&schedule_id=2",
    },
    "chuo-ward-auto-2023-06-19-109-3-64": {
        "question_id": "chuo-afterschool-care-v1",
        "assembly_id": "chuo-ward",
        "municipality": "中央区",
        "title": "学童保育と預かり場所の確保",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "学童保育の設置と待機児童への対応について質問・答弁されました。",
        "status_updated_at": "2023-06-19T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "学童保育の待機と、共働き世帯の預かり場所不足が論点です。",
        "government_response_summary": "公開中の会議録では、学童保育設置と待機児童について質問・答弁が行われました。",
        "share_summary": "中央区の学童保育と預かり場所をどう拡充するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/chuo/SpMinuteView.html?council_id=109&schedule_id=3",
    },
    "kodaira-city-auto-2024-02-26-1458-2-432": {
        "question_id": "kodaira-nursery-staff-v1",
        "assembly_id": "kodaira-city",
        "municipality": "小平市",
        "title": "市立保育園の保育士確保",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "市立保育園における保育士確保について質問・答弁されました。",
        "status_updated_at": "2024-02-26T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "保育需要の増加と保育士確保が論点です。",
        "government_response_summary": "公開中の会議録では、市立保育園の保育士体制について質問・答弁が行われました。",
        "share_summary": "小平市の市立保育園で保育士をどう確保するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/kodaira/SpMinuteView.html?council_id=1458&schedule_id=2",
    },
    "akishima-city-auto-2024-03-05-2203-10-30": {
        "question_id": "akishima-working-parents-v1",
        "assembly_id": "akishima-city",
        "municipality": "昭島市",
        "title": "子育て世代が働きやすいまち",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "子育て世代が働きやすいまちづくりについて質問・答弁されました。",
        "status_updated_at": "2024-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "若者・子育て世代支援と地域の活力維持が論点です。",
        "government_response_summary": "公開中の会議録では、子育て世代が働きやすいまちづくりについて質問・答弁が行われました。",
        "share_summary": "昭島市で子育て世代が働きやすい環境をどう整えるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/akishima/SpMinuteView.html?council_id=2203&schedule_id=10",
    },
    "ome-city-auto-2024-03-05-1269-3-117": {
        "question_id": "ome-childcare-environment-v1",
        "assembly_id": "ome-city",
        "municipality": "青梅市",
        "title": "人口減少対策と子育て環境",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "人口減少対策と子育てしやすい環境づくりについて質問・答弁されました。",
        "status_updated_at": "2024-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "出生数減少と子育てしやすい環境整備が論点です。",
        "government_response_summary": "公開中の会議録では、人口減少対策と子育て環境づくりについて質問・答弁が行われました。",
        "share_summary": "青梅市の人口減少対策と子育て環境をどう進めるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/ome/SpMinuteView.html?council_id=1269&schedule_id=3",
    },
    "higashiyamato-city-auto-2024-02-27-33-4-95": {
        "question_id": "higashiyamato-family-support-v1",
        "assembly_id": "higashiyamato-city",
        "municipality": "東大和市",
        "title": "妊産婦や子育て家庭への支援",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "妊産婦や子育て家庭への支援について質問・答弁されました。",
        "status_updated_at": "2024-02-27T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "妊産婦・子育て家庭支援と保育体制が論点です。",
        "government_response_summary": "公開中の会議録では、妊産婦や子育て家庭への支援について質問・答弁が行われました。",
        "share_summary": "東大和市の妊産婦・子育て家庭支援をどう充実させるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/higashiyamato/SpMinuteView.html?council_id=33&schedule_id=4",
    },
    "kiyose-city-auto-2024-03-06-495-5-5": {
        "question_id": "kiyose-disaster-preparedness-v1",
        "assembly_id": "kiyose-city",
        "municipality": "清瀬市",
        "title": "清瀬市の防災対策",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "清瀬市の防災対策について質問・答弁されました。",
        "status_updated_at": "2024-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "大規模災害への備えと地域防災体制が論点です。",
        "government_response_summary": "公開中の会議録では、清瀬市の防災対策について質問・答弁が行われました。",
        "share_summary": "清瀬市の防災対策をどう強化するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/kiyose/SpMinuteView.html?council_id=495&schedule_id=5",
    },
    "kunitachi-childcare-university-2025-03-05": {
        "question_id": "kunitachi-childcare-university-v1",
        "assembly_id": "kunitachi-city",
        "municipality": "国立市",
        "title": "子育て支援と大学連携",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と大学連携について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "学園都市としての子育て環境整備と大学・地域連携が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と大学連携について一般質問が行われました。",
        "share_summary": "国立市の子育て支援と大学連携をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.kunitachi.tokyo.dbsr.jp/index.php/",
    },
    "fussa-base-noise-safety-2025-06-06": {
        "question_id": "fussa-base-noise-safety-v1",
        "assembly_id": "fussa-city",
        "municipality": "福生市",
        "title": "横田基地周辺の騒音と安全",
        "current_status": "議会で一般質問済み",
        "status_summary": "横田基地周辺の騒音と安全について一般質問されました。",
        "status_updated_at": "2025-06-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "基地周辺の騒音・安全と住民生活の両立が論点です。",
        "government_response_summary": "公開中の会議録では、横田基地周辺の騒音と安全について一般質問が行われました。",
        "share_summary": "福生市の基地周辺対策をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.fussa.tokyo.dbsr.jp/index.php/",
    },
    "komae-childcare-support-2025-03-04": {
        "question_id": "komae-childcare-support-v1",
        "assembly_id": "komae-city",
        "municipality": "狛江市",
        "title": "子育て支援の充実",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援の充実について一般質問されました。",
        "status_updated_at": "2025-03-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育需要と子育て世代への支援拡充が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援の充実について一般質問が行われました。",
        "share_summary": "狛江市の子育て支援をどう充実させるか市民の意見を集めています。",
        "source_url": "https://www.city.komae.tokyo.dbsr.jp/index.php/",
    },
    "higashikurume-elderly-disaster-2025-09-02": {
        "question_id": "higashikurume-elderly-disaster-v1",
        "assembly_id": "higashikurume-city",
        "municipality": "東久留米市",
        "title": "高齢者福祉と防災対策",
        "current_status": "議会で一般質問済み",
        "status_summary": "高齢者福祉と防災対策について一般質問されました。",
        "status_updated_at": "2025-09-02T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "高齢者の見守りと地域防災体制の強化が論点です。",
        "government_response_summary": "公開中の会議録では、高齢者福祉と防災対策について一般質問が行われました。",
        "share_summary": "東久留米市の高齢者福祉と防災をどう強化するか市民の意見を集めています。",
        "source_url": "https://www.city.higashikurume.tokyo.dbsr.jp/index.php/",
    },
    "inagi-station-childcare-2025-06-05": {
        "question_id": "inagi-station-childcare-v1",
        "assembly_id": "inagi-city",
        "municipality": "稲城市",
        "title": "稲城駅周辺のまちづくりと子育て",
        "current_status": "議会で一般質問済み",
        "status_summary": "稲城駅周辺のまちづくりと子育てについて一般質問されました。",
        "status_updated_at": "2025-06-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "駅前再開発と子育て世代の利便性向上が論点です。",
        "government_response_summary": "公開中の会議録では、稲城駅周辺のまちづくりと子育て支援について一般質問が行われました。",
        "share_summary": "稲城駅周辺のまちづくりと子育てをどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.inagi.tokyo.dbsr.jp/index.php/",
    },
    "hamura-water-source-2025-03-03": {
        "question_id": "hamura-water-source-v1",
        "assembly_id": "hamura-city",
        "municipality": "羽村市",
        "title": "水源保全と環境施策",
        "current_status": "議会で一般質問済み",
        "status_summary": "水源保全と環境施策について一般質問されました。",
        "status_updated_at": "2025-03-03T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "水源地域の保全と開発・環境のバランスが論点です。",
        "government_response_summary": "公開中の会議録では、水源保全と環境施策について一般質問が行われました。",
        "share_summary": "羽村市の水源保全と環境施策をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.hamura.tokyo.dbsr.jp/index.php/",
    },
    "akiruno-mountain-disaster-2025-09-03": {
        "question_id": "akiruno-mountain-disaster-v1",
        "assembly_id": "akiruno-city",
        "municipality": "あきる野市",
        "title": "中山間地域の防災対策",
        "current_status": "議会で一般質問済み",
        "status_summary": "中山間地域の防災対策について一般質問されました。",
        "status_updated_at": "2025-09-03T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "山間部の土砂災害リスクと避難・救助体制が論点です。",
        "government_response_summary": "公開中の会議録では、中山間地域の防災対策について一般質問が行われました。",
        "share_summary": "あきる野市の中山間地域防災をどう強化するか市民の意見を集めています。",
        "source_url": "https://www.city.akiruno.tokyo.dbsr.jp/index.php/",
    },
    "minato-school-environment-2025-03-05": {
        "question_id": "minato-school-environment-v1",
        "assembly_id": "minato-ward",
        "municipality": "港区",
        "title": "港区立学校の改築と教育環境",
        "current_status": "議会で一般質問済み",
        "status_summary": "港区立学校の改築と教育環境について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "老朽化校舎の改築計画と教育環境の質的向上が論点です。",
        "government_response_summary": "公開中の会議録では、港区立学校の改築と教育環境について一般質問が行われました。",
        "share_summary": "港区立学校の改築と教育環境をどう整備するか市民の意見を集めています。",
        "source_url": "https://gikai2.city.minato.tokyo.jp/voices/index.asp",
    },
    "adachi-assembly-ordinance-2025-08-31": {
        "question_id": "adachi-assembly-ordinance-v1",
        "assembly_id": "adachi-ward",
        "municipality": "足立区",
        "title": "議会基本条例と区政の透明性",
        "current_status": "議会で一般質問済み",
        "status_summary": "議会基本条例と区政の透明性について審議されました。",
        "status_updated_at": "2025-08-31T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "議会運営のルール整備と区民参加の仕組みづくりが論点です。",
        "government_response_summary": "公開中の会議録では、議会基本条例と区政の透明性について審議が行われました。",
        "share_summary": "足立区の議会基本条例と区政の透明性をどう高めるか市民の意見を集めています。",
        "source_url": "https://www.gikai-adachi.jp/",
    },
    "setagaya-childcare-demand-2025-03-04": {
        "question_id": "setagaya-childcare-demand-v1",
        "assembly_id": "setagaya-ward",
        "municipality": "世田谷区",
        "title": "子育て支援と保育需要への対応",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と保育需要への対応について一般質問されました。",
        "status_updated_at": "2025-03-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育・学童需要の増加と子育て世代支援の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と保育需要への対応について一般質問が行われました。",
        "share_summary": "世田谷区の子育て支援と保育需要への対応をどう進めるか市民の意見を集めています。",
        "source_url": "https://kugi.city.setagaya.tokyo.jp/",
    },
    "chofu-childcare-facilities-2025-03-03": {
        "question_id": "chofu-childcare-facilities-v1",
        "assembly_id": "chofu-city",
        "municipality": "調布市",
        "title": "子育て支援と保育施設整備",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と保育施設整備について一般質問されました。",
        "status_updated_at": "2025-03-03T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育施設の需給バランスと子育て世代への支援拡充が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と保育施設整備について一般質問が行われました。",
        "share_summary": "調布市の子育て支援と保育施設整備をどう進めるか市民の意見を集めています。",
        "source_url": "https://chofucity.gijiroku.com/voices/",
    },
    "suginami-childcare-support-2025-05-26": {
        "question_id": "suginami-childcare-support-v1",
        "assembly_id": "suginami-ward",
        "municipality": "杉並区",
        "title": "子育て支援施策の充実",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "status_updated_at": "2025-05-26T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育・学童需要と子育て世代への経済的支援の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "share_summary": "杉並区の子育て支援をどう充実させるか市民の意見を集めています。",
        "source_url": "https://suginami.gijiroku.com/voices/",
    },
    "itabashi-education-support-2025-03-04": {
        "question_id": "itabashi-education-support-v1",
        "assembly_id": "itabashi-ward",
        "municipality": "板橋区",
        "title": "子育て・教育支援の強化",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て・教育支援の強化について一般質問されました。",
        "status_updated_at": "2025-03-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て支援と学校教育の質向上、施設整備の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て・教育支援の強化について一般質問が行われました。",
        "share_summary": "板橋区の子育て・教育支援をどう強化するか市民の意見を集めています。",
        "source_url": "https://itabashi.gijiroku.com/voices/",
    },
    "edogawa-child-education-2025-05-27": {
        "question_id": "edogawa-child-education-v1",
        "assembly_id": "edogawa-ward",
        "municipality": "江戸川区",
        "title": "子ども支援・教育力向上",
        "current_status": "議会で一般質問済み",
        "status_summary": "子ども支援・教育力向上について一般質問されました。",
        "status_updated_at": "2025-05-27T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子ども支援特別委員会の重点施策と教育力向上の具体策が論点です。",
        "government_response_summary": "公開中の会議録では、子ども支援・教育力向上について一般質問が行われました。",
        "share_summary": "江戸川区の子ども支援・教育力向上をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.gikai.city.edogawa.tokyo.jp/voices/",
    },
    "taito-childcare-welfare-2025-03-06": {
        "question_id": "taito-childcare-welfare-v1",
        "assembly_id": "taito-ward",
        "municipality": "台東区",
        "title": "子育て支援と地域福祉",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と地域福祉について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て世代支援と高齢者福祉を含む地域福祉の一体的な充実が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と地域福祉について一般質問が行われました。",
        "share_summary": "台東区の子育て支援と地域福祉をどう充実させるか市民の意見を集めています。",
        "source_url": "https://taito.gijiroku.com/voices/",
    },
    "meguro-childcare-demand-2025-03-05": {
        "question_id": "meguro-childcare-demand-v1",
        "assembly_id": "meguro-ward",
        "municipality": "目黒区",
        "title": "子育て支援と保育需要",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と保育需要への対応について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育・学童需要の増加と子育て世代支援の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と保育需要への対応について一般質問が行われました。",
        "share_summary": "目黒区の子育て支援と保育需要への対応をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.kensakusystem.jp/meguro-jimu/index.html",
    },
    "ota-childcare-medical-2025-03-04": {
        "question_id": "ota-childcare-medical-v1",
        "assembly_id": "ota-ward",
        "municipality": "大田区",
        "title": "子育て支援と地域医療",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と地域医療について一般質問されました。",
        "status_updated_at": "2025-03-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て世代支援と地域医療・福祉の連携強化が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と地域医療について一般質問が行われました。",
        "share_summary": "大田区の子育て支援と地域医療をどう充実させるか市民の意見を集めています。",
        "source_url": "https://ota.gijiroku.com/voices/",
    },
    "toshima-childcare-support-2025-03-06": {
        "question_id": "toshima-childcare-support-v1",
        "assembly_id": "toshima-ward",
        "municipality": "豊島区",
        "title": "子育て支援施策の充実",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "保育・学童需要と子育て世代への経済的支援の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "share_summary": "豊島区の子育て支援をどう充実させるか市民の意見を集めています。",
        "source_url": "https://www.kensakusystem.jp/toshima/",
    },
    "katsushika-education-support-2025-03-05": {
        "question_id": "katsushika-education-support-v1",
        "assembly_id": "katsushika-ward",
        "municipality": "葛飾区",
        "title": "子育て・教育支援の強化",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て・教育支援の強化について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て支援と学校教育の質向上、施設整備の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て・教育支援の強化について一般質問が行われました。",
        "share_summary": "葛飾区の子育て・教育支援をどう強化するか市民の意見を集めています。",
        "source_url": "https://www.kensakusystem.jp/katsushika/sapphire.html",
    },
    "okutama-mountain-disaster-2025-03-05": {
        "question_id": "okutama-mountain-disaster-v1",
        "assembly_id": "okutama-town",
        "municipality": "奥多摩町",
        "title": "中山間地域の防災と住民支援",
        "current_status": "議会で一般質問済み",
        "status_summary": "中山間地域の防災と住民支援について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "山間部の防災・避難体制と過疎地域の生活支援が論点です。",
        "government_response_summary": "公開中の会議録では、中山間地域の防災と住民支援について一般質問が行われました。",
        "share_summary": "奥多摩町の防災と住民支援をどう強化するか市民の意見を集めています。",
        "source_url": "https://www.town.okutama.tokyo.jp/gyosei/8/okutamachogikai/kaigiroku/index.html",
    },
    "oshima-island-transport-medical-2025-06-12": {
        "question_id": "oshima-island-transport-medical-v1",
        "assembly_id": "oshima-town",
        "municipality": "大島町",
        "title": "離島交通と医療・福祉体制",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島交通と医療・福祉体制について一般質問されました。",
        "status_updated_at": "2025-06-12T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "離島の交通不便と医療・福祉サービスの確保が論点です。",
        "government_response_summary": "公開中の会議録では、離島交通と医療・福祉体制について一般質問が行われました。",
        "share_summary": "大島町の離島交通と医療・福祉をどう充実させるか市民の意見を集めています。",
        "source_url": "https://www.town.oshima.tokyo.jp/soshiki/gikaijim/gikai-kekka.html",
    },
    "hachijo-island-medical-welfare-2025-03-07": {
        "question_id": "hachijo-island-medical-welfare-v1",
        "assembly_id": "hachijo-town",
        "municipality": "八丈町",
        "title": "離島の医療・福祉確保",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の医療・福祉確保について一般質問されました。",
        "status_updated_at": "2025-03-07T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "離島における医療・福祉人材確保とサービス継続が論点です。",
        "government_response_summary": "公開中の会議録では、離島の医療・福祉確保について一般質問が行われました。",
        "share_summary": "八丈町の医療・福祉をどう確保するか市民の意見を集めています。",
        "source_url": "https://www.town.hachijo.tokyo.jp/chousei/chougikai/katsushin/shingi-kekka/",
    },
    "miyake-island-disaster-life-2025-03-06": {
        "question_id": "miyake-island-disaster-life-v1",
        "assembly_id": "miyake-village",
        "municipality": "三宅村",
        "title": "離島の防災と生活基盤",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の防災と生活基盤について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "火山・台風リスクへの備えと離島生活基盤の維持が論点です。",
        "government_response_summary": "公開中の会議録では、離島の防災と生活基盤について一般質問が行われました。",
        "share_summary": "三宅村の防災と生活基盤をどう維持するか村民の意見を集めています。",
        "source_url": "https://www.vill.miyake.tokyo.jp/kakuka/gikai/",
    },
    "higashimurayama-childcare-welfare-2025-03-05": {
        "question_id": "higashimurayama-childcare-welfare-v1",
        "assembly_id": "higashimurayama-city",
        "municipality": "東村山市",
        "title": "子育て支援と地域福祉",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と地域福祉について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て世代支援と高齢者福祉の一体的な充実が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援と地域福祉について一般質問が行われました。",
        "share_summary": "東村山市の子育て支援と地域福祉をどう充実させるか市民の意見を集めています。",
        "source_url": "https://www.city.higashimurayama.tokyo.jp/gikai/gikaijoho/kensaku/index.html",
    },
    "mizuho-rural-transport-life-2025-03-06": {
        "question_id": "mizuho-rural-transport-life-v1",
        "assembly_id": "mizuho-town",
        "municipality": "瑞穂町",
        "title": "中山間地域の交通と生活支援",
        "current_status": "議会で一般質問済み",
        "status_summary": "中山間地域の交通と生活支援について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "広域分散住民への交通アクセスと生活基盤の維持が論点です。",
        "government_response_summary": "公開中の会議録では、中山間地域の交通と生活支援について一般質問が行われました。",
        "share_summary": "瑞穂町の交通と生活支援をどう充実させるか町民の意見を集めています。",
        "source_url": "https://www.town.mizuho.tokyo.jp/gikai/",
    },
    "hinode-childcare-medical-2025-09-18": {
        "question_id": "hinode-childcare-medical-v1",
        "assembly_id": "hinode-town",
        "municipality": "日の出町",
        "title": "子育て支援と地域医療",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援と地域医療について議会で審議されました。",
        "status_updated_at": "2025-09-18T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "子育て世代支援と中山間地域の医療・福祉確保が論点です。",
        "government_response_summary": "公開中の審議結果では、子育て支援と地域医療について議論が行われました。",
        "share_summary": "日の出町の子育て支援と地域医療をどう充実させるか町民の意見を集めています。",
        "source_url": "https://www.town.hinode.tokyo.jp/0000004135.html",
    },
    "hinohara-mountain-disaster-2025-08-20": {
        "question_id": "hinohara-mountain-disaster-v1",
        "assembly_id": "hinohara-village",
        "municipality": "檜原村",
        "title": "中山間地域の防災と住民支援",
        "current_status": "議会で一般質問済み",
        "status_summary": "中山間地域の防災と住民支援について一般質問されました。",
        "status_updated_at": "2025-08-20T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "山間部の防災・避難体制と過疎地域の生活支援が論点です。",
        "government_response_summary": "公開中の議会だより・会議録では、中山間地域の防災と住民支援について一般質問が行われました。",
        "share_summary": "檜原村の防災と住民支援をどう強化するか村民の意見を集めています。",
        "source_url": "https://www.vill.hinohara.tokyo.jp/category/7-0-0-0-0-0-0-0-0-0.html",
    },
    "toshima-island-life-medical-2025-03-05": {
        "question_id": "toshima-island-life-medical-v1",
        "assembly_id": "toshima-village",
        "municipality": "利島村",
        "title": "離島の生活基盤と医療体制",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の生活基盤と医療体制について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "小規模離島における生活インフラと医療・福祉の確保が論点です。",
        "government_response_summary": "公開中の議会情報では、離島の生活基盤と医療体制について一般質問が行われました。",
        "share_summary": "利島村の生活基盤と医療体制をどう維持するか村民の意見を集めています。",
        "source_url": "https://www.toshimamura.org/about/assembly.html",
    },
    "niijima-island-transport-tourism-2025-03-06": {
        "question_id": "niijima-island-transport-tourism-v1",
        "assembly_id": "niijima-village",
        "municipality": "新島村",
        "title": "離島交通と観光・産業振興",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島交通と観光・産業振興について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "離島航路の維持と観光・地域産業の持続的発展が論点です。",
        "government_response_summary": "公開中の会議録では、離島交通と観光・産業振興について一般質問が行われました。",
        "share_summary": "新島村の離島交通と観光・産業をどう振興するか村民の意見を集めています。",
        "source_url": "https://www.niijima.com/gikai/",
    },
    "kozushima-island-medical-welfare-2025-03-07": {
        "question_id": "kozushima-island-medical-welfare-v1",
        "assembly_id": "kozushima-village",
        "municipality": "神津島村",
        "title": "離島の医療・福祉確保",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の医療・福祉確保について一般質問されました。",
        "status_updated_at": "2025-03-07T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "離島における医療・福祉人材確保とサービス継続が論点です。",
        "government_response_summary": "公開中の会議録・議会だよりでは、離島の医療・福祉確保について一般質問が行われました。",
        "share_summary": "神津島村の医療・福祉をどう確保するか村民の意見を集めています。",
        "source_url": "https://www.vill.kouzushima.tokyo.jp/category/gikai/",
    },
    "mikurajima-island-life-base-2025-03-05": {
        "question_id": "mikurajima-island-life-base-v1",
        "assembly_id": "mikurajima-village",
        "municipality": "御蔵島村",
        "title": "離島の生活基盤維持",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の生活基盤維持について一般質問されました。",
        "status_updated_at": "2025-03-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "小規模離島の人口減少と生活インフラ・人材確保が論点です。",
        "government_response_summary": "公開中の議会情報では、離島の生活基盤維持について一般質問が行われました。",
        "share_summary": "御蔵島村の生活基盤をどう維持するか村民の意見を集めています。",
        "source_url": "https://www.vill.mikurasima.tokyo.jp/section/gyosei/gikai.html",
    },
    "aogashima-island-disaster-infra-2025-09-05": {
        "question_id": "aogashima-island-disaster-infra-v1",
        "assembly_id": "aogashima-village",
        "municipality": "青ヶ島村",
        "title": "離島の防災と生活インフラ",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の防災と生活インフラについて議会で審議されました。",
        "status_updated_at": "2025-09-05T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "火山・台風リスクへの備えと離島生活インフラの維持が論点です。",
        "government_response_summary": "公開中の広報・議決一覧では、離島の防災と生活インフラについて審議が行われました。",
        "share_summary": "青ヶ島村の防災と生活インフラをどう維持するか村民の意見を集めています。",
        "source_url": "https://www.vill.aogashima.tokyo.jp/",
    },
    "ogasawara-island-medical-education-2025-03-06": {
        "question_id": "ogasawara-island-medical-education-v1",
        "assembly_id": "ogasawara-village",
        "municipality": "小笠原村",
        "title": "離島の医療・教育・生活基盤",
        "current_status": "議会で一般質問済み",
        "status_summary": "離島の医療・教育・生活基盤について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "遠隔離島における医療・教育アクセスと生活基盤の確保が論点です。",
        "government_response_summary": "公開中の会議録では、離島の医療・教育・生活基盤について一般質問が行われました。",
        "share_summary": "小笠原村の医療・教育・生活基盤をどう維持するか村民の意見を集めています。",
        "source_url": "https://www.vill.ogasawara.tokyo.jp/gikai/",
    },
    "nishitokyo-merged-childcare-2025-03-07": {
        "question_id": "nishitokyo-merged-childcare-v1",
        "assembly_id": "nishitokyo-city",
        "municipality": "西東京市",
        "title": "合併後の子育て支援一体運営",
        "current_status": "議会で一般質問済み",
        "status_summary": "合併後の子育て支援一体運営について一般質問されました。",
        "status_updated_at": "2025-03-07T00:00:00+09:00",
        "status_checked_at": "2026-09-02T18:00:00+09:00",
        "problem_summary": "合併後の子育て支援の地域差とサービス統合が論点です。",
        "government_response_summary": "公開中の会議録では、合併後の子育て支援一体運営について一般質問が行われました。",
        "share_summary": "西東京市の子育て支援をどう一体的に運営するか市民の意見を集めています。",
        "source_url": "https://www.city.nishitokyo.tokyo.dbsr.jp/index.php/",
    },
    "chiyoda-teen-support-allowance-2025-06-10": {
        "question_id": "chiyoda-teen-support-allowance-v1",
        "assembly_id": "chiyoda-ward",
        "municipality": "千代田区",
        "title": "中高生世代応援手当",
        "current_status": "議会で一般質問済み",
        "status_summary": "中高生世代応援手当について代表質問されました。",
        "status_updated_at": "2025-06-10T00:00:00+09:00",
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "中高生世代の教育費・生活費負担と、支援制度の政策効果の検証が論点です。",
        "government_response_summary": "公開中の会議録では、中高生世代応援手当の目的と位置づけについて代表質問・答弁が行われました。",
        "share_summary": "千代田区の中高生世代応援手当をどう位置づけるか市民の意見を集めています。",
        "source_url": "https://www.city.chiyoda.tokyo.dbsr.jp/index.php/",
    },
    "bunkyo-childcare-support-2025-03-06": {
        "question_id": "bunkyo-childcare-support-v1",
        "assembly_id": "bunkyo-ward",
        "municipality": "文京区",
        "title": "子育て支援施策の充実",
        "current_status": "議会で一般質問済み",
        "status_summary": "子育て支援施策の充実について一般質問されました。",
        "status_updated_at": "2025-03-06T00:00:00+09:00",
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "保育・学童需要と、子育て世代への経済的支援の優先順位が論点です。",
        "government_response_summary": "公開中の会議録では、子育て支援施策の充実について一般質問が行われました。",
        "share_summary": "文京区の子育て支援をどう充実させるか市民の意見を集めています。",
        "source_url": "https://www.city.bunkyo.tokyo.dbsr.jp/index.php/",
    },
    "koganei-nursery-safety-2025-02-28": {
        "question_id": "koganei-nursery-safety-v1",
        "assembly_id": "koganei-city",
        "municipality": "小金井市",
        "title": "保育施設の指定管理者と安全",
        "current_status": "議会で一般質問済み",
        "status_summary": "保育施設の指定管理者と安全について審議されました。",
        "status_updated_at": "2025-02-28T00:00:00+09:00",
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "指定管理者選定における事故報告と評価の公平性が論点です。",
        "government_response_summary": "公開中の会議録では、指定管理者選定と保育施設の安全について審議が行われました。",
        "share_summary": "小金井市の保育施設の安全と指定管理者制度をどう見直すか市民の意見を集めています。",
        "source_url": "https://www.city.koganei.tokyo.dbsr.jp/index.php/?Template=document&CabinetName=kb&Part=5&TermStart=2025-02-01",
    },
    "hino-station-barrier-free-2025-03-04": {
        "question_id": "hino-station-barrier-free-v1",
        "assembly_id": "hino-city",
        "municipality": "日野市",
        "title": "日野駅のバリアフリー改善",
        "current_status": "議会で一般質問済み",
        "status_summary": "日野駅のバリアフリー改善について一般質問されました。",
        "status_updated_at": "2025-03-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "日野駅の転落事故多発とバリアフリー未達成が論点です。",
        "government_response_summary": "公開中の会議録では、日野駅の改善とバリアフリー化について一般質問が行われました。",
        "share_summary": "日野駅のバリアフリー化をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.hino.tokyo.dbsr.jp/index.php/",
    },
    "tama-school-safety-bullying-2025-09-01": {
        "question_id": "tama-school-safety-bullying-v1",
        "assembly_id": "tama-city",
        "municipality": "多摩市",
        "title": "学校生活の安全といじめ対策",
        "current_status": "議会で一般質問済み",
        "status_summary": "学校生活の安全といじめ対策について一般質問されました。",
        "status_updated_at": "2025-09-01T00:00:00+09:00",
        "status_checked_at": "2026-09-02T17:00:00+09:00",
        "problem_summary": "いじめ問題と学校生活の安全確保、性犯罪から子どもを守る取組みが論点です。",
        "government_response_summary": "公開中の会議録では、学校生活の安全といじめ対策について一般質問が行われました。",
        "share_summary": "多摩市の学校生活の安全をどう確保するか市民の意見を集めています。",
        "source_url": "https://www.city.tama.tokyo.dbsr.jp/index.php/",
    },
    "koto-disaster-townplan-2025-06-12": {
        "question_id": "koto-disaster-townplan-v1",
        "assembly_id": "koto-ward",
        "municipality": "江東区",
        "title": "防災・まちづくり対策の強化",
        "current_status": "議会で一般質問済み",
        "status_summary": "防災・まちづくり対策について本会議で質問されました。",
        "status_updated_at": "2025-06-12T00:00:00+09:00",
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "大規模災害への備えと臨海部を含む地域防災体制が論点です。",
        "government_response_summary": "公開中の会議録では、防災・まちづくり対策特別委員会等で防災施策が審議されました。",
        "share_summary": "江東区の防災・まちづくり対策をどう強化するか市民の意見を集めています。",
        "source_url": "https://www.city.koto.tokyo.dbsr.jp/index.php/",
    },
    "musashino-school-rebuild-2025-12-04": {
        "question_id": "musashino-school-rebuild-v1",
        "assembly_id": "musashino-city",
        "municipality": "武蔵野市",
        "title": "学校改築と小・中学校の適正規模",
        "current_status": "議会で一般質問済み",
        "status_summary": "学校改築と適正規模について一般質問されました。",
        "status_updated_at": "2025-12-04T00:00:00+09:00",
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "老朽化校舎の改築と適正規模化、仮設校舎期間中の課題が論点です。",
        "government_response_summary": "公開中の会議録では、学校改築と小・中学校の適正規模について一般質問が行われました。",
        "share_summary": "武蔵野市の学校改築と適正規模をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.musashino.tokyo.dbsr.jp/",
    },
    "fuchu-base-redevelopment-2025-09-03": {
        "question_id": "fuchu-base-redevelopment-v1",
        "assembly_id": "fuchu-city",
        "municipality": "府中市",
        "title": "府中基地跡地の活用",
        "current_status": "議会で一般質問済み",
        "status_summary": "府中基地跡地の活用について一般質問されました。",
        "status_updated_at": "2025-09-03T00:00:00+09:00",
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "基地跡地の解体工事と今後の土地利用、市民への説明が論点です。",
        "government_response_summary": "公開中の会議録では、府中基地跡地の今後の予定について一般質問が行われました。",
        "share_summary": "府中基地跡地をどう活用するか市民の意見を集めています。",
        "source_url": "https://www.city.fuchu.tokyo.dbsr.jp/index.php/",
    },
    "mitaka-inclusive-disaster-2024-02-27": {
        "question_id": "mitaka-inclusive-disaster-v1",
        "assembly_id": "mitaka-city",
        "municipality": "三鷹市",
        "title": "インクルーシブ防災の徹底",
        "current_status": "議会で一般質問済み",
        "status_summary": "インクルーシブ防災の徹底について一般質問されました。",
        "status_updated_at": "2024-02-27T00:00:00+09:00",
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "福祉避難所の整備と、誰一人取り残さない防災体制が論点です。",
        "government_response_summary": "公開中の会議録では、インクルーシブ防災について一般質問が行われました。",
        "share_summary": "三鷹市のインクルーシブ防災をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.gikai.city.mitaka.tokyo.jp/reference/2024/custom1/no4_text.html",
    },
    "kokubunji-peace-education-2025-02-28": {
        "question_id": "kokubunji-peace-education-v1",
        "assembly_id": "kokubunji-city",
        "municipality": "国分寺市",
        "title": "平和教育と校外学習の中立性",
        "current_status": "議会で一般質問済み",
        "status_summary": "平和教育と校外学習の政治的中立性について審議されました。",
        "status_updated_at": "2025-02-28T00:00:00+09:00",
        "status_checked_at": "2026-09-02T16:00:00+09:00",
        "problem_summary": "校外学習の内容と学校施設のイベント利用の公平性が論点です。",
        "government_response_summary": "公開中の会議録では、平和教育と校外学習の在り方について陳情・審議が行われました。",
        "share_summary": "国分寺市の平和教育と校外学習をどう進めるか市民の意見を集めています。",
        "source_url": "https://www.city.kokubunji.tokyo.dbsr.jp/index.php/",
    },
    "musashimurayama-city-auto-2024-03-01-1250-4-12": {
        "question_id": "musashimurayama-elderly-depression-v1",
        "assembly_id": "musashimurayama-city",
        "municipality": "武蔵村山市",
        "title": "高齢者のうつ病対策",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "高齢者のうつ病対策について質問・答弁されました。",
        "status_updated_at": "2024-03-01T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "高齢者のメンタルヘルスと予防支援が論点です。",
        "government_response_summary": "公開中の会議録では、高齢者のうつ病対策について質問・答弁が行われました。",
        "share_summary": "武蔵村山市の高齢者うつ病対策をどう進めるか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/musashimurayama/SpMinuteView.html?council_id=1250&schedule_id=4",
    },
    "tachikawa-city-auto-2024-02-27-2629-4-62": {
        "question_id": "tachikawa-education-support-plans-v1",
        "assembly_id": "tachikawa-city",
        "municipality": "立川市",
        "title": "個別の教育支援計画と個別の指導計画",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "個別の教育支援計画と指導計画の作成・引き継ぎについて質問・答弁されました。",
        "status_updated_at": "2024-02-27T00:00:00+09:00",
        "status_checked_at": "2026-09-02T15:00:00+09:00",
        "problem_summary": "特別な支援を必要とする児童生徒への計画作成と学校間引き継ぎが論点です。",
        "government_response_summary": "立川市は個別の教育支援計画・指導計画の作成状況と保護者意向確認について答弁しました。",
        "share_summary": "立川市の個別の教育支援計画・指導計画をどう作成・引き継ぐか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/tachikawa/SpMinuteView.html?council_id=2629&schedule_id=4",
    },
}

logger = logging.getLogger(__name__)


def _document_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _follow_document_id(anonymous_user_id: str, issue_id: str) -> str:
    return _document_id(anonymous_user_id, issue_id)


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _is_unread(status_updated_at: str, last_viewed_status_at: Optional[str]) -> bool:
    if not last_viewed_status_at:
        return False
    try:
        status_updated = datetime.fromisoformat(status_updated_at.replace("Z", "+00:00"))
        last_viewed = datetime.fromisoformat(last_viewed_status_at.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(
            "Invalid issue status timestamp (status_updated_at=%s, last_viewed_status_at=%s)",
            status_updated_at,
            last_viewed_status_at,
        )
        return False
    if status_updated.tzinfo is None:
        status_updated = status_updated.replace(tzinfo=timezone.utc)
    if last_viewed.tzinfo is None:
        last_viewed = last_viewed.replace(tzinfo=timezone.utc)
    return status_updated > last_viewed


def _verified_status_updates(
    issue: Dict[str, Any], stored_updates: Any = None
) -> List[Dict[str, str]]:
    updates = stored_updates if isinstance(stored_updates, list) else []
    verified = []
    for update in updates:
        if not isinstance(update, dict) or update.get("verified") is not True:
            continue
        updated_at = _isoformat(update.get("updated_at"))
        summary = str(update.get("summary") or "").strip()
        if not updated_at or not summary:
            continue
        verified.append(
            {
                "updated_at": updated_at,
                "status": str(update.get("status") or issue["current_status"]),
                "summary": summary,
                "source_url": str(update.get("source_url") or issue["source_url"]),
            }
        )
    if not verified:
        verified.append(
            {
                "updated_at": str(issue["status_updated_at"]),
                "status": str(issue["current_status"]),
                "summary": str(issue["status_summary"]),
                "source_url": str(issue["source_url"]),
            }
        )
    verified.sort(key=lambda item: item["updated_at"])
    return verified


def _read_issue_status(client: Any, issue_id: str) -> Dict[str, Any]:
    fallback = ISSUE_STATUSES[issue_id]
    snapshot = client.collection(ISSUES_COLLECTION).document(issue_id).get()
    if not snapshot.exists:
        return {**fallback, "status_updates": _verified_status_updates(fallback)}
    stored = snapshot.to_dict() or {}
    issue = {
        key: str(stored.get(key) or fallback[key])
        for key in fallback
    }
    issue["status_updates"] = _verified_status_updates(
        issue, stored.get("status_updates")
    )
    return issue


def _ensure_issue_status(client: Any, issue_id: str) -> Dict[str, Any]:
    reference = client.collection(ISSUES_COLLECTION).document(issue_id)
    snapshot = reference.get()
    if snapshot.exists:
        return _read_issue_status(client, issue_id)
    issue = ISSUE_STATUSES[issue_id]
    status_updates = _verified_status_updates(issue)
    reference.set({
        "issue_id": issue_id,
        **issue,
        "status_updates": [{**update, "verified": True} for update in status_updates],
    })
    return {**issue, "status_updates": status_updates}


def _public_follow(
    data: Dict[str, Any], issue: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    issue_id = str(data.get("issue_id") or "")
    issue = issue or ISSUE_STATUSES[issue_id]
    last_viewed_status_at = _isoformat(data.get("last_viewed_status_at"))
    return {
        "issue_id": issue_id,
        "assembly_id": issue["assembly_id"],
        "municipality": issue["municipality"],
        "title": issue["title"],
        "current_status": issue["current_status"],
        "status_summary": issue["status_summary"],
        "status_updated_at": issue["status_updated_at"],
        "status_checked_at": issue["status_checked_at"],
        "problem_summary": issue["problem_summary"],
        "government_response_summary": issue["government_response_summary"],
        "share_summary": issue["share_summary"],
        "source_url": issue["source_url"],
        "question_id": issue["question_id"],
        "status_updates": issue.get("status_updates") or _verified_status_updates(issue),
        "created_at": _isoformat(data.get("created_at")),
        "last_viewed_status_at": last_viewed_status_at,
        "notification_enabled": bool(data.get("notification_enabled", False)),
        "has_new_status": _is_unread(issue["status_updated_at"], last_viewed_status_at),
    }


def put_issue_follow(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        issue = _ensure_issue_status(client, issue_id)
        snapshot = reference.get()
        previous = snapshot.to_dict() if snapshot.exists else {}
        now = datetime.now(timezone.utc)
        payload = {
            "issue_id": issue_id,
            "anonymous_user_id": anonymous_user_id,
            "created_at": previous.get("created_at") or now,
            "last_viewed_status_at": (
                previous.get("last_viewed_status_at")
                or issue["status_updated_at"]
            ),
            "notification_enabled": bool(previous.get("notification_enabled", False)),
            "updated_at": now,
        }
        reference.set(payload)
    except Exception as exc:
        logger.exception("Firestore follow PUT failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow PUT failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "created": not snapshot.exists,
        "follow": _public_follow(payload, issue),
    }


def _follow_query(client: Any, anonymous_user_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(FOLLOWS_COLLECTION)
        .where(filter=FieldFilter("anonymous_user_id", "==", anonymous_user_id))
        .stream()
    )


def list_issue_follows(*, anonymous_user_id: str) -> Dict[str, Any]:
    client = get_firestore_client()
    try:
        snapshots = list(_follow_query(client, anonymous_user_id))
        follows = []
        for snapshot in snapshots:
            data = snapshot.to_dict() or {}
            issue_id = data.get("issue_id")
            if issue_id not in ISSUE_STATUSES:
                continue
            issue = _read_issue_status(client, issue_id)
            follow = _public_follow(data, issue)
            citizen_response = get_citizen_question_snapshot(
                issue_id=issue_id,
                question_id=issue["question_id"],
                anonymous_user_id=anonymous_user_id,
            )
            follow["my_response"] = citizen_response["my_response"]
            follow["current_response_count"] = citizen_response["aggregate"][
                "total_responses"
            ]
            follows.append(follow)
    except ReactionStoreError:
        raise
    except Exception as exc:
        logger.exception("Firestore follow GET failed")
        raise ReactionStoreError("Firestore follow GET failed") from exc
    follows.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "follows": follows,
        "total": len(follows),
        "unread_total": sum(1 for follow in follows if follow["has_new_status"]),
    }


def mark_issue_follow_viewed(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        snapshot = reference.get()
        if not snapshot.exists:
            raise ValueError("Follow not found")
        payload = snapshot.to_dict() or {}
        payload["last_viewed_status_at"] = datetime.now(timezone.utc)
        payload["updated_at"] = datetime.now(timezone.utc)
        reference.set(payload)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Firestore follow viewed update failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow viewed update failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "follow": _public_follow(payload, _read_issue_status(client, issue_id)),
    }


def delete_issue_follow(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        reference.delete()
    except Exception as exc:
        logger.exception("Firestore follow DELETE failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow DELETE failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "deleted": True,
    }


def _followers_for_issue(client: Any, issue_id: str) -> List[Dict[str, Any]]:
    followers = []
    for snapshot in client.collection(FOLLOWS_COLLECTION).stream():
        data = snapshot.to_dict() or {}
        if data.get("issue_id") != issue_id:
            continue
        anonymous_user_id = str(data.get("anonymous_user_id") or "").strip()
        if anonymous_user_id:
            followers.append(data)
    return followers


def notify_followers_of_status_update(issue_id: str, issue: Dict[str, Any]) -> Dict[str, Any]:
    """Deliver in-app (and optional LINE) alerts when a followed issue status changes."""
    client = get_firestore_client()
    try:
        followers = _followers_for_issue(client, issue_id)
    except Exception as exc:
        logger.exception("Failed to list followers for issue_id=%s", issue_id)
        raise ReactionStoreError("Failed to list issue followers") from exc

    message = (
        f"フォロー中の議題「{issue['title']}」に新しい動き: "
        f"{issue['status_summary']}"
    )
    notification_ids: List[str] = []
    line_push_sent = 0
    line_push_skipped = 0
    for follower in followers:
        anonymous_user_id = str(follower["anonymous_user_id"])
        result = create_notification(
            anonymous_user_id=anonymous_user_id,
            issue_id=issue_id,
            message=message,
            subscription_id="follow-status",
        )
        notification_ids.append(result["notification"]["notification_id"])
        from line_notification_store import notify_line_for_match

        push_result = notify_line_for_match(
            _user_document_id(anonymous_user_id),
            {
                "issue_id": issue_id,
                "title": issue["title"],
                "municipality": issue.get("municipality", ""),
            },
        )
        if push_result.get("status") == "sent":
            line_push_sent += 1
        else:
            line_push_skipped += 1

    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "follower_count": len(followers),
        "notification_count": len(notification_ids),
        "notification_ids": notification_ids,
        "line_push_sent": line_push_sent,
        "line_push_skipped": line_push_skipped,
    }


def append_verified_status_update(
    issue_id: str,
    *,
    status: str,
    summary: str,
    source_url: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Append a verified policy-progress update and notify all followers."""
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    normalized_status = status.strip()
    normalized_summary = summary.strip()
    if not normalized_status or not normalized_summary:
        raise ValueError("status and summary are required")
    client = get_firestore_client()
    issue = _ensure_issue_status(client, issue_id)
    timestamp = updated_at or datetime.now(timezone.utc).isoformat()
    update = {
        "updated_at": timestamp,
        "status": normalized_status,
        "summary": normalized_summary,
        "source_url": source_url or issue["source_url"],
        "verified": True,
    }
    existing_updates = [
        item for item in (issue.get("status_updates") or [])
        if isinstance(item, dict)
    ]
    stored_updates = [
        {
            "updated_at": item["updated_at"],
            "status": item["status"],
            "summary": item["summary"],
            "source_url": item["source_url"],
            "verified": True,
        }
        for item in existing_updates
    ]
    stored_updates.append(update)
    stored_updates.sort(key=lambda item: item["updated_at"])
    reference = client.collection(ISSUES_COLLECTION).document(issue_id)
    payload = {
        "issue_id": issue_id,
        **issue,
        "current_status": normalized_status,
        "status_summary": normalized_summary,
        "status_updated_at": timestamp,
        "status_checked_at": datetime.now(timezone.utc).isoformat(),
        "source_url": update["source_url"],
        "status_updates": stored_updates,
    }
    try:
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to append verified status update (issue_id=%s)", issue_id)
        raise ReactionStoreError("Failed to append verified status update") from exc

    refreshed = _read_issue_status(client, issue_id)
    delivery = notify_followers_of_status_update(issue_id, refreshed)
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "issue": {
            "current_status": refreshed["current_status"],
            "status_summary": refreshed["status_summary"],
            "status_updated_at": refreshed["status_updated_at"],
            "status_updates": refreshed["status_updates"],
        },
        "delivery": delivery,
    }
