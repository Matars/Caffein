"""
MongoDB connection module with async initialization
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os
from dotenv import load_dotenv
import threading
from logger import get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('database')

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_DB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'projectvis_db')

# Global variables
client = None
db = None
connection_status = {
    'connected': False,
    'error': None,
    'attempting': False
}


def init_db():
    """Initialize MongoDB connection asynchronously"""
    global client, db, connection_status

    if connection_status['attempting']:
        return

    connection_status['attempting'] = True

    def connect():
        global client, db, connection_status
        try:
            logger.info(f"Attempting to connect to MongoDB at {MONGO_URI}")
            # Set a timeout so it doesn't hang
            temp_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )

            # Test the connection
            temp_client.admin.command('ping')

            # If successful, set global variables
            client = temp_client
            db = client[DATABASE_NAME]
            connection_status['connected'] = True
            connection_status['error'] = None
            logger.info(
                f"✓ MongoDB connection successful! Database: {DATABASE_NAME}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            connection_status['connected'] = False
            connection_status['error'] = f"Connection timeout: {str(e)}"
            logger.warning(f"MongoDB connection failed: {str(e)}")
            logger.info("Server will continue without database connection")

        except Exception as e:
            connection_status['connected'] = False
            connection_status['error'] = str(e)
            logger.error(f"MongoDB connection error: {str(e)}")
            logger.info("Server will continue without database connection")

        finally:
            connection_status['attempting'] = False

    # Run connection in background thread
    thread = threading.Thread(target=connect, daemon=True)
    thread.start()


def get_db():
    """Get the database instance"""
    return db


def get_connection_status():
    """Get current connection status"""
    return {
        'connected': connection_status['connected'],
        'error': connection_status['error'],
        'attempting': connection_status['attempting']
    }


def close_db():
    """Close the database connection"""
    global client, db, connection_status
    if client:
        client.close()
        client = None
        db = None
        connection_status['connected'] = False
        logger.info("MongoDB connection closed")
        connection_status['connected'] = False
        print("MongoDB connection closed")
