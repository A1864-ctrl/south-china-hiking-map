<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

/**
 * 返回顶部：滚过一屏后浮出，带一圈阅读进度环。
 * 全局挂在 App.vue，所有页面都有。
 */
const SHOW_AFTER = 520

const y = ref(0)
const total = ref(1)
const show = ref(false)

const percent = computed(() => Math.min(1, Math.max(0, y.value / Math.max(1, total.value))))
const dash = computed(() => `${(percent.value * 132).toFixed(1)} 132`)

function onScroll() {
  const doc = document.documentElement
  y.value = window.scrollY || doc.scrollTop || 0
  total.value = Math.max(1, (doc.scrollHeight || 0) - window.innerHeight)
  show.value = y.value > SHOW_AFTER
}

function toTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll, { passive: true })
  onScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
})
</script>

<template>
  <transition name="bt">
    <button v-if="show" class="back-top" type="button" title="返回顶部" @click="toTop">
      <svg class="ring" viewBox="0 0 48 48" aria-hidden="true">
        <circle cx="24" cy="24" r="21" fill="none" stroke="rgba(45,90,61,0.14)" stroke-width="2.4" />
        <circle
          cx="24"
          cy="24"
          r="21"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          :stroke-dasharray="dash"
          transform="rotate(-90 24 24)"
        />
      </svg>
      <svg class="arrow" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path d="M12 19V6M6 12l6-6 6 6" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <em>{{ Math.round(percent * 100) }}%</em>
    </button>
  </transition>
</template>

<style scoped>
.back-top {
  position: fixed;
  right: 10px;
  top: calc(var(--nav-h) + 104px);
  z-index: 900;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.96);
  color: var(--forest);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(30, 61, 41, 0.18);
  border: 1px solid rgba(45, 90, 61, 0.12);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.back-top:hover {
  transform: translateY(-2px);
  background: #fff;
  box-shadow: 0 10px 26px rgba(30, 61, 41, 0.24);
}

.back-top:hover em {
  opacity: 0;
}

.ring {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.arrow {
  position: relative;
  transition: transform 0.18s ease;
}

.back-top:hover .arrow {
  transform: translateY(-1px);
}

.back-top em {
  position: absolute;
  bottom: 7px;
  left: 0;
  right: 0;
  font-style: normal;
  font-size: 0.5rem;
  letter-spacing: 0.02em;
  color: var(--gray);
  opacity: 0.9;
  transition: opacity 0.16s ease;
}

.bt-enter-active,
.bt-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.bt-enter-from,
.bt-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.94);
}

@media (max-width: 760px) {
  .back-top {
    right: 8px;
    top: calc(var(--nav-h) + 96px);
    width: 42px;
    height: 42px;
  }
  .back-top em {
    display: none;
  }
}
</style>
