# db.py - SQLite Persistence Layer for MachiVoice
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "gijiraku.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. リアクションテーブル (多重投票防止のため user_id, topic_id, statement_id のユニーク制約)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        assembly_id TEXT NOT NULL,
        statement_id TEXT NOT NULL DEFAULT '',
        reaction_type TEXT NOT NULL, -- 'agree', 'concern', 'more_info', 'struggling'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, topic_id, statement_id)
    )
    """)

    # 2. 市民コメント・意見テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL DEFAULT '市民（匿名）',
        topic_id TEXT NOT NULL,
        assembly_id TEXT NOT NULL,
        statement_id TEXT NOT NULL DEFAULT '',
        comment_text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 3. 更新通知購読テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        assembly_id TEXT NOT NULL,
        theme TEXT NOT NULL,
        email TEXT DEFAULT '',
        notify_type TEXT NOT NULL DEFAULT 'browser', -- 'browser', 'email', 'in_app'
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # 4. ユーザーアクティビティ・閲覧履歴テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_activity (
        user_id TEXT PRIMARY KEY,
        viewed_topics TEXT NOT NULL DEFAULT '[]',
        last_assembly_id TEXT DEFAULT 'tokyo-metropolitan',
        last_theme TEXT DEFAULT 'all',
        updated_at TEXT NOT NULL
    )
    """)

    # 5. フィードバック・通報テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        category TEXT NOT NULL, -- 'feedback', 'report', 'data_correction'
        content TEXT NOT NULL,
        assembly_id TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    # 初期シードデータ投入 (初期表示用のリアクション実績)
    cursor.execute("SELECT COUNT(*) FROM reactions")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        initial_seed = [
            # 品川区 子育て議題
            ("seed_user_1", "shinagawa-childcare-2026-001", "shinagawa-ward", "", "agree", now),
            ("seed_user_2", "shinagawa-childcare-2026-001", "shinagawa-ward", "", "agree", now),
            ("seed_user_3", "shinagawa-childcare-2026-001", "shinagawa-ward", "", "concern", now),
            ("seed_user_4", "shinagawa-childcare-2026-001", "shinagawa-ward", "", "more_info", now),
            ("seed_user_5", "shinagawa-childcare-2026-001", "shinagawa-ward", "", "struggling", now),
            # 発言単位
            ("seed_user_6", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-morisawa-01", "agree", now),
            ("seed_user_7", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-ito-02", "agree", now),
            ("seed_user_8", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-matsumoto-03", "concern", now),
            ("seed_user_9", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-tanaka-04", "more_info", now),
            # 新宿区
            ("seed_user_10", "shinjuku-childcare-2026-001", "shinjuku-ward", "", "agree", now),
            ("seed_user_11", "shinjuku-childcare-2026-001", "shinjuku-ward", "", "struggling", now),
            # 町田市
            ("seed_user_12", "machida-childcare-2026-001", "machida-city", "", "agree", now),
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO reactions (user_id, topic_id, assembly_id, statement_id, reaction_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(u, t, a, s, r, d, d) for u, t, a, s, r, d in initial_seed])

        # 初期コメント
        initial_comments = [
            ("seed_user_1", "品川区民 (30代保護者)", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-morisawa-01", "給食費とおむつのW支援は本当に助かります！継続を強く希望します。", now),
            ("seed_user_3", "共働きパパAさん", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-ito-02", "病児保育のLINE予約は絶対必要。朝電話がつながらない問題を解消してほしい。", now),
            ("seed_user_4", "区民Bさん", "shinagawa-childcare-2026-001", "shinagawa-ward", "shinagawa-matsumoto-03", "ただ無償化するだけでなく、将来の区財政が圧迫されないかの懸念チェックは大切。", now)
        ]
        cursor.executemany("""
            INSERT INTO comments (user_id, user_name, topic_id, assembly_id, statement_id, comment_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, initial_comments)

    conn.commit()
    conn.close()

# ---------------------------------------------------------
# リアクション関数
# ---------------------------------------------------------
def save_or_toggle_reaction(user_id: str, topic_id: str, assembly_id: str, statement_id: str, reaction_type: str) -> Dict[str, Any]:
    """
    リアクションを保存・変更・トグル。
    同じタイプを押した場合は取り消し、違うタイプを押した場合は更新。
    """
    valid_types = {'agree', 'concern', 'more_info', 'struggling'}
    if reaction_type not in valid_types:
        raise ValueError(f"Invalid reaction_type: {reaction_type}")

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        SELECT reaction_type FROM reactions 
        WHERE user_id = ? AND topic_id = ? AND statement_id = ?
    """, (user_id, topic_id, statement_id))
    row = cursor.fetchone()

    current_reaction = None
    if row:
        existing_type = row["reaction_type"]
        if existing_type == reaction_type:
            # 取り消し
            cursor.execute("""
                DELETE FROM reactions 
                WHERE user_id = ? AND topic_id = ? AND statement_id = ?
            """, (user_id, topic_id, statement_id))
            current_reaction = None
        else:
            # 変更
            cursor.execute("""
                UPDATE reactions SET reaction_type = ?, updated_at = ?
                WHERE user_id = ? AND topic_id = ? AND statement_id = ?
            """, (reaction_type, now, user_id, topic_id, statement_id))
            current_reaction = reaction_type
    else:
        # 新規作成
        cursor.execute("""
            INSERT INTO reactions (user_id, topic_id, assembly_id, statement_id, reaction_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, topic_id, assembly_id, statement_id, reaction_type, now, now))
        current_reaction = reaction_type

    conn.commit()
    conn.close()

    summary = get_reaction_counts(topic_id=topic_id, statement_id=statement_id)
    return {
        "user_reaction": current_reaction,
        "counts": summary,
        "topic_id": topic_id,
        "statement_id": statement_id,
        "assembly_id": assembly_id
    }

def get_reaction_counts(topic_id: Optional[str] = None, statement_id: Optional[str] = None, assembly_id: Optional[str] = None) -> Dict[str, int]:
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []
    if topic_id is not None:
        conditions.append("topic_id = ?")
        params.append(topic_id)
    if statement_id is not None:
        conditions.append("statement_id = ?")
        params.append(statement_id)
    if assembly_id is not None:
        conditions.append("assembly_id = ?")
        params.append(assembly_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor.execute(f"""
        SELECT reaction_type, COUNT(*) as count 
        FROM reactions
        {where_clause}
        GROUP BY reaction_type
    """, params)

    counts = {
        "agree": 0,
        "concern": 0,
        "more_info": 0,
        "struggling": 0
    }
    for row in cursor.fetchall():
        rtype = row["reaction_type"]
        if rtype in counts:
            counts[rtype] = row["count"]

    counts["total"] = sum(counts.values())
    conn.close()
    return counts

def get_user_reactions(user_id: str) -> Dict[str, str]:
    """特定ユーザーが投票済みの全リアクションマップ { key: reaction_type } を取得"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_id, statement_id, reaction_type FROM reactions WHERE user_id = ?
    """, (user_id,))
    
    result = {}
    for row in cursor.fetchall():
        key = f"{row['topic_id']}::{row['statement_id']}" if row['statement_id'] else row['topic_id']
        result[key] = row['reaction_type']
    conn.close()
    return result

# ---------------------------------------------------------
# コメント関数
# ---------------------------------------------------------
def add_comment(user_id: str, user_name: str, topic_id: str, assembly_id: str, statement_id: str, comment_text: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO comments (user_id, user_name, topic_id, assembly_id, statement_id, comment_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, user_name or '市民（匿名）', topic_id, assembly_id, statement_id, comment_text.strip(), now))

    comment_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": comment_id,
        "user_id": user_id,
        "user_name": user_name or '市民（匿名）',
        "topic_id": topic_id,
        "assembly_id": assembly_id,
        "statement_id": statement_id,
        "comment_text": comment_text.strip(),
        "created_at": now
    }

def get_comments(topic_id: Optional[str] = None, statement_id: Optional[str] = None, assembly_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []
    if topic_id is not None:
        conditions.append("topic_id = ?")
        params.append(topic_id)
    if statement_id is not None:
        conditions.append("statement_id = ?")
        params.append(statement_id)
    if assembly_id is not None:
        conditions.append("assembly_id = ?")
        params.append(assembly_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor.execute(f"""
        SELECT id, user_id, user_name, topic_id, assembly_id, statement_id, comment_text, created_at
        FROM comments
        {where_clause}
        ORDER BY id DESC
        LIMIT ?
    """, params + [limit])

    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

# ---------------------------------------------------------
# 通知購読関数
# ---------------------------------------------------------
def save_subscription(user_id: str, assembly_id: str, theme: str, email: str = "", notify_type: str = "browser") -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        SELECT id FROM subscriptions
        WHERE user_id = ? AND assembly_id = ? AND theme = ?
    """, (user_id, assembly_id, theme))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE subscriptions SET is_active = 1, email = ?, notify_type = ?, created_at = ?
            WHERE id = ?
        """, (email, notify_type, now, existing["id"]))
        sub_id = existing["id"]
    else:
        cursor.execute("""
            INSERT INTO subscriptions (user_id, assembly_id, theme, email, notify_type, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (user_id, assembly_id, theme, email, notify_type, now))
        sub_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "id": sub_id,
        "user_id": user_id,
        "assembly_id": assembly_id,
        "theme": theme,
        "email": email,
        "notify_type": notify_type,
        "is_active": True,
        "created_at": now
    }

def delete_subscription(sub_id: int, user_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ? AND user_id = ?", (sub_id, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def get_user_subscriptions(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, assembly_id, theme, email, notify_type, is_active, created_at
        FROM subscriptions
        WHERE user_id = ? AND is_active = 1
        ORDER BY id DESC
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# ---------------------------------------------------------
# ユーザーアクティビティ・閲覧履歴
# ---------------------------------------------------------
def save_user_activity(user_id: str, topic_id: Optional[str] = None, last_assembly_id: Optional[str] = None, last_theme: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("SELECT viewed_topics, last_assembly_id, last_theme FROM user_activity WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    viewed_list = []
    current_assembly = last_assembly_id or "tokyo-metropolitan"
    current_theme = last_theme or "all"

    if row:
        try:
            viewed_list = json.loads(row["viewed_topics"])
        except:
            viewed_list = []
        if not last_assembly_id:
            current_assembly = row["last_assembly_id"] or "tokyo-metropolitan"
        if not last_theme:
            current_theme = row["last_theme"] or "all"

    if topic_id:
        if topic_id in viewed_list:
            viewed_list.remove(topic_id)
        viewed_list.insert(0, topic_id)
        viewed_list = viewed_list[:30] # 直近30件

    cursor.execute("""
        INSERT INTO user_activity (user_id, viewed_topics, last_assembly_id, last_theme, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            viewed_topics = excluded.viewed_topics,
            last_assembly_id = excluded.last_assembly_id,
            last_theme = excluded.last_theme,
            updated_at = excluded.updated_at
    """, (user_id, json.dumps(viewed_list), current_assembly, current_theme, now))

    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "viewed_topics": viewed_list,
        "last_assembly_id": current_assembly,
        "last_theme": current_theme,
        "updated_at": now
    }

def get_user_activity(user_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT viewed_topics, last_assembly_id, last_theme, updated_at FROM user_activity WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "user_id": user_id,
            "viewed_topics": [],
            "last_assembly_id": "tokyo-metropolitan",
            "last_theme": "all",
            "updated_at": None
        }

    try:
        viewed = json.loads(row["viewed_topics"])
    except:
        viewed = []

    return {
        "user_id": user_id,
        "viewed_topics": viewed,
        "last_assembly_id": row["last_assembly_id"],
        "last_theme": row["last_theme"],
        "updated_at": row["updated_at"]
    }

# ---------------------------------------------------------
# フィードバック・通報
# ---------------------------------------------------------
def save_feedback(user_id: str, category: str, content: str, assembly_id: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO feedback_reports (user_id, category, content, assembly_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, category, content.strip(), assembly_id, now))

    fid = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": fid,
        "user_id": user_id,
        "category": category,
        "content": content.strip(),
        "assembly_id": assembly_id,
        "created_at": now,
        "status": "received"
    }

# 初期化実行
init_db()
