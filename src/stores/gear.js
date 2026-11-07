// 装备勾选状态：用 Pinia 管，落地到 localStorage
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

const KEY = 'yejing-gear-packed-v1'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {}
  } catch (e) {
    return {}
  }
}

export const useGearStore = defineStore('gear', () => {
  const packed = ref(load())

  watch(
    packed,
    (v) => {
      try {
        localStorage.setItem(KEY, JSON.stringify(v))
      } catch (e) {
        /* 隐身模式写不进去就算了 */
      }
    },
    { deep: true }
  )

  const isPacked = (key) => !!packed.value[key]

  function toggle(key) {
    if (packed.value[key]) delete packed.value[key]
    else packed.value[key] = 1
  }

  function setMany(keys, on) {
    keys.forEach((k) => {
      if (on) packed.value[k] = 1
      else delete packed.value[k]
    })
    // 触发一次响应
    packed.value = { ...packed.value }
  }

  /** 某个命名空间下已勾选的数量 */
  function countOf(keys) {
    return keys.filter((k) => packed.value[k]).length
  }

  function clearPrefix(prefix) {
    Object.keys(packed.value).forEach((k) => {
      if (k.startsWith(prefix)) delete packed.value[k]
    })
    packed.value = { ...packed.value }
  }

  const total = computed(() => Object.keys(packed.value).length)

  return { packed, isPacked, toggle, setMany, countOf, clearPrefix, total }
})
