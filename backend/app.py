from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from db import init_db, get_db, get_connection_status, close_db
from models import Message, FireDetectionSweden, NO2MeasurementSweden
from sqlalchemy import func
from logger import get_logger
from athena_client import get_athena_client
import atexit

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('api')

app = Flask(__name__)
CORS(app)

# Initialize PostgreSQL connection asynchronously (non-blocking)
logger.info("Starting Flask server...")
init_db()
logger.info("PostgreSQL connection initializing in background...")

# Cleanup on exit
atexit.register(close_db)


@app.route('/api/hello', methods=['GET'])
def hello():
    """Hello world endpoint that returns a message from the database or default"""
    session = get_db()
    try:
        if session is not None:
            # Try to get message from database
            message_obj = session.query(
                Message).filter_by(type='hello').first()

            if message_obj:
                message = message_obj.content
                logger.debug("Retrieved message from database")
            else:
                # Insert default message if not exists
                default_message = Message(
                    type='hello',
                    content='Hello from Caffein - NASA FIRMS Sweden Fire Detection System!'
                )
                session.add(default_message)
                session.commit()
                message = default_message.content
                logger.info("Inserted default message into database")

            session.close()
        else:
            message = 'Hello World from Flask backend (PostgreSQL not connected)'
            logger.warning("Database not connected, using default message")

        return jsonify({
            'message': message,
            'status': 'success',
            'database_connected': session is not None
        })
    except Exception as e:
        if session:
            session.rollback()
            session.close()
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
    """Get NASA FIRMS fire detections with coordinates for mapping"""
    session = get_db()
    try:
        if session is None:
            logger.warning("Database not connected")
            return jsonify({
                'error': 'Database not connected',
                'status': 'error'
            }), 503

        # Optional query parameters for filtering
        limit = request.args.get('limit', 100, type=int)
        date_from = request.args.get('date_from')  # YYYY-MM-DD
        date_to = request.args.get('date_to')  # YYYY-MM-DD

        # Build query
        query = session.query(FireDetectionSweden)
        if date_from:
            query = query.filter(FireDetectionSweden.acq_date >= date_from)
        if date_to:
            query = query.filter(FireDetectionSweden.acq_date <= date_to)

        # Order and limit
        fires_query = query.order_by(
            FireDetectionSweden.acq_date.desc()).limit(limit).all()

        # Check if table is empty
        if len(fires_query) == 0:
            session.close()
            logger.warning(
                "No fire detection records found in database. Run seeding script first.")
            return jsonify({
                'data': [],
                'count': 0,
                'status': 'success',
                'message': 'No data found. Please run: python scripts/seed_sweden_data.py'
            })

        # Convert to dict and validate coordinates
        cleaned_fires = []
        for fire in fires_query:
            fire_dict = fire.to_dict()

            # Validate coordinates exist
            if fire_dict['latitude'] is None or fire_dict['longitude'] is None:
                continue

            cleaned_fires.append(fire_dict)

        session.close()

        logger.info(
            f"Retrieved {len(cleaned_fires)} valid fire detection records "
            f"(filtered from {len(fires_query)})"
        )

        return jsonify({
            'data': cleaned_fires,
            'count': len(cleaned_fires),
            'status': 'success'
        })

    except Exception as e:
        if session:
            session.close()
        logger.error(f"Error fetching fire detections: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/fires/range', methods=['GET'])
def get_fires_range():
    """Return the min and max acquisition dates available for Sweden fire detections"""
    session = get_db()
    try:
        if session is None:
            return jsonify({'error': 'Database not connected', 'status': 'error'}), 503

        # Query min/max dates
        res = session.query(func.min(FireDetectionSweden.acq_date).label('min_date'),
                            func.max(FireDetectionSweden.acq_date).label('max_date')).one()
        session.close()

        min_date = res.min_date.isoformat() if res.min_date else None
        max_date = res.max_date.isoformat() if res.max_date else None

        return jsonify({'min_date': min_date, 'max_date': max_date, 'status': 'success'})

    except Exception as e:
        if session:
            session.close()
        logger.error(f"Error fetching fires date range: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/fires/athena', methods=['GET'])
def get_fires_athena():
    """
    Query wildfire data from AWS Athena by bounding box
    
    Query parameters:
    - min_lat: Minimum latitude (default: 55.0 for Sweden)
    - max_lat: Maximum latitude (default: 69.0 for Sweden)
    - min_lon: Minimum longitude (default: 11.0 for Sweden)
    - max_lon: Maximum longitude (default: 24.0 for Sweden)
    - limit: Maximum number of results (default: 1000)
    """
    try:
        # Get bounding box parameters (default to Sweden)
        min_lat = request.args.get('min_lat', 55.0, type=float)
        max_lat = request.args.get('max_lat', 69.0, type=float)
        min_lon = request.args.get('min_lon', 11.0, type=float)
        max_lon = request.args.get('max_lon', 24.0, type=float)
        limit = request.args.get('limit', 1000, type=int)

        # Validate inputs
        if min_lat >= max_lat:
            return jsonify({
                'error': 'min_lat must be less than max_lat',
                'status': 'error'
            }), 400

        if min_lon >= max_lon:
            return jsonify({
                'error': 'min_lon must be less than max_lon',
                'status': 'error'
            }), 400

        logger.info(
            f"Querying Athena for wildfires: "
            f"lat=[{min_lat}, {max_lat}], lon=[{min_lon}, {max_lon}], limit={limit}"
        )

        # Query Athena
        athena_client = get_athena_client()
        results = athena_client.query_wildfire_by_bbox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit
        )

        logger.info(f"Athena query returned {len(results)} records")

        return jsonify({
            'data': results,
            'count': len(results),
            'status': 'success',
            'source': 'athena',
            'bbox': {
                'min_lat': min_lat,
                'max_lat': max_lat,
                'min_lon': min_lon,
                'max_lon': max_lon
            }
        })

    except Exception as e:
        logger.error(f"Error querying Athena: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/no2', methods=['GET'])
def get_no2_measurements():
    """Get Sentinel-5P NO2 pollution measurements for Sweden"""
    session = get_db()
    try:
        if session is None:
            logger.warning("Database not connected")
            return jsonify({
                'error': 'Database not connected',
                'status': 'error'
            }), 503

        # Optional query parameters for filtering
        limit = request.args.get('limit', 10000, type=int)
        date_from = request.args.get('date_from')  # YYYY-MM-DD
        date_to = request.args.get('date_to')  # YYYY-MM-DD
        min_qa = request.args.get('min_qa', 0.5, type=float)  # Minimum quality

        # Build query
        query = session.query(NO2MeasurementSweden)

        # Apply filters
        if date_from:
            query = query.filter(
                NO2MeasurementSweden.measurement_date >= date_from)
        if date_to:
            query = query.filter(
                NO2MeasurementSweden.measurement_date <= date_to)
        if min_qa:
            query = query.filter(NO2MeasurementSweden.qa_value >= min_qa)

        # Order by date (most recent first) and apply limit
        query = query.order_by(
            NO2MeasurementSweden.measurement_date.desc()).limit(limit)

        measurements = query.all()

        # Check if table is empty
        if len(measurements) == 0:
            session.close()
            logger.warning("No NO2 measurement records found in database")
            return jsonify({
                'data': [],
                'count': 0,
                'status': 'success',
                'message': 'No data found. Please run: python scripts/seed_no2_data.py'
            })

        # Convert to dict and validate
        cleaned_measurements = []
        for measurement in measurements:
            measurement_dict = measurement.to_dict()

            # Validate coordinates and NO2 value exist
            if (measurement_dict['latitude'] is None or
                measurement_dict['longitude'] is None or
                    measurement_dict['no2_column'] is None):
                continue

            cleaned_measurements.append(measurement_dict)

        session.close()

        logger.info(
            f"Retrieved {len(cleaned_measurements)} valid NO2 measurement records "
            f"(filtered from {len(measurements)})"
        )

        return jsonify({
            'data': cleaned_measurements,
            'count': len(cleaned_measurements),
            'status': 'success'
        })

    except Exception as e:
        if session:
            session.close()
        logger.error(f"Error fetching NO2 measurements: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask development server on port 5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
