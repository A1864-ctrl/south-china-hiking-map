// 「我的记录」：每条路线可以放自己的笔记 / 链接，存在本机
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const KEY = 'yejing-mine-v1'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {}
  } catch (e) {
    return {}
  }
}

export const useMineStore = defineStore('mine', () => {
  const data = ref(load())

  watch(
    data,
    (v) => {
      try {
        localStorage.setItem(KEY, JSON.stringify(v))
      } catch (e) {
        /* 隐身模式忽略 */
      }
    },
    { deep: true }
  )

  const of = (id) => data.value[id] || []

  function add(id, item) {
    const list = data.value[id] || []
    list.unshift({ id: Date.now(), text: item.text || '', url: item.url || '', at: new Date().toISOString().slice(0, 10) })
    data.value = { ...data.value, [id]: list }
  }

  function remove(id, itemId) {
    const list = (data.value[id] || []).filter((x) => x.id !== itemId)
    data.value = { ...data.value, [id]: list }
  }

  const countOf = (id) => (data.value[id] || []).length
  const total = () => Object.values(data.value).reduce((a, b) => a + b.length, 0)

  return { data, of, add, remove, countOf, total }
})
