"""
Test cases for the ParQL CLI.
"""

import pytest
import tempfile
import os
import pandas as pd
from click.testing import CliRunner

from parql.cli import cli


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
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIBasicCommands:
    """Test basic CLI commands."""
    
    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'ParQL' in result.output
        assert 'head' in result.output
        assert 'schema' in result.output
    
    def test_head_command(self, runner, temp_parquet_file):
        """Test head command."""
        result = runner.invoke(cli, ['--quiet', 'head', temp_parquet_file, '-n', '3'])
        assert result.exit_code == 0
        # Should contain the data (in quiet mode, just the table)
        lines = result.output.strip().split('\n')
        assert len(lines) >= 3  # At least header + 3 data rows
    
    def test_head_with_columns(self, runner, temp_parquet_file):
        """Test head command with column selection."""
        result = runner.invoke(cli, ['--quiet', 'head', temp_parquet_file, '-n', '2', '-c', 'name,value'])
        assert result.exit_code == 0
        assert 'name' in result.output
        assert 'value' in result.output
        # Should not contain other columns
        assert 'category' not in result.output
    
    def test_schema_command(self, runner, temp_parquet_file):
        """Test schema command."""
        result = runner.invoke(cli, ['--quiet', 'schema', temp_parquet_file])
        assert result.exit_code == 0
        assert 'id' in result.output
        assert 'name' in result.output
        assert 'value' in result.output
    
    def test_count_command(self, runner, temp_parquet_file):
        """Test count command."""
        result = runner.invoke(cli, ['--quiet', 'count', temp_parquet_file])
        assert result.exit_code == 0
        assert '5' in result.output
    
    def test_count_with_where(self, runner, temp_parquet_file):
        """Test count with WHERE clause."""
        result = runner.invoke(cli, ['--quiet', 'count', temp_parquet_file, '-w', 'value > 20'])
        assert result.exit_code == 0
        assert '3' in result.output  # Bob, David, Eve
    
    def test_select_command(self, runner, temp_parquet_file):
        """Test select command."""
        result = runner.invoke(cli, ['--quiet', 'select', temp_parquet_file, '-c', 'name,value', '-l', '3'])
        assert result.exit_code == 0
        assert 'Alice' in result.output
        assert '10.5' in result.output
    
    def test_select_with_where(self, runner, temp_parquet_file):
        """Test select with WHERE clause."""
        result = runner.invoke(cli, ['--quiet', 'select', temp_parquet_file, '-w', 'category = \'A\''])
        assert result.exit_code == 0
        assert 'Alice' in result.output
        assert 'Charlie' in result.output
        assert 'Bob' not in result.output
    
    def test_distinct_command(self, runner, temp_parquet_file):
        """Test distinct command."""
        result = runner.invoke(cli, ['--quiet', 'distinct', temp_parquet_file, '-c', 'category'])
        assert result.exit_code == 0
        # Should contain A, B, C
        assert 'A' in result.output
        assert 'B' in result.output
        assert 'C' in result.output


class TestCLIAggregation:
    """Test aggregation commands."""
    
    def test_agg_simple(self, runner, temp_parquet_file):
        """Test simple aggregation."""
        result = runner.invoke(cli, ['--quiet', 'agg', temp_parquet_file, '-g', 'category'])
        assert result.exit_code == 0
        assert 'category' in result.output
        assert 'count' in result.output
    
    def test_agg_with_functions(self, runner, temp_parquet_file):
        """Test aggregation with custom functions."""
        result = runner.invoke(cli, [
            '--quiet', 'agg', temp_parquet_file, 
            '-g', 'category', 
            '-a', 'avg(value):avg_val,sum(value):total_val'
        ])
        assert result.exit_code == 0
        assert 'category' in result.output
        assert 'avg_val' in result.output
        assert 'total_val' in result.output


class TestCLISQL:
    """Test SQL command."""
    
    def test_sql_simple(self, runner, temp_parquet_file):
        """Test simple SQL query."""
        result = runner.invoke(cli, [
            '--quiet', 'sql', 
            'SELECT name, value FROM t WHERE value > 20',
            '-p', f't={temp_parquet_file}'
        ])
        assert result.exit_code == 0
        assert 'Bob' in result.output
        assert 'David' in result.output
        assert 'Eve' in result.output
        assert 'Alice' not in result.output  # value = 10.5
    
    def test_sql_aggregation(self, runner, temp_parquet_file):
        """Test SQL with aggregation."""
        result = runner.invoke(cli, [
            '--quiet', 'sql',
            'SELECT category, COUNT(*) as cnt, AVG(value) as avg_val FROM t GROUP BY category ORDER BY cnt DESC',
            '-p', f't={temp_parquet_file}'
        ])
        assert result.exit_code == 0
        assert 'category' in result.output
        assert 'cnt' in result.output
        assert 'avg_val' in result.output


class TestCLIFileOperations:
    """Test file I/O operations."""
    
    def test_write_csv(self, runner, temp_parquet_file):
        """Test writing to CSV."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = runner.invoke(cli, [
                '--quiet', 'write', temp_parquet_file, output_path,
                '--format', 'csv', '-c', 'name,value'
            ])
            assert result.exit_code == 0
            
            # Verify the file was created and has content
            assert os.path.exists(output_path)
            with open(output_path, 'r') as f:
                content = f.read()
                assert 'name,value' in content
                assert 'Alice' in content
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_write_json(self, runner, temp_parquet_file):
        """Test writing to JSON."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            result = runner.invoke(cli, [
                '--quiet', 'write', temp_parquet_file, output_path,
                '--format', 'json'
            ])
            assert result.exit_code == 0
            
            # Verify the file was created
            assert os.path.exists(output_path)
            
            # Verify it's valid JSON
            import json
            with open(output_path, 'r') as f:
                data = json.load(f)
                assert len(data) == 5  # All 5 rows since no limit
                assert 'name' in data[0]
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestCLIErrorHandling:
    """Test error handling in CLI commands."""
    
    def test_nonexistent_file(self, runner):
        """Test handling of nonexistent file."""
        result = runner.invoke(cli, ['head', '/nonexistent/file.parquet'])
        assert result.exit_code == 1
        assert 'Error' in result.output
    
    def test_invalid_sql(self, runner, temp_parquet_file):
        """Test handling of invalid SQL."""
        result = runner.invoke(cli, [
            'sql', 'SELECT * FROM nonexistent_table',
            '-p', f't={temp_parquet_file}'
        ])
        assert result.exit_code == 1
        assert 'Error' in result.output
    
    def test_invalid_column(self, runner, temp_parquet_file):
        """Test handling of invalid column name."""
        result = runner.invoke(cli, [
            'select', temp_parquet_file, '-c', 'nonexistent_column'
        ])
        assert result.exit_code == 1
        assert 'Error' in result.output


class TestCLIOutputFormats:
    """Test different output formats."""
    
    def test_csv_output(self, runner, temp_parquet_file):
        """Test CSV output format."""
        result = runner.invoke(cli, [
            '--format', 'csv', 'head', temp_parquet_file, '-n', '2'
        ])
        assert result.exit_code == 0
        assert 'id,name,value,category,active' in result.output
        assert '1,Alice,10.5,A,True' in result.output
    
    def test_json_output(self, runner, temp_parquet_file):
        """Test JSON output format."""
        result = runner.invoke(cli, [
            '--format', 'json', 'head', temp_parquet_file, '-n', '1'
        ])
        assert result.exit_code == 0
        # Should be valid JSON
        import json
        json.loads(result.output)  # Will raise exception if invalid
    
    def test_quiet_mode(self, runner, temp_parquet_file):
        """Test quiet mode."""
        result = runner.invoke(cli, ['--quiet', 'count', temp_parquet_file])
        assert result.exit_code == 0
        # In quiet mode, should just have the number
        assert result.output.strip() == '5'
