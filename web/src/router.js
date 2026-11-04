import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from './views/HomeView.vue'
import SpotsView from './views/SpotsView.vue'
import RoutesView from './views/RoutesView.vue'
import HeatView from './views/HeatView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '项目说明' } },
  { path: '/spots', name: 'spots', component: SpotsView, meta: { title: '景点搜索' } },
  { path: '/routes', name: 'routes', component: RoutesView, meta: { title: '徒步轨迹' } },
  { path: '/heat', name: 'heat', component: HeatView, meta: { title: '城市热度' } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 华南徒步地图` : '华南徒步地图'
})

export default router
