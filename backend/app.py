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
import math
import random
import requests
from datetime import datetime
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('api')

app = Flask(__name__)
# Enable CORS for all domains on all routes
CORS(app, resources={r"/*": {"origins": "*"}})

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
    - start_date: Start date (YYYY-MM-DD format, optional)
    - end_date: End date (YYYY-MM-DD format, optional)
    - min_frp: Minimum Fire Radiative Power (optional)
    """
    try:
        # Get bounding box parameters (default to Sweden)
        min_lat = request.args.get('min_lat', 55.0, type=float)
        max_lat = request.args.get('max_lat', 69.0, type=float)
        min_lon = request.args.get('min_lon', 11.0, type=float)
        max_lon = request.args.get('max_lon', 24.0, type=float)
        limit = request.args.get('limit', 1000, type=int)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        min_frp = request.args.get('min_frp', type=float)

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
            f"lat=[{min_lat}, {max_lat}], lon=[{min_lon}, {max_lon}], "
            f"dates=[{start_date}, {end_date}], limit={limit}, min_frp={min_frp}"
        )

        # Query Athena
        athena_client = get_athena_client()
        results = athena_client.query_wildfire_by_bbox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            min_frp=min_frp
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
            },
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            } if start_date or end_date else None
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


@app.route('/api/simulate-fire', methods=['POST'])
def simulate_fire():
    """
    Simulate fire impact and pollutant spread
    
    Expected JSON body:
    - latitude: float
    - longitude: float
    - frp: float (Fire Radiative Power)
    - pollutants: list[str] (e.g. ['CO', 'NO2', 'CH4'])
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided', 'status': 'error'}), 400
            
        lat = data.get('latitude')
        lon = data.get('longitude')
        frp = data.get('frp', 100.0)
        pollutants = data.get('pollutants', ['CO', 'NO2'])
        
        if lat is None or lon is None:
            return jsonify({'error': 'Latitude and longitude are required', 'status': 'error'}), 400
            
        # Simulation parameters
        # Grid size (degrees)
        grid_radius = 0.5  # approx 50km
        grid_steps = 20
        step_size = (grid_radius * 2) / grid_steps
        
        grid_data = []
        
        # Wind parameters (randomized for now, could be inputs)
        wind_speed = random.uniform(5, 15)  # km/h
        wind_dir = random.uniform(0, 360)  # degrees
        wind_rad = math.radians(wind_dir)
        
        # Generate grid points
        for i in range(grid_steps):
            for j in range(grid_steps):
                # Calculate point coordinates
                p_lat = (lat - grid_radius) + (i * step_size)
                p_lon = (lon - grid_radius) + (j * step_size)
                
                # Calculate distance from fire (approximate)
                # 1 deg lat approx 111km
                dy = (p_lat - lat) * 111.0
                dx = (p_lon - lon) * 111.0 * math.cos(math.radians(lat))
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Calculate angle for wind effect
                angle = math.atan2(dy, dx)
                angle_diff = abs(angle - wind_rad)
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                angle_diff = abs(angle_diff)
                
                # Wind factor: higher concentration downwind
                # Gaussian distribution along wind direction
                wind_factor = math.exp(-(angle_diff * angle_diff) / (2 * 0.5 * 0.5))
                if dist > 0:
                    wind_factor *= (1 + wind_speed/10.0)
                
                # Base concentration based on FRP and distance
                # Decay with distance (Gaussian plume model simplified)
                if dist < 0.5:
                    concentration = frp  # At source
                else:
                    # Dispersion
                    concentration = (frp / (dist * dist + 1)) * (0.5 + 0.5 * wind_factor)
                
                # Add some noise
                concentration *= random.uniform(0.8, 1.2)
                
                point_data = {
                    'latitude': p_lat,
                    'longitude': p_lon,
                    'distance': dist
                }
                
                # Calculate specific pollutants
                # Ratios relative to generic concentration (arbitrary for simulation)
                ratios = {
                    'CO': 1.0,
                    'NO2': 0.1,
                    'CH4': 0.05,
                    'HCHO': 0.02,
                    'SO2': 0.01,
                    'AAI': 0.5
                }
                
                for p in pollutants:
                    ratio = ratios.get(p, 0.1)
                    point_data[p] = concentration * ratio
                
                # Only include points with significant concentration
                if concentration > 0.1:
                    grid_data.append(point_data)
        
        # Calculate summary statistics
        max_dist = 0
        pollutant_stats = {p: {'max': 0.0, 'sum': 0.0, 'count': 0} for p in pollutants}
        
        for point in grid_data:
            if point['distance'] > max_dist:
                max_dist = point['distance']
            
            for p in pollutants:
                if p in point:
                    val = point[p]
                    if val > pollutant_stats[p]['max']:
                        pollutant_stats[p]['max'] = val
                    pollutant_stats[p]['sum'] += val
                    pollutant_stats[p]['count'] += 1
        
        pollutant_peaks = {}
        for p, stats in pollutant_stats.items():
            if stats['count'] > 0:
                pollutant_peaks[p] = {
                    'max': stats['max'],
                    'mean': stats['sum'] / stats['count']
                }
            else:
                pollutant_peaks[p] = {'max': 0, 'mean': 0}

        return jsonify({
            'status': 'success',
            'grid_data': grid_data,
            'summary': {
                'fire_location': {'lat': lat, 'lon': lon},
                'fire_intensity': frp,
                'grid_points': len(grid_data),
                'max_distance_km': max_dist,
                'pollutant_peaks': pollutant_peaks
            },
            'metadata': {
                'wind_speed': wind_speed,
                'wind_direction': wind_dir,
                'frp': frp
            }
        })
        
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Get weather data from OpenWeather API"""
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    date = request.args.get('date') # Unix timestamp

    if not lat or not lon:
        return jsonify({'error': 'Missing lat or lon parameter'}), 400
    
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        logger.error("OPENWEATHER_API_KEY not found in environment variables")
        return jsonify({'error': 'Server configuration error'}), 500

    try:
        if date:
            # Historical data using History API 2.5
            url = "https://history.openweathermap.org/data/2.5/history/city"
            params = {
                'lat': lat,
                'lon': lon,
                'type': 'hour',
                'start': date,
                'cnt': 24, # Get 24 hours of data
                'appid': api_key,
                'units': 'metric'
            }
        else:
            # Current weather using Weather API 2.5
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key,
                'units': 'metric'
            }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            result = {}
            if date:
                 # Parse history response (list of hours)
                 # Find the hour with max wind speed to represent the day's worst case for fire
                 if 'list' in data and len(data['list']) > 0:
                     max_wind_entry = max(data['list'], key=lambda x: x.get('wind', {}).get('speed', 0))
                     wind = max_wind_entry.get('wind', {})
                     main = max_wind_entry.get('main', {})
                     
                     result = {
                        'wind_speed': wind.get('speed', 0),
                        'wind_deg': wind.get('deg', 0),
                        'temp': main.get('temp', 0),
                        'humidity': main.get('humidity', 0),
                        'rain': max_wind_entry.get('rain', {}).get('1h', 0) if isinstance(max_wind_entry.get('rain'), dict) else 0
                     }
                 else:
                    raise ValueError("No historical data found in response")
            else:
                # Parse current weather response
                wind = data.get('wind', {})
                main = data.get('main', {})
                rain = data.get('rain', {})
                result = {
                    'wind_speed': wind.get('speed', 0),
                    'wind_deg': wind.get('deg', 0),
                    'temp': main.get('temp', 0),
                    'humidity': main.get('humidity', 0),
                    'rain': rain.get('1h', 0) if isinstance(rain, dict) else 0
                }
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            logger.error(f"OpenWeather API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                 logger.error(f"Response content: {e.response.text}")
            
            # Fallback to mock data for demonstration if API fails
            logger.warning("Falling back to mock weather data")
            
            # Generate realistic seasonal temperatures for Sweden
            # Get month from timestamp (if provided) or use current month
            if date:
                month = datetime.fromtimestamp(int(date)).month
            else:
                month = datetime.now().month
            
            # Sweden seasonal temperature ranges (average ±5°C variation)
            # Month: 1=Jan, 2=Feb, ..., 12=Dec
            seasonal_temps = {
                1: -3,   # January: -8°C to +2°C
                2: -3,   # February: -8°C to +2°C
                3: 0,    # March: -5°C to +5°C
                4: 6,    # April: 1°C to 11°C
                5: 12,   # May: 7°C to 17°C
                6: 16,   # June: 11°C to 21°C
                7: 18,   # July: 13°C to 23°C
                8: 17,   # August: 12°C to 22°C
                9: 12,   # September: 7°C to 17°C
                10: 7,   # October: 2°C to 12°C
                11: 2,   # November: -3°C to +7°C
                12: -1   # December: -6°C to +4°C
            }
            
            base_temp = seasonal_temps.get(month, 10)
            temp = base_temp + random.uniform(-5, 5)  # Add realistic variation
            
            result = {
                'wind_speed': random.uniform(0, 10),
                'wind_deg': random.uniform(0, 360),
                'temp': round(temp, 1),  # Realistic seasonal temperature
                'humidity': random.uniform(30, 80),
                'rain': 0 if random.random() > 0.3 else random.uniform(0, 5),
                'is_mock': True
            }

        return jsonify({
            'status': 'success',
            'data': result
        })

    except Exception as e:
        logger.error(f"Unexpected error in get_weather: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/pollution', methods=['GET'])
def get_pollution():
    """Get air pollution data from OpenWeather API"""
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    date = request.args.get('date') # Unix timestamp

    if not lat or not lon:
        return jsonify({'error': 'Missing lat or lon parameter'}), 400
    
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        logger.error("OPENWEATHER_API_KEY not found in environment variables")
        return jsonify({'error': 'Server configuration error'}), 500

    try:
        # Determine if we need history, current, or forecast
        # For now, we'll support history (if date provided) and current (if not)
        # The user wants to plot data, so history/forecast is best.
        
        if date:
            # Historical data
            # Get 24 hours starting from the provided timestamp
            start_ts = int(date)
            end_ts = start_ts + 86400 # +24 hours
            
            url = "http://api.openweathermap.org/data/2.5/air_pollution/history"
            params = {
                'lat': lat,
                'lon': lon,
                'start': start_ts,
                'end': end_ts,
                'appid': api_key
            }
        else:
            # Current data
            url = "http://api.openweathermap.org/data/2.5/air_pollution"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key
            }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Return the raw list of data points
            # Each item has 'dt', 'main' (aqi), 'components' (co, no2, etc.)
            return jsonify({
                'status': 'success',
                'data': data.get('list', [])
            })

        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            logger.error(f"OpenWeather Pollution API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                 logger.error(f"Response content: {e.response.text}")
            
            # Fallback to mock data
            logger.warning("Falling back to mock pollution data")
            mock_data = []
            start_ts = int(date) if date else int(datetime.now().timestamp())
            for i in range(24):
                mock_data.append({
                    'dt': start_ts + i * 3600,
                    'main': {'aqi': random.randint(1, 5)},
                    'components': {
                        'co': random.uniform(200, 300),
                        'no2': random.uniform(0, 10),
                        'o3': random.uniform(50, 100),
                        'so2': random.uniform(0, 5),
                        'pm2_5': random.uniform(0, 15),
                        'pm10': random.uniform(0, 20),
                        'nh3': random.uniform(0, 1),
                        'no': random.uniform(0, 1)
                    }
                })
            
            return jsonify({
                'status': 'success',
                'data': mock_data,
                'is_mock': True
            })

    except Exception as e:
        logger.error(f"Unexpected error in get_pollution: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/fires/csv', methods=['GET'])
def get_fires_from_csv():
    """
    Get fire data from local CSV file (combined-countries.csv)
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD format, optional)
    - end_date: End date (YYYY-MM-DD format, optional)
    - min_frp: Minimum Fire Radiative Power (optional)
    - limit: Maximum number of results (default: 5000)
    """
    try:
        # Get query parameters
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        min_frp = request.args.get('min_frp', 0, type=float)
        limit = request.args.get('limit', 5000, type=int)
        
        # Path to CSV file
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'NASA-MODIS-DATA', 'combined-countries.csv')
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found at: {csv_path}")
            return jsonify({
                'error': 'CSV file not found',
                'status': 'error'
            }), 404
        
        logger.info(f"Reading fire data from CSV: {csv_path}")
        
        # Read CSV file
        df = pd.read_csv(csv_path)
        
        # Ensure acq_date is datetime
        df['acq_date'] = pd.to_datetime(df['acq_date'])
        
        # Apply filters
        if start_date:
            df = df[df['acq_date'] >= start_date]
        
        if end_date:
            df = df[df['acq_date'] <= end_date]
        
        if min_frp > 0:
            df = df[df['frp'] >= min_frp]
        
        # Sort by date (most recent first) and apply limit
        df = df.sort_values('acq_date', ascending=False).head(limit)
        
        # Convert to list of dicts
        fires = []
        for _, row in df.iterrows():
            fires.append({
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'acq_date': row['acq_date'].strftime('%Y-%m-%d'),
                'acq_time': str(row.get('acq_time', '')),
                'frp': float(row.get('frp', 0)),
                'brightness': float(row.get('brightness', 0)) if pd.notna(row.get('brightness')) else None,
                'confidence': str(row.get('confidence', '')),
                'satellite': str(row.get('satellite', '')),
                'instrument': str(row.get('instrument', ''))
            })
        
        logger.info(f"Returning {len(fires)} fire records from CSV")
        
        return jsonify({
            'data': fires,
            'count': len(fires),
            'status': 'success',
            'source': 'csv',
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'min_frp': min_frp
            }
        })
        
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask development server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
