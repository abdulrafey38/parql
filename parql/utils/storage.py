"""
Storage handlers for different backends (S3, GCS, Azure, HTTP, HDFS).

This module provides unified access to various storage systems.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from parql.utils.exceptions import ParQLIOError


class StorageHandler(ABC):
    """Abstract base class for storage handlers."""
    
    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read data from storage."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists in storage."""
        pass
    
    @abstractmethod
    def list(self, path: str) -> list:
        """List contents of a directory/prefix."""
        pass


class S3Handler(StorageHandler):
    """Handler for Amazon S3 storage."""
    
    def __init__(self, credentials: Optional[Dict[str, str]] = None):
        """Initialize S3 handler.
        
        Args:
            credentials: AWS credentials dictionary
        """
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
        except ImportError:
            raise ParQLIOError("boto3 is required for S3 access. Install with: pip install boto3")
        
        try:
            if credentials:
                self.s3_client = boto3.client('s3', **credentials)
            else:
                self.s3_client = boto3.client('s3')
        except NoCredentialsError:
            raise ParQLIOError("AWS credentials not found. Please configure credentials.")
    
    def _parse_s3_path(self, path: str) -> tuple:
        """Parse S3 path into bucket and key."""
        parsed = urlparse(path)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        return bucket, key
    
    def read(self, path: str) -> bytes:
        """Read data from S3."""
        bucket, key = self._parse_s3_path(path)
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        except Exception as e:
            raise ParQLIOError(f"Failed to read from S3: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if S3 object exists."""
        bucket, key = self._parse_s3_path(path)
        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False
    
    def list(self, path: str) -> list:
        """List S3 objects with prefix."""
        bucket, prefix = self._parse_s3_path(path)
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            raise ParQLIOError(f"Failed to list S3 objects: {e}")


class GCSHandler(StorageHandler):
    """Handler for Google Cloud Storage."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize GCS handler.
        
        Args:
            credentials_path: Path to service account credentials JSON
        """
        try:
            from google.cloud import storage
        except ImportError:
            raise ParQLIOError("google-cloud-storage is required for GCS access.")
        
        try:
            if credentials_path:
                self.client = storage.Client.from_service_account_json(credentials_path)
            else:
                self.client = storage.Client()
        except Exception as e:
            raise ParQLIOError(f"Failed to initialize GCS client: {e}")
    
    def _parse_gcs_path(self, path: str) -> tuple:
        """Parse GCS path into bucket and blob name."""
        parsed = urlparse(path)
        
        # Handle anonymous@ format for public datasets
        if '@' in parsed.netloc:
            # Format: gs://anonymous@bucket-name/path
            bucket = parsed.netloc.split('@', 1)[1]
        else:
            bucket = parsed.netloc
            
        blob_name = parsed.path.lstrip('/')
        return bucket, blob_name
    
    def read(self, path: str) -> bytes:
        """Read data from GCS."""
        bucket_name, blob_name = self._parse_gcs_path(path)
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes()
        except Exception as e:
            raise ParQLIOError(f"Failed to read from GCS: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if GCS blob exists."""
        bucket_name, blob_name = self._parse_gcs_path(path)
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.exists()
        except Exception:
            return False
    
    def list(self, path: str) -> list:
        """List GCS blobs with prefix."""
        bucket_name, prefix = self._parse_gcs_path(path)
        try:
            bucket = self.client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise ParQLIOError(f"Failed to list GCS blobs: {e}")


class AzureHandler(StorageHandler):
    """Handler for Azure Blob Storage and Data Lake Storage."""
    
    def __init__(self, account_name: str, account_key: Optional[str] = None):
        """Initialize Azure handler.
        
        Args:
            account_name: Azure storage account name
            account_key: Azure storage account key
        """
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ParQLIOError("azure-storage-blob is required for Azure access.")
        
        try:
            if account_key:
                account_url = f"https://{account_name}.blob.core.windows.net"
                self.client = BlobServiceClient(account_url=account_url, credential=account_key)
            else:
                # Try to use default Azure credentials
                account_url = f"https://{account_name}.blob.core.windows.net"
                self.client = BlobServiceClient(account_url=account_url)
        except Exception as e:
            raise ParQLIOError(f"Failed to initialize Azure client: {e}")
    
    def _parse_azure_path(self, path: str) -> tuple:
        """Parse Azure path into container and blob name.
        
        Supports:
        - abfs://container@account.dfs.core.windows.net/path
        - wasbs://container@account.blob.core.windows.net/path
        """
        parsed = urlparse(path)
        
        if parsed.scheme == 'abfs':
            # abfs://container@account.dfs.core.windows.net/path
            # netloc format: container@account.dfs.core.windows.net
            if '@' in parsed.netloc:
                container = parsed.netloc.split('@')[0]
            else:
                raise ParQLIOError("Invalid abfs:// URL format. Expected: abfs://container@account.dfs.core.windows.net/path")
        elif parsed.scheme == 'wasbs':
            # wasbs://container@account.blob.core.windows.net/path
            # netloc format: container@account.blob.core.windows.net
            if '@' in parsed.netloc:
                container = parsed.netloc.split('@')[0]
            else:
                raise ParQLIOError("Invalid wasbs:// URL format. Expected: wasbs://container@account.blob.core.windows.net/path")
        else:
            raise ParQLIOError(f"Unsupported Azure scheme: {parsed.scheme}")
        
        blob_name = parsed.path.lstrip('/')
        return container, blob_name
    
    def read(self, path: str) -> bytes:
        """Read data from Azure Blob Storage."""
        container, blob_name = self._parse_azure_path(path)
        try:
            blob_client = self.client.get_blob_client(container=container, blob=blob_name)
            return blob_client.download_blob().readall()
        except Exception as e:
            raise ParQLIOError(f"Failed to read from Azure: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if Azure blob exists."""
        container, blob_name = self._parse_azure_path(path)
        try:
            blob_client = self.client.get_blob_client(container=container, blob=blob_name)
            return blob_client.exists()
        except Exception:
            return False
    
    def list(self, path: str) -> list:
        """List Azure blobs with prefix."""
        container, prefix = self._parse_azure_path(path)
        try:
            container_client = self.client.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise ParQLIOError(f"Failed to list Azure blobs: {e}")


class HDFSHandler(StorageHandler):
    """Handler for Hadoop Distributed File System (HDFS)."""
    
    def __init__(self, namenode: Optional[str] = None, port: int = 9000):
        """Initialize HDFS handler.
        
        Args:
            namenode: HDFS namenode hostname or IP
            port: HDFS namenode port (default: 9000)
        """
        try:
            from hdfs import InsecureClient
        except ImportError:
            raise ParQLIOError("hdfs is required for HDFS access. Install with: pip install hdfs")
        
        try:
            if namenode:
                self.client = InsecureClient(f"http://{namenode}:{port}")
            else:
                # Try to use default HDFS configuration
                self.client = InsecureClient("http://localhost:9000")
        except Exception as e:
            raise ParQLIOError(f"Failed to initialize HDFS client: {e}")
    
    def _parse_hdfs_path(self, path: str) -> str:
        """Parse HDFS path."""
        parsed = urlparse(path)
        return parsed.path
    
    def read(self, path: str) -> bytes:
        """Read data from HDFS."""
        hdfs_path = self._parse_hdfs_path(path)
        try:
            with self.client.read(hdfs_path) as reader:
                return reader.read()
        except Exception as e:
            raise ParQLIOError(f"Failed to read from HDFS: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if HDFS file exists."""
        hdfs_path = self._parse_hdfs_path(path)
        try:
            return self.client.status(hdfs_path, strict=False) is not None
        except Exception:
            return False
    
    def list(self, path: str) -> list:
        """List HDFS files with prefix."""
        hdfs_path = self._parse_hdfs_path(path)
        try:
            files = []
            for file_info in self.client.list(hdfs_path, status=True):
                files.append(file_info[0])
            return files
        except Exception as e:
            raise ParQLIOError(f"Failed to list HDFS files: {e}")


class HTTPHandler(StorageHandler):
    """Handler for HTTP/HTTPS URLs."""
    
    def __init__(self):
        """Initialize HTTP handler."""
        pass
    
    def read(self, path: str) -> bytes:
        """Read data from HTTP/HTTPS URL."""
        try:
            import requests
        except ImportError:
            raise ParQLIOError("requests is required for HTTP access.")
        
        try:
            response = requests.get(path, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise ParQLIOError(f"Failed to read from HTTP: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if HTTP resource exists."""
        try:
            import requests
        except ImportError:
            return False
        
        try:
            response = requests.head(path)
            return response.status_code == 200
        except Exception:
            return False
    
    def list(self, path: str) -> list:
        """List is not supported for HTTP."""
        raise ParQLIOError("List operation not supported for HTTP URLs")


def get_storage_handler(path: str, context: Optional[Any] = None) -> StorageHandler:
    """Get appropriate storage handler for the given path.
    
    Args:
        path: Data source path or URL
        context: ParQL context with credentials
        
    Returns:
        Appropriate storage handler instance
    """
    parsed = urlparse(path)
    scheme = parsed.scheme.lower()
    
    if scheme == 's3':
        credentials = context.get_aws_credentials() if context else None
        return S3Handler(credentials)
    elif scheme == 'gs':
        creds_path = context.google_application_credentials if context else None
        return GCSHandler(creds_path)
    elif scheme in ('http', 'https'):
        return HTTPHandler()
    elif scheme == 'hdfs':
        namenode = context.hdfs_namenode if context else None
        port = context.hdfs_port if context else 9000
        return HDFSHandler(namenode, port)
    elif scheme in ('abfs', 'wasbs'):
        # Azure Blob Storage and Data Lake Storage
        account_name = context.azure_storage_account if context else None
        account_key = context.azure_storage_key if context else None
        if not account_name:
            raise ParQLIOError("Azure storage account name is required for abfs:// and wasbs:// URLs")
        return AzureHandler(account_name, account_key)
    else:
        raise ParQLIOError(f"Unsupported storage scheme: {scheme}")
