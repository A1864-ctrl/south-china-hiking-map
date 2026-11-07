import { spots } from './spots.js'
import { routes } from './routes.js'

export const cityMeta = {
  桂林: { province: '广西', center: [25.27, 110.29], tagline: '山水甲天下，梯田与漓江都能徒步', season: '4-10月' },
  广州: { province: '广东', center: [23.13, 113.26], tagline: '城市山林与从化乡村线，周末就能出发', season: '10-4月' },
  深圳: { province: '广东', center: [22.55, 114.06], tagline: '海岸线资源最好的城市，东西冲最好走', season: '10-4月' },
  长沙: { province: '湖南', center: [28.23, 112.94], tagline: '岳麓山下的烟火气，周边多是千米山', season: '3-5月/9-11月' },
  湘西: { province: '湖南', center: [28.31, 109.74], tagline: '古城、峡谷与苗寨，玩法密度很高', season: '4-10月' },
  张家界: { province: '湖南', center: [29.12, 110.48], tagline: '峰林天花板，景区线够走三天', season: '4-10月' },
  惠州: { province: '广东', center: [23.11, 114.42], tagline: '山、海、温泉三种玩法一城打包', season: '10-5月' },
  郴州: { province: '湖南', center: [25.77, 113.02], tagline: '雾漫小东江与丹霞山脊，性价比高', season: '4-10月' },
  韶关: { province: '广东', center: [24.81, 113.60], tagline: '船底顶与丹霞山，广东最硬的山都在这里', season: '10-12月' },
  衡阳: { province: '湖南', center: [26.89, 112.57], tagline: '南岳衡山，石阶古道与祝融峰云海', season: '全年' },
  清远: { province: '广东', center: [23.68, 113.05], tagline: '英西峰林与八排山，喀斯特与草甸并存', season: '10-4月' }
}

const maxSpots = Math.max(
  ...Object.keys(cityMeta).map((c) => spots.filter((s) => s.city === c).length)
)

export const cityStats = Object.keys(cityMeta).map((name) => {
  const citySpots = spots.filter((s) => s.city === name)
  const cityRoutes = routes.filter((r) => r.city === name)
  const spotAvg = citySpots.length
    ? Math.round(citySpots.reduce((a, s) => a + s.heat, 0) / citySpots.length)
    : 0
  const routeAvg = cityRoutes.length
    ? Math.round(cityRoutes.reduce((a, r) => a + r.heat, 0) / cityRoutes.length)
    : 0
  const index = Math.round(
    0.4 * spotAvg + 0.3 * routeAvg + 0.3 * (citySpots.length / maxSpots) * 100
  )
  return {
    name,
    ...cityMeta[name],
    spotCount: citySpots.length,
    routeCount: cityRoutes.length,
    spotAvg,
    routeAvg,
    index,
    totalKm: +cityRoutes.reduce((a, r) => a + r.distance, 0).toFixed(1),
    topSpot: citySpots.slice().sort((a, b) => b.heat - a.heat)[0],
    topRoute: cityRoutes.slice().sort((a, b) => b.heat - a.heat)[0]
  }
}).sort((a, b) => b.index - a.index)

export const cityNames = Object.keys(cityMeta)

export const overview = {
  spotCount: spots.length,
  routeCount: routes.length,
  cityCount: Object.keys(cityMeta).length,
  totalKm: +routes.reduce((a, r) => a + r.distance, 0).toFixed(0),
  totalClimb: routes.reduce((a, r) => a + r.climb, 0),
  hardest: routes.slice().sort((a, b) => b.climb - a.climb)[0],
  hottest: routes.slice().sort((a, b) => b.heat - a.heat)[0],
  topCity: cityStats[0]
}
