#!/usr/bin/env python3
"""
Generate ALTER TABLE statements to add all CH4 partitions to Athena.
Scans S3 bucket and generates SQL statements for all year/month/day partitions found.

Usage:
    python3 generate_partition_statements.py > add_partitions.sql
    # Then run the output SQL in Athena console
"""

import boto3
import os
from collections import defaultdict

BUCKET = 'caffine-analytics-storage-eu-central-1-925314695663'
PREFIX = 'raw/cds/ch4/'
TABLE_NAME = 'ch4'

def get_partitions_from_s3():
    """Scan S3 and extract all year/month/day partitions."""
    # Use default AWS credentials
    s3_client = boto3.client('s3', region_name='eu-central-1')
    
    print("-- Scanning S3 for partitions...", flush=True)
    print(f"-- Bucket: {BUCKET}", flush=True)
    print(f"-- Prefix: {PREFIX}", flush=True)
    print("--", flush=True)
    
    paginator = s3_client.get_paginator('list_objects_v2')
    partitions = set()
    
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            key = obj['Key']
            
            # Look for pattern: raw/cds/ch4/year=YYYY/month=MM/day=DD/data.parquet
            if 'year=' in key and 'month=' in key and 'day=' in key and key.endswith('.parquet'):
                # Extract year, month, day from path
                parts = key.split('/')
                year_part = [p for p in parts if p.startswith('year=')][0]
                month_part = [p for p in parts if p.startswith('month=')][0]
                day_part = [p for p in parts if p.startswith('day=')][0]
                
                year = year_part.split('=')[1]
                month = month_part.split('=')[1]
                day = day_part.split('=')[1]
                
                partitions.add((int(year), int(month), int(day)))
    
    return sorted(partitions)

def generate_alter_statements(partitions):
    """Generate ALTER TABLE ADD PARTITION statements."""
    print(f"-- Found {len(partitions)} partitions")
    print("--")
    print("-- Run these statements in AWS Athena console:")
    print("--")
    print()
    
    for year, month, day in partitions:
        location = f"s3://{BUCKET}/{PREFIX}year={year}/month={month:02d}/day={day:02d}/"
        sql = f"ALTER TABLE {TABLE_NAME} ADD IF NOT EXISTS PARTITION (year={year}, month={month}, day={day}) LOCATION '{location}';"
        print(sql)
    
    print()
    print(f"-- Total: {len(partitions)} partition statements generated")

def main():
    try:
        partitions = get_partitions_from_s3()
        
        if not partitions:
            print("-- ERROR: No partitions found in S3!")
            print(f"-- Check that data exists in s3://{BUCKET}/{PREFIX}")
            return
        
        generate_alter_statements(partitions)
        
    except Exception as e:
        print(f"-- ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
