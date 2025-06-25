class VideoCompressionError(Exception):
    """動画圧縮関連の基本例外"""
    def __init__(self, message: str, error_code: str = "COMPRESSION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class FFmpegError(VideoCompressionError):
    """FFmpeg実行エラー"""
    def __init__(self, message: str, returncode: int = None):
        self.returncode = returncode
        super().__init__(message, "FFMPEG_ERROR")

class ProcessingTimeoutError(VideoCompressionError):
    """処理タイムアウトエラー"""
    def __init__(self, timeout: int):
        message = f"Processing timeout after {timeout} seconds"
        super().__init__(message, "PROCESSING_TIMEOUT")

class FileValidationError(VideoCompressionError):
    """ファイルバリデーションエラー"""
    def __init__(self, message: str):
        super().__init__(message, "FILE_VALIDATION_ERROR")

class StorageError(VideoCompressionError):
    """ストレージ操作エラー"""
    def __init__(self, message: str):
        super().__init__(message, "STORAGE_ERROR")

class InvalidOptionsError(VideoCompressionError):
    """無効なオプションエラー"""
    def __init__(self, message: str):
        super().__init__(message, "INVALID_OPTIONS_ERROR")