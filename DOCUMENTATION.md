# ParQL Complete Documentation

**Comprehensive reference for all ParQL commands and features**

## Table of Contents

1. [Basic Operations](#basic-operations)
2. [Data Analysis](#data-analysis)  
3. [Aggregations](#aggregations)
4. [Joins & SQL](#joins--sql)
5. [String Operations](#string-operations)
6. [Visualization](#visualization)
7. [Data Quality](#data-quality)
8. [System Commands](#system-commands)
9. [Advanced Features](#advanced-features)
10. [Examples](#examples)

---

## Basic Operations

### `parql head` - Preview First Rows
Display the first N rows of a Parquet file.

```bash
# Basic usage
parql head data/sales.parquet
parql head data/sales.parquet -n 20

# With column selection
parql head data/sales.parquet -c "user_id,revenue,country" -n 10

# With filtering
parql head data/sales.parquet -w "revenue > 1000" -n 5
# Multiple where using AND
parql head data/sales.parquet -w "revenue > 1000 AND country = 'US'" 

# With ordering
parql head data/sales.parquet -o "revenue DESC" -n 10
```

**Options:**
- `-n, --rows`: Number of rows to display (default: 10)
- `-c, --columns`: Comma-separated list of columns
- `-w, --where`: WHERE clause condition  
- `-o, --order-by`: ORDER BY clause

---

### `parql tail` - Preview Last Rows
Display the last N rows of a Parquet file.

```bash
parql tail data/sales.parquet -n 20
parql tail data/sales.parquet -c "timestamp,revenue" -n 5
```

**Options:** Same as `head`

---

### `parql schema` - Column Information
Display schema and column information.

```bash
parql schema data/sales.parquet
```

**Output:** Table with column names, data types, and nullability.

---

### `parql count` - Count Rows
Count total rows or rows matching a condition.

```bash
# Total row count
parql count data/sales.parquet

# Conditional count
parql count data/sales.parquet -w "country = 'US'"
parql count data/sales.parquet -w "revenue > 1000 AND is_premium = true"  
```

---

### `parql select` - Filter and Select Data
Select columns and filter rows with advanced options.

```bash
# Select specific columns
parql select data/sales.parquet -c "user_id,revenue,country"

# Filter rows
parql select data/sales.parquet -w "revenue > 500 AND country IN ('US', 'UK')"

# Sort results
parql select data/sales.parquet -o "revenue DESC, timestamp ASC" -l 50

# Get distinct rows
parql select data/sales.parquet -c "country,device" --distinct
```

**Options:**
- `-c, --columns`: Column selection
- `-w, --where`: Filter conditions
- `-o, --order-by`: Sort specification
- `-l, --limit`: Maximum rows to return
- `--distinct`: Return unique rows only

---

### `parql distinct` - Unique Values
Get distinct values or combinations.

```bash
# Distinct values in one column
parql distinct data/sales.parquet -c "country"

# Distinct combinations
parql distinct data/sales.parquet -c "country,device"

# All distinct rows
parql distinct data/sales.parquet
```

---

### `parql sample` - Random Sampling
Sample data for quick analysis.

```bash
# Sample by number of rows
parql sample data/sales.parquet --rows 1000

# Sample by fraction
parql sample data/sales.parquet --fraction 0.01

# Reproducible sampling
parql sample data/sales.parquet --rows 500 --seed 42
```

---

## Data Analysis

### `parql corr` - Correlation Analysis
Calculate correlation matrices between numeric columns.

```bash
# All numeric columns
parql corr data/sales.parquet

# Specific columns
parql corr data/sales.parquet -c "quantity,price,revenue,discount"

# Different correlation methods
parql corr data/sales.parquet --method pearson
parql corr data/sales.parquet --method spearman
```

**Output:** Correlation matrix showing relationships between variables.

---

### `parql profile` - Data Profiling
Generate comprehensive data quality reports.

```bash
# Basic profiling
parql profile data/sales.parquet

# Detailed profiling with outliers
parql profile data/sales.parquet --include-all

# Profile specific columns
parql profile data/users.parquet -c "age,country,plan"
```

**Provides:**
- Null counts and percentages
- Distinct value counts  
- Min/max/mean/std for numeric columns
- String length statistics
- Outlier detection (with `--include-all`)
- Most common values

---

### `parql percentiles` - Percentile Analysis
Calculate detailed percentile statistics.

```bash
# Standard percentiles (25, 50, 75, 90, 95, 99)
parql percentiles data/sales.parquet -c "revenue,quantity"

# Custom percentiles
parql percentiles data/sales.parquet --percentiles "10,25,50,75,90,95,99"

# All numeric columns
parql percentiles data/sales.parquet
```

---

### `parql outliers` - Outlier Detection
Detect statistical outliers in numeric data.

```bash
# Z-score method (default)
parql outliers data/sales.parquet -c revenue --method zscore --threshold 3

# IQR method
parql outliers data/sales.parquet -c revenue --method iqr --threshold 1.5
```

**Methods:**
- `zscore`: Standard deviation based
- `iqr`: Interquartile range based

---

### `parql nulls` - Null Analysis
Analyze missing values across columns.

```bash
# All columns
parql nulls data/sales.parquet

# Specific column
parql nulls data/sales.parquet -c "discount"
```

**Output:** Null counts and percentages per column.

---

### `parql hist` - Histograms
Generate histograms for numeric columns.

```bash
parql hist data/sales.parquet -c revenue --bins 20
parql hist data/sales.parquet -c quantity --bins 10
```

---

## Aggregations

### `parql agg` - Group and Aggregate
Perform grouping and aggregation operations.

```bash
# Basic grouping
parql agg data/sales.parquet -g "country" -a "sum(revenue):total,count():orders"

# Multiple group columns
parql agg data/sales.parquet -g "country,device" -a "avg(revenue):avg_rev,count():cnt"

# With ordering and limits
parql agg data/sales.parquet -g "country" -a "sum(revenue):total" -o "total DESC" -l 10

# With HAVING clause
parql agg data/sales.parquet -g "user_id" -a "sum(revenue):total" -h "total > 1000"
```

**Aggregation Functions:**
- `count()`: Row count
- `sum(column)`: Sum of values
- `avg(column)`: Average
- `min(column)`: Minimum value
- `max(column)`: Maximum value
- `stddev(column)`: Standard deviation

---

### `parql pivot` - Pivot Tables
Transform data from long to wide format.

```bash
parql pivot data/sales.parquet -i "country" -c "device" -v "revenue" -f "sum"
parql pivot data/sales.parquet -i "user_id,country" -c "product" -v "quantity" -f "avg"
```

**Options:**
- `-i, --index`: Index columns (row headers)
- `-c, --columns`: Columns to pivot 
- `-v, --values`: Values column to aggregate
- `-f, --func`: Aggregation function

---

### `parql window` - Window Functions
Apply window functions for advanced analytics.

```bash
# Ranking within groups
parql window data/sales.parquet --partition "country" --order "revenue DESC" --expr "row_number() as rank"

# Running totals
parql window data/sales.parquet --partition "user_id" --order "timestamp" --expr "sum(revenue) over (rows unbounded preceding) as running_total"

# Moving averages
parql window data/sales.parquet --partition "user_id" --order "timestamp" --expr "avg(revenue) over (rows between 2 preceding and current row) as moving_avg"
```

**Window Functions:**
- `row_number()`: Sequential numbering
- `rank()`: Ranking with gaps
- `dense_rank()`: Ranking without gaps
- `lag(column, n)`: Previous value
- `lead(column, n)`: Next value
- `sum()`, `avg()`, `min()`, `max()`: Aggregates over window

---

## Joins & SQL

### `parql join` - Join Datasets
Join two Parquet files.

```bash
# Inner join
parql join data/users.parquet data/sales.parquet --on "user_id" --how inner

# Left join with column selection
parql join data/users.parquet data/sales.parquet --on "user_id" --how left -c "users.first_name,sales.revenue"

# Complex join conditions
parql join data/users.parquet data/sales.parquet --on "users.user_id = sales.user_id AND users.country = sales.country"
```

**Join Types:**
- `inner`: Only matching rows
- `left`: All left rows + matching right
- `right`: All right rows + matching left  
- `full`: All rows from both tables

---

### `parql sql` - Custom SQL Queries
Execute custom SQL with table parameters.

```bash
# Simple query
parql sql "SELECT country, SUM(revenue) FROM t GROUP BY country ORDER BY 2 DESC" -p t=data/sales.parquet

# Multi-table queries
parql sql "
  SELECT u.first_name, s.total_spent 
  FROM users u 
  JOIN (SELECT user_id, SUM(revenue) as total_spent FROM sales GROUP BY user_id) s 
  ON u.user_id = s.user_id
  WHERE s.total_spent > 1000
" -p users=data/users.parquet -p sales=data/sales.parquet

# CTEs and window functions
parql sql "
  WITH ranked_sales AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY country ORDER BY revenue DESC) as rank
    FROM t
  )
  SELECT * FROM ranked_sales WHERE rank <= 5
" -p t=data/sales.parquet
```

---

## String Operations

### `parql str` - String Manipulation
Perform string operations on text columns.

```bash
# Case conversion
parql str data/users.parquet --column first_name --operation upper
parql str data/users.parquet --column email --operation lower
parql str data/users.parquet --column name --operation title

# Trimming
parql str data/users.parquet --column name --operation strip
parql str data/users.parquet --column code --operation lstrip

# String length
parql str data/users.parquet --column email --operation length

# Pattern replacement
parql str data/users.parquet --column email --operation replace --pattern "@gmail.com" --replacement "@company.com"

# Regex extraction
parql str data/users.parquet --column email --operation extract --pattern "@([a-z]+\\.com)"

# Pattern checking
parql str data/users.parquet --column name --operation contains --pattern "John"
parql str data/users.parquet --column email --operation startswith --pattern "admin"
parql str data/users.parquet --column phone --operation endswith --pattern "000"
```

**Operations:**
- `upper`, `lower`, `title`, `capitalize`: Case conversion
- `strip`, `lstrip`, `rstrip`: Remove whitespace
- `length`: String length
- `split`: Split by delimiter
- `extract`: Regex extraction
- `replace`: Pattern replacement
- `contains`, `startswith`, `endswith`: Pattern matching

---

### `parql pattern` - Pattern Matching
Advanced pattern searching with SQL LIKE or regex.

```bash
# SQL LIKE patterns
parql pattern data/users.parquet --pattern "%gmail%"
parql pattern data/users.parquet --pattern "John_" --case-sensitive

# Regex patterns
parql pattern data/users.parquet --pattern "john.*@gmail" --regex
parql pattern data/users.parquet --pattern "\\d{3}-\\d{3}-\\d{4}" --regex

# Search specific columns
parql pattern data/users.parquet --pattern "%@company%" -c "email,plan"

# Count matches only
parql pattern data/users.parquet --pattern "premium" -c "plan" --count-only
```

---

## Visualization

### `parql plot` - ASCII Charts
Create terminal-based visualizations.

```bash
# Histogram
parql plot data/sales.parquet -c revenue --chart-type hist --bins 20 --width 60

# Bar chart for categories
parql plot data/sales.parquet -c country --chart-type bar --width 50 --limit 10

# Scatter plot
parql plot data/sales.parquet -c revenue --chart-type scatter -x quantity --limit 100

# Line chart for trends
parql plot data/timeseries.parquet -c metric_a --chart-type line --limit 50
```

**Chart Types:**
- `hist`: Histograms for numeric distributions
- `bar`: Bar charts for categorical data
- `scatter`: Scatter plots for relationships
- `line`: Line charts for trends

**Options:**
- `--bins`: Number of histogram bins
- `--width`: Chart width in characters
- `--height`: Chart height in characters
- `--limit`: Maximum data points
- `-x, --x-column`: X-axis column for scatter plots

---

## Data Quality

### `parql assert` - Data Validation
Assert data quality rules and constraints.

```bash
# Basic assertions
parql assert data/sales.parquet --rule "row_count > 1000"
parql assert data/sales.parquet --rule "no_nulls(user_id)" 
parql assert data/sales.parquet --rule "unique(order_id)"

# Custom SQL conditions
parql assert data/sales.parquet --rule "min(revenue) >= 0"
parql assert data/sales.parquet --rule "max(discount) <= 1.0"

# Multiple rules with fail-fast
parql assert data/sales.parquet --rule "row_count > 5000" --rule "no_nulls(order_id)" --fail-fast
```

**Built-in Rules:**
- `row_count > N`: Minimum row count
- `no_nulls(column)`: No null values
- `unique(column)`: All values unique
- Custom SQL expressions

---

### `parql compare-schema` - Schema Comparison
Compare schemas between two Parquet files.

```bash
# Basic comparison
parql compare-schema data/old.parquet data/new.parquet

# Fail on differences (useful for CI/CD)
parql compare-schema data/expected.parquet data/actual.parquet --fail-on-change
```

**Output:** Shows added, removed, and changed columns.

---

### `parql infer-types` - Type Optimization
Analyze and suggest optimal data types.

```bash
# Basic type inference
parql infer-types data/sales.parquet

# Get optimization suggestions with SQL
parql infer-types data/sales.parquet --suggest-types --sample-size 50000
```

**Features:**
- Detects optimal integer types (SMALLINT, INTEGER, BIGINT)
- Suggests appropriate VARCHAR lengths
- Identifies boolean and date columns
- Provides SQL for type conversion

---

## System Commands

### `parql config` - Configuration Management
Manage settings and profiles.

```bash
# Set configuration
parql config set --profile production --threads 8 --memory-limit 4GB --output-format csv

# Show current config
parql config show --profile production

# Remove setting
parql config unset --profile production memory-limit
```

**Settings:**
- `threads`: Processing threads
- `memory-limit`: Memory usage limit
- `output-format`: Default output format
- `max-width`: Display width
- `cache-enabled`: Enable caching
- `cache-ttl`: Cache expiration

---

### `parql cache` - Cache Management
Manage query result caching.

```bash
# View cache statistics
parql cache info

# Clear all cached results
parql cache clear
```

**Features:**
- Automatic result caching
- TTL-based expiration
- Cache size tracking
- Performance statistics

---

### `parql shell` - Interactive Mode
Start interactive REPL for exploratory analysis.

```bash
# Start shell
parql shell

# Start with profile
parql shell --profile myprofile
```

**Shell Commands:**
```bash
parql> \l data/sales.parquet sales    # Load file as 'sales'
parql> \tables                        # Show loaded tables  
parql> \schema sales                  # Show table schema
parql> \clear                         # Clear screen
parql> SELECT country, SUM(revenue) FROM sales GROUP BY country;
parql> exit                           # Exit shell
```

---

## Advanced Features

### `parql write` - Export Data
Write query results to various formats.

```bash
# Export to CSV
parql write data/sales.parquet output.csv --format csv -c "country,revenue" -w "revenue > 1000"

# Export to Parquet with compression
parql write data/sales.parquet output.parquet --format parquet --compression zstd

# Export to JSON
parql write data/sales.parquet output.json --format json -w "country = 'US'"

# Dry run to see what would be written
parql write data/sales.parquet output.csv --format csv --dry-run
```

**Formats:** `parquet`, `csv`, `tsv`, `json`, `ndjson`  
**Compression:** `snappy`, `gzip`, `lz4`, `zstd`

---

### Remote Data Sources
ParQL supports reading from cloud storage and distributed file systems.

```bash
# AWS S3
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
parql head s3://bucket/path/data.parquet

# Google Cloud Storage
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
parql agg gs://bucket/data/*.parquet -g country -a "sum(revenue):total"

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
parql schema https://example.com/data.parquet
```

---

### Glob Patterns and Partitioned Data
Work with multiple files and partitioned datasets.

```bash
# Glob patterns
parql head "data/2024/*.parquet" -n 10
parql agg "data/sales/year=*/month=*/*.parquet" -g year,month -a "sum(revenue):total"

# Hive-style partitions (auto-detected)
parql head data/sales_partitioned/country=US/date=2024-01-01/
```

---

## Examples

### Complete Data Analysis Workflow

```bash
# 1. Initial exploration
parql head examples/data/sales.parquet -n 5
parql schema examples/data/sales.parquet  
parql count examples/data/sales.parquet

# 2. Data quality assessment
parql profile examples/data/sales.parquet --include-all
parql nulls examples/data/sales.parquet
parql assert examples/data/sales.parquet --rule "no_nulls(order_id)" --rule "unique(order_id)"

# 3. Statistical analysis
parql corr examples/data/sales.parquet -c "quantity,price,revenue"
parql percentiles examples/data/sales.parquet -c "revenue"
parql outliers examples/data/sales.parquet -c revenue --method zscore

# 4. Visualization
parql plot examples/data/sales.parquet -c revenue --chart-type hist --bins 20
parql plot examples/data/sales.parquet -c country --chart-type bar

# 5. Advanced analytics
parql agg examples/data/sales.parquet -g "country,device" -a "sum(revenue):total,avg(revenue):avg_rev" -o "total DESC"
parql window examples/data/sales.parquet --partition "user_id" --order "timestamp" --expr "row_number() as order_num"
```

### Multi-table Analysis

```bash
# Join and analyze
parql join examples/data/users.parquet examples/data/sales.parquet --on "user_id" --how inner -c "users.country,sales.revenue"

# Complex SQL analysis
parql sql "
  WITH user_metrics AS (
    SELECT 
      u.user_id,
      u.country,
      u.plan,
      COUNT(s.order_id) as total_orders,
      SUM(s.revenue) as total_spent,
      AVG(s.revenue) as avg_order_value
    FROM users u
    LEFT JOIN sales s ON u.user_id = s.user_id
    GROUP BY u.user_id, u.country, u.plan
  )
  SELECT 
    country,
    plan,
    COUNT(*) as users,
    AVG(total_spent) as avg_lifetime_value,
    AVG(total_orders) as avg_orders_per_user
  FROM user_metrics
  GROUP BY country, plan
  ORDER BY avg_lifetime_value DESC
" -p users=examples/data/users.parquet -p sales=examples/data/sales.parquet
```

### Data Cleaning Pipeline

```bash
# 1. Identify data issues
parql pattern examples/data/users.parquet --pattern ".*invalid.*" --regex
parql profile examples/data/users.parquet -c "email,phone"

# 2. Clean string data
parql str examples/data/users.parquet --column first_name --operation title
parql str examples/data/users.parquet --column email --operation lower  

# 3. Validate results
parql assert examples/data/users.parquet --rule "no_nulls(email)"
parql pattern examples/data/users.parquet --pattern "%@%.%" -c "email" --count-only
```

### Performance Optimization

```bash
# 1. Set up configuration for large datasets
parql config set --threads 8 --memory-limit 8GB --cache-enabled true

# 2. Analyze data types for optimization
parql infer-types examples/data/sales.parquet --suggest-types

# 3. Use caching for repeated analysis
parql cache info
parql shell  # Use interactive mode with automatic caching
```

### Interactive Exploration

```bash
parql shell
# Inside shell:
parql> \l examples/data/sales.parquet sales
parql> \l examples/data/users.parquet users
parql> \tables
parql> SELECT COUNT(*) FROM sales;
parql> SELECT country, COUNT(*) FROM users GROUP BY country;
parql> SELECT u.country, AVG(s.revenue) 
       FROM users u JOIN sales s ON u.user_id = s.user_id 
       GROUP BY u.country 
       ORDER BY 2 DESC;
```

---

## Output Formats

All commands support multiple output formats:

```bash
# Table format (default, rich formatting)
parql head data/sales.parquet --format table

# CSV output
parql agg data/sales.parquet -g country -a "sum(revenue):total" --format csv

# JSON output  
parql select data/sales.parquet -c "country,revenue" --format json

# Markdown tables
parql schema data/sales.parquet --format markdown

# Quiet mode (minimal output)
parql --quiet count data/sales.parquet
```

---

## Global Options

These options work with all commands:

- `--threads INTEGER`: Number of processing threads
- `--memory-limit TEXT`: Memory limit (e.g., 4GB)  
- `--format [table|csv|tsv|json|ndjson|markdown]`: Output format
- `--verbose`: Verbose output with additional information
- `--quiet`: Minimal output mode
- `--max-width INTEGER`: Maximum display width

---

*This documentation covers all ParQL features. For more examples, see the `/examples` directory in the repository.*
