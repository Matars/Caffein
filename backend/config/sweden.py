"""
Sweden-specific configuration for wildfire simulation
"""

# Geographic boundaries
SWEDEN_BOUNDS = {
    'north': 69.06,  # Treriksröset (northernmost point)
    'south': 55.34,  # Smygehuk (southernmost point)
    'west': 10.96,   # Western border
    'east': 24.17,   # Haparanda (easternmost point)
}

# Grid configuration
GRID_RESOLUTION = 0.1  # degrees (~11 km at Sweden's latitude)

# Calculate grid dimensions
GRID_LAT_CELLS = int((SWEDEN_BOUNDS['north'] - SWEDEN_BOUNDS['south']) / GRID_RESOLUTION)
GRID_LON_CELLS = int((SWEDEN_BOUNDS['east'] - SWEDEN_BOUNDS['west']) / GRID_RESOLUTION)
TOTAL_CELLS = GRID_LAT_CELLS * GRID_LON_CELLS

# Map center for visualization
MAP_CENTER = {
    'latitude': 62.0,
    'longitude': 15.0,
    'zoom': 5
}

# Fire season (for filtering relevant data)
FIRE_SEASON = {
    'start_month': 5,   # May
    'end_month': 9,     # September
}

# Temporal configuration
TEMPORAL_RESOLUTION = 'daily'  # Daily predictions

# Data sources
DATA_SOURCES = {
    'firms': {
        'satellites': ['Aqua', 'Terra', 'NOAA-20', 'Suomi-NPP'],
        'instruments': ['MODIS', 'VIIRS'],
        'confidence_threshold': 50,  # Minimum confidence to include
    },
    'sentinel5p': {
        'product': 'COPERNICUS/S5P/OFFL/L3_NO2',
        'variable': 'NO2_column_number_density',
        'cloud_fraction_max': 0.3,  # Exclude pixels with >30% cloud cover
        'qa_threshold': 0.5,  # Minimum QA value
    },
    'weather': {
        'source': 'smhi',  # Swedish Meteorological Institute
        'api_url': 'https://opendata-download-metobs.smhi.se/api',
        'variables': ['temperature', 'humidity', 'wind_speed', 'wind_direction', 'precipitation'],
    },
    'landcover': {
        'source': 'copernicus_corine',
        'resolution': 100,  # meters
        'url': 'https://land.copernicus.eu/pan-european/corine-land-cover',
    },
    'elevation': {
        'source': 'eu_dem',
        'resolution': 25,  # meters
        'url': 'https://land.copernicus.eu/imagery-in-situ/eu-dem',
    }
}

# Fire spread model parameters
FIRE_SPREAD_PARAMS = {
    'max_spread_distance': 20,  # km per day (maximum)
    'wind_multiplier': 1.5,     # How much wind increases spread
    'humidity_threshold': 30,    # % below which fire spreads easily
    'slope_multiplier': 1.2,    # Uphill spread enhancement
}

# Fuel types and their characteristics (Sweden-specific)
FUEL_TYPES = {
    'coniferous_forest': {
        'id': 1,
        'name': 'Coniferous Forest',
        'ignitability': 0.8,
        'burn_rate': 0.7,
        'common_in_sweden': True,
    },
    'mixed_forest': {
        'id': 2,
        'name': 'Mixed Forest',
        'ignitability': 0.7,
        'burn_rate': 0.6,
        'common_in_sweden': True,
    },
    'broadleaf_forest': {
        'id': 3,
        'name': 'Broadleaf Forest',
        'ignitability': 0.5,
        'burn_rate': 0.5,
        'common_in_sweden': True,
    },
    'grassland': {
        'id': 4,
        'name': 'Grassland/Scrub',
        'ignitability': 0.9,
        'burn_rate': 0.8,
        'common_in_sweden': False,
    },
    'peatland': {
        'id': 5,
        'name': 'Peatland/Wetland',
        'ignitability': 0.3,
        'burn_rate': 0.4,
        'common_in_sweden': True,
    },
    'agricultural': {
        'id': 6,
        'name': 'Agricultural',
        'ignitability': 0.4,
        'burn_rate': 0.3,
        'common_in_sweden': True,
    },
    'urban': {
        'id': 7,
        'name': 'Urban/Built-up',
        'ignitability': 0.1,
        'burn_rate': 0.1,
        'common_in_sweden': True,
    },
    'water': {
        'id': 8,
        'name': 'Water',
        'ignitability': 0.0,
        'burn_rate': 0.0,
        'common_in_sweden': True,
    },
    'bare_rock': {
        'id': 9,
        'name': 'Bare Rock/Sparse Vegetation',
        'ignitability': 0.2,
        'burn_rate': 0.1,
        'common_in_sweden': True,
    }
}

# NO2 prediction parameters
NO2_PARAMS = {
    'background_level': 1.5e15,  # molecules/cm² (typical rural Sweden)
    'urban_level': 5.0e15,       # molecules/cm² (Stockholm/Gothenburg)
    'fire_emission_factor': 1.2e14,  # molecules/cm²/km² burned
    'plume_decay_rate': 0.1,     # per km distance
    'temporal_decay': 0.2,       # per day
}

# Model paths
MODEL_PATHS = {
    'fire_spread_ca': 'backend/ml/models/saved/fire_spread_ca.pkl',
    'fire_spread_rf': 'backend/ml/models/saved/fire_spread_rf.pkl',
    'no2_predictor': 'backend/ml/models/saved/no2_predictor.pkl',
}

# Data paths
DATA_PATHS = {
    'firms_sweden': 'data/sweden/firms_sweden.json',
    'sentinel5p_sweden': 'data/sweden/sentinel5p_no2/',
    'weather_sweden': 'data/sweden/weather/',
    'landcover_sweden': 'data/sweden/landcover/',
    'elevation_sweden': 'data/sweden/elevation/',
    'processed': 'data/sweden/processed/',
}

# Database configuration
DB_TABLES = {
    'fire_detections_sweden': 'fire_detections_sweden',
    'no2_measurements_sweden': 'no2_measurements_sweden',
    'weather_sweden': 'weather_sweden',
    'landcover_sweden': 'landcover_sweden',
    'topography_sweden': 'topography_sweden',
    'simulations': 'simulations',
    'simulation_results': 'simulation_results',
}

# Simulation defaults
SIMULATION_DEFAULTS = {
    'duration_days': 7,
    'time_step': 'daily',
    'initial_fire_radius': 0.5,  # km
    'weather_scenario': 'current',  # 'current', 'dry', 'wet', 'windy'
}

# Validation settings
VALIDATION = {
    'historical_fires': [
        {
            'name': 'Västmanland 2014',
            'start_date': '2014-07-31',
            'location': {'lat': 60.0, 'lon': 15.5},
            'duration_days': 10,
        },
        # Add more historical fires as references
    ]
}

def is_in_sweden(lat, lon):
    """Check if coordinates are within Sweden bounds"""
    return (
        SWEDEN_BOUNDS['south'] <= lat <= SWEDEN_BOUNDS['north'] and
        SWEDEN_BOUNDS['west'] <= lon <= SWEDEN_BOUNDS['east']
    )

def get_grid_cell(lat, lon):
    """Convert lat/lon to grid cell indices"""
    if not is_in_sweden(lat, lon):
        return None

    lat_idx = int((lat - SWEDEN_BOUNDS['south']) / GRID_RESOLUTION)
    lon_idx = int((lon - SWEDEN_BOUNDS['west']) / GRID_RESOLUTION)

    return (lat_idx, lon_idx)

def get_cell_center(lat_idx, lon_idx):
    """Convert grid cell indices to center lat/lon"""
    lat = SWEDEN_BOUNDS['south'] + (lat_idx + 0.5) * GRID_RESOLUTION
    lon = SWEDEN_BOUNDS['west'] + (lon_idx + 0.5) * GRID_RESOLUTION

    return (lat, lon)

# Print configuration summary
if __name__ == "__main__":
    print("=" * 60)
    print("SWEDEN WILDFIRE SIMULATION CONFIGURATION")
    print("=" * 60)
    print(f"Geographic Extent:")
    print(f"  Latitude:  {SWEDEN_BOUNDS['south']:.2f}°N to {SWEDEN_BOUNDS['north']:.2f}°N")
    print(f"  Longitude: {SWEDEN_BOUNDS['west']:.2f}°E to {SWEDEN_BOUNDS['east']:.2f}°E")
    print(f"\nGrid Configuration:")
    print(f"  Resolution: {GRID_RESOLUTION}° (~11 km)")
    print(f"  Cells: {GRID_LAT_CELLS} (lat) × {GRID_LON_CELLS} (lon) = {TOTAL_CELLS:,} total")
    print(f"\nTemporal:")
    print(f"  Resolution: {TEMPORAL_RESOLUTION}")
    print(f"  Fire Season: Month {FIRE_SEASON['start_month']} - {FIRE_SEASON['end_month']}")
    print(f"\nData Storage:")
    for key, path in DATA_PATHS.items():
        print(f"  {key}: {path}")
    print("=" * 60)
