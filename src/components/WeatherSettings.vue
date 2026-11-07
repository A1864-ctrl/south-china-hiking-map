<script setup>
/** 天气数据源配置：API Host + Key 只存本机，保存后立即测试一次 */
import { ref } from 'vue'
import { readConfig, saveConfig, fetchWeather } from '../data/qweather.js'
import { useUiStore } from '../stores/ui.js'

const emit = defineEmits(['changed'])
const ui = useUiStore()

const cfg = readConfig()
const configured = ref(!!(cfg.host && cfg.key))
const open = ref(false)
const host = ref(cfg.host)
const key = ref(cfg.key)
const msg = ref('')
const busy = ref(false)

async function save() {
  if (!host.value.trim()) {
    msg.value = '先填 API Host，在控制台项目详情页可以复制'
    return
  }
  if (!key.value.trim()) {
    msg.value = '先填 API Key'
    return
  }
  busy.value = true
  msg.value = '测试中…'
  const saved = saveConfig({ host: host.value, key: key.value })
  try {
    await fetchWeather(23.13, 113.26, { days: 1 })
    configured.value = true
    configured.value = true
    msg.value = '连接成功，已切换为真实数据'
    ui.toast('天气已接入和风')
    emit('changed')
  } catch (e) {
    msg.value = e.message || '连接失败'
    ui.toast(e.message || '连接失败')
  } finally {
    busy.value = false
  }
  return saved
}

function clear() {
  saveConfig({ host: host.value, key: '' })
  key.value = ''
  configured.value = false
  msg.value = '已清除 Key，回到模拟数据'
  emit('changed')
  ui.toast('已回到模拟数据')
}
</script>

<template>
  <div class="wcfg">
    <button class="wcfg-head" @click="open = !open">
      <span class="wcfg-k">数据源</span>
      <span class="wcfg-v">{{ configured ? '和风天气 · 已接入' : '当前为模拟数据' }}</span>
      <em>{{ open ? '收起' : '配置' }}</em>
    </button>

    <div v-if="open" class="wcfg-body">
      <p class="wcfg-tip">
        填入和风天气的 API Host 与 Key 后，这个页面与路线详情里的天气都会换成真实数据。
        Key 只保存在本机浏览器，不会随页面发布出去。
      </p>
      <label>
        <span>API Host</span>
        <input v-model="host" placeholder="例：abcxyz.qweatherapi.com" spellcheck="false" />
      </label>
      <label>
        <span>API Key</span>
        <input v-model="key" type="password" placeholder="控制台 → 项目管理 → 凭据" spellcheck="false" />
      </label>
      <div class="wcfg-acts">
        <button class="primary" :disabled="busy" @click="save">{{ busy ? '测试中…' : '保存并测试' }}</button>
        <button class="ghost" @click="clear">清除 Key</button>
        <a class="link" href="https://console.qweather.com/project" target="_blank" rel="noreferrer">打开和风控制台 →</a>
      </div>
      <p v-if="msg" class="wcfg-msg">{{ msg }}</p>
      <p class="wcfg-note">
        提示：新版接口路径里纬度在前；API Host 在控制台项目详情页可以复制，不要填 devapi（那是旧版默认域名）。
      </p>
    </div>
  </div>
</template>

<style scoped>
.wcfg {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
}
.wcfg-head {
  width: 100%;
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 14px;
  border: none;
  background: #fcfaf5;
  cursor: pointer;
  text-align: left;
}
.wcfg-k {
  font-size: 0.6rem;
  color: var(--gray-light);
  letter-spacing: 0.08em;
}
.wcfg-v {
  font-size: 0.72rem;
  color: var(--forest-dark);
  font-weight: 600;
}
.wcfg-head em {
  margin-left: auto;
  font-style: normal;
  font-size: 0.62rem;
  color: var(--forest);
}
.wcfg-body {
  padding: 12px 14px 13px;
  border-top: 1px solid var(--line);
}
.wcfg-tip {
  font-size: 0.64rem;
  color: var(--gray);
  line-height: 1.75;
  margin-bottom: 10px;
}
label {
  display: block;
  margin-bottom: 8px;
}
label span {
  display: block;
  font-size: 0.6rem;
  color: var(--gray);
  margin-bottom: 4px;
}
input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 0.72rem;
  background: #fcfaf5;
  color: var(--ink);
  outline: none;
  font-family: inherit;
}
input:focus {
  border-color: var(--forest-light);
  background: #fff;
}
.wcfg-acts {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.wcfg-acts .primary {
  border: none;
  background: var(--forest);
  color: #fff;
  border-radius: 4px;
  font-size: 0.68rem;
  padding: 6px 12px;
  cursor: pointer;
}
.wcfg-acts .primary:disabled {
  opacity: 0.6;
  cursor: wait;
}
.wcfg-acts .ghost {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--gray);
  border-radius: 4px;
  font-size: 0.68rem;
  padding: 6px 12px;
  cursor: pointer;
}
.wcfg-acts .link {
  font-size: 0.62rem;
  color: var(--forest);
  text-decoration: none;
}
.wcfg-msg {
  margin-top: 8px;
  font-size: 0.64rem;
  color: #8a6d2f;
  line-height: 1.7;
}
.wcfg-note {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.75;
}
</style>
