#!/bin/bash

# Quick test script for the new View Mode

echo "🧪 Testing View Mode Updates..."
echo ""

# Check if backend is running
echo "1️⃣ Checking if backend is accessible..."
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend is not running. Start it with: pnpm dev"
    exit 1
fi

echo ""
echo "2️⃣ Testing new /api/fires/csv endpoint..."

# Test 1: Basic query
echo ""
echo "   Test 1: Load fires from January 2024"
response=$(curl -s "http://localhost:5001/api/fires/csv?start_date=2024-01-01&end_date=2024-01-31")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')

if [ -n "$count" ]; then
    echo "   ✅ Success! Found $count fires"
else
    echo "   ❌ Failed to get data"
    echo "   Response: $response"
fi

# Test 2: With FRP filter
echo ""
echo "   Test 2: High intensity fires (FRP >= 100)"
response=$(curl -s "http://localhost:5001/api/fires/csv?start_date=2024-01-01&end_date=2024-12-31&min_frp=100")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')

if [ -n "$count" ]; then
    echo "   ✅ Success! Found $count high-intensity fires"
else
    echo "   ❌ Failed to get data"
fi

# Test 3: Full year
echo ""
echo "   Test 3: All 2024 fires"
response=$(curl -s "http://localhost:5001/api/fires/csv?start_date=2024-01-01&end_date=2024-12-31&limit=100")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')

if [ -n "$count" ]; then
    echo "   ✅ Success! Found $count fires (limited to 100)"
else
    echo "   ❌ Failed to get data"
fi

echo ""
echo "3️⃣ Checking CSV file..."
if [ -f "data/NASA-MODIS-DATA/combined-countries.csv" ]; then
    lines=$(wc -l < data/NASA-MODIS-DATA/combined-countries.csv)
    echo "   ✅ CSV file exists with $lines lines"
else
    echo "   ❌ CSV file not found at data/NASA-MODIS-DATA/combined-countries.csv"
fi

echo ""
echo "🎉 Testing complete!"
echo ""
echo "Next steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Make sure you're in View Mode (👁️ button)"
echo "   3. Select date range (e.g., 2024-01-01 to 2024-01-31)"
echo "   4. Click '🔥 Load Fires'"
echo "   5. You should see fire markers on the map!"
