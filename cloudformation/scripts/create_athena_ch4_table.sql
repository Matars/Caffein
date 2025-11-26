-- Create Athena external table for CAMS CH4 Parquet data
-- Run this in AWS Athena console after uploading Parquet files

CREATE EXTERNAL TABLE IF NOT EXISTS ch4 (
    latitude DOUBLE,
    longitude DOUBLE,
    ch4_concentration DOUBLE,
    time_value DOUBLE,
    ch4_units STRING,
    time_units STRING,
    level INT
)
PARTITIONED BY (
    year INT,
    month INT,
    day INT
)
STORED AS PARQUET
LOCATION 's3://caffine-analytics-storage-eu-central-1-925314695663/raw/cds/ch4/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY',
    'has_encrypted_data'='false'
);

-- After creating table, run this to discover partitions:
MSCK REPAIR TABLE ch4;

-- Or add partitions manually if needed:
-- ALTER TABLE ch4 ADD PARTITION (year=2023, month=1, day=1)
-- LOCATION 's3://caffine-analytics-storage-eu-central-1-925314695663/raw/cds/ch4/year=2023/month=01/day=01/';

-- Test query (get CH4 for a specific location and date range):
-- SELECT 
--     year, month, day,
--     latitude, longitude, 
--     ch4_concentration,
--     ch4_units
-- FROM ch4
-- WHERE year = 2023 
--   AND month = 1
--   AND latitude BETWEEN 55 AND 70
--   AND longitude BETWEEN 10 AND 25
-- LIMIT 100;
