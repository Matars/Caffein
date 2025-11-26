#!/usr/bin/env python3
"""
Test script to verify S3 NetCDF to Parquet converter setup.
Checks dependencies, AWS credentials, and S3 access.
"""

import sys

def check_dependencies():
    """Check if all required packages are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = {
        'boto3': 'AWS SDK',
        'netCDF4': 'NetCDF file handling',
        'pandas': 'Data processing',
        'pyarrow': 'Parquet format',
        'numpy': 'Array operations'
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package:15} - {description}")
        except ImportError:
            print(f"  ❌ {package:15} - {description} (MISSING)")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"   Install with: pip install -r requirements_s3_converter.txt")
        return False
    
    print("\n✅ All dependencies installed")
    return True


def check_aws_credentials():
    """Check AWS credentials."""
    print("\n🔍 Checking AWS credentials...")
    
    import os
    import boto3
    
    # Check environment variables
    aws_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_region = os.environ.get('AWS_DEFAULT_REGION', 'eu-central-1')
    
    if not aws_key or not aws_secret:
        print("  ❌ AWS credentials not found in environment")
        print("     Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    
    print(f"  ✅ AWS_ACCESS_KEY_ID: {aws_key[:10]}...")
    print(f"  ✅ AWS_SECRET_ACCESS_KEY: ***")
    print(f"  ✅ AWS_DEFAULT_REGION: {aws_region}")
    
    # Test credentials by listing S3 buckets
    try:
        print("\n🔍 Testing AWS connection...")
        s3 = boto3.client('s3', region_name=aws_region)
        response = s3.list_buckets()
        
        print(f"  ✅ Successfully connected to AWS")
        print(f"  ✅ Found {len(response['Buckets'])} S3 buckets")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed to connect to AWS: {str(e)}")
        return False


def check_source_bucket():
    """Check if source bucket and files exist."""
    print("\n🔍 Checking source bucket...")
    
    import boto3
    
    source_bucket = 'caff-dump'
    source_prefix = 'cds/ch4'
    
    try:
        s3 = boto3.client('s3')
        
        # List objects
        response = s3.list_objects_v2(
            Bucket=source_bucket,
            Prefix=source_prefix,
            MaxKeys=10
        )
        
        if 'Contents' not in response:
            print(f"  ⚠️  No files found in s3://{source_bucket}/{source_prefix}/")
            return False
        
        nc_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.nc')]
        
        print(f"  ✅ Bucket accessible: s3://{source_bucket}/{source_prefix}/")
        print(f"  ✅ Found {len(nc_files)} NetCDF files")
        
        if nc_files:
            print(f"\n  📄 Sample files:")
            for obj in nc_files[:3]:
                size_mb = obj['Size'] / (1024 * 1024)
                print(f"     - {obj['Key']} ({size_mb:.1f} MB)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Cannot access source bucket: {str(e)}")
        return False


def check_target_bucket():
    """Check if target bucket is writable."""
    print("\n🔍 Checking target bucket...")
    
    import boto3
    
    target_bucket = 'caffine-analytics-storage-eu-central-1-925314695663'
    target_prefix = 'raw/cds/ch4/test/'
    
    try:
        s3 = boto3.client('s3')
        
        # Try to put a test object
        test_key = f"{target_prefix}_test.txt"
        s3.put_object(
            Bucket=target_bucket,
            Key=test_key,
            Body=b"Test file for converter script"
        )
        
        print(f"  ✅ Bucket writable: s3://{target_bucket}/{target_prefix}")
        
        # Clean up test file
        s3.delete_object(Bucket=target_bucket, Key=test_key)
        print(f"  ✅ Write test successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Cannot write to target bucket: {str(e)}")
        return False


def main():
    """Run all checks."""
    print("="*80)
    print("S3 NetCDF to Parquet Converter - Setup Verification")
    print("="*80)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("AWS Credentials", check_aws_credentials),
        ("Source Bucket", check_source_bucket),
        ("Target Bucket", check_target_bucket)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ {name} check failed: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "="*80)
    print("📊 Summary")
    print("="*80)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {name}")
        if not passed:
            all_passed = False
    
    print("="*80)
    
    if all_passed:
        print("\n🎉 All checks passed! Ready to run converter.")
        print("\nRun: python s3_netcdf_to_parquet.py --process-all")
    else:
        print("\n⚠️  Some checks failed. Fix issues before running converter.")
        sys.exit(1)


if __name__ == '__main__':
    main()
