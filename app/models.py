from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class CompressionOptions(BaseModel):
    """動画圧縮オプション"""
    ffmpeg_args: List[str] = Field(default=[], description="FFmpegオプション配列")
    output_format: str = Field(default="mp4", description="出力フォーマット")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="メタデータ")

    @validator('ffmpeg_args')
    def validate_ffmpeg_args(cls, v):
        if not isinstance(v, list):
            raise ValueError("ffmpeg_args must be a list")
        if len(v) > 20:  # オプション数制限
            raise ValueError("Too many ffmpeg arguments")
        return v

    @validator('output_format')
    def validate_output_format(cls, v):
        allowed_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        if v not in allowed_formats:
            raise ValueError(f"Output format must be one of: {allowed_formats}")
        return v

class FileInfo(BaseModel):
    """ファイル情報"""
    original_size: int = Field(description="元のファイルサイズ (bytes)")
    compressed_size: int = Field(description="圧縮後ファイルサイズ (bytes)")
    compression_ratio: float = Field(description="圧縮率 (0.0-1.0)")
    duration: Optional[float] = Field(default=None, description="動画の長さ (秒)")
    original_format: Optional[str] = Field(default=None, description="元のフォーマット")

class CompressionResponse(BaseModel):
    """圧縮レスポンス"""
    status: str = Field(description="処理ステータス")
    download_url: str = Field(description="ダウンロードURL")
    expires_at: datetime = Field(description="URL有効期限")
    processing_time: float = Field(description="処理時間 (秒)")
    file_info: FileInfo = Field(description="ファイル情報")

class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    status: str = Field(default="error")
    error_code: str = Field(description="エラーコード")
    message: str = Field(description="エラーメッセージ")
    details: Optional[Dict[str, Any]] = Field(default=None, description="詳細情報")

class ProcessingStatus(BaseModel):
    """処理状況"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int = Field(ge=0, le=100)  # 0-100%
    message: Optional[str] = None