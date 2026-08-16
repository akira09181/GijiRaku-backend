import urllib.request
import json

# CKAN APIエンドポイント（q=議会, rows=10）
url = "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_search?q=%E8%AD%B0%E4%BC%9A&rows=10"

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())

    # 取得した10件のデータセットのタイトルと、利用可能なファイル形式を出力
    for dataset in data['result']['results']:
        print(f"■ データセット名: {dataset['title']}")
        for resource in dataset['resources']:
            print(f"  - 形式: {resource['format']} | URL: {resource['url']}")
        print("-" * 40)