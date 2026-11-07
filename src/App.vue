<script setup>
import { onMounted, onUnmounted } from 'vue'
import TopNav from './components/TopNav.vue'
import SiteFooter from './components/SiteFooter.vue'
import BackTop from './components/BackTop.vue'
import AuthDialog from './components/AuthDialog.vue'
import { useAuthStore } from './stores/auth.js'
import { useUiStore } from './stores/ui.js'

const auth = useAuthStore()
const ui = useUiStore()

let timer = null

onMounted(() => {
  auth.ensureFresh()
  // 每分钟检查一次会话是否过期：超时自动登出，不用等用户点
  timer = setInterval(() => auth.ensureFresh(), 60 * 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <TopNav />
  <main class="app-main">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
  <SiteFooter />
  <BackTop />
  <AuthDialog />

  <transition name="toast">
    <div v-if="ui.message" class="toast">{{ ui.message }}</div>
  </transition>
</template>

<style>
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.fade-leave-to {
  opacity: 0;
}

.toast {
  position: fixed;
  left: 50%;
  bottom: 40px;
  transform: translateX(-50%);
  z-index: 7000;
  background: rgba(24, 34, 26, 0.92);
  color: #fff;
  font-size: 0.8rem;
  padding: 9px 18px;
  border-radius: 999px;
  box-shadow: 0 8px 24px rgba(20, 30, 24, 0.28);
  pointer-events: none;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}
</style>
