const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api'

export interface ApiResponse {
  message: string
  status: string
  database_connected?: boolean
  error?: string
}

export interface HealthResponse {
  status: string
  database_connected: boolean
}

export interface FireDetection {
  id: number
  latitude: number
  longitude: number
  acq_date: string
  acq_time?: string
  confidence?: string
  frp?: number // Fire Radiative Power (MW)
  brightness?: number
  bright_t31?: number
  instrument?: string // MODIS or VIIRS
  satellite?: string
  version?: string
  daynight?: string // D or N
  type?: string
  scan?: number
  track?: number
}

export interface FiresResponse {
  data: FireDetection[]
  count: number
  status: string
  error?: string
  message?: string
  source?: string
  bbox?: {
    min_lat: number
    max_lat: number
    min_lon: number
    max_lon: number
  }
}

export interface NO2Measurement {
  id: number
  latitude: number
  longitude: number
  measurement_date: string
  no2_column?: number // Tropospheric NO2 column density (molecules/cm²)
  qa_value?: number // Quality assurance (0-1)
  cloud_fraction?: number // Cloud fraction (0-1)
  grid_lat_idx?: number
  grid_lon_idx?: number
  value: number
  unit: string
}

export interface NO2Response {
  data: NO2Measurement[]
  count: number
  status: string
  error?: string
}

export interface WeatherData {
  wind_speed: number
  wind_deg: number
  temp: number
  humidity: number
  rain?: number
}

export interface WeatherResponse {
  status: string
  data: WeatherData
  error?: string
}

export interface PollutionData {
  dt: number
  main: {
    aqi: number
  }
  components: {
    co: number
    no: number
    no2: number
    o3: number
    so2: number
    pm2_5: number
    pm10: number
    nh3: number
  }
}

export interface PollutionResponse {
  status: string
  data: PollutionData[]
  error?: string
  is_mock?: boolean
}

export const apiService = {
  async getHello(): Promise<ApiResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/hello`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching hello message:', error)
      throw error
    }
  },

  async getHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching health status:', error)
      throw error
    }
  },

  async getFires(params?: {
    limit?: number
    date_from?: string
    date_to?: string
  }): Promise<FiresResponse> {
    try {
      const queryParams = new URLSearchParams()
      if (params?.limit) queryParams.append('limit', params.limit.toString())
      if (params?.date_from) queryParams.append('date_from', params.date_from)
      if (params?.date_to) queryParams.append('date_to', params.date_to)

      const url = `${API_BASE_URL}/fires${queryParams.toString() ? '?' + queryParams.toString() : ''}`
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching fire data:', error)
      throw error
    }
  },

  async getFiresRange(): Promise<{
    min_date: string | null
    max_date: string | null
    status: string
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/fires/range`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching fires date range:', error)
      throw error
    }
  },

  async getFiresAthena(params: {
    min_lat: number
    max_lat: number
    min_lon: number
    max_lon: number
    limit?: number
    start_date?: string
    end_date?: string
  }): Promise<FiresResponse> {
    try {
      const queryParams = new URLSearchParams()
      queryParams.append('min_lat', params.min_lat.toString())
      queryParams.append('max_lat', params.max_lat.toString())
      queryParams.append('min_lon', params.min_lon.toString())
      queryParams.append('max_lon', params.max_lon.toString())
      if (params?.limit) queryParams.append('limit', params.limit.toString())
      if (params?.start_date) queryParams.append('start_date', params.start_date)
      if (params?.end_date) queryParams.append('end_date', params.end_date)

      const url = `${API_BASE_URL}/fires/athena?${queryParams.toString()}`
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching fire data from Athena:', error)
      throw error
    }
  },

  async getNO2(params?: {
    limit?: number
    date_from?: string
    date_to?: string
    min_qa?: number
  }): Promise<NO2Response> {
    try {
      const queryParams = new URLSearchParams()
      if (params?.limit) queryParams.append('limit', params.limit.toString())
      if (params?.date_from) queryParams.append('date_from', params.date_from)
      if (params?.date_to) queryParams.append('date_to', params.date_to)
      if (params?.min_qa) queryParams.append('min_qa', params.min_qa.toString())

      const url = `${API_BASE_URL}/no2${queryParams.toString() ? '?' + queryParams.toString() : ''}`
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching NO2 data:', error)
      throw error
    }
  },

  async getWeather(lat: number, lon: number, date?: number): Promise<WeatherResponse> {
    try {
      let url = `${API_BASE_URL}/weather?lat=${lat}&lon=${lon}`
      if (date) {
        url += `&date=${date}`
      }
      const response = await fetch(url)
      return await response.json()
    } catch (error) {
      console.error('Error fetching weather:', error)
      return { status: 'error', error: String(error), data: { wind_speed: 0, wind_deg: 0, temp: 0, humidity: 0, rain: 0 } }
    }
  },

  async getPollution(lat: number, lon: number, date?: number): Promise<PollutionResponse> {
    try {
      const url = new URL(`${API_BASE_URL}/pollution`)
      url.searchParams.append('lat', lat.toString())
      url.searchParams.append('lon', lon.toString())
      if (date) {
        url.searchParams.append('date', date.toString())
      }
      
      const response = await fetch(url.toString())
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching pollution data:', error)
      throw error
    }
  },
}
