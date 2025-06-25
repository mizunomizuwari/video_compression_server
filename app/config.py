import os
from typing import List

class Settings:
    # ファイル制限
    MAX_FILE_SIZE: int = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS: List[str] = [
        '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', 
        '.webm', '.m4v', '.3gp', '.ogv'
    ]
    
    # 処理制限
    MAX_PROCESSING_TIME: int = 60  # 60秒
    
    # ffmpeg設定
    FFMPEG_ALLOWED_OPTIONS: List[str] = [
        '-c:v', '-vcodec', '-c:a', '-acodec',
        '-b:v', '-b:a', '-crf', '-s', '-r', '-vf',
        '-preset', '-tune', '-profile:v', '-f'
    ]
    
    FFMPEG_FORBIDDEN_PATTERNS: List[str] = [
        '-i', '/dev/', 'file://', 'http://', 'https://',
        'exec', 'system', 'pipe', '$(', '`'
    ]
    
    # Cloud Storage設定
    GOOGLE_CLOUD_PROJECT: str = "ここにプロジェクト名"
    GCS_BUCKET_NAME: str = os.getenv('GCS_BUCKET_NAME', 'ここにバケット名')
    GCS_CREDENTIALS_PATH: str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
    
    # 一時ファイル設定
    TEMP_FILE_TTL: int = 3600  # 1時間
    TEMP_DIR: str = '/tmp'
    
    # API設定
    API_TITLE: str = "Video Compression API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "FFmpeg based video compression service"

settings = Settings()
