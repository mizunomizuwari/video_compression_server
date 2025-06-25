import os
import tempfile
import time
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models import CompressionOptions, CompressionResponse, ErrorResponse, FileInfo
from app.services.ffmpeg_service import FFmpegService
from app.services.storage_service import CloudStorageService
from app.utils.validators import FileValidator
from app.utils.exceptions import (
    VideoCompressionError, FFmpegError, ProcessingTimeoutError,
    FileValidationError, StorageError, InvalidOptionsError
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時処理
    print(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    
    # 一時ディレクトリ確認
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    
    yield
    
    # 終了時処理
    print("Shutting down...")

# FastAPIアプリケーション初期化
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# サービス初期化
ffmpeg_service = FFmpegService()
storage_service = CloudStorageService()
file_validator = FileValidator()

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/api/v1/status")
async def get_status():
    """サーバーステータス"""
    return {
        "status": "running",
        "version": settings.API_VERSION
    }

@app.post("/api/v1/compress", response_model=CompressionResponse)
async def compress_video(
    file: UploadFile = File(..., description="圧縮する動画ファイル"),
    options: str = Form(default='{}', description="圧縮オプション（JSON形式）")
):
    """
    動画圧縮API
    
    - **file**: 圧縮する動画ファイル（最大200MB）
    - **options**: FFmpegオプションとメタデータ（JSON形式）
    """
    
    input_file_path = None
    output_file_path = None
    
    try:
        # オプション解析
        try:
            options_dict = json.loads(options)
            compression_options = CompressionOptions(**options_dict)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in options")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid options format: {str(e)}")
        
        # ファイル検証
        file_validator.validate_file_size(file)
        file_validator.validate_file_extension(file.filename)
        
        # 一時ファイル保存
        input_file_path = await save_upload_file(file)
        file_validator.validate_file_type(input_file_path)
        
        # 元ファイル情報取得
        original_size = os.path.getsize(input_file_path)
        
        # 動画圧縮実行
        start_time = time.time()
        output_file_path, metadata = await ffmpeg_service.compress_video(
            input_file_path,
            compression_options.ffmpeg_args,
            compression_options.output_format
        )
        processing_time = time.time() - start_time
        
        # 圧縮後ファイル情報
        compressed_size = os.path.getsize(output_file_path)
        compression_ratio = compressed_size / original_size if original_size > 0 else 0
        
        # Cloud Storageアップロード
        download_url, expires_at = await storage_service.upload_and_get_url(
            output_file_path,
            f"video/{compression_options.output_format}"
        )
        
        # ファイル情報構築
        file_info = FileInfo(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            duration=metadata.get("input_info", {}).get("duration"),
            original_format=metadata.get("input_info", {}).get("format")
        )
        
        # レスポンス構築
        response = CompressionResponse(
            status="success",
            download_url=download_url,
            expires_at=expires_at,
            processing_time=processing_time,
            file_info=file_info
        )
        
        return response
        
    except VideoCompressionError as e:
        # カスタム例外処理
        status_code = {
            "FILE_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "INVALID_OPTIONS_ERROR": status.HTTP_400_BAD_REQUEST,
            "PROCESSING_TIMEOUT": status.HTTP_408_REQUEST_TIMEOUT,
            "FFMPEG_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "STORAGE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }.get(e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        raise HTTPException(status_code=status_code, detail=e.message)
        
    except HTTPException:
        # FastAPIのHTTPExceptionはそのまま再発生
        raise
        
    except Exception as e:
        # 予期しないエラー
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
        
    finally:
        # 一時ファイルクリーンアップ
        for file_path in [input_file_path, output_file_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass  # クリーンアップエラーは無視

async def save_upload_file(upload_file: UploadFile) -> str:
    """アップロードファイルを一時ディレクトリに保存"""
    try:
        # 一意なファイル名生成
        suffix = os.path.splitext(upload_file.filename)[1]
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=settings.TEMP_DIR
        ) as tmp_file:
            # ファイル内容をコピー
            content = await upload_file.read()
            tmp_file.write(content)
            return tmp_file.name
    except Exception as e:
        raise FileValidationError(f"Failed to save uploaded file: {str(e)}")

@app.exception_handler(VideoCompressionError)
async def video_compression_exception_handler(request, exc: VideoCompressionError):
    """動画圧縮エラーのハンドラー"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )