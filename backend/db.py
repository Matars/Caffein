"""
PostgreSQL connection module with SQLAlchemy
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import os
from dotenv import load_dotenv
import threading
from logger import get_logger
from models import Base

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('database')

# PostgreSQL configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'caffein')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Construct database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Global variables
engine = None
SessionLocal = None
connection_status = {
    'connected': False,
    'error': None,
    'attempting': False
}


def init_db():
    """Initialize PostgreSQL connection asynchronously"""
    global engine, SessionLocal, connection_status

    if connection_status['attempting']:
        return

    connection_status['attempting'] = True

    def connect():
        global engine, SessionLocal, connection_status
        try:
            logger.info(f"Attempting to connect to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")

            # Create engine with connection pool settings
            temp_engine = create_engine(
                DATABASE_URL,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,  # Verify connections before using
                connect_args={'connect_timeout': 5}
            )

            # Test the connection
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # If successful, set global variables
            engine = temp_engine
            SessionLocal = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            ))

            connection_status['connected'] = True
            connection_status['error'] = None
            logger.info(f"✓ PostgreSQL connection successful! Database: {DB_NAME}")

        except OperationalError as e:
            connection_status['connected'] = False
            connection_status['error'] = f"Connection failed: {str(e)}"
            logger.warning(f"PostgreSQL connection failed: {str(e)}")
            logger.info("Server will continue without database connection")

        except Exception as e:
            connection_status['connected'] = False
            connection_status['error'] = str(e)
            logger.error(f"PostgreSQL connection error: {str(e)}")
            logger.info("Server will continue without database connection")

        finally:
            connection_status['attempting'] = False

    # Run connection in background thread
    thread = threading.Thread(target=connect, daemon=True)
    thread.start()


def get_db():
    """Get a database session"""
    if SessionLocal is None:
        return None
    return SessionLocal()


def get_connection_status():
    """Get current connection status"""
    return {
        'connected': connection_status['connected'],
        'error': connection_status['error'],
        'attempting': connection_status['attempting']
    }


def close_db():
    """Close the database connection"""
    global engine, SessionLocal, connection_status
    if SessionLocal:
        SessionLocal.remove()
    if engine:
        engine.dispose()
        engine = None
        SessionLocal = None
        connection_status['connected'] = False
        logger.info("PostgreSQL connection closed")
