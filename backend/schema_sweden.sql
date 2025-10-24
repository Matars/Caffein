-- PostgreSQL Schema for Sweden Wildfire Simulation
-- Extends the base schema with NO2 and environmental data tables

-- ============================================================================
-- PART 1: BASE TABLES (from existing schema)
-- ============================================================================

-- Drop existing tables if they exist
DROP TABLE IF EXISTS simulation_results CASCADE;
DROP TABLE IF EXISTS simulations CASCADE;
DROP TABLE IF EXISTS topography_sweden CASCADE;
DROP TABLE IF EXISTS landcover_sweden CASCADE;
DROP TABLE IF EXISTS weather_sweden CASCADE;
DROP TABLE IF EXISTS no2_measurements_sweden CASCADE;
DROP TABLE IF EXISTS fire_detections_sweden CASCADE;
DROP TABLE IF EXISTS fire_detections CASCADE;
DROP TABLE IF EXISTS messages CASCADE;

-- Messages table (keep existing)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fire detections table (global - keep existing)
CREATE TABLE fire_detections (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(11, 6) NOT NULL,
    acq_date DATE NOT NULL,
    acq_time VARCHAR(4),
    confidence VARCHAR(10),
    frp DECIMAL(10, 2),
    brightness DECIMAL(10, 2),
    bright_t31 DECIMAL(10, 2),
    instrument VARCHAR(20),
    satellite VARCHAR(50),
    version VARCHAR(20),
    daynight VARCHAR(1),
    type VARCHAR(10),
    scan DECIMAL(10, 2),
    track DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PART 2: SWEDEN-SPECIFIC TABLES
-- ============================================================================

-- Sweden fire detections (filtered subset)
CREATE TABLE fire_detections_sweden (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(11, 6) NOT NULL,
    acq_date DATE NOT NULL,
    acq_time VARCHAR(4),
    confidence VARCHAR(10),
    frp DECIMAL(10, 2),
    brightness DECIMAL(10, 2),
    bright_t31 DECIMAL(10, 2),
    instrument VARCHAR(20),
    satellite VARCHAR(50),
    version VARCHAR(20),
    daynight VARCHAR(1),
    type VARCHAR(10),
    scan DECIMAL(10, 2),
    track DECIMAL(10, 2),
    grid_lat_idx INTEGER,  -- Grid cell latitude index
    grid_lon_idx INTEGER,  -- Grid cell longitude index
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sweden_bounds_check CHECK (
        latitude BETWEEN 55.34 AND 69.06 AND
        longitude BETWEEN 10.96 AND 24.17
    )
);

-- NO2 measurements for Sweden (Sentinel-5P data)
CREATE TABLE no2_measurements_sweden (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(11, 6) NOT NULL,
    measurement_date DATE NOT NULL,
    no2_column DECIMAL(15, 6),  -- Tropospheric NO2 column density (molecules/cm²)
    qa_value DECIMAL(5, 3),     -- Quality assurance (0-1)
    cloud_fraction DECIMAL(5, 3),  -- Cloud fraction (0-1)
    grid_lat_idx INTEGER,
    grid_lon_idx INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sweden_bounds_check_no2 CHECK (
        latitude BETWEEN 55.34 AND 69.06 AND
        longitude BETWEEN 10.96 AND 24.17
    )
);

-- Weather data for Sweden
CREATE TABLE weather_sweden (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    measurement_date DATE NOT NULL,
    measurement_time TIME,
    temperature DECIMAL(5, 2),        -- Celsius
    humidity DECIMAL(5, 2),           -- Percentage (0-100)
    wind_speed DECIMAL(6, 2),         -- m/s
    wind_direction DECIMAL(5, 2),     -- Degrees (0-360)
    precipitation DECIMAL(6, 2),      -- mm
    grid_lat_idx INTEGER,
    grid_lon_idx INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sweden_bounds_check_weather CHECK (
        latitude BETWEEN 55.34 AND 69.06 AND
        longitude BETWEEN 10.96 AND 24.17
    )
);

-- Land cover data for Sweden
CREATE TABLE landcover_sweden (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    land_type VARCHAR(50),            -- Forest, grassland, urban, etc.
    fuel_type_id INTEGER,             -- Reference to fuel type
    vegetation_density DECIMAL(5, 2), -- 0-100
    ndvi DECIMAL(5, 3),              -- Normalized Difference Vegetation Index (-1 to 1)
    fuel_load DECIMAL(10, 2),        -- Estimated fuel load (tonnes/hectare)
    ignitability DECIMAL(3, 2),      -- Fire ignitability score (0-1)
    burn_rate DECIMAL(3, 2),         -- Expected burn rate (0-1)
    grid_lat_idx INTEGER,
    grid_lon_idx INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sweden_bounds_check_landcover CHECK (
        latitude BETWEEN 55.34 AND 69.06 AND
        longitude BETWEEN 10.96 AND 24.17
    )
);

-- Topography data for Sweden
CREATE TABLE topography_sweden (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    elevation DECIMAL(8, 2),    -- Meters above sea level
    slope DECIMAL(5, 2),        -- Degrees (0-90)
    aspect DECIMAL(5, 2),       -- Degrees (0-360), direction of slope
    grid_lat_idx INTEGER,
    grid_lon_idx INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sweden_bounds_check_topo CHECK (
        latitude BETWEEN 55.34 AND 69.06 AND
        longitude BETWEEN 10.96 AND 24.17
    )
);

-- ============================================================================
-- PART 3: SIMULATION TABLES
-- ============================================================================

-- Simulation metadata
CREATE TABLE simulations (
    id SERIAL PRIMARY KEY,
    simulation_id VARCHAR(50) UNIQUE NOT NULL,
    ignition_lat DECIMAL(9, 6) NOT NULL,
    ignition_lon DECIMAL(10, 6) NOT NULL,
    start_date DATE NOT NULL,
    duration_days INTEGER NOT NULL,
    weather_scenario VARCHAR(50),  -- 'current', 'dry', 'wet', 'windy'
    model_type VARCHAR(50),        -- 'ca', 'rf', 'hybrid'
    status VARCHAR(20),            -- 'pending', 'running', 'completed', 'failed'
    progress DECIMAL(5, 2),        -- Percentage complete (0-100)
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Simulation results (fire spread over time)
CREATE TABLE simulation_results (
    id SERIAL PRIMARY KEY,
    simulation_id VARCHAR(50) REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    day INTEGER NOT NULL,
    grid_lat_idx INTEGER NOT NULL,
    grid_lon_idx INTEGER NOT NULL,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    is_burning BOOLEAN,
    fire_probability DECIMAL(5, 4),  -- 0-1
    fire_intensity DECIMAL(10, 2),   -- FRP or similar metric
    no2_prediction DECIMAL(15, 6),   -- Predicted NO2 column density
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_sim_day_cell UNIQUE (simulation_id, day, grid_lat_idx, grid_lon_idx)
);

-- ============================================================================
-- PART 4: INDEXES FOR PERFORMANCE
-- ============================================================================

-- Fire detections indexes
CREATE INDEX idx_fire_detections_coords ON fire_detections(latitude, longitude);
CREATE INDEX idx_fire_detections_acq_date ON fire_detections(acq_date);
CREATE INDEX idx_fire_detections_instrument ON fire_detections(instrument);
CREATE INDEX idx_fire_detections_satellite ON fire_detections(satellite);
CREATE INDEX idx_fire_detections_confidence ON fire_detections(confidence);
CREATE INDEX idx_fire_detections_datetime ON fire_detections(acq_date, acq_time);

-- Sweden fire detections indexes
CREATE INDEX idx_fire_sweden_coords ON fire_detections_sweden(latitude, longitude);
CREATE INDEX idx_fire_sweden_date ON fire_detections_sweden(acq_date);
CREATE INDEX idx_fire_sweden_grid ON fire_detections_sweden(grid_lat_idx, grid_lon_idx);
CREATE INDEX idx_fire_sweden_instrument ON fire_detections_sweden(instrument);

-- NO2 measurements indexes
CREATE INDEX idx_no2_sweden_coords ON no2_measurements_sweden(latitude, longitude);
CREATE INDEX idx_no2_sweden_date ON no2_measurements_sweden(measurement_date);
CREATE INDEX idx_no2_sweden_grid ON no2_measurements_sweden(grid_lat_idx, grid_lon_idx);
CREATE INDEX idx_no2_sweden_quality ON no2_measurements_sweden(qa_value, cloud_fraction);

-- Weather indexes
CREATE INDEX idx_weather_sweden_coords ON weather_sweden(latitude, longitude);
CREATE INDEX idx_weather_sweden_datetime ON weather_sweden(measurement_date, measurement_time);
CREATE INDEX idx_weather_sweden_grid ON weather_sweden(grid_lat_idx, grid_lon_idx);

-- Land cover indexes
CREATE INDEX idx_landcover_sweden_coords ON landcover_sweden(latitude, longitude);
CREATE INDEX idx_landcover_sweden_grid ON landcover_sweden(grid_lat_idx, grid_lon_idx);
CREATE INDEX idx_landcover_sweden_type ON landcover_sweden(land_type);

-- Topography indexes
CREATE INDEX idx_topo_sweden_coords ON topography_sweden(latitude, longitude);
CREATE INDEX idx_topo_sweden_grid ON topography_sweden(grid_lat_idx, grid_lon_idx);

-- Simulation indexes
CREATE INDEX idx_simulations_status ON simulations(status);
CREATE INDEX idx_simulations_created ON simulations(created_at);
CREATE INDEX idx_simulation_results_sim_id ON simulation_results(simulation_id);
CREATE INDEX idx_simulation_results_day ON simulation_results(day);
CREATE INDEX idx_simulation_results_grid ON simulation_results(grid_lat_idx, grid_lon_idx);

-- Messages index
CREATE INDEX idx_messages_type ON messages(type);

-- ============================================================================
-- PART 5: INSERT DEFAULT DATA
-- ============================================================================

-- Insert default message
INSERT INTO messages (type, content) VALUES
    ('hello', 'Hello from Caffein - Sweden Wildfire Simulation System!');

-- ============================================================================
-- PART 6: HELPER FUNCTIONS (Optional but useful)
-- ============================================================================

-- Function to calculate grid cell indices from lat/lon
CREATE OR REPLACE FUNCTION get_grid_indices(lat DECIMAL, lon DECIMAL)
RETURNS TABLE(lat_idx INTEGER, lon_idx INTEGER) AS $$
DECLARE
    grid_resolution DECIMAL := 0.1;
    south_bound DECIMAL := 55.34;
    west_bound DECIMAL := 10.96;
BEGIN
    RETURN QUERY SELECT
        FLOOR((lat - south_bound) / grid_resolution)::INTEGER,
        FLOOR((lon - west_bound) / grid_resolution)::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- Function to check if point is in Sweden
CREATE OR REPLACE FUNCTION is_in_sweden(lat DECIMAL, lon DECIMAL)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN lat BETWEEN 55.34 AND 69.06 AND lon BETWEEN 10.96 AND 24.17;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SCHEMA COMPLETE
-- ============================================================================

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Sweden Wildfire Simulation Schema Created Successfully';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - messages (existing)';
    RAISE NOTICE '  - fire_detections (global)';
    RAISE NOTICE '  - fire_detections_sweden';
    RAISE NOTICE '  - no2_measurements_sweden';
    RAISE NOTICE '  - weather_sweden';
    RAISE NOTICE '  - landcover_sweden';
    RAISE NOTICE '  - topography_sweden';
    RAISE NOTICE '  - simulations';
    RAISE NOTICE '  - simulation_results';
    RAISE NOTICE '============================================================';
END $$;
