"""
Test cases for the ParQL engine.
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext
from parql.utils.exceptions import ParQLError, ParQLDataError


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'value': [10.5, 20.3, 15.7, 30.2, 25.1],
        'category': ['A', 'B', 'A', 'C', 'B'],
        'active': [True, False, True, True, False]
    }
    return pd.DataFrame(data)


@pytest.fixture
def temp_parquet_file(sample_data):
    """Create a temporary Parquet file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        sample_data.to_parquet(tmp.name, index=False)
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def engine():
    """Create a ParQL engine for testing."""
    context = ParQLContext(verbose=False, quiet=True)
    return ParQLEngine(context)


class TestParQLEngine:
    """Test cases for ParQL engine core functionality."""
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = ParQLEngine()
        assert engine.context is not None
        assert engine._conn is None
        assert engine._tables == {}
    
    def test_load_source(self, engine, temp_parquet_file):
        """Test loading a Parquet source."""
        table_name = engine.load_source(temp_parquet_file)
        assert table_name == 't'
        assert table_name in engine._tables
        assert engine._tables[table_name] == temp_parquet_file
    
    def test_load_source_with_alias(self, engine, temp_parquet_file):
        """Test loading a source with custom alias."""
        table_name = engine.load_source(temp_parquet_file, 'my_table')
        assert table_name == 'my_table'
        assert table_name in engine._tables
    
    def test_head(self, engine, temp_parquet_file):
        """Test head operation."""
        df = engine.head(temp_parquet_file, n=3)
        assert len(df) == 3
        assert list(df.columns) == ['id', 'name', 'value', 'category', 'active']
        assert df.iloc[0]['name'] == 'Alice'
    
    def test_tail(self, engine, temp_parquet_file):
        """Test tail operation."""
        df = engine.tail(temp_parquet_file, n=2)
        assert len(df) == 2
        assert df.iloc[-1]['name'] == 'Eve'
    
    def test_schema(self, engine, temp_parquet_file):
        """Test schema operation."""
        df = engine.schema(temp_parquet_file)
        assert len(df) == 5  # 5 columns
        assert 'column_name' in df.columns
        assert 'data_type' in df.columns or 'column_type' in df.columns
        
        # Check that all our columns are present
        column_names = df['column_name'].tolist()
        expected_columns = ['id', 'name', 'value', 'category', 'active']
        for col in expected_columns:
            assert col in column_names
    
    def test_select_all(self, engine, temp_parquet_file):
        """Test select all columns."""
        df = engine.select(temp_parquet_file)
        assert len(df) == 5
        assert len(df.columns) == 5
    
    def test_select_columns(self, engine, temp_parquet_file):
        """Test select specific columns."""
        df = engine.select(temp_parquet_file, columns=['name', 'value'])
        assert len(df) == 5
        assert len(df.columns) == 2
        assert list(df.columns) == ['name', 'value']
    
    def test_select_with_where(self, engine, temp_parquet_file):
        """Test select with WHERE clause."""
        df = engine.select(temp_parquet_file, where="value > 20")
        assert len(df) == 3  # Bob, David, Eve
        assert all(df['value'] > 20)
    
    def test_select_with_order_by(self, engine, temp_parquet_file):
        """Test select with ORDER BY."""
        df = engine.select(temp_parquet_file, order_by="value DESC")
        assert len(df) == 5
        assert df.iloc[0]['value'] == 30.2  # David has highest value
        assert df.iloc[-1]['value'] == 10.5  # Alice has lowest value
    
    def test_select_with_limit(self, engine, temp_parquet_file):
        """Test select with LIMIT."""
        df = engine.select(temp_parquet_file, limit=2)
        assert len(df) == 2
    
    def test_count(self, engine, temp_parquet_file):
        """Test count operation."""
        count = engine.count(temp_parquet_file)
        assert count == 5
    
    def test_count_with_where(self, engine, temp_parquet_file):
        """Test count with WHERE clause."""
        count = engine.count(temp_parquet_file, where="active = true")
        assert count == 3  # Alice, Charlie, David
    
    def test_distinct(self, engine, temp_parquet_file):
        """Test distinct operation."""
        df = engine.distinct(temp_parquet_file, columns=['category'])
        assert len(df) == 3  # A, B, C
        categories = sorted(df['category'].tolist())
        assert categories == ['A', 'B', 'C']
    
    def test_aggregate_simple(self, engine, temp_parquet_file):
        """Test simple aggregation."""
        df = engine.aggregate(temp_parquet_file, group_by=['category'])
        assert len(df) == 3  # A, B, C
        assert 'category' in df.columns
        assert 'count' in df.columns
    
    def test_aggregate_with_functions(self, engine, temp_parquet_file):
        """Test aggregation with custom functions."""
        df = engine.aggregate(
            temp_parquet_file, 
            group_by=['category'],
            aggregations={'avg_value': 'AVG(value)', 'total_count': 'COUNT(*)'}
        )
        assert len(df) == 3
        assert 'category' in df.columns
        assert 'avg_value' in df.columns
        assert 'total_count' in df.columns
    
    def test_execute_sql(self, engine, temp_parquet_file):
        """Test direct SQL execution."""
        table_name = engine.load_source(temp_parquet_file)
        df = engine.execute_sql(f"SELECT name, value FROM {table_name} WHERE value > 15 ORDER BY value")
        assert len(df) >= 3
        assert list(df.columns) == ['name', 'value']
        assert all(df['value'] > 15)
    
    def test_write_parquet(self, engine, temp_parquet_file):
        """Test writing to Parquet format."""
        df = engine.head(temp_parquet_file, n=3)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            engine.write(df, output_path, format='parquet')
            
            # Verify the file was created
            assert os.path.exists(output_path)
            
            # Verify we can read it back
            df_read = pd.read_parquet(output_path)
            assert len(df_read) == 3
            assert list(df_read.columns) == list(df.columns)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_write_csv(self, engine, temp_parquet_file):
        """Test writing to CSV format."""
        df = engine.head(temp_parquet_file, n=2)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            engine.write(df, output_path, format='csv')
            
            # Verify the file was created
            assert os.path.exists(output_path)
            
            # Verify we can read it back
            df_read = pd.read_csv(output_path)
            assert len(df_read) == 2
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_invalid_source(self, engine):
        """Test handling of invalid source."""
        with pytest.raises(ParQLDataError):
            engine.load_source('/nonexistent/file.parquet')
    
    def test_invalid_sql(self, engine, temp_parquet_file):
        """Test handling of invalid SQL."""
        with pytest.raises(ParQLError):
            engine.execute_sql("SELECT * FROM nonexistent_table")


class TestJoinOperations:
    """Test join operations."""
    
    @pytest.fixture
    def second_sample_data(self):
        """Create second dataset for joins."""
        data = {
            'id': [1, 2, 3, 6, 7],
            'description': ['First', 'Second', 'Third', 'Sixth', 'Seventh'],
            'score': [90, 85, 95, 80, 88]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def second_temp_file(self, second_sample_data):
        """Create second temporary Parquet file."""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            second_sample_data.to_parquet(tmp.name, index=False)
            yield tmp.name
        os.unlink(tmp.name)
    
    def test_inner_join(self, engine, temp_parquet_file, second_temp_file):
        """Test inner join operation."""
        df = engine.join(temp_parquet_file, second_temp_file, 'id', 'inner')
        assert len(df) == 3  # Only IDs 1, 2, 3 exist in both
        assert 'name' in df.columns
        assert 'description' in df.columns
    
    def test_left_join(self, engine, temp_parquet_file, second_temp_file):
        """Test left join operation."""
        df = engine.join(temp_parquet_file, second_temp_file, 'id', 'left')
        assert len(df) == 5  # All rows from left table
        assert 'name' in df.columns
        assert 'description' in df.columns
    
    def test_join_complex_condition(self, engine, temp_parquet_file, second_temp_file):
        """Test join with complex condition."""
        # Load tables with specific aliases
        left_table = engine.load_source(temp_parquet_file, 'left_tbl')
        right_table = engine.load_source(second_temp_file, 'right_tbl')
        
        # Test complex join condition
        df = engine.execute_sql(f"""
            SELECT l.name, r.description, l.value, r.score
            FROM {left_table} l
            INNER JOIN {right_table} r ON l.id = r.id AND r.score > 85
        """)
        
        assert len(df) >= 2  # Should have matches with score > 85
        assert 'name' in df.columns
        assert 'description' in df.columns
