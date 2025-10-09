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

export interface Fire {
  Lat_DD: number
  Long_DD: number
  FireName: string
  FireYear: number
  EstTotalAcres: number
  HumanOrLightning: string
  FireCategory?: string
  Size_class?: string
  County?: string
}

export interface FiresResponse {
  data: Fire[]
  count: number
  status: string
  error?: string
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
}
