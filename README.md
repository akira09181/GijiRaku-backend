# GijiRaku API (バックエンド)

FastAPIとLangChain / Gemini AIを使用した議事録超翻訳および東京都オープンデータ連携APIサーバーです。

## ディレクトリ構成
```
gijiraku-api/
├── main.py                # FastAPI メインアプリケーション
├── reaction_store.py      # Firestoreリアクション永続化
├── opendata_service.py    # 東京都オープンデータ (CKAN API) 連携モジュール
├── requirements.txt       # 依存パッケージ定義
├── data/                  # 議事録データフォルダ (PDF, CSV)
└── experiments/           # 検証用スクリプト群
```

## 起動方法

1. **仮想環境の有効化** (Windows PowerShell):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **依存ライブラリのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

3. **FastAPIサーバーの起動**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   サーバー起動後、 `http://localhost:8000/docs` でSwagger UIのAPIドキュメントを確認できます。

## Firestore認証

ローカル開発では、FirebaseのサービスアカウントJSONをリポジトリ外へ保存し、`GOOGLE_APPLICATION_CREDENTIALS` に絶対パスを設定します。本番Renderでは、Secret File `firebase-service-account.json` を登録すると `/etc/secrets/firebase-service-account.json` が自動検出されます。

サービスアカウントJSONはGitへコミットしないでください。
