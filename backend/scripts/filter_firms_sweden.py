"""
Filter NASA FIRMS fire detection data to Sweden region only
This reduces the 27GB global dataset to a much smaller Sweden-specific dataset
"""
import json
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.sweden import SWEDEN_BOUNDS, DATA_PATHS, is_in_sweden

def filter_firms_file(input_file, output_file):
    """
    Filter a single FIRMS JSON file to Sweden region

    Args:
        input_file: Path to input FIRMS JSON file
        output_file: Path to output filtered JSON file
    """
    print(f"\nProcessing: {os.path.basename(input_file)}")

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"  ❌ File not found: {input_file}")
        return 0

    try:
        # Load JSON file
        print(f"  📖 Loading... (this may take a while for large files)")
        with open(input_file, 'r') as f:
            data = json.load(f)

        total_records = len(data)
        print(f"  ✓ Loaded {total_records:,} records")

        # Filter to Sweden bounding box
        sweden_records = [
            record for record in data
            if is_in_sweden(record.get('latitude', 0), record.get('longitude', 0))
        ]

        sweden_count = len(sweden_records)
        percentage = (sweden_count / total_records * 100) if total_records > 0 else 0

        print(f"  ✓ Found {sweden_count:,} records in Sweden ({percentage:.2f}%)")

        if sweden_count > 0:
            # Save filtered data
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(sweden_records, f, indent=2)

            # Calculate file sizes
            input_size = os.path.getsize(input_file) / (1024**3)  # GB
            output_size = os.path.getsize(output_file) / (1024**2)  # MB

            print(f"  ✓ Saved to: {os.path.basename(output_file)}")
            print(f"  📊 Size reduction: {input_size:.2f} GB → {output_size:.2f} MB")
        else:
            print(f"  ⚠️  No Sweden data found, skipping save")

        return sweden_count

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Main function to filter all FIRMS files"""
    print("=" * 70)
    print("FIRMS Data Filter - Sweden Region")
    print("=" * 70)
    print(f"\nSweden Bounding Box:")
    print(f"  Latitude:  {SWEDEN_BOUNDS['south']:.2f}° to {SWEDEN_BOUNDS['north']:.2f}°")
    print(f"  Longitude: {SWEDEN_BOUNDS['west']:.2f}° to {SWEDEN_BOUNDS['east']:.2f}°")

    # Find all FIRMS JSON files in data directory
    data_root = Path(__file__).parent.parent.parent / 'data'
    firms_files = list(data_root.glob('fire_*.json'))

    if not firms_files:
        print(f"\n❌ No FIRMS files found in {data_root}")
        print(f"   Looking for files matching: fire_*.json")
        print(f"\n   Make sure your FIRMS data files are in the data/ directory")
        sys.exit(1)

    print(f"\n✓ Found {len(firms_files)} FIRMS files:")
    for f in firms_files:
        size_gb = f.stat().st_size / (1024**3)
        print(f"   - {f.name} ({size_gb:.2f} GB)")

    # Create output directory
    output_dir = Path(DATA_PATHS['firms_sweden']).parent
    os.makedirs(output_dir, exist_ok=True)

    # Process each file
    total_sweden_records = 0

    for firms_file in firms_files:
        # Create output filename
        base_name = firms_file.stem  # e.g., "fire_archive_M-C61_671380"
        output_file = output_dir / f"{base_name}_sweden.json"

        # Filter file
        count = filter_firms_file(str(firms_file), str(output_file))
        total_sweden_records += count

    # Summary
    print(f"\n{'='*70}")
    print(f"Filtering Complete!")
    print(f"{'='*70}")
    print(f"Total Sweden fire detections: {total_sweden_records:,}")
    print(f"Output directory: {output_dir}")
    print(f"\nNext step:")
    print(f"  Load data into database with:")
    print(f"  python scripts/seed_sweden_data.py")
    print(f"{'='*70}")

    # Show file breakdown
    if total_sweden_records > 0:
        print(f"\nSweden Data Files:")
        sweden_files = list(output_dir.glob('*_sweden.json'))
        for f in sweden_files:
            with open(f, 'r') as file:
                count = len(json.load(file))
            size_mb = f.stat().st_size / (1024**2)
            print(f"  - {f.name}: {count:,} records ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
