// 收藏：登录后存云端（多设备同步）；未登录沿用本机。登录时自动把本机收藏合并上云
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth.js'
import { cloud } from '../services/cloud.js'

const KEY = 'yejing:fav:v2'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {}
  } catch {
    return {}
  }
}

export const useFavStore = defineStore('fav', () => {
  const auth = useAuthStore()
  const all = ref(read()) // 本机桶（游客 / 迁移前的旧数据）
  const cloudRows = ref([]) // 云端行 [{kind, item_id}]
  const loaded = ref(false)

  /** 统一视图：登录用云端，游客用本机 */
  const mine = computed(() => {
    if (auth.isLogged) {
      const out = { spot: [], route: [] }
      for (const r of cloudRows.value) {
        if (out[r.kind]) out[r.kind].push(r.item_id)
      }
      return out
    }
    return all.value[auth.account] || { spot: [], route: [] }
  })

  function persist() {
    try {
      localStorage.setItem(KEY, JSON.stringify(all.value))
    } catch {
      /* ignore */
    }
  }

  function localBucket(kind) {
    const acc = auth.account || '__guest'
    if (!all.value[acc]) all.value[acc] = { spot: [], route: [] }
    if (!all.value[acc][kind]) all.value[acc][kind] = []
    return all.value[acc][kind]
  }

  /** 登录后调用：把本机旧收藏上云合并，再拉取云端全量 */
  async function load() {
    if (!auth.isLogged) {
      loaded.value = true
      return
    }
    // 一次性合并本机旧数据（含迁移前的旧账号桶）
    const locals = new Set()
    for (const [acc, buckets] of Object.entries(read())) {
      for (const kind of ['spot', 'route']) {
        for (const id of buckets[kind] || []) locals.add(`${kind}:${id}`)
      }
    }
    if (locals.size) {
      for (const key of locals) {
        const [kind, itemId] = key.split(':')
        await cloud.database.from('favorites').upsert(
          { kind, item_id: itemId },
          { onConflict: 'owner_id,kind,item_id', ignoreDuplicates: true }
        )
      }
      try {
        localStorage.removeItem(KEY)
        localStorage.setItem('yejing:fav:migrated', String(Date.now()))
      } catch {
        /* ignore */
      }
    }
    const { data, error } = await cloud.database.from('favorites').select('kind, item_id')
    if (!error) {
      cloudRows.value = data || []
      all.value = {}
      persist()
    }
    loaded.value = true
  }

  function has(kind, id) {
    return mine.value[kind]?.includes(id) || false
  }

  /** 收藏 / 取消，返回是否已收藏；游客仍写本机 */
  async function toggle(kind, id) {
    const item = String(id)
    if (!auth.isLogged) {
      const list = localBucket(kind)
      const i = list.indexOf(item)
      if (i >= 0) list.splice(i, 1)
      else list.unshift(item)
      all.value = { ...all.value }
      persist()
      return i < 0
    }
    if (has(kind, id)) {
      const { error } = await cloud.database.from('favorites').delete().match({ kind, item_id: item })
      if (error) return false
      cloudRows.value = cloudRows.value.filter((r) => !(r.kind === kind && r.item_id === item))
      return false
    }
    const { error } = await cloud.database.from('favorites').insert({ kind, item_id: item })
    if (error) return false
    cloudRows.value = [{ kind, item_id: item }, ...cloudRows.value]
    return true
  }

  async function remove(kind, id) {
    if (!auth.isLogged) {
      const list = localBucket(kind)
      const i = list.indexOf(String(id))
      if (i >= 0) {
        list.splice(i, 1)
        all.value = { ...all.value }
        persist()
      }
      return
    }
    const { error } = await cloud.database.from('favorites').delete().match({ kind, item_id: String(id) })
    if (!error) cloudRows.value = cloudRows.value.filter((r) => !(r.kind === kind && r.item_id === String(id)))
  }

  function count(kind) {
    return mine.value[kind]?.length || 0
  }
  function total() {
    return count('spot') + count('route')
  }

  return { all, mine, has, toggle, remove, count, total, load, loaded }
})
