import sys
import netCDF4 as nc
import numpy as np

def safe_sample(var, max_items=5):
    """Safely sample data from a variable without loading the entire array."""
    shape = var.shape
    if len(shape) == 0:  # scalar variable
        try:
            value = var.getValue()
            return f"      Scalar value: {value}"
        except Exception as e:
            return f"      Error reading value: {e}"
    try:
        if len(shape) == 1:
            sample = var[:max_items] if shape[0] >= max_items else var[:]
            return f"      {sample}"
        elif len(shape) == 2:
            sample = var[0,:max_items] if shape[1] >= max_items else var[0,:]
            return f"      {sample}"
        elif len(shape) == 3:
            sample = var[0,0,:max_items] if shape[2] >= max_items else var[0,0,:]
            return f"      {sample}"
        else:
            return f"      Shape: {shape} (too high dim; showing no sample)"
    except Exception as e:
        return f"      Error sampling data: {e}"

def preview_netcdf(filepath):
    print(f"\n{'='*80}")
    print(f"NetCDF File Preview: {filepath}")
    print(f"{'='*80}\n")
    
    try:
        dataset = nc.Dataset(filepath, 'r')

        print("GLOBAL ATTRIBUTES:")
        print("-" * 80)
        for attr in dataset.ncattrs():
            print(f"  {attr}: {dataset.getncattr(attr)}")
        print()

        print("DIMENSIONS:")
        print("-" * 80)
        for dim_name, dim in dataset.dimensions.items():
            print(f"  {dim_name}: {len(dim)} {'(unlimited)' if dim.isunlimited() else ''}")
        print()

        print("VARIABLES:")
        print("-" * 80)
        for var_name, var in dataset.variables.items():
            print(f"\n  Variable: {var_name}")
            print(f"    Shape: {var.shape}")
            print(f"    Dimensions: {var.dimensions}")
            print(f"    Data Type: {var.dtype}")
            if var.ncattrs():
                print(f"    Attributes:")
                for attr in var.ncattrs():
                    print(f"      {attr}: {var.getncattr(attr)}")
            # Only sample a small portion!
            sample_str = safe_sample(var)
            print(f"    Sample data (preview):")
            print(sample_str)
        
        print()
        print("DATA SUMMARY (quick stats for small variables):")
        print("-" * 80)
        for var_name, var in dataset.variables.items():
            # Only do stats for small variables (e.g., coordinate variables)
            if var_name in ['lat', 'lon', 'latitude', 'longitude', 'time', 'x', 'y']:
                try:
                    data = var[:]
                    print(f"\n  {var_name}:")
                    print(f"    Min: {np.nanmin(data):.6f}")
                    print(f"    Max: {np.nanmax(data):.6f}")
                    print(f"    Mean: {np.nanmean(data):.6f}")
                    print(f"    Std Dev: {np.nanstd(data):.6f}")
                    print(f"    Valid (non-NaN) values: {np.count_nonzero(~np.isnan(data))}/{data.size}")
                except Exception as e:
                    print(f"    Could not read data: {e}")
        
        print()
        dataset.close()
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"Error reading NetCDF file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preview_netcdf.py <path_to_nc_file>")
        sys.exit(1)
    preview_netcdf(sys.argv[1])
