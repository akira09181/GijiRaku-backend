import urllib.request
import json

# キーワードを「議会」から「会議録」に変更（%E4%BC%9A%E8%AD%B0%E9%8C%B2 = 会議録）
url = "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_search?q=%E4%BC%9A%E8%AD%B0%E9%8C%B2&rows=10"

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())

    print("■ 「会議録」での検索結果\n" + "="*40)
    if not data['result']['results']:
        print("データが見つかりませんでした。別のキーワードを試します。")
        
    for i, dataset in enumerate(data['result']['results'], 1):
        formats = list(set([r['format'].upper() for r in dataset['resources'] if r['format']]))
        print(f"{i}. {dataset['title']}")
        print(f"   利用可能な形式: {', '.join(formats)}\n")