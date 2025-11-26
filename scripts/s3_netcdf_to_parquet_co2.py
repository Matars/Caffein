#!/usr/bin/env python3
"""
Convert CO2 NetCDF files from S3 to Parquet format with memory-efficient chunked processing.
Designed for 4GB RAM VMs. Processes CAMS CO2 data month-by-month, timestamp-by-timestamp.

Source: s3://caff-dump/cds/co2/*.nc (monthly files with 3-hourly data)
Target: s3://caffine-analytics-storage-eu-central-1-925314695663/raw/cds/co2/year={year}/month={month}/day={day}/hour={hour}/data.parquet

Usage:
    python s3_netcdf_to_parquet_co2.py --year 2023 --month 1
    python s3_netcdf_to_parquet_co2.py --process-all  # Process all files
"""

import sys
import argparse
import boto3
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
import netCDF4 as nc
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

# AWS Configuration
SOURCE_BUCKET = 'caff-dump'
SOURCE_PREFIX = 'cds/co2'
TARGET_BUCKET = 'caffine-analytics-storage-eu-central-1-925314695663'
TARGET_PREFIX = 'raw/cds/co2'

# Memory settings - conservative for 4GB RAM
CHUNK_SIZE = 10000  # Process 10k records at a time
MAX_TIMESTAMP_ROWS = 100000  # Expected max rows per timestamp (180 lat * 360 lon = 64,800)

class NetCDFToParquetConverterCO2:
    """Memory-efficient converter for CAMS CO2 NetCDF to Parquet."""
    
    def __init__(self, aws_access_key=None, aws_secret_key=None, aws_region='eu-central-1'):
        """Initialize with AWS credentials."""
        # Build S3 client configuration
        s3_config = {'region_name': aws_region}
        
        # Only add credentials if explicitly provided
        # Otherwise boto3 will use default credential chain (~/.aws/credentials, IAM roles, etc.)
        if aws_access_key and aws_secret_key:
            s3_config['aws_access_key_id'] = aws_access_key
            s3_config['aws_secret_access_key'] = aws_secret_key
        
        self.s3_client = boto3.client('s3', **s3_config)
        self.temp_dir = None
    
    def list_source_files(self):
        """List all .nc files in source bucket."""
        print(f"📂 Listing files from s3://{SOURCE_BUCKET}/{SOURCE_PREFIX}/")
        
        response = self.s3_client.list_objects_v2(
            Bucket=SOURCE_BUCKET,
            Prefix=SOURCE_PREFIX
        )
        
        nc_files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.nc'):
                    size_mb = obj['Size'] / (1024 * 1024)
                    nc_files.append({
                        'key': key,
                        'size_mb': round(size_mb, 2),
                        'last_modified': obj['LastModified']
                    })
        
        print(f"✓ Found {len(nc_files)} NetCDF files")
        return nc_files
    
    def parse_filename(self, s3_key):
        """
        Extract year and month from CAMS filename.
        Expected format: cams73_latest_co2_conc_surface_inst_YYYYMM.nc
        """
        filename = Path(s3_key).name
        
        # Try to extract YYYYMM from filename
        # Example: cams73_latest_co2_conc_surface_inst_202301.nc
        parts = filename.replace('.nc', '').split('_')
        date_str = parts[-1]  # Should be YYYYMM
        
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            return year, month
        except:
            print(f"⚠️  Could not parse year/month from: {filename}")
            return None, None
    
    def download_file(self, s3_key, local_path):
        """Download file from S3 to local temp directory."""
        print(f"⬇️  Downloading s3://{SOURCE_BUCKET}/{s3_key}")
        
        self.s3_client.download_file(
            SOURCE_BUCKET,
            s3_key,
            local_path
        )
        
        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"✓ Downloaded {file_size_mb:.2f} MB to {local_path}")
    
    def parse_time_value(self, time_value, time_units, base_year, base_month):
        """
        Parse time value to get year, month, day, hour.
        
        Args:
            time_value: Numeric time value (e.g., 0, 3, 6, 9 for hours)
            time_units: Time units string (e.g., "hours since 2023-01-01 00:00:00")
            base_year: Base year from filename
            base_month: Base month from filename
        
        Returns:
            tuple: (year, month, day, hour)
        """
        # Parse reference date from time_units
        # Format: "hours since 2023-01-01 00:00:00"
        try:
            ref_date_str = time_units.split('since')[1].strip()
            ref_date = datetime.strptime(ref_date_str, '%Y-%m-%d %H:%M:%S')
        except:
            # Fallback to using base year/month
            ref_date = datetime(base_year, base_month, 1, 0, 0, 0)
        
        # Add time_value hours to reference date
        timestamp = ref_date + timedelta(hours=float(time_value))
        
        return timestamp.year, timestamp.month, timestamp.day, timestamp.hour
    
    def extract_timestamp_data_chunked(self, dataset, time_idx, base_year, base_month, level=0):
        """
        Extract data for a single timestamp with chunked iteration (memory-efficient).
        
        Args:
            dataset: Open netCDF4.Dataset
            time_idx: Time index (0-based timestamp number)
            base_year: Base year from filename
            base_month: Base month from filename
            level: Vertical level (0 = surface)
        
        Returns:
            pandas.DataFrame with columns: latitude, longitude, co2_concentration, time_value, year, month, day, hour
        """
        # Get dimensions
        lons = dataset.variables['longitude'][:]
        lats = dataset.variables['latitude'][:]
        times = dataset.variables['time'][:]
        
        # Find CO2 variable
        co2_var_name = None
        for var in ['CO2', 'co2', 'carbon_dioxide']:
            if var in dataset.variables:
                co2_var_name = var
                break
        
        if not co2_var_name:
            raise ValueError("Could not find CO2 variable in NetCDF")
        
        co2_data = dataset.variables[co2_var_name]
        co2_units = co2_data.units if hasattr(co2_data, 'units') else 'unknown'
        
        # Get time metadata
        time_units = dataset.variables['time'].units if hasattr(dataset.variables['time'], 'units') else 'unknown'
        time_value = float(times[time_idx])
        
        # Parse timestamp to get year/month/day/hour
        year, month, day, hour = self.parse_time_value(time_value, time_units, base_year, base_month)
        
        print(f"  📊 Processing timestamp {time_idx + 1}/{len(times)}: {year}-{month:02d}-{day:02d} {hour:02d}:00")
        print(f"     Shape: {co2_data.shape}")
        
        # Extract data for this timestamp and level
        # Shape: (time, level, lat, lon) or (time, lat, lon)
        if len(co2_data.shape) == 4:
            # 4D: Extract specific timestamp and level
            timestamp_data = co2_data[time_idx, level, :, :]  # Shape: (lat, lon)
        elif len(co2_data.shape) == 3:
            # 3D: Extract specific timestamp
            timestamp_data = co2_data[time_idx, :, :]  # Shape: (lat, lon)
        else:
            raise ValueError(f"Unsupported data shape: {co2_data.shape}")
        
        # Convert to numpy array (loads into memory - but just one timestamp's data ~180*360 = 64k points)
        timestamp_array = np.array(timestamp_data)
        
        # Create meshgrid for lat/lon
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # Flatten arrays
        lat_flat = lat_grid.flatten()
        lon_flat = lon_grid.flatten()
        co2_flat = timestamp_array.flatten()
        
        # Filter out invalid/missing data (NaN, fill values)
        valid_mask = ~np.isnan(co2_flat) & (co2_flat > 0)
        
        # Build DataFrame in chunks to save memory
        records = []
        valid_indices = np.where(valid_mask)[0]
        
        print(f"     ✓ Valid data points: {len(valid_indices):,} / {len(co2_flat):,}")
        
        for i in range(0, len(valid_indices), CHUNK_SIZE):
            chunk_indices = valid_indices[i:i + CHUNK_SIZE]
            
            chunk_records = {
                'latitude': lat_flat[chunk_indices],
                'longitude': lon_flat[chunk_indices],
                'co2_concentration': np.round(co2_flat[chunk_indices], 8),  # More precision for mol mol-1
                'time_value': np.full(len(chunk_indices), time_value),
                'co2_units': co2_units,
                'time_units': time_units,
                'level': level,
                'year': year,
                'month': month,
                'day': day,
                'hour': hour
            }
            
            records.append(pd.DataFrame(chunk_records))
        
        # Concatenate chunks
        if records:
            df = pd.concat(records, ignore_index=True)
            return df
        else:
            return pd.DataFrame()
    
    def convert_file(self, s3_key, year=None, month=None):
        """
        Convert a single NetCDF file to hourly Parquet files.
        
        Downloads NetCDF, extracts data timestamp-by-timestamp, uploads Parquet per timestamp.
        """
        # Parse year/month if not provided
        if year is None or month is None:
            year, month = self.parse_filename(s3_key)
            if year is None:
                print(f"❌ Skipping {s3_key} - could not parse year/month")
                return False
        
        print(f"\n{'='*80}")
        print(f"🔄 Converting {s3_key}")
        print(f"   Year: {year}, Month: {month}")
        print(f"{'='*80}")
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix='netcdf_convert_co2_')
        local_nc_path = os.path.join(self.temp_dir, 'input.nc')
        
        try:
            # Download NetCDF file
            self.download_file(s3_key, local_nc_path)
            
            # Open NetCDF
            dataset = nc.Dataset(local_nc_path, 'r')
            num_timestamps = len(dataset.variables['time'])
            
            print(f"⏰ Processing {num_timestamps} timestamps (3-hourly data)...")
            
            # Process each timestamp
            for time_idx in range(num_timestamps):
                
                # Extract timestamp data
                df = self.extract_timestamp_data_chunked(dataset, time_idx, year, month, level=0)
                
                if df.empty:
                    print(f"     ⚠️  No valid data for timestamp {time_idx + 1}, skipping")
                    continue
                
                # Get year/month/day/hour from first row (all rows have same timestamp)
                ts_year = int(df['year'].iloc[0])
                ts_month = int(df['month'].iloc[0])
                ts_day = int(df['day'].iloc[0])
                ts_hour = int(df['hour'].iloc[0])
                
                # Write to Parquet
                local_parquet_path = os.path.join(self.temp_dir, f'ts_{time_idx}.parquet')
                df.to_parquet(local_parquet_path, engine='pyarrow', compression='snappy', index=False)
                
                parquet_size_mb = os.path.getsize(local_parquet_path) / (1024 * 1024)
                print(f"     ✓ Created Parquet: {parquet_size_mb:.2f} MB, {len(df):,} rows")
                
                # Upload to S3 with year/month/day/hour partitioning
                s3_key_target = f"{TARGET_PREFIX}/year={ts_year}/month={ts_month:02d}/day={ts_day:02d}/hour={ts_hour:02d}/data.parquet"
                
                self.s3_client.upload_file(
                    local_parquet_path,
                    TARGET_BUCKET,
                    s3_key_target
                )
                
                print(f"     ⬆️  Uploaded to s3://{TARGET_BUCKET}/{s3_key_target}")
                
                # Clean up parquet file to save disk space
                os.remove(local_parquet_path)
                
                # Clean up DataFrame to free memory
                del df
            
            dataset.close()
            print(f"\n✅ Successfully processed {num_timestamps} timestamps from {s3_key}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error processing {s3_key}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up temp directory")
    
    def process_all(self):
        """Process all NetCDF files in source bucket."""
        files = self.list_source_files()
        
        if not files:
            print("❌ No files found to process")
            return
        
        print(f"\n🚀 Starting batch conversion of {len(files)} files")
        
        success_count = 0
        failure_count = 0
        
        for file_info in files:
            s3_key = file_info['key']
            
            success = self.convert_file(s3_key)
            
            if success:
                success_count += 1
            else:
                failure_count += 1
        
        print(f"\n{'='*80}")
        print(f"📊 Conversion Summary")
        print(f"   Total files: {len(files)}")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Failed: {failure_count}")
        print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert CAMS CO2 NetCDF files from S3 to Parquet format (Athena-ready)'
    )
    
    parser.add_argument('--year', type=int, help='Year to process (if processing single file)')
    parser.add_argument('--month', type=int, help='Month to process (if processing single file)')
    parser.add_argument('--file', type=str, help='Specific S3 key to process (e.g., cds/co2/file.nc)')
    parser.add_argument('--process-all', action='store_true', help='Process all files in source bucket')
    parser.add_argument('--aws-access-key', type=str, help='AWS Access Key ID (or set AWS_ACCESS_KEY_ID env var)')
    parser.add_argument('--aws-secret-key', type=str, help='AWS Secret Access Key (or set AWS_SECRET_ACCESS_KEY env var)')
    parser.add_argument('--aws-region', type=str, default='eu-central-1', help='AWS region')
    
    args = parser.parse_args()
    
    # Get AWS credentials from args or environment
    # If not provided, boto3 will use default credential chain (~/.aws/credentials, IAM roles, etc.)
    aws_access_key = args.aws_access_key or os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = args.aws_secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    if aws_access_key and aws_secret_key:
        print("🔑 Using provided AWS credentials")
    else:
        print("🔑 Using default AWS credentials from ~/.aws/credentials or IAM role")
    
    # Initialize converter
    converter = NetCDFToParquetConverterCO2(
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_region=args.aws_region
    )
    
    # Process files
    if args.process_all:
        converter.process_all()
    elif args.file:
        converter.convert_file(args.file, year=args.year, month=args.month)
    else:
        print("❌ Must specify either --process-all or --file")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
