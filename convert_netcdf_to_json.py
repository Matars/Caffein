#!/usr/bin/env python3
"""
Convert NetCDF (.nc) files to JSON format.
Extracts CH4 data with coordinates and saves to JSON file.

Usage: python convert_netcdf_to_json.py <input.nc> [--output output.json] [--limit N] [--level L]
"""

import sys
import argparse
import netCDF4 as nc
import json
import numpy as np
from pathlib import Path

def convert_netcdf_to_json(input_file, output_file=None, limit=None, level=0):
    """
    Convert NetCDF file to JSON format.
    
    Args:
        input_file: Path to input .nc file
        output_file: Path to output .json file (auto-generated if None)
        limit: Maximum number of data points to extract (None = all)
        level: Vertical level to extract (0 = surface/first level)
    """
    print(f"Reading NetCDF file: {input_file}")
    
    # Open the NetCDF file
    dataset = nc.Dataset(input_file, 'r')
    
    # Auto-generate output filename if not provided
    if output_file is None:
        output_file = Path(input_file).stem + '.json'
    
    print(f"Output file: {output_file}")
    
    # Get variables
    lons = dataset.variables['longitude'][:] if 'longitude' in dataset.variables else dataset.variables['lon'][:]
    lats = dataset.variables['latitude'][:] if 'latitude' in dataset.variables else dataset.variables['lat'][:]
    times = dataset.variables['time'][:]
    
    # Find CH4 variable (might have different names)
    ch4_var_name = None
    for var in ['CH4', 'ch4', 'methane', 'CH4_concentration']:
        if var in dataset.variables:
            ch4_var_name = var
            break
    
    if ch4_var_name is None:
        print("ERROR: Could not find CH4 variable in NetCDF file")
        print(f"Available variables: {list(dataset.variables.keys())}")
        dataset.close()
        sys.exit(1)
    
    ch4_data = dataset.variables[ch4_var_name]
    
    # Get metadata
    ch4_units = ch4_data.units if hasattr(ch4_data, 'units') else 'unknown'
    time_units = dataset.variables['time'].units if hasattr(dataset.variables['time'], 'units') else 'unknown'
    
    print(f"Found CH4 variable: {ch4_var_name}")
    print(f"CH4 units: {ch4_units}")
    
    # Store shape before iterating
    data_shape = ch4_data.shape
    print(f"Data shape: {data_shape}")
    print(f"Extracting level: {level}")
    
    # Extract data points
    data_points = []
    count = 0
    
    # Determine data dimensions
    if len(data_shape) == 4:  # (time, level, lat, lon)
        print("4D data detected: (time, level, lat, lon)")
        for time_idx in range(len(times)):
            for lat_idx in range(len(lats)):
                for lon_idx in range(len(lons)):
                    value = float(ch4_data[time_idx, level, lat_idx, lon_idx])
                    
                    # Skip fill/missing values
                    if np.isnan(value) or value < 0 or value > 10000:
                        continue
                    
                    data_points.append({
                        "day": int(time_idx + 1),
                        "time_value": float(times[time_idx]),
                        "time_units": time_units,
                        "latitude": round(float(lats[lat_idx]), 4),
                        "longitude": round(float(lons[lon_idx]), 4),
                        "ch4_concentration": round(value, 4),
                        "unit": ch4_units,
                        "level": level
                    })
                    count += 1
                    
                    if limit and count >= limit:
                        break
                if limit and count >= limit:
                    break
            if limit and count >= limit:
                break
    
    elif len(data_shape) == 3:  # (time, lat, lon)
        print("3D data detected: (time, lat, lon)")
        for time_idx in range(len(times)):
            for lat_idx in range(len(lats)):
                for lon_idx in range(len(lons)):
                    value = float(ch4_data[time_idx, lat_idx, lon_idx])
                    
                    # Skip fill/missing values
                    if np.isnan(value) or value < 0 or value > 10000:
                        continue
                    
                    data_points.append({
                        "day": int(time_idx + 1),
                        "time_value": float(times[time_idx]),
                        "time_units": time_units,
                        "latitude": round(float(lats[lat_idx]), 4),
                        "longitude": round(float(lons[lon_idx]), 4),
                        "ch4_concentration": round(value, 4),
                        "unit": ch4_units
                    })
                    count += 1
                    
                    if limit and count >= limit:
                        break
                if limit and count >= limit:
                    break
            if limit and count >= limit:
                break
    
    else:
        print(f"ERROR: Unsupported data shape: {data_shape}")
        dataset.close()
        sys.exit(1)
    
    dataset.close()
    
    # Create output JSON
    output_data = {
        "source_file": str(input_file),
        "variable": ch4_var_name,
        "total_points": count,
        "metadata": {
            "units": ch4_units,
            "time_units": time_units,
            "level_extracted": level if len(data_shape) == 4 else None
        },
        "data": data_points
    }
    
    # Write to JSON file
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Successfully converted {count} data points to {output_file}")
    print(f"  First point: {data_points[0] if data_points else 'No data'}")
    print(f"  Last point: {data_points[-1] if data_points else 'No data'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert NetCDF files to JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert first 3 data points
  python convert_netcdf_to_json.py input.nc --limit 3
  
  # Convert all data from surface level
  python convert_netcdf_to_json.py input.nc
  
  # Convert specific level and save to custom output
  python convert_netcdf_to_json.py input.nc --output custom.json --level 5
  
  # Convert first 100 points from level 0
  python convert_netcdf_to_json.py input.nc --limit 100 --level 0
        """
    )
    
    parser.add_argument('input_file', help='Input NetCDF (.nc) file')
    parser.add_argument('--output', '-o', help='Output JSON file (default: auto-generated from input filename)')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of data points (default: all)')
    parser.add_argument('--level', type=int, default=0, help='Vertical level to extract for 4D data (default: 0 = surface)')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input_file).exists():
        print(f"ERROR: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Convert
    convert_netcdf_to_json(args.input_file, args.output, args.limit, args.level)
