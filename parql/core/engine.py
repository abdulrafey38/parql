"""
Core ParQL engine powered by DuckDB.

This module provides the main ParQL engine that handles data loading,
query execution, and result formatting.
"""

import os
import glob
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from parql.core.context import ParQLContext
from parql.utils.storage import get_storage_handler
from parql.utils.schema import SchemaInspector
from parql.utils.exceptions import ParQLError, ParQLDataError


class ParQLEngine:
    """Main ParQL engine for executing operations on Parquet datasets."""
    
    def __init__(self, context: Optional[ParQLContext] = None):
        """Initialize the ParQL engine.
        
        Args:
            context: Optional ParQL context with configuration settings
        """
        self.context = context or ParQLContext()
        self.console = Console()
        self._conn = None
        self._tables = {}  # Track registered tables
        
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection."""
        if self._conn is None:
            self._conn = duckdb.connect()
            self._setup_connection()
        return self._conn
    
    def _setup_connection(self):
        """Setup DuckDB connection with extensions and settings."""
        # Install and load useful extensions
        try:
            self.conn.execute("INSTALL httpfs;")
            self.conn.execute("LOAD httpfs;")
        except Exception:
            pass  # Extension might already be installed
            
        # Configure for GCS access
        try:
            self.conn.execute("SET s3_region='us-east-1';")
            self.conn.execute("SET s3_url_style='path';")
        except Exception:
            pass
            
        # Set memory limit if specified
        if self.context.memory_limit:
            self.conn.execute(f"SET memory_limit='{self.context.memory_limit}';")
            
        # Set thread count
        if self.context.threads:
            self.conn.execute(f"SET threads={self.context.threads};")
    
    def load_source(self, source: str, alias: Optional[str] = None) -> str:
        """Load a data source and return the table name.
        
        Args:
            source: Path to parquet file(s), directory, or URL
            alias: Optional alias for the table
            
        Returns:
            Table name that can be used in queries
        """
        table_name = alias or self._generate_table_name()
        
        # Reject invalid azure:// scheme
        if source.startswith('azure://'):
            raise ParQLDataError("Invalid Azure URI scheme 'azure://'. Use 'abfs://', 'wasbs://', or 'https://' instead.")
        
        # Convert GCS paths to HTTP URLs for public datasets
        if source.startswith('gs://'):
            if 'anonymous@' in source:
                # Convert gs://anonymous@bucket/path to https://storage.googleapis.com/bucket/path
                source = source.replace('gs://anonymous@', 'https://storage.googleapis.com/')
        
        # Handle Azure URI schemes
        if source.startswith('abfs://'):
            # Convert abfs://container@account.dfs.core.windows.net/path to https://account.blob.core.windows.net/container/path
            # This requires Azure credentials to be configured
            if '@' in source and '.dfs.core.windows.net' in source:
                parts = source.replace('abfs://', '').split('@')
                container = parts[0]
                account = parts[1].split('.')[0]
                path = source.split('.dfs.core.windows.net/')[1]
                source = f"https://{account}.blob.core.windows.net/{container}/{path}"
        
        elif source.startswith('wasbs://'):
            # Convert wasbs://container@account.blob.core.windows.net/path to https://account.blob.core.windows.net/container/path
            if '@' in source and '.blob.core.windows.net' in source:
                parts = source.replace('wasbs://', '').split('@')
                container = parts[0]
                account = parts[1].split('.')[0]
                path = source.split('.blob.core.windows.net/')[1]
                source = f"https://{account}.blob.core.windows.net/{container}/{path}"
        
        # Handle different source types
        if self._is_url(source):
            sql = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{source}')"
        elif os.path.isdir(source):
            # Directory - read all parquet files
            pattern = os.path.join(source, "*.parquet")
            sql = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{pattern}')"
        elif "*" in source or "?" in source:
            # Glob pattern
            sql = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{source}')"
        else:
            # Single file
            sql = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{source}')"
        
        try:
            self.conn.execute(sql)
            self._tables[table_name] = source
            return table_name
        except Exception as e:
            raise ParQLDataError(f"Failed to load source '{source}': {e}")
    
    def _is_url(self, path: str) -> bool:
        """Check if path is a URL."""
        parsed = urlparse(path)
        return parsed.scheme in ('http', 'https', 's3', 'gs', 'abfs', 'wasbs', 'hdfs')
    
    def _generate_table_name(self) -> str:
        """Generate a unique table name."""
        count = len(self._tables)
        if count == 0:
            return "t"
        elif count == 1:
            return "u"
        else:
            return f"t{count}"
    
    def execute_sql(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query results as pandas DataFrame
        """
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            raise ParQLError(f"Query execution failed: {e}")
    
    def head(self, source: str, n: int = 10) -> pd.DataFrame:
        """Get first n rows from source.
        
        Args:
            source: Data source path
            n: Number of rows to return
            
        Returns:
            First n rows as DataFrame
        """
        table_name = self.load_source(source)
        query = f"SELECT * FROM {table_name} LIMIT {n}"
        return self.execute_sql(query)
    
    def tail(self, source: str, n: int = 10) -> pd.DataFrame:
        """Get last n rows from source.
        
        Args:
            source: Data source path
            n: Number of rows to return
            
        Returns:
            Last n rows as DataFrame
        """
        table_name = self.load_source(source)
        # Use ORDER BY with OFFSET for tail behavior
        count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        total_rows = self.execute_sql(count_query).iloc[0]['cnt']
        offset = max(0, total_rows - n)
        query = f"SELECT * FROM {table_name} OFFSET {offset}"
        return self.execute_sql(query)
    
    def schema(self, source: str) -> pd.DataFrame:
        """Get schema information for source.
        
        Args:
            source: Data source path
            
        Returns:
            Schema information as DataFrame
        """
        table_name = self.load_source(source)
        query = f"DESCRIBE {table_name}"
        df = self.execute_sql(query)
        
        # Rename columns to match expected format
        if 'column_type' in df.columns:
            df = df.rename(columns={'column_type': 'data_type'})
        
        return df
    
    def select(self, source: str, columns: Optional[List[str]] = None, 
               where: Optional[str] = None, order_by: Optional[str] = None,
               limit: Optional[int] = None) -> pd.DataFrame:
        """Select data with optional filtering and sorting.
        
        Args:
            source: Data source path
            columns: List of columns to select
            where: WHERE clause condition
            order_by: ORDER BY clause
            limit: LIMIT number of rows
            
        Returns:
            Selected data as DataFrame
        """
        table_name = self.load_source(source)
        
        # Build SELECT clause
        if columns:
            cols_str = ", ".join(columns)
        else:
            cols_str = "*"
        
        query = f"SELECT {cols_str} FROM {table_name}"
        
        # Add WHERE clause
        if where:
            query += f" WHERE {where}"
        
        # Add ORDER BY clause  
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Add LIMIT clause
        if limit:
            query += f" LIMIT {limit}"
        
        return self.execute_sql(query)
    
    def count(self, source: str, where: Optional[str] = None) -> int:
        """Count rows in source.
        
        Args:
            source: Data source path
            where: Optional WHERE clause condition
            
        Returns:
            Number of rows
        """
        table_name = self.load_source(source)
        query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        return self.execute_sql(query).iloc[0]['cnt']
    
    def distinct(self, source: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Get distinct rows or distinct values for columns.
        
        Args:
            source: Data source path
            columns: Optional list of columns for distinct operation
            
        Returns:
            Distinct rows/values as DataFrame
        """
        table_name = self.load_source(source)
        
        if columns:
            cols_str = ", ".join(columns)
        else:
            cols_str = "*"
        
        query = f"SELECT DISTINCT {cols_str} FROM {table_name}"
        return self.execute_sql(query)
    
    def aggregate(self, source: str, group_by: Optional[List[str]] = None,
                  aggregations: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """Perform aggregation operations.
        
        Args:
            source: Data source path
            group_by: List of columns to group by
            aggregations: Dict of aggregation expressions
            
        Returns:
            Aggregated data as DataFrame
        """
        table_name = self.load_source(source)
        
        # Build aggregation expressions
        if aggregations:
            agg_exprs = [f"{expr} AS {alias}" for alias, expr in aggregations.items()]
            agg_str = ", ".join(agg_exprs)
        else:
            agg_str = "COUNT(*) AS count"
        
        query = f"SELECT"
        
        # Add GROUP BY columns
        if group_by:
            group_cols = ", ".join(group_by)
            query += f" {group_cols}, {agg_str} FROM {table_name} GROUP BY {group_cols}"
        else:
            query += f" {agg_str} FROM {table_name}"
        
        return self.execute_sql(query)
    
    def join(self, left_source: str, right_source: str, on: str, 
             how: str = "inner") -> pd.DataFrame:
        """Join two data sources.
        
        Args:
            left_source: Left data source
            right_source: Right data source  
            on: Join condition
            how: Join type (inner, left, right, full)
            
        Returns:
            Joined data as DataFrame
        """
        left_table = self.load_source(left_source, "left_tbl")
        right_table = self.load_source(right_source, "right_tbl")
        
        join_type = how.upper()
        
        # Handle simple column name joins by prefixing with table names
        if ' = ' not in on and ' ON ' not in on.upper() and '.' not in on:
            # Simple column name like "user_id"
            on_condition = f"{left_table}.{on} = {right_table}.{on}"
        else:
            # Complex join condition, use as is
            on_condition = on
        
        query = f"""
        SELECT * FROM {left_table} 
        {join_type} JOIN {right_table} ON {on_condition}
        """
        
        return self.execute_sql(query)
    
    def write(self, df: pd.DataFrame, output_path: str, format: str = "parquet",
              mode: str = "overwrite", **kwargs) -> None:
        """Write DataFrame to file.
        
        Args:
            df: DataFrame to write
            output_path: Output file path
            format: Output format (parquet, csv, json, etc.)
            mode: Write mode (overwrite, append)
            **kwargs: Additional format-specific options
        """
        if format.lower() == "parquet":
            df.to_parquet(output_path, index=False, **kwargs)
        elif format.lower() == "csv":
            df.to_csv(output_path, index=False, **kwargs)
        elif format.lower() == "json":
            df.to_json(output_path, orient="records", **kwargs)
        else:
            raise ParQLError(f"Unsupported output format: {format}")
    
    def close(self):
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
