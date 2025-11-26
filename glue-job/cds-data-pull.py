# cds-data-pull.py
# put cdsapi>=0.7.7 as additional-python-package
import os
import io
import zipfile
import boto3
import cdsapi
from botocore.exceptions import ClientError
import json

# --- config (pass via job args, env vars, or secrets) ---
S3_BUCKET = os.environ.get('TARGET_S3_BUCKET', 'caff-dump')
S3_PREFIX = os.environ.get('TARGET_S3_PREFIX', 'cds/co2')
# Example: "uid:apikey" or use cdsapi client config file

# setup clients
s3 = boto3.client('s3')
# create cdsapi client using api key from env or file
client = cdsapi.Client()

dataset = "cams-global-greenhouse-gas-inversion"
request = {
    "variable": "carbon_dioxide",
    "quantity": "concentration",
    "input_observations": "surface",
    "time_aggregation": "instantaneous",
    "version": "latest",
    "year": ["2023"],
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ]
}

def upload_zip_members_to_s3(zip_bytes, bucket, prefix):
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        for member in zf.namelist():
            with zf.open(member) as member_f:
                key = prefix + member
                # upload_fileobj handles streaming; good for large members
                s3.upload_fileobj(member_f, bucket, key)
                print(f"uploaded {key}")

def main():
    # cdsapi Client.retrieve(...).download() supports a target filename.
    # We'll download into memory if zip size is reasonable; otherwise write to /tmp
    target_path = '/tmp/cds_download-co2.zip'
    client.retrieve(dataset, request).download(target=target_path)
    with open(target_path, 'rb') as f:
        zip_bytes = f.read()
    upload_zip_members_to_s3(zip_bytes, S3_BUCKET, S3_PREFIX)
    print("done")

if __name__ == '__main__':
    main()
