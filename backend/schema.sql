-- PostgreSQL Schema for Caffein Project (NASA FIRMS Data)
-- Run this on your PostgreSQL instance

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS fire_detections CASCADE;
DROP TABLE IF EXISTS messages CASCADE;

-- Messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fire detections table (NASA FIRMS satellite data)
-- Supports both MODIS and VIIRS instruments
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

-- Indexes for better query performance
CREATE INDEX idx_fire_detections_coordinates ON fire_detections(latitude, longitude);
CREATE INDEX idx_fire_detections_acq_date ON fire_detections(acq_date);
CREATE INDEX idx_fire_detections_instrument ON fire_detections(instrument);
CREATE INDEX idx_fire_detections_satellite ON fire_detections(satellite);
CREATE INDEX idx_fire_detections_confidence ON fire_detections(confidence);
CREATE INDEX idx_fire_detections_datetime ON fire_detections(acq_date, acq_time);
CREATE INDEX idx_messages_type ON messages(type);

-- Insert default message
INSERT INTO messages (type, content) VALUES
    ('hello', 'Hello from Caffein - NASA FIRMS Fire Detection System!');
