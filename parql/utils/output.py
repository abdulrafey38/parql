"""
Output formatting utilities for ParQL.

This module handles formatting and displaying query results in various formats.
"""

import sys
import json
from typing import Any, Optional, Dict, List
from io import StringIO

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from tabulate import tabulate

from parql.core.context import ParQLContext


class OutputFormatter:
    """Handles formatting and output of query results."""
    
    def __init__(self, context: Optional[ParQLContext] = None):
        """Initialize output formatter.
        
        Args:
            context: ParQL context with output settings
        """
        self.context = context or ParQLContext()
        self.console = Console(
            width=self.context.max_width,
            force_terminal=not self.context.quiet
        )
    
    def format_dataframe(self, df: pd.DataFrame, format_type: str = None) -> str:
        """Format DataFrame for output.
        
        Args:
            df: DataFrame to format
            format_type: Output format (table, csv, json, etc.)
            
        Returns:
            Formatted string
        """
        format_type = format_type or self.context.output_format
        
        if format_type == "table":
            return self._format_table(df)
        elif format_type == "csv":
            return self._format_csv(df)
        elif format_type == "tsv":
            return self._format_tsv(df)
        elif format_type == "json":
            return self._format_json(df)
        elif format_type == "ndjson":
            return self._format_ndjson(df)
        elif format_type == "markdown":
            return self._format_markdown(df)
        else:
            # Default to table format
            return self._format_table(df)
    
    def _format_table(self, df: pd.DataFrame) -> str:
        """Format DataFrame as a rich table."""
        if df.empty:
            return "No data to display."
        
        # In quiet mode, use simpler tabulate format
        if self.context.quiet:
            return tabulate(df, headers='keys', tablefmt='simple', showindex=False)
        
        # Create rich table
        table = Table(show_header=True, header_style="bold magenta")
        
        # Add columns
        for col in df.columns:
            table.add_column(str(col))
        
        # Add rows (limit for display)
        max_rows = 1000  # Reasonable limit for terminal display
        display_df = df.head(max_rows) if len(df) > max_rows else df
        
        for _, row in display_df.iterrows():
            row_values = []
            for val in row:
                # Handle different data types for display
                if pd.isna(val):
                    row_values.append("[dim]null[/dim]")
                elif isinstance(val, (int, float)):
                    row_values.append(str(val))
                else:
                    # Truncate long strings if needed
                    str_val = str(val)
                    if self.context.truncate_columns and len(str_val) > 50:
                        str_val = str_val[:47] + "..."
                    row_values.append(str_val)
            
            table.add_row(*row_values)
        
        # Capture table output
        with StringIO() as output:
            console = Console(file=output, width=self.context.max_width)
            console.print(table)
            result = output.getvalue()
        
        # Add summary if truncated
        if len(df) > max_rows:
            result += f"\n... showing {max_rows} of {len(df)} rows"
        
        return result
    
    def _format_csv(self, df: pd.DataFrame) -> str:
        """Format DataFrame as CSV."""
        return df.to_csv(index=False)
    
    def _format_tsv(self, df: pd.DataFrame) -> str:
        """Format DataFrame as TSV."""
        return df.to_csv(index=False, sep='\t')
    
    def _format_json(self, df: pd.DataFrame) -> str:
        """Format DataFrame as JSON."""
        return df.to_json(orient='records', indent=2)
    
    def _format_ndjson(self, df: pd.DataFrame) -> str:
        """Format DataFrame as newline-delimited JSON."""
        return df.to_json(orient='records', lines=True)
    
    def _format_markdown(self, df: pd.DataFrame) -> str:
        """Format DataFrame as Markdown table."""
        return tabulate(df, headers='keys', tablefmt='pipe', showindex=False)
    
    def print_dataframe(self, df: pd.DataFrame, format_type: str = None):
        """Print DataFrame to stdout.
        
        Args:
            df: DataFrame to print
            format_type: Output format
        """
        output = self.format_dataframe(df, format_type)
        
        if format_type == "table" and not self.context.quiet:
            # Use rich console for table output when not in quiet mode
            self.console.print(output)
        else:
            # Use regular print for other formats or quiet mode
            print(output)
    
    def print_schema(self, schema_df: pd.DataFrame):
        """Print schema information in a formatted way.
        
        Args:
            schema_df: DataFrame with schema information
        """
        if self.context.quiet:
            # In quiet mode, just print the raw data
            self.print_dataframe(schema_df, "csv")
            return
        
        table = Table(title="Schema Information", show_header=True, header_style="bold blue")
        table.add_column("Column", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Nullable", style="green")
        
        for _, row in schema_df.iterrows():
            nullable_text = "✓" if row.get('nullable', True) else "✗"
            table.add_row(
                str(row['column_name']),
                str(row['data_type']),
                nullable_text
            )
        
        self.console.print(table)
    
    def print_metadata(self, metadata: Dict[str, Any]):
        """Print file metadata in a formatted way.
        
        Args:
            metadata: Dictionary with metadata information
        """
        if self.context.quiet:
            return
        
        table = Table(title="File Metadata", show_header=True, header_style="bold blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in metadata.items():
            table.add_row(str(key).replace('_', ' ').title(), str(value))
        
        self.console.print(table)
    
    def print_statistics(self, stats_df: pd.DataFrame):
        """Print column statistics in a formatted way.
        
        Args:
            stats_df: DataFrame with statistics information
        """
        if self.context.quiet:
            return
        
        table = Table(title="Column Statistics", show_header=True, header_style="bold blue")
        
        # Add columns dynamically based on DataFrame columns
        for col in stats_df.columns:
            table.add_column(str(col), style="white")
        
        for _, row in stats_df.iterrows():
            table.add_row(*[str(val) for val in row])
        
        self.console.print(table)
    
    def print_error(self, message: str):
        """Print error message.
        
        Args:
            message: Error message to print
        """
        if not self.context.quiet:
            self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def print_warning(self, message: str):
        """Print warning message.
        
        Args:
            message: Warning message to print
        """
        if not self.context.quiet:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    
    def print_info(self, message: str):
        """Print info message.
        
        Args:
            message: Info message to print
        """
        if self.context.verbose and not self.context.quiet:
            self.console.print(f"[bold blue]Info:[/bold blue] {message}")
    
    def print_success(self, message: str):
        """Print success message.
        
        Args:
            message: Success message to print
        """
        if not self.context.quiet:
            self.console.print(f"[bold green]Success:[/bold green] {message}")


def create_progress_bar(description: str = "Processing..."):
    """Create a progress bar for long-running operations.
    
    Args:
        description: Description text for the progress bar
        
    Returns:
        Rich Progress instance
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=Console()
    )
