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
  frp?: number  // Fire Radiative Power (MW)
  brightness?: number
  bright_t31?: number
  instrument?: string  // MODIS or VIIRS
  satellite?: string
  version?: string
  daynight?: string  // D or N
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
}

export interface NO2Measurement {
  id: number
  latitude: number
  longitude: number
  measurement_date: string
  no2_column?: number  // Tropospheric NO2 column density (molecules/cm²)
  qa_value?: number    // Quality assurance (0-1)
  cloud_fraction?: number  // Cloud fraction (0-1)
  grid_lat_idx?: number
  grid_lon_idx?: number
}

export interface NO2Response {
  data: NO2Measurement[]
  count: number
  status: string
  error?: string
  message?: string
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

  async getFires(): Promise<FiresResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/fires`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching fire data:', error)
      throw error
    }
  },

  async getNO2(params?: { limit?: number; date_from?: string; date_to?: string; min_qa?: number }): Promise<NO2Response> {
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
}
