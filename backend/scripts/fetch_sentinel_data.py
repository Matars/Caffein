#!/usr/bin/env python3
"""
Script to fetch Sentinel-5P atmospheric data for 2024
Run this after authenticating with: earthengine authenticate
"""

from googleEarth import SentinelDataFetcher
import sys
import os

# Add parent directory to path to import googleEarth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Fetch CO and CH4 data for 2024"""

    # Initialize the fetcher
    fetcher = SentinelDataFetcher(project_id="quick-composite-408320")

    # Set the region to Italy
    fetcher.initialize_region('Italy')

    # Define output paths
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data'
    )

    print("="*60)
    print("Fetching Sentinel-5P Atmospheric Data for 2024")
    print("="*60)

    # Fetch CO data (Carbon Monoxide - proxy for emissions)
    # Note: Sentinel-5P doesn't have CO2, but CO is a combustion indicator
    co_output = os.path.join(data_dir, 'sentinel_co_2024.csv')
    print(f"\n[1/2] Fetching CO data...")
    df_co = fetcher.fetch_co_data(
        start_date='2024-01-01',
        end_date='2024-12-31',
        output_csv=co_output
    )

    # Fetch CH4 data (Methane)
    ch4_output = os.path.join(data_dir, 'sentinel_ch4_2024.csv')
    print(f"\n[2/2] Fetching CH4 data...")
    df_ch4 = fetcher.fetch_ch4_data(
        start_date='2024-01-01',
        end_date='2024-12-31',
        output_csv=ch4_output
    )

    # Summary
    print("\n" + "="*60)
    print("✓ Data Fetch Complete!")
    print("="*60)
    print(f"CO data:  {len(df_co):4d} daily records → {co_output}")
    print(f"CH4 data: {len(df_ch4):4d} daily records → {ch4_output}")
    print("="*60)


if __name__ == "__main__":
    main()
