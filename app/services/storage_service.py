import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from app.config import settings
from app.utils.exceptions import StorageError

class CloudStorageService:
    """Google Cloud Storage サービス"""
    
    def __init__(self):
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
        except Exception as e:
            raise StorageError(f"Failed to initialize Cloud Storage: {str(e)}")
    
    async def upload_file(self, file_path: str, content_type: str = "video/mp4") -> str:
        """
        ファイルをCloud Storageにアップロード
        
        Args:
            file_path: アップロードするファイルパス
            content_type: MIMEタイプ
            
        Returns:
            アップロードされたファイルのCloud Storage上のパス
        """
        try:
            # ユニークなファイル名生成
            filename = f"compressed/{uuid.uuid4().hex}_{os.path.basename(file_path)}"
            
            # ブロブ作成
            blob = self.bucket.blob(filename)
            
            # メタデータ設定
            blob.metadata = {
                "uploaded_at": datetime.utcnow().isoformat(),
                "ttl": str(settings.TEMP_FILE_TTL)
            }
            
            # ファイルアップロード
            blob.upload_from_filename(
                file_path,
                content_type=content_type
            )
            
            return filename
            
        except GoogleCloudError as e:
            raise StorageError(f"Failed to upload file to Cloud Storage: {str(e)}")
        except Exception as e:
            raise StorageError(f"Unexpected error during file upload: {str(e)}")
    
    def generate_signed_url(
        self,
        blob_name: str,
        expiration: Optional[timedelta] = None
    ) -> str:
        """
        署名付きURLを生成
        
        Args:
            blob_name: Cloud Storage上のファイルパス
            expiration: URL有効期限
            
        Returns:
            署名付きURL
        """
        try:
            if expiration is None:
                expiration = timedelta(seconds=settings.TEMP_FILE_TTL)
            
            blob = self.bucket.blob(blob_name)
            
            # 署名付きURL生成
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            return url
            
        except GoogleCloudError as e:
            raise StorageError(f"Failed to generate signed URL: {str(e)}")
        except Exception as e:
            raise StorageError(f"Unexpected error during URL generation: {str(e)}")
    
    async def upload_and_get_url(
        self,
        file_path: str,
        content_type: str = "video/mp4"
    ) -> tuple[str, datetime]:
        """
        ファイルをアップロードして署名付きURLを取得
        
        Args:
            file_path: アップロードするファイルパス
            content_type: MIMEタイプ
            
        Returns:
            Tuple[署名付きURL, 有効期限]
        """
        # ファイルアップロード
        blob_name = await self.upload_file(file_path, content_type)
        
        # 署名付きURL生成
        signed_url = self.generate_signed_url(blob_name)
        
        # 有効期限計算
        expires_at = datetime.utcnow() + timedelta(seconds=settings.TEMP_FILE_TTL)
        
        return signed_url, expires_at
    
    def delete_file(self, blob_name: str) -> bool:
        """
        ファイルを削除
        
        Args:
            blob_name: 削除するファイルのパス
            
        Returns:
            削除成功したかどうか
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            return True
        except GoogleCloudError:
            return False
        except Exception:
            return False
    
    def cleanup_expired_files(self) -> int:
        """
        期限切れファイルのクリーンアップ
        
        Returns:
            削除されたファイル数
        """
        try:
            deleted_count = 0
            current_time = datetime.utcnow()
            
            # compressed/ プレフィックスのファイルを取得
            blobs = self.client.list_blobs(
                self.bucket,
                prefix="compressed/"
            )
            
            for blob in blobs:
                # メタデータから有効期限をチェック
                if blob.metadata and "uploaded_at" in blob.metadata:
                    uploaded_at = datetime.fromisoformat(blob.metadata["uploaded_at"])
                    ttl = int(blob.metadata.get("ttl", settings.TEMP_FILE_TTL))
                    
                    if current_time > uploaded_at + timedelta(seconds=ttl):
                        blob.delete()
                        deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            # ログに記録するが、エラーは発生させない
            print(f"Cleanup failed: {str(e)}")
            return 0