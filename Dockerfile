# Python 3.12ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新とffmpegインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係を先にコピー
COPY requirements.txt .

# Python依存関係インストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app/ ./app/

# 一時ディレクトリ作成
RUN mkdir -p /tmp

# 環境変数設定
ENV PYTHONPATH=/app
ENV PORT=8080

# ポート公開
EXPOSE 8080

# アプリケーション起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

