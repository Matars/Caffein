#!/usr/bin/env python3
"""
Glue ETL script to read large JSON files (arrays) from S3 and write partitioned Parquet.

Expected glue job arguments:
--SOURCE_S3_PATH     e.g. s3://caff-dump/data/*.json
--TARGET_S3_PATH     e.g. s3://caffine-analytics-storage-eu-central-1-925314695663/raw/nasa/wild_fire
--JOB_NAME
--TempDir            S3 temp dir for Glue (e.g. s3://<temp-bucket>/tmp/)

This script uses Spark (Glue) to read JSON with multiline support, casts fields,
extracts year/month/day from acq_date and writes partitioned parquet with snappy.
"""
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from pyspark.context import SparkContext
from pyspark.sql import functions as F
import sys

args = getResolvedOptions(sys.argv,
                          ['JOB_NAME', 'SOURCE_S3_PATH', 'TARGET_S3_PATH', 'TempDir'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

SOURCE = args['SOURCE_S3_PATH']
TARGET = args['TARGET_S3_PATH'].rstrip('/')

# Tune these depending on data size and Glue worker type
REPARTITION_NUM = 200

def main():

    print(f"Reading from {SOURCE}")


    from pyspark.sql.types import DoubleType, StringType, StructType, StructField, ArrayType

    # Define the schema for a single fire record
    record_schema = StructType([
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("acq_date", StringType(), True),
        StructField("acq_time", StringType(), True),
        StructField("confidence", StringType(), True),
        StructField("frp", DoubleType(), True),
        StructField("version", StringType(), True),
        StructField("instrument", StringType(), True),
        StructField("daynight", StringType(), True),
        StructField("bright_t31", DoubleType(), True),
        StructField("type", StringType(), True),
        StructField("scan", DoubleType(), True),
        StructField("brightness", DoubleType(), True),
        StructField("track", DoubleType(), True),
        StructField("satellite", StringType(), True)
    ])

    array_schema = ArrayType(record_schema)

    try:
        # Read all JSON files using glob pattern and multiline option
        raw = spark.read.option('multiline', 'true').json("s3://caff-dump/data/*.json")
        print("Raw schema after read:")
        raw.printSchema()
        print("Raw sample after read:")
        raw.show(1, truncate=False)

        # If the top-level is an array, explode it
        from pyspark.sql.types import ArrayType
        if len(raw.schema.fields) == 1 and isinstance(raw.schema.fields[0].dataType, ArrayType):
            df = raw.select(F.explode(F.col(raw.columns[0])).alias('row')).select('row.*')
        else:
            df = raw
    except Exception as e:
        print(f"ERROR: Failed to read JSON. Exception: {e}")
        print("Check that your input files are valid JSON arrays and not empty.")
        sys.exit(1)

    print("Schema after explode:")
    df.printSchema()
    print("Sample records after explode:")
    df.show(5)

    # Cast fields to expected types (redundant, but safe)
    df = (df
        .withColumn("latitude", F.col("latitude").cast(DoubleType()))
        .withColumn("longitude", F.col("longitude").cast(DoubleType()))
        .withColumn("acq_date", F.col("acq_date").cast(StringType()))
        .withColumn("acq_time", F.col("acq_time").cast(StringType()))
        .withColumn("confidence", F.col("confidence").cast(StringType()))
        .withColumn("frp", F.col("frp").cast(DoubleType()))
        .withColumn("version", F.col("version").cast(StringType()))
        .withColumn("instrument", F.col("instrument").cast(StringType()))
        .withColumn("daynight", F.col("daynight").cast(StringType()))
        .withColumn("bright_t31", F.col("bright_t31").cast(DoubleType()))
        .withColumn("type", F.col("type").cast(StringType()))
        .withColumn("scan", F.col("scan").cast(DoubleType()))
        .withColumn("brightness", F.col("brightness").cast(DoubleType()))
        .withColumn("track", F.col("track").cast(DoubleType()))
        .withColumn("satellite", F.col("satellite").cast(StringType()))
    )

    # Normalize field types and add partition columns
    df = df.withColumn('acq_date', F.to_date(F.col('acq_date'), 'yyyy-MM-dd'))
    print("Sample records after acq_date conversion:")
    df.show(5)

    # Extract year/month/day for partitioning
    df = df.withColumn('year', F.year(F.col('acq_date')))
    df = df.withColumn('month', F.format_string('%02d', F.month(F.col('acq_date'))))
    df = df.withColumn('day', F.format_string('%02d', F.dayofmonth(F.col('acq_date'))))

    # Repartition to a reasonable number to control file sizes
    df = df.repartition(REPARTITION_NUM, 'year', 'month', 'day')

    # Write partitioned Parquet with snappy compression
    out_path = TARGET
    print(f"Writing partitioned parquet to {out_path} ...")
    (df.write
       .mode('append')
       .partitionBy('year', 'month', 'day')
       .option('compression', 'snappy')
       .parquet(out_path))

    print('Write complete')


if __name__ == '__main__':
    main()
