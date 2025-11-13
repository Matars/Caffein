from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from db import init_db, get_db, get_connection_status, close_db
from logger import get_logger
import atexit
import math
import pickle
import numpy as np

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger('api')

app = Flask(__name__)
CORS(app)

# Helper function for distance calculation
def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# Simple fallback simulation function
def simulate_fire_pollution_impact_simple(fire_lat, fire_lon, frp, grid_resolution=0.15, radius_km=150):
    """
    Simple pollution dispersion model using Gaussian plume approximation.
    Creates a grid of points around the fire and estimates pollution levels.
    """
    import pandas as pd
    
    grid_data = []
    
    # Create a grid of points around the fire
    # Calculate how many degrees correspond to the radius
    lat_range = radius_km / 111.0  # Roughly 111 km per degree latitude
    lon_range = radius_km / (111.0 * math.cos(math.radians(fire_lat)))
    
    # Generate grid points
    lat_min = fire_lat - lat_range
    lat_max = fire_lat + lat_range
    lon_min = fire_lon - lon_range
    lon_max = fire_lon + lon_range
    
    current_lat = lat_min
    while current_lat <= lat_max:
        current_lon = lon_min
        while current_lon <= lon_max:
            # Calculate distance from fire
            dist_km = calculate_distance_km(fire_lat, fire_lon, current_lat, current_lon)
            
            if dist_km <= radius_km:
                # Simple Gaussian dispersion model
                # Pollution decreases with distance from source
                
                # Normalize FRP (typical range: 0-500)
                frp_normalized = min(frp / 500.0, 1.0)
                
                # Distance factor (pollution decreases with distance)
                if dist_km < 1:
                    distance_factor = 1.0
                else:
                    # Exponential decay
                    distance_factor = math.exp(-dist_km / 50.0)
                
                # Base pollution intensity
                base_intensity = frp_normalized * distance_factor
                
                # Simulate different pollutants with varying dispersion patterns
                co_level = base_intensity * 0.8 * (1 + 0.2 * np.random.random())  # CO disperses widely
                no2_level = base_intensity * 0.6 * (1 + 0.3 * np.random.random())  # NO2 moderate dispersion
                ch4_level = base_intensity * 0.5 * (1 + 0.2 * np.random.random())  # CH4 lighter
                hcho_level = base_intensity * 0.4 * (1 + 0.3 * np.random.random())  # HCHO reactive
                so2_level = base_intensity * 0.3 * (1 + 0.4 * np.random.random())  # SO2 heavier
                aai_level = base_intensity * 0.7 * (1 + 0.2 * np.random.random())  # AAI (aerosols)
                
                grid_data.append({
                    'latitude': current_lat,
                    'longitude': current_lon,
                    'distance_km': dist_km,
                    'CO': co_level,
                    'NO2': no2_level,
                    'CH4': ch4_level,
                    'HCHO': hcho_level,
                    'SO2': so2_level,
                    'AAI': aai_level
                })
            
            current_lon += grid_resolution
        current_lat += grid_resolution
    
    return pd.DataFrame(grid_data)

# Load fire impact model
fire_model = None
try:
    with open('../data/fire_impact_model.pkl', 'rb') as f:
        fire_model = pickle.load(f)
    logger.info("Fire impact model loaded successfully from pickle file")
except Exception as e:
    logger.warning(f"Could not load fire impact model from pickle: {e}")
    logger.info("Using simple fallback simulation model")
    # Create fallback model dictionary
    fire_model = {
        'simulate_fire_pollution_impact': simulate_fire_pollution_impact_simple
    }

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


# Load the fire simulation model (old endpoint)
fire_simulation_model = None
logger.info("Loading fire simulation model...")
try:
    with open('../model/fire_simulation_model.pkl', 'rb') as model_file:
        fire_simulation_model = pickle.load(model_file)
    logger.info("Fire simulation model loaded successfully")
except Exception as e:
    logger.warning(f"Could not load fire simulation model: {str(e)}")


@app.route('/api/simulate_fire', methods=['POST'])
def simulate_fire():
    """Simulate fire occurrence based on conditions"""
    try:
        # Get input data from request
        data = request.get_json()
        logger.debug(f"Received data for simulation: {data}")

        # Validate input data
        required_fields = ['temperature', 'humidity', 'wind_speed', 'precipitation']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f"Missing required field: {field}",
                    'status': 'error'
                }), 400

        # Extract features from input data
        features = np.array([
            data['temperature'],
            data['humidity'],
            data['wind_speed'],
            data['precipitation']
        ]).reshape(1, -1)

        # Log the features for debugging
        logger.debug(f"Features for model: {features}")

        # Make prediction using the loaded model
        prediction = fire_simulation_model.predict(features)
        logger.info(f"Model prediction: {prediction}")

        # Return the prediction result
        return jsonify({
            'predicted_fire_occurrence': bool(prediction[0]),
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error in /api/simulate_fire endpoint: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/simulate-fire', methods=['POST'])
def simulate_fire_pollution():
    """
    Simulate pollution impact from a fire at a given location.
    
    Expected JSON body:
    {
        "latitude": float,
        "longitude": float,
        "frp": float (optional, default: 100),
        "pollutants": array of strings (optional, default: ["CO", "NO2", "AAI"])
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'error'
            }), 400
        
        # Extract parameters
        lat = data.get('latitude')
        lon = data.get('longitude')
        frp = data.get('frp', 100)  # Default FRP
        pollutants = data.get('pollutants', ['CO', 'NO2', 'AAI'])
        
        # Validate inputs
        if lat is None or lon is None:
            return jsonify({
                'error': 'latitude and longitude are required',
                'status': 'error'
            }), 400
        
        if not (-90 <= lat <= 90):
            return jsonify({
                'error': 'Invalid latitude (must be -90 to 90)',
                'status': 'error'
            }), 400
        
        if not (-180 <= lon <= 180):
            return jsonify({
                'error': 'Invalid longitude (must be -180 to 180)',
                'status': 'error'
            }), 400
        
        if frp <= 0:
            return jsonify({
                'error': 'FRP must be positive',
                'status': 'error'
            }), 400
        
        logger.info(f"Simulating fire at ({lat}, {lon}) with FRP={frp}")
        
        # Run simulation using the model functions
        df_result = fire_model['simulate_fire_pollution_impact'](
            fire_lat=lat,
            fire_lon=lon,
            frp=frp,
            grid_resolution=0.15,
            radius_km=150
        )
        
        # Prepare grid data for response
        grid_data = []
        for _, row in df_result.iterrows():
            point = {
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'distance_km': float(row['distance_km'])
            }
            for pollutant in pollutants:
                if pollutant in row:
                    point[pollutant] = float(row[pollutant])
            grid_data.append(point)
        
        # Calculate summary statistics
        summary = {
            'fire_location': {'lat': lat, 'lon': lon},
            'fire_intensity': frp,
            'grid_points': len(grid_data),
            'max_distance_km': float(df_result['distance_km'].max()),
            'pollutant_peaks': {}
        }
        
        for pollutant in pollutants:
            if pollutant in df_result.columns:
                summary['pollutant_peaks'][pollutant] = {
                    'max': float(df_result[pollutant].max()),
                    'mean': float(df_result[pollutant].mean())
                }
        
        logger.info(f"Simulation complete: {len(grid_data)} grid points")
        
        return jsonify({
            'grid_data': grid_data,
            'summary': summary,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error in fire simulation: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/fires-csv', methods=['GET'])
def get_fires_csv():
    """
    Get fire data from the combined-countries.csv file with optional filtering.
    
    Query parameters:
    - start_date: Filter fires from this date (YYYY-MM-DD)
    - end_date: Filter fires until this date (YYYY-MM-DD)
    - min_frp: Minimum FRP value to include
    """
    try:
        import pandas as pd
        from flask import request
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        min_frp = request.args.get('min_frp', type=float, default=0)
        
        # Read the CSV file
        csv_path = '../data/NASA-MODIS-DATA/combined-countries.csv'
        
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found: {csv_path}")
            return jsonify({
                'error': 'Fire data file not found',
                'status': 'error',
                'message': 'Please ensure combined-countries.csv exists in data/NASA-MODIS-DATA/'
            }), 404
        
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from CSV")
        
        # Convert acq_date to datetime if it exists
        if 'acq_date' in df.columns:
            df['acq_date'] = pd.to_datetime(df['acq_date'])
            
            # Apply date filters
            if start_date:
                start = pd.to_datetime(start_date)
                df = df[df['acq_date'] >= start]
                logger.info(f"Filtered from {start_date}: {len(df)} records remain")
            
            if end_date:
                end = pd.to_datetime(end_date)
                df = df[df['acq_date'] <= end]
                logger.info(f"Filtered until {end_date}: {len(df)} records remain")
        
        # Apply FRP filter
        if 'frp' in df.columns:
            df = df[df['frp'] >= min_frp]
            logger.info(f"Filtered by FRP >= {min_frp}: {len(df)} records remain")
        
        # Drop rows with missing coordinates
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.dropna(subset=['latitude', 'longitude'])
            logger.info(f"After removing invalid coordinates: {len(df)} records remain")
        
        # Limit to prevent huge responses (max 5000 records)
        if len(df) > 5000:
            logger.warning(f"Dataset too large ({len(df)} records), sampling 5000")
            df = df.sample(n=5000, random_state=42)
        
        # Convert to JSON-serializable format
        # Convert datetime to string
        if 'acq_date' in df.columns:
            df['acq_date'] = df['acq_date'].dt.strftime('%Y-%m-%d')
        
        # Replace NaN/Inf with None
        df = df.replace([float('inf'), float('-inf')], None)
        df = df.where(pd.notnull(df), None)
        
        fires = df.to_dict('records')
        
        logger.info(f"Returning {len(fires)} fire records")
        
        return jsonify({
            'data': fires,
            'count': len(fires),
            'status': 'success',
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'min_frp': min_frp
            }
        })
        
    except Exception as e:
        logger.error(f"Error reading fires CSV: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask development server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
