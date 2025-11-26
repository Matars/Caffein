#!/usr/bin/env python3
"""
Export Sentinel-5P L3 CH4 annual mean (2024) tiled to GCS, then copy to AWS S3.

Requirements (install in Glue job environment):
 - earthengine-api
 - google-cloud-storage
 - boto3

Environment variables (or edit below):
 - EE_SERVICE_ACCOUNT  : service account email (e.g. sa@project.iam.gserviceaccount.com)
 - EE_KEY_FILE         : path to service account JSON key accessible in the job (e.g. /tmp/sa-key.json)
 - GCS_BUCKET          : target GCS bucket name for EE exports
 - GCS_PREFIX          : folder/prefix inside GCS (e.g. s5p_ch4/2024)
 - S3_BUCKET           : target AWS S3 bucket name
 - S3_PREFIX           : prefix inside S3 (e.g. s5p_ch4/2024)
Optional:
 - TILE_DEG            : tile degrees (default 60)
 - SCALE               : export scale in meters (default 7000)
 - YEAR                : year to export (default 2024)
 - POLL_FOR_COMPLETION : "true" to poll tasks until completion, default "false"
"""

import os
import math
import time
import json
import tempfile
import ee
import boto3
from google.cloud import storage as gcs_storage
from botocore.exceptions import BotoCoreError, ClientError

import sys
import subprocess

target = '/tmp/packages'
os.makedirs(target, exist_ok=True)

subprocess.check_call([
    sys.executable, '-m', 'pip', 'install',
    '--upgrade',
    '--target', target,
    'rasterio==1.3.6', 'numpy==1.25.2'
])

sys.path.insert(0, target)

import rasterio

# --- Config via env (defaults)
secret_name = "gee_service_account_key"
client = boto3.client("secretsmanager", region_name='eu-central-1')
response = client.get_secret_value(SecretId=secret_name)
secret_string = response['SecretString']

# write to /tmp so Earth Engine can read it
key_file_path = '/tmp/gee-key.json'
with open(key_file_path, 'w') as f:
    f.write(secret_string)

os.environ['EE_KEY_FILE'] = key_file_path

SERVICE_ACCOUNT = os.environ.get('EE_SERVICE_ACCOUNT', 'gee-exporter@possible-aspect-472714-r2.iam.gserviceaccount.com')
KEY_FILE = os.environ.get('EE_KEY_FILE')
GCS_BUCKET = os.environ.get('GCS_BUCKET','my-gee-exports-shankar')
GCS_PREFIX = os.environ.get('GCS_PREFIX', 'google/s5p_ch4/2024')
S3_BUCKET = os.environ.get('S3_BUCKET','caff-dump')
S3_PREFIX = os.environ.get('S3_PREFIX', 'google/s5p_ch4/2024')

TILE_DEG = float(os.environ.get('TILE_DEG', 60))   # recommended: 60 (18 tiles), or 30/20 for more parallelism
SCALE = int(os.environ.get('SCALE', 7000))
YEAR = int(os.environ.get('YEAR', 2024))
POLL_FOR_COMPLETION = True  # Set to True to wait for tasks to complete, False to launch and exit

# basic checks
if not SERVICE_ACCOUNT or not KEY_FILE or not GCS_BUCKET or not S3_BUCKET:
    raise SystemExit("Set EE_SERVICE_ACCOUNT, EE_KEY_FILE, GCS_BUCKET, and S3_BUCKET environment variables.")

YEAR = int(os.environ.get('YEAR', 2024))
TILE_DEG = float(os.environ.get('TILE_DEG', 20))
SCALE = int(os.environ.get('SCALE', 10000))
POLL_FOR_COMPLETION = os.environ.get('POLL_FOR_COMPLETION', 'False').lower()=='true'

# -----------------------------
# Initialize Earth Engine
# -----------------------------
ee.Initialize(ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE))

# -----------------------------
# Build CH4 image collection (daily data)
# -----------------------------
CH4_BAND = 'CH4_column_volume_mixing_ratio_dry_air'
UNC_BAND = 'CH4_column_volume_mixing_ratio_dry_air_uncertainty'
UNC_THRESHOLD = 0.2  # example

# Export mode: 'annual' for yearly mean, 'daily' for day-by-day
EXPORT_MODE = 'daily'  # Change to 'annual' for yearly mean

# Batch processing settings to avoid hitting task queue limits
MAX_CONCURRENT_TASKS = 2500  # Leave some buffer below 3000 limit
BATCH_WAIT_TIME = 300  # Wait 5 minutes between batches if queue is full

collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CH4') \
    .filterDate(f'{YEAR}-01-01', f'{YEAR}-12-31')

def mask_by_unc(img):
    unc = img.select(UNC_BAND).multiply(2)
    return img.updateMask(unc.lt(UNC_THRESHOLD))

masked_col = collection.map(mask_by_unc).select(CH4_BAND)

if EXPORT_MODE == 'annual':
    annual_mean = masked_col.mean()
    images_to_export = [{'image': annual_mean, 'date_suffix': ''}]
else:  # daily mode
    # Get list of all images with dates
    images_to_export = []
    image_list = masked_col.toList(masked_col.size())
    size = masked_col.size().getInfo()
    print(f"[INFO] Found {size} daily images in {YEAR}")
    
    for i in range(min(size, 365)):  # Limit to avoid too many API calls
        img = ee.Image(image_list.get(i))
        date_str = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        images_to_export.append({'image': img, 'date': date_str})
    
    print(f"[INFO] Prepared {len(images_to_export)} daily images for export")

# -----------------------------
# Export: per-country or global tiles
# -----------------------------
COUNTRIES = 'Albania, Andorra, Austria, Belarus, Belgium, Bosnia and Herzegovina, Bulgaria, Croatia, Cyprus, Czech Republic, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Iceland, Ireland, Italy, Kosovo, Latvia, Liechtenstein, Lithuania, Luxembourg, Malta, Moldova, Monaco, Montenegro, Netherlands, North Macedonia, Norway, Poland, Portugal, Romania, Russia, San Marino, Serbia, Slovakia, Slovenia, Spain, Sweden, Switzerland, Turkey, Ukraine, United Kingdom, Vatican City'
COUNTRY_FC = 'USDOS/LSIB_SIMPLE/2017'

def sanitize_name(name):
    # safe folder/name: lower, spaces -> _, keep alnum and _
    return ''.join([c if (c.isalnum() or c == '_' ) else '_' for c in name.strip().lower().replace(' ', '_')])

def find_country_geometry(country_name):
    """Try to find a country geometry in several ways. Returns ee.Geometry or None."""
    fc = ee.FeatureCollection(COUNTRY_FC)
    # try exact string contains on common property names
    candidates = ['country_na', 'country', 'name', 'Country', 'COUNTRY']
    filtered = None
    for prop in candidates:
        try:
            filtered = fc.filter(ee.Filter.stringContains(prop, country_name))
            if int(filtered.size().getInfo()) > 0:
                return filtered.geometry()
        except Exception:
            # property not found or server-side issue, continue
            filtered = None
            continue
    # as a final attempt, try filtering on any property that equals the name
    try:
        filtered = fc.filter(ee.Filter.eq('country_na', country_name))
        if int(filtered.size().getInfo()) > 0:
            return filtered.geometry()
    except Exception:
        pass
    return None

def get_active_task_count():
    """Get count of active (RUNNING, READY) tasks in the queue."""
    try:
        tasks = ee.data.getTaskList()
        active = sum(1 for t in tasks if t['state'] in ('RUNNING', 'READY'))
        return active
    except Exception as e:
        print(f"[WARN] Could not get task count: {e}")
        return 0

def wait_for_queue_space(target_space=500):
    """Wait until there's enough space in the task queue."""
    while True:
        active = get_active_task_count()
        available = MAX_CONCURRENT_TASKS - active
        print(f"[QUEUE] Active tasks: {active}, Available slots: {available}")
        
        if available >= target_space:
            return available
        
        print(f"[QUEUE] Waiting {BATCH_WAIT_TIME}s for queue space...")
        time.sleep(BATCH_WAIT_TIME)

tasks_info = []
if COUNTRIES:
    country_list = [c.strip() for c in COUNTRIES.split(',') if c.strip()]
    print(f"[INFO] Running per-country export for: {country_list}")
    
    for country in country_list:
        print(f"[INFO] Locating geometry for country: {country}")
        geom = find_country_geometry(country)
        if geom is None:
            print(f"[WARN] Could not find geometry for '{country}', skipping.")
            continue
        safe = sanitize_name(country)
        
        try:
            region = geom.bounds().getInfo()['coordinates']
        except Exception:
            # fallback to geometry coordinates (may be more complex)
            region = geom.getInfo().get('coordinates')
        
        # Export each image (daily or annual)
        for idx, img_info in enumerate(images_to_export):
            # Check queue space every 50 tasks
            if idx % 50 == 0:
                available = wait_for_queue_space(target_space=100)
                print(f"[INFO] Proceeding with {available} slots available")
            
            img = img_info['image']
            img_clip = img.clip(geom)
            
            if EXPORT_MODE == 'daily':
                date_str = img_info['date']
                desc = f"S5P_CH4_{date_str}_{safe}"
                file_prefix = f"{GCS_PREFIX}/{safe}/{date_str}/S5P_CH4_{date_str}_{safe}"
            else:
                desc = f"S5P_CH4_{YEAR}_{safe}"
                file_prefix = f"{GCS_PREFIX}/{safe}/S5P_CH4_{YEAR}_{safe}"

            try:
                task = ee.batch.Export.image.toCloudStorage(
                    image=img_clip,
                    description=desc,
                    bucket=GCS_BUCKET,
                    fileNamePrefix=file_prefix,
                    region=region,
                    scale=SCALE,
                    crs='EPSG:4326',
                    maxPixels=1e13,
                    shardSize=2048,
                    fileFormat='GeoTIFF',
                    formatOptions={'cloudOptimized': True}
                )
                task.start()
                
                task_entry = {
                    'description': desc,
                    'task_id': task.id,
                    'gcs_prefix': file_prefix,
                    'country': country
                }
                if EXPORT_MODE == 'daily':
                    task_entry['date'] = img_info['date']
                
                tasks_info.append(task_entry)
                print(f"[LAUNCHED] {desc} id={task.id} -> gs://{GCS_BUCKET}/{file_prefix}*.tif")
            
            except Exception as e:
                if "Too many tasks" in str(e):
                    print(f"[QUEUE FULL] Waiting for space...")
                    wait_for_queue_space(target_space=500)
                    # Retry this task
                    try:
                        task = ee.batch.Export.image.toCloudStorage(
                            image=img_clip,
                            description=desc,
                            bucket=GCS_BUCKET,
                            fileNamePrefix=file_prefix,
                            region=region,
                            scale=SCALE,
                            crs='EPSG:4326',
                            maxPixels=1e13,
                            shardSize=2048,
                            fileFormat='GeoTIFF',
                            formatOptions={'cloudOptimized': True}
                        )
                        task.start()
                        task_entry = {
                            'description': desc,
                            'task_id': task.id,
                            'gcs_prefix': file_prefix,
                            'country': country
                        }
                        if EXPORT_MODE == 'daily':
                            task_entry['date'] = img_info['date']
                        tasks_info.append(task_entry)
                        print(f"[LAUNCHED] {desc} id={task.id} (retry)")
                    except Exception as e2:
                        print(f"[ERROR] Failed to launch {desc}: {e2}")
                else:
                    print(f"[ERROR] Failed to launch {desc}: {e}")
else:
    # default: global tiles (legacy behavior)
    def make_tiles(tile_deg):
        tiles = []
        lon_steps = int(math.ceil(360.0 / tile_deg))
        lat_steps = int(math.ceil(180.0 / tile_deg))
        for i in range(lon_steps):
            lon_min = -180.0 + i * tile_deg
            lon_max = min(lon_min + tile_deg, 180.0)
            for j in range(lat_steps):
                lat_min = -90.0 + j * tile_deg
                lat_max = min(lat_min + tile_deg, 90.0)
                geom = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max], proj='EPSG:4326', geodesic=False)
                tiles.append({
                    'idx': f"{i:02d}_{j:02d}",
                    'geometry': geom
                })
        return tiles

    tiles = make_tiles(TILE_DEG)
    print(f"[INFO] Generated {len(tiles)} tiles with TILE_DEG={TILE_DEG}")

    # Export tiles to GCS
    for t in tiles:
        geom = t['geometry']
        tile_idx = t['idx']
        img_clip = annual_mean.clip(geom)
        desc = f"S5P_CH4_{YEAR}_tile_{tile_idx}"
        file_prefix = f"{GCS_PREFIX}/S5P_CH4_{YEAR}_tile_{tile_idx}"

        task = ee.batch.Export.image.toCloudStorage(
            image=img_clip,
            description=desc,
            bucket=GCS_BUCKET,
            fileNamePrefix=file_prefix,
            region=geom.getInfo()['coordinates'],
            scale=SCALE,
            crs='EPSG:4326',
            maxPixels=1e13,
            shardSize=2048,
            fileFormat='GeoTIFF',
            formatOptions={'cloudOptimized': True}
        )
        task.start()
        tasks_info.append({'description': desc, 'task_id': task.id, 'gcs_prefix': file_prefix})
        print(f"[LAUNCHED] {desc} id={task.id} -> gs://{GCS_BUCKET}/{file_prefix}*.tif")

# -----------------------------
# Optional: poll tasks
# -----------------------------
def poll_tasks(tasks, poll_interval=60, timeout_minutes=180):
    print(f"[POLL] Starting task polling for up to {timeout_minutes} minutes.")
    start_ts = time.time()
    deadline = start_ts + timeout_minutes*60
    remaining = {t['task_id']: t for t in tasks}
    while remaining and time.time() < deadline:
        for tid, tinfo in list(remaining.items()):
            status = ee.data.getTaskStatus(tid)[0]
            state = status.get('state', 'UNKNOWN')
            print(f"[TASK POLL] {tinfo['description']} id={tid} state={state}")
            if state in ('COMPLETED', 'FAILED', 'CANCELLED'):
                remaining.pop(tid)
        if remaining:
            time.sleep(poll_interval)
    if remaining:
        print(f"[POLL] Timeout reached with {len(remaining)} tasks still in-progress or queued.")
    else:
        print("[POLL] All tasks finished.")

if POLL_FOR_COMPLETION:
    poll_tasks(tasks_info, poll_interval=60, timeout_minutes=180)

# -----------------------------
# Copy GCS -> S3 and convert to structured JSON with coordinates
# -----------------------------
def gcs_to_s3_convert_json(gcs_bucket, gcs_prefix, s3_bucket, s3_prefix, country_name, date_str=None):
    """
    Download GeoTIFF from GCS, extract CH4 data with lat/lon coordinates,
    and upload structured JSON to S3.
    """
    gcs_client = gcs_storage.Client.from_service_account_json(KEY_FILE)
    bucket = gcs_client.bucket(gcs_bucket)
    blobs = list(gcs_client.list_blobs(gcs_bucket, prefix=gcs_prefix))
    print(f"[GCS] Found {len(blobs)} objects with prefix {gcs_prefix}")

    s3_client = boto3.client('s3')
    all_data_points = []

    for blob in blobs:
        gcs_name = blob.name
        filename = os.path.basename(gcs_name)
        
        # Skip if not a TIFF file
        if not filename.endswith('.tif'):
            continue
            
        s3_key_tif = f"{s3_prefix}/{filename}"
        
        # download TIFF to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmpf:
            tmp_path = tmpf.name
        
        try:
            blob.download_to_filename(tmp_path)

            # upload TIFF to S3
            s3_client.upload_file(tmp_path, s3_bucket, s3_key_tif)
            print(f"[OK] {filename} -> TIFF uploaded to S3")

            # Extract data with coordinates
            with rasterio.open(tmp_path) as src:
                # Read the CH4 data array
                ch4_data = src.read(1)
                
                # Get the affine transform to convert pixel coords to lat/lon
                transform = src.transform
                
                # Get dimensions
                height, width = ch4_data.shape
                
                # Extract data points with coordinates
                print(f"[INFO] Extracting {height}x{width} data points for {country_name}...")
                
                for row in range(height):
                    for col in range(width):
                        value = float(ch4_data[row, col])
                        
                        # Skip nodata values (typically very large negative or NaN)
                        if value == src.nodata or value < 0 or not (-90 <= value <= 90):
                            continue
                        
                        # Convert pixel coordinates to geographic coordinates
                        lon, lat = transform * (col, row)
                        
                        # Create data point
                        data_point = {
                            'country': country_name,
                            'latitude': round(lat, 6),
                            'longitude': round(lon, 6),
                            'ch4_concentration': round(value, 6),
                            'year': YEAR,
                            'unit': 'ppbv'  # parts per billion by volume
                        }
                        if date_str:
                            data_point['date'] = date_str
                        all_data_points.append(data_point)
                
                print(f"[INFO] Extracted {len(all_data_points)} valid data points from {filename}")

        finally:
            # safely remove temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # Upload consolidated JSON for this country (and date if daily)
    if all_data_points:
        safe_country = sanitize_name(country_name)
        if date_str:
            json_key = f"{s3_prefix}/{safe_country}_ch4_data_{date_str}.json"
        else:
            json_key = f"{s3_prefix}/{safe_country}_ch4_data_{YEAR}.json"
        
        json_data = {
            'country': country_name,
            'year': YEAR,
            'data_points': all_data_points,
            'total_points': len(all_data_points),
            'metadata': {
                'source': 'COPERNICUS/S5P/OFFL/L3_CH4',
                'band': 'CH4_column_volume_mixing_ratio_dry_air',
                'unit': 'ppbv',
                'uncertainty_threshold': UNC_THRESHOLD
            }
        }
        if date_str:
            json_data['date'] = date_str
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as jf:
            json.dump(json_data, jf, indent=2)
            json_path = jf.name
        
        s3_client.upload_file(json_path, s3_bucket, json_key)
        os.remove(json_path)
        print(f"[JSON] Uploaded {len(all_data_points)} data points to s3://{s3_bucket}/{json_key}")
        
        result = {'country': country_name, 's3_key': json_key, 'data_points': len(all_data_points)}
        if date_str:
            result['date'] = date_str
        return result
    else:
        print(f"[WARN] No valid data points found for {country_name}")
        return None

# Run conversion for all countries
manifest_entries = []
for t in tasks_info:
    gcs_pref = t['gcs_prefix']
    country = t.get('country', 'Unknown')
    date_str = t.get('date', None)
    result = gcs_to_s3_convert_json(GCS_BUCKET, gcs_pref, S3_BUCKET, S3_PREFIX, country, date_str)
    if result:
        manifest_entries.append(result)

# Upload final manifest
if manifest_entries:
    manifest_key = f"{S3_PREFIX}/manifest_all_countries_{YEAR}.json"
    s3_client = boto3.client('s3')
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as mf:
        json.dump({
            'year': YEAR,
            'countries': manifest_entries,
            'total_countries': len(manifest_entries),
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }, mf, indent=2)
        mf_path = mf.name
    s3_client.upload_file(mf_path, S3_BUCKET, manifest_key)
    os.remove(mf_path)
    print(f"[MANIFEST] Written to s3://{S3_BUCKET}/{manifest_key}")

print("[DONE] All tiles processed, TIFF + JSON uploaded to S3")