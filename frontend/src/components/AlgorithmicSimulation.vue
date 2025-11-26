<template>
  <div class="algorithmic-simulation-panel">
    <div class="panel-header">
      <h3><span class="icon">🔥</span> Fire Spread Simulation</h3>
      <p class="description">
        Cellular Automata Model with Real Weather Data
      </p>
    </div>

    <!-- Model Info Card -->
    <div class="model-info-card">
      <div class="model-info-header">
        <span class="icon">🧪</span> Simulation Model
      </div>
      <div class="model-info-content">
        <p>This simulation uses <strong>real-time weather data</strong> to model:</p>
        <ul class="model-features">
          <li><span class="feature-icon">🔥</span> Fire spread based on wind direction & speed</li>
          <li><span class="feature-icon">🌫️</span> Pollution cloud dispersion patterns</li>
          <li><span class="feature-icon">📊</span> CO, NO₂, PM2.5 emission estimates</li>
        </ul>
      </div>
    </div>

    <div class="panel-content">
      <!-- Date Selection -->
      <div class="control-section">
        <label class="section-label">Simulation Date</label>
        <VueDatePicker 
          v-model="selectedDate" 
          :enable-time-picker="false"
          auto-apply
          :format="'yyyy-MM-dd'"
          model-type="yyyy-MM-dd"
          @update:model-value="() => fetchWeather()"
          class="custom-datepicker"
        />
      </div>

      <!-- Weather Display -->
      <div class="weather-card">
        <div class="weather-header">
          <span class="icon">🌤️</span> Weather Conditions
          <span class="live-badge" v-if="selectedLocation">LIVE</span>
        </div>
        <div class="weather-grid">
          <div class="weather-item">
            <span class="label">Wind Speed</span>
            <span class="value">{{ windSpeed.toFixed(1) }} <span class="unit">m/s</span></span>
          </div>
          <div class="weather-item">
            <span class="label">Rain</span>
            <span class="value">{{ rainLevel.toFixed(1) }} <span class="unit">mm</span></span>
          </div>
          <div class="weather-item">
            <span class="label">Fire Risk</span>
            <span class="value" :style="{ color: seasonalRiskColor }">{{ seasonalRiskLabel }}</span>
          </div>
          <div class="weather-item">
            <span class="label">Wind From</span>
            <div class="direction-value">
              <span class="value">{{ getWindDirectionLabel(windDirection) }}</span>
              <div class="wind-compass">
                <div class="compass-ring">
                  <span class="compass-n">N</span>
                  <span class="compass-e">E</span>
                  <span class="compass-s">S</span>
                  <span class="compass-w">W</span>
                </div>
                <div class="wind-arrow-container" :style="{ transform: `rotate(${windDirection + 180}deg)` }">
                  <div class="wind-arrow">➤</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="wind-explanation">
          <small>🔥 Fire & pollution spread {{ getSpreadDirectionLabel(windDirection) }} with the wind</small>
        </div>
      </div>

      <!-- View Mode Toggle -->
      <div class="control-section">
        <label class="section-label">Map View</label>
        <div class="view-toggle">
          <button 
            class="toggle-btn" 
            :class="{ active: viewMode === 'fire' }"
            @click="viewMode = 'fire'"
          >
            🔥 Fire
          </button>
          <button 
            class="toggle-btn" 
            :class="{ active: viewMode === 'pollution' }"
            @click="viewMode = 'pollution'"
          >
            🌫️ Pollution
          </button>
        </div>

        <!-- Pollutant Selector -->
        <div v-if="viewMode === 'pollution'" class="pollutant-selector">
          <div class="pill-group">
            <button 
              v-for="p in pollutants" 
              :key="p.id"
              class="pill-btn"
              :class="{ active: selectedPollutant === p.id }"
              @click="selectedPollutant = p.id"
              :title="p.name"
            >
              {{ p.label }}
            </button>
          </div>
          <small class="note">{{ getPollutantDescription(selectedPollutant) }}</small>
          
          <div class="legend-box">
            <div class="legend-title">Concentration Severity</div>
            <div class="legend-bar" :style="{ background: getLegendGradient(selectedPollutant) }"></div>
            <div class="legend-labels">
              <span v-for="(label, index) in getLegendLabels(selectedPollutant)" :key="index">{{ label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Simulation Controls -->
      <div class="control-section">
        <div class="slider-header">
          <label class="section-label">Duration</label>
          <span class="slider-value">{{ elapsedSimulatedHours.toFixed(1) }} / {{ simulationDuration }}h</span>
        </div>
        <div class="slider-container">
          <input 
            type="range" 
            v-model.number="simulationDuration" 
            min="1" 
            max="24" 
            step="1"
            class="modern-slider"
          />
          <div class="slider-track-fill" :style="{ width: `${(simulationDuration / 24) * 100}%` }"></div>
        </div>
        <small class="note">2s real-time = 1h simulated</small>
      </div>

      <!-- Actions -->
      <div class="actions-grid">
        <button @click="togglePause" class="btn-action btn-primary" :disabled="isLoading || isFinished" :class="{ 'paused': isPaused }">
          <span class="icon">{{ isPaused ? '▶' : '⏸' }}</span>
          {{ isPaused ? 'Resume' : 'Pause' }}
        </button>
        <button @click="reset" class="btn-action btn-secondary">
          <span class="icon">↺</span> Reset
        </button>
      </div>

      <!-- Status & Stats -->
      <div v-if="isLoading" class="status-badge loading">
        <span class="spinner"></span> Loading terrain...
      </div>
      
      <div v-if="isFinished" class="status-badge finished">
        ✓ Simulation Complete
      </div>

      <div v-if="stats" class="stats-grid">
        <div class="stat-card burning">
          <span class="stat-label">Active Fires</span>
          <span class="stat-value">{{ stats.burning }}</span>
        </div>
        <div class="stat-card burnt">
          <span class="stat-label">Burnt Area</span>
          <span class="stat-value">{{ stats.burnt }}</span>
        </div>
      </div>

      <!-- Chart -->
      <div class="chart-section">
        <h4>Pollution Impact (Simulated)</h4>
        <div class="chart-container">
          <div v-if="pollutionHistory.length < 2" class="chart-placeholder">
            <span>Waiting for data...</span>
          </div>
          <svg v-else :viewBox="`0 0 ${fullWidth} ${fullHeight}`" class="chart-svg">
            <defs>
              <linearGradient id="gradCo2" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#ff4500;stop-opacity:0.2" />
                <stop offset="100%" style="stop-color:#ff4500;stop-opacity:0" />
              </linearGradient>
            </defs>
            
            <g :transform="`translate(${chartPadding.left}, 0)`">
              <!-- Grid lines -->
              <line v-for="i in 5" :key="i" x1="0" :y1="chartHeight * i / 5" :x2="chartWidth" :y2="chartHeight * i / 5" stroke="#f0f0f0" stroke-width="1"/>
              
              <!-- CO Line -->
              <polyline :points="simulatedPoints.co" fill="none" stroke="#8884d8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              
              <!-- NO2 Line -->
              <polyline :points="simulatedPoints.no2" fill="none" stroke="#82ca9d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

              <!-- PM2.5 Line -->
              <polyline :points="simulatedPoints.pm2_5" fill="none" stroke="#ffc658" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </g>
          </svg>
        </div>
        <div class="chart-legend">
          <span class="legend-item"><span class="dot" style="background: #8884d8"></span> CO</span>
          <span class="legend-item"><span class="dot" style="background: #82ca9d"></span> NO2</span>
          <span class="legend-item"><span class="dot" style="background: #ffc658"></span> PM2.5</span>
        </div>
      </div>

      <!-- Real Pollution Chart -->
      <div class="chart-section" v-if="realPollutionData.length > 0">
        <h4>Historical Air Quality (24h)</h4>
        <div class="chart-container">
          <svg :viewBox="`0 0 ${fullWidth} ${fullHeight}`" class="chart-svg">
            <g :transform="`translate(${chartPadding.left}, 0)`">
              <!-- Grid lines -->
              <line v-for="i in 5" :key="i" x1="0" :y1="chartHeight * i / 5" :x2="chartWidth" :y2="chartHeight * i / 5" stroke="#f0f0f0" stroke-width="1"/>
              
              <!-- CO Line -->
              <polyline :points="realPollutionPoints.co" fill="none" stroke="#8884d8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              
              <!-- NO2 Line -->
              <polyline :points="realPollutionPoints.no2" fill="none" stroke="#82ca9d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

              <!-- PM2.5 Line -->
              <polyline :points="realPollutionPoints.pm2_5" fill="none" stroke="#ffc658" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

              <!-- X Axis Labels -->
              <text v-for="label in timeLabels" :key="label.text" :x="label.x" :y="chartHeight + 15" font-size="10" fill="#666" text-anchor="middle">{{ label.text }}</text>
            </g>
            
            <!-- Y Axis Labels (Approximate for CO as primary) -->
            <text x="0" y="10" font-size="10" fill="#666">{{ Math.round(realPollutionPoints.maxCO) }}</text>
            <text x="0" :y="chartHeight" font-size="10" fill="#666">0</text>
          </svg>
        </div>
        <div class="chart-legend">
          <span class="legend-item"><span class="dot" style="background: #8884d8"></span> CO</span>
          <span class="legend-item"><span class="dot" style="background: #82ca9d"></span> NO2</span>
          <span class="legend-item"><span class="dot" style="background: #ffc658"></span> PM2.5</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, watch, computed } from 'vue'
import L from 'leaflet'
import { apiService, type PollutionData } from '../services/api'
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'

const props = defineProps<{
  map: L.Map | null
}>()

// Simulation Constants
const GRID_SIZE = 150 // Increased from 100 to 150 for larger area (approx 4.5km x 4.5km)
const CELL_SIZE_METERS = 30 // Each cell is 30m x 30m

// State
const windDirection = ref(0)
const windSpeed = ref(0)
const rainLevel = ref(0)
const simulationDuration = ref(10) // Default 10 hours
const elapsedSimulatedHours = ref(0)
const isPaused = ref(false)
const isLoading = ref(false)
const isFinished = ref(false)
const viewMode = ref<'fire' | 'pollution'>('fire')
const selectedPollutant = ref('pm2_5')
const gridLayers = ref<L.Rectangle[]>([])

const pollutants = [
  { id: 'pm2_5', label: 'PM2.5', name: 'Particulate Matter' },
  { id: 'co', label: 'CO', name: 'Carbon Monoxide' },
  { id: 'no2', label: 'NO₂', name: 'Nitrogen Dioxide' }
]

const getPollutantDescription = (id: string) => {
  if (id === 'pm2_5') return 'Smoke & Particles (High Visibility)'
  if (id === 'co') return 'Carbon Monoxide (High Concentration)'
  if (id === 'no2') return 'Nitrogen Dioxide (Low Concentration)'
  return ''
}

const getLegendGradient = (id: string) => {
  let color = '#000000'
  if (id === 'co') color = '#4b0082'
  if (id === 'no2') color = '#8b4513'
  
  // Convert hex to rgb
  let r = 0, g = 0, b = 0
  if (color.length === 7) {
    r = parseInt(color.slice(1, 3), 16)
    g = parseInt(color.slice(3, 5), 16)
    b = parseInt(color.slice(5, 7), 16)
  }
  
  // Gradient from low opacity (0.2) to high opacity (0.9)
  return `linear-gradient(to right, rgba(${r},${g},${b},0.2), rgba(${r},${g},${b},0.9))`
}

const getLegendLabels = (id: string) => {
  if (id === 'pm2_5') return ['0', '50', '150', '250+ µg/m³']
  if (id === 'co') return ['0', '10', '25', '50+ ppm']
  if (id === 'no2') return ['0', '50', '100', '200+ ppb']
  return ['Low', 'Mod', 'High', 'Ext']
}

// Wind direction helper functions
const getWindDirectionLabel = (degrees: number): string => {
  // Meteorological: 0° = North (wind FROM North)
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
  const index = Math.round(((degrees % 360) / 22.5)) % 16
  return `${Math.round(degrees)}° (${directions[index]})`
}

const getSpreadDirectionLabel = (degrees: number): string => {
  // Fire spreads in the opposite direction from where wind comes from
  const spreadDegrees = (degrees + 180) % 360
  const directions = ['South', 'SSW', 'Southwest', 'WSW', 'West', 'WNW', 'Northwest', 'NNW',
                      'North', 'NNE', 'Northeast', 'ENE', 'East', 'ESE', 'Southeast', 'SSE']
  const index = Math.round(((spreadDegrees % 360) / 22.5)) % 16
  return directions[index]
}

const simulationInterval = ref<number | null>(null)
const pollutionHistory = ref<{time: number, co: number, no2: number, pm2_5: number}[]>([])
const realPollutionData = ref<PollutionData[]>([])
const selectedDate = ref(new Date().toISOString().split('T')[0])
const selectedLocation = ref<{lat: number, lng: number} | null>(null)

// Seasonality Logic
const seasonalRiskFactor = computed(() => {
  const date = new Date(selectedDate.value)
  const month = date.getMonth() // 0-11
  
  // Sweden Fire Seasonality (0=Jan, 11=Dec)
  // High risk: May-Aug
  // Low risk: Oct-Mar
  const seasonality = [
    0.05, // Jan - Snow/Ice
    0.05, // Feb - Snow/Ice
    0.1,  // Mar - Thaw
    0.4,  // Apr - Early season
    0.8,  // May - Season start
    1.0,  // Jun - High
    1.2,  // Jul - Peak
    1.0,  // Aug - High
    0.5,  // Sep - Season end
    0.2,  // Oct - Damp
    0.05, // Nov - Frost/Snow (User requested very low)
    0.05  // Dec - Snow
  ]
  
  return seasonality[month]
})

const seasonalRiskLabel = computed(() => {
  const factor = seasonalRiskFactor.value
  if (factor < 0.2) return 'Very Low'
  if (factor < 0.5) return 'Low'
  if (factor < 0.8) return 'Moderate'
  if (factor < 1.1) return 'High'
  return 'Extreme'
})

const seasonalRiskColor = computed(() => {
  const factor = seasonalRiskFactor.value
  if (factor < 0.2) return '#3b82f6' // Blue
  if (factor < 0.5) return '#10b981' // Green
  if (factor < 0.8) return '#f59e0b' // Yellow
  if (factor < 1.1) return '#f97316' // Orange
  return '#ef4444' // Red
})

const fetchWeather = async (lat?: number, lng?: number) => {
  // Update location if provided
  if (typeof lat === 'number' && typeof lng === 'number') {
    selectedLocation.value = { lat, lng }
  }

  // Need a location to fetch weather
  if (!selectedLocation.value) return

  const { lat: targetLat, lng: targetLng } = selectedLocation.value
  const date = new Date(selectedDate.value).getTime() // Unix timestamp in ms
  const timestamp = Math.floor(date / 1000) // Convert to seconds

  // Fetch Weather
  try {
    const response = await apiService.getWeather(targetLat, targetLng, timestamp)
    if (response.status === 'success' && response.data) {
      windSpeed.value = response.data.wind_speed || 0
      windDirection.value = response.data.wind_deg || 0
      rainLevel.value = response.data.rain || 0
    } else {
      console.error('Weather fetch failed:', response)
    }
  } catch (e) {
    console.error('Weather fetch error:', e)
  }

  // Fetch Pollution
  try {
    const response = await apiService.getPollution(targetLat, targetLng, timestamp)
    if (response.status === 'success' && response.data) {
      realPollutionData.value = response.data
    }
  } catch (e) {
    console.error('Pollution fetch error:', e)
  }
}

// Chart dimensions
const chartWidth = 300
const chartHeight = 100
const chartPadding = { left: 35, bottom: 20 }
const fullWidth = chartWidth + chartPadding.left
const fullHeight = chartHeight + chartPadding.bottom

// Helper to scale values
const scaleY = (val: number, max: number) => chartHeight - (val / (max || 1)) * chartHeight
const scaleX = (i: number, total: number) => (i / (total - 1 || 1)) * chartWidth

const simulatedPoints = computed(() => {
  if (pollutionHistory.value.length < 2) return { co: '', no2: '', pm2_5: '' }
  
  const data = pollutionHistory.value
  // Find max across all to keep relative scale or individual? 
  // Individual scales are better for visibility
  const maxCO = Math.max(...data.map(d => d.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => {
      const x = scaleX(i, data.length)
      const y = scaleY(d[key], max)
      return `${x},${y}`
    }).join(' ')
  }

  return {
    co: createPoints('co', maxCO),
    no2: createPoints('no2', maxNO2),
    pm2_5: createPoints('pm2_5', maxPM25)
  }
})

// Real Pollution Data Points
const realPollutionPoints = computed(() => {
  if (realPollutionData.value.length < 2) return { co: '', no2: '', pm2_5: '', maxCO: 0, maxNO2: 0, maxPM25: 0 }
  
  const data = realPollutionData.value
  const maxCO = Math.max(...data.map(d => d.components.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.components.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.components.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => {
      const x = scaleX(i, data.length)
      const val = d.components[key]
      const y = scaleY(val, max)
      return `${x},${y}`
    }).join(' ')
  }

  return {
    co: createPoints('co', maxCO),
    no2: createPoints('no2', maxNO2),
    pm2_5: createPoints('pm2_5', maxPM25),
    maxCO,
    maxNO2,
    maxPM25
  }
})

// Axis Labels
const timeLabels = computed(() => {
  return ['00:00', '06:00', '12:00', '18:00', '23:00'].map((label, i) => ({
    text: label,
    x: (i / 4) * chartWidth
  }))
})


// Cell States: 0 = Fuel, 1 = Burning, 2 = Burnt, 3 = Water/Non-flammable, 4 = City
enum CellState {
  Fuel = 0,
  Burning = 1,
  Burnt = 2,
  Water = 3,
  City = 4
}

type LandType = 'forest' | 'grass' | 'scrub' | 'city' | 'water' | 'other'

interface Cell {
  state: CellState
  landType: LandType
  lat: number
  lng: number
  bounds: L.LatLngBounds
  fuelDensity: number // 0-1
  heat: number // 0-100, accumulation for ignition
  pollutionLevel: number // 0-100+, for visualization
  layer?: any // Use any to avoid strict Leaflet type issues with Vue reactivity
}

const grid = ref<Cell[][]>([])
const gridLayerGroup = ref<L.LayerGroup | null>(null)
const canvasRenderer = ref<L.Canvas | null>(null)

const stats = computed(() => {
  let burning = 0
  let burnt = 0
  grid.value.forEach(row => row.forEach(cell => {
    if (cell.state === CellState.Burning) burning++
    if (cell.state === CellState.Burnt) burnt++
  }))
  return { burning, burnt }
})

// Public method called by parent
const startSimulation = async (lat: number, lng: number) => {
  // Fetch weather for the specific location before starting
  await fetchWeather(lat, lng)

  reset()
  isLoading.value = true
  await initializeGrid(lat, lng)
  
  const centerI = Math.floor(GRID_SIZE / 2)
  const centerJ = Math.floor(GRID_SIZE / 2)
  
  if (grid.value[centerI][centerJ].state === CellState.Water) {
    alert("Cannot start fire on water!")
    isLoading.value = false
    return
  }
  
  // Ignite
  grid.value[centerI][centerJ].state = CellState.Burning
  updateCellVisual(grid.value[centerI][centerJ])

  isLoading.value = false
  elapsedSimulatedHours.value = 0
  startLoop()
}

const initializeGrid = async (centerLat: number, centerLng: number) => {
  if (!props.map) return

  // Create layer group if not exists
  if (!gridLayerGroup.value) {
    gridLayerGroup.value = L.layerGroup().addTo(props.map)
  } else {
    gridLayerGroup.value.clearLayers()
  }
  
  // Use Canvas renderer for better performance with large grid
  if (!canvasRenderer.value) {
    canvasRenderer.value = L.canvas({ padding: 0.5 })
  }

  // Simple approximation: 1 degree lat ~ 111km. 
  // 100m = 0.1km = 0.1/111 degrees lat ~= 0.0009
  const latStep = (CELL_SIZE_METERS / 1000) / 111
  // Longitude step depends on latitude
  const lngStep = (CELL_SIZE_METERS / 1000) / (111 * Math.cos(centerLat * Math.PI / 180))

  const startLat = centerLat - (GRID_SIZE / 2) * latStep
  const startLng = centerLng - (GRID_SIZE / 2) * lngStep

  // Calculate grid bounds for Overpass query
  const endLat = startLat + GRID_SIZE * latStep
  const endLng = startLng + GRID_SIZE * lngStep
  const gridBounds = L.latLngBounds([startLat, startLng], [endLat, endLng])

  // Fetch land cover data
  const landFeatures = await fetchLandCover(gridBounds)

  const newGrid: Cell[][] = []

  for (let i = 0; i < GRID_SIZE; i++) {
    const row: Cell[] = []
    for (let j = 0; j < GRID_SIZE; j++) {
      const cellLat = startLat + i * latStep
      const cellLng = startLng + j * lngStep
      const nextLat = cellLat + latStep
      const nextLng = cellLng + lngStep
      
      const bounds = L.latLngBounds([cellLat, cellLng], [nextLat, nextLng])
      const center = { lat: cellLat + latStep/2, lng: cellLng + lngStep/2 }
      
      // Determine type based on Overpass data
      let state = CellState.Fuel // Default
      let landType: LandType = 'other'
      let fuelDensity = 0.5 // Default

      // Check against features
      for (const feature of landFeatures) {
        const polygons = []
        if (feature.type === 'way' && feature.geometry) {
          polygons.push(feature.geometry)
        } else if (feature.type === 'relation' && feature.members) {
           // Extract outer rings from relation members
           feature.members.forEach((m: any) => {
             if (m.role === 'outer' && m.geometry) {
               polygons.push(m.geometry)
             }
           })
        }

        let match = false
        for (const poly of polygons) {
            if (isPointInPolygon(center, poly)) {
                match = true
                break
            }
        }

        if (match) {
          const tags = feature.tags || {}
          if (
            tags.natural === 'water' || 
            tags.natural === 'coastline' ||
            tags.natural === 'bay' ||
            tags.waterway === 'riverbank' || 
            tags.waterway === 'dock' ||
            tags.landuse === 'reservoir' ||
            tags.landuse === 'basin'
          ) {
            state = CellState.Water
            landType = 'water'
            fuelDensity = 0
            break // Water overrides everything
          } else if (tags.landuse === 'forest' || tags.natural === 'wood') {
            state = CellState.Fuel
            landType = 'forest'
            fuelDensity = 0.9 // High fuel
          } else if (
            tags.natural === 'scrub' || 
            tags.natural === 'heath' || 
            tags.natural === 'moor'
          ) {
            state = CellState.Fuel
            landType = 'scrub'
            fuelDensity = 0.8
          } else if (
            tags.natural === 'grassland' || 
            tags.landuse === 'meadow' || 
            tags.landuse === 'farmland' ||
            tags.landuse === 'orchard' ||
            tags.landuse === 'vineyard'
          ) {
            state = CellState.Fuel
            landType = 'grass'
            fuelDensity = 0.6
          } else if (['residential', 'commercial', 'industrial', 'retail'].includes(tags.landuse)) {
            state = CellState.City
            landType = 'city'
            fuelDensity = 0.3 // Low fuel density for city
          }
        }
      }
      
      // Create layer immediately
      let color = 'transparent'
      let opacity = 0.0
      
      if (state === CellState.Water) {
        color = '#1e90ff'
        opacity = 0.6
      } else if (state === CellState.Fuel) {
        if (landType === 'forest') {
          color = '#228b22'
          opacity = 0.4
        } else if (landType === 'scrub') {
          color = '#556b2f'
          opacity = 0.4
        } else if (landType === 'grass') {
          color = '#9acd32'
          opacity = 0.3
        } else {
          // Default fuel/other
          color = '#228b22'
          opacity = 0.2
        }
      } else if (state === CellState.City) {
        color = '#808080' // Gray for city
        opacity = 0.4
      }

      const rect = L.rectangle(bounds, {
        color: color,
        weight: 0,
        fillOpacity: opacity,
        renderer: canvasRenderer.value as any // Use canvas renderer
      })
      
      if (color !== 'transparent') {
        rect.addTo(gridLayerGroup.value as any)
      }

      row.push({
        state: state,
        landType: landType,
        lat: cellLat,
        lng: cellLng,
        bounds: bounds,
        fuelDensity: fuelDensity,
        heat: 0,
        pollutionLevel: 0,
        layer: rect
      })
    }
    newGrid.push(row)
  }

  grid.value = newGrid
}

async function fetchLandCover(bounds: L.LatLngBounds) {
  const south = bounds.getSouth()
  const west = bounds.getWest()
  const north = bounds.getNorth()
  const east = bounds.getEast()

  const query = `
    [out:json][timeout:25];
    (
      way["natural"="water"](${south},${west},${north},${east});
      relation["natural"="water"](${south},${west},${north},${east});
      way["waterway"="riverbank"](${south},${west},${north},${east});
      relation["waterway"="riverbank"](${south},${west},${north},${east});
      way["waterway"="dock"](${south},${west},${north},${east});
      relation["waterway"="dock"](${south},${west},${north},${east});
      way["landuse"="reservoir"](${south},${west},${north},${east});
      relation["landuse"="reservoir"](${south},${west},${north},${east});
      way["landuse"="basin"](${south},${west},${north},${east});
      relation["landuse"="basin"](${south},${west},${north},${east});
      way["natural"="coastline"](${south},${west},${north},${east});
      relation["natural"="coastline"](${south},${west},${north},${east});
      way["natural"="bay"](${south},${west},${north},${east});
      relation["natural"="bay"](${south},${west},${north},${east});
      way["landuse"="forest"](${south},${west},${north},${east});
      relation["landuse"="forest"](${south},${west},${north},${east});
      way["natural"="wood"](${south},${west},${north},${east});
      relation["natural"="wood"](${south},${west},${north},${east});
      way["natural"="scrub"](${south},${west},${north},${east});
      relation["natural"="scrub"](${south},${west},${north},${east});
      way["natural"="heath"](${south},${west},${north},${east});
      relation["natural"="heath"](${south},${west},${north},${east});
      way["natural"="moor"](${south},${west},${north},${east});
      relation["natural"="moor"](${south},${west},${north},${east});
      way["natural"="grassland"](${south},${west},${north},${east});
      relation["natural"="grassland"](${south},${west},${north},${east});
      way["landuse"="meadow"](${south},${west},${north},${east});
      relation["landuse"="meadow"](${south},${west},${north},${east});
      way["landuse"="farmland"](${south},${west},${north},${east});
      relation["landuse"="farmland"](${south},${west},${north},${east});
      way["landuse"="orchard"](${south},${west},${north},${east});
      relation["landuse"="orchard"](${south},${west},${north},${east});
      way["landuse"="vineyard"](${south},${west},${north},${east});
      relation["landuse"="vineyard"](${south},${west},${north},${east});
      way["landuse"="residential"](${south},${west},${north},${east});
      relation["landuse"="residential"](${south},${west},${north},${east});
      way["landuse"="commercial"](${south},${west},${north},${east});
      relation["landuse"="commercial"](${south},${west},${north},${east});
      way["landuse"="industrial"](${south},${west},${north},${east});
      relation["landuse"="industrial"](${south},${west},${north},${east});
    );
    out geom;
  `
  
  try {
    const response = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body: query
    })
    const data = await response.json()
    return data.elements || []
  } catch (e) {
    console.error("Failed to fetch land cover", e)
    return []
  }
}

function isPointInPolygon(point: {lat: number, lng: number}, vs: {lat: number, lon: number}[]) {
    // ray-casting algorithm based on
    // https://github.com/substack/point-in-polygon/blob/master/index.js
    
    var x = point.lat, y = point.lng;
    
    var inside = false;
    for (var i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        var xi = vs[i].lat, yi = vs[i].lon;
        var xj = vs[j].lat, yj = vs[j].lon;
        
        var intersect = ((yi > y) != (yj > y))
            && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    
    return inside;
};

const updateCellVisual = (cell: Cell) => {
  if (!cell.layer || !gridLayerGroup.value) return

  let color = 'transparent'
  let opacity = 0.0
  
  if (viewMode.value === 'pollution') {
    // Pollution View
    // Scale factor based on pollutant type relative to generic "smoke"
    let factor = 1.0
    let baseColor = '#000000'
    
    if (selectedPollutant.value === 'co') {
      factor = 1.5 // CO is more abundant than PM2.5
      baseColor = '#4b0082' // Indigo/Dark Purple for CO
    } else if (selectedPollutant.value === 'no2') {
      factor = 0.1 // NO2 is much less abundant
      baseColor = '#8b4513' // SaddleBrown for NO2
    } else {
      // PM2.5
      factor = 1.0
      baseColor = '#000000' // Black/Grey for Smoke
    }

    if (cell.pollutionLevel > 1) {
      const effectiveLevel = cell.pollutionLevel * factor
      const intensity = Math.min(1, effectiveLevel / 200) // Cap at 200 for visual max
      
      if (intensity < 0.1) {
        color = 'transparent'
      } else {
        color = baseColor
        // Opacity based on intensity
        opacity = 0.2 + (intensity * 0.6) // 0.2 to 0.8
      }
    }
  } else {
    // Fire View
    if (cell.state === CellState.Burning) {
      color = '#ff4500' // OrangeRed
      opacity = 0.8
    } else if (cell.state === CellState.Burnt) {
      color = '#000000' // Black
      opacity = 0.6
    } else if (cell.state === CellState.Water) {
      color = '#1e90ff' // DodgerBlue
      opacity = 0.6
    } else if (cell.state === CellState.Fuel) {
      if (cell.landType === 'forest') {
        color = '#228b22'
        opacity = 0.4
      } else if (cell.landType === 'scrub') {
        color = '#556b2f'
        opacity = 0.4
      } else if (cell.landType === 'grass') {
        color = '#9acd32'
        opacity = 0.3
      } else {
        color = '#228b22'
        opacity = 0.2
      }
    } else if (cell.state === CellState.City) {
      color = '#808080' // Gray for city
      opacity = 0.4
    }
  }

  if (color !== 'transparent') {
    cell.layer.setStyle({
      color: color,
      fillOpacity: opacity
    })
    // Ensure it's on the map
    if (!gridLayerGroup.value.hasLayer(cell.layer)) {
      gridLayerGroup.value.addLayer(cell.layer)
    }
  } else {
    // Remove if transparent to save performance
    if (gridLayerGroup.value.hasLayer(cell.layer)) {
      gridLayerGroup.value.removeLayer(cell.layer)
    }
  }
}

// Watch view mode or pollutant to redraw grid
watch([viewMode, selectedPollutant], () => {
  if (grid.value.length > 0) {
    grid.value.forEach(row => row.forEach(cell => updateCellVisual(cell)))
  }
})

const updateSimulation = () => {
  if (isPaused.value || isFinished.value) return
  
  // Increment simulated time (1 step = 0.1h)
  elapsedSimulatedHours.value += 0.1

  // Check time limit
  if (elapsedSimulatedHours.value >= simulationDuration.value) {
    isFinished.value = true
    if (simulationInterval.value) {
      clearInterval(simulationInterval.value)
      simulationInterval.value = null
    }
    return
  }

  let changed = false
  let burningCount = 0

  // Parameters
  const ignitionThresholds: Record<string, number> = {
    'grass': 30,
    'scrub': 60,
    'forest': 90,
    'city': 120,
    'other': 75,
    'water': 9999
  }

  const heatOutput: Record<string, number> = {
    'grass': 10,
    'scrub': 15,
    'forest': 20,
    'city': 10,
    'other': 10,
    'water': 0
  }

  // Apply Seasonality to Parameters
  // If risk is low (e.g. 0.05), thresholds increase significantly and heat output drops
  const seasonFactor = seasonalRiskFactor.value
  
  // Inverse relationship for threshold: Lower factor -> Higher threshold
  // We clamp the multiplier to avoid infinity, but make it very hard to burn in winter
  const thresholdMultiplier = Math.max(1, 1 / (seasonFactor + 0.01)) 
  
  // Direct relationship for heat: Lower factor -> Lower heat
  const heatMultiplier = seasonFactor

  // First pass: Burning cells emit heat
  for (let i = 0; i < GRID_SIZE; i++) {
    for (let j = 0; j < GRID_SIZE; j++) {
      const cell = grid.value[i][j]
      
      if (cell.state === CellState.Burning) {
        burningCount++
        
        // Burnout logic
        let burnoutProb = 0.05 + (1 - cell.fuelDensity) * 0.2
        if (rainLevel.value > 0) {
           burnoutProb += rainLevel.value * 0.05 // Rain increases burnout rate
        }
        
        // Seasonality affects burnout: Winter -> faster burnout
        if (seasonFactor < 0.5) {
           burnoutProb += (0.5 - seasonFactor) * 0.5
        }
        
        if (Math.random() < burnoutProb) { 
           cell.state = CellState.Burnt
           updateCellVisual(cell)
           changed = true
        }

        // Emit heat to neighbors
        const neighbors = [
          [i-1, j], [i+1, j], [i, j-1], [i, j+1],
          [i-1, j-1], [i-1, j+1], [i+1, j-1], [i+1, j+1]
        ]

        neighbors.forEach(([ni, nj]) => {
          if (ni >= 0 && ni < GRID_SIZE && nj >= 0 && nj < GRID_SIZE) {
            const targetCell = grid.value[ni][nj]
            if (targetCell.state === CellState.Fuel || targetCell.state === CellState.City) {
              
              // Calculate wind effect on fire spread
              // Grid coordinates: i increases going South, j increases going East
              const dy = ni - i  // positive = neighbor is South of current
              const dx = nj - j  // positive = neighbor is East of current
              
              // Convert grid direction to compass bearing (0=N, 90=E, 180=S, 270=W)
              // atan2(dx, -dy) gives compass bearing: East(+dx)=90°, South(+dy)=180°
              let directionToNeighbor = Math.atan2(dx, -dy) * 180 / Math.PI
              directionToNeighbor = (directionToNeighbor + 360) % 360
              
              // Wind spreads fire in the direction it's blowing TO (opposite of FROM)
              // windDirection 0 (N) means wind blows FROM North, so fire spreads TO South (180°)
              const spreadDirection = (windDirection.value + 180) % 360
              
              // Calculate how aligned the neighbor is with the spread direction
              let angleDiff = Math.abs(spreadDirection - directionToNeighbor)
              if (angleDiff > 180) angleDiff = 360 - angleDiff
              
              // windFactor: 1.0 when perfectly aligned, -1.0 when opposite
              const windFactor = Math.cos(angleDiff * Math.PI / 180)
              const windEffect = (windSpeed.value / 2) * windFactor 
              
              // Base heat
              let heat = heatOutput[cell.landType] || 15
              
              // Apply Seasonality to Heat Output
              heat *= heatMultiplier

              // Apply rain dampening
              if (rainLevel.value > 0) {
                 heat *= Math.max(0, 1 - (rainLevel.value * 0.15))
              }

              // Apply wind
              let multiplier = 1.0
              if (windEffect > 0) {
                 multiplier = 1 + windEffect
              } else {
                 multiplier = Math.max(0.1, 1 + windEffect)
              }
              
              // Distance factor (diagonals are further)
              const dist = Math.sqrt(dy*dy + dx*dx)
              heat /= dist

              // Add randomness
              heat *= (0.8 + Math.random() * 0.4)

              targetCell.heat += heat * multiplier
            }
          }
        })

        // Spotting (Embers)
        // Reduced spotting in low season
        if (seasonFactor > 0.3 && windSpeed.value > 3 && (cell.landType === 'forest' || cell.landType === 'scrub')) {
           if (Math.random() < 0.05 * seasonFactor) { // Scaled by season
              const dist = 2 + Math.floor(Math.random() * 3) // 2-4 cells away
              
              // Embers land in the direction the wind is blowing TO
              // Wind FROM North (0°) means embers land to the South (+i)
              const spreadDirection = (windDirection.value + 180) % 360
              const rad = spreadDirection * Math.PI / 180
              
              // Convert compass bearing to grid offsets
              // North (0°) = -i, East (90°) = +j, South (180°) = +i, West (270°) = -j
              const targetI = Math.round(i + Math.cos((spreadDirection - 180) * Math.PI / 180) * dist)
              const targetJ = Math.round(j + Math.sin(spreadDirection * Math.PI / 180) * dist)
              
              if (targetI >= 0 && targetI < GRID_SIZE && targetJ >= 0 && targetJ < GRID_SIZE) {
                 const spotCell = grid.value[targetI][targetJ]
                 if (spotCell.state === CellState.Fuel) {
                    spotCell.heat += 50 * seasonFactor // Reduced heat from embers in winter
                 }
              }
           }
        }
      }
    }
  }

  // Second pass: Check ignition and cool down
  for (let i = 0; i < GRID_SIZE; i++) {
    for (let j = 0; j < GRID_SIZE; j++) {
      const cell = grid.value[i][j]
      if (cell.state === CellState.Fuel || cell.state === CellState.City) {
        let threshold = ignitionThresholds[cell.landType] || 50
        
        // Apply Seasonality to Threshold
        // In winter (factor 0.05), threshold becomes ~20x higher. 
        // e.g. Forest 60 -> 1200. Heat accumulation is also 0.05x. 
        // So it's effectively impossible to ignite.
        threshold *= thresholdMultiplier

        if (cell.heat > threshold) {
          cell.state = CellState.Burning
          updateCellVisual(cell)
          changed = true
        } else {
          // Cooling
          let cooling = 5
          if (rainLevel.value > 0) {
             cooling += rainLevel.value * 2
          }
          // Faster cooling in winter
          if (seasonFactor < 0.5) {
             cooling += (0.5 - seasonFactor) * 10
          }
          cell.heat = Math.max(0, cell.heat - cooling)
        }
      }
    }
  }

  // Third pass: Pollution Dynamics
  const pollutionDeltas = new Float32Array(GRID_SIZE * GRID_SIZE).fill(0)
  
  for (let i = 0; i < GRID_SIZE; i++) {
    for (let j = 0; j < GRID_SIZE; j++) {
      const cell = grid.value[i][j]
      const idx = i * GRID_SIZE + j
      
      // 1. Emission from Fire
      if (cell.state === CellState.Burning) {
        pollutionDeltas[idx] += 50
      }
      
      // 2. Diffusion & Wind
      if (cell.pollutionLevel > 1) {
        const neighbors = [
          [i-1, j], [i+1, j], [i, j-1], [i, j+1]
        ]
        
        neighbors.forEach(([ni, nj]) => {
          if (ni >= 0 && ni < GRID_SIZE && nj >= 0 && nj < GRID_SIZE) {
            const nIdx = ni * GRID_SIZE + nj
            
            // Calculate wind factor for pollution spread
            // Grid: i increases South, j increases East
            const dy = ni - i
            const dx = nj - j
            
            // Direction to neighbor in compass terms
            let directionToNeighbor = Math.atan2(dx, -dy) * 180 / Math.PI
            directionToNeighbor = (directionToNeighbor + 360) % 360
            
            // Pollution spreads in direction wind is blowing TO
            const spreadDirection = (windDirection.value + 180) % 360
            
            let angleDiff = Math.abs(spreadDirection - directionToNeighbor)
            if (angleDiff > 180) angleDiff = 360 - angleDiff
            
            const windFactor = Math.cos(angleDiff * Math.PI / 180)
            
            // Base diffusion
            let transfer = cell.pollutionLevel * 0.05
            
            // Wind bias - more transfer in wind direction
            if (windFactor > 0) {
               transfer *= (1 + windSpeed.value * 0.2)
            } else {
               transfer *= 0.2
            }
            
            pollutionDeltas[nIdx] += transfer
            pollutionDeltas[idx] -= transfer
          }
        })
      }
    }
  }
  
  // Apply Pollution Updates
  for (let i = 0; i < GRID_SIZE; i++) {
    for (let j = 0; j < GRID_SIZE; j++) {
      const cell = grid.value[i][j]
      const idx = i * GRID_SIZE + j
      
      cell.pollutionLevel = Math.max(0, cell.pollutionLevel + pollutionDeltas[idx])
      
      // Decay
      cell.pollutionLevel *= 0.98
      
      // Update visual if in pollution mode
      if (viewMode.value === 'pollution') {
         updateCellVisual(cell)
      }
    }
  }

  // Update pollution history
  // Calculate Fire Emissions
  const fireEmissions = {
    co: burningCount * 150,   // High CO from fire
    no2: burningCount * 5,    // Some NO2
    pm2_5: burningCount * 80  // High PM2.5 (Smoke)
  }

  // Get Baseline (Normal Day)
  let baseline = { co: 200, no2: 1, pm2_5: 5 } // Default
  if (realPollutionData.value.length > 0) {
     // Map elapsed hours to index (0-23)
     // Assuming simulation starts at index 0 of the fetched data
     const index = Math.min(Math.floor(elapsedSimulatedHours.value), realPollutionData.value.length - 1)
     const dataPoint = realPollutionData.value[index]
     if (dataPoint && dataPoint.components) {
        baseline = {
            co: dataPoint.components.co,
            no2: dataPoint.components.no2,
            pm2_5: dataPoint.components.pm2_5
        }
     }
  }

  pollutionHistory.value.push({
    time: elapsedSimulatedHours.value,
    co: baseline.co + fireEmissions.co,
    no2: baseline.no2 + fireEmissions.no2,
    pm2_5: baseline.pm2_5 + fireEmissions.pm2_5
  })
  
  if (pollutionHistory.value.length > 100) {
    pollutionHistory.value.shift()
  }
}

const startLoop = () => {
  if (simulationInterval.value) clearInterval(simulationInterval.value)
  // 200ms tick. If 2s = 1h (7200s), then 200ms = 0.1h.
  // Max spread speed = 30m / 12min = 150m/h = 0.15 km/h
  simulationInterval.value = window.setInterval(updateSimulation, 200) 
}

const reset = () => {
  if (simulationInterval.value) {
    clearInterval(simulationInterval.value)
    simulationInterval.value = null
  }
  if (gridLayerGroup.value) {
    gridLayerGroup.value.clearLayers()
  }
  grid.value = []
  isFinished.value = false
  elapsedSimulatedHours.value = 0
  pollutionHistory.value = []
}

const togglePause = () => {
  isPaused.value = !isPaused.value
}

onUnmounted(() => {
  reset()
})

defineExpose({
  startSimulation,
  reset
})
</script>

<style scoped>
.algorithmic-simulation-panel {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  color: #333;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 100%;
}

.panel-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #ff4500 0%, #ff8c00 100%);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.description {
  margin: 4px 0 0 0;
  font-size: 0.8rem;
  opacity: 0.9;
}

.panel-content {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.control-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Custom Datepicker Override */
:deep(.dp__input) {
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  padding: 10px 12px 10px 35px; /* Increased left padding for icon */
  font-size: 0.9rem;
  background: #f9f9f9;
  transition: all 0.2s;
}

:deep(.dp__input:hover) {
  border-color: #ff8c00;
  background: #fff;
}

:deep(.dp__input:focus) {
  border-color: #ff4500;
  box-shadow: 0 0 0 3px rgba(255, 69, 0, 0.1);
}

/* Weather Card */
.weather-card {
  background: #f0f7ff;
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid #e1effe;
}

.weather-header {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1e429f;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-badge {
  margin-left: auto;
  background: #10b981;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.weather-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.weather-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.weather-item .label {
  font-size: 0.75rem;
  color: #6b7280;
}

.weather-item .value {
  font-size: 1.1rem;
  font-weight: 700;
  color: #111827;
}

.weather-item .unit {
  font-size: 0.8rem;
  font-weight: 400;
  color: #6b7280;
}

.direction-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wind-arrow {
  font-size: 1rem;
  color: #ff4500;
}

/* Wind Compass */
.wind-compass {
  position: relative;
  width: 50px;
  height: 50px;
}

.compass-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid #e0e0e0;
  border-radius: 50%;
  background: #fff;
}

.compass-ring span {
  position: absolute;
  font-size: 0.55rem;
  font-weight: 700;
  color: #666;
}

.compass-n { top: 2px; left: 50%; transform: translateX(-50%); color: #ef4444 !important; }
.compass-e { right: 3px; top: 50%; transform: translateY(-50%); }
.compass-s { bottom: 2px; left: 50%; transform: translateX(-50%); }
.compass-w { left: 3px; top: 50%; transform: translateY(-50%); }

.wind-arrow-container {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  transform-origin: center center;
  margin-left: -50%;
  margin-top: -50%;
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 5px;
}

.wind-arrow-container .wind-arrow {
  font-size: 0.9rem;
  color: #1e90ff;
}

.wind-explanation {
  margin-top: 10px;
  padding: 8px;
  background: rgba(255, 140, 0, 0.1);
  border-radius: 6px;
  border-left: 3px solid #ff8c00;
}

.wind-explanation small {
  font-size: 0.75rem;
  color: #92400e;
}

/* Model Info Card */
.model-info-card {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid #bbf7d0;
  margin-bottom: 10px;
}

.model-info-header {
  font-size: 0.85rem;
  font-weight: 600;
  color: #166534;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-info-content {
  font-size: 0.8rem;
  color: #374151;
}

.model-info-content p {
  margin: 0 0 8px 0;
}

.model-features {
  margin: 0;
  padding: 0;
  list-style: none;
}

.model-features li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 0.75rem;
}

.feature-icon {
  font-size: 0.9rem;
}

/* Modern Slider */
.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: #ff4500;
  background: rgba(255, 69, 0, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
}

.slider-container {
  position: relative;
  height: 24px;
  display: flex;
  align-items: center;
}

.modern-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  outline: none;
  z-index: 2;
  position: relative;
  background: transparent;
}

.slider-track-fill {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 6px;
  background: linear-gradient(90deg, #ff8c00, #ff4500);
  border-radius: 3px;
  z-index: 1;
  pointer-events: none;
}

.modern-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #ff4500;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.1s;
  margin-top: -6px; /* Adjust for track height */
}

.modern-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.modern-slider::-webkit-slider-runnable-track {
  width: 100%;
  height: 6px;
  cursor: pointer;
  background: #e5e7eb;
  border-radius: 3px;
}

.note {
  font-size: 0.75rem;
  color: #9ca3af;
  font-style: italic;
}

/* Actions */
.actions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.btn-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #10b981;
  color: white;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
}

.btn-primary:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.btn-primary.paused {
  background: #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

/* Status Badges */
.status-badge {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.status-badge.loading {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #ffedd5;
}

.status-badge.finished {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #d1fae5;
}

/* View Toggle */
.view-toggle {
  display: flex;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
  gap: 4px;
}

.toggle-btn {
  flex: 1;
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: white;
  color: #1f2937;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-weight: 600;
}

.toggle-btn:hover:not(.active) {
  color: #374151;
  background: rgba(255,255,255,0.5);
}

/* Pollutant Selector */
.pollutant-selector {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.pill-group {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.pill-btn {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 12px;
  font-size: 0.75rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.pill-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.pill-btn:hover:not(.active) {
  border-color: #d1d5db;
  background: #f9fafb;
}

.legend-box {
  margin-top: 12px;
  background: #f9fafb;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #f3f4f6;
}

.legend-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: #4b5563;
  margin-bottom: 4px;
}

.legend-bar {
  height: 10px;
  border-radius: 5px;
  width: 100%;
  margin-bottom: 4px;
  border: 1px solid rgba(0,0,0,0.05);
}

.legend-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #6b7280;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  padding: 12px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-card.burning {
  background: #fff1f2;
  border: 1px solid #ffe4e6;
}

.stat-card.burning .stat-value {
  color: #e11d48;
}

.stat-card.burnt {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}

.stat-card.burnt .stat-value {
  color: #374151;
}

.stat-label {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
}

/* Chart */
.chart-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
}

.chart-section h4 {
  margin: 0 0 12px 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.chart-container {
  position: relative;
  height: 100px;
  margin-bottom: 8px;
}

.chart-placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 0.85rem;
}

.chart-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  font-size: 0.8rem;
  color: #4b5563;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.co2 { background: #ff4500; }
.dot.ch4 { background: #1e90ff; }
</style>
