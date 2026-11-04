<script setup>
import { computed } from 'vue'
import { overview, cityStats } from '../data/cities.js'
import { routes } from '../data/routes.js'

const topRoutes = computed(() => routes.slice().sort((a, b) => b.heat - a.heat).slice(0, 5))
const topCities = cityStats.slice(0, 5)

const modules = [
  {
    to: '/spots',
    icon: '🔍',
    title: '景点搜索',
    en: 'SPOTS',
    desc: '输入地名、景点名或类型，看这一片值得去哪些地方、为什么值得去。',
    points: ['热门城市一键切换', '按类型筛选（山峰 / 海岸 / 丹霞 / 古镇…）', '地图上看点位分布与密度'],
    color: '#2d5a3d'
  },
  {
    to: '/routes',
    icon: '🥾',
    title: '徒步轨迹',
    en: 'TRAILS',
    desc: '选一条路线，地图上画出轨迹与途经点，附分段路书、补给点、交通接驳与装备清单。',
    points: ['湖南 + 广东全覆盖 + 全国热门', '轨迹 / 分段路书 / 高程剖面联动', '支持导出 GPX 到手表或两步路'],
    color: '#8b6914'
  },
  {
    to: '/heat',
    icon: '🔥',
    title: '城市热度',
    en: 'CITIES',
    desc: '把景点和徒步路线按城市汇总，看哪个城市更值得排进行程。',
    points: ['综合热度指数 Top 15', '景点与路线双维度对比', '观光型 / 徒步型城市一眼分辨'],
    color: '#c0392b'
  }
]

const tips = [
  { icon: '📱', title: '提前下载离线轨迹', text: '山区信号差，出发前把轨迹和离线地图下好，别把手机导航当成唯一依靠。' },
  { icon: '🔋', title: '备足电源', text: '长线建议带卫星通讯设备，手机导航耗电快，充电宝按每天 2 次满充准备。' },
  { icon: '👥', title: '结伴出行', text: '险峻山脊线不要独行，队伍里至少两人识图，出发前把行程告诉留守人。' },
  { icon: '🥾', title: '带双登山杖', text: '千级爬升路线务必带双杖，下坡对膝盖的保护非常明显。' },
  { icon: '🧥', title: '注意防风保暖', text: '高海拔和海边线路昼夜温差大，硬壳和薄羽绒常年放包里。' }
]

const steps = [
  { no: '01', title: '先定片区', text: '在「景点搜索」点一个城市，看这个片区有多少景点、热度分布如何。' },
  { no: '02', title: '再挑路线', text: '到「徒步轨迹」按难度筛选，看轨迹形状、爬升和最佳季节是否匹配你的体能。' },
  { no: '03', title: '排进行程', text: '「城市热度」把景点和路线对比一遍，决定这几天以观光为主还是徒步为主。' },
  { no: '04', title: '导出出发', text: '选中的路线可以导出 GPX，导入两步路 / 手表，离线也能跟着走。' }
]
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div class="hero-eyebrow">GUANGDONG · HUNAN · JIANGXI · GUILIN</div>
        <h1>探索山野 · 徒步中国</h1>
        <p class="hero-sub">
          广东 · 湖南 · 江西 · 广西桂林 —— 找景点、看徒步轨迹、查城市热度，一个页面把周末安排明白。
        </p>
        <div class="hero-stats">
          <div class="stat-item">
            <div class="stat-num mono">{{ overview.spotCount }}</div>
            <div class="stat-label">收录景点</div>
          </div>
          <div class="stat-item">
            <div class="stat-num mono">{{ overview.routeCount }}</div>
            <div class="stat-label">徒步路线</div>
          </div>
          <div class="stat-item">
            <div class="stat-num mono">{{ overview.cityCount }}</div>
            <div class="stat-label">覆盖城市</div>
          </div>
          <div class="stat-item">
            <div class="stat-num mono">{{ overview.totalKm }}</div>
            <div class="stat-label">公里轨迹</div>
          </div>
        </div>
        <div class="hero-actions">
          <router-link to="/spots" class="hero-btn primary">开始找景点 →</router-link>
          <router-link to="/routes" class="hero-btn ghost">看徒步轨迹</router-link>
        </div>
      </div>
      <div class="hero-scroll">向下滚动 ↓</div>
    </section>

    <div class="container">
      <!-- 三个入口 -->
      <section class="block">
        <div class="block-head">
          <div>
            <h2 class="block-title">这个站点回答三个问题</h2>
            <p class="block-desc">每个功能对应一个真实决策：去哪玩、怎么走、排几天。</p>
          </div>
        </div>
        <div class="module-grid">
          <router-link v-for="m in modules" :key="m.to" :to="m.to" class="module-card">
            <div class="m-top">
              <div class="m-icon" :style="{ background: m.color + '14', color: m.color }">{{ m.icon }}</div>
              <span class="m-en mono">{{ m.en }}</span>
            </div>
            <h3>{{ m.title }}</h3>
            <p class="m-desc">{{ m.desc }}</p>
            <ul class="m-points">
              <li v-for="p in m.points" :key="p">{{ p }}</li>
            </ul>
            <span class="m-go">进入 {{ m.title }} <i>→</i></span>
          </router-link>
        </div>
      </section>

      <!-- 数据速览 -->
      <section class="block">
        <div class="block-head">
          <div>
            <h2 class="block-title">现在最值得去的</h2>
            <p class="block-desc">按站点内热度排序，热度由景点评分、路线热度与可玩性综合得出。</p>
          </div>
        </div>
        <div class="preview-grid">
          <div class="preview-card card">
            <div class="p-head">
              <h4>🔥 热门徒步路线</h4>
              <router-link to="/routes" class="p-more">全部 →</router-link>
            </div>
            <ul class="p-list">
              <li v-for="(r, i) in topRoutes" :key="r.id">
                <router-link :to="'/routes?id=' + r.id" class="p-row">
                  <span class="p-rank mono" :class="{ top: i < 3 }">{{ i + 1 }}</span>
                  <span class="p-main">
                    <b>{{ r.name }}</b>
                    <em>{{ r.city }} · {{ r.terrain }} · {{ r.days }}</em>
                  </span>
                  <span class="p-num mono">{{ r.heat }}</span>
                </router-link>
              </li>
            </ul>
          </div>

          <div class="preview-card card">
            <div class="p-head">
              <h4>🔥 综合热度城市</h4>
              <router-link to="/heat" class="p-more">全部 →</router-link>
            </div>
            <ul class="p-list">
              <li v-for="(c, i) in topCities" :key="c.name">
                <router-link :to="'/spots?city=' + encodeURIComponent(c.name)" class="p-row">
                  <span class="p-rank mono" :class="{ top: i < 3 }">{{ i + 1 }}</span>
                  <span class="p-main">
                    <b>{{ c.name }}</b>
                    <em>{{ c.spotCount }} 景点 · {{ c.routeCount }} 路线 · {{ c.province }}</em>
                  </span>
                  <span class="p-num mono" :style="{ color: 'var(--forest)' }">{{ c.index }}</span>
                </router-link>
              </li>
            </ul>
          </div>

          <div class="hard-card card">
            <div class="p-head">
              <h4>⛰ 强度天花板</h4>
            </div>
            <div class="h-name">{{ overview.hardest.name }}</div>
            <div class="h-meta">{{ overview.hardest.city }} · {{ overview.hardest.terrain }}</div>
            <div class="h-stats">
              <div><span class="mono">{{ overview.hardest.distance }}</span><em>km</em></div>
              <div><span class="mono">{{ overview.hardest.climb }}</span><em>m 爬升</em></div>
              <div><span class="mono">{{ overview.hardest.days }}</span><em>建议行程</em></div>
            </div>
            <p class="h-desc">{{ overview.hardest.desc }}</p>
            <router-link :to="'/routes?id=' + overview.hardest.id" class="btn btn-ghost h-btn">
              查看轨迹
            </router-link>
          </div>
        </div>
      </section>

      <!-- 使用步骤 -->
      <section class="block">
        <div class="block-head">
          <div>
            <h2 class="block-title">四步用起来</h2>
            <p class="block-desc">页面切换、功能切换都在顶部导航，随时点到哪个模块都不会丢上下文。</p>
          </div>
        </div>
        <div class="steps">
          <div v-for="s in steps" :key="s.no" class="step">
            <span class="step-no mono">{{ s.no }}</span>
            <h4>{{ s.title }}</h4>
            <p>{{ s.text }}</p>
          </div>
        </div>
      </section>

      <!-- 安全贴士 -->
      <section class="block">
        <div class="block-head">
          <div>
            <h2 class="block-title">徒步安全贴士</h2>
            <p class="block-desc">户外徒步，安全永远排在风景前面。</p>
          </div>
        </div>
        <div class="tips-grid">
          <div v-for="t in tips" :key="t.title" class="tip-card">
            <div class="tip-icon">{{ t.icon }}</div>
            <div class="tip-title">{{ t.title }}</div>
            <div class="tip-text">{{ t.text }}</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ── Hero ── */
.hero {
  position: relative;
  min-height: 560px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #fff;
  overflow: hidden;
  padding: calc(var(--nav-h) + 40px) 24px 60px;
  background: linear-gradient(135deg, #1e3d29, #2d5a3d 55%, #3d6b4f);
}

.hero-bg {
  position: absolute;
  inset: 0;
  background-image: url('https://media.doubao.com/space/api/box/stream/download/all_by_mount_point/XqBJbDwT1ovX6ixiY63cf63OnJb');
  background-size: cover;
  background-position: center 40%;
  opacity: 0.55;
  z-index: 0;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(30, 61, 41, 0.55) 0%, rgba(30, 61, 41, 0.72) 55%, rgba(30, 61, 41, 0.88) 100%);
  z-index: 1;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 880px;
}

.hero-eyebrow {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.28em;
  color: var(--earth-light);
  margin-bottom: 18px;
}

.hero h1 {
  font-size: clamp(2.2rem, 5.4vw, 3.9rem);
  font-weight: 800;
  letter-spacing: 0.04em;
  text-shadow: 0 4px 30px rgba(0, 0, 0, 0.35);
  line-height: 1.2;
}

.hero-sub {
  margin: 18px auto 36px;
  font-size: clamp(0.9rem, 1.5vw, 1.05rem);
  color: rgba(255, 255, 255, 0.86);
  max-width: 660px;
  line-height: 1.8;
}

.hero-stats {
  display: flex;
  justify-content: center;
  gap: 56px;
  flex-wrap: wrap;
}

.stat-num {
  font-size: 2.1rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.62);
  letter-spacing: 0.1em;
}

.hero-actions {
  display: flex;
  gap: 14px;
  justify-content: center;
  margin-top: 36px;
  flex-wrap: wrap;
}

.hero-btn {
  padding: 12px 26px;
  border-radius: 999px;
  font-size: 0.92rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.hero-btn.primary {
  background: #fff;
  color: var(--forest-dark);
}

.hero-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
}

.hero-btn.ghost {
  border: 1.5px solid rgba(255, 255, 255, 0.5);
  color: #fff;
}

.hero-btn.ghost:hover {
  background: rgba(255, 255, 255, 0.12);
}

.hero-scroll {
  position: absolute;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  color: rgba(255, 255, 255, 0.5);
  z-index: 2;
}

/* ── Block ── */
.block {
  padding: 56px 0 8px;
}

.block-head {
  margin-bottom: 26px;
}

.block-title {
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--forest-dark);
  letter-spacing: -0.01em;
}

.block-desc {
  color: var(--gray);
  font-size: 0.94rem;
  margin-top: 6px;
}

/* ── 模块卡 ── */
.module-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.module-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 26px 24px 22px;
  display: flex;
  flex-direction: column;
  transition: all 0.22s ease;
  box-shadow: var(--shadow-sm);
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: #cfd9d0;
}

.m-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.m-icon {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 21px;
}

.m-en {
  font-size: 0.66rem;
  letter-spacing: 0.2em;
  color: var(--gray-light);
}

.module-card h3 {
  font-size: 1.22rem;
  color: var(--forest-dark);
  margin-bottom: 8px;
}

.m-desc {
  font-size: 0.9rem;
  color: var(--ink-soft);
  line-height: 1.7;
  min-height: 62px;
}

.m-points {
  margin: 14px 0 18px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.m-points li {
  font-size: 0.82rem;
  color: var(--gray);
  padding-left: 15px;
  position: relative;
}

.m-points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--earth-light);
}

.m-go {
  margin-top: auto;
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--forest);
  display: flex;
  align-items: center;
  gap: 6px;
}

.m-go i {
  font-style: normal;
  transition: transform 0.2s;
}

.module-card:hover .m-go i {
  transform: translateX(4px);
}

/* ── 数据速览 ── */
.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 20px;
}

.preview-card {
  padding: 20px 22px;
}

.p-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.p-head h4 {
  font-size: 0.95rem;
  color: var(--forest-dark);
}

.p-more {
  font-size: 0.76rem;
  color: var(--gray);
}

.p-more:hover {
  color: var(--forest);
}

.p-list {
  display: flex;
  flex-direction: column;
}

.p-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 6px;
  border-radius: 8px;
  transition: background 0.15s;
}

.p-row:hover {
  background: var(--forest-soft);
}

.p-rank {
  width: 20px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--gray-light);
  text-align: center;
}

.p-rank.top {
  color: var(--earth);
}

.p-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.p-main b {
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.p-main em {
  font-style: normal;
  font-size: 0.72rem;
  color: var(--gray-light);
}

.p-num {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--earth);
}

.hard-card {
  padding: 20px 22px;
  background: linear-gradient(160deg, var(--forest-dark), #2d5a3d 65%, #3d6b4f);
  border: none;
  color: #fff;
  display: flex;
  flex-direction: column;
}

.hard-card .p-head h4 {
  color: #fff;
  opacity: 0.9;
}

.h-name {
  font-size: 1.15rem;
  font-weight: 700;
  margin-top: 4px;
}

.h-meta {
  font-size: 0.76rem;
  color: rgba(255, 255, 255, 0.62);
  margin-bottom: 14px;
}

.h-stats {
  display: flex;
  gap: 22px;
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}

.h-stats > div {
  display: flex;
  flex-direction: column;
}

.h-stats span {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--earth-light);
  line-height: 1.3;
}

.h-stats em {
  font-style: normal;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.55);
}

.h-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.7;
  margin: 14px 0 16px;
  flex: 1;
}

.h-btn {
  border-color: rgba(255, 255, 255, 0.28);
  background: transparent;
  color: #fff;
  align-self: flex-start;
  padding: 7px 16px;
  font-size: 0.82rem;
}

.h-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.5);
}

/* ── 步骤 ── */
.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

.step {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px;
  position: relative;
}

.step-no {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--cream-dark);
  line-height: 1;
}

.step h4 {
  font-size: 0.95rem;
  color: var(--forest-dark);
  margin: 8px 0 6px;
}

.step p {
  font-size: 0.82rem;
  color: var(--gray);
  line-height: 1.7;
}

/* ── Tips ── */
.tips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
  padding-bottom: 40px;
}

.tip-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--earth);
  padding: 20px;
}

.tip-icon {
  font-size: 1.3rem;
  margin-bottom: 8px;
}

.tip-title {
  font-weight: 700;
  color: var(--forest-dark);
  font-size: 0.9rem;
  margin-bottom: 6px;
}

.tip-text {
  font-size: 0.82rem;
  color: var(--gray);
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .module-grid,
  .preview-grid {
    grid-template-columns: 1fr 1fr;
  }

  .hard-card {
    grid-column: 1 / -1;
  }

  .steps {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .module-grid,
  .preview-grid,
  .steps {
    grid-template-columns: 1fr;
  }

  .hero-stats {
    gap: 28px;
  }

  .block-title {
    font-size: 1.35rem;
  }
}

@media (max-width: 480px) {
  .hero h1 {
    font-size: 1.9rem;
    letter-spacing: 0.02em;
  }

  .hero-eyebrow {
    font-size: 0.64rem;
    letter-spacing: 0.18em;
  }

  .hero-sub {
    font-size: 0.86rem;
  }

  .stat-num {
    font-size: 1.7rem;
  }

  .hero-stats {
    gap: 22px;
  }

  .hero {
    min-height: 500px;
    padding: calc(var(--nav-h) + 28px) 18px 54px;
  }

  .hero-actions {
    margin-top: 26px;
  }

  .hero-btn {
    padding: 10px 20px;
    font-size: 0.86rem;
  }
}
</style>
