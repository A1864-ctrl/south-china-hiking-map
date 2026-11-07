/**
 * 宽松搜索：输入一个字就能命中所有含这个字的内容。
 * 规则：
 *  1. 整串连续包含 → 直接命中（"武功" 命中 "武功山"）
 *  2. 否则按字拆开，要求每个字都出现（"武功山" 也能命中 "山·武功"、"武 功"）
 *  3. 英文/数字忽略大小写
 */
export function matchLoose(text, query) {
  const q = String(query || '').trim().toLowerCase().replace(/\s+/g, '')
  if (!q) return true
  const h = String(text || '').toLowerCase()
  if (!h) return false
  if (h.includes(q)) return true
  for (const ch of q) {
    if (!h.includes(ch)) return false
  }
  return true
}

/** 把若干字段拼成一个可搜字符串 */
export function haystack(...fields) {
  const out = []
  const push = (v) => {
    if (v == null) return
    if (Array.isArray(v)) v.forEach(push)
    else out.push(String(v))
  }
  fields.forEach(push)
  return out.join(' ')
}
