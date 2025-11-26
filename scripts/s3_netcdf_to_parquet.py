#!/usr/bin/env python3
"""
Convert NetCDF files from S3 to Parquet format with memory-efficient chunked processing.
Designed for 4GB RAM VMs. Processes CAMS CH4 data month-by-month, day-by-day.

Source: s3://caff-dump/cds/ch4/*.nc (monthly files, 400-600MB each)
Target: s3://caffine-analytics-storage-eu-central-1/raw/cds/ch4/year={year}/month={month}/day={day}/data.parquet

Usage:
    python s3_netcdf_to_parquet.py --year 2023 --month 1
    python s3_netcdf_to_parquet.py --process-all  # Process all files
"""

import sys
import argparse
import boto3
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime
import netCDF4 as nc
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

# AWS Configuration
SOURCE_BUCKET = 'caff-dump'
SOURCE_PREFIX = 'cds/ch4'
TARGET_BUCKET = 'caffine-analytics-storage-eu-central-1-925314695663'
TARGET_PREFIX = 'raw/cds/ch4'

# Memory settings - conservative for 4GB RAM
CHUNK_SIZE = 10000  # Process 10k records at a time
MAX_DAILY_ROWS = 100000  # Expected max rows per day (180 lat * 360 lon = 64,800)

class NetCDFToParquetConverter:
    """Memory-efficient converter for CAMS CH4 NetCDF to Parquet."""
    
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
        Expected format: cams73_latest_ch4_conc_surface_satellite_dm_YYYYMM.nc
        """
        filename = Path(s3_key).name
        
        # Try to extract YYYYMM from filename
        # Example: cams73_latest_ch4_conc_surface_satellite_dm_202301.nc
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
    
    def extract_day_data_chunked(self, dataset, day_idx, level=0):
        """
        Extract data for a single day with chunked iteration (memory-efficient).
        
        Args:
            dataset: Open netCDF4.Dataset
            day_idx: Time index (0-based day number)
            level: Vertical level (0 = surface)
        
        Returns:
            pandas.DataFrame with columns: latitude, longitude, ch4_concentration, time_value
        """
        # Get dimensions
        lons = dataset.variables['longitude'][:]
        lats = dataset.variables['latitude'][:]
        times = dataset.variables['time'][:]
        
        # Find CH4 variable
        ch4_var_name = None
        for var in ['CH4', 'ch4', 'methane']:
            if var in dataset.variables:
                ch4_var_name = var
                break
        
        if not ch4_var_name:
            raise ValueError("Could not find CH4 variable in NetCDF")
        
        ch4_data = dataset.variables[ch4_var_name]
        ch4_units = ch4_data.units if hasattr(ch4_data, 'units') else 'unknown'
        
        # Get time metadata
        time_units = dataset.variables['time'].units if hasattr(dataset.variables['time'], 'units') else 'unknown'
        
        print(f"  📊 Processing day {day_idx + 1}, shape: {ch4_data.shape}")
        
        # Extract data for this day and level
        # Shape: (time, level, lat, lon) or (time, lat, lon)
        if len(ch4_data.shape) == 4:
            # 4D: Extract specific day and level
            day_data = ch4_data[day_idx, level, :, :]  # Shape: (lat, lon)
        elif len(ch4_data.shape) == 3:
            # 3D: Extract specific day
            day_data = ch4_data[day_idx, :, :]  # Shape: (lat, lon)
        else:
            raise ValueError(f"Unsupported data shape: {ch4_data.shape}")
        
        # Convert to numpy array (loads into memory - but just one day's data ~180*360 = 64k points)
        day_array = np.array(day_data)
        
        # Create meshgrid for lat/lon
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # Flatten arrays
        lat_flat = lat_grid.flatten()
        lon_flat = lon_grid.flatten()
        ch4_flat = day_array.flatten()
        
        # Filter out invalid/missing data (NaN, fill values)
        valid_mask = ~np.isnan(ch4_flat) & (ch4_flat > 0)
        
        # Build DataFrame in chunks to save memory
        records = []
        valid_indices = np.where(valid_mask)[0]
        
        print(f"  ✓ Valid data points: {len(valid_indices):,} / {len(ch4_flat):,}")
        
        for i in range(0, len(valid_indices), CHUNK_SIZE):
            chunk_indices = valid_indices[i:i + CHUNK_SIZE]
            
            chunk_records = {
                'latitude': lat_flat[chunk_indices],
                'longitude': lon_flat[chunk_indices],
                'ch4_concentration': np.round(ch4_flat[chunk_indices], 4),
                'time_value': np.full(len(chunk_indices), float(times[day_idx])),
                'ch4_units': ch4_units,
                'time_units': time_units,
                'level': level
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
        Convert a single NetCDF file to daily Parquet files.
        
        Downloads NetCDF, extracts data day-by-day, uploads Parquet per day.
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
        self.temp_dir = tempfile.mkdtemp(prefix='netcdf_convert_')
        local_nc_path = os.path.join(self.temp_dir, 'input.nc')
        
        try:
            # Download NetCDF file
            self.download_file(s3_key, local_nc_path)
            
            # Open NetCDF
            dataset = nc.Dataset(local_nc_path, 'r')
            num_days = len(dataset.variables['time'])
            
            print(f"📅 Processing {num_days} days...")
            
            # Process each day
            for day_idx in range(num_days):
                day_num = day_idx + 1
                
                print(f"\n  Day {day_num}/{num_days}")
                
                # Extract day data
                df = self.extract_day_data_chunked(dataset, day_idx, level=0)
                
                if df.empty:
                    print(f"  ⚠️  No valid data for day {day_num}, skipping")
                    continue
                
                # Add date columns
                df['year'] = year
                df['month'] = month
                df['day'] = day_num
                
                # Write to Parquet
                local_parquet_path = os.path.join(self.temp_dir, f'day_{day_num}.parquet')
                df.to_parquet(local_parquet_path, engine='pyarrow', compression='snappy', index=False)
                
                parquet_size_mb = os.path.getsize(local_parquet_path) / (1024 * 1024)
                print(f"  ✓ Created Parquet: {parquet_size_mb:.2f} MB, {len(df):,} rows")
                
                # Upload to S3
                s3_key_target = f"{TARGET_PREFIX}/year={year}/month={month:02d}/day={day_num:02d}/data.parquet"
                
                self.s3_client.upload_file(
                    local_parquet_path,
                    TARGET_BUCKET,
                    s3_key_target
                )
                
                print(f"  ⬆️  Uploaded to s3://{TARGET_BUCKET}/{s3_key_target}")
                
                # Clean up parquet file to save disk space
                os.remove(local_parquet_path)
                
                # Clean up DataFrame to free memory
                del df
            
            dataset.close()
            print(f"\n✅ Successfully processed {num_days} days from {s3_key}")
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
        description='Convert CAMS CH4 NetCDF files from S3 to Parquet format (Athena-ready)'
    )
    
    parser.add_argument('--year', type=int, help='Year to process (if processing single file)')
    parser.add_argument('--month', type=int, help='Month to process (if processing single file)')
    parser.add_argument('--file', type=str, help='Specific S3 key to process (e.g., cds/ch4/file.nc)')
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
    converter = NetCDFToParquetConverter(
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
