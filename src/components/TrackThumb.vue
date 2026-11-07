<script setup>
import { computed } from 'vue'

const props = defineProps({
  track: { type: Array, default: () => [] },
  color: { type: String, default: '#2d5a3d' },
  w: { type: Number, default: 120 },
  h: { type: Number, default: 78 },
  strokeWidth: { type: Number, default: 2 }
})

const path = computed(() => {
  const t = props.track
  if (!t || t.length < 2) return ''
  let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity
  for (const [la, ln] of t) {
    if (la < minLat) minLat = la
    if (la > maxLat) maxLat = la
    if (ln < minLng) minLng = ln
    if (ln > maxLng) maxLng = ln
  }
  const pad = 8
  const dLat = maxLat - minLat || 1e-6
  const dLng = maxLng - minLng || 1e-6
  const scale = Math.min((props.w - pad * 2) / dLng, (props.h - pad * 2) / dLat)
  const ox = (props.w - dLng * scale) / 2
  const oy = (props.h - dLat * scale) / 2
  return t
    .map(([la, ln], i) => {
      const x = ox + (ln - minLng) * scale
      const y = props.h - (oy + (la - minLat) * scale)
      return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
})

const start = computed(() => {
  const p = path.value.split(' ')
  return p.length > 1 ? p[0] : ''
})
</script>

<template>
  <svg v-if="path" class="track" :viewBox="`0 0 ${w} ${h}`" :width="w" :height="h" aria-hidden="true">
    <path :d="path" fill="none" stroke="#ffffff" stroke-width="4.5" stroke-linejoin="round" opacity="0.85" />
    <path :d="path" fill="none" :stroke="color" :stroke-width="strokeWidth" stroke-linejoin="round" />
  </svg>
</template>

<style scoped>
.track {
  display: block;
  overflow: visible;
}
</style>
