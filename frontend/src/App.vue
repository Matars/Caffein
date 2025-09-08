<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiService, type ApiResponse, type HealthResponse } from './services/api'

const message = ref<string>('Loading...')
const health = ref<HealthResponse | null>(null)
const error = ref<string | null>(null)
const loading = ref<boolean>(true)

const fetchData = async () => {
  try {
    loading.value = true
    error.value = null

    // Fetch hello message
    const helloResponse: ApiResponse = await apiService.getHello()
    message.value = helloResponse.message

    // Fetch health status
    const healthResponse: HealthResponse = await apiService.getHealth()
    health.value = healthResponse
  } catch (err) {
    console.error('Error fetching data:', err)
    error.value = err instanceof Error ? err.message : 'Unknown error occurred'
    message.value = 'Failed to connect to backend'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="app">
    <header>
      <h1>Full-Stack Vue + Flask + MongoDB Project</h1>
    </header>

    <main>
      <div class="card">
        <h2>Backend Message</h2>
        <div v-if="loading" class="loading">Loading...</div>
        <div v-else-if="error" class="error">
          <p>Error: {{ error }}</p>
          <button @click="fetchData">Retry</button>
        </div>
        <div v-else class="message">
          <p>{{ message }}</p>
        </div>
      </div>

      <div class="card" v-if="health">
        <h2>System Status</h2>
        <div class="status">
          <p>
            Backend Status:
            <span :class="health.status === 'healthy' ? 'healthy' : 'unhealthy'">{{
              health.status
            }}</span>
          </p>
          <p>
            Database Connected:
            <span :class="health.database_connected ? 'connected' : 'disconnected'">{{
              health.database_connected ? 'Yes' : 'No'
            }}</span>
          </p>
        </div>
      </div>

      <div class="actions">
        <button @click="fetchData" :disabled="loading">Refresh Data</button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: Arial, sans-serif;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

h1 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.card {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.card h2 {
  color: #495057;
  margin-top: 0;
  margin-bottom: 1rem;
}

.loading {
  color: #6c757d;
  font-style: italic;
}

.error {
  color: #dc3545;
}

.error button {
  background: #dc3545;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 0.5rem;
}

.error button:hover {
  background: #c82333;
}

.message {
  color: #28a745;
  font-weight: 500;
}

.status p {
  margin: 0.5rem 0;
}

.healthy,
.connected {
  color: #28a745;
  font-weight: bold;
}

.unhealthy,
.disconnected {
  color: #dc3545;
  font-weight: bold;
}

.actions {
  text-align: center;
}

.actions button {
  background: #007bff;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.actions button:hover:not(:disabled) {
  background: #0056b3;
}

.actions button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}
</style>
