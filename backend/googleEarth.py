"""
Google Earth Engine Data Fetcher
Fetches Sentinel-5P atmospheric data (CO, CH4, etc.) and saves to CSV
"""

import ee
import pandas as pd
import math
from statistics import mean
from datetime import datetime
import os


class SentinelDataFetcher:
    """Fetch and process Sentinel-5P atmospheric data from Google Earth Engine"""

    def __init__(self, project_id="quick-composite-408320"):
        """
        Initialize Earth Engine with project ID

        Args:
            project_id: GEE project ID (run `earthengine authenticate` first)
        """
        self.project_id = project_id
        self.italy_geom = None

    def authenticate(self):
        """Authenticate and initialize Earth Engine"""
        try:
            ee.Authenticate()
            ee.Initialize(project=self.project_id)
            print(
                f"✓ Earth Engine initialized with project: {self.project_id}")
        except Exception as e:
            print(
                f"Authentication failed. Run 'earthengine authenticate' in terminal first.")
            raise e

    def initialize_region(self, country='Italy'):
        """
        Set up the geographic region for data collection

        Args:
            country: Country name (default: 'Italy')
        """
        try:
            country_fc = ee.FeatureCollection('FAO/GAUL/2015/level0').filter(
                ee.Filter.eq('ADM0_NAME', country)
            )
            self.italy_geom = country_fc.geometry()
            print(f"✓ Region set to: {country}")
        except Exception as e:
            print(f"Failed to load region: {e}")
            raise e

    def filter_valid_images(self, collection, region, band_name):
        """
        Filter collection to only images with valid data over the region

        Args:
            collection: Earth Engine ImageCollection
            region: Earth Engine Geometry
            band_name: Name of the band to check

        Returns:
            Filtered ImageCollection with only valid images
        """
        def add_pixel_count(img):
            count = img.select(band_name).reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=region,
                scale=10000,
                bestEffort=True,
                maxPixels=1e9
            ).get(band_name)
            return img.set('pixel_count', count)

        ic_with_counts = collection.map(add_pixel_count)
        return ic_with_counts.filter(ee.Filter.gt('pixel_count', 0))

    def fetch_co_data(self, start_date, end_date, output_csv=None):
        """
        Fetch CO (Carbon Monoxide) data from Sentinel-5P

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_csv: Path to save CSV (optional)

        Returns:
            pandas DataFrame with daily mean CO values
        """
        if self.italy_geom is None:
            self.initialize_region()

        band_name = 'CO_column_number_density'

        print(f"\nFetching CO data from {start_date} to {end_date}...")

        # Load Sentinel-5P CO collection
        collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CO') \
            .select(band_name) \
            .filterDate(start_date, end_date)

        total_images = collection.size().getInfo()
        print(f"Total images in collection: {total_images}")

        # Filter to valid images over Italy
        valid_collection = self.filter_valid_images(
            collection, self.italy_geom, band_name)
        valid_size = valid_collection.size().getInfo()
        print(f"Images with data over Italy: {valid_size}")

        if valid_size == 0:
            print("⚠ No valid images found for this period")
            return pd.DataFrame()

        # Add mean value for each image
        def add_italy_mean(img):
            mean_val = img.select(band_name).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.italy_geom,
                scale=10000,
                bestEffort=True,
                maxPixels=1e9
            ).get(band_name)
            return img.set({
                'date_str': img.date().format('YYYY-MM-dd'),
                'italy_mean': mean_val
            })

        processed = valid_collection.map(add_italy_mean)

        # Extract dates and means
        dates = processed.aggregate_array('date_str').getInfo()
        means = processed.aggregate_array('italy_mean').getInfo()

        # Build results list
        results = []
        for date, mean_val in zip(dates, means):
            if mean_val is not None:
                results.append({'date': date, 'mean_co': mean_val})

        print(f"✓ Found {len(results)} valid observations")

        # Aggregate by date (multiple overpasses per day)
        by_date = {}
        for r in results:
            d = r['date']
            v = r['mean_co']
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                continue
            by_date.setdefault(d, []).append(v)

        # Create DataFrame with daily averages
        rows = [(d, mean(vals)) for d, vals in by_date.items()]
        if not rows:
            print("⚠ No numeric rows to build DataFrame")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=['date', 'mean_co'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        print(f"\n✓ DataFrame created with {len(df)} daily records")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"\nSummary statistics:\n{df['mean_co'].describe()}")

        # Save to CSV if path provided
        if output_csv:
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"\n✓ Data saved to: {output_csv}")

        return df

    def fetch_ch4_data(self, start_date, end_date, output_csv=None):
        """
        Fetch CH4 (Methane) data from Sentinel-5P

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_csv: Path to save CSV (optional)

        Returns:
            pandas DataFrame with daily mean CH4 values
        """
        if self.italy_geom is None:
            self.initialize_region()

        band_name = 'CH4_column_volume_mixing_ratio_dry_air'

        print(f"\nFetching CH4 data from {start_date} to {end_date}...")

        # Load Sentinel-5P CH4 collection
        collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CH4') \
            .select(band_name) \
            .filterDate(start_date, end_date)

        total_images = collection.size().getInfo()
        print(f"Total images in collection: {total_images}")

        # Filter to valid images over Italy
        valid_collection = self.filter_valid_images(
            collection, self.italy_geom, band_name)
        valid_size = valid_collection.size().getInfo()
        print(f"Images with data over Italy: {valid_size}")

        if valid_size == 0:
            print("⚠ No valid images found for this period")
            return pd.DataFrame()

        # Add mean value for each image
        def add_italy_mean(img):
            mean_val = img.select(band_name).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=self.italy_geom,
                scale=10000,
                bestEffort=True,
                maxPixels=1e9
            ).get(band_name)
            return img.set({
                'date_str': img.date().format('YYYY-MM-dd'),
                'italy_mean': mean_val
            })

        processed = valid_collection.map(add_italy_mean)

        # Extract dates and means
        dates = processed.aggregate_array('date_str').getInfo()
        means = processed.aggregate_array('italy_mean').getInfo()

        # Build results list
        results = []
        for date, mean_val in zip(dates, means):
            if mean_val is not None:
                results.append({'date': date, 'mean_ch4': mean_val})

        print(f"✓ Found {len(results)} valid observations")

        # Aggregate by date (multiple overpasses per day)
        by_date = {}
        for r in results:
            d = r['date']
            v = r['mean_ch4']
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                continue
            by_date.setdefault(d, []).append(v)

        # Create DataFrame with daily averages
        rows = [(d, mean(vals)) for d, vals in by_date.items()]
        if not rows:
            print("⚠ No numeric rows to build DataFrame")
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=['date', 'mean_ch4'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        print(f"\n✓ DataFrame created with {len(df)} daily records")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"\nSummary statistics:\n{df['mean_ch4'].describe()}")

        # Save to CSV if path provided
        if output_csv:
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"\n✓ Data saved to: {output_csv}")

        return df


def main():
    """Main execution function"""
    # Initialize fetcher
    fetcher = SentinelDataFetcher(project_id="quick-composite-408320")

    # Authenticate (comment out if already authenticated)
    # fetcher.authenticate()

    # Initialize Earth Engine (if already authenticated)
    ee.Initialize(project=fetcher.project_id)

    # Set region
    fetcher.initialize_region('Italy')

    # Fetch CO data for 2024 (Note: Sentinel-5P has CO, not CO2)
    # CO is a proxy for combustion/emissions which relates to carbon emissions
    output_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'sentinel_co_2024.csv'
    )

    df_co = fetcher.fetch_co_data(
        start_date='2024-01-01',
        end_date='2024-12-31',
        output_csv=output_path
    )

    # Optional: Also fetch CH4 data
    ch4_output_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'data',
        'sentinel_ch4_2024.csv'
    )

    df_ch4 = fetcher.fetch_ch4_data(
        start_date='2024-01-01',
        end_date='2024-12-31',
        output_csv=ch4_output_path
    )

    print("\n" + "="*60)
    print("Data fetch complete!")
    print(f"CO records: {len(df_co)}")
    print(f"CH4 records: {len(df_ch4)}")
    print("="*60)


if __name__ == "__main__":
    main()
