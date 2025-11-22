"""
Test script to verify Sweden wildfire simulation setup
Run this after completing the quickstart guide
"""
import sys
import os
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

# Test 1: Python packages
def test_python_packages():
    print_header("Test 1: Python Package Installation")

    packages = [
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('sklearn', 'Scikit-learn'),
        ('geopandas', 'GeoPandas'),
        ('rasterio', 'Rasterio'),
        ('ee', 'Google Earth Engine'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('flask', 'Flask'),
    ]

    all_passed = True
    for module_name, display_name in packages:
        try:
            __import__(module_name)
            print_success(f"{display_name} installed")
        except ImportError:
            print_error(f"{display_name} NOT installed")
            all_passed = False

    return all_passed

# Test 2: Configuration files
def test_configuration():
    print_header("Test 2: Configuration Files")

    try:
        from config.sweden import (
            SWEDEN_BOUNDS, GRID_RESOLUTION, MAP_CENTER,
            is_in_sweden, get_grid_cell
        )

        print_success("Sweden configuration loaded")
        print(f"  Bounds: {SWEDEN_BOUNDS['south']:.2f}°N to {SWEDEN_BOUNDS['north']:.2f}°N")
        print(f"  Grid: {GRID_RESOLUTION}° resolution")

        # Test helper functions
        stockholm_in = is_in_sweden(59.3, 18.1)
        london_in = is_in_sweden(51.5, -0.1)

        if stockholm_in and not london_in:
            print_success("Bounds checking works correctly")
        else:
            print_error("Bounds checking failed")
            return False

        return True
    except Exception as e:
        print_error(f"Configuration error: {e}")
        return False

# Test 3: Data files
def test_data_files():
    print_header("Test 3: Data Files")

    data_dir = Path('data/sweden')
    if not data_dir.exists():
        print_warning(f"Sweden data directory doesn't exist yet: {data_dir}")
        print("  Run: python scripts/filter_firms_sweden.py")
        return False

    # Check for Sweden FIRMS data
    firms_files = list(data_dir.glob('*_sweden.json'))
    if firms_files:
        print_success(f"Found {len(firms_files)} Sweden FIRMS file(s)")

        # Load and count total records
        import json
        total_records = 0
        for file in firms_files:
            with open(file, 'r') as f:
                data = json.load(f)
                count = len(data)
                total_records += count
                size_mb = file.stat().st_size / (1024**2)
                print(f"  - {file.name}: {count:,} records ({size_mb:.2f} MB)")

        print_success(f"Total fire detections: {total_records:,}")
    else:
        print_warning("No Sweden FIRMS data found")
        print("  Run: python scripts/filter_firms_sweden.py")

    # Check for NO2 data
    no2_dir = Path('data/sweden/sentinel5p_no2')
    if no2_dir.exists():
        no2_files = list(no2_dir.glob('*.json'))
        if no2_files:
            print_success(f"Found {len(no2_files)} NO2 data file(s)")
        else:
            print_warning("NO2 directory exists but is empty")
    else:
        print_warning("NO2 data not downloaded yet")
        print("  Run: python scripts/download_sentinel5p_sweden.py --start 2024-07-01 --end 2024-07-31")

    return True

# Test 4: Database connection
def test_database():
    print_header("Test 4: Database Connection")

    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text
        import os

        load_dotenv()

        # Get DB config
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'caffein')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(database_url, connect_args={'connect_timeout': 5})

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print_success(f"Connected to PostgreSQL at {db_host}:{db_port}")

            # Check if Sweden tables exist
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE '%sweden%'
                ORDER BY table_name;
            """))

            tables = [row[0] for row in result]

            if tables:
                print_success(f"Found {len(tables)} Sweden table(s):")
                for table in tables:
                    print(f"  - {table}")
            else:
                print_warning("No Sweden tables found")
                print("  Run: psql -U postgres -d caffein -f schema_sweden.sql")

            return len(tables) > 0

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print("  Make sure PostgreSQL is running and .env is configured")
        return False

# Test 5: Earth Engine
def test_earth_engine():
    print_header("Test 5: Google Earth Engine")

    try:
        import ee
        ee.Initialize()
        print_success("Earth Engine initialized successfully")

        # Try a simple operation
        point = ee.Geometry.Point([18.0, 59.3])  # Stockholm
        print_success("Can create geometries")

        return True
    except Exception as e:
        print_error(f"Earth Engine initialization failed: {e}")
        print("  Run: earthengine authenticate")
        return False

# Test 6: Grid system
def test_grid_system():
    print_header("Test 6: Grid System")

    try:
        from config.sweden import get_grid_cell, get_cell_center, is_in_sweden

        # Test major Swedish cities
        cities = [
            ("Stockholm", 59.3293, 18.0686),
            ("Gothenburg", 57.7089, 11.9746),
            ("Malmö", 55.6050, 13.0038),
            ("Uppsala", 59.8586, 17.6389),
            ("Kiruna", 67.8558, 20.2253),
        ]

        print("Testing grid conversion for Swedish cities:")
        all_valid = True

        for name, lat, lon in cities:
            in_sweden = is_in_sweden(lat, lon)
            grid = get_grid_cell(lat, lon)

            if in_sweden and grid:
                lat_idx, lon_idx = grid
                center_lat, center_lon = get_cell_center(lat_idx, lon_idx)
                print(f"  {name:12} → Grid[{lat_idx:3d}, {lon_idx:3d}] "
                      f"→ Center({center_lat:.2f}, {center_lon:.2f})")
            else:
                print_error(f"  {name} not properly detected in Sweden!")
                all_valid = False

        if all_valid:
            print_success("Grid system working correctly")

        return all_valid

    except Exception as e:
        print_error(f"Grid system test failed: {e}")
        return False

# Main test runner
def main():
    print(f"\n{Colors.BLUE}")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*15 + "SWEDEN WILDFIRE SIMULATION SETUP TEST" + " "*16 + "║")
    print("╚" + "═"*68 + "╝")
    print(Colors.END)

    tests = [
        ("Python Packages", test_python_packages),
        ("Configuration", test_configuration),
        ("Data Files", test_data_files),
        ("Database", test_database),
        ("Earth Engine", test_earth_engine),
        ("Grid System", test_grid_system),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print_header("Test Summary")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        if passed:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"Results: {passed_count}/{total_count} tests passed")
    print(f"{'='*70}{Colors.END}\n")

    if passed_count == total_count:
        print(f"{Colors.GREEN}")
        print("╔" + "═"*68 + "╗")
        print("║" + " "*18 + "✓ ALL TESTS PASSED! READY TO CODE!" + " "*18 + "║")
        print("╚" + "═"*68 + "╝")
        print(Colors.END)
        print("\n Next steps:")
        print("  1. Start building fire spread model")
        print("  2. See SWEDEN_IMPLEMENTATION_PLAN.md for details")
        return 0
    else:
        print(f"{Colors.YELLOW}")
        print("╔" + "═"*68 + "╗")
        print("║" + " "*12 + "⚠ SOME TESTS FAILED - REVIEW QUICKSTART GUIDE" + " "*12 + "║")
        print("╚" + "═"*68 + "╝")
        print(Colors.END)
        print("\n Fix failed tests before proceeding")
        print("  See SWEDEN_QUICKSTART.md for setup instructions")
        return 1

if __name__ == "__main__":
    sys.exit(main())
