<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import { wgs84ToGcj02 } from '../data/geo.js'

const props = defineProps({
  points: { type: Array, default: () => [] },
  track: { type: Array, default: () => [] },
  waypoints: { type: Array, default: () => [] },
  center: { type: Array, default: () => [23.8, 112.6] },
  zoom: { type: Number, default: 7 },
  color: { type: String, default: '#2d5a3d' },
  height: { type: String, default: '420px' },
  fitTrack: { type: Boolean, default: true },
  label: { type: String, default: '' }
})

const el = ref(null)
const emit = defineEmits(['pin-click'])

// 两套底图：高德矢量（GCJ-02 偏移坐标）与天地图影像（WGS84/CGCS2000 无偏移）
const TDK = '01a165dff03ee02cc289d9958aa93768'
const base = ref('amap')          // 'amap' | 'tdt'
const tdtError = ref(false)
let map = null
let markerLayer = null
let trackLayer = null
let tileAmap = null
const markerMap = new Map()
let tileTdt = null
let tileTdtLabel = null

/** 坐标基准随底图切换：高德要纠偏到 GCJ-02，天地图本身就是 WGS84 */
const toLL = ([lat, lng]) => (base.value === 'tdt' ? [lat, lng] : wgs84ToGcj02(lat, lng))

function initMap() {
  if (!el.value) return
  const c = toLL(props.center)
  map = L.map(el.value, {
    center: c,
    zoom: props.zoom,
    zoomControl: true,
    attributionControl: true,
    scrollWheelZoom: true,
    wheelDebounceTime: 30,
    zoomSnap: 0.5,
    maxZoom: 19
  })

  tileAmap = L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    {
      subdomains: '1234',
      maxNativeZoom: 18,
      maxZoom: 19,
      attribution: '© 高德地图 · 矢量'
    }
  )

  const wmts = (layerName) =>
    'https://t{s}.tianditu.gov.cn/' + layerName + '_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0' +
    '&LAYER=' + layerName + '&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles' +
    '&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=' + TDK

  tileTdt = L.tileLayer(wmts('img'), {
    subdomains: '01234567',
    maxNativeZoom: 18,
    maxZoom: 19,
    attribution: '© 天地图 · 影像'
  })
  tileTdtLabel = L.tileLayer(wmts('cia'), {
    subdomains: '01234567',
    maxNativeZoom: 18,
    maxZoom: 19,
    opacity: 0.9
  })
  tileTdt.on('tileerror', () => {
    tdtError.value = true
  })

  // 按当前基准挂第一层底图
  if (base.value === 'tdt') {
    tileTdt.addTo(map)
    tileTdtLabel.addTo(map)
  } else {
    tileAmap.addTo(map)
  }

  L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map)

  markerLayer = L.layerGroup().addTo(map)
  trackLayer = L.layerGroup().addTo(map)

  drawPins()
  drawTrack()
  // 容器尺寸变化（折叠、切页）后修正
  setTimeout(() => map && map.invalidateSize(), 200)
}

function switchLayer(name) {
  if (!map || base.value === name) return
  base.value = name
  tdtError.value = false
  if (name === 'tdt') {
    map.removeLayer(tileAmap)
    tileTdt.addTo(map)
    tileTdtLabel.addTo(map)
  } else {
    map.removeLayer(tileTdt)
    map.removeLayer(tileTdtLabel)
    tileAmap.addTo(map)
  }
  // 基准换了，点位和轨迹必须按新基准重画
  drawPins()
  drawTrack()
}

function drawPins() {
  if (!map || !markerLayer) return
  markerLayer.clearLayers()
  markerMap.clear()
  props.points.forEach((p) => {
    const [lat, lng] = toLL([p.lat, p.lng])
    const color = p.color || props.color
    const icon = L.divIcon({
      className: '',
      html: `<span class="map-pin" style="background:${color}"></span>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    })
    const m = L.marker([lat, lng], { icon, title: p.name })
    if (p.name) {
      m.bindPopup(
        `<strong>${p.name}</strong>${p.sub ? `<br/><span style="color:#6b7280">${p.sub}</span>` : ''}`
      )
    }
    if (p.id != null) {
      m.on('click', () => emit('pin-click', p.id))
      markerMap.set(p.id, m)
    }
    m.addTo(markerLayer)
  })
}

function drawTrack() {
  if (!map || !trackLayer) return
  trackLayer.clearLayers()
  if (!props.track.length) return

  const path = props.track.map(toLL)
  L.polyline(path, { color: '#ffffff', weight: 8, opacity: 0.85, lineCap: 'round' }).addTo(trackLayer)
  L.polyline(path, { color: props.color, weight: 4.5, opacity: 0.96, lineCap: 'round' }).addTo(trackLayer)

  props.waypoints.forEach((w, i) => {
    const [lat, lng] = toLL([w.lat, w.lng])
    const cls = i === 0 ? 'start' : i === props.waypoints.length - 1 ? 'end' : ''
    const icon = L.divIcon({
      className: '',
      html: `<span class="wp-marker ${cls}">${i + 1}</span>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    })
    const extra = [w.ele ? `海拔 ${w.ele}m` : '', w.note || ''].filter(Boolean).join('<br/>')
    L.marker([lat, lng], { icon })
      .bindPopup(
        `<strong>${i + 1}. ${w.name}</strong><br/><span style="color:#6b7280">约 ${w.km} km 处</span>${
          extra ? `<br/><span style="color:#374151">${extra}</span>` : ''
        }`
      )
      .addTo(trackLayer)
  })

  if (props.fitTrack) {
    const bounds = L.latLngBounds(path)
    map.fitBounds(bounds, { padding: [34, 34], maxZoom: 15 })
  }
}

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})

watch(() => props.points, drawPins, { deep: true })
watch(
  () => props.center,
  (c) => {
    if (map && !props.track.length && c && c.length === 2) {
      map.invalidateSize()
      map.setView(toLL(c), props.zoom, { animate: true })
    }
  }
)
watch(
  () => props.zoom,
  (z) => {
    if (map && !props.track.length) map.setZoom(z)
  }
)
watch(() => props.track, drawTrack, { deep: true })
watch(
  () => props.waypoints,
  () => drawTrack(),
  { deep: true }
)

defineExpose({
  focus(lat, lng, zoom = 12) {
    if (!map) return
    map.flyTo(toLL([lat, lng]), zoom, { duration: 0.8 })
  },
  fitBounds(points) {
    if (!map || !points.length) return
    map.fitBounds(L.latLngBounds(points.map(toLL)), { padding: [40, 40], maxZoom: 13 })
  },
  /** 定位到某个点位并弹出气泡（列表点卡片时用） */
  focusPoint(id, zoom = 11) {
    if (!map) return
    const m = markerMap.get(id)
    if (!m) return
    map.flyTo(m.getLatLng(), zoom, { duration: 0.7 })
    setTimeout(() => m.openPopup(), 620)
  }
})
</script>

<template>
  <div class="map-wrap" :style="{ height }">
    <div ref="el" class="map-el"></div>
    <div class="map-tools">
      <button :class="{ on: base === 'amap' }" @click="switchLayer('amap')" title="高德矢量地图">
        高德矢量
      </button>
      <button :class="{ on: base === 'tdt' }" @click="switchLayer('tdt')" title="天地图卫星影像">
        天地卫星
      </button>
    </div>
    <p v-if="tdtError" class="map-err">天地图影像未加载：Key 可能未授权当前域名（{{
      typeof window !== 'undefined' ? window.location.host : ''
    }}），请到天地图控制台把该域名加入白名单</p>
    <div v-if="label" class="map-label">{{ label }}</div>
    <div class="map-hint">滚轮直接缩放 · 双击放大</div>
  </div>
</template>

<style scoped>
.map-wrap {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: #e8eef0;
}

.map-el {
  width: 100%;
  height: 100%;
}

.map-tools {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 600;
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.94);
  padding: 3px;
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.map-tools button {
  border: none;
  background: transparent;
  font-size: 0.72rem;
  padding: 5px 10px;
  border-radius: 6px;
  color: var(--ink-soft);
  cursor: pointer;
}

.map-tools button.on {
  background: var(--forest);
  color: #fff;
}

.map-err {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 44px;
  z-index: 600;
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.5;
  color: #7a2e2e;
  background: rgba(255, 244, 240, 0.95);
  border: 1px solid rgba(180, 90, 70, 0.3);
  border-radius: 8px;
  padding: 7px 10px;
}

.map-err {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 44px;
  z-index: 600;
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.5;
  color: #7a2e2e;
  background: rgba(255, 244, 240, 0.95);
  border: 1px solid rgba(180, 90, 70, 0.3);
  border-radius: 8px;
  padding: 7px 10px;
}

.map-hint {
  position: absolute;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  z-index: 500;
  font-size: 0.68rem;
  color: #fff;
  background: rgba(30, 45, 36, 0.62);
  padding: 3px 10px;
  border-radius: 20px;
  pointer-events: none;
  white-space: nowrap;
}

.map-label {
  position: absolute;
  top: 12px;
  left: 52px;
  z-index: 500;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--forest-dark);
  box-shadow: var(--shadow-sm);
  pointer-events: none;
}
</style>
