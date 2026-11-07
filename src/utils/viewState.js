/**
 * 列表页的「记忆」：筛选条件 + 滚动位置。
 *
 * 从列表点进详情、再点返回时，用户期待回到刚才那屏，
 * 而不是回到顶部、筛选被清空。这里用 module 级对象 + sessionStorage 双写：
 * 同一会话内的前进后退走内存（快），刷新页面还能从 sessionStorage 恢复。
 */
const mem = {}
const PREFIX = 'yj:view:'

export function saveView(key, value) {
  mem[key] = value
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    /* 隐私模式下 sessionStorage 会抛错，忽略即可 */
  }
}

export function loadView(key) {
  if (mem[key]) return mem[key]
  try {
    const raw = sessionStorage.getItem(PREFIX + key)
    if (!raw) return null
    const v = JSON.parse(raw)
    mem[key] = v
    return v
  } catch {
    return null
  }
}

export function clearView(key) {
  delete mem[key]
  try {
    sessionStorage.removeItem(PREFIX + key)
  } catch {
    /* ignore */
  }
}
