"""
Download Sentinel-5P NO2 data for Sweden using Google Earth Engine
"""
import ee
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.sweden import SWEDEN_BOUNDS, DATA_PATHS

def initialize_earth_engine():
    """Initialize Google Earth Engine"""
    try:
        ee.Initialize()
        print("✓ Earth Engine initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Earth Engine initialization failed: {e}")
        print("\nPlease run: earthengine authenticate")
        return False

def get_sweden_geometry():
    """Create Earth Engine geometry for Sweden bounding box"""
    return ee.Geometry.Rectangle([
        SWEDEN_BOUNDS['west'],
        SWEDEN_BOUNDS['south'],
        SWEDEN_BOUNDS['east'],
        SWEDEN_BOUNDS['north']
    ])

def download_no2_data(start_date, end_date, output_dir):
    """
    Download Sentinel-5P NO2 data for Sweden

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Directory to save data
    """
    print(f"\n{'='*70}")
    print(f"Downloading Sentinel-5P NO2 Data for Sweden")
    print(f"{'='*70}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Output: {output_dir}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get Sweden geometry
    sweden = get_sweden_geometry()

    # Load Sentinel-5P NO2 collection
    collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2') \
        .filterDate(start_date, end_date) \
        .filterBounds(sweden) \
        .select(['tropospheric_NO2_column_number_density',
                 'NO2_column_number_density',
                 'tropospheric_NO2_column_number_density_amf',
                 'qa_value',
                 'cloud_fraction'])

    # Get collection size
    count = collection.size().getInfo()
    print(f"\n✓ Found {count} Sentinel-5P images")

    if count == 0:
        print("⚠️  No data found for this date range")
        return

    # Get list of dates
    def get_date(image):
        return ee.Feature(None, {'date': image.date().format('YYYY-MM-dd')})

    dates = collection.map(get_date).aggregate_array('date').getInfo()
    unique_dates = sorted(set(dates))

    print(f"✓ Unique dates: {len(unique_dates)}")
    print(f"  First: {unique_dates[0]}")
    print(f"  Last: {unique_dates[-1]}")

    # Download data for each date
    downloaded = 0
    skipped = 0
    errors = 0

    for date in unique_dates:
        try:
            output_file = os.path.join(output_dir, f"no2_sweden_{date}.json")

            # Skip if already exists
            if os.path.exists(output_file):
                skipped += 1
                print(f"  ⏭️  Skipping {date} (already exists)")
                continue

            # Get images for this date
            daily_images = collection.filterDate(date,
                                                 (datetime.strptime(date, '%Y-%m-%d') +
                                                  timedelta(days=1)).strftime('%Y-%m-%d'))

            # Use median if multiple images per day
            if daily_images.size().getInfo() > 1:
                image = daily_images.median()
            else:
                image = daily_images.first()

            # Sample the image over Sweden
            # Use a grid of points for manageable file size
            grid_spacing = 0.1  # degrees (~11 km)
            lats = []
            lons = []

            lat = SWEDEN_BOUNDS['south']
            while lat <= SWEDEN_BOUNDS['north']:
                lon = SWEDEN_BOUNDS['west']
                while lon <= SWEDEN_BOUNDS['east']:
                    lats.append(lat)
                    lons.append(lon)
                    lon += grid_spacing
                lat += grid_spacing

            # Create points
            points = [ee.Geometry.Point([lon, lat]) for lon, lat in zip(lons, lats)]
            points_fc = ee.FeatureCollection(points)

            # Sample the image
            sampled = image.sampleRegions(
                collection=points_fc,
                scale=7000,  # Sentinel-5P native resolution
                geometries=True
            )

            # Convert to list
            data_list = sampled.getInfo()['features']

            # Filter out bad quality data
            filtered_data = []
            for feature in data_list:
                props = feature['properties']
                coords = feature['geometry']['coordinates']

                # Quality filters
                qa = props.get('qa_value', 0)
                cloud_frac = props.get('cloud_fraction', 1)
                no2_value = props.get('tropospheric_NO2_column_number_density')

                # Skip if low quality or cloudy
                if qa < 0.5 or cloud_frac > 0.3 or no2_value is None:
                    continue

                filtered_data.append({
                    'latitude': coords[1],
                    'longitude': coords[0],
                    'date': date,
                    'no2_column': no2_value,
                    'qa_value': qa,
                    'cloud_fraction': cloud_frac
                })

            # Save to JSON
            if filtered_data:
                with open(output_file, 'w') as f:
                    json.dump(filtered_data, f, indent=2)

                downloaded += 1
                print(f"  ✓ {date}: {len(filtered_data)} measurements saved")
            else:
                errors += 1
                print(f"  ⚠️  {date}: No valid data (clouds or low quality)")

        except Exception as e:
            errors += 1
            print(f"  ❌ {date}: Error - {str(e)}")

    # Summary
    print(f"\n{'='*70}")
    print(f"Download Summary:")
    print(f"  Downloaded: {downloaded} days")
    print(f"  Skipped: {skipped} days (already existed)")
    print(f"  Errors: {errors} days")
    print(f"{'='*70}")

    # Estimate file sizes
    if downloaded > 0:
        total_size = sum(os.path.getsize(os.path.join(output_dir, f))
                        for f in os.listdir(output_dir) if f.endswith('.json'))
        avg_size = total_size / len(os.listdir(output_dir))
        print(f"\nFile Statistics:")
        print(f"  Total size: {total_size / 1024 / 1024:.2f} MB")
        print(f"  Average per day: {avg_size / 1024:.2f} KB")

def main():
    parser = argparse.ArgumentParser(description='Download Sentinel-5P NO2 data for Sweden')
    parser.add_argument('--start', type=str, required=True,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', type=str,
                       default=DATA_PATHS['sentinel5p_sweden'],
                       help='Output directory')

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start, '%Y-%m-%d')
        datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    # Initialize Earth Engine
    if not initialize_earth_engine():
        sys.exit(1)

    # Download data
    download_no2_data(args.start, args.end, args.output)

if __name__ == "__main__":
    # Example usage if run without arguments
    if len(sys.argv) == 1:
        print("=" * 70)
        print("Sentinel-5P NO2 Data Downloader for Sweden")
        print("=" * 70)
        print("\nUsage:")
        print("  python download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31")
        print("\nOptions:")
        print("  --start    Start date (YYYY-MM-DD) [required]")
        print("  --end      End date (YYYY-MM-DD) [required]")
        print("  --output   Output directory [optional]")
        print("\nExample:")
        print("  # Download July 2024 data")
        print("  python download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31")
        print("\nBefore running:")
        print("  1. Install: pip install earthengine-api")
        print("  2. Authenticate: earthengine authenticate")
        print("  3. Run this script")
        print("=" * 70)
    else:
        main()
