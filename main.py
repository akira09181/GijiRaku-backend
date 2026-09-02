# main.py - GijiRaku FastAPI Server
from contextlib import asynccontextmanager
import json
import logging
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

from opendata_service import (
    get_all_assemblies,
    get_assembly_chat_dialogue,
    fetch_tokyo_catalog_datasets
)
from assembly_records import (
    get_assembly_record_stats,
    get_assembly_records,
    sync_json_snapshot_to_firestore,
)
from issue_catalog import get_issue_catalog
from reaction_store import (
    ReactionStoreError,
    get_active_reaction_storage_backend,
    list_reaction_aggregates,
    list_user_reaction_states,
    put_reaction_state,
    verify_reaction_store_connection,
)
from citizen_question_store import (
    get_citizen_question_admin_results,
    get_citizen_question_snapshot,
    put_citizen_question_response,
)
from etl_worker import (
    EtlAuthorizationError,
    EtlConfigurationError,
    authorize_etl_request,
    extract_assembly_record,
    save_extracted_record,
)
from follow_store import (
    append_verified_status_update,
    delete_issue_follow,
    list_issue_follows,
    mark_issue_follow_viewed,
    put_issue_follow,
)
from notification_store import (
    NotificationBatchAuthorizationError,
    NotificationBatchConfigurationError,
    authorize_notification_batch,
    get_user_preferences,
    list_user_notifications,
    mark_notifications_read,
    match_issue_notifications,
    run_notification_matching,
    save_user_preferences,
)
from trend_service import get_cross_assembly_trends
from lead_store import save_pro_lead
from region_request_store import save_region_request
from line_notification_store import (
    LineNotificationConfigurationError,
    LineOAuthError,
    exchange_line_login_code,
    get_line_link_status,
    link_line_user,
    unlink_line_user,
)
from semantic_search_service import (
    SemanticSearchConfigurationError,
    semantic_search,
)

logger = logging.getLogger("gijiraku.reactions")


@asynccontextmanager
async def lifespan(_: FastAPI):
    assembly_sync = sync_json_snapshot_to_firestore()
    logger.info(
        "Assembly record store ready (backend=%s, sync_status=%s)",
        assembly_sync["storage_backend"],
        assembly_sync["status"],
    )
    try:
        storage = verify_reaction_store_connection()
        logger.info(
            "Reaction store ready (backend=%s, project_id=%s, database_id=%s)",
            storage["storage_backend"],
            storage["project_id"],
            storage["database_id"],
        )
    except ReactionStoreError:
        logger.exception(
            "Reaction store startup verification failed; reaction APIs will return HTTP 500"
        )
    yield


app = FastAPI(
    title="MachiVoice API (マチボイス)",
    description="東京都オープンデータ活用 ・ 地域・生活テーマ議会情報インフラ API",
    lifespan=lifespan,
)

# Next.js (フロントエンド) からのアクセスを許可するCORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# データモデルの定義
# ---------------------------------------------------------
class TranslationRequest(BaseModel):
    question: str
    assembly_id: Optional[str] = "tokyo-metropolitan"
    discussion_id: Optional[str] = None

class AiChainStep(BaseModel):
    step_number: int
    title: str
    detail: str
    status: str = "completed"

class TranslationResponse(BaseModel):
    answer: str
    issue_id: Optional[str] = None
    speaker: str = "マチボイス AI"
    role: str = "超翻訳ナビゲーター"
    original_quote: Optional[str] = None
    timestamp: str = "12:00"
    source_url: Optional[str] = "https://catalog.data.metro.tokyo.lg.jp/"
    source_verified: bool = False
    ai_chain_steps: List[AiChainStep] = []


class AssemblyRecordExtractionRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=100_000)
    persist_to_firestore: bool = False
    model: Optional[str] = Field(default=None, max_length=100)


class AssemblyRecordExtractionResponse(BaseModel):
    ok: bool
    record: Dict[str, Any]
    stored: bool = False
    document_id: Optional[str] = None

# ---------------------------------------------------------
# 政策トラッカー 構造化 Topic Schema (ハッカソンデータ設計)
# ---------------------------------------------------------
class MunicipalityInfo(BaseModel):
    name: str
    assembly: str

class TopicSummary(BaseModel):
    what_changes: str
    who_is_affected: str
    current_status: str
    budget: str
    next_step: str

class TimelineEvent(BaseModel):
    date: str
    event: str
    status: str = "completed"

class PolicyArguments(BaseModel):
    supporting: List[str]
    concerns: List[str]

class SpeakerUtterance(BaseModel):
    speaker_name: str
    speaker_role: str
    party_name: Optional[str] = None
    committee_name: Optional[str] = None
    stance_label: str
    vote_record: Optional[str] = "未採決" # '賛成' | '反対' | '棄権' | '未採決'
    summary_quote: str
    avatar_color: str = "emerald"
    source_excerpt: Optional[str] = None
    meeting_name: Optional[str] = None
    meeting_date: Optional[str] = None
    question_type: Optional[str] = None

class TopicSource(BaseModel):
    meeting_name: str
    meeting_date: str
    speaker: str
    excerpt: str
    source_url: str
    open_data_url: str

class ClaimVerification(BaseModel):
    claim: str
    verified: bool = True
    source_excerpt_id: str

class TopicVerification(BaseModel):
    status: str = "verified"
    checked_against_source: bool = True
    confidence: float = 0.96
    claims: List[ClaimVerification] = []

class CitizenReactions(BaseModel):
    support: int = 0
    concern: int = 0
    comments: int = 0

class TopicDetailResponse(BaseModel):
    topic_id: str
    municipality: MunicipalityInfo
    title: str
    summary: TopicSummary
    timeline: List[TimelineEvent]
    arguments: PolicyArguments
    speaker_utterances: List[SpeakerUtterance] = []
    source: TopicSource
    verification: TopicVerification
    citizen_reactions: CitizenReactions
    tags: List[str]
    updated_at: str = "2026-08-20T05:00:00+09:00"

SAMPLE_TOPIC_DATA = TopicDetailResponse(
    topic_id="tokyo-ebpm-2024-06-05",
    municipality=MunicipalityInfo(name="東京都", assembly="東京都議会"),
    title="事業評価へのEBPM導入と成果重視の評価",
    summary=TopicSummary(
        what_changes="事業の設計段階から評価指標・測定方法・データ取得を組み込み、成果を検証する考え方が議論されました。",
        who_is_affected="東京都の政策・行政サービスを利用する都民と、事業を設計・評価する行政部門",
        current_status="2024年6月5日の東京都議会本会議で質疑・答弁済み",
        budget="事業評価による財源確保と成果重視の評価制度について議論",
        next_step="評価制度を継続的に見直し、都民サービス向上と財源確保につなげる方針"
    ),
    timeline=[
        TimelineEvent(date="2024-06-05", event="福島りえこ議員が事業評価へのEBPM導入を質問", status="completed"),
        TimelineEvent(date="2024-06-05", event="小池知事が成果重視の評価制度について答弁", status="completed")
    ],
    arguments=PolicyArguments(
        supporting=[
            "政策目的に対応した成果指標を事前に設計できる",
            "データ分析を事業改善と財源確保につなげられる"
        ],
        concerns=[
            "複合要因を扱うため、統計的な分析設計が必要",
            "事業実施前から継続的にデータを取得する必要がある"
        ]
    ),
    speaker_utterances=[
        SpeakerUtterance(
            speaker_name="福島 りえこ",
            speaker_role="東京都議会議員",
            party_name="都民ファーストの会",
            committee_name="本会議",
            stance_label="課題提起",
            vote_record=None,
            summary_quote="事業の成果を正しく測るため、設計段階から評価指標と測定方法を組み込む必要があると提案しました。",
            source_excerpt="「あらかじめ事業に評価を組み込む必要があります。」",
            avatar_color="sky",
            meeting_name="令和6年第2回定例会 東京都議会会議録第9号",
            meeting_date="2024-06-05",
            question_type="一般質問"
        ),
        SpeakerUtterance(
            speaker_name="小池 百合子",
            speaker_role="東京都知事",
            party_name="行政執行部",
            committee_name="本会議・知事答弁",
            stance_label="推進",
            vote_record=None,
            summary_quote="成果重視の評価やデータ分析を活用し、都民サービス向上と財源確保につなげると答弁しました。",
            source_excerpt="「評価制度の不断の見直しで、都民のQOL向上と着実な財源確保につなげてまいります。」",
            avatar_color="emerald",
            meeting_name="令和6年第2回定例会 東京都議会会議録第9号",
            meeting_date="2024-06-05",
            question_type="知事答弁"
        )
    ],
    source=TopicSource(
        meeting_name="令和6年第2回定例会 東京都議会会議録第9号",
        meeting_date="2024-06-05",
        speaker="福島 りえこ",
        excerpt="「あらかじめ事業に評価を組み込む必要があります。」",
        source_url="https://www.gikai.metro.tokyo.lg.jp/record/proceedings/2024-2/03-07.html",
        open_data_url="https://www.gikai.metro.tokyo.lg.jp/record/"
    ),
    verification=TopicVerification(
        status="verified",
        checked_against_source=True,
        confidence=1.0,
        claims=[
            ClaimVerification(claim="事業設計段階から評価を組み込む必要性を質問", verified=True, source_excerpt_id="excerpt-001"),
            ClaimVerification(claim="成果重視の評価とデータ分析の活用を知事が答弁", verified=True, source_excerpt_id="excerpt-002")
        ]
    ),
    citizen_reactions=CitizenReactions(support=0, concern=0, comments=0),
    tags=["EBPM", "事業評価", "オープンデータ"],
    updated_at="2026-08-24T00:00:00+09:00"
)

# ---------------------------------------------------------
# APIエンドポイントの定義
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "ok", "message": "GijiRaku API 稼働中"}

@app.get("/api/assemblies")
def get_assemblies():
    """地図にピン留めする東京都の自治体議会一覧を取得"""
    assemblies = get_all_assemblies()
    return {"status": "success", "count": len(assemblies), "data": assemblies}

@app.get("/api/topics")
def list_topics(municipality: Optional[str] = None, category: Optional[str] = None):
    """トップページおよび地域一覧用 構造化議題リスト取得 API"""
    return {"status": "success", "count": 1, "data": [SAMPLE_TOPIC_DATA]}

@app.get("/api/topics/{topic_id}", response_model=TopicDetailResponse)
def get_topic_detail(topic_id: str):
    """3分解説画面用 構造化議題詳細（原文・検証・時間軸・論点全データ）取得 API"""
    return SAMPLE_TOPIC_DATA

@app.get("/api/assemblies/{assembly_id}/chat")
def get_assembly_chat(assembly_id: str, page: int = 1):
    """特定の議会のLINE風対話メッセージ一覧を取得（pageパラメータで過去ログ追加）"""
    dialogues = get_assembly_chat_dialogue(assembly_id, page=page)
    return {
        "status": "success",
        "data_status": "legacy_demo",
        "assembly_id": assembly_id,
        "page": page,
        "messages": dialogues,
    }

from opendata_service import record_user_opinion

class OpinionRequest(BaseModel):
    opinion_type: str  # 'agree' | 'disagree'
    comment_text: Optional[str] = None

@app.post("/api/assemblies/{assembly_id}/messages/{message_id}/opinion")
def post_opinion(assembly_id: str, message_id: str, request: OpinionRequest):
    """市民の投票（賛成/懸念）および意見コメント投稿を記録し、EBPMデータに即時反映"""
    res = record_user_opinion(
        assembly_id=assembly_id,
        message_id=message_id,
        opinion_type=request.opinion_type,
        comment_text=request.comment_text
    )
    return res

from analytics_service import get_assembly_analytics

@app.get("/api/assemblies/{assembly_id}/analytics")
def get_analytics(assembly_id: str):
    """特定議会の政党別注力テーマおよび議員向けEBPM分析を取得"""
    try:
        data = get_assembly_analytics(assembly_id)
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore analytics aggregation failed (assembly_id=%s)", assembly_id
        )
        raise HTTPException(
            status_code=500, detail="Firestore reaction store unavailable"
        ) from exc
    return {"status": "success", "data": data}


@app.get("/api/pro/trends")
def get_pro_trends(
    from_date: str,
    to_date: str,
    assembly_id: Optional[List[str]] = None,
    keyword_limit: int = 12,
):
    """Return deterministic, source-linked trend aggregates across assemblies."""
    try:
        data = get_cross_assembly_trends(
            from_date=from_date,
            to_date=to_date,
            assembly_ids=assembly_id,
            keyword_limit=keyword_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Cross-assembly trend aggregation failed")
        raise HTTPException(status_code=500, detail="Trend aggregation unavailable") from exc
    return {"status": "success", "data": data}

@app.get("/api/opendata/catalog")
def get_catalog():
    """東京都オープンデータカタログAPIの最新結果を取得"""
    datasets = fetch_tokyo_catalog_datasets()
    return {"status": "success", "datasets": datasets}


@app.post("/api/etl/extract", response_model=AssemblyRecordExtractionResponse)
def extract_assembly_record_api(
    request: AssemblyRecordExtractionRequest,
    x_etl_api_key: Optional[str] = Header(default=None),
):
    """Convert raw council transcript text into a structured JSON record and persist it."""
    try:
        authorize_etl_request(x_etl_api_key)
        record = extract_assembly_record(request.raw_text, model_name=request.model)
        stored = False
        document_id = None
        if request.persist_to_firestore:
            result = save_extracted_record(record)
            stored = result.get("ok", False)
            document_id = result.get("document_id")
        return {
            "ok": True,
            "record": record,
            "stored": stored,
            "document_id": document_id,
        }
    except EtlConfigurationError as exc:
        logger.error("ETL endpoint is disabled because ETL_API_KEY is not configured")
        raise HTTPException(status_code=503, detail="ETL endpoint is not configured") from exc
    except EtlAuthorizationError as exc:
        raise HTTPException(status_code=401, detail="Invalid ETL API key") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ETL extraction API failed")
        raise HTTPException(status_code=500, detail="ETL extraction failed") from exc


@app.get("/api/assembly-records")
def list_assembly_records(
    assembly_id: str,
    limit: int = 20,
    discussion_id: Optional[str] = None,
):
    """構造化・原文照合済み会議録を会議日の新しい順で返す。"""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try:
        data = get_assembly_records(
            assembly_id,
            limit=limit,
            discussion_id=discussion_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Assembly records not found")
    if discussion_id is not None and not data["records"]:
        raise HTTPException(status_code=404, detail="Discussion record not found")
    return {"status": "success", **data}


@app.get("/api/assembly-records/stats")
def assembly_record_stats():
    """公開中の公式会議録・構造化発言の実数を返す。"""
    stats = get_assembly_record_stats()
    stats["catalog_issue_count"] = get_issue_catalog()["total_catalog_issue_count"]
    return {"status": "success", **stats}


@app.get("/api/issues")
def list_public_issues(
    assembly_id: Optional[str] = None,
    theme: Optional[str] = None,
    stage: Optional[str] = None,
):
    """Return compact list metadata without sending full statement text."""
    return {
        "status": "success",
        **get_issue_catalog(assembly_id=assembly_id, theme=theme, stage=stage),
    }


@app.get("/api/search/semantic")
def search_public_statements(
    q: str,
    assembly_id: Optional[str] = None,
    limit: int = 8,
):
    """Search published statements by meaning while preserving source IDs."""
    try:
        return {"status": "success", **semantic_search(
            q,
            assembly_id=assembly_id,
            limit=limit,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SemanticSearchConfigurationError as exc:
        logger.warning("Semantic search is not configured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Semantic search is not configured",
        ) from exc
    except Exception as exc:
        logger.exception("Semantic search failed")
        raise HTTPException(status_code=500, detail="Semantic search unavailable") from exc

from opendata_service import perform_real_rag_inference

@app.post("/api/translate", response_model=TranslationResponse)
async def translate_giji(request: TranslationRequest):
    """ユーザーの質問に対する東京都オープンデータカタログAPIリアルタイム推論レスポンス生成"""
    try:
        q = request.question.strip()
        if not q:
            raise HTTPException(status_code=400, detail="質問内容を入力してください")

        assembly_id = request.assembly_id or "tokyo-metropolitan"
        rag_res = perform_real_rag_inference(
            q,
            assembly_id=assembly_id,
            discussion_id=request.discussion_id,
        )

        if rag_res.get("verified"):
            chain_steps = [
                AiChainStep(step_number=1, title="公式会議録取得", detail=f"{rag_res.get('assembly_name', '自治体議会')}の公式サイトから会議録本文を取得"),
                AiChainStep(step_number=2, title="発言者・所属構造化", detail="会議録本文から質問者・答弁者・会議情報を構造化"),
                AiChainStep(step_number=3, title="平易な要約", detail="発言内容を市民向けに要約"),
                AiChainStep(step_number=4, title="原文照合", detail="氏名・日付・発言・出典URLを公式会議録と照合済み")
            ]
        else:
            chain_steps = [
                AiChainStep(step_number=1, title="公開情報の対象確認", detail=f"東京都オープンデータカタログAPIで関連候補を{len(rag_res.get('live_sources', []))}件取得"),
                AiChainStep(step_number=2, title="デモ回答生成", detail="画面体験用の回答を生成"),
                AiChainStep(step_number=3, title="平易な要約", detail="行政テーマを市民向けに整理"),
                AiChainStep(step_number=4, title="個別原文照合", detail="この回答は公式会議録との個別照合対象外")
            ]

        answer_text = (
            f"💡 何が変わる？\n{rag_res['what_changes']}\n\n"
            f"📌 誰に関係する？\n{rag_res['target_audience']}\n\n"
            f"🟡 いまどの段階？\n{rag_res['current_stage']}\n\n"
            f"💰 お金・予算は？\n{rag_res['budget_info']}"
        )

        return TranslationResponse(
            answer=answer_text,
            issue_id=rag_res.get("issue_id"),
            speaker="マチボイス AI",
            role="超翻訳アシスタント",
            original_quote=rag_res['original_quote'],
            timestamp="12:00",
            source_url=rag_res['source_url'],
            source_verified=bool(rag_res.get("verified")),
            ai_chain_steps=chain_steps
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# 発言単位の市民リアクション・コメント リアルタイム集計 API
# ---------------------------------------------------------
ReactionType = Literal['agree', 'concern', 'helpful']

class ReactionCounts(BaseModel):
    agree: int = Field(default=0, ge=0)
    concern: int = Field(default=0, ge=0)
    helpful: int = Field(default=0, ge=0)

class ReactionStateRequest(BaseModel):
    discussion_id: str = Field(min_length=1)
    statement_id: str = Field(min_length=1)
    reaction_type: Optional[ReactionType] = None
    anonymous_user_id: str = Field(min_length=1)
    base_counts: ReactionCounts = Field(default_factory=ReactionCounts)


class CitizenQuestionResponseRequest(BaseModel):
    issue_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    anonymous_user_id: str = Field(min_length=1)
    selected_answer: str = Field(min_length=1)
    selected_reasons: List[str] = Field(min_length=1)
    free_text: str = Field(default="", max_length=500)


class IssueFollowRequest(BaseModel):
    issue_id: str = Field(min_length=1)
    anonymous_user_id: str = Field(min_length=1)


class UserNotificationPreferencesRequest(BaseModel):
    interest_themes: List[str] = Field(default_factory=list, max_length=20)
    municipalities: List[str] = Field(default_factory=list, max_length=20)
    keywords: List[str] = Field(default_factory=list, max_length=20)


class ProLeadRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    purpose: str = Field(default="", max_length=1000)


class RegionRequestRequest(BaseModel):
    municipality_id: str = Field(min_length=1, max_length=80)
    municipality_name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=254)
    message: str = Field(default="", max_length=500)
    anonymous_user_id: str = Field(default="", max_length=80)


class NotificationBatchRequest(BaseModel):
    issue_ids: List[str] = Field(default_factory=list, max_length=100)


class LineLinkRequest(BaseModel):
    line_user_id: str = Field(min_length=1, max_length=80)


class LineOAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)
    redirect_uri: str = Field(min_length=1, max_length=512)
    anonymous_user_id: str = Field(min_length=1, max_length=80)


class NotificationReadRequest(BaseModel):
    anonymous_user_id: str = Field(min_length=1, max_length=80)
    notification_ids: List[str] = Field(default_factory=list, max_length=100)


class IssueStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=500)
    source_url: str = Field(default="", max_length=512)
    updated_at: str = Field(default="", max_length=40)


@app.post('/api/pro/leads', status_code=201)
def create_pro_lead(request: ProLeadRequest):
    """Persist one idempotent B2B consultation lead in Firestore."""
    try:
        return save_pro_lead(**request.model_dump())
    except ReactionStoreError as exc:
        logger.exception("Pro lead save failed")
        raise HTTPException(status_code=500, detail="Lead store unavailable") from exc


@app.post('/api/region-requests', status_code=201)
def create_region_request(request: RegionRequestRequest):
    """Persist one idempotent B2C municipality rollout request in Firestore."""
    normalized_email = request.email.strip().lower()
    if normalized_email and '@' not in normalized_email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    try:
        return save_region_request(
            municipality_id=request.municipality_id,
            municipality_name=request.municipality_name,
            email=normalized_email,
            message=request.message,
            anonymous_user_id=request.anonymous_user_id,
        )
    except ReactionStoreError as exc:
        logger.exception("Region request save failed")
        raise HTTPException(status_code=500, detail="Region request store unavailable") from exc


@app.post('/api/internal/notifications/match')
def match_deployed_issue_notifications(
    request: NotificationBatchRequest,
    x_internal_api_key: Optional[str] = Header(default=None),
):
    """Protected, idempotent matching batch called after record deployment."""
    try:
        authorize_notification_batch(x_internal_api_key)
        return run_notification_matching(issue_ids=request.issue_ids)
    except NotificationBatchConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Notification batch is not configured") from exc
    except NotificationBatchAuthorizationError as exc:
        raise HTTPException(status_code=401, detail="Invalid notification batch API key") from exc
    except ReactionStoreError as exc:
        logger.exception("Notification matching batch failed")
        raise HTTPException(status_code=500, detail="Notification matching store unavailable") from exc


@app.post('/api/internal/issues/{issue_id}/status-updates')
def publish_issue_status_update(
    issue_id: str,
    request: IssueStatusUpdateRequest,
    x_internal_api_key: Optional[str] = Header(default=None),
):
    """Publish a verified policy-progress update and notify issue followers."""
    try:
        authorize_notification_batch(x_internal_api_key)
        return append_verified_status_update(
            issue_id=issue_id,
            status=request.status,
            summary=request.summary,
            source_url=request.source_url,
            updated_at=request.updated_at or None,
        )
    except NotificationBatchConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Notification batch is not configured") from exc
    except NotificationBatchAuthorizationError as exc:
        raise HTTPException(status_code=401, detail="Invalid notification batch API key") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("Issue status update publish failed (issue_id=%s)", issue_id)
        raise HTTPException(status_code=500, detail="Follow status update store unavailable") from exc


@app.put('/api/reactions')
def put_reaction(request: ReactionStateRequest):
    """匿名ユーザーの対象別リアクション状態を冪等に設定する。"""
    try:
        return put_reaction_state(
            discussion_id=request.discussion_id,
            statement_id=request.statement_id,
            reaction_type=request.reaction_type,
            anonymous_user_id=request.anonymous_user_id,
            base_counts=request.base_counts.model_dump(),
        )
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore reaction PUT failed (discussion_id=%s, statement_id=%s)",
            request.discussion_id,
            request.statement_id,
        )
        raise HTTPException(
            status_code=500, detail="Firestore reaction store unavailable"
        ) from exc

@app.get('/api/reactions')
def get_reactions(
    discussion_id: str,
    anonymous_user_id: Optional[str] = None,
    include_user_state: bool = True,
):
    """全体集計と、任意の匿名ユーザー自身の選択状態を分離して返す。"""
    if not discussion_id.strip():
        raise HTTPException(status_code=400, detail='discussion_id is required')
    normalized_user_id = (anonymous_user_id or "").strip()
    if include_user_state and not normalized_user_id:
        raise HTTPException(
            status_code=400,
            detail='anonymous_user_id is required when include_user_state is true',
        )

    try:
        aggregates = list_reaction_aggregates(discussion_id=discussion_id)
        user_reactions = (
            list_user_reaction_states(
                discussion_id=discussion_id,
                anonymous_user_id=normalized_user_id,
                statement_ids=(item['statement_id'] for item in aggregates),
            )
            if include_user_state
            else []
        )
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore reaction GET failed (discussion_id=%s)", discussion_id
        )
        raise HTTPException(
            status_code=500, detail="Firestore reaction store unavailable"
        ) from exc

    user_reaction_by_statement = {
        item['statement_id']: item['reaction_type'] for item in user_reactions
    }
    legacy_data = [
        {
            **aggregate,
            'reaction_type': user_reaction_by_statement.get(
                aggregate['statement_id']
            ),
        }
        for aggregate in aggregates
    ]

    return {
        'status': 'success',
        'storage_backend': get_active_reaction_storage_backend(),
        'discussion_id': discussion_id,
        'aggregates': aggregates,
        'user_reactions': user_reactions,
        # Kept temporarily for clients deployed before the separated response shape.
        'data': legacy_data,
    }


@app.put('/api/citizen-question-responses')
def put_citizen_question_answer(request: CitizenQuestionResponseRequest):
    """Save one issue-specific response per anonymous user in Firestore."""
    try:
        return put_citizen_question_response(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore citizen question PUT failed (issue_id=%s, question_id=%s)",
            request.issue_id,
            request.question_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Firestore citizen response store unavailable",
        ) from exc


@app.get('/api/citizen-question-responses')
def get_citizen_question_answer(
    issue_id: str,
    question_id: str,
    anonymous_user_id: Optional[str] = None,
    include_my_response: bool = True,
):
    """Return the Firestore aggregate separately from the current user's answer."""
    normalized_user_id = (anonymous_user_id or "").strip()
    if include_my_response and not normalized_user_id:
        raise HTTPException(
            status_code=400,
            detail="anonymous_user_id is required when include_my_response is true",
        )
    try:
        return get_citizen_question_snapshot(
            issue_id=issue_id,
            question_id=question_id,
            anonymous_user_id=(normalized_user_id if include_my_response else None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore citizen question GET failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Firestore citizen response store unavailable",
        ) from exc


@app.get('/api/admin/citizen-question-results')
def get_citizen_question_admin(
    issue_id: str,
    question_id: str,
):
    """Return issue-level aggregates and anonymized response details."""
    try:
        return get_citizen_question_admin_results(
            issue_id=issue_id,
            question_id=question_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception(
            "Firestore citizen question admin GET failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Firestore citizen response store unavailable",
        ) from exc


@app.put('/api/follows')
def put_follow(request: IssueFollowRequest):
    """Create one idempotent Firestore follow per anonymous user and issue."""
    try:
        return put_issue_follow(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("Firestore follow PUT failed (issue_id=%s)", request.issue_id)
        raise HTTPException(status_code=500, detail="Firestore follow store unavailable") from exc


@app.get('/api/follows')
def get_follows(anonymous_user_id: str):
    """List one anonymous user's follows enriched with current issue status."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return list_issue_follows(anonymous_user_id=anonymous_user_id)
    except ReactionStoreError as exc:
        logger.exception("Firestore follow GET failed")
        raise HTTPException(status_code=500, detail="Firestore follow store unavailable") from exc


@app.patch('/api/follows/viewed')
def mark_follow_viewed(request: IssueFollowRequest):
    """Mark status as read only when the followed issue detail is opened."""
    try:
        return mark_issue_follow_viewed(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("Firestore follow viewed update failed (issue_id=%s)", request.issue_id)
        raise HTTPException(status_code=500, detail="Firestore follow store unavailable") from exc


@app.delete('/api/follows')
def delete_follow(issue_id: str, anonymous_user_id: str):
    """Remove one anonymous user's follow without touching response data."""
    if not issue_id.strip() or not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="issue_id and anonymous_user_id are required")
    try:
        return delete_issue_follow(
            issue_id=issue_id,
            anonymous_user_id=anonymous_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("Firestore follow DELETE failed (issue_id=%s)", issue_id)
        raise HTTPException(status_code=500, detail="Firestore follow store unavailable") from exc


@app.put('/api/notifications/preferences')
def put_notification_preferences(
    request: UserNotificationPreferencesRequest,
    anonymous_user_id: str,
):
    """Save issue-interest preferences for a user so matching can be done later."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return save_user_preferences(anonymous_user_id=anonymous_user_id, preferences=request.model_dump())
    except ReactionStoreError as exc:
        logger.exception("User notification preferences save failed")
        raise HTTPException(status_code=500, detail="Notification preference store unavailable") from exc


@app.get('/api/notifications/preferences')
def get_notification_preferences(anonymous_user_id: str):
    """Return preference metadata for matching and follow-up notifications."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return get_user_preferences(anonymous_user_id=anonymous_user_id)
    except ReactionStoreError as exc:
        logger.exception("User notification preferences get failed")
        raise HTTPException(status_code=500, detail="Notification preference store unavailable") from exc


@app.get('/api/notifications/matches')
def get_notification_matches(anonymous_user_id: str):
    """Find issue records relevant to a user's configured interests and keywords."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return match_issue_notifications(anonymous_user_id=anonymous_user_id)
    except ReactionStoreError as exc:
        logger.exception("User notification match failed")
        raise HTTPException(status_code=500, detail="Notification matching store unavailable") from exc


@app.get('/api/notifications')
def get_user_notifications(anonymous_user_id: str, limit: int = 50):
    """Return in-app notifications delivered to the user."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return list_user_notifications(anonymous_user_id=anonymous_user_id, limit=limit)
    except ReactionStoreError as exc:
        logger.exception("User notification list failed")
        raise HTTPException(status_code=500, detail="Notification inbox store unavailable") from exc


@app.patch('/api/notifications/read')
def patch_notifications_read(request: NotificationReadRequest):
    """Mark one or all unread notifications as read."""
    try:
        return mark_notifications_read(
            anonymous_user_id=request.anonymous_user_id,
            notification_ids=request.notification_ids or None,
        )
    except ReactionStoreError as exc:
        logger.exception("User notification read update failed")
        raise HTTPException(status_code=500, detail="Notification inbox store unavailable") from exc


@app.get('/api/notifications/line/status')
def get_line_notification_status(anonymous_user_id: str):
    """Return whether the user has linked LINE for push notifications."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return get_line_link_status(anonymous_user_id=anonymous_user_id)
    except ReactionStoreError as exc:
        logger.exception("LINE link status get failed")
        raise HTTPException(status_code=500, detail="LINE link store unavailable") from exc


@app.put('/api/notifications/line/link')
def put_line_notification_link(
    request: LineLinkRequest,
    anonymous_user_id: str,
):
    """Link a LINE user id to the anonymous browser profile for push delivery."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return link_line_user(
            anonymous_user_id=anonymous_user_id,
            line_user_id=request.line_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("LINE link save failed")
        raise HTTPException(status_code=500, detail="LINE link store unavailable") from exc


@app.delete('/api/notifications/line/link')
def delete_line_notification_link(anonymous_user_id: str):
    """Remove the LINE link for push notifications."""
    if not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail="anonymous_user_id is required")
    try:
        return unlink_line_user(anonymous_user_id=anonymous_user_id)
    except ReactionStoreError as exc:
        logger.exception("LINE link delete failed")
        raise HTTPException(status_code=500, detail="LINE link store unavailable") from exc


@app.post('/api/notifications/line/oauth/callback')
def complete_line_notification_oauth(request: LineOAuthCallbackRequest):
    """Exchange a LINE Login authorization code and persist the link."""
    try:
        profile = exchange_line_login_code(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )
        return link_line_user(
            anonymous_user_id=request.anonymous_user_id,
            line_user_id=profile["line_user_id"],
            display_name=profile.get("display_name"),
        )
    except LineNotificationConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LineOAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ReactionStoreError as exc:
        logger.exception("LINE OAuth callback failed")
        raise HTTPException(status_code=500, detail="LINE link store unavailable") from exc


class UtteranceReactionRequest(BaseModel):
    reaction_type: str # 'agree' | 'concern' | 'helpful'
    speaker_name: Optional[str] = None

class UtteranceCommentRequest(BaseModel):
    user_label: Optional[str] = "市民（匿名）"
    comment_text: str
    speaker_name: Optional[str] = None

# コメントは現行リアクション集計とは分離する。リアクションはFirestore以外へ保存しない。
UTTERANCE_COMMENTS_DB: Dict[str, Dict[str, Any]] = {}

def get_or_create_utterance_data(utt_id: str) -> Dict[str, Any]:
    if utt_id not in UTTERANCE_COMMENTS_DB:
        UTTERANCE_COMMENTS_DB[utt_id] = {
            "utt_id": utt_id,
            "comments": []
        }
    return UTTERANCE_COMMENTS_DB[utt_id]

@app.post("/api/statements/{statement_id}/reaction")
def post_statement_reaction(statement_id: str, req: UtteranceReactionRequest):
    """廃止済み。リアクションはPUT /api/reactionsでFirestoreへ保存する。"""
    raise HTTPException(
        status_code=410,
        detail="Use PUT /api/reactions; in-memory reaction storage is disabled",
    )

@app.post("/api/statements/{statement_id}/comment")
def post_statement_comment(statement_id: str, req: UtteranceCommentRequest):
    """個々の議員・首長の発言への1行匿名理由・コメントを記録"""
    if not req.comment_text or not req.comment_text.strip():
        raise HTTPException(status_code=400, detail="コメント内容を入力してください")

    utt_data = get_or_create_utterance_data(statement_id)
    user_label = req.user_label or "市民（匿名）"
    new_comment = {"user": user_label, "text": req.comment_text.strip()}
    utt_data["comments"].append(new_comment)

    return {
        "status": "success",
        "statement_id": statement_id,
        "comments": utt_data["comments"],
        "total_comments": len(utt_data["comments"])
    }

@app.get("/api/statements/{statement_id}/reactions")
def get_statement_reactions(statement_id: str):
    """廃止済み。リアクションはGET /api/reactionsから取得する。"""
    raise HTTPException(
        status_code=410,
        detail="Use GET /api/reactions; in-memory reaction storage is disabled",
    )
