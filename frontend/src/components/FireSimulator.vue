<template>
  <div class="fire-simulator">
    <div class="controls">
      <h2>🔥 Fire & Pollution System</h2>
      
      <!-- Mode Selection -->
      <div class="mode-selector">
        <button 
          :class="['mode-btn', { active: currentMode === 'view' }]"
          @click="switchMode('view')"
        >
          👁️ View Mode
        </button>
        <button 
          :class="['mode-btn', { active: currentMode === 'simulation' }]"
          @click="switchMode('simulation')"
        >
          🧪 Simulation Mode
        </button>
        <button 
          :class="['mode-btn', { active: currentMode === 'algorithmic' }]"
          @click="switchMode('algorithmic')"
        >
          🤖 Algorithmic Sim
        </button>
      </div>

      <!-- View Mode Controls -->
      <div v-if="currentMode === 'view'" class="mode-content">
        <p class="instructions">
          View historical fire data from NASA MODIS across Scandinavia (2019-2024). Select a date range to explore.
        </p>

        <div class="control-group">
          <label for="start-date">Start Date:</label>
          <input 
            type="date" 
            id="start-date"
            v-model="startDate"
            class="date-input"
          />
        </div>

        <div class="control-group">
          <label for="end-date">End Date:</label>
          <input 
            type="date" 
            id="end-date"
            v-model="endDate"
            class="date-input"
          />
        </div>

        <div class="control-group">
          <label for="min-frp">Minimum FRP (Fire Intensity):</label>
          <input 
            type="number" 
            id="min-frp"
            v-model.number="minFrpFilter"
            min="0"
            max="500"
            step="10"
            class="number-input"
          />
          <small>Filter fires with FRP >= {{ minFrpFilter }} MW</small>
        </div>

        <button 
          @click="loadHistoricalFires" 
          class="btn-primary"
          :disabled="loadingFires"
        >
          {{ loadingFires ? 'Loading...' : '🔥 Load Fires' }}
        </button>

        <div v-if="historicalFires.length > 0" class="results">
          <h3>📊 Loaded Fires</h3>
          <div class="result-item">
            <strong>Total Fires:</strong> {{ historicalFires.length }}
          </div>
          <div class="result-item">
            <strong>Date Range:</strong> {{ startDate }} to {{ endDate }}
          </div>
          <div class="result-item">
            <strong>Min FRP:</strong> {{ minFrpFilter }} MW
          </div>
        </div>

        <button 
          v-if="historicalFires.length > 0" 
          @click="clearHistoricalFires" 
          class="btn-clear"
        >
          🗑️ Clear Fires
        </button>
      </div>

      <!-- Simulation Mode Controls -->
      <div v-else-if="currentMode === 'simulation'" class="mode-content">
        <p class="instructions">
          Click anywhere on the map to place a fire and see predicted pollution spread.
        </p>

        <div class="control-group">
          <label for="sim-date">Simulation Date:</label>
          <input 
            type="date" 
            id="sim-date"
            v-model="selectedDate"
            class="date-input"
          />
        </div>
        
        <div class="control-group">
          <label for="frp-slider">Fire Intensity (FRP): {{ frp }}</label>
          <input 
            type="range" 
            id="frp-slider"
            v-model.number="frp" 
            min="10" 
            max="500" 
            step="10"
            class="slider"
          />
          <div class="slider-labels">
            <span>Small (10)</span>
            <span>Medium (250)</span>
            <span>Large (500)</span>
          </div>
        </div>

        <div class="control-group pollutant-section">
          <label>Pollutant Overlays (Select Multiple):</label>
          <p class="helper-text">Choose one or more pollutants to display on the heatmap</p>
          <div class="pollutant-grid">
            <label 
              v-for="pollutant in availablePollutants" 
              :key="pollutant" 
              class="pollutant-chip"
              :class="{ active: selectedPollutants.includes(pollutant) }"
            >
              <input 
                type="checkbox" 
                :value="pollutant" 
                v-model="selectedPollutants"
                class="checkbox-hidden"
              />
              <span class="chip-icon">{{ getPollutantIcon(pollutant) }}</span>
              <span class="chip-label">{{ pollutant }}</span>
            </label>
          </div>
          <div class="selection-summary" v-if="selectedPollutants.length > 0">
            <span class="summary-label">Selected:</span>
            <span class="summary-badges">
              <span 
                v-for="p in selectedPollutants" 
                :key="p" 
                class="badge"
                :style="{ backgroundColor: getPollutantColor(p) }"
              >
                {{ p }}
              </span>
            </span>
          </div>
        </div>

        <div class="action-buttons">
          <button 
            v-if="simulationData" 
            @click="clearSimulation" 
            class="btn-clear"
          >
            <span class="btn-icon">🗑️</span>
            Clear Simulation
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Running simulation...</p>
      </div>

      <div v-if="error" class="error">
        {{ error }}
      </div>

      <div v-if="simulationData" class="results">
        <h3>Simulation Results</h3>
        <div class="result-item">
          <strong>Location:</strong> 
          {{ simulationData.summary.fire_location.lat.toFixed(2) }}, 
          {{ simulationData.summary.fire_location.lon.toFixed(2) }}
        </div>
        <div class="result-item">
          <strong>Fire Intensity:</strong> {{ simulationData.summary.fire_intensity }} FRP
        </div>
        <div class="result-item">
          <strong>Grid Points:</strong> {{ simulationData.summary.grid_points }}
        </div>
        <div class="result-item">
          <strong>Max Distance:</strong> {{ simulationData.summary.max_distance_km.toFixed(1) }} km
        </div>
        
        <h4>Pollution Peaks:</h4>
        <div 
          v-for="(values, pollutant) in simulationData.summary.pollutant_peaks" 
          :key="pollutant"
          class="pollutant-stat"
        >
          <strong>{{ pollutant }}:</strong> 
          Max: {{ values.max.toFixed(4) }}, 
          Mean: {{ values.mean.toFixed(4) }}
        </div>
      </div>

      <!-- Algorithmic Simulation Mode -->
      <div v-if="currentMode === 'algorithmic'" class="mode-content">
        <AlgorithmicSimulation 
          ref="algorithmicSimRef"
          :map="map" 
        />
      </div>
    </div>

    <div class="map-container">
      <div id="fire-simulation-map" ref="mapContainer"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.heat'
import axios from 'axios'
import AlgorithmicSimulation from './AlgorithmicSimulation.vue'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api'

// State - Map
const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let heatLayer: any = null
let fireMarker: L.Marker | null = null
let historicalFireMarkers: L.CircleMarker[] = []

// State - Mode
const currentMode = ref<'view' | 'simulation' | 'algorithmic'>('view')
const algorithmicSimRef = ref<InstanceType<typeof AlgorithmicSimulation> | null>(null)

// State - View Mode
const startDate = ref('2024-01-01')
const endDate = ref('2024-01-31')
const minFrpFilter = ref(0)
const historicalFires = ref<any[]>([])
const loadingFires = ref(false)

// State - Simulation Mode
const selectedDate = ref('2024-01-01') // Used for simulation date picker
const frp = ref(150)
const availablePollutants = ['CO', 'NO2', 'CH4', 'HCHO', 'SO2', 'AAI']
const selectedPollutants = ref<string[]>(['CO']) // Now supports multiple selections
const loading = ref(false)
const error = ref('')
const simulationData = ref<any>(null)
const currentPollutantIndex = ref(0)

// Initialize map
onMounted(() => {
  if (mapContainer.value) {
    // Create map centered on Sweden with restricted bounds
    const swedenBounds: L.LatLngBoundsExpression = [[55.0, 10.0], [70.0, 25.0]]
    
    map = L.map(mapContainer.value, {
      maxBounds: swedenBounds,
      maxBoundsViscosity: 1.0,
      minZoom: 5
    }).setView([62.0, 15.0], 5)

    // Add tile layer (Standard OSM for clear land cover visibility)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(map)

    // Add click handler (only active in simulation mode)
    map.on('click', handleMapClick)
  }
})

// Switch between modes
function switchMode(mode: 'view' | 'simulation' | 'algorithmic') {
  currentMode.value = mode
  
  // Clear everything when switching modes
  clearHistoricalFires()
  clearSimulation()
  
  // Reset algorithmic simulation if switching away from it
  if (mode !== 'algorithmic' && algorithmicSimRef.value) {
    algorithmicSimRef.value.reset()
  }
}

// Load historical fires from CSV
async function loadHistoricalFires() {
  loadingFires.value = true
  error.value = ''
  
  try {
    // Query CSV endpoint for fire data
    const params: any = {
      start_date: startDate.value,
      end_date: endDate.value,
      min_frp: minFrpFilter.value,
      limit: 5000
    }

    const response = await axios.get(`${API_BASE_URL}/fires/csv`, { params })
    
    historicalFires.value = response.data.data || []
    
    // Display fires on map
    displayHistoricalFires()
    
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Failed to load fires from CSV'
    console.error('Load fires error:', err)
  } finally {
    loadingFires.value = false
  }
}

// Display historical fires on map
function displayHistoricalFires() {
  if (!map) return
  
  // Clear existing markers
  clearHistoricalFireMarkers()
  
  // Create markers for each fire
  historicalFires.value.forEach((fire: any) => {
    if (!fire.latitude || !fire.longitude) return
    
    const lat = parseFloat(fire.latitude)
    const lon = parseFloat(fire.longitude)
    const fireFrp = parseFloat(fire.frp || 0)
    
    if (isNaN(lat) || isNaN(lon)) return
    
    // Color based on FRP
    const color = getFireColor(fireFrp)
    
    // Create circle marker
    const marker = L.circleMarker([lat, lon], {
      radius: Math.min(Math.max(fireFrp / 50, 3), 15),
      fillColor: color,
      color: color,
      weight: 1,
      opacity: 0.8,
      fillOpacity: 0.6
    }).bindPopup(`
      <strong>Fire Event</strong><br>
      Date: ${fire.acq_date || 'Unknown'}<br>
      FRP: ${fireFrp.toFixed(2)}<br>
      Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}
    `)
    
    marker.addTo(map!)
    historicalFireMarkers.push(marker)
  })
  
  // Fit map to show all markers if any exist
  if (historicalFireMarkers.length > 0) {
    const group = L.featureGroup(historicalFireMarkers)
    map!.fitBounds(group.getBounds().pad(0.1))
  }
}

// Get color based on FRP value
function getFireColor(frp: number): string {
  if (frp < 50) return '#ffff00'      // Yellow
  if (frp < 100) return '#ffaa00'     // Orange-yellow
  if (frp < 200) return '#ff6600'     // Orange
  if (frp < 300) return '#ff3300'     // Red-orange
  return '#ff0000'                     // Red
}

// Clear historical fire markers
function clearHistoricalFireMarkers() {
  historicalFireMarkers.forEach(marker => {
    if (map) {
      map.removeLayer(marker)
    }
  })
  historicalFireMarkers = []
}

// Clear historical fires
function clearHistoricalFires() {
  clearHistoricalFireMarkers()
  historicalFires.value = []
}

// Handle map click
async function handleMapClick(e: L.LeafletMouseEvent) {
  // View Mode - no map interaction needed (just load fires via button)
  if (currentMode.value === 'view') {
    return
  }

  // Handle Algorithmic Simulation Mode
  if (currentMode.value === 'algorithmic') {
    if (algorithmicSimRef.value) {
      algorithmicSimRef.value.startSimulation(e.latlng.lat, e.latlng.lng)
    }
    return
  }

  // Only handle clicks in simulation mode
  if (currentMode.value !== 'simulation') return
  
  const { lat, lng } = e.latlng
  
  // Clear previous simulation
  clearSimulation()
  
  // Place fire marker
  placeFireMarker(lat, lng)
  
  // Run simulation
  await runSimulation(lat, lng)
}

// Place fire marker on map
function placeFireMarker(lat: number, lng: number) {
  if (fireMarker) {
    fireMarker.remove()
  }
  
  const fireIcon = L.divIcon({
    className: 'fire-icon',
    html: '🔥',
    iconSize: [30, 30]
  })
  
  fireMarker = L.marker([lat, lng], { icon: fireIcon })
    .addTo(map!)
    .bindPopup(`Fire Source<br>FRP: ${frp.value}`)
    .openPopup()
}

// Helper functions for pollutant display
function getPollutantIcon(pollutant: string): string {
  const icons: Record<string, string> = {
    'CO': '💨',
    'NO2': '🟤',
    'CH4': '🔵',
    'HCHO': '🟣',
    'SO2': '🟡',
    'AAI': '🟠'
  }
  return icons[pollutant] || '⚪'
}

function getPollutantColor(pollutant: string): string {
  const colors: Record<string, string> = {
    'CO': '#8884d8',
    'NO2': '#82ca9d',
    'CH4': '#3498db',
    'HCHO': '#9b59b6',
    'SO2': '#f1c40f',
    'AAI': '#e67e22'
  }
  return colors[pollutant] || '#95a5a6'
}

// Run simulation
async function runSimulation(lat: number, lng: number) {
  loading.value = true
  error.value = ''
  
  try {
    // Use all selected pollutants or default to CO if none selected
    const pollutantsToSimulate = selectedPollutants.value.length > 0 
      ? selectedPollutants.value 
      : ['CO']
    
    const response = await axios.post(`${API_BASE_URL}/simulate-fire`, {
      latitude: lat,
      longitude: lng,
      frp: frp.value,
      pollutants: pollutantsToSimulate
    })
    
    simulationData.value = response.data
    
    // Display combined heatmap for all selected pollutants
    displayCombinedHeatmap()
    
  } catch (err: any) {
    error.value = err.response?.data?.error || 'Simulation failed'
    console.error('Simulation error:', err)
  } finally {
    loading.value = false
  }
}

// Display heatmap for a specific pollutant
function displayHeatmap(pollutant: string) {
  if (!simulationData.value || !map) return
  
  // Remove existing heatmap
  if (heatLayer) {
    map.removeLayer(heatLayer)
  }
  
  // Prepare heat data
  const heatData = simulationData.value.grid_data
    .filter((point: any) => point[pollutant] !== undefined)
    .map((point: any) => [
      point.latitude,
      point.longitude,
      point[pollutant]
    ])
  
  // Get max value for normalization
  const maxValue = Math.max(...heatData.map((d: number[]) => d[2]))
  
  // Create heatmap layer
  heatLayer = (L as any).heatLayer(heatData, {
    radius: 25,
    blur: 35,
    maxZoom: 10,
    max: maxValue,
    gradient: {
      0.0: 'blue',
      0.3: 'lime',
      0.5: 'yellow',
      0.7: 'orange',
      1.0: 'red'
    }
  }).addTo(map)
}

// Display combined heatmap for multiple pollutants
function displayCombinedHeatmap() {
  if (!simulationData.value || !map) return
  
  // Remove existing heatmap
  if (heatLayer) {
    map.removeLayer(heatLayer)
  }
  
  const pollutantsToShow = selectedPollutants.value.length > 0 
    ? selectedPollutants.value 
    : ['CO']
  
  // Combine heat data from all selected pollutants
  const heatData: number[][] = []
  
  simulationData.value.grid_data.forEach((point: any) => {
    let combinedValue = 0
    let validPollutants = 0
    
    pollutantsToShow.forEach((pollutant: string) => {
      if (point[pollutant] !== undefined) {
        combinedValue += point[pollutant]
        validPollutants++
      }
    })
    
    if (validPollutants > 0) {
      // Average the values for combined display
      heatData.push([point.latitude, point.longitude, combinedValue / validPollutants])
    }
  })
  
  // Get max value for normalization
  const maxValue = Math.max(...heatData.map((d: number[]) => d[2]))
  
  // Create heatmap layer with gradient based on number of pollutants
  heatLayer = (L as any).heatLayer(heatData, {
    radius: 25,
    blur: 35,
    maxZoom: 10,
    max: maxValue,
    gradient: {
      0.0: 'blue',
      0.3: 'lime',
      0.5: 'yellow',
      0.7: 'orange',
      1.0: 'red'
    }
  }).addTo(map)
}

// Clear simulation
function clearSimulation() {
  if (heatLayer && map) {
    map.removeLayer(heatLayer)
    heatLayer = null
  }
  
  if (fireMarker) {
    fireMarker.remove()
    fireMarker = null
  }
  
  simulationData.value = null
  error.value = ''
}

// Watch for pollutant selection changes
watch(selectedPollutants, () => {
  if (simulationData.value && fireMarker) {
    // Re-run simulation with all selected pollutants
    const { lat, lng } = fireMarker.getLatLng()
    runSimulation(lat, lng)
  }
}, { deep: true })

// Watch for FRP changes (re-run simulation if fire is placed)
watch(frp, async () => {
  if (fireMarker && map) {
    const { lat, lng } = fireMarker.getLatLng()
    await runSimulation(lat, lng)
  }
})
</script>

<style scoped>
.fire-simulator {
  display: flex;
  height: calc(100vh - 60px);
  gap: 20px;
}

.controls {
  width: 380px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.controls h2 {
  margin: 0 0 15px 0;
  font-size: 24px;
  text-align: center;
}

/* Mode Selector */
.mode-selector {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  background: #f5f5f5;
  padding: 5px;
  border-radius: 8px;
}

.mode-btn {
  flex: 1;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  color: #666;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.mode-btn:hover {
  background: #e0e0e0;
  color: #333;
}

.mode-btn.active {
  background: #667eea;
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  width: 100%;
  padding: 10px;
  background: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  color: #333;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-secondary.active {
  background: #3388ff;
  color: white;
  border-color: #3388ff;
}

.bbox-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-icon {
  padding: 10px;
  background: #fff0f0;
  border: 1px solid #ffcccc;
  border-radius: 6px;
  cursor: pointer;
}

.btn-icon:hover {
  background: #ffe0e0;
}

.bbox-status {
  display: block;
  margin-top: 5px;
  color: #666;
  font-size: 11px;
}

.mode-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Instructions */
.instructions {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
  padding: 12px;
  background: #f0f8ff;
  border-radius: 6px;
  border-left: 4px solid #007bff;
  line-height: 1.5;
}

/* Control Groups */
.control-group {
  margin-bottom: 20px;
}

.control-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
  font-size: 14px;
}

.control-group small {
  display: block;
  color: #666;
  font-size: 12px;
  margin-top: 5px;
}

/* Date and Number Inputs */
.date-input,
.number-input {
  width: 100%;
  padding: 10px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.date-input:focus,
.number-input:focus {
  outline: none;
  border-color: #667eea;
}

/* Slider */
.slider {
  width: 100%;
  margin-bottom: 5px;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #ffeb3b, #ff9800, #f44336);
  outline: none;
  appearance: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #666;
  margin-top: 5px;
}

/* Pollutant Section Styles */
.pollutant-section {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 10px;
  border: 1px solid #e0e0e0;
}

.pollutant-section > label {
  font-size: 15px;
  color: #333;
  margin-bottom: 4px;
}

.helper-text {
  color: #888;
  font-size: 12px;
  margin: 4px 0 12px 0;
  font-style: italic;
}

.pollutant-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.pollutant-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 8px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
}

.pollutant-chip:hover {
  border-color: #667eea;
  background: #f0f4ff;
  transform: translateY(-1px);
}

.pollutant-chip.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
  box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
}

.checkbox-hidden {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.chip-icon {
  font-size: 16px;
}

.chip-label {
  font-size: 12px;
  font-weight: 600;
}

.selection-summary {
  margin-top: 12px;
  padding: 10px;
  background: white;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.summary-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: white;
}

.action-buttons {
  margin-top: 15px;
}

.action-buttons .btn-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.action-buttons .btn-icon {
  font-size: 16px;
}

/* Buttons */
.btn-primary,
.btn-clear {
  width: 100%;
  padding: 12px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
  margin-bottom: 15px;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-clear {
  background: #dc3545;
  color: white;
}

.btn-clear:hover {
  background: #c82333;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
}

.loading {
  text-align: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 4px;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  padding: 15px;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  border-left: 4px solid #dc3545;
  margin-bottom: 15px;
}

.results {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  font-size: 14px;
}

.results h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
}

.results h4 {
  margin: 15px 0 8px 0;
  font-size: 14px;
}

.result-item {
  margin-bottom: 8px;
}

.pollutant-stat {
  margin-bottom: 5px;
  padding: 5px;
  background: white;
  border-radius: 3px;
}

.map-container {
  flex: 1;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

#fire-simulation-map {
  width: 100%;
  height: 100%;
}

.fire-icon {
  font-size: 30px;
  text-align: center;
  line-height: 30px;
}
</style>
