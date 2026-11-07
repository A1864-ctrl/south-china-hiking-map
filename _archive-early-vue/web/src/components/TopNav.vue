<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { overview } from '../data/cities.js'

const route = useRoute()

const navs = [
  { name: 'home', to: '/', label: '项目说明', icon: '◎' },
  { name: 'spots', to: '/spots', label: '景点搜索', icon: '◉' },
  { name: 'routes', to: '/routes', label: '徒步轨迹', icon: '⌁' },
  { name: 'heat', to: '/heat', label: '城市热度', icon: '▲' }
]

const current = computed(() => route.name)
</script>

<template>
  <header class="topnav">
    <div class="nav-inner">
      <router-link to="/" class="brand">
        <span class="brand-mark">⛰</span>
        <span class="brand-text">
          <strong>华南徒步地图</strong>
          <em>探索山野 · 徒步中国</em>
        </span>
      </router-link>

      <nav class="nav-links">
        <router-link
          v-for="n in navs"
          :key="n.name"
          :to="n.to"
          class="nav-link"
          :class="{ active: current === n.name }"
        >
          <span class="nav-icon">{{ n.icon }}</span>
          {{ n.label }}
        </router-link>
      </nav>

      <div class="nav-side">
        <span class="nav-stat">
          <b class="mono">{{ overview.spotCount }}</b> 景点
          <i></i>
          <b class="mono">{{ overview.routeCount }}</b> 路线
        </span>
        <router-link to="/routes" class="nav-cta">开始找路线 →</router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: var(--nav-h);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--line);
}

.nav-inner {
  max-width: 1320px;
  height: 100%;
  margin: 0 auto;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 36px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(145deg, var(--forest-light), var(--forest-dark));
  color: #fff;
  font-size: 19px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(45, 90, 61, 0.28);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand-text strong {
  font-size: 1rem;
  color: var(--forest-dark);
  letter-spacing: 0.02em;
}

.brand-text em {
  font-style: normal;
  font-size: 0.7rem;
  color: var(--gray-light);
  letter-spacing: 0.12em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-links::-webkit-scrollbar {
  display: none;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 16px;
  border-radius: 9px;
  font-size: 0.94rem;
  font-weight: 500;
  color: var(--ink-soft);
  white-space: nowrap;
  transition: all 0.18s ease;
}

.nav-link:hover {
  background: var(--forest-soft);
  color: var(--forest);
}

.nav-link.active {
  background: var(--forest);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(45, 90, 61, 0.24);
}

.nav-icon {
  font-size: 0.72rem;
  opacity: 0.75;
}

.nav-side {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}

.nav-stat {
  font-size: 0.78rem;
  color: var(--gray);
  display: flex;
  align-items: center;
  gap: 5px;
}

.nav-stat b {
  color: var(--forest);
}

.nav-stat i {
  width: 1px;
  height: 11px;
  background: var(--line);
  margin: 0 4px;
}

.nav-cta {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--forest);
  border: 1.5px solid var(--forest);
  padding: 7px 15px;
  border-radius: 999px;
  transition: all 0.18s ease;
}

.nav-cta:hover {
  background: var(--forest);
  color: #fff;
}

@media (max-width: 1100px) {
  .nav-side {
    display: none;
  }
}

@media (max-width: 760px) {
  .nav-inner {
    padding: 0 14px;
    gap: 12px;
  }

  .brand-text em {
    display: none;
  }

  .brand-text strong {
    font-size: 0.9rem;
  }

  .nav-link {
    padding: 7px 11px;
    font-size: 0.85rem;
  }

  .nav-icon {
    display: none;
  }
}

@media (max-width: 480px) {
  .nav-inner {
    padding: 0 10px;
    gap: 8px;
  }

  .brand-text {
    display: none;
  }

  .nav-link {
    padding: 6px 9px;
    font-size: 0.8rem;
  }
}
</style>
