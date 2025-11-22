# Quick Reference: Architecture Q&A

## Your Questions Answered

### Q1: Why run `pnpm dev` from root instead of `cd frontend && pnpm dev`?

**Short Answer:** To start BOTH backend and frontend together with one command.

**Before (manual):**
```bash
# Terminal 1
source venv/bin/activate
cd backend
python app.py

# Terminal 2
cd frontend
pnpm dev
```

**Now (automated):**
```bash
# One terminal, one command
pnpm dev
```

**How it works:**
```
Root package.json
  → pnpm dev script
    → concurrently (runs multiple commands in parallel)
      → Backend: source venv && python backend/app.py
      → Frontend: cd frontend && pnpm run dev
```

**Benefits:**
- ✅ Single command starts entire stack
- ✅ Color-coded output shows which service logs what
- ✅ Both processes managed together (Ctrl+C kills both)
- ✅ New developers just run `pnpm dev` and it works

---

### Q2: Are we using the .pkl file I built in my notebooks?

**Short Answer:** **NO**, the pickle file is NOT being used currently.

**What happens:**

1. **Backend tries to load it:**
   ```python
   # app.py line 96
   with open('../data/fire_impact_model.pkl', 'rb') as f:
       fire_model = pickle.load(f)
   ```

2. **Loading FAILS:**
   ```
   WARNING | api | Could not load fire impact model from pickle: 
   Can't get attribute 'pollution_concentration_at_distance' on <module '__main__'...
   ```

3. **Fallback activates:**
   ```python
   # app.py line 102
   logger.info("Using simple fallback simulation model")
   fire_model = {
       'simulate_fire_pollution_impact': simulate_fire_pollution_impact_simple
   }
   ```

**Why it fails:**
- Pickle saves function **references**, not actual code
- Functions were defined in your Jupyter notebook
- When `app.py` tries to unpickle, it looks for those functions in `app.py`
- They don't exist there → error
- Fallback model is used instead

**Current simulation uses:**
- ❌ NOT your pickle file
- ✅ `simulate_fire_pollution_impact_simple()` function defined in `app.py`

---

### Q3: Where is the simulation call being made?

**Short Answer:** In `backend/app.py` at line 333, inside the `/api/simulate-fire` endpoint.

**Call stack:**

```
1. User clicks map in browser
   └─> FireSimulator.vue, line 364
       └─> handleMapClick(e)

2. Frontend calls API
   └─> FireSimulator.vue, line 392
       └─> axios.post('http://localhost:5000/api/simulate-fire', {...})

3. Backend receives request
   └─> backend/app.py, line 304
       └─> @app.route('/api/simulate-fire', methods=['POST'])

4. Simulation is called
   └─> backend/app.py, line 333
       └─> df_result = fire_model['simulate_fire_pollution_impact'](
                fire_lat=lat,
                fire_lon=lon,
                frp=frp,
                grid_resolution=0.15,
                radius_km=150
           )

5. Which function actually runs?
   └─> backend/app.py, line 26
       └─> simulate_fire_pollution_impact_simple()
           └─> This is the fallback Gaussian model
           └─> NOT from your pickle file!

6. Returns data
   └─> backend/app.py, line 343
       └─> return jsonify({ grid_data: [...], summary: {...} })

7. Frontend displays heatmap
   └─> FireSimulator.vue, line 403
       └─> displayHeatmap(pollutant)
```

**Exact file locations:**

| Step | File | Line | What |
|------|------|------|------|
| User action | `frontend/src/components/FireSimulator.vue` | 364 | `handleMapClick()` |
| API call | `frontend/src/components/FireSimulator.vue` | 392 | `axios.post()` |
| Backend endpoint | `backend/app.py` | 304 | `@app.route('/api/simulate-fire')` |
| **THE SIMULATION CALL** | `backend/app.py` | 333 | `fire_model['simulate_fire_pollution_impact'](...)` |
| Fallback function | `backend/app.py` | 26 | `def simulate_fire_pollution_impact_simple()` |
| Return response | `backend/app.py` | 343 | `return jsonify(...)` |
| Display heatmap | `frontend/src/components/FireSimulator.vue` | 403 | `displayHeatmap()` |

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────────┐
│  Q1: Why pnpm from root?                                    │
│                                                             │
│  pnpm dev (root)                                            │
│     │                                                       │
│     ├─> Starts Backend (Flask on :5000)                   │
│     └─> Starts Frontend (Vite on :5176)                   │
│                                                             │
│  One command, two servers! 🎉                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Q2: Is my .pkl file being used?                            │
│                                                             │
│  Your pickle file:                                          │
│  data/fire_impact_model.pkl                                 │
│     │                                                       │
│     ├─> Backend tries to load it ❌                         │
│     ├─> Loading fails (missing functions)                  │
│     └─> Falls back to simple model ✅                       │
│                                                             │
│  Currently using: Gaussian fallback model in app.py        │
│  NOT your pickle file!                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Q3: Where is simulation called?                            │
│                                                             │
│  User clicks map                                            │
│     ↓                                                       │
│  FireSimulator.vue (line 392)                               │
│     ↓ axios.post()                                          │
│  backend/app.py (line 304) - endpoint receives request     │
│     ↓                                                       │
│  backend/app.py (line 333) - ⭐ SIMULATION CALL HERE ⭐    │
│     fire_model['simulate_fire_pollution_impact'](...)      │
│     ↓                                                       │
│  backend/app.py (line 26) - fallback function runs         │
│     simulate_fire_pollution_impact_simple()                 │
│     ↓                                                       │
│  Returns: {grid_data: [...], summary: {...}}               │
│     ↓                                                       │
│  Frontend displays heatmap                                  │
└─────────────────────────────────────────────────────────────┘
```

## Key Files Reference

| File | Purpose | Used For |
|------|---------|----------|
| `package.json` (root) | Orchestrate dev workflow | Running `pnpm dev` |
| `frontend/package.json` | Frontend dependencies | Vue, Vite, Leaflet, Axios |
| `backend/app.py` | Flask API server | All backend logic |
| `data/NASA-MODIS-DATA/combined-countries.csv` | Fire data | ✅ View Mode |
| `data/fire_impact_model.pkl` | Your trained model | ❌ Not used (loading fails) |
| `frontend/src/components/FireSimulator.vue` | Main UI component | Both modes |

## TL;DR

1. **pnpm from root** = Start everything with one command
2. **Your pickle** = Not used (fallback model instead)
3. **Simulation call** = `app.py` line 333 → fallback function

Everything works, just not using your notebook's trained model yet! 🚀
