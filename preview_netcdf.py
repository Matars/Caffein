#!/usr/bin/env python3
"""
Preview NetCDF (.nc) files - shows metadata, dimensions, variables, and sample data.
Usage: python preview_netcdf.py <path_to_nc_file>
"""

import sys
import netCDF4 as nc
import numpy as np

def preview_netcdf(filepath):
    """Preview a NetCDF file showing its structure and sample data."""
    print(f"\n{'='*80}")
    print(f"NetCDF File Preview: {filepath}")
    print(f"{'='*80}\n")
    
    try:
        # Open the NetCDF file
        dataset = nc.Dataset(filepath, 'r')
        
        # 1. Global Attributes
        print("GLOBAL ATTRIBUTES:")
        print("-" * 80)
        for attr in dataset.ncattrs():
            print(f"  {attr}: {dataset.getncattr(attr)}")
        print()
        
        # 2. Dimensions
        print("DIMENSIONS:")
        print("-" * 80)
        for dim_name, dim in dataset.dimensions.items():
            print(f"  {dim_name}: {len(dim)} {'(unlimited)' if dim.isunlimited() else ''}")
        print()
        
        # 3. Variables
        print("VARIABLES:")
        print("-" * 80)
        for var_name, var in dataset.variables.items():
            print(f"\n  Variable: {var_name}")
            print(f"    Shape: {var.shape}")
            print(f"    Dimensions: {var.dimensions}")
            print(f"    Data Type: {var.dtype}")
            
            # Variable attributes
            if var.ncattrs():
                print(f"    Attributes:")
                for attr in var.ncattrs():
                    print(f"      {attr}: {var.getncattr(attr)}")
            
            # Show sample data (first few values)
            data = var[:]
            if data.size > 0:
                print(f"    Sample data (first 5 values):")
                if len(data.shape) == 1:
                    sample = data[:5] if len(data) > 5 else data
                    print(f"      {sample}")
                elif len(data.shape) == 2:
                    print(f"      {data[0, :5]}")
                elif len(data.shape) == 3:
                    print(f"      {data[0, 0, :5]}")
                else:
                    print(f"      Shape: {data.shape}, Min: {np.nanmin(data)}, Max: {np.nanmax(data)}, Mean: {np.nanmean(data)}")
        
        print()
        
        # 4. Summary Statistics for main data variables
        print("DATA SUMMARY:")
        print("-" * 80)
        for var_name, var in dataset.variables.items():
            # Skip coordinate variables
            if var_name in ['lat', 'lon', 'latitude', 'longitude', 'time', 'x', 'y']:
                continue
            
            data = var[:]
            if data.size > 0:
                print(f"\n  {var_name}:")
                print(f"    Min: {np.nanmin(data):.6f}")
                print(f"    Max: {np.nanmax(data):.6f}")
                print(f"    Mean: {np.nanmean(data):.6f}")
                print(f"    Std Dev: {np.nanstd(data):.6f}")
                print(f"    Valid (non-NaN) values: {np.count_nonzero(~np.isnan(data))}/{data.size}")
        
        print()
        dataset.close()
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"Error reading NetCDF file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preview_netcdf.py <path_to_nc_file>")
        print("\nExample:")
        print("  python preview_netcdf.py MonthlyWetland_CH4_WetCHARTsV2_2346/data/WetCHARTs_v1_3_3_2021.nc")
        sys.exit(1)
    
    preview_netcdf(sys.argv[1])
