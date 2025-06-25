import os
import subprocess
import tempfile
import time
import uuid
from typing import List, Tuple, Optional
from app.config import settings
from app.utils.validators import FFmpegValidator
from app.utils.exceptions import FFmpegError, ProcessingTimeoutError, InvalidOptionsError

class FFmpegService:
    """FFmpeg処理サービス"""
    
    def __init__(self):
        self.validator = FFmpegValidator()
    
    async def compress_video(
        self,
        input_path: str,
        ffmpeg_args: List[str],
        output_format: str = "mp4"
    ) -> Tuple[str, dict]:
        """
        動画を圧縮する
        
        Args:
            input_path: 入力ファイルパス
            ffmpeg_args: FFmpegオプション
            output_format: 出力フォーマット
            
        Returns:
            Tuple[出力ファイルパス, メタデータ]
        """
        # オプション検証
        is_valid, error_msg = self.validator.validate_options(ffmpeg_args)
        if not is_valid:
            raise InvalidOptionsError(error_msg)
        
        # 出力ファイルパス生成
        output_path = self._generate_output_path(output_format)
        
        # FFmpegコマンド構築
        cmd = self._build_ffmpeg_command(input_path, output_path, ffmpeg_args)
        
        # 実行前の情報取得
        input_info = await self._get_video_info(input_path)
        
        # FFmpeg実行
        start_time = time.time()
        await self._execute_ffmpeg(cmd)
        processing_time = time.time() - start_time
        
        # 出力ファイル情報取得
        output_info = await self._get_video_info(output_path)
        
        # メタデータ構築
        metadata = {
            "processing_time": processing_time,
            "input_info": input_info,
            "output_info": output_info,
            "ffmpeg_args": ffmpeg_args,
            "command": " ".join(cmd)
        }
        
        return output_path, metadata
    
    def _generate_output_path(self, output_format: str) -> str:
        """出力ファイルパスを生成"""
        filename = f"compressed_{uuid.uuid4().hex}.{output_format}"
        return os.path.join(settings.TEMP_DIR, filename)
    
    def _build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        ffmpeg_args: List[str]
    ) -> List[str]:
        """FFmpegコマンドを構築"""
        cmd = ["ffmpeg", "-i", input_path]
        
        # カスタムオプション追加
        if ffmpeg_args:
            cmd.extend(ffmpeg_args)
        
        # デフォルトオプション（指定されていない場合）
        if not any(arg.startswith('-c:v') or arg == '-vcodec' for arg in ffmpeg_args):
            cmd.extend(["-c:v", "libx264"])
        
        if not any(arg == '-crf' for arg in ffmpeg_args):
            cmd.extend(["-crf", "23"])  # デフォルト品質
        
        # 出力ファイル
        cmd.extend(["-y", output_path])  # -y: 上書き許可
        
        return cmd
    
    async def _execute_ffmpeg(self, cmd: List[str]) -> None:
        """FFmpegを実行"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # タイムアウト付きで実行
            try:
                stdout, stderr = process.communicate(timeout=settings.MAX_PROCESSING_TIME)
            except subprocess.TimeoutExpired:
                process.kill()
                raise ProcessingTimeoutError(settings.MAX_PROCESSING_TIME)
            
            # エラーチェック
            if process.returncode != 0:
                error_message = f"FFmpeg failed: {stderr}"
                raise FFmpegError(error_message, process.returncode)
                
        except FileNotFoundError:
            raise FFmpegError("FFmpeg not found. Please install ffmpeg.")
        except Exception as e:
            if isinstance(e, (ProcessingTimeoutError, FFmpegError)):
                raise
            raise FFmpegError(f"Unexpected error during FFmpeg execution: {str(e)}")
    
    async def _get_video_info(self, file_path: str) -> dict:
        """動画ファイルの情報を取得"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"error": "Could not get video info"}
            
            import json
            info = json.loads(result.stdout)
            
            # 基本情報抽出
            file_size = os.path.getsize(file_path)
            duration = None
            format_name = None
            
            if 'format' in info:
                duration = float(info['format'].get('duration', 0))
                format_name = info['format'].get('format_name', 'unknown')
            
            return {
                "file_size": file_size,
                "duration": duration,
                "format": format_name,
                "streams": len(info.get('streams', []))
            }
            
        except Exception as e:
            return {"error": f"Failed to get video info: {str(e)}"}