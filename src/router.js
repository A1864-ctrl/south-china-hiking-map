import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from './views/HomeView.vue'
import SpotsView from './views/SpotsView.vue'
import RoutesView from './views/RoutesView.vue'
import HeatView from './views/HeatView.vue'
import GearView from './views/GearView.vue'
import RouteDetailView from './views/RouteDetailView.vue'
import SpotDetailView from './views/SpotDetailView.vue'
import MeView from './views/MeView.vue'
import VersionsView from './views/VersionsView.vue'
import CommunityView from './views/CommunityView.vue'
import ReportsView from './views/ReportsView.vue'
import SafetyView from './views/SafetyView.vue'
import CampsView from './views/CampsView.vue'
import WeatherView from './views/WeatherView.vue'
import LearnView from './views/LearnView.vue'
import GearLabView from './views/GearLabView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '项目说明' } },
  { path: '/spots', name: 'spots', component: SpotsView, meta: { title: '景点搜索' } },
  { path: '/routes', name: 'routes', component: RoutesView, meta: { title: '徒步轨迹' } },
  { path: '/route/:id', name: 'routeDetail', component: RouteDetailView, meta: { title: '路线详情' } },
  { path: '/spot/:name', name: 'spotDetail', component: SpotDetailView, meta: { title: '景点路书' } },
  { path: '/heat', name: 'heat', component: HeatView, meta: { title: '城市热度' } },
  { path: '/gear', name: 'gear', component: GearView, meta: { title: '装备清单' } },
  { path: '/community', name: 'community', component: CommunityView, meta: { title: '山友社区' } },
  { path: '/me', name: 'me', component: MeView, meta: { title: '我的收藏' } },
  { path: '/reports', name: 'reports', component: ReportsView, meta: { title: '路况上报' } },
  { path: '/safety', name: 'safety', component: SafetyView, meta: { title: '安全报备' } },
  { path: '/camps', name: 'camps', component: CampsView, meta: { title: '营地库' } },
  { path: '/weather', name: 'weather', component: WeatherView, meta: { title: '点位天气' } },
  { path: '/learn', name: 'learn', component: LearnView, meta: { title: '山野知识库' } },
  { path: '/gear-lab', name: 'gearLab', component: GearLabView, meta: { title: '我的装备库' } },
  { path: '/versions', name: 'versions', component: VersionsView, meta: { title: '版本对比' } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 浏览器前进/后退：回到离开时的位置；其它跳转：从顶部开始
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 野径` : '野径 · 华南徒步图鉴'
})

export default router
