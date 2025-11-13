# Project Architecture Explanation

## 📋 Table of Contents
1. [Project Structure](#project-structure)
2. [Why pnpm from Root?](#why-pnpm-from-root)
3. [Simulation Model & Pickle File](#simulation-model--pickle-file)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)

---

## 🏗️ Project Structure

```
Caffein/
├── package.json                    # ROOT package.json (workspace orchestrator)
├── pnpm-workspace.yaml            # Defines monorepo structure
├── pnpm-lock.yaml                 # Lock file for all dependencies
├── requirements.txt               # Python dependencies
├── venv/                          # Python virtual environment
│
├── backend/                       # Flask API Server
│   ├── app.py                     # Main Flask application
│   ├── db.py                      # MongoDB connection
│   ├── logger.py                  # Logging utilities
│   └── package.json               # Backend-specific config (if any)
│
├── frontend/                      # Vue.js + Vite Application
│   ├── package.json               # Frontend dependencies (Vue, Leaflet, etc.)
│   ├── vite.config.ts             # Vite bundler config
│   ├── src/
│   │   ├── App.vue                # Root component (imports FireSimulator)
│   │   ├── main.ts                # Vue app entry point
│   │   └── components/
│   │       ├── FireSimulator.vue  # Main dual-mode component
│   │       └── MapView.vue        # Old component (not used)
│   └── dist/                      # Built files (after `pnpm build`)
│
├── data/
│   ├── NASA-MODIS-DATA/
│   │   ├── combined-countries.csv # Historical fire data (2019-2024)
│   │   └── *.csv                  # Individual country/year files
│   └── fire_impact_model.pkl      # Your trained model (NOT CURRENTLY USED)
│
└── notebooks/
    ├── wildfire_prediction.ipynb  # Your analysis notebook
    ├── datalookup.ipynb
    └── fetchdata.ipynb
```

---

## ⚙️ Why pnpm from Root?

### The Old Way (Before)
```bash
cd frontend
pnpm install
pnpm run dev
```
**Problems:**
- ❌ Only starts frontend
- ❌ Backend must be started separately
- ❌ No coordination between services
- ❌ Easy to forget to start backend

### The New Way (Now)
```bash
# From root directory
pnpm dev
```
**Benefits:**
- ✅ Starts BOTH backend AND frontend together
- ✅ Single command for entire development workflow
- ✅ Uses `concurrently` to run multiple processes
- ✅ Coordinated logging with color-coded output

### How It Works

**1. Root `package.json` acts as orchestrator:**
```json
{
  "scripts": {
    "setup": "pnpm install && pnpm run setup:venv && pnpm run setup:backend",
    "setup:venv": "python3 -m venv venv",
    "setup:backend": "bash -c 'source venv/bin/activate && pip install -r requirements.txt'",
    "dev": "pnpm run dev:start",
    "dev:start": "concurrently ... \"pnpm run dev:backend\" \"pnpm run dev:frontend\"",
    "dev:backend": "bash -c 'source venv/bin/activate && cd backend && python app.py'",
    "dev:frontend": "cd frontend && pnpm run dev"
  }
}
```

**2. When you run `pnpm dev`:**
```
pnpm dev
  └─> pnpm run dev:start
       └─> concurrently
            ├─> pnpm run dev:backend
            │    └─> source venv/bin/activate
            │         └─> cd backend
            │              └─> python app.py (Flask server starts on :5000)
            │
            └─> pnpm run dev:frontend
                 └─> cd frontend
                      └─> pnpm run dev (Vite server starts on :5176)
```

**3. Concurrently output:**
```
[backend]  10:28:27 | INFO | api | Starting Flask server on port 5000
[frontend] VITE v7.2.2 ready in 1256 ms
[frontend] ➜ Local: http://localhost:5176/
[backend]  * Running on http://127.0.0.1:5000
```

### Monorepo Structure

The `pnpm-workspace.yaml` file defines this as a monorepo:
```yaml
packages:
  - 'frontend'
  - 'backend'
```

This means:
- Root `package.json` manages workspace-level commands
- `frontend/package.json` has Vue/Vite dependencies
- `backend/package.json` (optional) could have Node tools if needed
- One `pnpm install` in root installs ALL dependencies for all packages

---

## 🔬 Simulation Model & Pickle File

### **IMPORTANT: Your .pkl file is NOT being used currently!**

Here's what's happening:

### What You Built in Notebooks

In `notebooks/wildfire_prediction.ipynb`, you likely:
1. Trained a Prophet model for wildfire prediction
2. Created simulation functions
3. Saved everything to `data/fire_impact_model.pkl`

Example of what might be in the pickle:
```python
fire_model = {
    'calculate_distance_km': <function>,
    'pollution_concentration_at_distance': <function>,
    'simulate_fire_pollution_impact': <function>,
    'prophet_model': <Prophet model object>,
    'scaler': <sklearn scaler>,
    # ... other dependencies
}

with open('data/fire_impact_model.pkl', 'wb') as f:
    pickle.dump(fire_model, f)
```

### What the Backend Tries to Do

**File:** `backend/app.py` (lines 20-106)

```python
# Load fire impact model
fire_model = None
try:
    with open('../data/fire_impact_model.pkl', 'rb') as f:
        fire_model = pickle.load(f)
    logger.info("Fire impact model loaded successfully from pickle file")
except Exception as e:
    logger.warning(f"Could not load fire impact model from pickle: {e}")
    logger.info("Using simple fallback simulation model")
    # Create fallback model dictionary
    fire_model = {
        'simulate_fire_pollution_impact': simulate_fire_pollution_impact_simple
    }
```

### Why Your Pickle Fails to Load

When you see this log:
```
WARNING | api | Could not load fire impact model from pickle: 
Can't get attribute 'pollution_concentration_at_distance' on <module '__main__'...
```

**Reason:** Pickle files save references to functions, not the actual function code. When unpickling:
- Python looks for `pollution_concentration_at_distance` function in the current module
- But that function was defined in your notebook, not in `app.py`
- Pickle can't find the function → loading fails

### Current Solution: Fallback Model

Instead of failing completely, I created a **fallback simulation model**:

**File:** `backend/app.py` (lines 26-92)

```python
def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance using Haversine formula"""
    R = 6371  # Earth's radius in km
    # ... Haversine math
    return R * c

def simulate_fire_pollution_impact_simple(fire_lat, fire_lon, frp, 
                                          grid_resolution=0.15, radius_km=150):
    """
    Simple pollution dispersion model using Gaussian plume approximation.
    Creates a grid of points around the fire and estimates pollution levels.
    """
    import pandas as pd
    
    grid_data = []
    
    # Create grid around fire
    lat_range = radius_km / 111.0
    lon_range = radius_km / (111.0 * math.cos(math.radians(fire_lat)))
    
    # For each grid point:
    for lat in range(...):
        for lon in range(...):
            dist_km = calculate_distance_km(fire_lat, fire_lon, lat, lon)
            
            # Gaussian dispersion model
            distance_factor = math.exp(-dist_km / 50.0)
            base_intensity = (frp / 500.0) * distance_factor
            
            # Calculate each pollutant
            grid_data.append({
                'latitude': lat,
                'longitude': lon,
                'distance_km': dist_km,
                'CO': base_intensity * 0.8 * random_variation,
                'NO2': base_intensity * 0.6 * random_variation,
                'AAI': base_intensity * 0.7 * random_variation,
                # ... etc
            })
    
    return pd.DataFrame(grid_data)
```

### Where the Simulation Call is Made

**API Endpoint:** `/api/simulate-fire`

**File:** `backend/app.py` (lines 304-345)

```python
@app.route('/api/simulate-fire', methods=['POST'])
def simulate_fire_pollution():
    # Get user inputs
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    frp = data.get('frp', 100)
    pollutants = data.get('pollutants', ['CO', 'NO2', 'AAI'])
    
    # Run simulation using the model
    df_result = fire_model['simulate_fire_pollution_impact'](  # ← THE CALL
        fire_lat=lat,
        fire_lon=lon,
        frp=frp,
        grid_resolution=0.15,
        radius_km=150
    )
    
    # Convert to JSON and return
    return jsonify({
        'grid_data': [...],
        'summary': {...},
        'status': 'success'
    })
```

Since `fire_model` uses the fallback, it's actually calling:
```python
fire_model['simulate_fire_pollution_impact']
  = simulate_fire_pollution_impact_simple  # ← Our simple Gaussian model
```

### To Use Your Actual Pickle File

You need to modify the pickle saving in your notebook to include all functions:

**In your notebook:**
```python
# Option 1: Save functions as source code (better approach)
import dill  # pip install dill (better than pickle for functions)

fire_model = {
    'simulate_fire_pollution_impact': your_simulation_function,
    'calculate_distance_km': your_distance_function,
    # ... include ALL helper functions
}

with open('../data/fire_impact_model.pkl', 'wb') as f:
    dill.dump(fire_model, f)

# Option 2: Just save the data/model, not functions
# Then implement the functions directly in app.py
```

Or better yet, **move the functions from notebook to a Python module:**

```python
# Create: backend/simulation_model.py
def simulate_fire_pollution_impact(fire_lat, fire_lon, frp, ...):
    # Your actual simulation logic from notebook
    pass

# Then in app.py:
from simulation_model import simulate_fire_pollution_impact
```

---

## 🔄 Data Flow

### View Mode Flow

```
User Action: "Load Fires" button clicked
  │
  ├─> Frontend (FireSimulator.vue)
  │    └─> loadHistoricalFires()
  │         └─> axios.get('http://localhost:5000/api/fires-csv', {
  │              params: { start_date, end_date, min_frp }
  │            })
  │
  ├─> Backend (app.py)
  │    └─> @app.route('/api/fires-csv')
  │         └─> pd.read_csv('../data/NASA-MODIS-DATA/combined-countries.csv')
  │              └─> Filter by date/FRP
  │                   └─> Return JSON: { data: [...fires], count: N }
  │
  └─> Frontend receives data
       └─> displayHistoricalFires()
            └─> Create L.circleMarker for each fire
                 └─> Add to Leaflet map
```

### Simulation Mode Flow

```
User Action: Clicks on map
  │
  ├─> Frontend (FireSimulator.vue)
  │    └─> handleMapClick(e)
  │         └─> Get lat/lng from click
  │              └─> runSimulation(lat, lng)
  │                   └─> axios.post('http://localhost:5000/api/simulate-fire', {
  │                        latitude: lat,
  │                        longitude: lng,
  │                        frp: frp,
  │                        pollutants: ['CO', 'NO2', 'AAI']
  │                      })
  │
  ├─> Backend (app.py)
  │    └─> @app.route('/api/simulate-fire', methods=['POST'])
  │         └─> fire_model['simulate_fire_pollution_impact'](...)
  │              └─> simulate_fire_pollution_impact_simple()  ← FALLBACK
  │                   └─> Generate grid points (534 points)
  │                        └─> Calculate pollution at each point
  │                             └─> Return: { 
  │                                  grid_data: [{lat, lon, CO, NO2, ...}, ...],
  │                                  summary: {fire_location, peaks, ...}
  │                                }
  │
  └─> Frontend receives simulation data
       └─> displayHeatmap(pollutant)
            └─> Create L.heatLayer with pollution data
                 └─> Overlay on Leaflet map
```

---

## 🛠️ Technology Stack

### Frontend
```
Vue 3 (TypeScript)
  └─> Vite (build tool & dev server)
       ├─> Leaflet (interactive maps)
       │    └─> Leaflet.heat (heatmap plugin)
       ├─> Axios (HTTP client)
       └─> TypeScript (type safety)
```

**Key Files:**
- `frontend/src/main.ts` - Vue app bootstrap
- `frontend/src/App.vue` - Root component
- `frontend/src/components/FireSimulator.vue` - Main UI
- `frontend/vite.config.ts` - Build configuration

### Backend
```
Python 3
  └─> Flask (web framework)
       ├─> Flask-CORS (enable cross-origin requests)
       ├─> Pandas (CSV data processing)
       ├─> NumPy (numerical calculations)
       ├─> PyMongo (MongoDB - optional)
       └─> Python-dotenv (environment variables)
```

**Key Files:**
- `backend/app.py` - Flask API routes
- `backend/db.py` - Database connection
- `backend/logger.py` - Logging setup
- `requirements.txt` - Python dependencies

### Data Layer
```
NASA MODIS Fire Data (CSV)
  ├─> 3559 fire records (2019-2024)
  ├─> Scandinavia region (Sweden, Norway, Finland, Denmark, Baltics)
  └─> Columns: acq_date, latitude, longitude, frp, brightness, confidence, etc.

Simulation Model
  ├─> Gaussian plume dispersion
  ├─> 6 pollutants: CO, NO2, CH4, HCHO, SO2, AAI
  └─> Grid-based calculation (~500 points per simulation)
```

### Development Tools
```
pnpm
  ├─> Monorepo workspace management
  ├─> Fast dependency installation
  └─> Efficient disk usage (symlinks)

Concurrently
  └─> Run backend + frontend simultaneously

Python venv
  └─> Isolated Python environment
```

---

## 📊 Summary Answers

### Q1: Why pnpm from root?
**Answer:** 
- Root `package.json` orchestrates the entire development workflow
- Single command (`pnpm dev`) starts both backend and frontend
- Workspace structure keeps frontend dependencies separate but coordinated
- Better developer experience: one command instead of two terminals

### Q2: Is the .pkl file being used?
**Answer:** 
- **NO**, your pickle file is NOT currently being used
- Loading fails because pickle references functions not present in `app.py`
- Backend uses a **fallback Gaussian model** instead
- The fallback is defined in `app.py` (lines 26-92)
- Simulation call is in `/api/simulate-fire` endpoint (line 333)

### Q3: Where is the simulation call made?
**Answer:**
```
Frontend click → handleMapClick() → runSimulation()
  → axios.post('/api/simulate-fire', {lat, lon, frp, pollutants})
    → Backend: @app.route('/api/simulate-fire')
      → fire_model['simulate_fire_pollution_impact'](...)
        → simulate_fire_pollution_impact_simple()  ← THE ACTUAL CALL
          → Returns DataFrame with pollution grid
            → Converted to JSON
              → Sent back to frontend
                → Displayed as heatmap
```

---

## 🎯 Key Takeaways

1. **Monorepo Structure**: Root manages both frontend and backend as one coordinated project
2. **Your Model NOT Used**: Pickle loading fails, fallback model runs instead
3. **Simple but Functional**: Fallback uses basic physics (Gaussian dispersion) which works well for demos
4. **Two Data Sources**: 
   - View Mode: Real CSV data from your notebooks
   - Simulation Mode: Calculated on-the-fly using fallback model
5. **Architecture is Scalable**: Easy to add more features, swap models, or integrate new data sources

Would you like me to help you integrate your actual pickle model, or are you happy with the fallback for now?
