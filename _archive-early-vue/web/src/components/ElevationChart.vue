<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  profile: { type: Array, required: true },
  distance: { type: Number, default: 0 },
  color: { type: String, default: '#2d5a3d' }
})

const uid = 'ele' + Math.random().toString(36).slice(2, 8)
const hover = ref(null)
const W = 800
const H = 170
const PAD_L = 44
const PAD_R = 12
const PAD_T = 16
const PAD_B = 24

const minMax = computed(() => {
  const min = Math.min(...props.profile)
  const max = Math.max(...props.profile)
  return { min, max }
})

const pts = computed(() => {
  const { min, max } = minMax.value
  const span = Math.max(1, max - min)
  const n = props.profile.length - 1
  return props.profile.map((v, i) => {
    const x = PAD_L + ((W - PAD_L - PAD_R) * i) / n
    const y = PAD_T + (H - PAD_T - PAD_B) * (1 - (v - min) / span)
    return [x, y]
  })
})

const linePath = computed(() => {
  const p = pts.value
  if (!p.length) return ''
  let d = `M${p[0][0]},${p[0][1]}`
  for (let i = 1; i < p.length; i++) {
    const [px, py] = p[i - 1]
    const [cx, cy] = p[i]
    const mx = (px + cx) / 2
    d += ` Q${px},${py} ${mx},${(py + cy) / 2}`
  }
  const last = p[p.length - 1]
  d += ` L${last[0]},${last[1]}`
  return d
})

const areaPath = computed(() => {
  const p = pts.value
  if (!p.length) return ''
  return `${linePath.value} L${p[p.length - 1][0]},${H - PAD_B} L${p[0][0]},${H - PAD_B} Z`
})

const gridLines = computed(() => {
  const { min, max } = minMax.value
  return [0, 0.5, 1].map((t) => ({
    y: PAD_T + (H - PAD_T - PAD_B) * t,
    label: Math.round(max - (max - min) * t)
  }))
})

function onMove(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * W
  const ratio = (x - PAD_L) / (W - PAD_L - PAD_R)
  if (ratio < -0.02 || ratio > 1.02) {
    hover.value = null
    return
  }
  const idx = Math.max(0, Math.min(props.profile.length - 1, Math.round(ratio * (props.profile.length - 1))))
  const [hx, hy] = pts.value[idx]
  hover.value = {
    x: hx,
    y: hy,
    ele: props.profile[idx],
    km: +((props.distance * idx) / (props.profile.length - 1)).toFixed(1)
  }
}
</script>

<template>
  <div class="ele">
    <div class="ele-head">
      <span class="ele-title">高程剖面</span>
      <span class="ele-meta mono">
        {{ minMax.min }}m – {{ minMax.max }}m · 全程 {{ distance }}km
      </span>
    </div>
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      preserveAspectRatio="none"
      class="ele-svg"
      @mousemove="onMove"
      @mouseleave="hover = null"
    >
      <defs>
        <linearGradient :id="uid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="color" stop-opacity="0.28" />
          <stop offset="100%" :stop-color="color" stop-opacity="0.02" />
        </linearGradient>
      </defs>

      <g>
        <line
          v-for="(g, i) in gridLines"
          :key="i"
          :x1="PAD_L"
          :x2="W - PAD_R"
          :y1="g.y"
          :y2="g.y"
          stroke="#e6e1d6"
          stroke-width="1"
          stroke-dasharray="3 4"
        />
        <text
          v-for="(g, i) in gridLines"
          :key="'t' + i"
          :x="PAD_L - 8"
          :y="g.y + 4"
          text-anchor="end"
          font-size="10"
          fill="#9ca3af"
        >
          {{ g.label }}
        </text>
      </g>

      <path :d="areaPath" :fill="`url(#${uid})`" />
      <path
        :d="linePath"
        fill="none"
        :stroke="color"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <text :x="PAD_L" :y="H - 6" font-size="10" fill="#9ca3af">0 km</text>
      <text :x="W - PAD_R" :y="H - 6" font-size="10" fill="#9ca3af" text-anchor="end">
        {{ distance }} km
      </text>

      <g v-if="hover">
        <line
          :x1="hover.x"
          :x2="hover.x"
          :y1="PAD_T"
          :y2="H - PAD_B"
          :stroke="color"
          stroke-width="1"
          stroke-dasharray="3 3"
          opacity="0.6"
        />
        <circle :cx="hover.x" :cy="hover.y" r="4.5" fill="#fff" :stroke="color" stroke-width="2.5" />
      </g>
    </svg>
    <div v-if="hover" class="ele-tip mono">
      {{ hover.km }} km · {{ hover.ele }} m
    </div>
  </div>
</template>

<style scoped>
.ele {
  position: relative;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px 6px;
}

.ele-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 4px;
}

.ele-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--forest-dark);
}

.ele-meta {
  font-size: 0.72rem;
  color: var(--gray);
}

.ele-svg {
  width: 100%;
  height: 132px;
  display: block;
  overflow: visible;
}

.ele-tip {
  position: absolute;
  top: 10px;
  right: 14px;
  background: var(--forest-dark);
  color: #fff;
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 6px;
}
</style>
