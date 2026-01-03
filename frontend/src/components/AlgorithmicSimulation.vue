<template>
  <div class="algorithmic-simulation-panel">
    <!-- Main Content - Fills Available Space -->
    <div class="panel-content">
      
      <!-- Section 1: Weather Configuration -->
      <div class="section-block">
        <div class="section-header">
          <span class="section-icon">🌤️</span>
          <span class="section-title">Weather Configuration</span>
          <div class="info-tooltip" @mouseenter="showTooltip($event, 'weather')" @mouseleave="hideTooltip">
            <span class="info-icon">ⓘ</span>
          </div>
          <span class="live-badge" v-if="selectedLocation && !isMockData">LIVE DATA</span>
          <span class="mock-badge" v-if="isMockData && selectedLocation">SIMULATED</span>
        </div>
        
        <div class="weather-controls">
          <!-- Weather Source Toggle -->
          <div class="control-group">
            <label class="control-label">Data Source</label>
            <div class="weather-source-row">
              <div class="toggle-group">
                <button 
                  class="toggle-btn large" 
                  :class="{ active: weatherMode === 'real' }"
                  @click="switchWeatherMode('real')"
                >
                  📅 Real Weather
                </button>
                <button 
                  class="toggle-btn large" 
                  :class="{ active: weatherMode === 'custom' }"
                  @click="switchWeatherMode('custom')"
                >
                  ⚙️ Custom Weather
                </button>
              </div>
              <!-- Date Picker (Real Mode) - inline -->
              <div v-if="weatherMode === 'real'" class="date-picker-inline">
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
            </div>
          </div>
        </div>

        <!-- Weather Display Grid -->
        <div class="weather-display-grid">
          <div class="weather-stat">
            <span class="weather-icon">🌡️</span>
            <div class="weather-info">
              <span class="weather-value">{{ temperature.toFixed(0) }}°C</span>
              <span class="weather-label">Temperature</span>
            </div>
          </div>
          <div class="weather-stat">
            <span class="weather-icon">💨</span>
            <div class="weather-info">
              <span class="weather-value">{{ windSpeed.toFixed(1) }} m/s</span>
              <span class="weather-label">Wind Speed</span>
            </div>
          </div>
          <div class="weather-stat">
            <span class="weather-icon">🌧️</span>
            <div class="weather-info">
              <span class="weather-value">{{ rainLevel.toFixed(0) }} mm</span>
              <span class="weather-label">Precipitation</span>
            </div>
          </div>
          <div class="weather-stat">
            <span class="weather-icon">⚠️</span>
            <div class="weather-info">
              <span class="weather-value" :style="{ color: seasonalRiskColor }">{{ seasonalRiskLabel }}</span>
              <span class="weather-label">Fire Risk</span>
            </div>
          </div>
        </div>

        <!-- Custom Weather Sliders (Custom Mode) -->
        <div class="custom-weather-panel" v-if="weatherMode === 'custom'">
          <div class="custom-sliders-grid">
            <div class="slider-group">
              <label class="slider-label">🌡️ Temperature</label>
              <div class="slider-row">
                <input type="range" v-model.number="customWeather.temperature" min="-20" max="40" step="1" class="custom-slider" />
                <span class="slider-value">{{ customWeather.temperature }}°C</span>
              </div>
            </div>
            <div class="slider-group">
              <label class="slider-label">💨 Wind Speed</label>
              <div class="slider-row">
                <input type="range" v-model.number="customWeather.windSpeed" min="0" max="25" step="1" class="custom-slider" />
                <span class="slider-value">{{ customWeather.windSpeed }} m/s</span>
              </div>
            </div>
            <div class="slider-group">
              <label class="slider-label">🧭 Wind Direction</label>
              <div class="slider-row">
                <input type="range" v-model.number="customWeather.windDirection" min="0" max="359" step="15" class="custom-slider" />
                <span class="slider-value">{{ customWeather.windDirection }}°</span>
              </div>
            </div>
            <div class="slider-group">
              <label class="slider-label">🌧️ Rainfall</label>
              <div class="slider-row">
                <input type="range" v-model.number="customWeather.rain" min="0" max="50" step="1" class="custom-slider" />
                <span class="slider-value">{{ customWeather.rain }} mm</span>
              </div>
            </div>
          </div>
          <div class="custom-actions">
            <select v-model.number="customWeather.month" class="month-select">
              <option :value="0">January</option>
              <option :value="1">February</option>
              <option :value="2">March</option>
              <option :value="3">April</option>
              <option :value="4">May</option>
              <option :value="5">June</option>
              <option :value="6">July</option>
              <option :value="7">August</option>
              <option :value="8">September</option>
              <option :value="9">October</option>
              <option :value="10">November</option>
              <option :value="11">December</option>
            </select>
            <button @click="applyCustomWeather" class="btn-apply">
              ✓ Apply Weather Settings
            </button>
          </div>
        </div>
      </div>

      <!-- Section 2: Simulation Controls -->
      <div class="section-block">
        <div class="section-header">
          <span class="section-icon">🎮</span>
          <span class="section-title">Simulation Controls</span>
          <div class="info-tooltip" @mouseenter="showTooltip($event, 'controls')" @mouseleave="hideTooltip">
            <span class="info-icon">ⓘ</span>
          </div>
        </div>

        <div class="sim-controls-grid">
          <!-- Map View Toggle -->
          <div class="control-group">
            <label class="control-label">Map Display</label>
            <div class="toggle-group">
              <button class="toggle-btn large" :class="{ active: viewMode === 'fire' }" @click="viewMode = 'fire'">
                🔥 Fire Spread
              </button>
              <button class="toggle-btn large" :class="{ active: viewMode === 'pollution' }" @click="viewMode = 'pollution'">
                🌫️ Pollution
              </button>
            </div>
          </div>

          <!-- Pollutant Selector -->
          <div v-if="viewMode === 'pollution'" class="control-group">
            <label class="control-label">Pollutant Type</label>
            <div class="pollutant-buttons">
              <button 
                v-for="p in pollutants" 
                :key="p.id" 
                class="pollutant-btn" 
                :class="{ active: selectedPollutant === p.id }" 
                @click="selectedPollutant = p.id"
              >
                {{ p.label }}
              </button>
            </div>
          </div>

          <!-- Duration Slider -->
          <div class="control-group">
            <label class="control-label">Simulation Duration</label>
            <div class="duration-control">
              <input type="range" v-model.number="simulationDuration" min="1" max="24" step="1" class="duration-slider" />
              <span class="duration-value">{{ simulationDuration }} hours</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 3: Live Status -->
      <div class="section-block status-section">
        <div class="section-header">
          <span class="section-icon">📊</span>
          <span class="section-title">Simulation Status</span>
          <div class="info-tooltip" @mouseenter="showTooltip($event, 'status')" @mouseleave="hideTooltip">
            <span class="info-icon">ⓘ</span>
          </div>
        </div>

        <div class="status-grid">
          <!-- Status Badge -->
          <div class="status-item">
            <div v-if="isLoading" class="status-badge loading">
              <span class="spinner"></span> Simulating...
            </div>
            <div v-else-if="isFinished" class="status-badge finished">
              ✓ Simulation Complete
            </div>
            <div v-else-if="!stats" class="status-badge waiting">
              ⏳ Waiting for fire placement
            </div>
            <div v-else class="status-badge running">
              🔥 Fire spreading...
            </div>
          </div>

          <!-- Fire Stats + Action Buttons -->
          <div class="stats-cards" v-if="stats">
            <div class="stat-card burning">
              <span class="stat-icon">🔥</span>
              <div class="stat-info">
                <span class="stat-value">{{ stats.burning }}</span>
                <span class="stat-label">Burning</span>
              </div>
            </div>
            <div class="stat-card burnt">
              <span class="stat-icon">⬛</span>
              <div class="stat-info">
                <span class="stat-value">{{ stats.burnt }}</span>
                <span class="stat-label">Burnt</span>
              </div>
            </div>
            <button 
              @click="togglePause" 
              class="stat-card action-card" 
              :class="{ 'paused': isPaused }"
              :disabled="isLoading || isFinished"
            >
              <span class="stat-icon">{{ isPaused ? '▶' : '⏸' }}</span>
              <div class="stat-info">
                <span class="stat-label">{{ isPaused ? 'Resume' : 'Pause' }}</span>
              </div>
            </button>
            <button @click="reset" class="stat-card action-card reset-card">
              <span class="stat-icon">↺</span>
              <div class="stat-info">
                <span class="stat-label">Reset</span>
              </div>
            </button>
          </div>

          <!-- Progress Bar -->
          <div class="progress-section">
            <div class="progress-header">
              <span class="progress-label">⏱️ Time Elapsed</span>
              <span class="progress-value">{{ elapsedSimulatedHours.toFixed(1) }}h / {{ simulationDuration }}h</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${(elapsedSimulatedHours / simulationDuration) * 100}%` }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Section 4: Emissions Charts -->
      <div class="section-block charts-section">
        <div class="section-header">
          <span class="section-icon">📈</span>
          <span class="section-title">Emissions Analysis</span>
          <div class="info-tooltip" @mouseenter="showTooltip($event, 'emissions')" @mouseleave="hideTooltip">
            <span class="info-icon">ⓘ</span>
          </div>
        </div>

        <div class="charts-grid">
          <!-- Simulated Pollution Chart -->
          <div class="chart-card">
            <div class="chart-header">
              <span class="chart-title">Simulated Emissions</span>
              <button class="chart-expand-btn" @click="openExpandedChart('simulated')" title="Expand chart">⛶</button>
            </div>
            <div class="chart-container">
              <div v-if="pollutionHistory.length < 2" class="chart-placeholder">
                <span class="placeholder-icon">📊</span>
                <span class="placeholder-text">Waiting for simulation data...</span>
              </div>
              <svg v-else :viewBox="`0 0 ${chartWidthMini} ${chartHeightMini}`" class="chart-svg">
                <polyline :points="simulatedPointsMini.co" fill="none" stroke="#8884d8" stroke-width="2"/>
                <polyline :points="simulatedPointsMini.no2" fill="none" stroke="#82ca9d" stroke-width="2"/>
                <polyline :points="simulatedPointsMini.pm2_5" fill="none" stroke="#ffc658" stroke-width="2"/>
              </svg>
            </div>
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot" style="background:#8884d8"></span>CO</span>
              <span class="legend-item"><span class="legend-dot" style="background:#82ca9d"></span>NO₂</span>
              <span class="legend-item"><span class="legend-dot" style="background:#ffc658"></span>PM2.5</span>
            </div>
          </div>

          <!-- Real Pollution Chart -->
          <div class="chart-card" v-if="realPollutionData.length > 0">
            <div class="chart-header">
              <span class="chart-title">Historical Data (24h)</span>
              <span class="chart-badge" :class="isPollutionMock ? 'simulated' : 'live'">
                {{ isPollutionMock ? 'SIMULATED' : 'LIVE' }}
              </span>
              <button class="chart-expand-btn" @click="openExpandedChart('historical')" title="Expand chart">⛶</button>
            </div>
            <div class="chart-container">
              <svg :viewBox="`0 0 ${chartWidthMini} ${chartHeightMini}`" class="chart-svg">
                <polyline :points="realPollutionPointsMini.co" fill="none" stroke="#8884d8" stroke-width="2"/>
                <polyline :points="realPollutionPointsMini.no2" fill="none" stroke="#82ca9d" stroke-width="2"/>
                <polyline :points="realPollutionPointsMini.pm2_5" fill="none" stroke="#ffc658" stroke-width="2"/>
              </svg>
            </div>
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot" style="background:#8884d8"></span>CO</span>
              <span class="legend-item"><span class="legend-dot" style="background:#82ca9d"></span>NO₂</span>
              <span class="legend-item"><span class="legend-dot" style="background:#ffc658"></span>PM2.5</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Click Instruction (only when no simulation running) -->
      <div class="click-instruction" v-if="!stats">
        <span class="instruction-icon">👆</span>
        <span class="instruction-text">Click anywhere on the map to place a fire and start simulation</span>
      </div>
    </div>

    <!-- Global Tooltip (rendered outside overflow containers) -->
    <Teleport to="body">
      <div 
        v-if="activeTooltip" 
        class="global-tooltip"
        :style="{ top: tooltipPosition.y + 'px', left: tooltipPosition.x + 'px' }"
      >
        <div v-html="tooltipTexts[activeTooltip]"></div>
      </div>
    </Teleport>

    <!-- Expanded Chart Modal -->
    <Teleport to="body">
      <div v-if="expandedChart" class="chart-modal-overlay" @click="closeExpandedChart">
        <div class="chart-modal" @click.stop>
          <div class="chart-modal-header">
            <h3>{{ expandedChart === 'simulated' ? 'Simulated Emissions' : 'Historical Pollution Data (24h)' }}</h3>
            <button class="close-modal-btn" @click="closeExpandedChart">×</button>
          </div>
          <div class="chart-modal-body">
            <!-- Simulated Chart Expanded -->
            <div v-if="expandedChart === 'simulated'" class="expanded-chart-container">
              <div v-if="pollutionHistory.length < 2" class="chart-placeholder">
                <span class="placeholder-icon">📊</span>
                <span class="placeholder-text">Waiting for simulation data...</span>
              </div>
              <svg v-else :viewBox="`0 0 ${chartWidthExpanded} ${chartHeightExpanded}`" class="chart-svg-expanded">
                <polyline :points="simulatedPointsExpanded.co" fill="none" stroke="#8884d8" stroke-width="3"/>
                <polyline :points="simulatedPointsExpanded.no2" fill="none" stroke="#82ca9d" stroke-width="3"/>
                <polyline :points="simulatedPointsExpanded.pm2_5" fill="none" stroke="#ffc658" stroke-width="3"/>
              </svg>
            </div>
            <!-- Historical Chart Expanded -->
            <div v-if="expandedChart === 'historical'" class="expanded-chart-container">
              <svg :viewBox="`0 0 ${chartWidthExpanded} ${chartHeightExpanded}`" class="chart-svg-expanded">
                <polyline :points="realPollutionPointsExpanded.co" fill="none" stroke="#8884d8" stroke-width="3"/>
                <polyline :points="realPollutionPointsExpanded.no2" fill="none" stroke="#82ca9d" stroke-width="3"/>
                <polyline :points="realPollutionPointsExpanded.pm2_5" fill="none" stroke="#ffc658" stroke-width="3"/>
              </svg>
            </div>
          </div>
          <div class="chart-modal-legend">
            <span class="legend-item-lg"><span class="legend-dot-lg" style="background:#8884d8"></span>CO (Carbon Monoxide)</span>
            <span class="legend-item-lg"><span class="legend-dot-lg" style="background:#82ca9d"></span>NO₂ (Nitrogen Dioxide)</span>
            <span class="legend-item-lg"><span class="legend-dot-lg" style="background:#ffc658"></span>PM2.5 (Particulate Matter)</span>
          </div>
        </div>
      </div>
    </Teleport>
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

// Tooltip state
const activeTooltip = ref<string | null>(null)
const tooltipPosition = ref({ x: 0, y: 0 })
const tooltipTexts: Record<string, string> = {
  weather: `<strong>Real Weather:</strong> Fetches real historical daily weather data. Use this to simulate a fire on a historical date.<br><br><strong>Custom Weather:</strong> Create your own weather scenario with custom temperature, wind, and rainfall settings.`,
  controls: `<strong>Fire Spread:</strong> View how the fire spreads on the map and how areas get burnt.<br><br><strong>Pollution:</strong> See how pollutants like CO, NO₂, and PM2.5 spread as a result of the fire.<br><br><strong>Duration:</strong> Select how long the fire simulation will last (1-24 hours).`,
  status: `Track the simulation progress: see how many cells are actively burning, how many have been burnt, and how much time has elapsed in the simulation.`,
  emissions: `Compare pollution levels: see how CO, NO₂, and PM2.5 emissions spike during fires versus historical baseline data.`
}

const showTooltip = (event: MouseEvent, key: string) => {
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  tooltipPosition.value = {
    x: rect.right + 10,
    y: rect.top
  }
  activeTooltip.value = key
}

const hideTooltip = () => {
  activeTooltip.value = null
}

// Expanded chart modal state
const expandedChart = ref<'simulated' | 'historical' | null>(null)
const chartWidthExpanded = 600
const chartHeightExpanded = 300

const openExpandedChart = (chart: 'simulated' | 'historical') => {
  expandedChart.value = chart
}

const closeExpandedChart = () => {
  expandedChart.value = null
}

// Simulation Constants
const GRID_SIZE = 150 // Increased from 100 to 150 for larger area (approx 4.5km x 4.5km)
const CELL_SIZE_METERS = 30 // Each cell is 30m x 30m

// State
const windDirection = ref(0)
const windSpeed = ref(0)
const rainLevel = ref(0)
const temperature = ref(15) // Temperature in Celsius
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
const isMockData = ref(false) // Track if weather data is simulated
const isPollutionMock = ref(false) // Track if pollution data is simulated

// Custom Weather Mode
const weatherMode = ref<'real' | 'custom'>('real')
const customWeather = ref({
  temperature: 15,
  windSpeed: 5,
  windDirection: 180,
  rain: 0,
  month: new Date().getMonth()
})

const switchWeatherMode = (mode: 'real' | 'custom') => {
  weatherMode.value = mode
  if (mode === 'custom') {
    applyCustomWeather()
  } else if (selectedLocation.value) {
    // Fetch real weather when switching back
    fetchWeather()
  }
}

const applyCustomWeather = () => {
  temperature.value = customWeather.value.temperature
  windSpeed.value = customWeather.value.windSpeed
  windDirection.value = customWeather.value.windDirection
  rainLevel.value = customWeather.value.rain
  // Update selected date to match the custom month for seasonal calculations
  const year = new Date().getFullYear()
  selectedDate.value = `${year}-${String(customWeather.value.month + 1).padStart(2, '0')}-15`
  isMockData.value = true // Mark as custom/simulated
}

const getSeasonName = (month: number): string => {
  const seasons = [
    'Winter', 'Winter', 'Early Spring', 'Spring', 'Late Spring', 'Summer',
    'Summer', 'Late Summer', 'Early Fall', 'Fall', 'Late Fall', 'Winter'
  ]
  return seasons[month] || 'Unknown'
}

// Seasonality Logic
const seasonalRiskFactor = computed(() => {
  // Use custom month if in custom mode, otherwise use selected date
  let month: number
  if (weatherMode.value === 'custom') {
    month = customWeather.value.month
  } else {
    const date = new Date(selectedDate.value)
    month = date.getMonth() // 0-11
  }
  
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

  // If in custom mode, just apply custom weather instead of fetching
  if (weatherMode.value === 'custom') {
    applyCustomWeather()
    return
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
      temperature.value = response.data.temp || 15 // Store temperature
      isMockData.value = response.data.is_mock || false // Track if data is simulated
    } else {
      console.error('Weather fetch failed:', response)
    }
  } catch (e) {
    console.error('Weather fetch error:', e)
    isMockData.value = true // Assume mock on error
  }

  // Fetch Pollution
  try {
    const response = await apiService.getPollution(targetLat, targetLng, timestamp)
    if (response.status === 'success' && response.data) {
      realPollutionData.value = response.data
      // Check if any data point has is_mock flag
      isPollutionMock.value = response.data.some((d: any) => d.is_mock) || false
    }
  } catch (e) {
    console.error('Pollution fetch error:', e)
    isPollutionMock.value = true // Assume mock on error
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

// Mini Chart dimensions for compact layout
const chartWidthMini = 200
const chartHeightMini = 60

const scaleYMini = (val: number, max: number) => chartHeightMini - (val / (max || 1)) * chartHeightMini
const scaleXMini = (i: number, total: number) => (i / (total - 1 || 1)) * chartWidthMini

const simulatedPointsMini = computed(() => {
  if (pollutionHistory.value.length < 2) return { co: '', no2: '', pm2_5: '' }
  const data = pollutionHistory.value
  const maxCO = Math.max(...data.map(d => d.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => `${scaleXMini(i, data.length)},${scaleYMini(d[key], max)}`).join(' ')
  }
  return { co: createPoints('co', maxCO), no2: createPoints('no2', maxNO2), pm2_5: createPoints('pm2_5', maxPM25) }
})

const realPollutionPointsMini = computed(() => {
  if (realPollutionData.value.length < 2) return { co: '', no2: '', pm2_5: '' }
  const data = realPollutionData.value
  const maxCO = Math.max(...data.map(d => d.components.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.components.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.components.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => `${scaleXMini(i, data.length)},${scaleYMini(d.components[key], max)}`).join(' ')
  }
  return { co: createPoints('co', maxCO), no2: createPoints('no2', maxNO2), pm2_5: createPoints('pm2_5', maxPM25) }
})

// Expanded chart scaling
const scaleYExpanded = (val: number, max: number) => chartHeightExpanded - (val / (max || 1)) * chartHeightExpanded
const scaleXExpanded = (i: number, total: number) => (i / (total - 1 || 1)) * chartWidthExpanded

const simulatedPointsExpanded = computed(() => {
  if (pollutionHistory.value.length < 2) return { co: '', no2: '', pm2_5: '' }
  const data = pollutionHistory.value
  const maxCO = Math.max(...data.map(d => d.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => `${scaleXExpanded(i, data.length)},${scaleYExpanded(d[key], max)}`).join(' ')
  }
  return { co: createPoints('co', maxCO), no2: createPoints('no2', maxNO2), pm2_5: createPoints('pm2_5', maxPM25) }
})

const realPollutionPointsExpanded = computed(() => {
  if (realPollutionData.value.length < 2) return { co: '', no2: '', pm2_5: '' }
  const data = realPollutionData.value
  const maxCO = Math.max(...data.map(d => d.components.co)) || 1
  const maxNO2 = Math.max(...data.map(d => d.components.no2)) || 1
  const maxPM25 = Math.max(...data.map(d => d.components.pm2_5)) || 1

  const createPoints = (key: 'co' | 'no2' | 'pm2_5', max: number) => {
    return data.map((d, i) => `${scaleXExpanded(i, data.length)},${scaleYExpanded(d.components[key], max)}`).join(' ')
  }
  return { co: createPoints('co', maxCO), no2: createPoints('no2', maxNO2), pm2_5: createPoints('pm2_5', maxPM25) }
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
}

/* Header - removed, keeping style for compatibility */
.panel-header {
  padding: 12px 16px;
  background: linear-gradient(135deg, #ff4500 0%, #ff8c00 100%);
  color: white;
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.description {
  margin: 2px 0 0 0;
  font-size: 0.8rem;
  opacity: 0.9;
}

/* Main Content - Scrollable */
.panel-content {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  overflow-y: auto;
}

/* Section Blocks - More compact */
.section-block {
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  flex-shrink: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.section-icon {
  font-size: 1rem;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1f2937;
  flex: 1;
}

/* Info Tooltip */
.info-tooltip {
  position: static;
  display: inline-flex;
  align-items: center;
}

.info-icon {
  font-size: 0.85rem;
  color: #9ca3af;
  cursor: help;
  transition: color 0.2s;
  user-select: none;
}

.info-icon:hover {
  color: #3b82f6;
}

/* Badges */
.live-badge, .mock-badge {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.live-badge {
  background: #10b981;
  color: white;
}

.mock-badge {
  background: #f59e0b;
  color: white;
}

/* Weather Controls */
.weather-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #4b5563;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Weather Source Row - inline toggle + date picker */
.weather-source-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.date-picker-inline {
  min-width: 140px;
}

.date-picker-inline :deep(.dp__input) {
  padding: 6px 8px 6px 32px;
  font-size: 0.8rem;
}

/* Toggle Group */
.toggle-group {
  display: flex;
  background: #e5e7eb;
  padding: 4px;
  border-radius: 8px;
  gap: 4px;
}

.toggle-btn {
  padding: 6px 10px;
  border: none;
  background: transparent;
  border-radius: 5px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.toggle-btn.large {
  padding: 8px 12px;
  font-size: 0.85rem;
}

.toggle-btn.active {
  background: white;
  color: #1f2937;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  font-weight: 600;
}

.toggle-btn:hover:not(.active) {
  background: rgba(255,255,255,0.5);
}

/* Date Picker */
:deep(.dp__input) {
  border-radius: 8px;
  border: 1px solid #d1d5db;
  padding: 10px 12px 10px 36px;
  font-size: 0.95rem;
  background: white;
}

/* Weather Display Grid */
.weather-display-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: #f0f7ff;
  border: 1px solid #e1effe;
  border-radius: 8px;
  padding: 10px;
}

.weather-stat {
  display: flex;
  align-items: center;
  gap: 6px;
}

.weather-icon {
  font-size: 1.2rem;
}

.weather-info {
  display: flex;
  flex-direction: column;
}

.weather-value {
  font-size: 0.95rem;
  font-weight: 700;
  color: #111827;
}

.weather-label {
  font-size: 0.65rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

/* Custom Weather Panel */
.custom-weather-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  margin-top: 8px;
}

.custom-sliders-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.slider-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #374151;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.custom-slider {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: #e5e7eb;
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.custom-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.slider-value {
  font-size: 0.8rem;
  font-weight: 700;
  color: #1f2937;
  min-width: 45px;
  text-align: right;
}

.custom-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #e2e8f0;
}

.month-select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.8rem;
  background: white;
  cursor: pointer;
}

.btn-apply {
  flex: 1;
  padding: 8px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-apply:hover {
  background: #2563eb;
}

/* Simulation Controls Grid */
.sim-controls-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
}

/* Pollutant Buttons */
.pollutant-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pollutant-btn {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  background: white;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.pollutant-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.pollutant-btn:hover:not(.active) {
  border-color: #3b82f6;
  color: #3b82f6;
}

/* Duration Control */
.duration-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.duration-slider {
  flex: 1;
  height: 5px;
  border-radius: 3px;
  background: linear-gradient(90deg, #ff8c00, #ff4500);
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.duration-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #ff4500;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.duration-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: #ff4500;
  min-width: 65px;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.85rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action .btn-icon {
  font-size: 1rem;
}

.btn-action.btn-primary {
  flex: 1;
  background: #10b981;
  color: white;
}

.btn-action.btn-primary:hover:not(:disabled) {
  background: #059669;
}

.btn-action.btn-primary.paused {
  background: #3b82f6;
}

.btn-action.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-action.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  padding: 10px 14px;
}

.btn-action.btn-secondary:hover {
  background: #e5e7eb;
}

/* Status Section */
.status-section {
  flex: 0;
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  justify-content: center;
}

.status-badge {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-badge.loading {
  background: #fff7ed;
  color: #c2410c;
}

.status-badge.finished {
  background: #ecfdf5;
  color: #047857;
}

.status-badge.waiting {
  background: #f3f4f6;
  color: #6b7280;
}

.status-badge.running {
  background: #fef3c7;
  color: #b45309;
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

/* Stats Cards */
.stats-cards {
  display: flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: wrap;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  min-width: 80px;
  border: 1px solid #e5e7eb;
}

.stat-card.burning {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.stat-card.burnt {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}

/* Action cards (pause/reset buttons styled as stat cards) */
.stat-card.action-card {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card.action-card:hover:not(:disabled) {
  background: #dcfce7;
  border-color: #86efac;
}

.stat-card.action-card.paused {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.stat-card.action-card.paused:hover {
  background: #dbeafe;
}

.stat-card.action-card:disabled {
  background: #f3f4f6;
  border-color: #e5e7eb;
  cursor: not-allowed;
  opacity: 0.6;
}

.stat-card.action-card.reset-card {
  background: #fef3c7;
  border-color: #fde68a;
}

.stat-card.action-card.reset-card:hover {
  background: #fde68a;
}

.stat-card .stat-icon {
  font-size: 1rem;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
}

.stat-label {
  font-size: 0.65rem;
  color: #6b7280;
  text-transform: uppercase;
}

/* Progress Section */
.progress-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 12px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.progress-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #4b5563;
}

.progress-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: #ff4500;
}

.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ff8c00, #ff4500);
  border-radius: 3px;
  transition: width 0.3s ease;
}

/* Charts Section */
.charts-section {
  flex: 0;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.chart-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.chart-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: #1f2937;
}

.chart-subtitle {
  font-size: 0.65rem;
  color: #6b7280;
  margin-left: 4px;
}

.chart-badge {
  font-size: 0.55rem;
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 3px;
  text-transform: uppercase;
}

.chart-badge.live {
  background: #10b981;
  color: white;
}

.chart-badge.simulated {
  background: #f59e0b;
  color: white;
}

.chart-container {
  flex: 1;
  min-height: 50px;
  max-height: 60px;
  margin-bottom: 6px;
}

.chart-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
  border-radius: 6px;
  gap: 4px;
}

.placeholder-icon {
  font-size: 1rem;
  opacity: 0.5;
}

.placeholder-text {
  font-size: 0.7rem;
  color: #9ca3af;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding-top: 4px;
  border-top: 1px solid #f3f4f6;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.7rem;
  font-weight: 500;
  color: #4b5563;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

/* Click Instruction */
.click-instruction {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border-radius: 8px;
  border: 1px dashed #7dd3fc;
}

.instruction-icon {
  font-size: 1.1rem;
}

.instruction-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #0369a1;
}

/* Chart Expand Button */
.chart-expand-btn {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  padding: 2px 6px;
  color: #6b7280;
  border-radius: 4px;
  transition: all 0.2s;
}

.chart-expand-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

/* Animation */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>

<!-- Global tooltip styles (not scoped) -->
<style>
.global-tooltip {
  position: fixed;
  background: #1f2937;
  color: white;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 0.8rem;
  line-height: 1.6;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  z-index: 99999;
  text-align: left;
  font-weight: 400;
  pointer-events: none;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.global-tooltip strong {
  color: #60a5fa;
  font-weight: 600;
}

/* Chart Modal Styles */
.chart-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99999;
  backdrop-filter: blur(2px);
}

.chart-modal {
  background: white;
  border-radius: 12px;
  padding: 0;
  min-width: 650px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.chart-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-bottom: 1px solid #e2e8f0;
}

.chart-modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1f2937;
}

.close-modal-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  padding: 4px 8px;
  line-height: 1;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-modal-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.chart-modal-body {
  padding: 24px;
}

.expanded-chart-container {
  width: 100%;
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-svg-expanded {
  width: 100%;
  height: 100%;
  max-width: 600px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
}

.chart-modal-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 16px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.legend-item-lg {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
}

.legend-dot-lg {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
</style>
