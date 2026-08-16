import urllib.request
import json
import pandas as pd
from bs4 import BeautifulSoup

# 1. CKAN APIから「議会だより」のCSV URLを取得
api_url = "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_search?q=%E8%AD%B0%E4%BC%9A&rows=1"
req = urllib.request.Request(api_url)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    csv_url = data['result']['results'][0]['resources'][0]['url']

# 2. CSVを読み込んで、最初のURLを取り出す
try:
    df = pd.read_csv(csv_url, encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(csv_url, encoding='shift-jis')

# 有効なURLを持つ行からサンプルを1つ取得
target_row = df.dropna(subset=['URL']).iloc[0]
page_url = target_row['URL']
print(f"■ スクレイピング対象URL: {page_url}")

# 3. リンク先のHTMLからテキストをスクレイピング
req_page = urllib.request.Request(
    page_url, 
    headers={'User-Agent': 'Mozilla/5.0'} # ブロック回避のUser-Agent AIzaSyAjGODJcazqYeVjVgUnxhNAXBtrSB6nnQc
)

try:
    with urllib.request.urlopen(req_page) as res:
        html_content = res.read().decode('shift_jis', errors='ignore') # 自治体サイトによくあるSJIS
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 不要なタグ（ヘッダー、フッター、ナビゲーション等）を除去
        for script in soup(["script", "style", "header", "footer"]):
            script.extract()
            
        # 本文テキストを抽出
        text = soup.get_text(separator='\n', strip=True)
        
        print("\n■ 抽出されたテキストのプレビュー（先頭300文字）:")
        print("-" * 40)
        print(text[:300])
        print("-" * 40)
        
except Exception as e:
    print(f"取得に失敗しました: {e}")