# main.py - GijiRaku FastAPI Server
import os
import json
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

from opendata_service import (
    get_all_assemblies,
    get_assembly_chat_dialogue,
    fetch_tokyo_catalog_datasets
)
from assembly_records import get_assembly_records

app = FastAPI(title="MachiVoice API (マチボイス)", description="東京都オープンデータ活用 ・ 地域・生活テーマ議会情報インフラ API")

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

class AiChainStep(BaseModel):
    step_number: int
    title: str
    detail: str
    status: str = "completed"

class TranslationResponse(BaseModel):
    answer: str
    speaker: str = "マチボイス AI"
    role: str = "超翻訳ナビゲーター"
    original_quote: Optional[str] = None
    timestamp: str = "12:00"
    source_url: Optional[str] = "https://catalog.data.metro.tokyo.lg.jp/"
    source_verified: bool = False
    ai_chain_steps: List[AiChainStep] = []

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
    support: int = 42
    concern: int = 3
    comments: int = 1

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
    return {"status": "success", "assembly_id": assembly_id, "page": page, "messages": dialogues}

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
    data = get_assembly_analytics(assembly_id)
    return {"status": "success", "data": data}

@app.get("/api/opendata/catalog")
def get_catalog():
    """東京都オープンデータカタログAPIの最新結果を取得"""
    datasets = fetch_tokyo_catalog_datasets()
    return {"status": "success", "datasets": datasets}

@app.get("/api/assembly-records")
def list_assembly_records(assembly_id: str, limit: int = 20):
    """構造化・原文照合済み会議録を会議日の新しい順で返す。"""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try:
        data = get_assembly_records(assembly_id, limit=limit)
    except KeyError:
        raise HTTPException(status_code=404, detail="Assembly records not found")
    return {"status": "success", **data}

from opendata_service import perform_real_rag_inference

@app.post("/api/translate", response_model=TranslationResponse)
async def translate_giji(request: TranslationRequest):
    """ユーザーの質問に対する東京都オープンデータカタログAPIリアルタイム推論レスポンス生成"""
    try:
        q = request.question.strip()
        if not q:
            raise HTTPException(status_code=400, detail="質問内容を入力してください")

        assembly_id = request.assembly_id or "tokyo-metropolitan"
        rag_res = perform_real_rag_inference(q, assembly_id=assembly_id)

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

REACTIONS_DB_PATH = Path(
    os.getenv(
        'GIJIRAKU_REACTIONS_DB_PATH',
        str(Path(__file__).resolve().parent / 'data' / 'reactions.sqlite3')
    )
)

def get_reactions_connection() -> sqlite3.Connection:
    REACTIONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(REACTIONS_DB_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 5000')
    return connection

def initialize_reactions_db() -> None:
    with get_reactions_connection() as connection:
        connection.execute('PRAGMA journal_mode = WAL')
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reaction_targets (
                discussion_id TEXT NOT NULL,
                statement_id TEXT NOT NULL,
                agree_base INTEGER NOT NULL DEFAULT 0 CHECK (agree_base >= 0),
                concern_base INTEGER NOT NULL DEFAULT 0 CHECK (concern_base >= 0),
                helpful_base INTEGER NOT NULL DEFAULT 0 CHECK (helpful_base >= 0),
                PRIMARY KEY (discussion_id, statement_id)
            );

            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id TEXT NOT NULL,
                statement_id TEXT NOT NULL,
                reaction_type TEXT NOT NULL
                    CHECK (reaction_type IN ('agree', 'concern', 'helpful')),
                anonymous_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE (discussion_id, statement_id, anonymous_user_id),
                FOREIGN KEY (discussion_id, statement_id)
                    REFERENCES reaction_targets (discussion_id, statement_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_reactions_target_type
                ON reactions (discussion_id, statement_id, reaction_type);
            """
        )

def get_reaction_counts(
    connection: sqlite3.Connection,
    discussion_id: str,
    statement_id: str,
) -> Dict[str, int]:
    row = connection.execute(
        """
        SELECT
            targets.agree_base + COUNT(CASE WHEN reactions.reaction_type = 'agree' THEN 1 END) AS agree_count,
            targets.concern_base + COUNT(CASE WHEN reactions.reaction_type = 'concern' THEN 1 END) AS concern_count,
            targets.helpful_base + COUNT(CASE WHEN reactions.reaction_type = 'helpful' THEN 1 END) AS helpful_count
        FROM reaction_targets AS targets
        LEFT JOIN reactions
          ON reactions.discussion_id = targets.discussion_id
         AND reactions.statement_id = targets.statement_id
        WHERE targets.discussion_id = ? AND targets.statement_id = ?
        GROUP BY targets.discussion_id, targets.statement_id
        """,
        (discussion_id, statement_id),
    ).fetchone()
    if row is None:
        return {'agree': 0, 'concern': 0, 'helpful': 0}
    return {
        'agree': row['agree_count'],
        'concern': row['concern_count'],
        'helpful': row['helpful_count'],
    }


def get_live_reaction_counts(
    connection: sqlite3.Connection,
    discussion_id: str,
    statement_id: str,
) -> Dict[str, int]:
    """デモ初期値を除き、住民がAPI経由で送信した件数だけを返す。"""
    row = connection.execute(
        """
        SELECT
            COUNT(CASE WHEN reaction_type = 'agree' THEN 1 END) AS agree_count,
            COUNT(CASE WHEN reaction_type = 'concern' THEN 1 END) AS concern_count,
            COUNT(CASE WHEN reaction_type = 'helpful' THEN 1 END) AS helpful_count
        FROM reactions
        WHERE discussion_id = ? AND statement_id = ?
        """,
        (discussion_id, statement_id),
    ).fetchone()
    return {
        'agree': row['agree_count'],
        'concern': row['concern_count'],
        'helpful': row['helpful_count'],
    }


initialize_reactions_db()

@app.put('/api/reactions')
def put_reaction(request: ReactionStateRequest):
    """匿名ユーザーの対象別リアクション状態を冪等に設定する。"""
    with get_reactions_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO reaction_targets (
                discussion_id,
                statement_id,
                agree_base,
                concern_base,
                helpful_base
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.discussion_id,
                request.statement_id,
                request.base_counts.agree,
                request.base_counts.concern,
                request.base_counts.helpful,
            ),
        )
        existing = connection.execute(
            """
            SELECT reaction_type
            FROM reactions
            WHERE discussion_id = ?
              AND statement_id = ?
              AND anonymous_user_id = ?
            """,
            (
                request.discussion_id,
                request.statement_id,
                request.anonymous_user_id,
            ),
        ).fetchone()
        previous_reaction_type = existing['reaction_type'] if existing else None
        changed = previous_reaction_type != request.reaction_type

        if request.reaction_type is None:
            if existing:
                connection.execute(
                    """
                    DELETE FROM reactions
                    WHERE discussion_id = ?
                      AND statement_id = ?
                      AND anonymous_user_id = ?
                    """,
                    (
                        request.discussion_id,
                        request.statement_id,
                        request.anonymous_user_id,
                    ),
                )
        elif existing:
            if changed:
                connection.execute(
                    """
                    UPDATE reactions
                    SET reaction_type = ?
                    WHERE discussion_id = ?
                      AND statement_id = ?
                      AND anonymous_user_id = ?
                    """,
                    (
                        request.reaction_type,
                        request.discussion_id,
                        request.statement_id,
                        request.anonymous_user_id,
                    ),
                )
        else:
            connection.execute(
                """
                INSERT INTO reactions (
                    discussion_id,
                    statement_id,
                    reaction_type,
                    anonymous_user_id
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    request.discussion_id,
                    request.statement_id,
                    request.reaction_type,
                    request.anonymous_user_id,
                ),
            )

        counts = get_reaction_counts(
            connection,
            request.discussion_id,
            request.statement_id,
        )
        live_counts = get_live_reaction_counts(
            connection,
            request.discussion_id,
            request.statement_id,
        )

    return {
        'status': 'success',
        'discussion_id': request.discussion_id,
        'statement_id': request.statement_id,
        'previous_reaction_type': previous_reaction_type,
        'reaction_type': request.reaction_type,
        'changed': changed,
        'counts': counts,
        'live_counts': live_counts,
    }

@app.get('/api/reactions')
def get_reactions(discussion_id: str, anonymous_user_id: str):
    """議論内の最新件数と匿名ユーザー自身の選択状態を取得する。"""
    if not discussion_id.strip() or not anonymous_user_id.strip():
        raise HTTPException(status_code=400, detail='discussion_id and anonymous_user_id are required')

    with get_reactions_connection() as connection:
        targets = connection.execute(
            """
            SELECT statement_id
            FROM reaction_targets
            WHERE discussion_id = ?
            ORDER BY statement_id
            """,
            (discussion_id,),
        ).fetchall()
        data = []
        for target in targets:
            statement_id = target['statement_id']
            user_reaction = connection.execute(
                """
                SELECT reaction_type
                FROM reactions
                WHERE discussion_id = ?
                  AND statement_id = ?
                  AND anonymous_user_id = ?
                """,
                (discussion_id, statement_id, anonymous_user_id),
            ).fetchone()
            data.append({
                'statement_id': statement_id,
                'reaction_type': user_reaction['reaction_type'] if user_reaction else None,
                'counts': get_reaction_counts(connection, discussion_id, statement_id),
                'live_counts': get_live_reaction_counts(connection, discussion_id, statement_id),
            })

    return {
        'status': 'success',
        'discussion_id': discussion_id,
        'data': data,
    }

class UtteranceReactionRequest(BaseModel):
    reaction_type: str # 'agree' | 'concern' | 'helpful'
    speaker_name: Optional[str] = None

class UtteranceCommentRequest(BaseModel):
    user_label: Optional[str] = "市民（匿名）"
    comment_text: str
    speaker_name: Optional[str] = None

# 発言別リアクション・コメント用インメモリ/簡易永続化データ
UTTERANCE_REACTIONS_DB: Dict[str, Dict[str, Any]] = {}

def get_or_create_utterance_data(utt_id: str) -> Dict[str, Any]:
    if utt_id not in UTTERANCE_REACTIONS_DB:
        UTTERANCE_REACTIONS_DB[utt_id] = {
            "utt_id": utt_id,
            "agree_count": 42,
            "concern_count": 8,
            "helpful_count": 15,
            "comments": [
                {"user": "品川区民 (30代)", "text": "財源の持続性についての検証をしっかり行ってほしいです。"},
                {"user": "世田谷区在住パパ", "text": "病児保育予約のLINE化は本当に助かります。全区で進めてください！"}
            ]
        }
    return UTTERANCE_REACTIONS_DB[utt_id]

@app.post("/api/statements/{statement_id}/reaction")
def post_statement_reaction(statement_id: str, req: UtteranceReactionRequest):
    """個々の議員・首長の発言単位での市民リアクション（👍 賛成 / ⚠️ 気になる / 💡 参考）を記録"""
    utt_data = get_or_create_utterance_data(statement_id)
    r_type = req.reaction_type.lower()
    if r_type == 'agree':
        utt_data["agree_count"] += 1
    elif r_type in ['concern', 'disagree']:
        utt_data["concern_count"] += 1
    elif r_type == 'helpful':
        utt_data["helpful_count"] += 1
    else:
        raise HTTPException(status_code=400, detail="無効なリアクションタイプです")

    total = utt_data["agree_count"] + utt_data["concern_count"] + utt_data["helpful_count"]
    return {
        "status": "success",
        "statement_id": statement_id,
        "reaction_type": r_type,
        "agree_count": utt_data["agree_count"],
        "concern_count": utt_data["concern_count"],
        "helpful_count": utt_data["helpful_count"],
        "total_reactions": total,
        "agree_percentage": round((utt_data["agree_count"] / total) * 100) if total > 0 else 0,
        "concern_percentage": round((utt_data["concern_count"] / total) * 100) if total > 0 else 0,
        "helpful_percentage": round((utt_data["helpful_count"] / total) * 100) if total > 0 else 0
    }

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
    """議員ダッシュボード・EBPM分析用 発言別集計リアクション・コメント取得"""
    utt_data = get_or_create_utterance_data(statement_id)
    return {
        "status": "success",
        "statement_id": statement_id,
        "data": utt_data
    }
