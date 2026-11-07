<script setup>
/** 顶部导航的图标：统一 24 网格、1.6 描边，悬停时各自有一个小动作 */
defineProps({ name: { type: String, required: true } })
</script>

<template>
  <svg viewBox="0 0 24 24" width="19" height="19" fill="none" aria-hidden="true">
    <template v-if="name === 'home'">
      <path d="M2.5 19h19L14 6.5l-3 5.6-2-3.2L2.5 19z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
      <circle class="ic-sun" cx="17.6" cy="6.4" r="1.9" stroke="currentColor" stroke-width="1.5" />
    </template>

    <template v-else-if="name === 'spots'">
      <rect class="ic-frame" x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" stroke-width="1.6" />
      <path d="M6.4 15.6l3.4-4.3 2.3 2.8 1.7-2 3.6 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="8.6" cy="9.3" r="1.1" fill="currentColor" />
    </template>

    <template v-else-if="name === 'routes'">
      <circle cx="6" cy="17.5" r="2.2" stroke="currentColor" stroke-width="1.6" />
      <circle cx="18" cy="6.5" r="2.2" stroke="currentColor" stroke-width="1.6" />
      <path
        class="ic-trail"
        d="M7.6 15.7c1.6-2 .4-3.4-1-4.4-1.6-1.2-1.2-2.9.7-3.4 2.6-.7 4.2 1.2 5.6 2.6 1.4 1.4 3 1.9 4.3.6"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-dasharray="3 3"
      />
    </template>

    <template v-else-if="name === 'heat'">
      <rect class="ic-bar b1" x="4" y="12" width="3.4" height="8" rx="1" fill="currentColor" opacity="0.55" />
      <rect class="ic-bar b2" x="10.3" y="8.5" width="3.4" height="11.5" rx="1" fill="currentColor" opacity="0.75" />
      <rect class="ic-bar b3" x="16.6" y="5" width="3.4" height="15" rx="1" fill="currentColor" />
    </template>

    <template v-else-if="name === 'gear'">
      <path class="ic-pack" d="M7.5 9.5V8a4.5 4.5 0 019 0v1.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      <rect x="4.5" y="9.5" width="15" height="10.5" rx="3" stroke="currentColor" stroke-width="1.6" />
      <path d="M9.5 13.6h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <path class="ic-strap" d="M15.2 9.5v10.5" stroke="currentColor" stroke-width="1.3" opacity="0.5" />
    </template>

    <template v-else-if="name === 'community'">
      <path
        d="M4.6 6.4h10.6a2.2 2.2 0 012.2 2.2v4.5a2.2 2.2 0 01-2.2 2.2H9.6L6.2 18v-2.7H4.6a2.2 2.2 0 01-2.2-2.2V8.6a2.2 2.2 0 012.2-2.2z"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linejoin="round"
      />
      <circle class="ic-dot d1" cx="7.6" cy="10.9" r="0.95" fill="currentColor" />
      <circle class="ic-dot d2" cx="10.6" cy="10.9" r="0.95" fill="currentColor" />
      <circle class="ic-dot d3" cx="13.6" cy="10.9" r="0.95" fill="currentColor" />
      <path
        class="ic-reply"
        d="M18.6 10.2h.8a2 2 0 012 2v3.2a2 2 0 01-2 2h-.6v2.2l-2.6-2.2"
        stroke="currentColor"
        stroke-width="1.4"
        stroke-linejoin="round"
        opacity="0.45"
      />
    </template>

    <template v-else-if="name === 'versions'">
      <path class="ic-layer l1" d="M12 3.6l8 4.2-8 4.2-8-4.2 8-4.2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
      <path class="ic-layer l2" d="M4 12.2l8 4.2 8-4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.7" />
      <path class="ic-layer l3" d="M4 16.4l8 4.2 8-4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.42" />
    </template>

    <template v-else>
      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6" />
    </template>
  </svg>
</template>

<style scoped>
svg {
  display: block;
  overflow: visible;
}

.ic-sun,
.ic-frame,
.ic-bar,
.ic-pack,
.ic-layer {
  transition: transform 0.26s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.2s;
  transform-box: fill-box;
  transform-origin: center;
}

.ic-trail {
  transition: stroke-dashoffset 0.5s linear;
  stroke-dashoffset: 0;
}

.ic-bar {
  transform-origin: center bottom;
}

.ic-layer.l1 {
  transform-origin: center top;
}
</style>
