from google import genai

client = genai.Client(api_key="AIzaSyAjGODJcazqYeVjVgUnxhNAXBtrSB6nnQc")

print("利用可能なモデル一覧:")
for model in client.models.list():
    print(model.name)