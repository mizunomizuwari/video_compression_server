# 動画圧縮サーバー構築手順

Python + FFmpeg + Google Cloud Run で動作する動画圧縮APIサーバーの構築手順です。

## 前提条件

- Docker Desktop
- Google Cloud SDK (gcloud CLI)
- Googleアカウント・プロジェクト


## 設定系ファイル修正

- `service-account-key.json` (サービスアカウントキーを配置する)
- `app/config.py` (プロジェクトIDを設定)


## Google Cloud 設定

### 認証・プロジェクト設定

```bash
# 認証
gcloud auth login
gcloud auth application-default login

# プロジェクトID設定
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# API有効化
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

## Docker ビルド・実行

### ビルド

```bash
docker build -t video-compression .
```

### ローカル実行

```bash
docker run -p 8080:8080 \
  -e GCS_BUCKET_NAME=$BUCKET_NAME \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json \
  -v $(pwd)/service-account-key.json:/credentials.json:ro \
  video-compression
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8080/health

# ステータス確認
curl http://localhost:8080/api/v1/status
```

## API テスト

### 基本圧縮テスト

```bash
curl -X POST \
  -F "file=@sample.mp4" \
  -F 'options={"ffmpeg_args":["-c:v","libx264","-crf","28"]}' \
  http://localhost:8080/api/v1/compress
```

### 解像度変更テスト

```bash
curl -X POST \
  -F "file=@sample.mp4" \
  -F 'options={"ffmpeg_args":["-vf","scale=1280:720","-c:v","libx264","-crf","23"]}' \
  http://localhost:8080/api/v1/compress
```

## Cloud Run デプロイ

### Container Registry にプッシュ

```bash
# イメージタグ付け
docker tag video-compression gcr.io/$PROJECT_ID/video-compression

# プッシュ
docker push gcr.io/$PROJECT_ID/video-compression
```

### Cloud Run デプロイ

```bash
gcloud run deploy video-compression-api \
  --image gcr.io/$PROJECT_ID/video-compression \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 3 \
  --max-instances 1 \
  --timeout 60s \
  --set-env-vars GCS_BUCKET_NAME=$BUCKET_NAME
```

### デプロイ確認

```bash
# サービスURL取得
export SERVICE_URL=$(gcloud run services describe video-compression-api \
  --region asia-northeast1 \
  --format 'value(status.url)')

echo "Service URL: $SERVICE_URL"

# 動作確認
curl $SERVICE_URL/health
```

## 8. 本番環境テスト

```bash
# 本番環境での圧縮テスト
curl -X POST \
  -F "file=@sample.mp4" \
  -F 'options={"ffmpeg_args":["-c:v","libx264","-crf","28"]}' \
  $SERVICE_URL/api/v1/compress
```

## 運用・メンテナンス

### ログ確認

```bash
# リアルタイムログ
gcloud logs tail video-compression-api

# 過去ログ検索
gcloud logs read --service video-compression-api --limit 50
```

### 更新デプロイ

```bash
# コード変更後
docker build -t video-compression .
docker tag video-compression gcr.io/$PROJECT_ID/video-compression
docker push gcr.io/$PROJECT_ID/video-compression
gcloud run deploy video-compression-api --image gcr.io/$PROJECT_ID/video-compression
```

## デバッグ・トラブルシューティング

### コンテナ内デバッグ

```bash
# コンテナ内でシェル実行
docker run -it --rm \
  -e GCS_BUCKET_NAME=$BUCKET_NAME \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json \
  -v $(pwd)/service-account-key.json:/credentials.json:ro \
  video-compression bash

# FFmpeg確認
ffmpeg -version

# 認証確認
python -c "from google.cloud import storage; storage.Client()"
```

### よくある問題

**認証エラー:**
```bash
gcloud auth application-default login
```

**バケット確認:**
```bash
gsutil ls -b gs://$BUCKET_NAME
```

**メモリ不足:**
```bash
gcloud run services update video-compression-api \
  --memory 4Gi \
  --region asia-northeast1
```

## 許可されたFFmpegオプション

- **ビデオコーデック**: `-c:v`, `-vcodec`
- **オーディオコーデック**: `-c:a`, `-acodec`
- **ビットレート**: `-b:v`, `-b:a`, `-crf`
- **解像度・フレームレート**: `-s`, `-r`, `-vf`
- **品質設定**: `-preset`, `-tune`, `-profile:v`
- **フォーマット**: `-f`

## API仕様

### エンドポイント
```
POST /api/v1/compress
```

### リクエスト例
```json
{
  "file": "動画ファイル",
  "options": {
    "ffmpeg_args": ["-c:v", "libx264", "-crf", "23"],
    "output_format": "mp4"
  }
}
```

### レスポンス例
```json
{
  "status": "success",
  "download_url": "https://storage.googleapis.com/...",
  "expires_at": "2025-06-23T15:30:00Z",
  "processing_time": 45.2,
  "file_info": {
    "original_size": 104857600,
    "compressed_size": 52428800,
    "compression_ratio": 0.5
  }
}
```