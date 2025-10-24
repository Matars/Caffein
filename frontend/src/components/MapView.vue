<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { apiService, type FireDetection, type NO2Measurement } from '../services/api'

const mapContainer = ref<HTMLDivElement | null>(null)
const map = ref<maplibregl.Map | null>(null)
const isGlobeView = ref(false)
const is3DTerrain = ref(false)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const showResults = ref(false)
const isSearching = ref(false)
const fires = ref<FireDetection[]>([])
const isLoadingFires = ref(false)
const fireMarkers = ref<maplibregl.Marker[]>([])
const isDropFireMode = ref(false)
const droppedFireLocation = ref<{ lng: number; lat: number } | null>(null)
const droppedFireMarker = ref<maplibregl.Marker | null>(null)
const isMenuOpen = ref(false)
const no2Measurements = ref<NO2Measurement[]>([])
const isLoadingNO2 = ref(false)
const no2Markers = ref<maplibregl.Marker[]>([])
const showNO2Layer = ref(false)
const showFireLayer = ref(true)

const initMap = () => {
  if (!mapContainer.value) return

  map.value = new maplibregl.Map({
    container: mapContainer.value,
    zoom: 2,
    center: [0, 20],
    pitch: 0,
    hash: true,
    style: {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '&copy; OpenStreetMap Contributors',
          maxzoom: 19,
        },
        terrainSource: {
          type: 'raster-dem',
          url: 'https://demotiles.maplibre.org/terrain-tiles/tiles.json',
          tileSize: 256,
        },
        hillshadeSource: {
          type: 'raster-dem',
          url: 'https://demotiles.maplibre.org/terrain-tiles/tiles.json',
          tileSize: 256,
        },
      },
      layers: [
        {
          id: 'osm',
          type: 'raster',
          source: 'osm',
        },
        {
          id: 'hills',
          type: 'hillshade',
          source: 'hillshadeSource',
          layout: { visibility: 'none' },
          paint: { 'hillshade-shadow-color': '#473B24' },
        },
      ],
    },
    maxZoom: 18,
    maxPitch: 85,
  })

  // Add navigation controls with pitch visualization
  map.value.addControl(
    new maplibregl.NavigationControl({
      visualizePitch: true,
      showZoom: true,
      showCompass: true,
    }),
    'top-right',
  )

  // Add scale control
  map.value.addControl(new maplibregl.ScaleControl(), 'bottom-left')

  // Load fire data after map is initialized
  map.value.on('load', () => {
    loadFireData()
  })

  // Add click handler for dropping fire starting points
  map.value.on('click', handleMapClick)
}

const loadFireData = async () => {
  if (!map.value) return

  isLoadingFires.value = true
  try {
    const response = await apiService.getFires()
    fires.value = response.data
    console.log(`Loaded ${fires.value.length} fire records`)

    if (fires.value.length === 0) {
      console.warn('No fire data available. Run the seed script to populate the database.')
      alert(
        'No fire data found. Please run the seed script: python backend/scripts/seed_fire_detections.py',
      )
    } else {
      displayFireMarkers()
    }
  } catch (error) {
    console.error('Error loading fire data:', error)
    alert(`Error loading fire data: ${error}. Please check that the backend is running.`)
  } finally {
    isLoadingFires.value = false
  }
}

const displayFireMarkers = () => {
  if (!map.value) return

  // Clear existing markers
  fireMarkers.value.forEach((marker) => marker.remove())
  fireMarkers.value = []

  if (!showFireLayer.value) return

  // Add markers for each fire detection
  fires.value.forEach((fire) => {
    if (!fire.latitude || !fire.longitude) return

    // Create marker color based on confidence
    let color = '#FF6B00' // Default orange
    if (fire.confidence) {
      const conf = parseInt(fire.confidence)
      if (conf >= 80) color = '#FF0000' // High confidence - red
      else if (conf >= 50) color = '#FF6B00' // Medium confidence - orange
      else color = '#FFAA00' // Low confidence - yellow
    }

    // Create popup content with FIRMS data
    const popupContent = `
      <div style="font-family: sans-serif;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">🔥 Fire Detection</h3>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Date:</strong> ${fire.acq_date} ${fire.acq_time || ''}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Satellite:</strong> ${fire.satellite || 'N/A'} (${fire.instrument || 'N/A'})</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Confidence:</strong> ${fire.confidence || 'N/A'}%</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>FRP:</strong> ${fire.frp ? fire.frp.toFixed(1) + ' MW' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Brightness:</strong> ${fire.brightness ? fire.brightness.toFixed(1) + ' K' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Day/Night:</strong> ${fire.daynight === 'D' ? 'Day' : fire.daynight === 'N' ? 'Night' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 11px; color: #666;">Lat: ${fire.latitude.toFixed(4)}, Lon: ${fire.longitude.toFixed(4)}</p>
      </div>
    `

    // Create marker
    const marker = new maplibregl.Marker({ color, scale: 0.6 })
      .setLngLat([fire.longitude, fire.latitude])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupContent))
      .addTo(map.value!)

    fireMarkers.value.push(marker)
  })

  // Fit map to show all markers
  if (fires.value.length > 0) {
    const bounds = new maplibregl.LngLatBounds()
    fires.value.forEach((fire) => {
      if (fire.latitude && fire.longitude) {
        bounds.extend([fire.longitude, fire.latitude])
      }
    })
    map.value.fitBounds(bounds, { padding: 50, maxZoom: 10 })
  }
}

const loadNO2Data = async () => {
  if (!map.value) return

  isLoadingNO2.value = true
  try {
    const response = await apiService.getNO2({ limit: 100000, min_qa: 0.5 })
    no2Measurements.value = response.data
    console.log(`Loaded ${no2Measurements.value.length} NO2 measurement records`)

    if (no2Measurements.value.length === 0) {
      console.warn('No NO2 data available. Run the seed script to populate the database.')
    } else if (showNO2Layer.value) {
      displayNO2Markers()
    }
  } catch (error) {
    console.error('Error loading NO2 data:', error)
  } finally {
    isLoadingNO2.value = false
  }
}

const displayNO2Markers = () => {
  if (!map.value) return

  // Clear existing NO2 markers
  no2Markers.value.forEach((marker) => marker.remove())
  no2Markers.value = []

  if (!showNO2Layer.value) return

  // Add markers for each NO2 measurement
  no2Measurements.value.forEach((measurement) => {
    if (!measurement.latitude || !measurement.longitude || !measurement.no2_column) return

    // Color code based on NO2 concentration levels (molecules/cm²)
    // Typical tropospheric NO2: 1e14 - 1e16 molecules/cm²
    const no2Value = measurement.no2_column
    let color = '#00FF00' // Green - low

    if (no2Value > 1e16) color = '#8B0000' // Dark red - very high
    else if (no2Value > 5e15) color = '#FF0000' // Red - high
    else if (no2Value > 2e15) color = '#FF6B00' // Orange - moderate-high
    else if (no2Value > 1e15) color = '#FFAA00' // Yellow - moderate
    else if (no2Value > 5e14) color = '#90EE90' // Light green - low-moderate

    // Create popup content with NO2 data
    const popupContent = `
      <div style="font-family: sans-serif;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">🌫️ NO2 Measurement</h3>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Date:</strong> ${measurement.measurement_date}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>NO2 Column:</strong> ${(no2Value).toExponential(2)} mol/cm²</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Quality:</strong> ${measurement.qa_value ? (measurement.qa_value * 100).toFixed(1) + '%' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Cloud Fraction:</strong> ${measurement.cloud_fraction ? (measurement.cloud_fraction * 100).toFixed(1) + '%' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 11px; color: #666;">Lat: ${measurement.latitude.toFixed(4)}, Lon: ${measurement.longitude.toFixed(4)}</p>
      </div>
    `

    // Create marker
    const marker = new maplibregl.Marker({ color, scale: 0.5 })
      .setLngLat([measurement.longitude, measurement.latitude])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupContent))
      .addTo(map.value!)

    no2Markers.value.push(marker)
  })
}

const toggleFireLayer = () => {
  showFireLayer.value = !showFireLayer.value
  displayFireMarkers()
}

const toggleNO2Layer = () => {
  showNO2Layer.value = !showNO2Layer.value

  if (showNO2Layer.value && no2Measurements.value.length === 0) {
    // Load NO2 data if not already loaded
    loadNO2Data()
  } else {
    displayNO2Markers()
  }
}

const toggleProjection = () => {
  if (!map.value) return
  isGlobeView.value = !isGlobeView.value
  map.value.setProjection({ type: isGlobeView.value ? 'globe' : 'mercator' })
}

const toggle3DTerrain = () => {
  if (!map.value) return
  is3DTerrain.value = !is3DTerrain.value

  if (is3DTerrain.value) {
    // Enable 3D terrain
    map.value.setTerrain({ source: 'terrainSource', exaggeration: 1 })
    map.value.setLayoutProperty('hills', 'visibility', 'visible')
    map.value.setPitch(70)
    // Add sky
    map.value.setSky({})
  } else {
    // Disable 3D terrain
    map.value.setTerrain(null)
    map.value.setLayoutProperty('hills', 'visibility', 'none')
    map.value.setPitch(0)
    // Remove sky by setting it to undefined
    map.value.setSky(undefined as any)
  }
}

// Geocoding search using Nominatim (OpenStreetMap)
const searchLocation = async () => {
  if (!searchQuery.value.trim()) return

  isSearching.value = true
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        searchQuery.value,
      )}&limit=5`,
    )
    const data = await response.json()
    searchResults.value = data
    showResults.value = data.length > 0
  } catch (error) {
    console.error('Search error:', error)
  } finally {
    isSearching.value = false
  }
}

const selectLocation = (result: any) => {
  if (!map.value) return

  const lat = parseFloat(result.lat)
  const lon = parseFloat(result.lon)

  // Fly to the selected location
  map.value.flyTo({
    center: [lon, lat],
    zoom: 12,
    essential: true,
  })

  // Add a marker
  new maplibregl.Marker({ color: '#FF0000' })
    .setLngLat([lon, lat])
    .setPopup(new maplibregl.Popup().setHTML(`<strong>${result.display_name}</strong>`))
    .addTo(map.value)

  // Clear search
  showResults.value = false
  searchQuery.value = ''
}

const handleSearchInput = () => {
  if (searchQuery.value.length > 2) {
    searchLocation()
  } else {
    showResults.value = false
  }
}

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value
}

const toggleDropFireMode = () => {
  isDropFireMode.value = !isDropFireMode.value

  if (!isDropFireMode.value) {
    // Remove the dropped fire marker when exiting drop mode
    if (droppedFireMarker.value) {
      droppedFireMarker.value.remove()
      droppedFireMarker.value = null
    }
    droppedFireLocation.value = null

    // Reset cursor
    if (map.value) {
      map.value.getCanvas().style.cursor = ''
    }
  } else {
    // Change cursor to crosshair when in drop mode
    if (map.value) {
      map.value.getCanvas().style.cursor = 'crosshair'
    }
  }
}

const handleMapClick = (e: maplibregl.MapMouseEvent) => {
  if (!isDropFireMode.value || !map.value) return

  const { lng, lat } = e.lngLat

  // Store the dropped fire location
  droppedFireLocation.value = { lng, lat }

  // Remove previous marker if it exists
  if (droppedFireMarker.value) {
    droppedFireMarker.value.remove()
  }

  // Create a distinctive marker for the dropped fire starting point
  const el = document.createElement('div')
  el.className = 'fire-drop-marker'
  el.style.width = '30px'
  el.style.height = '30px'
  el.style.borderRadius = '50%'
  el.style.backgroundColor = '#FF4500'
  el.style.border = '3px solid #FFD700'
  el.style.boxShadow = '0 0 10px rgba(255, 69, 0, 0.8)'
  el.style.cursor = 'pointer'
  el.innerHTML = '🔥'
  el.style.display = 'flex'
  el.style.alignItems = 'center'
  el.style.justifyContent = 'center'
  el.style.fontSize = '18px'

  // Create popup with coordinates
  const popupContent = `
    <div style="font-family: sans-serif; min-width: 200px;">
      <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #FF4500;">🔥 Fire Starting Point</h3>
      <p style="margin: 4px 0; font-size: 12px;"><strong>Latitude:</strong> ${lat.toFixed(6)}</p>
      <p style="margin: 4px 0; font-size: 12px;"><strong>Longitude:</strong> ${lng.toFixed(6)}</p>
      <p style="margin: 8px 0 4px 0; font-size: 11px; color: #666;">Click again to relocate</p>
    </div>
  `

  // Create and add the marker
  droppedFireMarker.value = new maplibregl.Marker({ element: el })
    .setLngLat([lng, lat])
    .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupContent))
    .addTo(map.value)

  console.log('Fire starting point dropped at:', { lng, lat })
}

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  map.value?.remove()
})
</script>

<template>
  <div class="map-wrapper">
    <div ref="mapContainer" class="map-container"></div>

    <!-- Search Bar -->
    <div class="search-container">
      <input
        v-model="searchQuery"
        @input="handleSearchInput"
        @keyup.enter="searchLocation"
        type="text"
        placeholder="Search location..."
        class="search-input"
      />
      <button @click="searchLocation" class="search-button" :disabled="isSearching">🔍</button>

      <!-- Search Results Dropdown -->
      <div v-if="showResults" class="search-results">
        <div
          v-for="(result, index) in searchResults"
          :key="index"
          @click="selectLocation(result)"
          class="search-result-item"
        >
          {{ result.display_name }}
        </div>
      </div>
    </div>

    <!-- Hamburger Menu Button -->
    <button @click="toggleMenu" class="hamburger-button" :class="{ open: isMenuOpen }">
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
    </button>

    <!-- Menu Panel -->
    <div v-if="isMenuOpen" class="menu-panel">
      <button @click="toggleProjection" class="menu-item">
        <span v-if="isGlobeView">🗺️ Flat Map</span>
        <span v-else>🌍 Globe View</span>
      </button>

      <button @click="toggle3DTerrain" class="menu-item">
        <span v-if="is3DTerrain">📍 2D View</span>
        <span v-else>⛰️ 3D Terrain</span>
      </button>

      <button @click="toggleFireLayer" :class="['menu-item', { active: showFireLayer }]">
        <span v-if="showFireLayer">🔥 Hide Fires</span>
        <span v-else>🔥 Show Fires</span>
      </button>

      <button @click="toggleNO2Layer" :class="['menu-item', { active: showNO2Layer }]">
        <span v-if="showNO2Layer">🌫️ Hide NO2</span>
        <span v-else>🌫️ Show NO2</span>
      </button>

      <button @click="toggleDropFireMode" :class="['menu-item', { active: isDropFireMode }]">
        <span v-if="isDropFireMode">✓ Drop Fire Mode</span>
        <span v-else>🔥 Drop Fire</span>
      </button>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoadingFires || isLoadingNO2" class="loading-indicator">
      <div class="spinner"></div>
      <p v-if="isLoadingFires">Loading fire data...</p>
      <p v-if="isLoadingNO2">Loading NO2 data...</p>
    </div>

    <!-- Data Stats -->
    <div v-if="fires.length > 0 || no2Measurements.length > 0" class="data-stats">
      <p v-if="fires.length > 0 && showFireLayer">🔥 {{ fires.length.toLocaleString() }} fires</p>
      <p v-if="no2Measurements.length > 0 && showNO2Layer">
        🌫️ {{ no2Measurements.length.toLocaleString() }} NO2 measurements
      </p>
    </div>
  </div>
</template>

<style scoped>
.map-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

/* Search Container */
.search-container {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  width: 90%;
  max-width: 500px;
}

.search-input {
  width: 100%;
  padding: 12px 50px 12px 16px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  outline: none;
  transition: box-shadow 0.2s ease;
}

.search-input:focus {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.search-button {
  position: absolute;
  right: 4px;
  top: 4px;
  background: transparent;
  border: none;
  padding: 8px 12px;
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s ease;
}

.search-button:hover {
  background: #f0f0f0;
}

.search-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Search Results Dropdown */
.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 8px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 300px;
  overflow-y: auto;
  z-index: 3;
}

.search-result-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s ease;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background: #f8f8f8;
}

/* Hamburger Menu Button */
.hamburger-button {
  position: absolute;
  bottom: 100px;
  left: 20px;
  z-index: 3;
  background: white;
  border: none;
  border-radius: 8px;
  width: 50px;
  height: 50px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0;
}

.hamburger-button:hover {
  background: #f0f0f0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

.hamburger-line {
  width: 24px;
  height: 3px;
  background: #333;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.hamburger-button.open .hamburger-line:nth-child(1) {
  transform: translateY(8px) rotate(45deg);
}

.hamburger-button.open .hamburger-line:nth-child(2) {
  opacity: 0;
}

.hamburger-button.open .hamburger-line:nth-child(3) {
  transform: translateY(-8px) rotate(-45deg);
}

/* Menu Panel */
.menu-panel {
  position: absolute;
  bottom: 100px;
  left: 80px;
  z-index: 2;
  background: white;
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 180px;
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.menu-item {
  background: transparent;
  border: none;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  text-align: left;
  color: #333;
}

.menu-item:hover {
  background: #f0f0f0;
}

.menu-item.active {
  background: #ff6b35;
  color: white;
}

.menu-item.active:hover {
  background: #ff5722;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .search-container {
    width: calc(100% - 40px);
    max-width: none;
  }

  .hamburger-button {
    bottom: 20px;
    left: 20px;
  }

  .menu-panel {
    bottom: 20px;
    left: 80px;
  }

  .menu-item {
    font-size: 14px;
    padding: 10px 14px;
  }
}

/* Loading Indicator */
.loading-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 24px 32px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #ff6b35;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Data Stats */
.data-stats {
  position: absolute;
  top: 80px;
  left: 20px;
  background: white;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1;
  font-weight: 600;
  color: #333;
}

.data-stats p {
  margin: 4px 0;
  font-size: 14px;
}
</style>
