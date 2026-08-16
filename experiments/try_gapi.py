import json
from google import genai
from google.genai import types

# APIキーの設定（環境変数 GEMINI_API_KEY に設定している場合は api_key= の指定は不要です）
client = genai.Client(api_key="AIzaSyAjGODJcazqYeVjVgUnxhNAXBtrSB6nnQc")

print("PDFをアップロード中...")
# 新SDKでのファイルアップロード
sample_pdf = client.files.upload(file="194kugikai.pdf")
prompt = """
あなたは優秀なデータ入力オペレーターです。
添付された議会だより（または会議録）のPDFを読み込み、以下のJSONスキーマに従って、発言者と発言内容のペアを抽出してください。

【抽出ルール】
1. 議長や進行役の定型的な発言は無視してください。
2. 質問と答弁のセットが分かるように抽出してください。
3. 発言内容が複数の段落に跨っている場合は、1つの文章として要約せずに結合してください。
4. PDFの段組みや改行の崩れは、人間が読みやすいように自然な日本語に修正してください。

【出力JSONスキーマ】
[
  {
    "speaker": "発言者の名前（例：山田太郎 議員）",
    "role": "役職や会派（わかる場合のみ）",
    "content": "発言の本文"
  }
]
"""

print("Geminiにデータ抽出を依頼中...")
# 新SDKでのコンテンツ生成（JSONモード指定）
response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=[sample_pdf, prompt],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
    ),
)

try:
    extracted_data = json.loads(response.text)
    print("■ 抽出成功！")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
except json.JSONDecodeError:
    print("JSONのパースに失敗しました。")
    print(response.text)

# クリーンアップ（サーバー上のPDFを削除）
client.files.delete(name=sample_pdf.name)
print("■ クリーンアップ完了")