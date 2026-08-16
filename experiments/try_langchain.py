import json
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ---------------------------------------------------------
# 1. データ準備（先ほど抽出成功したJSONデータをモックとして使用）
# ---------------------------------------------------------
json_data = [
    {
        "speaker": "田中広一 議員",
        "role": "中央区議会公明党",
        "content": "【子育て支援策について】分かりやすい広報や、おむつ替え・授乳コーナーの整備、小児用肺炎球菌ワクチンやみずぼうそう等の任意接種への公費助成を求める。"
    },
    {
        "speaker": "区長",
        "role": "答弁者",
        "content": "子育て支援について、多様な媒体を活用した分かりやすい広報に努める。授乳室等は民間施設への働きかけや、区の施設への拡大を進める。任意接種ワクチンについては、国の動向や流通等を見極め、適切に対処・検討する。"
    }
]

# JSONデータをLangChainのDocumentオブジェクトに変換
# メタデータ（発言者や属性）を持たせることで、検索精度やLLMの理解力が向上します
documents = []
for item in json_data:
    doc = Document(
        page_content=item['content'],
        metadata={"speaker": item['speaker'], "role": item['role']}
    )
    documents.append(doc)


# ---------------------------------------------------------
# 2. Vector DB (Chroma) の構築
# ---------------------------------------------------------
print("Vector DBを構築中...")
# GeminiのEmbeddingモデルを使用
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# メモリ上で動作するChroma DBにデータを投入
vectorstore = Chroma.from_documents(documents, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2}) # 関連度の高い2件を取得


# ---------------------------------------------------------
# 3. GijiRaku 超翻訳エンジン (RAG Chain) の構築
# ---------------------------------------------------------
# ここがGijiRakuの「超翻訳」を司るプロンプトです
template = """
あなたは、議事録の堅苦しい言葉を、一般市民（中学生レベル）でもパッと見て分かるように噛み砕く「超翻訳」AIです。
以下の過去の議会での発言（コンテキスト）を踏まえて、ユーザーの質問に答えてください。

【コンテキスト（過去の発言）】
{context}

【ルール】
- 「前向きに検討する」「適切に対処する」といったお役所言葉は、「要するにどういうことか（やるのか、やらないのか、保留なのか）」を推測して率直に書いてください。
- 誰が発言した内容か分かるように記載してください。

質問: {question}
超翻訳:
"""
prompt = PromptTemplate.from_template(template)

# LLMの初期化（Gemini 1.5 Proを使用）
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.7)

# ドキュメントを結合してプロンプトに渡すためのヘルパー関数
def format_docs(docs):
    return "\n\n".join(f"[{doc.metadata['speaker']} ({doc.metadata['role']})] {doc.page_content}" for doc in docs)

# LangChain Expression Language (LCEL) でチェーンを構築
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ---------------------------------------------------------
# 4. 超翻訳の実行テスト
# ---------------------------------------------------------
print("\n■ GijiRaku 超翻訳エンジン 起動")
print("-" * 40)
user_question = "子育てのワクチン代って結局タダになるの？"
print(f"市民の疑問: {user_question}")
print("-" * 40)

# RAGチェーンの実行
response = rag_chain.invoke(user_question)
print(response)