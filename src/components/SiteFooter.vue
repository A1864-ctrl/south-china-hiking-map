<script setup>
import { overview } from '../data/cities.js'
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="f-brand">
        <div class="f-title">野径 · 华南徒步图鉴</div>
        <p>广东 · 湖南 · 江西 · 广西桂林 —— 找景点、看徒步轨迹、查城市热度</p>
      </div>
      <div class="f-links">
        <router-link to="/spots">景点搜索</router-link>
        <router-link to="/routes">徒步轨迹</router-link>
        <router-link to="/heat">城市热度</router-link>
        <router-link to="/community">山友社区</router-link>
        <router-link to="/reports">路况上报</router-link>
        <router-link to="/safety">安全报备</router-link>
        <router-link to="/camps">营地库</router-link>
        <router-link to="/weather">点位天气</router-link>
        <router-link to="/learn">山野知识</router-link>
        <router-link to="/gear-lab">我的装备库</router-link>
        <router-link to="/versions" title="这个站点每一版改了什么">更新日志</router-link>
      </div>
      <div class="f-stats">
        <span class="mono">{{ overview.spotCount }}</span> 个景点 ·
        <span class="mono">{{ overview.routeCount }}</span> 条路线 ·
        <span class="mono">{{ overview.totalKm }}</span> 公里轨迹
      </div>
      <div class="f-disclaimer">
        关于数据：景点照片来自维基百科条目的开放版权图片，作者与许可标注在图集右上角；轨迹是按真实关键点拟合的示意线，
        不是 GPS 实测记录，实地请以路标和官方步道为准。热度分、门票与建议时长是整理估算，出发前看一眼景区公告。
        <br />
        徒步有风险，出行请结伴，把行程告诉留守人。
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
