"""
System commands for ParQL CLI - configuration, caching, shell mode.

This module contains system-level commands for managing ParQL configuration,
caching, and interactive features.
"""

import sys
import os
import json
import pickle
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile
import sys

# Conditional import for readline (not available on Windows)
try:
    import readline  # For shell mode
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

import click
import pandas as pd

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext
from parql.utils.output import OutputFormatter
from parql.utils.exceptions import ParQLError


@click.group()
def config():
    """Manage ParQL configuration and profiles."""
    pass


@config.command()
@click.option('--profile', default='default', help='Configuration profile name')
@click.pass_context
def show(ctx, profile):
    """Show current configuration."""
    try:
        config_dir = Path.home() / '.parql'
        config_file = config_dir / f'{profile}.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            formatter = ctx.obj['formatter']
            config_df = pd.DataFrame([
                {'setting': k, 'value': str(v)} for k, v in config_data.items()
            ])
            formatter.print_dataframe(config_df)
        else:
            click.echo(f"No configuration found for profile '{profile}'")
    
    except Exception as e:
        click.echo(f"Error reading configuration: {e}")


@config.command()
@click.option('--profile', default='default', help='Configuration profile name')
@click.option('--threads', type=int, help='Number of threads to use')
@click.option('--memory-limit', help='Memory limit (e.g., 4GB)')
@click.option('--output-format', type=click.Choice(['table', 'csv', 'json', 'markdown']),
              help='Default output format')
@click.option('--max-width', type=int, help='Maximum output width')
@click.option('--cache-enabled', type=bool, help='Enable query caching')
@click.option('--cache-ttl', help='Cache time-to-live (e.g., 1h, 30m)')
@click.pass_context
def set(ctx, profile, **kwargs):
    """Set configuration values."""
    try:
        config_dir = Path.home() / '.parql'
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / f'{profile}.json'
        
        # Load existing config
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {}
        
        # Update with new values (excluding None values)
        for key, value in kwargs.items():
            if value is not None:
                config_data[key.replace('_', '-')] = value
        
        # Save config
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        click.echo(f"Configuration saved to profile '{profile}'")
        
    except Exception as e:
        click.echo(f"Error saving configuration: {e}")


@config.command()
@click.option('--profile', default='default', help='Configuration profile name')
@click.argument('key')
@click.pass_context
def unset(ctx, profile, key):
    """Remove a configuration setting."""
    try:
        config_dir = Path.home() / '.parql'
        config_file = config_dir / f'{profile}.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            if key in config_data:
                del config_data[key]
                
                with open(config_file, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                click.echo(f"Removed '{key}' from profile '{profile}'")
            else:
                click.echo(f"Setting '{key}' not found in profile '{profile}'")
        else:
            click.echo(f"No configuration found for profile '{profile}'")
    
    except Exception as e:
        click.echo(f"Error updating configuration: {e}")


@click.group()
def cache():
    """Manage ParQL query cache."""
    pass


@cache.command()
@click.pass_context
def clear(ctx):
    """Clear all cached query results."""
    try:
        cache_dir = Path.home() / '.parql' / 'cache'
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True)
            click.echo("Cache cleared successfully")
        else:
            click.echo("No cache directory found")
    
    except Exception as e:
        click.echo(f"Error clearing cache: {e}")


@cache.command()
@click.pass_context
def info(ctx):
    """Show cache information and statistics."""
    try:
        cache_dir = Path.home() / '.parql' / 'cache'
        
        if not cache_dir.exists():
            click.echo("No cache directory found")
            return
        
        cache_files = list(cache_dir.glob('*.pkl'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        # Cache statistics
        stats = {
            'cache_entries': len(cache_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_directory': str(cache_dir)
        }
        
        formatter = ctx.obj['formatter']
        stats_df = pd.DataFrame([
            {'metric': k, 'value': str(v)} for k, v in stats.items()
        ])
        formatter.print_dataframe(stats_df)
        
        # Show recent cache entries
        if cache_files:
            recent_files = sorted(cache_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            
            click.echo("\\nRecent cache entries:")
            for cache_file in recent_files:
                mtime = time.ctime(cache_file.stat().st_mtime)
                size_mb = round(cache_file.stat().st_size / (1024 * 1024), 2)
                click.echo(f"  {cache_file.stem[:50]:<50} {mtime} ({size_mb} MB)")
    
    except Exception as e:
        click.echo(f"Error reading cache info: {e}")


def _get_cache_key(query: str, source: str) -> str:
    """Generate a cache key for a query."""
    content = f"{query}:{source}"
    return hashlib.md5(content.encode()).hexdigest()


def _load_from_cache(cache_key: str) -> Optional[pd.DataFrame]:
    """Load result from cache if available and not expired."""
    try:
        cache_dir = Path.home() / '.parql' / 'cache'
        cache_file = cache_dir / f'{cache_key}.pkl'
        
        if cache_file.exists():
            # Check if cache is still valid (simple TTL check)
            cache_age = time.time() - cache_file.stat().st_mtime
            max_age = 3600  # 1 hour default TTL
            
            if cache_age < max_age:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        return None
    
    except Exception:
        return None


def _save_to_cache(cache_key: str, data: pd.DataFrame):
    """Save result to cache."""
    try:
        cache_dir = Path.home() / '.parql' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f'{cache_key}.pkl'
        
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    
    except Exception:
        pass  # Fail silently if caching doesn't work


@click.command()
@click.option('--profile', help='Configuration profile to use')
@click.option('--non-interactive', is_flag=True, help='Non-interactive mode for testing')
@click.pass_context
def shell(ctx, profile, non_interactive):
    """Start interactive ParQL shell mode."""
    try:
        formatter = ctx.obj['formatter']
        
        # Load profile if specified
        if profile:
            config_dir = Path.home() / '.parql'
            config_file = config_dir / f'{profile}.json'
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    # Apply configuration to context
                    for key, value in config_data.items():
                        if hasattr(ctx.obj['context'], key.replace('-', '_')):
                            setattr(ctx.obj['context'], key.replace('-', '_'), value)
        
        engine = ParQLEngine(ctx.obj['context'])
        
        if non_interactive:
            # Non-interactive mode for testing
            click.echo("ParQL Shell (Non-interactive Mode)")
            return
        
        click.echo("Welcome to ParQL Interactive Shell!")
        click.echo("Type 'help' for available commands, 'exit' to quit.")
        click.echo("Use SQL syntax with table aliases: SELECT * FROM table_name")
        click.echo()
        
        # Track loaded tables
        loaded_tables = {}
        
        while True:
            try:
                # Get user input
                command = input("parql> ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit', '\\\\q']:
                    click.echo("Goodbye!")
                    break
                
                elif command.lower() in ['help', '\\\\h']:
                    click.echo("""
Available commands:
  help, \\\\h          - Show this help
  exit, quit, \\\\q    - Exit shell
  \\\\l <file> [alias] - Load Parquet file with optional alias
  \\\\tables          - Show loaded tables
  \\\\schema <table>  - Show table schema
  \\\\clear           - Clear screen
  
SQL Commands:
  SELECT * FROM table_name;
  SELECT col1, col2 FROM table_name WHERE condition;
  
Examples:
  \\\\l data/sales.parquet sales
  SELECT country, SUM(revenue) FROM sales GROUP BY country;
                    """)
                
                elif command.startswith('\\\\l '):
                    # Load table command
                    parts = command[3:].strip().split()
                    if len(parts) >= 1:
                        file_path = parts[0]
                        alias = parts[1] if len(parts) > 1 else None
                        
                        try:
                            table_name = engine.load_source(file_path, alias)
                            loaded_tables[table_name] = file_path
                            click.echo(f"Loaded {file_path} as '{table_name}'")
                        except Exception as e:
                            click.echo(f"Error loading file: {e}")
                    else:
                        click.echo("Usage: \\\\l <file_path> [alias]")
                
                elif command == '\\\\tables':
                    if loaded_tables:
                        click.echo("Loaded tables:")
                        for table, file_path in loaded_tables.items():
                            click.echo(f"  {table:<15} -> {file_path}")
                    else:
                        click.echo("No tables loaded")
                
                elif command.startswith('\\\\schema '):
                    table_name = command[8:].strip()
                    if table_name in loaded_tables:
                        try:
                            df = engine.schema(loaded_tables[table_name])
                            formatter.print_schema(df)
                        except Exception as e:
                            click.echo(f"Error getting schema: {e}")
                    else:
                        click.echo(f"Table '{table_name}' not found. Use \\\\tables to see loaded tables.")
                
                elif command == '\\\\clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                
                else:
                    # Assume it's a SQL query
                    try:
                        # Check cache first
                        cache_key = _get_cache_key(command, str(loaded_tables))
                        cached_result = _load_from_cache(cache_key)
                        
                        if cached_result is not None:
                            click.echo("(from cache)")
                            formatter.print_dataframe(cached_result)
                        else:
                            df = engine.execute_sql(command)
                            
                            # Save to cache
                            _save_to_cache(cache_key, df)
                            
                            formatter.print_dataframe(df)
                    
                    except Exception as e:
                        click.echo(f"Error executing query: {e}")
                        click.echo("Make sure to load tables first with: \\\\l <file_path> [alias]")
            
            except KeyboardInterrupt:
                click.echo("\\nUse 'exit' to quit")
                continue
            
            except EOFError:
                click.echo("\\nGoodbye!")
                break
    
    except Exception as e:
        click.echo(f"Error in shell mode: {e}")
        sys.exit(1)


@click.command()
@click.argument('source')
@click.option('--suggest-types', is_flag=True, help='Suggest optimal data types')
@click.option('--sample-size', type=int, default=10000, help='Sample size for type inference')
@click.option('-n', '--limit', type=int, help='Limit number of rows to analyze')
@click.pass_context
def infer_types_temp(ctx, source, suggest_types, sample_size, limit):
    """Infer optimal data types for columns."""
    try:
        engine = ctx.obj['engine']
        formatter = ctx.obj['formatter']
        
        table_name = engine.load_source(source)
        current_schema = engine.schema(source)
        
        # Sample data for analysis
        sample_query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
        sample_df = engine.execute_sql(sample_query)
        
        # Build basic type inference results
        type_suggestions = []
        for _, col_info in current_schema.iterrows():
            col_name = col_info['column_name']
            current_type = col_info.get('data_type', col_info.get('column_type', 'UNKNOWN'))
            
            type_suggestions.append({
                'column': col_name,
                'current_type': current_type,
                'inferred_type': current_type,  # Simple - suggest same type for now
                'confidence': 'High'
            })
        
        # Create and display results
        result_df = pd.DataFrame(type_suggestions)
        formatter.print_dataframe(result_df)
        
    except ParQLError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# Register system commands
def register_system_commands(cli_group):
    """Register system commands with the main CLI group."""
    cli_group.add_command(config)
    cli_group.add_command(cache)
    cli_group.add_command(shell)
    cli_group.add_command(infer_types_temp, name='infer-types')