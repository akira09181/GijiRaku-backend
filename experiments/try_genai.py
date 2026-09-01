import os
from google import genai

# The client automatically picks up the GEMINI_API_KEY environment variable.
# If you prefer, you can pass it directly: client = genai.Client(api_key="YOUR_KEY")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print("PDFをアップロード中...")
# Upload the PDF using the new client
sample_pdf = client.files.upload(file="194kugikai.pdf")

print("Geminiにデータ抽出を依頼中...")
prompt = "Extract the key data from this document." # Replace with your actual prompt

# Generate content using the correct model and new syntax
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[sample_pdf, prompt]
)

print(response.text)
