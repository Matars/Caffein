"""
Script to seed Sentinel-5P NO2 measurement data into PostgreSQL
Processes JSON files from download_sentinel5p_sweden.py and inserts them into the database
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from dotenv import load_dotenv
import glob

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))
from models import Base, NO2MeasurementSweden
from config.sweden import SWEDEN_BOUNDS, GRID_RESOLUTION, get_grid_cell

# Load environment variables
load_dotenv()

# PostgreSQL configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'caffein')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Construct database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def connect_to_postgresql():
    """Connect to PostgreSQL and return engine and session"""
    print(f"Attempting to connect to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            connect_args={'connect_timeout': 10}
        )

        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        Session = sessionmaker(bind=engine)
        print(f"✓ PostgreSQL connection successful! Database: {DB_NAME}")
        return engine, Session

    except OperationalError as e:
        print(f"❌ PostgreSQL connection failed: {str(e)}")
        print(f"   Make sure PostgreSQL is running at {DB_HOST}:{DB_PORT}")
        print(f"   and database '{DB_NAME}' exists")
        return None, None

    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return None, None


def seed_no2_data(session, data_dir, batch_size=1000):
    """
    Seed NO2 measurement data from JSON files into the database

    Args:
        session: SQLAlchemy session
        data_dir: Directory containing no2_sweden_*.json files
        batch_size: Number of records to insert per batch
    """
    print(f"\n{'='*70}")
    print("Seeding NO2 Measurement Data")
    print(f"{'='*70}")
    print(f"Data directory: {data_dir}")
    print(f"Batch size: {batch_size:,}")

    # Find all NO2 JSON files
    json_files = sorted(glob.glob(os.path.join(data_dir, "no2_sweden_*.json")))

    if not json_files:
        print(f"\n⚠️  No NO2 data files found in {data_dir}")
        print(f"    Expected files matching pattern: no2_sweden_*.json")
        print(f"\n    To download data, run:")
        print(f"    python scripts/download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31")
        return

    print(f"✓ Found {len(json_files)} NO2 data files")

    # Clear existing data (optional - comment out to append instead)
    print("\n⚠️  Clearing existing NO2 data...")
    try:
        count = session.query(NO2MeasurementSweden).delete()
        session.commit()
        print(f"✓ Cleared {count:,} existing records")
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        session.rollback()
        return

    # Process each file
    total_inserted = 0
    total_skipped = 0
    batch = []

    for file_path in json_files:
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if not data:
                print(f"  ⏭️  {filename}: Empty file, skipping")
                continue

            print(f"  📂 {filename}: {len(data):,} measurements")

            # Process each measurement
            for record in data:
                lat = record.get('latitude')
                lon = record.get('longitude')
                date = record.get('date')
                no2_column = record.get('no2_column')
                qa_value = record.get('qa_value')
                cloud_fraction = record.get('cloud_fraction')

                # Validate required fields
                if not all([lat, lon, date, no2_column]):
                    total_skipped += 1
                    continue

                # Parse date
                try:
                    measurement_date = datetime.strptime(date, '%Y-%m-%d').date()
                except ValueError:
                    total_skipped += 1
                    continue

                # Calculate grid indices
                grid_cell = get_grid_cell(lat, lon)
                if grid_cell is None:
                    total_skipped += 1
                    continue

                lat_idx, lon_idx = grid_cell

                # Create measurement object
                measurement = NO2MeasurementSweden(
                    latitude=lat,
                    longitude=lon,
                    measurement_date=measurement_date,
                    no2_column=no2_column,
                    qa_value=qa_value,
                    cloud_fraction=cloud_fraction,
                    grid_lat_idx=lat_idx,
                    grid_lon_idx=lon_idx
                )

                batch.append(measurement)

                # Insert batch when it reaches batch_size
                if len(batch) >= batch_size:
                    try:
                        session.bulk_save_objects(batch)
                        session.commit()
                        total_inserted += len(batch)
                        print(f"    ✓ Inserted {total_inserted:,} measurements so far...")
                        batch = []
                    except SQLAlchemyError as e:
                        print(f"    ❌ Error inserting batch: {e}")
                        session.rollback()
                        batch = []

        except json.JSONDecodeError as e:
            print(f"  ❌ {filename}: Invalid JSON - {e}")
            continue
        except Exception as e:
            print(f"  ❌ {filename}: Error - {e}")
            continue

    # Insert remaining records
    if batch:
        try:
            session.bulk_save_objects(batch)
            session.commit()
            total_inserted += len(batch)
            print(f"    ✓ Inserted final batch")
        except SQLAlchemyError as e:
            print(f"    ❌ Error inserting final batch: {e}")
            session.rollback()

    # Summary
    print(f"\n{'='*70}")
    print("Seeding Summary")
    print(f"{'='*70}")
    print(f"Files processed: {len(json_files)}")
    print(f"Total inserted: {total_inserted:,}")
    print(f"Total skipped: {total_skipped:,}")

    # Verify the data
    print(f"\n{'='*70}")
    print("Database Verification")
    print(f"{'='*70}")

    try:
        total_count = session.query(NO2MeasurementSweden).count()
        print(f"Total records in database: {total_count:,}")

        # Get date range
        min_date = session.query(func.min(NO2MeasurementSweden.measurement_date)).scalar()
        max_date = session.query(func.max(NO2MeasurementSweden.measurement_date)).scalar()

        if min_date and max_date:
            print(f"Date range: {min_date} to {max_date}")

        # Get average NO2 levels
        avg_no2 = session.query(func.avg(NO2MeasurementSweden.no2_column)).scalar()
        if avg_no2:
            print(f"Average NO2 column: {float(avg_no2):.2e} molecules/cm²")

        # Get quality statistics
        avg_qa = session.query(func.avg(NO2MeasurementSweden.qa_value)).scalar()
        avg_cloud = session.query(func.avg(NO2MeasurementSweden.cloud_fraction)).scalar()

        if avg_qa:
            print(f"Average QA value: {float(avg_qa):.3f}")
        if avg_cloud:
            print(f"Average cloud fraction: {float(avg_cloud):.3f}")

        print(f"{'='*70}")
        print("✓ NO2 data seeding completed successfully!")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"❌ Error during verification: {e}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Seed NO2 measurement data into PostgreSQL')
    parser.add_argument('--data-dir', type=str, default='data/sweden/sentinel5p_no2',
                       help='Directory containing NO2 JSON files')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for insertions (default: 1000)')

    args = parser.parse_args()

    # Check if data directory exists
    if not os.path.exists(args.data_dir):
        print(f"❌ Data directory not found: {args.data_dir}")
        print(f"\n   Please create the directory and download NO2 data first:")
        print(f"   mkdir -p {args.data_dir}")
        print(f"   python scripts/download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31 --output {args.data_dir}")
        sys.exit(1)

    # Connect to PostgreSQL
    engine, Session = connect_to_postgresql()
    if not Session:
        sys.exit(1)

    session = Session()

    try:
        # Seed the data
        seed_no2_data(session, args.data_dir, args.batch_size)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        session.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    # Import func for aggregations
    from sqlalchemy import func

    if len(sys.argv) == 1:
        print("=" * 70)
        print("NO2 Measurement Data Seeder")
        print("=" * 70)
        print("\nUsage:")
        print("  python scripts/seed_no2_data.py --data-dir data/sweden/sentinel5p_no2")
        print("\nOptions:")
        print("  --data-dir    Directory with NO2 JSON files (default: data/sweden/sentinel5p_no2)")
        print("  --batch-size  Records per batch insert (default: 1000)")
        print("\nExample:")
        print("  python scripts/seed_no2_data.py --data-dir data/sweden/sentinel5p_no2 --batch-size 2000")
        print("\nBefore running:")
        print("  1. Download NO2 data:")
        print("     python scripts/download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31")
        print("  2. Ensure PostgreSQL is running and database exists")
        print("  3. Run this script")
        print("=" * 70)
    else:
        main()
