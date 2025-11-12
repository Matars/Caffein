"""
Script to seed fire occurrences data from CSV into MongoDB
Self-contained script without external imports from backend modules
"""
import time
import pandas as pd
import sys
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_DB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'projectvis_db')


def connect_to_mongodb():
    """Connect to MongoDB and return client and database"""
    print(f"Attempting to connect to MongoDB at {MONGO_URI}")
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        # Test the connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        print(f"✓ MongoDB connection successful! Database: {DATABASE_NAME}")
        return client, db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        return None, None
    except Exception as e:
        print(f"❌ MongoDB connection error: {str(e)}")
        return None, None


def load_fire_data():
    """Load fire occurrence data from CSV file"""
    csv_path = Path(__file__).parent.parent.parent / 'data' / \
        'kaggle_raw' / 'fire-occurence.csv'

    if not csv_path.exists():
        print(f"❌ CSV file not found at: {csv_path}")
        return None

    try:
        print(f"Reading CSV from: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} records from CSV")

        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        return data
    except Exception as e:
        print(f"❌ Error reading CSV: {str(e)}")
        return None


def seed_fire_occurrences(db, data):
    """Seed fire occurrences data into the database"""
    if db is None:
        print("❌ Database not connected. Cannot seed data.")
        return False

    try:
        collection = db.fire_occurrences
        if isinstance(data, list) and data:
            # Clear existing data first (optional)
            existing_count = collection.count_documents({})
            if existing_count > 0:
                print(
                    f"⚠️  Found {existing_count} existing records. Clearing collection...")
                collection.delete_many({})

            # Insert new data
            result = collection.insert_many(data)
            print(
                f"✓ Inserted {len(result.inserted_ids)} fire occurrence records.")
            return True
        else:
            print("⚠️  No data provided to seed.")
            return False
    except Exception as e:
        print(f"❌ Error seeding fire occurrences: {str(e)}")
        return False


def main():
    """Main function to seed the database"""
    print("=" * 60)
    print("Starting fire occurrences seeding process...")
    print("=" * 60)

    # Connect to MongoDB
    print("\n[1/3] Connecting to MongoDB...")
    client, db = connect_to_mongodb()

    if db is None:
        print("\n❌ Failed to connect to database. Exiting.")
        sys.exit(1)

    # Load data from CSV
    print("\n[2/3] Loading fire data from CSV...")
    data = load_fire_data()
    if data is None:
        print("\n❌ Failed to load fire data from CSV. Exiting.")
        if client:
            client.close()
        sys.exit(1)

    # Seed the database
    print(
        f"\n[3/3] Seeding {len(data)} fire occurrence records to database...")
    success = seed_fire_occurrences(db, data)

    # Close connection
    if client:
        client.close()
        print("\n✓ Database connection closed.")

    if success:
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
