import os
import re
import magic
from typing import List, Tuple
from fastapi import HTTPException, UploadFile
from app.config import settings

class FileValidator:
    """ファイルバリデーション"""
    
    @staticmethod
    def validate_file_size(file: UploadFile) -> bool:
        """ファイルサイズをチェック"""
        if hasattr(file, 'size') and file.size:
            if file.size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size too large. Maximum: {settings.MAX_FILE_SIZE / (1024*1024):.0f}MB"
                )
        return True
    
    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """ファイル拡張子をチェック"""
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        _, ext = os.path.splitext(filename.lower())
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        return True
    
    @staticmethod
    def validate_file_type(file_path: str) -> bool:
        """ファイルタイプをチェック（magic number）"""
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            
            video_types = [
                'video/mp4', 'video/avi', 'video/quicktime', 
                'video/x-msvideo', 'video/x-matroska', 'video/webm'
            ]
            
            if not any(video_type in file_type for video_type in video_types):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid video file type: {file_type}"
                )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"File type validation failed: {str(e)}")
        
        return True

class FFmpegValidator:
    """FFmpegオプションバリデーション"""
    
    @staticmethod
    def validate_options(ffmpeg_args: List[str]) -> Tuple[bool, str]:
        """FFmpegオプションの安全性をチェック"""
        if not ffmpeg_args:
            return True, "No options provided"
        
        # 禁止パターンチェック
        args_str = ' '.join(ffmpeg_args)
        for forbidden in settings.FFMPEG_FORBIDDEN_PATTERNS:
            if forbidden in args_str:
                return False, f"Forbidden pattern detected: {forbidden}"
        
        # 許可されたオプションのみかチェック
        i = 0
        while i < len(ffmpeg_args):
            arg = ffmpeg_args[i]
            
            # オプション（-で始まる）のチェック
            if arg.startswith('-'):
                if arg not in settings.FFMPEG_ALLOWED_OPTIONS:
                    return False, f"Option not allowed: {arg}"
            
            # 値の簡易チェック
            else:
                # ファイルパスや危険な文字列のチェック
                dangerous_chars = ['/', '\\', '|', '&', ';', '`', '$', '(', ')']
                if any(char in arg for char in dangerous_chars):
                    if not FFmpegValidator._is_safe_value(arg):
                        return False, f"Potentially dangerous value: {arg}"
            
            i += 1
        
        return True, "Valid options"
    
    @staticmethod
    def _is_safe_value(value: str) -> bool:
        """値が安全かどうかの詳細チェック"""
        # 数値やコーデック名など安全な値のパターン
        safe_patterns = [
            r'^\d+$',  # 数値
            r'^libx264$', r'^libx265$', r'^libvpx$', r'^aac$',  # コーデック
            r'^(ultrafast|superfast|veryfast|faster|fast|medium|slow|slower|veryslow)$',  # preset
            r'^\d+x\d+$',  # 解像度 (1920x1080)
            r'^scale=\d+:\d+$',  # scale filter
        ]
        
        return any(re.match(pattern, value) for pattern in safe_patterns)