"""
Main CLI entry point for ParQL.

This module provides the command-line interface using Click.
"""

import sys
import os
from typing import Optional, List, Dict, Any

import click
from rich.console import Console

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext
from parql.utils.output import OutputFormatter
from parql.utils.exceptions import ParQLError
from parql.commands.advanced import register_advanced_commands
from parql.commands.utilities import register_utility_commands
from parql.commands.system import register_system_commands


# Global context and formatter
console = Console()


@click.group(invoke_without_command=True)
@click.option('--threads', type=int, help='Number of threads to use')
@click.option('--memory-limit', help='Memory limit (e.g., 4GB)')
@click.option('--format', 'output_format', 
              type=click.Choice(['table', 'csv', 'tsv', 'json', 'ndjson', 'markdown']),
              default='table', help='Output format')
@click.option('--verbose', is_flag=True, help='Verbose output')
@click.option('--quiet', is_flag=True, help='Quiet mode')
@click.option('--max-width', type=int, help='Maximum output width')
@click.pass_context
def cli(ctx, threads, memory_limit, output_format, verbose, quiet, max_width):
    """ParQL - Query and manipulate Parquet datasets from the command line."""
    
    # Create context with CLI options
    context = ParQLContext(
        threads=threads,
        memory_limit=memory_limit,
        output_format=output_format,
        verbose=verbose,
        quiet=quiet,
        max_width=max_width
    )
    
    # Store context in Click context
    ctx.ensure_object(dict)
    ctx.obj['context'] = context
    ctx.obj['engine'] = ParQLEngine(context)
    ctx.obj['formatter'] = OutputFormatter(context)
    
    # If no command specified, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument('source')
@click.option('-n', '--rows', default=10, help='Number of rows to display')
@click.option('-c', '--columns', help='Comma-separated list of columns to select')
@click.option('-w', '--where', help='WHERE clause condition')
@click.option('-o', '--order-by', help='ORDER BY clause')
@click.pass_context
def head(ctx, source, rows, columns, where, order_by):
    """Display first N rows of Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        # Use select method for more control
        df = engine.select(
            source=source,
            columns=column_list,
            where=where,
            order_by=order_by,
            limit=rows
        )
        
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('-n', '--rows', default=10, help='Number of rows to display')
@click.option('-c', '--columns', help='Comma-separated list of columns to select')
@click.option('-w', '--where', help='WHERE clause condition')
@click.option('-o', '--order-by', help='ORDER BY clause')
@click.pass_context
def tail(ctx, source, rows, columns, where, order_by):
    """Display last N rows of Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        df = engine.tail(source, rows)
        
        # Apply additional filtering if specified
        if column_list or where or order_by:
            table_name = engine.load_source(source)
            query = f"SELECT "
            
            if column_list:
                query += ", ".join(column_list)
            else:
                query += "*"
            
            query += f" FROM {table_name}"
            
            if where:
                query += f" WHERE {where}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            # Get total count for tail calculation
            count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
            if where:
                count_query += f" WHERE {where}"
            
            total_rows = engine.execute_sql(count_query).iloc[0]['cnt']
            offset = max(0, total_rows - rows)
            query += f" OFFSET {offset}"
            
            df = engine.execute_sql(query)
        
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.pass_context
def schema(ctx, source):
    """Display schema information for Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        df = engine.schema(source)
        formatter.print_schema(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('-c', '--columns', help='Comma-separated list of columns to select')
@click.option('-w', '--where', help='WHERE clause condition')
@click.option('-o', '--order-by', help='ORDER BY clause')
@click.option('-l', '--limit', type=int, help='Limit number of rows')
@click.option('--distinct', is_flag=True, help='Return distinct rows')
@click.pass_context
def select(ctx, source, columns, where, order_by, limit, distinct):
    """Select and filter data from Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        if distinct:
            df = engine.distinct(source, column_list)
        else:
            df = engine.select(
                source=source,
                columns=column_list,
                where=where,
                order_by=order_by,
                limit=limit
            )
        
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('-w', '--where', help='WHERE clause condition')
@click.option('-n', '--limit', type=int, help='Limit number of rows to count')
@click.pass_context
def count(ctx, source, where, limit):
    """Count rows in Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        row_count = engine.count(source, where)
        
        if not formatter.context.quiet:
            console.print(f"[bold green]{row_count:,}[/bold green] rows")
        else:
            print(row_count)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('-c', '--columns', help='Comma-separated list of columns for distinct operation')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def distinct(ctx, source, columns, limit):
    """Get distinct rows or values from Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        df = engine.distinct(source, column_list)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('-g', '--group-by', help='Comma-separated list of columns to group by')
@click.option('-a', '--aggregations', help='Aggregation expressions (e.g., count():rows,sum(amount):total)')
@click.option('-h', '--having', help='HAVING clause condition')
@click.option('-o', '--order-by', help='ORDER BY clause')
@click.option('-l', '--limit', type=int, help='Limit number of rows')
@click.pass_context
def agg(ctx, source, group_by, aggregations, having, order_by, limit):
    """Perform aggregation operations on Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse group by columns
        group_cols = None
        if group_by:
            group_cols = [col.strip() for col in group_by.split(',')]
        
        # Parse aggregations
        agg_dict = {}
        if aggregations:
            for agg_expr in aggregations.split(','):
                if ':' in agg_expr:
                    expr, alias = agg_expr.split(':', 1)
                    agg_dict[alias.strip()] = expr.strip()
                else:
                    agg_dict[agg_expr.strip()] = agg_expr.strip()
        
        df = engine.aggregate(source, group_cols, agg_dict)
        
        # Apply additional filtering/sorting if specified
        if having or order_by or limit:
            # Register the DataFrame as a table in DuckDB
            engine.conn.register('temp_agg_result', df)
            
            query = f"SELECT * FROM temp_agg_result"
            
            if having:
                query += f" WHERE {having}"  # HAVING is like WHERE for aggregated results
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = engine.execute_sql(query)
        
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('-p', '--param', 'params', multiple=True, 
              help='Parameters in format key=value (e.g., -p t=data.parquet)')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def sql(ctx, query, params, limit):
    """Execute custom SQL query on Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Load parameters as tables
        for param in params:
            if '=' not in param:
                formatter.print_error(f"Invalid parameter format: {param}. Use key=value")
                sys.exit(1)
            
            key, value = param.split('=', 1)
            engine.load_source(value.strip(), key.strip())
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('left_source')
@click.argument('right_source')
@click.option('--on', 'join_condition', required=True, help='Join condition')
@click.option('--how', default='inner', 
              type=click.Choice(['inner', 'left', 'right', 'full']),
              help='Join type')
@click.option('-c', '--columns', help='Comma-separated list of columns to select from result')
@click.option('-l', '--limit', type=int, help='Limit number of rows')
@click.option('-n', '--rows', type=int, help='Limit number of rows to return')
@click.pass_context
def join(ctx, left_source, right_source, join_condition, how, columns, limit, rows):
    """Join two Parquet datasets."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Load tables with aliases
        left_table = engine.load_source(left_source, "left_tbl")
        right_table = engine.load_source(right_source, "right_tbl")
        
        join_type = how.upper()
        
        # Handle simple column name joins by prefixing with table names
        if ' = ' not in join_condition and ' ON ' not in join_condition.upper() and '.' not in join_condition:
            # Simple column name like "user_id"
            on_condition = f"left_tbl.{join_condition} = right_tbl.{join_condition}"
        else:
            # Complex join condition, replace table references with aliases
            on_condition = join_condition.replace(f"{left_source.split('/')[-1].replace('.parquet', '')}.", "left_tbl.").replace(f"{right_source.split('/')[-1].replace('.parquet', '')}.", "right_tbl.")
        
        # Build the join query
        query = f"""
        SELECT """
        
        if columns:
            # Handle column selection with table prefixes
            column_list = []
            for col in columns.split(','):
                col = col.strip()
                if '.' in col:
                    # Column has table prefix, map to aliases
                    table_name, column_name = col.split('.', 1)
                    if table_name in [left_source.split('/')[-1].replace('.parquet', ''), 'left_tbl']:
                        column_list.append(f"left_tbl.{column_name}")
                    elif table_name in [right_source.split('/')[-1].replace('.parquet', ''), 'right_tbl']:
                        column_list.append(f"right_tbl.{column_name}")
                    else:
                        column_list.append(col)  # Keep as is if unknown table
                else:
                    # No table prefix, add to both tables if ambiguous
                    column_list.append(col)
            query += ", ".join(column_list)
        else:
            query += "*"
        
        query += f"""
        FROM {left_table} left_tbl
        {join_type} JOIN {right_table} right_tbl ON {on_condition}
        """
        
        # Use rows parameter if provided, otherwise use limit
        final_limit = rows if rows is not None else limit
        if final_limit:
            query += f" LIMIT {final_limit}"
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('source')
@click.option('--fraction', type=float, help='Fraction of rows to sample (0.0-1.0)')
@click.option('--rows', type=int, help='Number of rows to sample')
@click.option('--seed', type=int, help='Random seed for reproducible sampling')
@click.option('-n', '--limit', type=int, help='Limit number of rows to return')
@click.pass_context
def sample(ctx, source, fraction, rows, seed, limit):
    """Sample rows from Parquet file(s)."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        
        if not fraction and not rows:
            formatter.print_error("Must specify either --fraction or --rows")
            sys.exit(1)
        
        if fraction and rows:
            formatter.print_error("Cannot specify both --fraction and --rows")
            sys.exit(1)
        
        query = f"SELECT * FROM {table_name}"
        
        if fraction:
            query += f" USING SAMPLE {fraction * 100}%"
        elif rows:
            # Use TABLESAMPLE for row-based sampling
            query = f"SELECT * FROM (SELECT * FROM {table_name} ORDER BY RANDOM()) LIMIT {rows}"
        
        if seed:
            # Set random seed
            engine.conn.execute(f"SELECT setseed({seed / 2147483647.0});")  # Normalize seed to 0-1
        
        df = engine.execute_sql(query)
        formatter.print_dataframe(df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument('input_source')
@click.argument('output_path')
@click.option('--format', 'output_format',
              type=click.Choice(['parquet', 'csv', 'tsv', 'json', 'ndjson']),
              default='parquet', help='Output format')
@click.option('--mode', type=click.Choice(['overwrite', 'append']),
              default='overwrite', help='Write mode')
@click.option('-c', '--columns', help='Comma-separated list of columns to include')
@click.option('-w', '--where', help='WHERE clause condition')
@click.option('--compression', help='Compression type (for Parquet: snappy, gzip, lz4, zstd)')
@click.option('--dry-run', is_flag=True, help='Show what would be written without actually writing')
@click.option('-n', '--limit', type=int, help='Limit number of rows to write')
@click.pass_context
def write(ctx, input_source, output_path, output_format, mode, columns, where, compression, dry_run, limit):
    """Write query results to file."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        # Get the data to write
        df = engine.select(
            source=input_source,
            columns=column_list,
            where=where,
            limit=limit
        )
        
        if dry_run:
            formatter.print_info(f"Would write {len(df):,} rows to {output_path}")
            formatter.print_info(f"Columns: {list(df.columns)}")
            formatter.print_info(f"Format: {output_format}")
            return
        
        # Prepare write options
        write_options = {}
        if compression:
            write_options['compression'] = compression
        
        # Write the file
        engine.write(df, output_path, output_format, mode, **write_options)
        
        formatter.print_success(f"Written {len(df):,} rows to {output_path}")
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    # Register all command modules
    register_advanced_commands(cli)
    register_utility_commands(cli)
    register_system_commands(cli)
    
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
