// 全局轻提示
import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', () => {
  const message = ref('')
  let timer = null

  function toast(text, ms = 2200) {
    message.value = text
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      message.value = ''
      timer = null
    }, ms)
  }

  return { message, toast }
})
