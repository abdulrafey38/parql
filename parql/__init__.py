"""
ParQL - A command-line tool for querying and manipulating Parquet datasets.

ParQL is powered by DuckDB and provides pandas-like operations and SQL queries
directly from the command line. It supports local files, directories, and
remote storage (S3, GCS, Azure) with fast, memory-efficient processing.
"""

__version__ = "1.0.2"
__author__ = "Abdul Rafey"
__email__ = "abdulrafey38@gmail.com"

from parql.core.engine import ParQLEngine
from parql.core.context import ParQLContext

__all__ = ["ParQLEngine", "ParQLContext"]
