#!/usr/bin/env python3
"""
Create sample Parquet data for ParQL examples and testing.

This script generates various types of sample datasets to demonstrate
ParQL's capabilities.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


def create_sales_data():
    """Create sample sales data."""
    np.random.seed(42)
    
    # Generate sample data
    n_records = 10000
    
    countries = ['US', 'UK', 'Germany', 'France', 'Japan', 'Canada', 'Australia']
    devices = ['mobile', 'desktop', 'tablet']
    products = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
    
    start_date = datetime(2024, 1, 1)
    
    data = {
        'order_id': [f'ORD-{i:06d}' for i in range(1, n_records + 1)],
        'user_id': np.random.randint(1, 1000, n_records),
        'timestamp': [start_date + timedelta(days=np.random.randint(0, 365), 
                                           hours=np.random.randint(0, 24),
                                           minutes=np.random.randint(0, 60)) 
                      for _ in range(n_records)],
        'country': np.random.choice(countries, n_records),
        'device': np.random.choice(devices, n_records),
        'product': np.random.choice(products, n_records),
        'quantity': np.random.randint(1, 10, n_records),
        'price': np.round(np.random.uniform(10, 500, n_records), 2),
        'revenue': None,  # Will calculate below
        'discount': np.random.uniform(0, 0.3, n_records),
        'is_premium': np.random.choice([True, False], n_records, p=[0.2, 0.8])
    }
    
    df = pd.DataFrame(data)
    
    # Calculate revenue
    df['revenue'] = np.round(df['quantity'] * df['price'] * (1 - df['discount']), 2)
    
    # Add some nulls for testing
    null_indices = np.random.choice(df.index, size=int(0.02 * len(df)), replace=False)
    df.loc[null_indices, 'discount'] = None
    
    return df


def create_users_data():
    """Create sample users data."""
    np.random.seed(42)
    
    n_users = 1000
    
    first_names = ['John', 'Jane', 'Bob', 'Alice', 'Charlie', 'Diana', 'Eve', 'Frank']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller']
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'company.com']
    
    data = {
        'user_id': range(1, n_users + 1),
        'first_name': np.random.choice(first_names, n_users),
        'last_name': np.random.choice(last_names, n_users),
        'age': np.random.randint(18, 80, n_users),
        'country': np.random.choice(['US', 'UK', 'Germany', 'France', 'Japan'], n_users),
        'signup_date': [datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 400)) 
                       for _ in range(n_users)],
        'plan': np.random.choice(['free', 'basic', 'premium'], n_users, p=[0.6, 0.3, 0.1])
    }
    
    df = pd.DataFrame(data)
    
    # Create email addresses
    df['email'] = (df['first_name'].str.lower() + '.' + 
                   df['last_name'].str.lower() + 
                   df['user_id'].astype(str) + '@' +
                   np.random.choice(domains, n_users))
    
    return df


def create_events_data():
    """Create sample events data with JSON payload."""
    np.random.seed(42)
    
    n_events = 50000
    
    event_types = ['page_view', 'click', 'purchase', 'signup', 'logout']
    pages = ['home', 'product', 'cart', 'checkout', 'profile', 'about']
    
    data = {
        'event_id': [f'EVT-{i:08d}' for i in range(1, n_events + 1)],
        'user_id': np.random.randint(1, 1000, n_events),
        'timestamp': [datetime(2024, 1, 1) + timedelta(
            days=np.random.randint(0, 90),
            hours=np.random.randint(0, 24),
            minutes=np.random.randint(0, 60),
            seconds=np.random.randint(0, 60)
        ) for _ in range(n_events)],
        'event_type': np.random.choice(event_types, n_events),
        'page': np.random.choice(pages, n_events),
        'session_id': [f'SES-{np.random.randint(1, 10000):06d}' for _ in range(n_events)],
    }
    
    df = pd.DataFrame(data)
    
    # Create JSON payload column
    payloads = []
    for _, row in df.iterrows():
        payload = {
            'page': row['page'],
            'referrer': np.random.choice(['google', 'facebook', 'direct', 'email'], 1)[0],
            'browser': np.random.choice(['chrome', 'firefox', 'safari', 'edge'], 1)[0],
            'screen_resolution': np.random.choice(['1920x1080', '1366x768', '1440x900'], 1)[0]
        }
        
        if row['event_type'] == 'purchase':
            payload['amount'] = round(np.random.uniform(10, 500), 2)
            payload['product_id'] = f'PROD-{np.random.randint(1, 100):03d}'
        
        payloads.append(json.dumps(payload))
    
    df['payload'] = payloads
    
    return df


def create_time_series_data():
    """Create sample time series data."""
    np.random.seed(42)
    
    # Generate hourly data for 30 days
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(24 * 30)]
    
    # Simulate metric values with trend and seasonality
    trend = np.linspace(100, 200, len(dates))
    seasonal = 20 * np.sin(2 * np.pi * np.arange(len(dates)) / 24)  # Daily pattern
    noise = np.random.normal(0, 10, len(dates))
    
    data = {
        'timestamp': dates,
        'metric_a': trend + seasonal + noise,
        'metric_b': np.random.exponential(50, len(dates)),
        'metric_c': np.random.poisson(10, len(dates)),
        'region': np.random.choice(['north', 'south', 'east', 'west'], len(dates)),
        'server_id': np.random.choice([f'srv-{i:02d}' for i in range(1, 11)], len(dates))
    }
    
    df = pd.DataFrame(data)
    df['metric_a'] = np.round(df['metric_a'], 2)
    df['metric_b'] = np.round(df['metric_b'], 2)
    
    return df


def main():
    """Create all sample datasets."""
    data_dir = 'examples/data'
    os.makedirs(data_dir, exist_ok=True)
    
    print("Creating sample datasets...")
    
    # Create sales data
    print("  - sales.parquet")
    sales_df = create_sales_data()
    sales_df.to_parquet(f'{data_dir}/sales.parquet', index=False)
    
    # Create users data
    print("  - users.parquet")
    users_df = create_users_data()
    users_df.to_parquet(f'{data_dir}/users.parquet', index=False)
    
    # Create events data
    print("  - events.parquet")
    events_df = create_events_data()
    events_df.to_parquet(f'{data_dir}/events.parquet', index=False)
    
    # Create time series data
    print("  - timeseries.parquet")
    ts_df = create_time_series_data()
    ts_df.to_parquet(f'{data_dir}/timeseries.parquet', index=False)
    
    # Create partitioned data (by country and date)
    print("  - partitioned data (sales_partitioned/)")
    partition_dir = f'{data_dir}/sales_partitioned'
    os.makedirs(partition_dir, exist_ok=True)
    
    sales_df['date'] = sales_df['timestamp'].dt.date
    for (country, date), group in sales_df.groupby(['country', 'date']):
        part_dir = f'{partition_dir}/country={country}/date={date}'
        os.makedirs(part_dir, exist_ok=True)
        group.drop(['country', 'date'], axis=1).to_parquet(
            f'{part_dir}/data.parquet', index=False
        )
    
    print("\nSample data summary:")
    print(f"  Sales: {len(sales_df):,} rows")
    print(f"  Users: {len(users_df):,} rows") 
    print(f"  Events: {len(events_df):,} rows")
    print(f"  Time Series: {len(ts_df):,} rows")
    print(f"\nData created in: {data_dir}/")


if __name__ == '__main__':
    main()
