"""
ParQL context and configuration management.

This module handles configuration settings, profiles, and environment variables
for ParQL operations.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class ParQLContext:
    """ParQL execution context with configuration settings."""
    
    # Performance settings
    threads: Optional[int] = None
    memory_limit: Optional[str] = None
    
    # Output settings
    output_format: str = "table"
    max_width: Optional[int] = None
    truncate_columns: bool = True
    show_progress: bool = True
    verbose: bool = False
    quiet: bool = False
    
    # Caching settings
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    cache_ttl: Optional[str] = None
    
    # Security settings
    allow_remote: bool = True
    
    # AWS/S3 settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_region: Optional[str] = None
    
    # Google Cloud settings
    google_application_credentials: Optional[str] = None
    
    # Azure settings
    azure_storage_account: Optional[str] = None
    azure_storage_key: Optional[str] = None
    
    # HDFS settings
    hdfs_namenode: Optional[str] = None
    hdfs_port: int = 9000
    
    # Additional settings
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize context from environment variables."""
        self._load_from_env()
        self._set_defaults()
    
    def _load_from_env(self):
        """Load settings from environment variables."""
        # Performance settings
        if not self.threads and os.getenv("PARQL_THREADS"):
            self.threads = int(os.getenv("PARQL_THREADS"))
        
        if not self.memory_limit and os.getenv("PARQL_MEMORY_LIMIT"):
            self.memory_limit = os.getenv("PARQL_MEMORY_LIMIT")
        
        # Output settings
        if os.getenv("PARQL_OUTPUT_FORMAT"):
            self.output_format = os.getenv("PARQL_OUTPUT_FORMAT")
        
        if os.getenv("PARQL_MAX_WIDTH"):
            self.max_width = int(os.getenv("PARQL_MAX_WIDTH"))
        
        if os.getenv("PARQL_VERBOSE"):
            self.verbose = os.getenv("PARQL_VERBOSE").lower() in ("true", "1", "yes")
        
        if os.getenv("PARQL_QUIET"):
            self.quiet = os.getenv("PARQL_QUIET").lower() in ("true", "1", "yes")
        
        # AWS settings
        self.aws_access_key_id = self.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = self.aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = self.aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        self.aws_region = self.aws_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        # Google Cloud settings
        self.google_application_credentials = (
            self.google_application_credentials or 
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        
        # Azure settings
        self.azure_storage_account = (
            self.azure_storage_account or 
            os.getenv("AZURE_STORAGE_ACCOUNT")
        )
        self.azure_storage_key = (
            self.azure_storage_key or 
            os.getenv("AZURE_STORAGE_KEY")
        )
        
        # HDFS settings
        self.hdfs_namenode = (
            self.hdfs_namenode or 
            os.getenv("HDFS_NAMENODE")
        )
        if os.getenv("HDFS_PORT"):
            self.hdfs_port = int(os.getenv("HDFS_PORT"))
    
    def _set_defaults(self):
        """Set default values for unspecified settings."""
        if self.cache_dir is None:
            self.cache_dir = Path.home() / ".parql" / "cache"
        
        if self.threads is None:
            self.threads = min(8, os.cpu_count() or 4)
    
    def get_aws_credentials(self) -> Dict[str, str]:
        """Get AWS credentials as dictionary."""
        creds = {}
        if self.aws_access_key_id:
            creds["aws_access_key_id"] = self.aws_access_key_id
        if self.aws_secret_access_key:
            creds["aws_secret_access_key"] = self.aws_secret_access_key
        if self.aws_session_token:
            creds["aws_session_token"] = self.aws_session_token
        if self.aws_region:
            creds["region_name"] = self.aws_region
        return creds
    
    def update(self, **kwargs):
        """Update context settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.config[key] = value
