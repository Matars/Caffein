<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { apiService, type Fire } from '../services/api'

const mapContainer = ref<HTMLDivElement | null>(null)
const map = ref<maplibregl.Map | null>(null)
const isGlobeView = ref(false)
const is3DTerrain = ref(false)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const showResults = ref(false)
const isSearching = ref(false)
const fires = ref<Fire[]>([])
const isLoadingFires = ref(false)
const fireMarkers = ref<maplibregl.Marker[]>([])

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
        'No fire data found. Please run the seed script: python backend/scripts/seed_fire_occurrences.py',
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

  // Add markers for each fire
  fires.value.forEach((fire) => {
    if (!fire.Lat_DD || !fire.Long_DD) return

    // Create marker color based on cause
    const color = fire.HumanOrLightning === 'Lightning' ? '#FFA500' : '#FF0000'

    // Create popup content
    const popupContent = `
      <div style="font-family: sans-serif;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">${fire.FireName || 'Unnamed Fire'}</h3>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Year:</strong> ${fire.FireYear}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Acres:</strong> ${fire.EstTotalAcres?.toFixed(2) || 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Cause:</strong> ${fire.HumanOrLightning || 'Unknown'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>County:</strong> ${fire.County || 'N/A'}</p>
      </div>
    `

    // Create marker
    const marker = new maplibregl.Marker({ color, scale: 0.5 })
      .setLngLat([fire.Long_DD, fire.Lat_DD])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupContent))
      .addTo(map.value!)

    fireMarkers.value.push(marker)
  })

  // Fit map to show all markers
  if (fires.value.length > 0) {
    const bounds = new maplibregl.LngLatBounds()
    fires.value.forEach((fire) => {
      if (fire.Lat_DD && fire.Long_DD) {
        bounds.extend([fire.Long_DD, fire.Lat_DD])
      }
    })
    map.value.fitBounds(bounds, { padding: 50, maxZoom: 10 })
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

    <!-- Toggle Controls -->
    <div class="toggle-controls">
      <button @click="toggleProjection" class="toggle-button">
        <span v-if="isGlobeView">🗺️ Flat Map</span>
        <span v-else>🌍 Globe View</span>
      </button>

      <button @click="toggle3DTerrain" class="toggle-button">
        <span v-if="is3DTerrain">📍 2D View</span>
        <span v-else>⛰️ 3D Terrain</span>
      </button>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoadingFires" class="loading-indicator">
      <div class="spinner"></div>
      <p>Loading fire data...</p>
    </div>

    <!-- Fire Stats -->
    <div v-if="fires.length > 0" class="fire-stats">
      <p>🔥 {{ fires.length.toLocaleString() }} fires loaded</p>
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

/* Toggle Controls */
.toggle-controls {
  position: absolute;
  bottom: 100px;
  left: 20px;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toggle-button {
  background: white;
  border: none;
  border-radius: 8px;
  padding: 12px 20px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.toggle-button:hover {
  background: #f0f0f0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

.toggle-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .search-container {
    width: calc(100% - 40px);
    max-width: none;
  }

  .toggle-controls {
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    flex-direction: row;
    width: calc(100% - 40px);
    justify-content: center;
  }

  .toggle-button {
    flex: 1;
    justify-content: center;
    font-size: 14px;
    padding: 10px 16px;
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

/* Fire Stats */
.fire-stats {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1;
  font-weight: 600;
  color: #333;
}

.fire-stats p {
  margin: 0;
}
</style>
