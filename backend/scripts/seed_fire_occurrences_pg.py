"""
Script to seed fire occurrences data from CSV into PostgreSQL
Reads directly from the CSV file and populates the PostgreSQL database
"""
import pandas as pd
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from dotenv import load_dotenv

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))
from models import Base, FireOccurrence, Message

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
        return None, None
    except Exception as e:
        print(f"❌ PostgreSQL connection error: {str(e)}")
        return None, None


def load_fire_data():
    """Load fire occurrence data from CSV file"""
    # Try Docker mount path first, then relative path
    csv_path = Path('/data/kaggle_raw/fire-occurence.csv')
    if not csv_path.exists():
        csv_path = Path(__file__).parent.parent.parent / 'data' / \
            'kaggle_raw' / 'fire-occurence.csv'

    if not csv_path.exists():
        print(f"❌ CSV file not found at: {csv_path}")
        return None

    try:
        print(f"Reading CSV from: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} records from CSV")

        # Print column names for debugging
        print(f"CSV columns: {list(df.columns)}")

        return df
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return None


def seed_fire_occurrences(session, df):
    """Seed fire occurrences data into PostgreSQL"""
    if session is None or df is None:
        print("❌ Session or data not available. Cannot seed data.")
        return False

    try:
        # Check existing data
        existing_count = session.query(FireOccurrence).count()
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing records. Clearing table...")
            session.query(FireOccurrence).delete()
            session.commit()

        # Insert new data in batches
        batch_size = 1000
        total_inserted = 0
        total_records = len(df)

        print(f"Inserting {total_records} records in batches of {batch_size}...")

        for i in range(0, total_records, batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_records = []

            for _, row in batch_df.iterrows():
                # Skip records with invalid coordinates
                if pd.isna(row.get('Lat_DD')) or pd.isna(row.get('Long_DD')):
                    continue

                fire = FireOccurrence(
                    fire_name=str(row.get('FireName')) if pd.notna(row.get('FireName')) else None,
                    fire_year=int(row.get('FireYear')) if pd.notna(row.get('FireYear')) else None,
                    lat_dd=float(row.get('Lat_DD')),
                    long_dd=float(row.get('Long_DD')),
                    est_total_acres=float(row.get('EstTotalAcres')) if pd.notna(row.get('EstTotalAcres')) else None,
                    human_or_lightning=str(row.get('HumanOrLightning')) if pd.notna(row.get('HumanOrLightning')) else None,
                    fire_category=str(row.get('FireCategory')) if pd.notna(row.get('FireCategory')) else None,
                    size_class=str(row.get('Size_class')) if pd.notna(row.get('Size_class')) else None,
                    county=str(row.get('County')) if pd.notna(row.get('County')) else None
                )
                batch_records.append(fire)

            if batch_records:
                session.bulk_save_objects(batch_records)
                session.commit()
                total_inserted += len(batch_records)
                print(f"  Progress: {total_inserted}/{total_records} records ({(total_inserted/total_records)*100:.1f}%)")

        print(f"✓ Inserted {total_inserted} fire occurrence records.")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding fire occurrences: {str(e)}")
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
            content='Hello World from Flask backend with PostgreSQL!'
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
    print("=" * 60)
    print("PostgreSQL Fire Occurrences Seeding Script")
    print("=" * 60)

    # Connect to PostgreSQL
    print("\n[1/4] Connecting to PostgreSQL...")
    engine, Session = connect_to_postgresql()

    if engine is None:
        print("\n❌ Failed to connect to database. Exiting.")
        sys.exit(1)

    # Create tables if they don't exist
    print("\n[2/4] Creating tables if they don't exist...")
    try:
        Base.metadata.create_all(engine)
        print("✓ Tables created/verified successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        sys.exit(1)

    # Load data from CSV
    print("\n[3/4] Loading fire data from CSV...")
    df = load_fire_data()
    if df is None:
        print("\n❌ Failed to load fire data from CSV. Exiting.")
        sys.exit(1)

    # Seed the database
    session = Session()

    print(f"\n[4/4] Seeding database...")
    print("\n  → Seeding fire occurrences...")
    fire_success = seed_fire_occurrences(session, df)

    print("\n  → Seeding default message...")
    message_success = seed_default_message(session)

    # Close session
    session.close()
    engine.dispose()
    print("\n✓ Database connection closed.")

    if fire_success and message_success:
        print("\n" + "=" * 60)
        print("✓ Seeding completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Seeding failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
