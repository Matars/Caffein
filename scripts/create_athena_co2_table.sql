-- Create Athena external table for CAMS CO2 Parquet data
-- Run this in AWS Athena console after uploading Parquet files

CREATE EXTERNAL TABLE IF NOT EXISTS co2 (
    latitude DOUBLE,
    longitude DOUBLE,
    co2_concentration DOUBLE,
    time_value DOUBLE,
    co2_units STRING,
    time_units STRING,
    level INT
)
PARTITIONED BY (
    year INT,
    month INT,
    day INT,
    hour INT
)
STORED AS PARQUET
LOCATION 's3://caffine-analytics-storage-eu-central-1-925314695663/raw/cds/co2/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY',
    'has_encrypted_data'='false'
);

-- After creating table, run this to discover partitions:
MSCK REPAIR TABLE co2;

-- Or add partitions manually if needed:
-- ALTER TABLE co2 ADD PARTITION (year=2023, month=1, day=1, hour=0)
-- LOCATION 's3://caffine-analytics-storage-eu-central-1-925314695663/raw/cds/co2/year=2023/month=01/day=01/hour=00/';

-- Test query (get CO2 for a specific location and date range):
-- SELECT 
--     year, month, day, hour,
--     latitude, longitude, 
--     co2_concentration,
--     co2_units
-- FROM co2
-- WHERE year = 2023 
--   AND month = 1
--   AND day = 1
--   AND latitude BETWEEN 55 AND 70
--   AND longitude BETWEEN 10 AND 25
-- ORDER BY hour
-- LIMIT 100;

-- Query to get average daily CO2:
-- SELECT 
--     year, month, day,
--     AVG(co2_concentration) as avg_co2,
--     COUNT(*) as num_measurements
-- FROM co2
-- WHERE year = 2023
--   AND month = 1
--   AND latitude BETWEEN 55 AND 70
--   AND longitude BETWEEN 10 AND 25
-- GROUP BY year, month, day
-- ORDER BY year, month, day;
