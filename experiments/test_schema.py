import urllib.request
import json
import pandas as pd

# CKAN APIエンドポイント
url = "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_search?q=%E8%AD%B0%E4%BC%9A&rows=10"

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())

    # 最初のデータセット（議会だより）からCSVのURLを探す
    for dataset in data['result']['results']:
        if '議会だより' in dataset['title']:
            for resource in dataset['resources']:
                if 'CS' in resource['format'].upper(): # CSVまたはCSにマッチ
                    csv_url = resource['url']
                    print(f"■ {dataset['title']} のCSVを読み込み中...\nURL: {csv_url}\n")
                    
                    # 文字コードのトラップを回避しつつ読み込み
                    try:
                        df = pd.read_csv(csv_url, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(csv_url, encoding='shift-jis')
                    
                    print("■ カラム（列）一覧:")
                    print(df.columns.tolist())
                    
                    print("\n■ データのサンプル（最初の1行）:")
                    print(json.dumps(df.head(1).to_dict(orient='records')[0], indent=2, ensure_ascii=False))
                    
                    # 1つ見つけたら終了
                    exit()