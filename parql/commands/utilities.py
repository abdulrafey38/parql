"""
Utility commands for ParQL CLI - string manipulation, plotting, etc.

This module contains utility commands that enhance ParQL's functionality
with string operations, visualization, and other helpful tools.
"""

import sys
import re
import os
from typing import Optional, List, Dict, Any

import click
import pandas as pd

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext
from parql.utils.output import OutputFormatter
from parql.utils.exceptions import ParQLError


@click.command()
@click.argument('source')
@click.option('-c', '--column', required=True, help='Column to perform string operations on')
@click.option('--operation', type=click.Choice([
    'upper', 'lower', 'title', 'capitalize', 'strip', 'lstrip', 'rstrip',
    'length', 'split', 'extract', 'replace', 'contains', 'startswith', 'endswith'
]), required=True, help='String operation to perform')
@click.option('--pattern', help='Pattern for operations like split, extract, replace, contains')
@click.option('--replacement', help='Replacement string for replace operation')
@click.option('--separator', default=' ', help='Separator for split operation')
@click.option('--new-column', help='Name for the new column (default: column_operation)')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def str_ops(ctx, source, column, operation, pattern, replacement, separator, new_column, limit):
    """Perform string manipulation operations on text columns."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Determine the new column name
        if not new_column:
            new_column = f"{column}_{operation}"
        
        # Build the SQL expression based on operation
        if operation == 'upper':
            expr = f"UPPER({column})"
        elif operation == 'lower':
            expr = f"LOWER({column})"
        elif operation == 'title':
            expr = f"INITCAP({column})"
        elif operation == 'capitalize':
            expr = f"CONCAT(UPPER(SUBSTRING({column}, 1, 1)), LOWER(SUBSTRING({column}, 2)))"
        elif operation == 'strip':
            expr = f"TRIM({column})"
        elif operation == 'lstrip':
            expr = f"LTRIM({column})"
        elif operation == 'rstrip':
            expr = f"RTRIM({column})"
        elif operation == 'length':
            expr = f"LENGTH({column})"
        elif operation == 'split':
            if not pattern:
                pattern = separator
            expr = f"STRING_SPLIT({column}, '{pattern}')"
        elif operation == 'extract':
            if not pattern:
                formatter.print_error("Pattern is required for extract operation")
                sys.exit(1)
            expr = f"REGEXP_EXTRACT({column}, '{pattern}', 1)"
        elif operation == 'replace':
            if not pattern or replacement is None:
                formatter.print_error("Both pattern and replacement are required for replace operation")
                sys.exit(1)
            expr = f"REPLACE({column}, '{pattern}', '{replacement}')"
        elif operation == 'contains':
            if not pattern:
                formatter.print_error("Pattern is required for contains operation")
                sys.exit(1)
            expr = f"CASE WHEN {column} LIKE '%{pattern}%' THEN true ELSE false END"
        elif operation == 'startswith':
            if not pattern:
                formatter.print_error("Pattern is required for startswith operation")
                sys.exit(1)
            expr = f"CASE WHEN {column} LIKE '{pattern}%' THEN true ELSE false END"
        elif operation == 'endswith':
            if not pattern:
                formatter.print_error("Pattern is required for endswith operation")
                sys.exit(1)
            expr = f"CASE WHEN {column} LIKE '%{pattern}' THEN true ELSE false END"
        else:
            formatter.print_error(f"Unknown operation: {operation}")
            sys.exit(1)
        
        # Execute the query
        query = f"SELECT *, {expr} AS {new_column} FROM {table_name}"
        
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
@click.option('-c', '--column', required=True, help='Column to plot')
@click.option('--chart-type', type=click.Choice(['hist', 'bar', 'line', 'scatter']),
              default='hist', help='Type of chart to create')
@click.option('--bins', type=int, default=20, help='Number of bins for histogram')
@click.option('--width', type=int, default=60, help='Width of the chart in characters')
@click.option('--height', type=int, default=20, help='Height of the chart in characters')
@click.option('-x', '--x-column', help='X-axis column for scatter plots')
@click.option('--limit', type=int, default=100, help='Limit number of data points')
@click.option('-n', '--rows', type=int, help='Limit number of rows to analyze')
@click.pass_context
def plot(ctx, source, column, chart_type, bins, width, height, x_column, limit, rows):
    """Create ASCII charts and plots."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        if chart_type == 'hist':
            # Create histogram using manual binning
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
            )
            SELECT 
                bin_number,
                frequency,
                REPEAT('█', CAST(frequency * {width} / (SELECT MAX(frequency) FROM histogram_data) AS INTEGER)) as bar
            FROM histogram_data
            """
            
        elif chart_type == 'bar':
            # Create bar chart for categorical data
            query = f"""
            WITH bar_data AS (
                SELECT 
                    {column},
                    COUNT(*) as frequency
                FROM {table_name}
                WHERE {column} IS NOT NULL
                GROUP BY {column}
                ORDER BY frequency DESC
                LIMIT {limit}
            )
            SELECT 
                {column},
                frequency,
                REPEAT('█', CAST(frequency * {width} / (SELECT MAX(frequency) FROM bar_data) AS INTEGER)) as bar
            FROM bar_data
            """
            
        elif chart_type == 'line':
            # Simple line chart (works best with time series or ordered data)
            query = f"""
            WITH line_data AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY {column}) as x_pos,
                    {column} as y_val
                FROM {table_name}
                WHERE {column} IS NOT NULL
                ORDER BY {column}
                LIMIT {limit}
            )
            SELECT 
                x_pos,
                y_val,
                REPEAT(' ', CAST((y_val - (SELECT MIN(y_val) FROM line_data)) * {width} / 
                    ((SELECT MAX(y_val) FROM line_data) - (SELECT MIN(y_val) FROM line_data)) AS INTEGER)) || '•' as line
            FROM line_data
            ORDER BY x_pos
            """
            
        elif chart_type == 'scatter':
            if not x_column:
                formatter.print_error("X-column is required for scatter plots")
                sys.exit(1)
            
            query = f"""
            WITH scatter_data AS (
                SELECT 
                    {x_column} as x_val,
                    {column} as y_val
                FROM {table_name}
                WHERE {x_column} IS NOT NULL AND {column} IS NOT NULL
                LIMIT {limit}
            ),
            normalized_data AS (
                SELECT 
                    x_val,
                    y_val,
                    CAST((x_val - (SELECT MIN(x_val) FROM scatter_data)) * {width} / 
                        ((SELECT MAX(x_val) FROM scatter_data) - (SELECT MIN(x_val) FROM scatter_data)) AS INTEGER) as x_pos,
                    CAST((y_val - (SELECT MIN(y_val) FROM scatter_data)) * {height} / 
                        ((SELECT MAX(y_val) FROM scatter_data) - (SELECT MIN(y_val) FROM scatter_data)) AS INTEGER) as y_pos
                FROM scatter_data
            )
            SELECT 
                x_val,
                y_val,
                x_pos,
                y_pos,
                REPEAT(' ', x_pos) || '•' as plot_line
            FROM normalized_data
            ORDER BY y_pos DESC, x_pos
            """
        
        df = engine.execute_sql(query)
        
        if chart_type in ['hist', 'bar']:
            formatter.print_info(f"{chart_type.title()} Chart for column '{column}':")
            formatter.print_dataframe(df)
        else:
            formatter.print_info(f"{chart_type.title()} Plot for column '{column}':")
            if chart_type == 'scatter':
                formatter.print_info(f"X-axis: {x_column}, Y-axis: {column}")
            
            # For line and scatter plots, we need to render the actual plot
            if chart_type == 'line':
                for _, row in df.iterrows():
                    print(f"{row['y_val']:8.2f} |{row['line']}")
            elif chart_type == 'scatter':
                # Group by y_pos and create scatter plot lines
                plot_lines = {}
                for _, row in df.iterrows():
                    y_pos = row['y_pos']
                    if y_pos not in plot_lines:
                        plot_lines[y_pos] = [' '] * (width + 1)
                    if row['x_pos'] < len(plot_lines[y_pos]):
                        plot_lines[y_pos][row['x_pos']] = '•'
                
                # Print the plot
                for y in sorted(plot_lines.keys(), reverse=True):
                    line = ''.join(plot_lines[y]).rstrip()
                    print(f"{y:3d} |{line}")
                
                # Print x-axis labels
                print("    " + "+" + "-" * width)
                print("     " + f"{df['x_val'].min():.1f}" + " " * (width - 10) + f"{df['x_val'].max():.1f}")
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('--pattern', required=True, help='Pattern to search for (supports SQL LIKE patterns)')
@click.option('-c', '--columns', help='Specific columns to search in (comma-separated)')
@click.option('--regex', is_flag=True, help='Use regex pattern matching instead of LIKE')
@click.option('--case-sensitive', is_flag=True, help='Case-sensitive search')
@click.option('--count-only', is_flag=True, help='Only return match counts')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def pattern(ctx, source, pattern, columns, regex, case_sensitive, count_only, limit):
    """Find patterns in data using LIKE or regex matching."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Get all string/text columns if none specified
        if columns:
            search_columns = [col.strip() for col in columns.split(',')]
        else:
            schema_df = engine.schema(source)
            search_columns = []
            for _, row in schema_df.iterrows():
                col_type = row.get('data_type', row.get('column_type', ''))
                if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                    search_columns.append(row['column_name'])
        
        if not search_columns:
            formatter.print_error("No text columns found to search in")
            sys.exit(1)
        
        # Build the search conditions
        conditions = []
        for col in search_columns:
            if regex:
                if case_sensitive:
                    condition = f"{col} ~ '{pattern}'"
                else:
                    # DuckDB doesn't support ~* for case-insensitive regex, use UPPER() instead
                    condition = f"UPPER({col}) ~ UPPER('{pattern}')"
            else:
                if case_sensitive:
                    condition = f"{col} LIKE '{pattern}'"
                else:
                    condition = f"UPPER({col}) LIKE UPPER('{pattern}')"
            conditions.append(condition)
        
        where_clause = " OR ".join(conditions)
        
        if count_only:
            # Just return counts per column
            count_queries = []
            for col in search_columns:
                if regex:
                    if case_sensitive:
                        condition = f"{col} ~ '{pattern}'"
                    else:
                        # DuckDB doesn't support ~* for case-insensitive regex, use UPPER() instead
                        condition = f"UPPER({col}) ~ UPPER('{pattern}')"
                else:
                    if case_sensitive:
                        condition = f"{col} LIKE '{pattern}'"
                    else:
                        condition = f"UPPER({col}) LIKE UPPER('{pattern}')"
                
                count_queries.append(f"SUM(CASE WHEN {condition} THEN 1 ELSE 0 END) AS {col}_matches")
            
            query = f"SELECT {', '.join(count_queries)} FROM {table_name}"
            df = engine.execute_sql(query)
            
            # Reshape for better display
            match_counts = []
            for col in search_columns:
                count = df.iloc[0][f"{col}_matches"]
                match_counts.append({'column': col, 'matches': count})
            
            result_df = pd.DataFrame(match_counts)
            formatter.print_dataframe(result_df)
        else:
            # Return all matching rows
            query = f"SELECT * FROM {table_name} WHERE {where_clause}"
            
            # Add LIMIT if specified
            if limit:
                query += f" LIMIT {limit}"
            
            df = engine.execute_sql(query)
            
            if df.empty:
                formatter.print_info(f"No matches found for pattern: {pattern}")
            else:
                formatter.print_info(f"Found {len(df)} rows matching pattern: {pattern}")
                formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('-c', '--columns', help='Columns to calculate percentiles for (comma-separated)')
@click.option('--percentiles', default='25,50,75,90,95,99', 
              help='Comma-separated list of percentiles to calculate')
@click.option('-n', '--limit', type=int, help='Limit number of rows to analyze')
@click.pass_context
def percentiles(ctx, source, columns, percentiles, limit):
    """Calculate detailed percentile statistics for numeric columns."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        # Parse percentiles
        pct_list = [float(p.strip()) / 100.0 for p in percentiles.split(',')]
        
        # Get numeric columns
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        else:
            schema_df = engine.schema(source)
            numeric_types = ['BIGINT', 'INTEGER', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC']
            column_list = []
            for _, row in schema_df.iterrows():
                col_type = row.get('data_type', row.get('column_type', ''))
                if any(nt in col_type.upper() for nt in numeric_types):
                    column_list.append(row['column_name'])
        
        if not column_list:
            formatter.print_error("No numeric columns found")
            sys.exit(1)
        
        results = []
        
        for col in column_list:
            # Build percentile query
            percentile_exprs = []
            for pct in pct_list:
                percentile_exprs.append(
                    f"PERCENTILE_CONT({pct}) WITHIN GROUP (ORDER BY {col}) AS p{int(pct * 100)}"
                )
            
            query = f"""
            SELECT 
                '{col}' AS column_name,
                COUNT({col}) AS count,
                COUNT(*) - COUNT({col}) AS null_count,
                MIN({col}) AS min_val,
                {', '.join(percentile_exprs)},
                MAX({col}) AS max_val,
                AVG({col}) AS mean_val,
                STDDEV({col}) AS std_val
            FROM {table_name}
            """
            
            result = engine.execute_sql(query)
            results.append(result.iloc[0])
        
        # Combine results
        combined_df = pd.DataFrame(results)
        
        # Round numeric columns
        numeric_cols = combined_df.select_dtypes(include=['float64', 'float32']).columns
        combined_df[numeric_cols] = combined_df[numeric_cols].round(3)
        
        formatter.print_dataframe(combined_df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# Register utility commands
def register_utility_commands(cli_group):
    """Register utility commands with the main CLI group."""
    cli_group.add_command(str_ops, name='str')
    cli_group.add_command(plot)
    cli_group.add_command(pattern)
    cli_group.add_command(percentiles)
