<script setup>
import { overview } from '../data/cities.js'
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="f-brand">
        <div class="f-title">⛰ 华南徒步地图</div>
        <p>广东 · 湖南 · 江西 · 广西桂林 —— 找景点、看徒步轨迹、查城市热度</p>
      </div>
      <div class="f-links">
        <router-link to="/spots">景点搜索</router-link>
        <router-link to="/routes">徒步轨迹</router-link>
        <router-link to="/heat">城市热度</router-link>
      </div>
      <div class="f-stats">
        <span class="mono">{{ overview.spotCount }}</span> 个景点 ·
        <span class="mono">{{ overview.routeCount }}</span> 条路线 ·
        <span class="mono">{{ overview.totalKm }}</span> 公里轨迹
      </div>
      <div class="f-disclaimer">
        免责声明：本页面为个人学习项目，数据为示例数据，仅供参考。徒步有风险，出行需谨慎。请根据自身体能选择合适路线，
        出发前查询当地天气与景区公告，走成熟线路并结伴同行。
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  background: var(--forest-dark);
  color: rgba(255, 255, 255, 0.72);
  padding: 44px 0 34px;
  margin-top: auto;
}

.footer-inner {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 32px;
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 28px;
  align-items: start;
}

.f-title {
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: 8px;
}

.f-brand p {
  font-size: 0.82rem;
  opacity: 0.65;
  max-width: 340px;
}

.f-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85rem;
}

.f-links a {
  opacity: 0.75;
  transition: opacity 0.15s;
}

.f-links a:hover {
  opacity: 1;
  color: var(--earth-light);
}

.f-stats {
  font-size: 0.82rem;
  opacity: 0.75;
  font-variant-numeric: tabular-nums;
}

.f-stats .mono {
  color: var(--earth-light);
  font-weight: 600;
}

.f-disclaimer {
  grid-column: 1 / -1;
  margin-top: 14px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.74rem;
  line-height: 1.7;
  opacity: 0.45;
}

@media (max-width: 800px) {
  .footer-inner {
    grid-template-columns: minmax(0, 1fr);
    padding: 0 18px;
  }
}
</style>
