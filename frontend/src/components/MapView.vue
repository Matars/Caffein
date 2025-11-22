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
const isBboxMode = ref(false)
const bboxStartPoint = ref<{ lng: number; lat: number } | null>(null)
const bboxLayer = ref<any>(null)
const bboxSource = ref<any>(null)
const athenaFires = ref<any[]>([])
const isLoadingAthena = ref(false)
const currentBbox = ref<{ min_lat: number; max_lat: number; min_lon: number; max_lon: number } | null>(null)
const cursorX = ref(0)
const cursorY = ref(0)

// Time filter state (2024 months: 0=Jan, 11=Dec)
const selectedMonth = ref(0) // Default to January 2024
const months = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

// Track mouse position for cursor tooltip
const handleMouseMove = (e: MouseEvent) => {
  cursorX.value = e.clientX + 10
  cursorY.value = e.clientY + 10
}

// Forward declarations for functions used in initMap
const displayAthenaFireMarkers = () => {
  if (!map.value) return

  // Clear existing markers (keep the bbox on map)
  fireMarkers.value.forEach((marker) => marker.remove())
  fireMarkers.value = []

  // Add markers for each Athena fire
  athenaFires.value.forEach((fire: any) => {
    if (!fire.latitude || !fire.longitude) return

    let color = '#FF6B00'
    if (fire.confidence) {
      const conf = parseInt(fire.confidence)
      if (conf >= 80) color = '#FF0000'
      else if (conf >= 50) color = '#FF6B00'
      else color = '#FFAA00'
    }

    const popupContent = `
      <div style="font-family: sans-serif;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">🔥 Fire Detection (Athena)</h3>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Date:</strong> ${fire.acq_date || 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Confidence:</strong> ${fire.confidence || 'N/A'}%</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>FRP:</strong> ${fire.frp ? fire.frp.toFixed(1) + ' MW' : 'N/A'}</p>
        <p style="margin: 4px 0; font-size: 11px; color: #666;">Lat: ${fire.latitude.toFixed(4)}, Lon: ${fire.longitude.toFixed(4)}</p>
      </div>
    `

    const marker = new maplibregl.Marker({ color, scale: 0.6 })
      .setLngLat([fire.longitude, fire.latitude])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupContent))
      .addTo(map.value!)

    fireMarkers.value.push(marker)
  })
}

const handleMapClick = (e: maplibregl.MapMouseEvent) => {
  if (isBboxMode.value && map.value) {
    const { lng, lat } = e.lngLat

    if (!bboxStartPoint.value) {
      // First click - set start point
      bboxStartPoint.value = { lng, lat }
    } else {
      // Second click - create bounding box and query
      const minLat = Math.min(bboxStartPoint.value.lat, lat)
      const maxLat = Math.max(bboxStartPoint.value.lat, lat)
      const minLon = Math.min(bboxStartPoint.value.lng, lng)
      const maxLon = Math.max(bboxStartPoint.value.lng, lng)

      currentBbox.value = { min_lat: minLat, max_lat: maxLat, min_lon: minLon, max_lon: maxLon }
      drawBoundingBox(minLat, maxLat, minLon, maxLon)
      queryAthenaFires(minLat, maxLat, minLon, maxLon)

      bboxStartPoint.value = null
      
      // Automatically exit bbox mode after completing the query
      isBboxMode.value = false
      if (map.value) {
        map.value.getCanvas().style.cursor = ''
      }
    }
    return
  }

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

const drawBoundingBox = (minLat: number, maxLat: number, minLon: number, maxLon: number) => {
  if (!map.value) return

  // Create GeoJSON for the bbox rectangle
  const bboxGeoJson = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [minLon, minLat],
              [maxLon, minLat],
              [maxLon, maxLat],
              [minLon, maxLat],
              [minLon, minLat],
            ],
          ],
        },
      },
    ],
  }

  // Remove old layer and source if they exist
  if (bboxLayer.value && map.value.getLayer(bboxLayer.value)) {
    map.value.removeLayer(bboxLayer.value)
  }
  if (bboxSource.value && map.value.getSource(bboxSource.value)) {
    map.value.removeSource(bboxSource.value)
  }

  // Add new source
  const sourceId = 'bbox-source'
  const layerId = 'bbox-layer'

  map.value.addSource(sourceId, {
    type: 'geojson',
    data: bboxGeoJson as any,
  })

  // Add fill layer
  map.value.addLayer({
    id: layerId,
    type: 'fill',
    source: sourceId,
    paint: {
      'fill-color': '#088',
      'fill-opacity': 0.1,
    },
  })

  // Add border
  map.value.addLayer({
    id: `${layerId}-border`,
    type: 'line',
    source: sourceId,
    paint: {
      'line-color': '#088',
      'line-width': 2,
    },
  })

  bboxSource.value = sourceId
  bboxLayer.value = layerId
}

const getMonthDateRange = (monthIndex: number) => {
  const year = 2024
  const startDate = new Date(year, monthIndex, 1)
  const endDate = new Date(year, monthIndex + 1, 0) // Last day of month
  
  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0]
  }
  
  return {
    start_date: formatDate(startDate),
    end_date: formatDate(endDate)
  }
}

const queryAthenaFires = async (
  minLat: number,
  maxLat: number,
  minLon: number,
  maxLon: number,
) => {
  if (!map.value) return

  isLoadingAthena.value = true
  try {
    const dateRange = getMonthDateRange(selectedMonth.value)
    const response = await apiService.getFiresAthena({
      min_lat: minLat,
      max_lat: maxLat,
      min_lon: minLon,
      max_lon: maxLon,
      limit: 1000,
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
    })

    athenaFires.value = response.data
    console.log(`Loaded ${athenaFires.value.length} fires from Athena for ${months[selectedMonth.value]} 2024`)

    // Display fires on map
    displayAthenaFireMarkers()

    // Fit map to show query results
    if (athenaFires.value.length > 0) {
      const bounds = new maplibregl.LngLatBounds()
      athenaFires.value.forEach((fire: any) => {
        if (fire.latitude && fire.longitude) {
          bounds.extend([fire.longitude, fire.latitude])
        }
      })
      map.value.fitBounds(bounds, { padding: 50, maxZoom: 12 })
    }
  } catch (error) {
    console.error('Error querying Athena fires:', error)
    alert(`Error querying fires: ${error}`)
  } finally {
    isLoadingAthena.value = false
  }
}

const initMap = () => {
  if (!mapContainer.value) return

  map.value = new maplibregl.Map({
    container: mapContainer.value,
    zoom: 6,
    center: [18.0686, 59.3293], // Stockholm, Sweden
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
  map.value.on('load', async () => {
    // Load default fires using Athena with wide bounding box (all Sweden)
    try {
      // Sweden bounding box
      const defaultBbox = {
        min_lat: 55.0,
        max_lat: 69.0,
        min_lon: 11.0,
        max_lon: 24.0,
        limit: 500,
      }
      const dateRange = getMonthDateRange(selectedMonth.value)
      const response = await apiService.getFiresAthena({
        ...defaultBbox,
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      })
      athenaFires.value = response.data
      currentBbox.value = {
        min_lat: defaultBbox.min_lat,
        max_lat: defaultBbox.max_lat,
        min_lon: defaultBbox.min_lon,
        max_lon: defaultBbox.max_lon,
      }
      console.log(`Loaded ${athenaFires.value.length} fire records from Athena for ${months[selectedMonth.value]} 2024`)
      if (athenaFires.value.length > 0) {
        displayAthenaFireMarkers()
        // Fit map to show all markers
        const bounds = new maplibregl.LngLatBounds()
        athenaFires.value.forEach((fire: any) => {
          if (fire.latitude && fire.longitude) {
            bounds.extend([fire.longitude, fire.latitude])
          }
        })
        map.value.fitBounds(bounds, { padding: 50, maxZoom: 10 })
      }
    } catch (err) {
      console.warn('Could not fetch fires from Athena', err)
      alert('Could not load fire data. Please ensure Athena endpoint is available.')
    }
  })

  // Add click handler for dropping fire starting points
  map.value.on('click', handleMapClick)
}

const loadFireData = async () => {
  // Deprecated: Use Athena instead
  console.warn('loadFireData deprecated, use Athena endpoint')
}

const displayFireMarkers = () => {
  // Deprecated: Use displayAthenaFireMarkers instead
  console.warn('displayFireMarkers deprecated, use displayAthenaFireMarkers instead')
}

// Build months array (YYYY-MM) between min and max inclusive
const buildMonths = (minDateStr: string, maxDateStr: string) => {
  // Deprecated: No longer used with Athena
  console.warn('buildMonths deprecated')
}

const formatMonthLabel = (ym: string) => {
  // Deprecated: No longer used with Athena
  return ''
}

const loadFireDataForSelectedMonth = async () => {
  // Deprecated: Use queryAthenaFires instead
  console.warn('loadFireDataForSelectedMonth deprecated')
}

const loadNO2Data = async () => {
  if (!map.value) return

  isLoadingNO2.value = true
  try {
    const response = await apiService.getNO2({ limit: 100, min_qa: 0.5 })
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

    if (no2Value > 1e16)
      color = '#8B0000' // Dark red - very high
    else if (no2Value > 5e15)
      color = '#FF0000' // Red - high
    else if (no2Value > 2e15)
      color = '#FF6B00' // Orange - moderate-high
    else if (no2Value > 1e15)
      color = '#FFAA00' // Yellow - moderate
    else if (no2Value > 5e14) color = '#90EE90' // Light green - low-moderate

    // Create popup content with NO2 data
    const popupContent = `
      <div style="font-family: sans-serif;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">🌫️ NO2 Measurement</h3>
        <p style="margin: 4px 0; font-size: 12px;"><strong>Date:</strong> ${measurement.measurement_date}</p>
        <p style="margin: 4px 0; font-size: 12px;"><strong>NO2 Column:</strong> ${no2Value.toExponential(2)} mol/cm²</p>
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

const toggleBboxMode = () => {
  isBboxMode.value = !isBboxMode.value

  if (!isBboxMode.value) {
    // Exit bbox mode
    bboxStartPoint.value = null
    if (map.value) {
      map.value.getCanvas().style.cursor = ''
    }
  } else {
    // Enter bbox mode
    if (map.value) {
      map.value.getCanvas().style.cursor = 'crosshair'
    }
  }
}

// Month navigation functions
const prevMonth = () => {
  if (selectedMonth.value > 0) {
    selectedMonth.value--
    reloadFiresForCurrentView()
  }
}

const nextMonth = () => {
  if (selectedMonth.value < 11) {
    selectedMonth.value++
    reloadFiresForCurrentView()
  }
}

const selectMonth = (monthIndex: number) => {
  selectedMonth.value = monthIndex
  reloadFiresForCurrentView()
}

const reloadFiresForCurrentView = () => {
  if (currentBbox.value) {
    // If bbox is set, reload with bbox
    queryAthenaFires(
      currentBbox.value.min_lat,
      currentBbox.value.max_lat,
      currentBbox.value.min_lon,
      currentBbox.value.max_lon
    )
  } else {
    // Otherwise reload with default Sweden bbox
    queryAthenaFires(55.0, 69.0, 11.0, 24.0)
  }
}

onMounted(() => {
  initMap()
  // Add mouse move listener for cursor tooltip
  window.addEventListener('mousemove', handleMouseMove)
})

onBeforeUnmount(() => {
  map.value?.remove()
  // Remove mouse move listener
  window.removeEventListener('mousemove', handleMouseMove)
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

      <button @click="toggleBboxMode" :class="['menu-item', { active: isBboxMode }]">
        <span v-if="isBboxMode">✓ Bbox Query Mode</span>
        <span v-else>📦 Query by Bbox</span>
      </button>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoadingAthena || isLoadingNO2" class="loading-indicator">
      <div class="spinner"></div>
      <p v-if="isLoadingAthena">Loading fire data...</p>
      <p v-if="isLoadingNO2">Loading NO2 data...</p>
    </div>

    <!-- Data Stats -->
    <div v-if="athenaFires.length > 0 || no2Measurements.length > 0" class="data-stats">
      <p v-if="athenaFires.length > 0 && showFireLayer">🔥 {{ athenaFires.length.toLocaleString() }} fires</p>
      <p v-if="no2Measurements.length > 0 && showNO2Layer">
        🌫️ {{ no2Measurements.length.toLocaleString() }} NO2 measurements
      </p>
    </div>

    <!-- Athena Bbox Query Info -->
    <div v-if="currentBbox && athenaFires.length > 0" class="bbox-info">
      <p style="margin: 0 0 8px 0; font-weight: 600;">📦 Bbox Query Results</p>
      <p style="margin: 2px 0; font-size: 12px;">🔥 {{ athenaFires.length.toLocaleString() }} fires found</p>
      <p style="margin: 2px 0; font-size: 11px; color: #666;">
        Lat: {{ currentBbox.min_lat.toFixed(2) }} to {{ currentBbox.max_lat.toFixed(2) }}
      </p>
      <p style="margin: 2px 0; font-size: 11px; color: #666;">
        Lon: {{ currentBbox.min_lon.toFixed(2) }} to {{ currentBbox.max_lon.toFixed(2) }}
      </p>
    </div>

    <!-- Cursor tooltip for bbox mode -->
    <div 
      v-if="isBboxMode" 
      class="cursor-tooltip"
      :style="{ left: cursorX + 'px', top: cursorY + 'px' }"
    >
      {{ bboxStartPoint ? '2nd corner' : '1st corner' }}
    </div>

    <!-- Time Slider -->
    <div class="time-slider-container">
      <div class="time-slider-header">
        <span class="time-slider-title">🔥 2024 - {{ months[selectedMonth] }}</span>
      </div>
      
      <div class="time-slider-controls">
        <button 
          @click="prevMonth" 
          :disabled="selectedMonth === 0"
          class="month-nav-btn"
          title="Previous month"
        >
          ◀
        </button>
        
        <div class="month-slider">
          <div 
            v-for="(month, index) in months" 
            :key="index"
            @click="selectMonth(index)"
            :class="['month-notch', { active: selectedMonth === index }]"
            :title="month + ' 2024'"
          >
            <span class="month-label">{{ month }}</span>
          </div>
        </div>
        
        <button 
          @click="nextMonth" 
          :disabled="selectedMonth === 11"
          class="month-nav-btn"
          title="Next month"
        >
          ▶
        </button>
      </div>
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

/* Bbox Info */
.bbox-info {
  position: absolute;
  top: 80px;
  right: 20px;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1;
  color: #333;
  border-left: 4px solid #088;
}

/* Cursor tooltip for bbox mode */
.cursor-tooltip {
  position: fixed;
  background: rgba(0, 136, 136, 0.9);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  z-index: 10000;
  pointer-events: none;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Time Slider */
.time-slider-container {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.95);
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  min-width: 700px;
  backdrop-filter: blur(10px);
}

.time-slider-header {
  text-align: center;
  margin-bottom: 12px;
}

.time-slider-title {
  font-weight: 700;
  font-size: 16px;
  color: #ff6b35;
}

.time-slider-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.month-nav-btn {
  background: #088;
  color: white;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  flex-shrink: 0;
}

.month-nav-btn:hover:not(:disabled) {
  background: #0aa;
  transform: scale(1.1);
}

.month-nav-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.5;
}

.month-slider {
  display: flex;
  gap: 8px;
  flex: 1;
  justify-content: space-between;
}

.month-notch {
  flex: 1;
  height: 40px;
  background: #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 2px solid transparent;
}

.month-notch:hover {
  background: #c0c0c0;
  transform: translateY(-2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.month-notch.active {
  background: linear-gradient(135deg, #ff6b35, #ff8c42);
  border-color: #ff6b35;
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(255, 107, 53, 0.4);
}

.month-label {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  user-select: none;
}

.month-notch.active .month-label {
  color: white;
  font-size: 12px;
}
</style>

