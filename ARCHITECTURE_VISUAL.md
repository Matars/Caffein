# Visual Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                    http://localhost:5176                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │              FireSimulator.vue                        │     │
│  │                                                       │     │
│  │  ┌──────────────┐  ┌────────────────┐               │     │
│  │  │ 👁️ View Mode │  │ 🧪 Simulation  │               │     │
│  │  │              │  │     Mode       │               │     │
│  │  └──────────────┘  └────────────────┘               │     │
│  │                                                       │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │         Leaflet Map                          │    │     │
│  │  │  - Tile Layer (OpenStreetMap)               │    │     │
│  │  │  - CircleMarkers (historical fires)         │    │     │
│  │  │  - HeatLayer (simulation pollution)         │    │     │
│  │  └─────────────────────────────────────────────┘    │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                            │ HTTP
                            │ (Axios)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FLASK BACKEND SERVER                         │
│                    http://localhost:5000                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                    app.py                            │      │
│  │                                                      │      │
│  │  API Endpoints:                                      │      │
│  │                                                      │      │
│  │  GET  /api/health                                   │      │
│  │  GET  /api/fires-csv?start_date&end_date&min_frp   │      │
│  │  POST /api/simulate-fire {lat, lon, frp}           │      │
│  │                                                      │      │
│  │  ┌────────────────────────────────────────┐         │      │
│  │  │  fire_model (Dictionary)              │         │      │
│  │  │                                        │         │      │
│  │  │  'simulate_fire_pollution_impact':    │         │      │
│  │  │     simulate_fire_pollution_impact_   │         │      │
│  │  │     simple()                          │         │      │
│  │  │                                        │         │      │
│  │  │  ← Fallback Gaussian Model            │         │      │
│  │  │  ← NOT from pickle file!              │         │      │
│  │  └────────────────────────────────────────┘         │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ File I/O
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                             │
│                                                                 │
│  ┌────────────────────────────────────────┐                    │
│  │  data/NASA-MODIS-DATA/                │                    │
│  │    combined-countries.csv              │                    │
│  │                                        │                    │
│  │  ✅ ACTIVELY USED                      │                    │
│  │  - 3559 fire records                  │                    │
│  │  - View Mode data source              │                    │
│  └────────────────────────────────────────┘                    │
│                                                                 │
│  ┌────────────────────────────────────────┐                    │
│  │  data/fire_impact_model.pkl           │                    │
│  │                                        │                    │
│  │  ❌ NOT USED (loading fails)           │                    │
│  │  - Your trained model from notebook   │                    │
│  │  - Can't unpickle functions           │                    │
│  └────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPER MACHINE                            │
│                                                                 │
│  Terminal: pnpm dev                                             │
│       │                                                         │
│       └──> package.json (root)                                 │
│              │                                                  │
│              ├─> dev:backend                                   │
│              │    │                                             │
│              │    ├─> source venv/bin/activate                 │
│              │    └─> cd backend && python app.py              │
│              │         │                                        │
│              │         └─> Flask Server (:5000)                │
│              │              - Loads fallback model             │
│              │              - Reads CSV files                  │
│              │              - Serves API endpoints             │
│              │                                                 │
│              └─> dev:frontend                                  │
│                   │                                             │
│                   └─> cd frontend && pnpm run dev              │
│                        │                                        │
│                        └─> Vite Dev Server (:5176)             │
│                             - Hot Module Reload                │
│                             - Compiles Vue components          │
│                             - Serves static assets             │
│                                                                 │
│  Both processes run concurrently with colored output:          │
│  [backend]  INFO | api | Starting Flask server...              │
│  [frontend] VITE v7.2.2 ready in 1256 ms                       │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: View Mode

```
USER                FRONTEND              BACKEND                DATA
 │                     │                     │                    │
 │  Click "Load       │                     │                    │
 │  Fires"            │                     │                    │
 ├──────────────────> │                     │                    │
 │                     │                     │                    │
 │                     │  GET /api/fires-csv │                    │
 │                     │  ?start_date=...    │                    │
 │                     ├──────────────────> │                    │
 │                     │                     │                    │
 │                     │                     │  Read CSV          │
 │                     │                     ├─────────────────> │
 │                     │                     │                    │
 │                     │                     │  3559 records      │
 │                     │                     │ <─────────────────┤
 │                     │                     │                    │
 │                     │                     │  Filter by date    │
 │                     │                     │  Filter by FRP     │
 │                     │                     │  (541 records)     │
 │                     │                     │                    │
 │                     │  JSON: {data: [...]}│                    │
 │                     │ <──────────────────┤                    │
 │                     │                     │                    │
 │                     │  Create markers     │                    │
 │                     │  for each fire      │                    │
 │                     │                     │                    │
 │  See fires on      │                     │                    │
 │  map               │                     │                    │
 │ <──────────────────┤                     │                    │
```

## Data Flow: Simulation Mode

```
USER                FRONTEND              BACKEND              MODEL
 │                     │                     │                   │
 │  Click on map      │                     │                   │
 │  at (62°N, 15°E)   │                     │                   │
 ├──────────────────> │                     │                   │
 │                     │                     │                   │
 │                     │  POST /api/simulate-│                   │
 │                     │  fire               │                   │
 │                     │  {lat:62, lon:15,   │                   │
 │                     │   frp:150}          │                   │
 │                     ├──────────────────> │                   │
 │                     │                     │                   │
 │                     │                     │  Call model       │
 │                     │                     ├────────────────> │
 │                     │                     │                   │
 │                     │                     │  fire_model[      │
 │                     │                     │   'simulate_...'  │
 │                     │                     │  ]()              │
 │                     │                     │                   │
 │                     │                     │  ↓                │
 │                     │                     │                   │
 │                     │                     │  simulate_fire_   │
 │                     │                     │  pollution_       │
 │                     │                     │  impact_simple()  │
 │                     │                     │                   │
 │                     │                     │  - Calculate      │
 │                     │                     │    grid (150km)   │
 │                     │                     │  - Gaussian       │
 │                     │                     │    dispersion     │
 │                     │                     │  - 534 points     │
 │                     │                     │  - 6 pollutants   │
 │                     │                     │                   │
 │                     │                     │  DataFrame        │
 │                     │                     │ <────────────────┤
 │                     │                     │                   │
 │                     │  JSON: {grid_data:  │                   │
 │                     │   [{lat,lon,CO,NO2, │                   │
 │                     │     AAI,...},...],  │                   │
 │                     │   summary:{...}}    │                   │
 │                     │ <──────────────────┤                   │
 │                     │                     │                   │
 │                     │  Create heatmap     │                   │
 │                     │  layer              │                   │
 │                     │                     │                   │
 │  See pollution     │                     │                   │
 │  heatmap           │                     │                   │
 │ <──────────────────┤                     │                   │
```

## File System: Who Accesses What?

```
Caffein/
│
├── package.json              ← pnpm reads this (root orchestrator)
├── pnpm-workspace.yaml       ← pnpm reads this (workspace config)
├── requirements.txt          ← pip reads this (Python deps)
│
├── venv/                     ← Python interpreter uses this
│   ├── bin/python            ← Backend runs from here
│   └── lib/...               ← Flask, pandas, numpy installed here
│
├── backend/
│   └── app.py                ← Python reads/executes this
│        │
│        ├── Tries to read: ../data/fire_impact_model.pkl ❌
│        └── Reads: ../data/NASA-MODIS-DATA/combined-countries.csv ✅
│
├── frontend/
│   ├── package.json          ← pnpm installs Vue, Vite, Leaflet
│   ├── src/
│   │   ├── App.vue           ← Vite compiles this
│   │   └── components/
│   │       └── FireSimulator.vue ← Vite compiles this
│   │                              ← Browser runs the compiled JS
│   └── dist/                 ← Vite outputs here (after build)
│
└── data/
    ├── NASA-MODIS-DATA/
    │   └── combined-countries.csv ← Backend reads this ✅
    └── fire_impact_model.pkl      ← Backend tries but fails ❌
```

## Process Tree

```
Terminal
└── pnpm dev
    └── concurrently
        ├── Process 1: pnpm run dev:backend
        │   └── bash
        │       └── source venv/bin/activate
        │           └── python backend/app.py
        │               ├── Flask Server (port 5000)
        │               ├── Thread: MongoDB connection attempt
        │               └── Main: Handle HTTP requests
        │
        └── Process 2: pnpm run dev:frontend
            └── vite
                ├── Vite Dev Server (port 5176)
                ├── File Watcher (Hot Module Reload)
                └── HTTP Server (serve Vue app)
```

## Why Your Pickle Doesn't Work

```
notebooks/wildfire_prediction.ipynb
│
├── Cell: Define function
│   def pollution_concentration_at_distance(dist, frp):
│       return frp / (dist ** 2)  # Example
│
├── Cell: Create model dict
│   fire_model = {
│       'simulate_fire_pollution_impact': my_simulation_func,
│       'pollution_concentration_at_distance': pollution_concentration_at_distance
│   }
│
└── Cell: Save to pickle
    with open('../data/fire_impact_model.pkl', 'wb') as f:
        pickle.dump(fire_model, f)

    What gets saved:
    {
        'simulate_fire_pollution_impact': <reference to function at 0x7f8a9b...>,
        'pollution_concentration_at_distance': <reference to function at 0x7f8a9c...>
    }
    
    ⚠️ Pickle saves REFERENCES, not the actual code!

backend/app.py
│
└── with open('../data/fire_impact_model.pkl', 'rb') as f:
        fire_model = pickle.load(f)
        
    Python tries to find:
    - pollution_concentration_at_distance in current module
    - But it's not defined in app.py!
    - Error: Can't get attribute 'pollution_concentration_at_distance'
    
    ❌ Loading FAILS
    
    ✅ Fallback kicks in:
    fire_model = {
        'simulate_fire_pollution_impact': simulate_fire_pollution_impact_simple
    }
```

## Summary

1. **pnpm from root** = Orchestrate entire project (backend + frontend) with one command
2. **Your .pkl file** = NOT used (unpickling fails due to missing function references)
3. **Simulation call** = `backend/app.py` line 333 → calls fallback function, not your model
4. **View Mode** = Uses real CSV data from your notebooks ✅
5. **Simulation Mode** = Uses simple Gaussian model (not your pickle) ✅

Both work, just not using your trained model yet!
