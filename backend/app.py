from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from db import init_db, get_db, get_connection_status, close_db
from logger import get_logger
import atexit
import math

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('api')

app = Flask(__name__)
CORS(app)

# Initialize MongoDB connection asynchronously (non-blocking)
logger.info("Starting Flask server...")
init_db()
logger.info("MongoDB connection initializing in background...")

# Cleanup on exit
atexit.register(close_db)


@app.route('/api/hello', methods=['GET'])
def hello():
    """Hello world endpoint that returns a message from the database or default"""
    db = get_db()
    try:
        if db is not None:
            # Try to get message from database
            messages_collection = db.messages
            message_doc = messages_collection.find_one({'type': 'hello'})

            if message_doc:
                message = message_doc['content']
                logger.debug("Retrieved message from database")
            else:
                # Insert default message if not exists
                default_message = {
                    'type': 'hello',
                    'content': 'Hello World from Flask backend with MongoDB!'
                }
                messages_collection.insert_one(default_message)
                message = default_message['content']
                logger.info("Inserted default message into database")
        else:
            message = 'Hello World from Flask backend (MongoDB not connected)'
            logger.warning("Database not connected, using default message")

        return jsonify({
            'message': message,
            'status': 'success',
            'database_connected': db is not None
        })
    except Exception as e:
        logger.error(f"Error in /api/hello endpoint: {str(e)}")
        return jsonify({
            'message': 'Hello World from Flask backend (error occurred)',
            'status': 'error',
            'error': str(e),
            'database_connected': False
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    status = get_connection_status()
    logger.debug(f"Health check: DB connected={status['connected']}")

    return jsonify({
        'status': 'healthy',
        'database_connected': status['connected'],
        'database_connecting': status['attempting'],
        'database_error': status['error']
    })


@app.route('/api/fires', methods=['GET'])
def get_fires():
    """Get fire occurrences with coordinates for mapping"""
    try:
        db = get_db()
        if db is None:
            logger.warning("Database not connected")
            return jsonify({
                'error': 'Database not connected',
                'status': 'error'
            }), 503

        # Query fires with only necessary fields for mapping
        fires = list(db.fire_occurrences.find(
            {},
            {
                '_id': 0,
                'Lat_DD': 1,
                'Long_DD': 1,
                'FireName': 1,
                'FireYear': 1,
                'EstTotalAcres': 1,
                'HumanOrLightning': 1,
                'FireCategory': 1,
                'Size_class': 1,
                'County': 1
            }
        ).limit(100))  # Limit to 1k records for performance

        # Check if collection is empty
        if len(fires) == 0:
            logger.warning(
                "No fire records found in database. Run seed script first.")
            return jsonify({
                'data': [],
                'count': 0,
                'status': 'success',
                'message': 'No data found. Please run the seed script to populate the database.'
            })

        # Clean the data - remove NaN, Infinity, and None values
        cleaned_fires = []
        for fire in fires:
            # Check if coordinates are valid numbers
            lat = fire.get('Lat_DD')
            lon = fire.get('Long_DD')

            # Skip fires with invalid coordinates
            if lat is None or lon is None:
                continue
            if isinstance(lat, float) and (math.isnan(lat) or math.isinf(lat)):
                continue
            if isinstance(lon, float) and (math.isnan(lon) or math.isinf(lon)):
                continue

            # Clean other numeric fields
            acres = fire.get('EstTotalAcres')
            if isinstance(acres, float) and (math.isnan(acres) or math.isinf(acres)):
                fire['EstTotalAcres'] = 0

            cleaned_fires.append(fire)

        logger.info(
            f"Retrieved {len(cleaned_fires)} valid fire records "
            f"(filtered from {len(fires)})"
        )

        return jsonify({
            'data': cleaned_fires,
            'count': len(cleaned_fires),
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error fetching fires: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask development server on port 5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
