#!/bin/bash

# ParQL Basic Examples
# ====================
# 
# This script demonstrates basic ParQL usage with the sample data.
# Make sure to run create_sample_data.py first to generate the sample datasets.

echo "=========================================="
echo "           ParQL Basic Examples"
echo "=========================================="
echo

# Set data directory
DATA_DIR="examples/data"

echo "1. Viewing Data"
echo "---------------"
echo "Preview first 5 rows of sales data:"
parql head $DATA_DIR/sales.parquet -n 5
echo

echo "Check the schema:"
parql schema $DATA_DIR/sales.parquet
echo

echo "2. Basic Filtering and Selection"
echo "--------------------------------"
echo "High-value orders (revenue > 1000):"
parql select $DATA_DIR/sales.parquet -c "order_id,country,revenue" -w "revenue > 1000" -l 5
echo

echo "3. Aggregations by Country"
echo "--------------------------"
echo "Revenue by country (top 5):"
parql agg $DATA_DIR/sales.parquet -g "country" -a "sum(revenue):total_revenue,count():orders,avg(revenue):avg_order" -o "total_revenue DESC" -l 5
echo

echo "4. SQL Queries"
echo "--------------"
echo "Top customers by total revenue:"
parql sql "
  SELECT user_id, COUNT(*) as orders, SUM(revenue) as total_revenue 
  FROM t 
  GROUP BY user_id 
  ORDER BY total_revenue DESC 
  LIMIT 10
" -p t=$DATA_DIR/sales.parquet
echo

echo "5. Joining Data"
echo "---------------"
echo "User information with their order summary:"
parql sql "
  WITH user_summary AS (
    SELECT 
      user_id,
      COUNT(*) as total_orders,
      SUM(revenue) as total_spent,
      AVG(revenue) as avg_order_value
    FROM sales 
    GROUP BY user_id
  )
  SELECT 
    u.user_id,
    u.first_name,
    u.last_name,
    u.country as user_country,
    u.plan,
    s.total_orders,
    ROUND(s.total_spent, 2) as total_spent,
    ROUND(s.avg_order_value, 2) as avg_order_value
  FROM users u
  JOIN user_summary s ON u.user_id = s.user_id
  ORDER BY s.total_spent DESC
  LIMIT 10
" -p users=$DATA_DIR/users.parquet -p sales=$DATA_DIR/sales.parquet
echo

echo "6. Data Quality Checks"
echo "----------------------"
echo "Validate data quality:"
parql assert $DATA_DIR/sales.parquet \
  --rule "row_count > 5000" \
  --rule "no_nulls(order_id)" \
  --rule "no_nulls(user_id)"
echo

echo "7. Sampling and Statistics"
echo "--------------------------"
echo "Random sample of 3 orders:"
parql sample $DATA_DIR/sales.parquet --rows 3 --seed 42
echo

echo "Check for outliers in revenue:"
parql outliers $DATA_DIR/sales.parquet -c revenue --method zscore --threshold 3 | head -5
echo

echo "8. Export Results"
echo "-----------------"
echo "Export US sales to CSV:"
parql write $DATA_DIR/sales.parquet us_sales_example.csv \
  --format csv \
  -c "order_id,user_id,revenue,timestamp" \
  -w "country = 'US'" 

echo "Exported $(wc -l < us_sales_example.csv) rows to us_sales_example.csv"
echo

echo "=========================================="
echo "       Examples completed successfully!"
echo "=========================================="
