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

ローカル開発では、FirebaseのサービスアカウントJSONをリポジトリ外へ保存し、`GOOGLE_APPLICATION_CREDENTIALS` に絶対パスを設定します。本番Renderでは、Secret File `firebase-service-account.json` を登録すると `/etc/secrets/firebase-service-account.json` が自動検出されます。代わりにSecret環境変数 `FIREBASE_SERVICE_ACCOUNT_JSON` へJSON全体を登録することもできますが、ファイルと環境変数を同時に設定しないでください。

Renderでは明示的な認証情報が必須です。認証情報がない、JSONが壊れている、または `FIREBASE_PROJECT_ID` と秘密鍵内の `project_id` が異なる場合、リアクションAPIはHTTP 500を返し、空集計へフォールバックしません。`FIREBASE_DATABASE_ID` は初回運用時の値（通常は `(default)`）から変更しないでください。変更すると別のFirestoreデータベースを参照します。

起動ログの次の行で接続先を確認できます（秘密鍵の内容は出力されません）。

```text
Reaction store ready (backend=firestore, project_id=..., database_id=...)
```

Firestoreドキュメントと本番APIの集計値は、Render Shellで次の読取専用監査を実行して比較できます。

```bash
python scripts/audit_reaction_storage.py \
  --discussion-id tokyo-metropolitan \
  --api-base https://gijiraku-backend.onrender.com
```

実Firestoreを使う再起動テストは明示的に有効化して実行します。GET、PUT、別プロセスからのGETを順に行い、テスト専用ドキュメントだけを最後に削除します。

```bash
RUN_FIRESTORE_INTEGRATION_TEST=1 \
python -m unittest tests.test_reaction_persistence_integration -v
```

## 議事録ETL API

`POST /api/etl/extract` は外部公開用ではなく、管理ジョブ専用です。Render と呼び出し元の両方に十分長い同一の `ETL_API_KEY` を設定し、リクエストの `X-ETL-API-Key` ヘッダーで送信してください。キー未設定時は 503、不一致時は 401 を返します。

Gemini を利用する場合は `GEMINI_API_KEY` を設定します。モデルは `GEMINI_MODEL` で変更でき、未設定時は既定モデルを使用します。`persist: true` の抽出結果は公開議題へ直接混入させず、レビュー用の Firestore コレクション `assembly_record_extractions` に保存されます。

```bash
curl -X POST http://localhost:8000/api/etl/extract \
  -H "Content-Type: application/json" \
  -H "X-ETL-API-Key: ${ETL_API_KEY}" \
  -d '{"raw_text":"議事録本文","persist":false}'
```

通知設定 API は匿名ユーザーIDをハッシュ化して保存します。設定の取得・更新は `/api/notifications/preferences/{anonymous_user_id}`、一致件数の取得は `/api/notifications/matches/{anonymous_user_id}` です。

サービスアカウントJSONはGitへコミットしないでください。
