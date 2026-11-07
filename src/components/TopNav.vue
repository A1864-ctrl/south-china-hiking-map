<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { overview } from '../data/cities.js'
import { useAuthStore } from '../stores/auth.js'
import { useFavStore } from '../stores/fav.js'
import NavIcon from './NavIcon.vue'

const route = useRoute()
const auth = useAuthStore()
const fav = useFavStore()

const navs = [
  { name: 'home', to: '/', label: '项目说明', sub: '为什么做这个站', icon: 'home', tone: '#2d5a3d' },
  { name: 'spots', to: '/spots', label: '景点路书', sub: '四季 · 机位 · 吃什么', icon: 'spots', tone: '#1f7a5c' },
  { name: 'routes', to: '/routes', label: '徒步轨迹', sub: '分段路书 · 交通接驳', icon: 'routes', tone: '#a97a17' },
  { name: 'heat', to: '/heat', label: '城市热度', sub: '该去哪座城', icon: 'heat', tone: '#bf4a2f' },
  { name: 'gear', to: '/gear', label: '装备清单', sub: '74 项 · 按路线配', icon: 'gear', tone: '#2f6f9e' },
  { name: 'community', to: '/community', label: '山友社区', sub: '约伴 · 附近', icon: 'community', tone: '#8a6d2f' }
]

const current = computed(() => route.name)

/* 山野工具：放在右侧下拉里，避免挤压主导航 */
const tools = [
  { to: '/reports', name: 'reports', label: '路况上报', desc: '塌方 · 杂草 · 水源 · 蜂群', icon: '⛰' },
  { to: '/safety', name: 'safety', label: '安全报备', desc: '登记行程 · 平安打卡', icon: '🛡' },
  { to: '/camps', name: 'camps', label: '营地库', desc: '明火 · 水源 · 过夜权限', icon: '⛺' },
  { to: '/weather', name: 'weather', label: '点位天气', desc: '降水 · 风力 · 雷电预警', icon: '☁' },
  { to: '/gear-lab', name: 'gearLab', label: '我的装备库', desc: '分类盘点 · 智能清单', icon: '🎒' },
  { to: '/learn', name: 'learn', label: '山野知识库', desc: 'LNT · 山野急救', icon: '📖' }
]
const toolsActive = computed(() => tools.some((t) => t.name === current.value))
const toolsOpen = ref(false)
</script>

<template>
  <header class="nav">
    <div class="inner">
      <router-link to="/" class="brand" aria-label="回到首页">
        <span class="mark">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M2 19h20L14.5 6l-3.2 6-2.1-3.4L2 19z" fill="currentColor" />
            <circle cx="17.6" cy="6.6" r="1.9" fill="currentColor" opacity="0.7" />
          </svg>
        </span>
        <span class="brand-txt">
          <strong>野径 · 华南徒步图鉴</strong>
          <em>YEJING · SOUTH CHINA TRAILS</em>
        </span>
      </router-link>

      <nav class="tabs">
        <router-link
          v-for="n in navs"
          :key="n.name"
          :to="n.to"
          class="tab"
          :class="{ on: current === n.name }"
        >
          <span
            class="thumb"
            :style="{ color: n.tone, background: `${n.tone}14`, borderColor: current === n.name ? `${n.tone}40` : 'transparent' }"
          >
            <NavIcon :name="n.icon" />
          </span>
          <span class="txt">
            <b>{{ n.label }}</b>
            <em>{{ n.sub }}</em>
          </span>
        </router-link>
      </nav>

      <div class="side">
        <div class="toolbtn" @mouseenter="toolsOpen = true" @mouseleave="toolsOpen = false">
          <button class="tool-trigger" :class="{ on: toolsActive }" @click="toolsOpen = !toolsOpen">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none">
              <path d="M4 7.5h16M4 12h16M4 16.5h10" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
              <circle cx="18.5" cy="16.5" r="2.1" stroke="currentColor" stroke-width="1.6" />
            </svg>
            工具
            <i class="caret"></i>
          </button>
          <transition name="drop">
            <div v-if="toolsOpen" class="tool-panel">
              <p class="tp-head">山野工具 · FIELD KIT</p>
              <div class="tp-grid">
                <router-link v-for="t in tools" :key="t.to" :to="t.to" class="tp-item" @click="toolsOpen = false">
                  <span class="tp-icon">{{ t.icon }}</span>
                  <span class="tp-txt">
                    <b>{{ t.label }}</b>
                    <em>{{ t.desc }}</em>
                  </span>
                </router-link>
              </div>
            </div>
          </transition>
        </div>

        <span class="stat"><b>{{ overview.spotCount }}</b>点位<i></i><b>{{ overview.routeCount }}</b>路线</span>

        <router-link v-if="auth.isLogged" to="/me" class="me" title="我的收藏">
          <span class="avatar" :class="{ 'has-img': auth.avatarUrl }">
            <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="" />
            <template v-else>{{ auth.initial }}</template>
          </span>
          <span class="me-name">{{ auth.nickname }}</span>
          <em v-if="fav.total()" class="fav-badge">{{ fav.total() }}</em>
        </router-link>
        <button v-else class="login" @click="auth.openDialog('login')">登录</button>

        <router-link to="/routes" class="cta">找路线</router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.nav {
  position: fixed;
  inset: 0 0 auto 0;
  z-index: 1000;
  height: var(--nav-h);
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}

.inner {
  max-width: 1320px;
  height: 100%;
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  align-items: center;
  gap: 18px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-shrink: 0;
}

.mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--forest-dark);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-txt {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-txt strong {
  font-size: 0.94rem;
  color: var(--forest-dark);
  letter-spacing: 0.02em;
}

.brand-txt em {
  font-style: normal;
  font-size: 0.56rem;
  letter-spacing: 0.2em;
  color: var(--gray-light);
}

.tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.tabs::-webkit-scrollbar {
  display: none;
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 7px 5px 4px;
  border-radius: 10px;
  border: 1px solid transparent;
  flex-shrink: 0;
  transition: background 0.16s, box-shadow 0.16s;
}

.tab:hover {
  background: var(--cream);
}

.tab.on {
  background: #fff;
  border-color: var(--line);
  box-shadow: 0 2px 8px rgba(30, 61, 41, 0.07);
}

/* 图标块：底色用各版块的主色，悬停时图标做一个小动作 */
.thumb {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.22s ease, background 0.22s ease, border-color 0.22s ease;
}

.tab:hover .thumb {
  transform: translateY(-1px);
}

.tab:hover :deep(.ic-sun) {
  transform: translateY(-2.2px);
}

.tab:hover :deep(.ic-frame) {
  transform: rotate(-2.4deg) scale(1.04);
}

.tab:hover :deep(.ic-trail) {
  stroke-dashoffset: -24;
}

.tab:hover :deep(.ic-bar) {
  transform: scaleY(1.12);
}

.tab:hover :deep(.ic-bar.b2) {
  transition-delay: 0.06s;
}

.tab:hover :deep(.ic-bar.b3) {
  transition-delay: 0.12s;
}

.tab:hover :deep(.ic-pack) {
  transform: translateY(-1.6px);
}

.tab:hover :deep(.ic-layer.l2) {
  transform: translateY(-1.6px);
}

.tab:hover :deep(.ic-layer.l3) {
  transform: translateY(-3.2px);
}

/* 当前页的轨迹图标保持缓慢流动，暗示「在路上」 */
.tab.on :deep(.ic-trail) {
  animation: trail-flow 2.6s linear infinite;
}

@keyframes trail-flow {
  from {
    stroke-dashoffset: 0;
  }
  to {
    stroke-dashoffset: -24;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tab.on :deep(.ic-trail) {
    animation: none;
  }
  .thumb,
  .tab:hover :deep(svg *) {
    transition: none;
    transform: none;
  }
}

.txt {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.txt b {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--ink-soft);
}

.tab.on .txt b {
  color: var(--forest-dark);
}

.txt em {
  font-style: normal;
  font-size: 0.62rem;
  color: var(--gray-light);
  white-space: nowrap;
}

.side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  position: relative;
}

/* ── 山野工具下拉 ── */
.toolbtn {
  position: relative;
}
.tool-trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 0.76rem;
  color: var(--ink-soft);
  cursor: pointer;
  transition: 0.18s;
  white-space: nowrap;
}
.tool-trigger:hover,
.tool-trigger.on {
  border-color: var(--forest-light);
  color: var(--forest-dark);
  background: var(--forest-soft);
}
.caret {
  width: 0;
  height: 0;
  border-left: 3px solid transparent;
  border-right: 3px solid transparent;
  border-top: 4px solid currentColor;
  opacity: 0.5;
  margin-left: 1px;
}
.tool-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  width: 396px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 16px 40px rgba(30, 61, 41, 0.16);
  padding: 12px;
  z-index: 60;
}
.tp-head {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.54rem;
  letter-spacing: 0.16em;
  color: var(--gray-light);
  padding: 0 4px 8px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 8px;
}
.tp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.tp-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 8px;
  border-radius: 6px;
  text-decoration: none;
  transition: 0.16s;
}
.tp-item:hover {
  background: var(--cream);
}
.tp-icon {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--forest-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
}
.tp-txt {
  min-width: 0;
}
.tp-txt b {
  display: block;
  font-size: 0.76rem;
  color: var(--ink);
  font-weight: 600;
}
.tp-txt em {
  display: block;
  font-size: 0.58rem;
  font-style: normal;
  color: var(--gray);
  margin-top: 1px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.drop-enter-active,
.drop-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.stat {
  font-size: 0.72rem;
  color: var(--gray);
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--forest);
  font-size: 0.8rem;
}

.stat i {
  width: 1px;
  height: 10px;
  background: var(--line);
  margin: 0 3px;
}

.ver {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: var(--gray);
  padding: 6px 9px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #fcfbf7;
  white-space: nowrap;
}

.ver:hover {
  color: var(--forest-dark);
  border-color: var(--forest-light);
  background: #fff;
}

.ver :deep(svg) {
  width: 15px;
  height: 15px;
}

.me {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fcfbf7;
  position: relative;
}

.me:hover {
  border-color: var(--forest-light);
  background: #fff;
}

.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--forest);
  color: #fff;
  font-size: 0.76rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.me-name {
  font-size: 0.76rem;
  color: var(--forest-dark);
  max-width: 84px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #c0392b;
  color: #fff;
  font-style: normal;
  font-size: 0.6rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login {
  font-size: 0.76rem;
  color: var(--forest-dark);
  border: 1px solid rgba(45, 90, 61, 0.28);
  background: var(--forest-soft);
  padding: 7px 12px;
  border-radius: 8px;
  white-space: nowrap;
}

.login:hover {
  background: var(--forest);
  color: #fff;
  border-color: var(--forest);
}

.cta {
  font-size: 0.78rem;
  color: #fff;
  background: var(--forest);
  padding: 7px 14px;
  border-radius: 8px;
  white-space: nowrap;
}

.cta:hover {
  background: var(--forest-dark);
}

@media (max-width: 1560px) {
  .stat {
    display: none;
  }
}

/* 1240px 以下：导航整体收紧，避免 1092px 附近「装备清单」被挤出可视区 */
@media (max-width: 1240px) {
  .inner {
    gap: 14px;
    padding: 0 20px;
  }

  .tabs {
    gap: 2px;
  }

  .tab {
    gap: 6px;
    padding: 4px 7px 4px 4px;
  }

  .thumb {
    width: 30px;
    height: 30px;
    border-radius: 8px;
  }

  .txt b {
    font-size: 0.8rem;
  }

  .txt em {
    font-size: 0.56rem;
    letter-spacing: 0;
  }

  .ver {
    padding: 5px 8px;
  }

  .cta {
    padding: 7px 12px;
  }
}

/* 1320px 以下六个标签 + 副标题挤不下，副标题让位，只留主标签；
   主标签本身带 title，鼠标悬停仍能看到说明 */
@media (max-width: 1320px) {
  .tab {
    gap: 5px;
    padding: 6px 10px;
  }

  .txt em {
    display: none;
  }
}

/* 1180px 以下右侧「找路线」与导航里的「徒步轨迹」重复，先让位 */
@media (max-width: 1180px) {
  .cta {
    display: none;
  }
}

@media (max-width: 1180px) {
  .ver span {
    display: none;
  }
  .ver {
    padding: 6px;
  }
}

@media (max-width: 900px) {
  .me-name {
    display: none;
  }
}

@media (max-width: 760px) {
  .inner {
    padding: 0 12px;
    gap: 10px;
  }

  .brand-txt,
  .txt em,
  .cta {
    display: none;
  }

  .tab {
    padding: 5px;
    gap: 0;
  }

  .txt {
    display: none;
  }

  .tab.on {
    gap: 7px;
  }

  .tab.on .txt {
    display: flex;
    padding-right: 8px;
  }

  .txt b {
    font-size: 0.78rem;
  }

  .thumb {
    width: 30px;
    height: 30px;
  }

  .login {
    padding: 6px 9px;
    font-size: 0.72rem;
  }
}
.avatar.has-img {
  overflow: hidden;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}
</style>
