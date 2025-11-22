<script setup lang="ts">
import FireSimulator from './components/FireSimulator.vue'
</script>

<template>
  <div class="app">
    <FireSimulator />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}
</style>
