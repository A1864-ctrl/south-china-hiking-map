<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  index: { type: Number, default: 0 },
  open: { type: Boolean, default: false }
})
const emit = defineEmits(['close', 'update:index'])

const cur = computed(() => props.images[props.index] || null)

function close() {
  emit('close')
}
function step(d) {
  const n = props.images.length
  if (n < 2) return
  emit('update:index', (props.index + d + n) % n)
}

function onKey(e) {
  if (!props.open) return
  if (e.key === 'Escape') close()
  else if (e.key === 'ArrowRight') step(1)
  else if (e.key === 'ArrowLeft') step(-1)
}

// 触屏左右滑
let tx = 0
function onTouchStart(e) {
  tx = e.changedTouches[0].clientX
}
function onTouchEnd(e) {
  const dx = e.changedTouches[0].clientX - tx
  if (Math.abs(dx) > 46) step(dx < 0 ? 1 : -1)
}

watch(
  () => props.open,
  (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
    if (v) window.addEventListener('keydown', onKey)
    else window.removeEventListener('keydown', onKey)
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
      <transition name="lb">
      <div
        v-if="open && cur"
        class="lb"
        @click.self="close"
        @touchstart.passive="onTouchStart"
        @touchend.passive="onTouchEnd"
      >
        <div class="lb-top">
          <span class="counter">{{ index + 1 }} / {{ images.length }}</span>
          <button class="x" aria-label="关闭" @click="close">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" />
            </svg>
          </button>
        </div>

        <img class="pic" :src="cur.src" :alt="cur.title || ''" @click.stop />

        <template v-if="images.length > 1">
          <button class="nav prev" aria-label="上一张" @click.stop="step(-1)">
            <svg viewBox="0 0 24 24" width="24" height="24">
              <path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <button class="nav next" aria-label="下一张" @click.stop="step(1)">
            <svg viewBox="0 0 24 24" width="24" height="24">
              <path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </template>

        <div class="lb-bottom">
          <p v-if="cur.title" class="cap">{{ cur.title }}</p>
          <p v-if="cur.caption" class="sub">{{ cur.caption }}</p>
          <div class="acts">
            <slot name="actions" :image="cur" />
            <span class="hint">← → 翻页 · Esc 关闭 · 手机左右滑</span>
          </div>
        </div>
      </div>
    </transition>
</template>

<style scoped>
.lb {
  position: fixed;
  top: 0;
  left: 0;
  inset: 0;
  z-index: 5000;
  background: rgba(8, 12, 9, 0.94);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56px 68px;
  touch-action: pan-y;
}

.pic {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 6px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  cursor: default;
}

.lb-top {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
}

.counter {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.82);
  font-variant-numeric: tabular-nums;
}

.x {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #24352a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.x:hover {
  background: #fff;
}

.nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.nav:hover {
  background: rgba(255, 255, 255, 0.32);
}

.nav.prev {
  left: 16px;
}

.nav.next {
  right: 16px;
}

.lb-bottom {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 14px 22px 18px;
  text-align: center;
  color: #fff;
}

.cap {
  font-size: 0.88rem;
  font-weight: 600;
}

.sub {
  margin-top: 3px;
  font-size: 0.74rem;
  color: rgba(255, 255, 255, 0.7);
}

.acts {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hint {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.45);
}

.lb-enter-active,
.lb-leave-active {
  transition: opacity 0.18s ease;
}

.lb-enter-from,
.lb-leave-to {
  opacity: 0;
}

@media (max-width: 680px) {
  .lb {
    padding: 52px 8px 96px;
  }
  .nav {
    width: 38px;
    height: 38px;
  }
  .nav.prev {
    left: 6px;
  }
  .nav.next {
    right: 6px;
  }
}
</style>
