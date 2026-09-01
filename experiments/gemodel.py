import os

from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print("利用可能なモデル一覧:")
for model in client.models.list():
    print(model.name)
