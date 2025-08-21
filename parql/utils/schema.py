"""
Schema inspection and manipulation utilities.

This module provides tools for analyzing Parquet file schemas,
statistics, and metadata.
"""

import pandas as pd
import pyarrow.parquet as pq
from typing import Dict, List, Optional, Any
from pathlib import Path

from parql.utils.exceptions import ParQLDataError


class SchemaInspector:
    """Utility class for schema inspection and analysis."""
    
    def __init__(self, file_path: str):
        """Initialize schema inspector.
        
        Args:
            file_path: Path to Parquet file
        """
        self.file_path = file_path
        try:
            self.parquet_file = pq.ParquetFile(file_path)
        except Exception as e:
            raise ParQLDataError(f"Failed to open Parquet file: {e}")
    
    def get_schema(self) -> pd.DataFrame:
        """Get schema information as DataFrame.
        
        Returns:
            DataFrame with column information
        """
        schema = self.parquet_file.schema_arrow
        
        schema_data = []
        for i, field in enumerate(schema):
            schema_data.append({
                'column_name': field.name,
                'data_type': str(field.type),
                'nullable': field.nullable,
                'metadata': dict(field.metadata) if field.metadata else {}
            })
        
        return pd.DataFrame(schema_data)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get file metadata.
        
        Returns:
            Dictionary with file metadata
        """
        metadata = self.parquet_file.metadata
        
        return {
            'num_rows': metadata.num_rows,
            'num_columns': metadata.num_columns,
            'num_row_groups': metadata.num_row_groups,
            'format_version': metadata.format_version,
            'created_by': metadata.created_by,
            'serialized_size': metadata.serialized_size
        }
    
    def get_row_group_metadata(self, row_group_idx: int = 0) -> Dict[str, Any]:
        """Get metadata for specific row group.
        
        Args:
            row_group_idx: Row group index
            
        Returns:
            Dictionary with row group metadata
        """
        if row_group_idx >= self.parquet_file.metadata.num_row_groups:
            raise ParQLDataError(f"Row group {row_group_idx} does not exist")
        
        row_group = self.parquet_file.metadata.row_group(row_group_idx)
        
        return {
            'num_rows': row_group.num_rows,
            'num_columns': row_group.num_columns,
            'total_byte_size': row_group.total_byte_size,
            'compressed_size': getattr(row_group, 'compressed_size', None)
        }
    
    def get_column_statistics(self, column_name: str) -> Dict[str, Any]:
        """Get statistics for a specific column.
        
        Args:
            column_name: Name of the column
            
        Returns:
            Dictionary with column statistics
        """
        schema = self.parquet_file.schema_arrow
        
        # Find column index
        column_idx = None
        for i, field in enumerate(schema):
            if field.name == column_name:
                column_idx = i
                break
        
        if column_idx is None:
            raise ParQLDataError(f"Column '{column_name}' not found")
        
        stats = {}
        
        # Collect statistics from all row groups
        for rg_idx in range(self.parquet_file.metadata.num_row_groups):
            row_group = self.parquet_file.metadata.row_group(rg_idx)
            column = row_group.column(column_idx)
            
            if column.statistics:
                stats[f'row_group_{rg_idx}'] = {
                    'min': column.statistics.min,
                    'max': column.statistics.max,
                    'null_count': column.statistics.null_count,
                    'distinct_count': getattr(column.statistics, 'distinct_count', None)
                }
        
        return stats
    
    def get_column_info(self) -> pd.DataFrame:
        """Get detailed column information including statistics.
        
        Returns:
            DataFrame with detailed column information
        """
        schema = self.parquet_file.schema_arrow
        column_info = []
        
        for i, field in enumerate(schema):
            info = {
                'column_name': field.name,
                'data_type': str(field.type),
                'nullable': field.nullable,
                'total_null_count': 0,
                'total_rows': 0,
                'min_value': None,
                'max_value': None
            }
            
            # Aggregate statistics across row groups
            for rg_idx in range(self.parquet_file.metadata.num_row_groups):
                row_group = self.parquet_file.metadata.row_group(rg_idx)
                column = row_group.column(i)
                
                info['total_rows'] += row_group.num_rows
                
                if column.statistics:
                    info['total_null_count'] += column.statistics.null_count or 0
                    
                    if info['min_value'] is None or (column.statistics.min and column.statistics.min < info['min_value']):
                        info['min_value'] = column.statistics.min
                    
                    if info['max_value'] is None or (column.statistics.max and column.statistics.max > info['max_value']):
                        info['max_value'] = column.statistics.max
            
            # Calculate null percentage
            if info['total_rows'] > 0:
                info['null_percentage'] = (info['total_null_count'] / info['total_rows']) * 100
            else:
                info['null_percentage'] = 0
            
            column_info.append(info)
        
        return pd.DataFrame(column_info)
    
    def compare_schema(self, other_file: str) -> pd.DataFrame:
        """Compare schema with another Parquet file.
        
        Args:
            other_file: Path to other Parquet file
            
        Returns:
            DataFrame showing schema differences
        """
        try:
            other_inspector = SchemaInspector(other_file)
        except Exception as e:
            raise ParQLDataError(f"Failed to inspect other file: {e}")
        
        schema1 = self.get_schema()
        schema2 = other_inspector.get_schema()
        
        # Create comparison
        comparison = []
        
        # Columns in both files
        common_cols = set(schema1['column_name']) & set(schema2['column_name'])
        
        for col in common_cols:
            row1 = schema1[schema1['column_name'] == col].iloc[0]
            row2 = schema2[schema2['column_name'] == col].iloc[0]
            
            status = "SAME" if row1['data_type'] == row2['data_type'] else "DIFFERENT"
            
            comparison.append({
                'column_name': col,
                'status': status,
                'file1_type': row1['data_type'],
                'file2_type': row2['data_type'],
                'file1_nullable': row1['nullable'],
                'file2_nullable': row2['nullable']
            })
        
        # Columns only in first file
        only_in_1 = set(schema1['column_name']) - set(schema2['column_name'])
        for col in only_in_1:
            row1 = schema1[schema1['column_name'] == col].iloc[0]
            comparison.append({
                'column_name': col,
                'status': 'ONLY_IN_FILE1',
                'file1_type': row1['data_type'],
                'file2_type': None,
                'file1_nullable': row1['nullable'],
                'file2_nullable': None
            })
        
        # Columns only in second file
        only_in_2 = set(schema2['column_name']) - set(schema1['column_name'])
        for col in only_in_2:
            row2 = schema2[schema2['column_name'] == col].iloc[0]
            comparison.append({
                'column_name': col,
                'status': 'ONLY_IN_FILE2',
                'file1_type': None,
                'file2_type': row2['data_type'],
                'file1_nullable': None,
                'file2_nullable': row2['nullable']
            })
        
        return pd.DataFrame(comparison).sort_values('column_name')
