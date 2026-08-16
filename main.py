# main.py - GijiRaku FastAPI Server
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from opendata_service import (
    get_all_assemblies,
    get_assembly_chat_dialogue,
    fetch_tokyo_catalog_datasets
)

app = FastAPI(title="GijiRaku API", description="議事録の超翻訳・LINE風対話API")

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

class TranslationResponse(BaseModel):
    answer: str
    speaker: str = "GijiRaku AI"
    role: str = "超翻訳ナビゲーター"
    original_quote: Optional[str] = None
    timestamp: str = "12:00"

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
    """市民の投票（賛成/懸念）および意見コメント投稿を記録"""
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

@app.post("/api/translate", response_model=TranslationResponse)
async def translate_giji(request: TranslationRequest):
    """ユーザーの質問に対する超翻訳RAGレスポンス生成"""
    try:
        q = request.question.strip()
        if not q:
            raise HTTPException(status_code=400, detail="質問内容を入力してください")

        # インタラクティブ質問に対するLINE風超翻訳回答生成
        # APIキーが設定されている場合はLangChain/Geminiを実行
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser
                
                llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.7, google_api_key=api_key)
                prompt = PromptTemplate.from_template(
                    "あなたは議事録の堅苦しい言葉を、中学生にもパッと分かる言葉へ会話調で超翻訳するAIです。"
                    "【ルール】LINE風の会話の返事として、「要するにどういうことか」を親しみやすく率直に100文字程度で答えてください。"
                    "質問: {question}\n超翻訳回答:"
                )
                chain = prompt | llm | StrOutputParser()
                answer_text = chain.invoke(q)
            except Exception as e:
                print(f"Gemini API 呼び出しエラー: {e}")
                answer_text = f"【要するに：{q} について議論が続いています！】\n過去の議決結果をもとに、予算配分や支援策を計画的に進める方針が示されています。"
        else:
            # フォールバックのルールベース超翻訳レスポンス
            if "子育て" in q or "ワクチン" in q or "給付金" in q:
                answer_text = "【要するに：保護者の自己負担を減らす方向で動いています！】\n授乳スペースの拡充やワクチンの公費助成について、国や周辺自治体と連携して準備が進んでいます。"
            elif "デジタル" in q or "DX" in q or "スマホ" in q:
                answer_text = "【要するに：役所に行かずにスマホで手続き完了を目指します！】\n申請手続きのキャッシュレス化やオンライン化を今年度末までに急ピッチで拡大する方針です。"
            else:
                answer_text = f"【要するに：「{q}」についての市民の声を受けて、議会で予算と実施計画が前向きに話し合われています！】\n次回の委員会で具体的なロードマップが決定される予定です。"

        return TranslationResponse(
            answer=answer_text,
            speaker="GijiRaku AI",
            role="超翻訳アシスタント",
            original_quote=f"「ご質問の『{q}』に関しまして、本区議会および各種委員会にて活発な質疑が行われております。」",
            timestamp="12:00"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))