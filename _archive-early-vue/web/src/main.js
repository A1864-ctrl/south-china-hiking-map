import { createApp } from 'vue'
import 'leaflet/dist/leaflet.css'
import App from './App.vue'
import router from './router.js'
import './style.css'

createApp(App).use(router).mount('#app')
