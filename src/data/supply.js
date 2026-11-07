/**
 * 补给与撤离：把途经点的 sup / camp / tips 拆成可读的结构化信息。
 * 判断都基于数据里已有的文字，不臆造具体电话号码或医院名称。
 */

const has = (s, words) => words.some((w) => s.includes(w))

export function supplyPlan(r) {
  const pts = r.waypoints || []
  const dist = Number(r.distance) || 0

  const items = pts.map((p, i) => {
    const sup = p.sup || ''
    const note = p.note || ''
    const text = sup + note
    return {
      i,
      name: p.name,
      km: p.km,
      ele: p.ele,
      camp: !!p.camp,
      hasSup: !!sup,
      // 有溪泉算能接水；有小卖部/农家乐/客栈则至少能买瓶装水
      water: has(text, ['水', '溪', '泉', '井', '小卖部', '农家', '客栈']),
      food: has(text, ['吃', '餐', '小卖部', '农家', '客栈', '饭']),
      bed: has(text, ['客栈', '住宿', '农家', '营地']),
      signal: p.ele >= 1200 ? '多数有（山顶/垭口）' : has(text, ['峡谷', '谷底']) ? '弱或无' : '不稳定',
      note: sup || note || '无补给，通过即可'
    }
  })

  const withSup = items.filter((x) => x.hasSup)
  const lastSup = withSup.length ? withSup[withSup.length - 1] : null
  const waterPoints = items.filter((x) => x.water)
  const gapToEnd = lastSup ? +(dist - lastSup.km).toFixed(1) : dist

  // 撤离：每个节点回到起点的里程与耗时（按 3km/h、含 15% 绕行）
  const exits = items.map((x) => {
    const back = +(x.km * 1.15).toFixed(1)
    const hours = back > 0 ? Math.max(0.3, back / 3) : 0
    let way
    if (x.i === 0) way = '起点，无需撤离'
    else if (x.hasSup) way = '沿来路或机耕道下撤，回到有车的地方'
    else if (x.camp) way = '从营地原路下撤到最近补给点'
    else way = '原路返回最近一个有补给的点'
    return {
      name: x.name,
      km: x.km,
      way,
      back,
      hours: !hours ? '—' : hours >= 1 ? `${hours.toFixed(1)} 小时` : `${Math.round(hours * 60)} 分钟`,
      transport: x.i === 0 ? (r.access?.car || '—') : x.hasSup ? '到村口后可叫车/摩托接驳' : '无车，只能走回'
    }
  })

  // 水计划：按里程 + 爬升估行程（r.hours 存的是「2 天」这类时长文案，不能直接当小时）
  const hours = (Number(r.distance) || 0) / 3.2 + (Number(r.climb) || 0) / 500
  const totalWater = Math.min(4.5, Math.max(0.5, Math.round((hours || 6) * 0.45 * 2) / 2))
  const firstWater = waterPoints.find((x) => x.km > 0)
  const carryFromStart = firstWater ? Math.min(2, totalWater) : totalWater

  return {
    items,
    lastSup,
    waterPoints,
    gapToEnd,
    exits,
    water: {
      total: totalWater,
      carry: carryFromStart,
      firstAt: firstWater ? `${firstWater.name}（${firstWater.km}km）` : '全程无可靠水源'
    },
    signalNote: has(String(r.tips || ''), ['无信号', '无人区'])
      ? '中段基本无手机信号，别把导航全押在手机上'
      : '山谷与密林段信号会掉，关键路口先存离线轨迹'
  }
}
