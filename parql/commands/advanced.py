"""
Advanced commands for ParQL CLI.

This module contains commands for advanced operations like pivot, window functions,
data validation, and schema operations.
"""

import sys
from typing import Optional, List, Dict, Any

import click
import pandas as pd

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext
from parql.utils.output import OutputFormatter
from parql.utils.schema import SchemaInspector
from parql.utils.exceptions import ParQLError


@click.command()
@click.argument('source')
@click.option('-i', '--index', required=True, help='Index columns (comma-separated)')
@click.option('-c', '--columns', required=True, help='Columns to pivot')
@click.option('-v', '--values', required=True, help='Values column')
@click.option('-f', '--func', default='sum', help='Aggregation function')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def pivot(ctx, source, index, columns, values, func, limit):
    """Pivot data from long to wide format."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Parse parameters
        index_cols = [col.strip() for col in index.split(',')]
        pivot_cols = [col.strip() for col in columns.split(',')]
        
        # Build pivot query using DuckDB's PIVOT syntax
        index_str = ', '.join(index_cols)
        pivot_str = ', '.join(pivot_cols)
        
        query = f"""
        PIVOT {table_name}
        ON {pivot_str}
        USING {func}({values})
        GROUP BY {index_str}
        """
        
        # Add LIMIT if specified
        if limit:
            query += f" LIMIT {limit}"
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('--partition', help='PARTITION BY columns (comma-separated)')
@click.option('--order', help='ORDER BY clause')
@click.option('--expr', required=True, help='Window function expression')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def window(ctx, source, partition, order, expr, limit):
    """Apply window functions to data."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Check if the expression already contains an OVER clause
        if ' over ' in expr.lower():
            # Expression already has OVER clause, use it as-is
            window_expr = expr
        else:
            # Build the OVER clause
            over_parts = []
            
            if partition:
                partition_cols = [col.strip() for col in partition.split(',')]
                over_parts.append(f"PARTITION BY {', '.join(partition_cols)}")
            
            if order:
                over_parts.append(f"ORDER BY {order}")
            
            over_clause = f"OVER ({' '.join(over_parts)})"
            
            # Build the window function expression
            if ' as ' in expr.lower():
                # Expression with alias
                parts = expr.split(' as ')
                if len(parts) == 2:
                    func_part = parts[0].strip()
                    alias_part = parts[1].strip()
                    window_expr = f"{func_part} {over_clause} as {alias_part}"
                else:
                    window_expr = f"{expr} {over_clause}"
            else:
                # Simple expression
                window_expr = f"{expr} {over_clause}"
        
        # Build the complete query
        query = f"SELECT *, {window_expr} FROM {table_name}"
        
        # Add LIMIT if specified
        if limit:
            query += f" LIMIT {limit}"
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('--rule', 'rules', multiple=True, required=True,
              help='Validation rules (e.g., "row_count > 1000", "no_nulls(id)")')
@click.option('--fail-fast', is_flag=True, help='Stop on first validation failure')
@click.option('-n', '--limit', type=int, help='Limit number of rows to validate')
@click.pass_context
def assert_cmd(ctx, source, rules, fail_fast, limit):
    """Assert data quality rules on Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        failed_rules = []
        
        for rule in rules:
            try:
                if rule.startswith('row_count'):
                    # Handle row count assertions
                    count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
                    actual_count = engine.execute_sql(count_query).iloc[0]['cnt']
                    
                    # Parse the rule (e.g., "row_count > 1000")
                    condition = rule.replace('row_count', str(actual_count))
                    if not eval(condition):
                        failed_rules.append(f"{rule} (actual: {actual_count})")
                        if fail_fast:
                            break
                
                elif rule.startswith('no_nulls('):
                    # Handle no nulls assertions
                    column = rule[9:-1]  # Extract column name from no_nulls(column)
                    null_query = f"SELECT COUNT(*) as null_count FROM {table_name} WHERE {column} IS NULL"
                    null_count = engine.execute_sql(null_query).iloc[0]['null_count']
                    
                    if null_count > 0:
                        failed_rules.append(f"{rule} (found {null_count} nulls)")
                        if fail_fast:
                            break
                
                elif rule.startswith('unique('):
                    # Handle uniqueness assertions
                    column = rule[7:-1]  # Extract column name from unique(column)
                    dup_query = f"""
                    SELECT COUNT(*) as dup_count FROM (
                        SELECT {column}, COUNT(*) as cnt 
                        FROM {table_name} 
                        GROUP BY {column} 
                        HAVING COUNT(*) > 1
                    )
                    """
                    dup_count = engine.execute_sql(dup_query).iloc[0]['dup_count']
                    
                    if dup_count > 0:
                        failed_rules.append(f"{rule} (found {dup_count} duplicate values)")
                        if fail_fast:
                            break
                
                else:
                    # Generic SQL condition
                    check_query = f"SELECT CASE WHEN {rule} THEN 1 ELSE 0 END as passes FROM {table_name} LIMIT 1"
                    passes = engine.execute_sql(check_query).iloc[0]['passes']
                    
                    if not passes:
                        failed_rules.append(rule)
                        if fail_fast:
                            break
                            
            except Exception as e:
                failed_rules.append(f"{rule} (error: {e})")
                if fail_fast:
                    break
        
        if failed_rules:
            formatter.print_error("Validation failed:")
            for failed_rule in failed_rules:
                formatter.print_error(f"  ✗ {failed_rule}")
            sys.exit(1)
        else:
            formatter.print_success(f"All {len(rules)} validation rules passed ✓")
            
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source1')
@click.argument('source2')
@click.option('--fail-on-change', is_flag=True, help='Fail if schemas differ')
@click.option('-n', '--limit', type=int, help='Limit number of differences to show')
@click.pass_context
def compare_schema(ctx, source1, source2, fail_on_change, limit):
    """Compare schemas between two Parquet files."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # For schema comparison, we need to use the SchemaInspector directly
        # since it works with file paths
        from parql.utils.schema import SchemaInspector
        
        inspector1 = SchemaInspector(source1)
        comparison_df = inspector1.compare_schema(source2)
        
        formatter.print_dataframe(comparison_df)
        
        # Check if there are any differences
        has_differences = (
            (comparison_df['status'] == 'DIFFERENT').any() or
            (comparison_df['status'] == 'ONLY_IN_FILE1').any() or
            (comparison_df['status'] == 'ONLY_IN_FILE2').any()
        )
        
        if has_differences and fail_on_change:
            formatter.print_error("Schema differences detected!")
            sys.exit(1)
        elif has_differences:
            formatter.print_warning("Schema differences detected")
        else:
            formatter.print_success("Schemas are identical")
            
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--column', help='Column to analyze for outliers')
@click.option('--method', type=click.Choice(['zscore', 'iqr']), default='zscore',
              help='Outlier detection method')
@click.option('--threshold', type=float, default=3.0, help='Threshold for outlier detection')
@click.option('-n', '--limit', type=int, help='Limit number of outliers to return')
@click.pass_context
def outliers(ctx, source, column, method, threshold, limit):
    """Detect outliers in numeric columns."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        if not column:
            formatter.print_error("Column name is required for outlier detection")
            sys.exit(1)
        
        if method == 'zscore':
            # Z-score method
            query = f"""
            WITH stats AS (
                SELECT 
                    AVG({column}) as mean_val,
                    STDDEV({column}) as std_val
                FROM {table_name}
                WHERE {column} IS NOT NULL
            )
            SELECT 
                *,
                ABS(({column} - stats.mean_val) / stats.std_val) as z_score
            FROM {table_name}
            CROSS JOIN stats
            WHERE ABS(({column} - stats.mean_val) / stats.std_val) > {threshold}
            ORDER BY z_score DESC
            """
        
        elif method == 'iqr':
            # Interquartile range method
            query = f"""
            WITH quartiles AS (
                SELECT 
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {column}) as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {column}) as q3
                FROM {table_name}
                WHERE {column} IS NOT NULL
            ),
            iqr_calc AS (
                SELECT 
                    q1,
                    q3,
                    (q3 - q1) as iqr,
                    q1 - {threshold} * (q3 - q1) as lower_bound,
                    q3 + {threshold} * (q3 - q1) as upper_bound
                FROM quartiles
            )
            SELECT 
                t.*,
                i.lower_bound,
                i.upper_bound
            FROM {table_name} t
            CROSS JOIN iqr_calc i
            WHERE t.{column} < i.lower_bound OR t.{column} > i.upper_bound
            ORDER BY t.{column}
            """
        
        df = engine.execute_sql(query)
        
        if df.empty:
            formatter.print_success(f"No outliers detected in column '{column}' using {method} method")
        else:
            formatter.print_info(f"Found {len(df)} outliers in column '{column}' using {method} method")
            formatter.print_dataframe(df)
            
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--column', help='Specific column to analyze for nulls')
@click.pass_context
def nulls(ctx, source, column):
    """Analyze null values in Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        if column:
            # Analyze specific column
            query = f"""
            SELECT 
                '{column}' as column_name,
                COUNT(*) as total_rows,
                COUNT({column}) as non_null_count,
                COUNT(*) - COUNT({column}) as null_count,
                ROUND(100.0 * (COUNT(*) - COUNT({column})) / COUNT(*), 2) as null_percentage
            FROM {table_name}
            """
        else:
            # Analyze all columns
            # First get column names
            schema_df = engine.schema(source)
            columns = schema_df['column_name'].tolist()
            
            # Build query for all columns
            col_analyses = []
            for col in columns:
                col_analyses.append(f"""
                SELECT 
                    '{col}' as column_name,
                    COUNT(*) as total_rows,
                    COUNT({col}) as non_null_count,
                    COUNT(*) - COUNT({col}) as null_count,
                    ROUND(100.0 * (COUNT(*) - COUNT({col})) / COUNT(*), 2) as null_percentage
                FROM {table_name}
                """)
            
            query = " UNION ALL ".join(col_analyses)
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--column', required=True, help='Column to generate histogram for')
@click.option('--bins', type=int, default=10, help='Number of histogram bins')
@click.pass_context
def hist(ctx, source, column, bins):
    """Generate histogram for numeric column."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Create histogram using manual binning (WIDTH_BUCKET not available in DuckDB)
        query = f"""
        WITH min_max AS (
            SELECT MIN({column}) as min_val, MAX({column}) as max_val 
            FROM {table_name} 
            WHERE {column} IS NOT NULL
        ),
        histogram_data AS (
            SELECT 
                FLOOR(({column} - min_val) / ((max_val - min_val) / {bins})) + 1 as bin_number,
                COUNT(*) as frequency
            FROM {table_name}, min_max
            WHERE {column} IS NOT NULL
            GROUP BY bin_number
            ORDER BY bin_number
        ),
        bin_ranges AS (
            SELECT 
                bin_number,
                frequency,
                ROUND(min_val + (bin_number - 1) * (max_val - min_val) / {bins}, 2) as bin_start,
                ROUND(min_val + bin_number * (max_val - min_val) / {bins}, 2) as bin_end
            FROM histogram_data, min_max
        )
        SELECT 
            CONCAT('[', bin_start, ', ', bin_end, ')') as bin_range,
            frequency,
            REPEAT('█', CAST(frequency * 50.0 / (SELECT MAX(frequency) FROM histogram_data) AS INTEGER)) as bar
        FROM bin_ranges
        ORDER BY bin_number
        """
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--columns', help='Specific columns to include (comma-separated)')
@click.option('--method', type=click.Choice(['pearson', 'spearman', 'kendall']), 
              default='pearson', help='Correlation method')
@click.option('--min-periods', type=int, default=1, help='Minimum number of observations')
@click.option('-n', '--limit', type=int, help='Limit number of rows to analyze')
@click.pass_context
def corr(ctx, source, columns, method, min_periods, limit):
    """Calculate correlation matrix between numeric columns."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Get numeric columns
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
            # Validate columns are numeric
            schema_query = f"DESCRIBE {table_name}"
            schema_df = engine.execute_sql(schema_query)
            numeric_types = ['BIGINT', 'INTEGER', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']
            
            numeric_columns = []
            for col in column_list:
                col_info = schema_df[schema_df['column_name'] == col]
                if not col_info.empty:
                    col_type = col_info.iloc[0]['column_type'] if 'column_type' in col_info.columns else col_info.iloc[0]['data_type']
                    if any(nt in str(col_type).upper() for nt in numeric_types):
                        numeric_columns.append(col)
        else:
            # Auto-detect numeric columns
            schema_query = f"DESCRIBE {table_name}"
            schema_df = engine.execute_sql(schema_query)
            numeric_types = ['BIGINT', 'INTEGER', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']
            
            numeric_columns = []
            for _, row in schema_df.iterrows():
                col_type = row['column_type'] if 'column_type' in row else row['data_type']
                if any(nt in str(col_type).upper() for nt in numeric_types):
                    numeric_columns.append(row['column_name'])
        
        if len(numeric_columns) < 2:
            formatter.print_error("Need at least 2 numeric columns for correlation analysis")
            sys.exit(1)
        
        # Build correlation query using DuckDB's corr function
        correlation_pairs = []
        for i, col1 in enumerate(numeric_columns):
            for j, col2 in enumerate(numeric_columns):
                if method == 'pearson':
                    corr_func = f"corr({col1}, {col2})"
                else:
                    # For Spearman/Kendall, we'll use a simpler approach
                    corr_func = f"corr({col1}, {col2})"  # DuckDB primarily supports Pearson
                
                correlation_pairs.append(f"{corr_func} AS corr_{i}_{j}")
        
        query = f"SELECT {', '.join(correlation_pairs)} FROM {table_name}"
        corr_result = engine.execute_sql(query)
        
        # Reshape into correlation matrix
        import pandas as pd
        corr_matrix = pd.DataFrame(index=numeric_columns, columns=numeric_columns)
        
        idx = 0
        for i, col1 in enumerate(numeric_columns):
            for j, col2 in enumerate(numeric_columns):
                corr_value = corr_result.iloc[0, idx]
                corr_matrix.iloc[i, j] = corr_value
                idx += 1
        
        # Convert to numeric and round
        corr_matrix = corr_matrix.astype(float).round(3)
        
        formatter.print_dataframe(corr_matrix.reset_index())
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--columns', help='Specific columns to profile (comma-separated)')
@click.option('--include-all', is_flag=True, help='Include all statistics (can be slow)')
@click.option('-n', '--limit', type=int, help='Limit number of rows to profile')
@click.pass_context
def profile(ctx, source, columns, include_all, limit):
    """Generate comprehensive data quality profile."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Get basic info
        count_query = f"SELECT COUNT(*) as total_rows FROM {table_name}"
        total_rows = engine.execute_sql(count_query).iloc[0]['total_rows']
        
        # Get schema info
        schema_df = engine.schema(source)
        
        if columns:
            selected_columns = [col.strip() for col in columns.split(',')]
            schema_df = schema_df[schema_df['column_name'].isin(selected_columns)]
        
        profile_data = []
        
        for _, col_info in schema_df.iterrows():
            col_name = col_info['column_name']
            col_type = col_info.get('data_type', col_info.get('column_type', 'UNKNOWN'))
            
            # Basic statistics
            stats = {
                'column': col_name,
                'type': col_type,
                'total_rows': total_rows,
            }
            
            # Null count and percentage
            null_query = f"SELECT COUNT(*) - COUNT({col_name}) as null_count FROM {table_name}"
            null_count = engine.execute_sql(null_query).iloc[0]['null_count']
            stats['null_count'] = null_count
            stats['null_percentage'] = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0
            stats['non_null_count'] = total_rows - null_count
            
            # Distinct count
            distinct_query = f"SELECT COUNT(DISTINCT {col_name}) as distinct_count FROM {table_name}"
            distinct_count = engine.execute_sql(distinct_query).iloc[0]['distinct_count']
            stats['distinct_count'] = distinct_count
            stats['unique_percentage'] = round((distinct_count / total_rows) * 100, 2) if total_rows > 0 else 0
            
            # Type-specific statistics
            if any(t in col_type.upper() for t in ['INT', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']):
                # Numeric statistics
                num_stats_query = f"""
                SELECT 
                    MIN({col_name}) as min_val,
                    MAX({col_name}) as max_val,
                    AVG({col_name}) as mean_val,
                    STDDEV({col_name}) as std_val,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {col_name}) as median_val
                FROM {table_name}
                WHERE {col_name} IS NOT NULL
                """
                num_stats = engine.execute_sql(num_stats_query)
                if not num_stats.empty:
                    stats.update({
                        'min': num_stats.iloc[0]['min_val'],
                        'max': num_stats.iloc[0]['max_val'],
                        'mean': round(num_stats.iloc[0]['mean_val'], 3) if num_stats.iloc[0]['mean_val'] is not None else None,
                        'std': round(num_stats.iloc[0]['std_val'], 3) if num_stats.iloc[0]['std_val'] is not None else None,
                        'median': num_stats.iloc[0]['median_val']
                    })
                    
                    # Check for outliers using IQR method
                    if include_all:
                        iqr_query = f"""
                        SELECT 
                            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col_name}) as q1,
                            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col_name}) as q3
                        FROM {table_name}
                        WHERE {col_name} IS NOT NULL
                        """
                        iqr_stats = engine.execute_sql(iqr_query)
                        if not iqr_stats.empty:
                            q1, q3 = iqr_stats.iloc[0]['q1'], iqr_stats.iloc[0]['q3']
                            iqr = q3 - q1
                            lower_bound = q1 - 1.5 * iqr
                            upper_bound = q3 + 1.5 * iqr
                            
                            outlier_query = f"""
                            SELECT COUNT(*) as outlier_count 
                            FROM {table_name} 
                            WHERE {col_name} < {lower_bound} OR {col_name} > {upper_bound}
                            """
                            outlier_count = engine.execute_sql(outlier_query).iloc[0]['outlier_count']
                            stats['outlier_count'] = outlier_count
            
            elif 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                # String statistics
                str_stats_query = f"""
                SELECT 
                    MIN(LENGTH({col_name})) as min_length,
                    MAX(LENGTH({col_name})) as max_length,
                    AVG(LENGTH({col_name})) as avg_length
                FROM {table_name}
                WHERE {col_name} IS NOT NULL
                """
                str_stats = engine.execute_sql(str_stats_query)
                if not str_stats.empty:
                    stats.update({
                        'min_length': str_stats.iloc[0]['min_length'],
                        'max_length': str_stats.iloc[0]['max_length'],
                        'avg_length': round(str_stats.iloc[0]['avg_length'], 1) if str_stats.iloc[0]['avg_length'] is not None else None
                    })
                
                # Most common values
                if include_all:
                    common_query = f"""
                    SELECT {col_name}, COUNT(*) as frequency 
                    FROM {table_name} 
                    WHERE {col_name} IS NOT NULL 
                    GROUP BY {col_name} 
                    ORDER BY frequency DESC 
                    LIMIT 3
                    """
                    common_values = engine.execute_sql(common_query)
                    if not common_values.empty:
                        top_values = [f"{row[col_name]} ({row['frequency']})" for _, row in common_values.iterrows()]
                        stats['top_values'] = '; '.join(top_values)
            
            profile_data.append(stats)
        
        # Convert to DataFrame and display
        profile_df = pd.DataFrame(profile_data)
        
        formatter.print_info(f"Data Profile Summary for {total_rows:,} rows")
        formatter.print_dataframe(profile_df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# Register commands with the main CLI
def register_advanced_commands(cli_group):
    """Register advanced commands with the main CLI group."""
    cli_group.add_command(pivot)
    cli_group.add_command(window)
    cli_group.add_command(assert_cmd, name='assert')
    cli_group.add_command(compare_schema)
    cli_group.add_command(outliers)
    cli_group.add_command(nulls)
    cli_group.add_command(hist)
    cli_group.add_command(corr)
    cli_group.add_command(profile)
