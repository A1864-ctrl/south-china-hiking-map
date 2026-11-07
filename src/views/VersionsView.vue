<script setup>
import { versions, diffRows } from '../data/versions.js'
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="head">
        <p class="eyebrow">CHANGELOG</p>
        <h1>本次 vs 上一次</h1>
        <p class="lead">
          每轮改动都在这里留一条记录：改了什么、数据变了多少、长什么样、对应哪个快照。
          左边是最新一次，下面是逐项对照。
        </p>
      </header>

      <section class="diff-card">
        <div class="diff-head">
          <span class="tag">逐项对照</span>
          <div class="legend">
            <i class="d1"></i>上一次
            <i class="d2"></i>本次
          </div>
        </div>
        <div class="diff-rows">
          <div v-for="r in diffRows" :key="r.k" class="diff-row">
            <dt>{{ r.k }}</dt>
            <dd class="old">{{ r.v1 }}</dd>
            <dd class="new">{{ r.v2 }}</dd>
          </div>
        </div>
      </section>

      <section class="versions">
        <article v-for="v in versions" :key="v.id" class="vcard" :class="{ latest: v.tag === '本次' }">
          <div class="vhead">
            <span class="badge" :class="{ hot: v.tag === '本次' }">{{ v.tag }}</span>
            <span class="date">{{ v.date }}</span>
          </div>
          <h2>{{ v.title }}</h2>
          <p class="vsum">{{ v.summary }}</p>

          <dl class="metrics">
            <div v-for="m in v.metrics" :key="m.k">
              <dt>{{ m.k }}</dt>
              <dd>{{ m.v }}</dd>
            </div>
          </dl>

          <div v-if="v.shots?.length" class="shots">
            <figure v-for="s in v.shots" :key="s.src">
              <img :src="s.src" :alt="s.label" loading="lazy" />
              <figcaption>{{ s.label }}</figcaption>
            </figure>
          </div>

          <div class="vfoot">
            <span class="snap">快照 <code>{{ v.snapshot }}</code></span>
            <a v-if="v.live" :href="v.live" target="_blank" rel="noreferrer">线上版本 →</a>
          </div>
        </article>
      </section>

      <p class="tip">
        快照目录在 <code>桌面/户外徒步网站修改/快照/</code>，任意一版都能用 <code>回滚.py</code> 还原。
      </p>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding-top: var(--nav-h);
  min-height: 100vh;
}

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 30px 32px 70px;
}

.head h1 {
  font-size: 1.62rem;
  color: var(--forest-dark);
  letter-spacing: 0.01em;
}

.eyebrow {
  font-size: 0.66rem;
  letter-spacing: 0.22em;
  color: var(--earth);
  margin-bottom: 8px;
}

.lead {
  margin-top: 9px;
  font-size: 0.86rem;
  line-height: 1.85;
  color: var(--gray);
  max-width: 720px;
}

.diff-card {
  margin-top: 22px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 20px 8px;
  box-shadow: var(--shadow-sm);
}

.diff-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.tag {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--forest-dark);
  background: var(--forest-soft);
  padding: 3px 10px;
  border-radius: 999px;
}

.legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.68rem;
  color: var(--gray);
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

.legend .d1 {
  background: #e6e1d6;
}

.legend .d2 {
  background: #cfe3d6;
}

.diff-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr) minmax(0, 1.15fr);
  gap: 14px;
  padding: 11px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 0.8rem;
  line-height: 1.7;
}

.diff-row:last-child {
  border-bottom: none;
}

.diff-row dt {
  color: var(--gray);
  font-weight: 600;
}

.diff-row dd {
  margin: 0;
  border-radius: 8px;
  padding: 2px 9px;
}

.diff-row .old {
  color: var(--gray);
  background: #f6f4ee;
}

.diff-row .new {
  color: var(--forest-dark);
  background: #eef5f0;
}

.versions {
  margin-top: 20px;
  display: grid;
  gap: 16px;
}

.vcard {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px 20px 14px;
  box-shadow: var(--shadow-sm);
}

.vcard.latest {
  border-color: rgba(45, 90, 61, 0.35);
  box-shadow: 0 0 0 3px rgba(45, 90, 61, 0.07), var(--shadow-sm);
}

.vhead {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge {
  font-size: 0.66rem;
  padding: 2px 9px;
  border-radius: 999px;
  background: #efece4;
  color: var(--gray);
}

.badge.hot {
  background: var(--forest);
  color: #fff;
}

.date {
  font-size: 0.68rem;
  color: var(--gray-light);
  font-variant-numeric: tabular-nums;
}

.vcard h2 {
  margin-top: 8px;
  font-size: 1.02rem;
  color: var(--ink);
}

.vsum {
  margin-top: 6px;
  font-size: 0.8rem;
  line-height: 1.85;
  color: var(--ink-soft);
}

.metrics {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.metrics > div {
  background: #faf8f2;
  border-radius: 9px;
  padding: 7px 10px;
}

.metrics dt {
  font-size: 0.64rem;
  color: var(--gray-light);
}

.metrics dd {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: var(--forest-dark);
  font-weight: 600;
}

.shots {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.shots figure {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: #f4f2ea;
}

.shots img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
}

.shots figcaption {
  font-size: 0.68rem;
  color: var(--gray);
  padding: 6px 9px;
}

.vfoot {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.72rem;
  color: var(--gray);
}

.vfoot a {
  color: var(--forest);
}

.tip {
  margin-top: 18px;
  font-size: 0.72rem;
  color: var(--gray-light);
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: #f2efe6;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.72rem;
}

@media (max-width: 760px) {
  .container {
    padding: 20px 16px 60px;
  }
  .diff-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 5px;
  }
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .shots {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
