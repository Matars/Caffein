"""
Script to seed NASA FIRMS fire detection data from JSON files into PostgreSQL
Processes large JSON files efficiently with streaming and batch inserts
Uses ijson for memory-efficient streaming of large JSON files
"""
from models import Base, FireDetection, Message
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from dotenv import load_dotenv
import ijson
import concurrent.futures

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    print(
        f"Attempting to connect to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
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
        return None, None
    except Exception as e:
        print(f"❌ PostgreSQL connection error: {str(e)}")
        return None, None


def find_json_files():
    """Find all FIRMS JSON files in the data directory"""
    # Try Docker mount path first, then relative path
    data_dir = Path('/data')
    if not data_dir.exists():
        data_dir = Path(__file__).parent.parent.parent / 'data'

    if not data_dir.exists():
        print(f"❌ Data directory not found at: {data_dir}")
        return []

    # Find all JSON files that match FIRMS naming pattern
    json_files = list(data_dir.glob('fire_*.json'))

    if not json_files:
        print(f"❌ No FIRMS JSON files found in: {data_dir}")
        return []

    print(f"✓ Found {len(json_files)} JSON files:")
    for f in json_files:
        size_gb = f.stat().st_size / (1024**3)
        print(f"  - {f.name} ({size_gb:.2f} GB)")

    return json_files


def process_single_file(json_file, batch_size=5000, limit_per_file=None):
    """Process a single JSON file and insert records into DB"""
    # Create a new engine and session for this thread
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 10}
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f"\n📁 Processing: {json_file.name} (Thread: {json_file.name})")

        inserted = 0
        skipped = 0

        # Use streaming JSON parser to avoid loading entire file into memory
        with open(json_file, 'rb') as f:
            records_stream = ijson.items(f, 'item')

            batch_records = []
            records_processed = 0

            for record in records_stream:
                # Check limit
                if limit_per_file and records_processed >= limit_per_file:
                    print(
                        f"  ⚠️  Reached limit of {limit_per_file:,} records for {json_file.name}")
                    break

                # Skip records with invalid coordinates
                if not record.get('latitude') or not record.get('longitude'):
                    skipped += 1
                    continue

                # Parse acquisition date
                try:
                    acq_date = datetime.strptime(
                        record['acq_date'], '%Y-%m-%d').date()
                except:
                    skipped += 1
                    continue

                detection = FireDetection(
                    latitude=float(record['latitude']),
                    longitude=float(record['longitude']),
                    acq_date=acq_date,
                    acq_time=record.get('acq_time'),
                    confidence=str(record.get('confidence')) if record.get(
                        'confidence') else None,
                    frp=float(record['frp']) if record.get('frp') else None,
                    brightness=float(record['brightness']) if record.get(
                        'brightness') else None,
                    bright_t31=float(record.get('bright_t31')) if record.get(
                        'bright_t31') else None,
                    instrument=record.get('instrument'),
                    satellite=record.get('satellite'),
                    version=record.get('version'),
                    daynight=record.get('daynight'),
                    type=str(record.get('type')) if record.get(
                        'type') else None,
                    scan=float(record.get('scan')) if record.get(
                        'scan') else None,
                    track=float(record.get('track')) if record.get(
                        'track') else None
                )
                batch_records.append(detection)
                records_processed += 1

                # Commit batch when it reaches batch_size
                if len(batch_records) >= batch_size:
                    session.bulk_save_objects(batch_records)
                    session.commit()
                    inserted += len(batch_records)
                    print(
                        f"    Progress {json_file.name}: {inserted:,} records inserted")
                    batch_records = []

            # Commit remaining records
            if batch_records:
                session.bulk_save_objects(batch_records)
                session.commit()
                inserted += len(batch_records)
                print(
                    f"    Progress {json_file.name}: {inserted:,} records inserted")

            print(
                f"  ✓ Completed {json_file.name}: {records_processed:,} records processed, {inserted:,} inserted, {skipped:,} skipped")

        session.close()
        engine.dispose()
        return True, inserted, skipped

    except Exception as e:
        session.rollback()
        session.close()
        engine.dispose()
        print(f"  ❌ Error processing {json_file.name}: {str(e)}")
        return False, 0, 0


def seed_fire_detections(session, json_files, batch_size=5000, limit_per_file=None):
    """Seed fire detection data from JSON files into PostgreSQL using multithreading"""
    if session is None or not json_files:
        print("❌ Session or data files not available. Cannot seed data.")
        return False

    try:
        # Check existing data and clear table
        existing_count = session.query(FireDetection).count()
        if existing_count > 0:
            print(
                f"⚠️  Found {existing_count:,} existing records. Clearing table...")
            session.query(FireDetection).delete()
            session.commit()

        total_inserted = 0
        total_skipped = 0
        total_success = True

        # Use ThreadPoolExecutor to process files concurrently
        max_workers = min(len(json_files), 4)  # Limit to 4 threads max
        print(
            f"\n🚀 Starting multithreaded processing with {max_workers} threads...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file processing tasks
            future_to_file = {
                executor.submit(process_single_file, json_file, batch_size, limit_per_file): json_file
                for json_file in json_files
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                json_file = future_to_file[future]
                try:
                    success, inserted, skipped = future.result()
                    total_inserted += inserted
                    total_skipped += skipped
                    if not success:
                        total_success = False
                except Exception as e:
                    print(
                        f"  ❌ Thread for {json_file.name} raised exception: {str(e)}")
                    total_success = False

        print(f"\n✓ Total inserted {total_inserted:,} fire detection records.")
        if total_skipped > 0:
            print(
                f"  ⚠️  Total skipped {total_skipped:,} records (invalid data)")
        return total_success

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding fire detections: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def seed_default_message(session):
    """Seed default message into the messages table"""
    try:
        # Check if message exists
        existing = session.query(Message).filter_by(type='hello').first()
        if existing:
            print("⚠️  Default message already exists. Skipping.")
            return True

        # Insert default message
        message = Message(
            type='hello',
            content='Hello from Caffein - NASA FIRMS Fire Detection System!'
        )
        session.add(message)
        session.commit()
        print("✓ Inserted default message.")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding message: {str(e)}")
        return False


def main():
    """Main function to seed the database"""
    print("=" * 70)
    print("NASA FIRMS Fire Detection Data Seeding Script")
    print("=" * 70)

    # Parse command line arguments
    limit_per_file = None
    if len(sys.argv) > 1:
        try:
            limit_per_file = int(sys.argv[1])
            print(
                f"\n⚠️  LIMIT MODE: Will load max {limit_per_file:,} records per file")
        except ValueError:
            print(f"\n⚠️  Invalid limit argument, ignoring: {sys.argv[1]}")

    # Connect to PostgreSQL
    print("\n[1/5] Connecting to PostgreSQL...")
    engine, Session = connect_to_postgresql()

    if engine is None:
        print("\n❌ Failed to connect to database. Exiting.")
        sys.exit(1)

    # Create tables if they don't exist
    print("\n[2/5] Creating tables if they don't exist...")
    try:
        Base.metadata.create_all(engine)
        print("✓ Tables created/verified successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        sys.exit(1)

    # Find JSON files
    print("\n[3/5] Finding JSON data files...")
    json_files = find_json_files()
    if not json_files:
        print("\n❌ No data files found. Exiting.")
        sys.exit(1)

    # Seed the database
    session = Session()

    print(f"\n[4/5] Seeding database...")
    print("\n  → Seeding fire detections...")
    fire_success = seed_fire_detections(
        session, json_files, limit_per_file=limit_per_file)

    print("\n  → Seeding default message...")
    message_success = seed_default_message(session)

    # Close session
    session.close()
    engine.dispose()
    print("\n[5/5] Database connection closed.")

    if fire_success and message_success:
        print("\n" + "=" * 70)
        print("✓ Seeding completed successfully!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ Seeding failed!")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
