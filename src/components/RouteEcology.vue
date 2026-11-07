<script setup>
/** 单条路线的山野科普：地形 / 植被 / 动物 / 注意事项 */
import { computed } from 'vue'
import { ecologyOf, ANIMAL_LEVEL } from '../data/routeEcology.js'

const props = defineProps({ route: { type: Object, required: true } })
const eco = computed(() => ecologyOf(props.route))
const lv = (n) => ANIMAL_LEVEL[n] || ANIMAL_LEVEL[1]
</script>

<template>
  <div class="eco">
    <div class="facts">
      <div>
        <span>所属区域</span>
        <b>{{ eco.region }}</b>
      </div>
      <div>
        <span>地貌类型</span>
        <b>{{ eco.terrain.name }}</b>
      </div>
      <div>
        <span>海拔区间</span>
        <b>{{ eco.facts.ele }}</b>
      </div>
      <div>
        <span>建议季节</span>
        <b>{{ eco.facts.season }}</b>
      </div>
    </div>

    <p v-if="eco.fact" class="fact">{{ eco.fact }}</p>
    <p class="region-geo">{{ eco.regionGeo }}</p>

    <div class="grid">
      <!-- 地形地势 -->
      <section class="card-block">
        <h3><em>01</em>地形地势</h3>
        <p class="lead">{{ eco.terrain.geo }}</p>
        <div v-if="eco.keyPoints.length" class="points">
          <p class="p-title">关键节点</p>
          <div v-for="p in eco.keyPoints" :key="p.name" class="point">
            <span class="p-name">{{ p.name }}</span>
            <span class="p-ele">{{ p.ele }} m</span>
            <p class="p-note">{{ p.note }}</p>
          </div>
        </div>
      </section>

      <!-- 植被 -->
      <section class="card-block">
        <h3><em>02</em>植被分布</h3>
        <p class="lead">{{ eco.terrain.flora }}</p>
        <div class="plants">
          <span v-for="p in eco.terrain.plants" :key="p">{{ p }}</span>
        </div>
        <div v-if="eco.bands.length" class="bands">
          <p class="p-title">垂直带谱</p>
          <div v-for="(b, i) in eco.bands" :key="b.r" class="band">
            <span class="b-r">{{ b.r }}</span>
            <span class="b-dot" :style="{ opacity: 1 - i * 0.22 }"></span>
            <p class="b-t">{{ b.t }}</p>
          </div>
        </div>
        <p class="season-note">{{ eco.terrain.seasonNote }}</p>
      </section>

      <!-- 动物 -->
      <section class="card-block">
        <h3><em>03</em>动物种类</h3>
        <p class="lead">以下为该区域有记录的代表性种类，按对人影响标注等级。多数冲突来自「投喂」与「突然靠近」。</p>
        <div class="animals">
          <div v-for="a in eco.animals" :key="a.n" class="animal">
            <div class="a-top">
              <b>{{ a.n }}</b>
              <em :style="{ color: lv(a.lv).tone, borderColor: lv(a.lv).tone + '55' }">{{ lv(a.lv).name }}</em>
            </div>
            <p>{{ a.t }}</p>
          </div>
        </div>
      </section>

      <!-- 注意事项 -->
      <section class="card-block">
        <h3><em>04</em>需要注意</h3>
        <ol class="cautions">
          <li v-for="(c, i) in eco.cautions" :key="i">{{ c }}</li>
        </ol>
        <div v-if="eco.risks.length" class="risks">
          <span class="r-label">本条线标注</span>
          <span v-for="r in eco.risks" :key="r" class="r-chip">{{ r }}</span>
        </div>
        <p class="tip">
          保护区内一切以管理公告为准；不要投喂、不要采集、不要为了拍照离开步道。
        </p>
      </section>
    </div>

    <p class="foot">
      内容按「地区自然地理档案 × 地貌类型 × 本条线特征」整理，用于行前科普与风险预判；
      物种记录以保护区名录与公开调查为准，不作为辨认依据。遇到不确定的蛇虫，保持距离、不要触碰。
    </p>
  </div>
</template>

<style scoped>
.eco {
  animation: fade 0.3s ease;
}
@keyframes fade {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}
.facts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.facts div {
  padding: 11px 14px;
  border-right: 1px solid var(--line);
}
.facts div:last-child {
  border-right: none;
}
.facts span {
  display: block;
  font-size: 0.58rem;
  color: var(--gray-light);
  letter-spacing: 0.08em;
}
.facts b {
  display: block;
  font-family: var(--serif);
  font-size: 0.9rem;
  color: var(--forest-dark);
  margin-top: 3px;
  line-height: 1.4;
}
.fact {
  margin-top: 12px;
  padding: 11px 14px;
  background: #fdf7e8;
  border: 1px dashed #e3d3a8;
  border-radius: 5px;
  font-size: 0.78rem;
  color: #6b5320;
  line-height: 1.9;
}
.region-geo {
  font-size: 0.76rem;
  color: var(--gray);
  line-height: 1.9;
  margin-top: 10px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}
.card-block {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px 16px;
  background: #fff;
}
.card-block h3 {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-family: var(--serif);
  font-size: 0.94rem;
  font-weight: 600;
  color: var(--ink);
  padding-bottom: 9px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 10px;
}
.card-block h3 em {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.58rem;
  font-style: normal;
  color: var(--forest-light);
  letter-spacing: 0.1em;
}
.lead {
  font-size: 0.76rem;
  color: var(--ink-soft);
  line-height: 1.95;
}
.p-title {
  font-size: 0.6rem;
  color: var(--gray-light);
  letter-spacing: 0.08em;
  margin: 12px 0 6px;
}
.points {
  margin-top: 2px;
}
.point {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(230, 225, 214, 0.8);
}
.point:last-child {
  border-bottom: none;
}
.p-name {
  font-size: 0.72rem;
  color: var(--ink);
  font-weight: 600;
}
.p-ele {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.6rem;
  color: var(--gray-light);
}
.p-note {
  grid-column: 1 / -1;
  font-size: 0.66rem;
  color: var(--gray);
  line-height: 1.75;
}
.plants {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 9px;
}
.plants span {
  font-size: 0.58rem;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--forest-soft);
  color: var(--forest);
}
.bands {
  margin-top: 2px;
}
.band {
  display: grid;
  grid-template-columns: 74px 10px 1fr;
  gap: 8px;
  align-items: start;
  padding: 7px 0;
}
.b-r {
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.6rem;
  color: var(--forest);
  padding-top: 2px;
}
.b-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--forest-light);
  margin-top: 5px;
}
.b-t {
  font-size: 0.68rem;
  color: var(--ink-soft);
  line-height: 1.8;
}
.animals {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
}
.animal {
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 8px 9px;
  background: #fcfaf5;
}
.a-top {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}
.a-top b {
  font-size: 0.72rem;
  color: var(--ink);
}
.a-top em {
  font-size: 0.52rem;
  font-style: normal;
  border: 1px solid;
  border-radius: 2px;
  padding: 0 4px;
}
.animal p {
  font-size: 0.6rem;
  color: var(--gray);
  line-height: 1.7;
  margin-top: 3px;
}
.cautions {
  margin: 0;
  padding-left: 18px;
}
.cautions li {
  font-size: 0.72rem;
  color: var(--ink-soft);
  line-height: 1.95;
  margin-bottom: 3px;
}
.cautions li::marker {
  color: var(--forest-light);
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.62rem;
}
.risks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 10px;
}
.r-label {
  font-size: 0.56rem;
  color: var(--gray-light);
  letter-spacing: 0.06em;
  margin-right: 2px;
}
.r-chip {
  font-size: 0.56rem;
  padding: 1px 7px;
  border-radius: 999px;
  background: #f7eae7;
  color: #a9462f;
}
.tip {
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px dashed var(--line);
  font-size: 0.62rem;
  color: var(--gray-light);
  line-height: 1.8;
}
.season-note {
  margin-top: 11px;
  padding-top: 9px;
  border-top: 1px dashed var(--line);
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.85;
}
.foot {
  font-size: 0.6rem;
  color: var(--gray-light);
  line-height: 1.85;
  margin-top: 12px;
}
@media (max-width: 900px) {
  .facts {
    grid-template-columns: 1fr 1fr;
  }
  .facts b {
    font-size: 0.8rem;
    line-height: 1.35;
  }
  .facts div {
    padding: 9px 11px;
  }
  .facts b {
    font-size: 0.8rem;
    line-height: 1.35;
  }
  .facts div {
    padding: 9px 11px;
  }
  .facts div:nth-child(2) {
    border-right: none;
  }
  .facts div:nth-child(1),
  .facts div:nth-child(2) {
    border-bottom: 1px solid var(--line);
  }
  .grid {
    grid-template-columns: 1fr;
  }
  .animals {
    grid-template-columns: 1fr;
  }
}
</style>
