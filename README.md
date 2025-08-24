# ParQL 🦆

**A powerful command-line tool for querying and manipulating Parquet datasets directly from the terminal.**

ParQL brings pandas-like operations and SQL capabilities to the command line, powered by DuckDB. Query, analyze, visualize, and transform Parquet data instantly without writing scripts or loading into memory. Perfect for data exploration, ETL pipelines, and data quality checks.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI Downloads](https://static.pepy.tech/badge/parql)](https://pepy.tech/projects/parql)

## 🚀 Key Features

- **25+ Commands** - Complete data analysis toolkit from the CLI
- **Interactive Shell** - REPL mode for exploratory data analysis  
- **Built-in Visualizations** - ASCII charts and plots in your terminal
- **Advanced Analytics** - Correlations, profiling, percentiles, outliers
- **String Processing** - Text manipulation and pattern matching
- **Cloud Storage** - Native S3, GCS, Azure, and HTTP support
- **Smart Caching** - Automatic query result caching for performance
- **Data Quality** - Validation, assertions, and schema comparison
- **Multiple Formats** - Output to CSV, JSON, Parquet, Markdown

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (when published)
pip install parql

# Or install from source
git clone https://github.com/abdulrafey38/parql.git
cd parql
pip install -e .
```

### Basic Usage

```bash
# Preview data
parql head data/sales.parquet -n 10

# Data analysis
parql profile data/sales.parquet
parql corr data/sales.parquet -c "quantity,price,revenue"

# Filtering and aggregation  
parql select data/sales.parquet -w "revenue > 1000" -c "country,revenue"
parql agg data/sales.parquet -g "country" -a "sum(revenue):total,count():orders"

# Visualizations
parql plot data/sales.parquet -c revenue --chart-type hist --bins 20

# Interactive exploration
parql shell
parql> \l data/sales.parquet sales
parql> SELECT country, SUM(revenue) FROM sales GROUP BY country;

# Export results
parql write data/sales.parquet output.csv --format csv -w "country='US'"
```

### Complete Documentation

📖 **[View Live Documentation](https://abdulrafey38.github.io/parql/)** - Beautiful, interactive documentation with examples

📖 **[Commands Reference](https://abdulrafey38.github.io/parql/commands.html)** - Complete command reference with examples

📖 **[DOCUMENTATION.md](DOCUMENTATION.md)** - Markdown documentation for offline reference

## 📊 Command Categories

### 🔍 **Data Exploration**
- `head`, `tail`, `schema`, `sample` - Quick data inspection
- `profile` - Comprehensive data quality reports  
- `corr` - Correlation analysis between columns
- `percentiles` - Detailed percentile statistics

### 📈 **Analytics & Aggregation**
- `agg` - Group by and aggregate operations
- `window` - Window functions (ranking, moving averages)
- `pivot` - Pivot tables and data reshaping
- `sql` - Custom SQL queries with full DuckDB support

### 🔧 **Data Processing**  
- `select` - Filter rows and select columns
- `join` - Multi-table joins with various strategies
- `str` - String manipulation and text processing
- `pattern` - Advanced pattern matching with regex

### 📊 **Visualization & Quality**
- `plot` - ASCII charts (histograms, bar charts, scatter plots)
- `assert` - Data validation and quality checks
- `outliers` - Statistical outlier detection
- `nulls` - Missing value analysis

### 🖥️ **System & Productivity**
- `shell` - Interactive REPL mode for exploration
- `config` - Profile and settings management
- `cache` - Query result caching for performance
- `write` - Export to multiple formats

## 💡 Quick Examples

### Data Exploration
```bash
# Get a quick overview
parql head data/sales.parquet -n 5
parql schema data/sales.parquet
parql profile data/sales.parquet

# Statistical analysis
parql corr data/sales.parquet -c "quantity,price,revenue"
parql percentiles data/sales.parquet -c "revenue"
```

### Data Analysis
```bash
# Aggregations and grouping
parql agg data/sales.parquet -g "country" -a "sum(revenue):total,count():orders"

# Window functions
parql window data/sales.parquet --partition "user_id" --order "timestamp" --expr "row_number() as rank"

# SQL queries
parql sql "SELECT country, SUM(revenue) FROM t GROUP BY country ORDER BY 2 DESC" -p t=data/sales.parquet
```

### Visualizations
```bash
# Charts in your terminal
parql plot data/sales.parquet -c revenue --chart-type hist --bins 20
parql plot data/sales.parquet -c country --chart-type bar
```

### Interactive Mode
```bash
parql shell
parql> \l data/sales.parquet sales
parql> \l data/users.parquet users  
parql> SELECT u.country, AVG(s.revenue) FROM users u JOIN sales s ON u.user_id = s.user_id GROUP BY u.country;
```

## 🌐 Remote Data Sources

ParQL works with data anywhere:

```bash
# AWS S3
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret  
parql head s3://bucket/path/data.parquet

# Google Cloud Storage
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
parql agg gs://bucket/data/*.parquet -g region -a "count():total"

# Public GCS Datasets
parql head gs://anonymous@voltrondata-labs-datasets/diamonds/cut=Good/part-0.parquet
parql agg gs://anonymous@voltrondata-labs-datasets/diamonds/cut=Good/part-0.parquet -g color -a "avg(price):avg_price"

# Azure Blob Storage
export AZURE_STORAGE_ACCOUNT=your_account
export AZURE_STORAGE_KEY=your_key

# Azure Data Lake Storage (Gen2)
parql head abfs://container@account.dfs.core.windows.net/path/data.parquet

# Azure Blob Storage (Hadoop-style)
parql head wasbs://container@account.blob.core.windows.net/path/data.parquet

# Public Azure files via HTTPS
parql head https://account.blob.core.windows.net/container/path/data.parquet

# HDFS (Hadoop Distributed File System)
export HDFS_NAMENODE=localhost
export HDFS_PORT=9000
parql head hdfs://localhost/tmp/save/part-r-00000-6a3ccfae-5eb9-4a88-8ce8-b11b2644d5de.gz.parquet

# HTTP/HTTPS
parql head https://example.com/data.parquet

# Multiple files and glob patterns
parql head "data/2024/*.parquet" -n 10
parql agg "data/sales/year=*/month=*/*.parquet" -g year,month
```

## 🎯 Why ParQL?

### Before ParQL
```python
# Traditional approach - slow, memory intensive
import pandas as pd
df = pd.read_parquet("large_file.parquet")  # Load entire file
result = df[df['revenue'] > 1000].groupby('country')['revenue'].sum()
print(result)
```

### With ParQL  
```bash
# Fast, memory efficient, one command
parql agg data.parquet -g country -a "sum(revenue):total" -w "revenue > 1000"
```

## 📈 Performance

- **Columnar Processing** - Only reads necessary columns
- **Parallel Execution** - Multi-threaded operations  
- **Memory Efficient** - Streams large datasets
- **Cloud Optimized** - Predicate pushdown for remote data

## 🛠️ Development

```bash
# Clone and setup
git clone https://github.com/abdulrafey38/parql.git
cd parql
python -m venv .env
source .env/bin/activate
pip install -e .

# Run tests
pytest tests/

# Check all features
parql --help
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Built With

- **[DuckDB](https://duckdb.org/)** - High-performance analytical database
- **[Rich](https://github.com/willmcgugan/rich)** - Beautiful terminal output
- **[Click](https://click.palletsprojects.com/)** - Command-line interface framework

---

⭐ **If ParQL helps you, please star this repo!** ⭐
