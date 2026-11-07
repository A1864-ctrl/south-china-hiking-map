/**
 * 营地独立库
 * ─ 坐标不手写，全部从对应路线的途经点取，保证营地落在真实轨迹上
 * ─ 五项关键信息：明火 / 水源 / 厕所 / 收费 / 过夜权限
 */
import { routes } from './routes.js'
import { routePhotoOf } from './photos.js'

const R = Object.fromEntries(routes.map((r) => [r.id, r]))

function at(rid, wn) {
  const r = R[rid]
  if (!r || !r.waypoints || !r.waypoints.length) return { lat: 23.1, lng: 113.3, ele: 0 }
  const w = r.waypoints.find((x) => x.name === wn) || r.waypoints[0]
  return { lat: w.lat, lng: w.lng, ele: w.ele, km: w.km || 0 }
}

function cover(rid) {
  const r = R[rid]
  if (!r) return ''
  const p = routePhotoOf(r, r.terrain)
  return p ? p.src : ''
}

const RAW = [
  {
    id: 'c01', rid: 1, wp: '坪坑坳营地', name: '坪坑坳营地', city: '韶关', kind: '高山草甸',
    fire: '限指定区域', water: '季节性溪水（需过滤）', toilet: '无', fee: '免费', night: '可过夜',
    cap: 10, wind: '中等', note: '船底顶传统 D1 营地，避风，草甸平整可容 10 顶。溪水雨季有水、旱季断流。',
    tags: ['风口下方', '看日出 15 分钟']
  },
  {
    id: 'c02', rid: 1, wp: '船底顶主峰', name: '船底顶主峰草甸', city: '韶关', kind: '山顶草甸',
    fire: '禁止', water: '无（需背水）', toilet: '无', fee: '免费', night: '可过夜',
    cap: 8, wind: '极大', note: '1586 米主峰东南侧草甸，日出机位就在帐篷门口。风大，必须石堆压帐，禁止明火。',
    tags: ['日出机位', '无水源']
  },
  {
    id: 'c03', rid: 3, wp: '大南山草甸', name: '大南山草甸营地', city: '惠州', kind: '高山草甸',
    fire: '限指定区域', water: '山泉（雨后）', toilet: '无', fee: '免费', night: '可过夜',
    cap: 12, wind: '中等', note: '惠东大南山最经典的露营草甸，坡度缓，适合新手第一次野营。周末人多，建议靠东侧。',
    tags: ['新手友好', '草甸']
  },
  {
    id: 'c04', rid: 6, wp: '高洋尾沙滩', name: '高洋尾沙滩营地', city: '惠州', kind: '海岸沙滩',
    fire: '禁止', water: '无', toilet: '无', fee: '免费', night: '需报备', cap: 15,
    wind: '大（海风）', note: '黑排角穿越的中途沙滩，沙地打钉要用长地钉。涨潮线以上扎营，注意夜间潮位。',
    tags: ['听海', '长地钉']
  },
  {
    id: 'c05', rid: 8, wp: '西涌沙滩', name: '大鹿港沙滩营地', city: '深圳', kind: '海岸沙滩',
    fire: '禁止', water: '无（村口可买）', toilet: '有（季节性）', fee: '¥30/顶', night: '可过夜',
    cap: 20, wind: '大（海风）', note: '大鹿港无人沙滩，夏季有简易管理点收费。海风夹沙，帐篷要拉满风绳。',
    tags: ['收费营地', '有厕所']
  },
  {
    id: 'c06', rid: 18, wp: '大雾山', name: '八排山·大雾山营地', city: '清远', kind: '高山草甸',
    fire: '限指定区域', water: '山溪（需过滤）', toilet: '无', fee: '免费', night: '可过夜',
    cap: 10, wind: '大', note: '连州八排山 D1 营地，海拔 1290 米，草甸背风处可扎 10 顶。夜间温差可达 12℃。',
    tags: ['避风', '温差大']
  },
  {
    id: 'c07', rid: 20, wp: '八宝山营地', name: '南岭·八宝山营地', city: '韶关', kind: '林间平地',
    fire: '禁止', water: '溪流（需过滤）', toilet: '旱厕', fee: '免费', night: '需报备', cap: 8,
    wind: '小（林内）', note: '石坑崆南北穿越的中间营地，林间平地，林冠挡风。属保护区范围，进山需登记。',
    tags: ['林间', '需登记']
  },
  {
    id: 'c08', rid: 17, wp: '半山瀑布', name: '云髻山半山营地', city: '韶关', kind: '溪谷',
    fire: '禁止', water: '瀑布溪流（需过滤）', toilet: '无', fee: '免费', night: '可过夜', cap: 6,
    wind: '小', note: '瀑布下方小片平地，潮湿，蚊虫多。雨后水位上涨快，不要在河床正中扎营。',
    tags: ['近水', '潮湿']
  },
  {
    id: 'c09', rid: 30, wp: '鬼子寨', name: '莽山·鬼子寨营地', city: '郴州', kind: '林间平地',
    fire: '禁止', water: '溪流（需过滤）', toilet: '有（景区）', fee: '¥50/顶', night: '需报备', cap: 12,
    wind: '小', note: '莽山景区内指定露营点，需在入口登记。有管理人员，禁止一切明火。',
    tags: ['景区指定', '有厕所']
  },
  {
    id: 'c10', rid: 33, wp: '七星岭', name: '大围山·七星岭营地', city: '长沙', kind: '山顶草甸',
    fire: '限指定区域', water: '无（需背水）', toilet: '无', fee: '免费', night: '可过夜', cap: 8,
    wind: '极大', note: '海拔 1608 米，视野开阔但完全暴露。看日出极好，风大时建议下撤到栗木桥。',
    tags: ['日出', '暴露']
  },
  {
    id: 'c11', rid: 34, wp: '千家洞', name: '韭菜岭·千家洞营地', city: '永州', kind: '溪谷',
    fire: '禁止', water: '溪流（充足）', toilet: '无', fee: '免费', night: '可过夜', cap: 14,
    wind: '小', note: '湖南驴友「毕业线」韭菜岭的 D1 营地，水源充足、地势平缓，是全线最好的扎营点。',
    tags: ['水源充足', '经典营地']
  },
  {
    id: 'c12', rid: 36, wp: '天平山', name: '八大公山·天平山营地', city: '张家界', kind: '林间平地',
    fire: '禁止', water: '山泉', toilet: '无', fee: '免费', night: '需报备', cap: 10,
    wind: '小', note: '原始森林腹地，保护区核心区边缘，进山须报备。地面腐殖层厚，地钉容易松。',
    tags: ['原始林', '需报备']
  },
  {
    id: 'c13', rid: 46, wp: '金顶', name: '武功山·金顶营地', city: '萍乡', kind: '山顶草甸',
    fire: '禁止', water: '客栈可买', toilet: '有（客栈）', fee: '¥80/顶', night: '可过夜', cap: 40,
    wind: '大', note: '金顶石碑下方草甸，商业化程度最高：有客栈、热水、租帐篷。旺季要提前订。',
    tags: ['可补给', '人多']
  },
  {
    id: 'c14', rid: 46, wp: '发云界', name: '武功山·发云界营地', city: '萍乡', kind: '高山草甸',
    fire: '限指定区域', water: '客栈水龙头', toilet: '旱厕', fee: '¥60/顶', night: '可过夜', cap: 30,
    wind: '大', note: '发云界是看云海概率最高的一段，营地沿山脊分布。夜里风大，注意帐杆。',
    tags: ['云海', '有旱厕']
  },
  {
    id: 'c15', rid: 51, wp: '药王庙', name: '太白山·药王庙营地', city: '宝鸡', kind: '高山草甸',
    fire: '禁止', water: '山泉（需过滤）', toilet: '无', fee: '免费', night: '需报备', cap: 15,
    wind: '大', note: '太白山南北穿越 D1 营地，海拔 2800 米。夜间可到 0℃ 以下，四季帐必备。',
    tags: ['高海拔', '需报备']
  },
  {
    id: 'c16', rid: 53, wp: '上雨崩', name: '雨崩·上雨崩营地', city: '迪庆', kind: '村边平地',
    fire: '禁止', water: '村内自来水', toilet: '有（客栈）', fee: '¥50/顶', night: '可过夜', cap: 25,
    wind: '小', note: '上雨崩村口平地，可望梅里雪山。村内可补给、有热食，是全线最舒服的一晚。',
    tags: ['看雪山', '可补给']
  },
  {
    id: 'c17', rid: 52, wp: '28 道拐', name: '虎跳峡·28 道拐平台', city: '香格里拉', kind: '山腰平台',
    fire: '禁止', water: '无', toilet: '无', fee: '免费', night: '禁止过夜', cap: 0,
    wind: '大', note: '高路徒步的观景平台，路面窄、下方是崖，不具备扎营条件，只作休息点。',
    tags: ['仅休息', '禁露营']
  },
  {
    id: 'c18', rid: 49, wp: '光明顶', name: '黄山·天海营地', city: '黄山', kind: '山顶平台',
    fire: '禁止', water: '有（公共）', toilet: '有', fee: '¥200+/位', night: '限指定营地', cap: 60,
    wind: '大', note: '黄山全山禁止野外扎营，只能住山上酒店或指定帐篷位。看日出方便，价格高。',
    tags: ['仅指定营地', '贵']
  },
  {
    id: 'c19', rid: 50, wp: '南峰', name: '华山·南峰（禁露营）', city: '渭南', kind: '山顶平台',
    fire: '禁止', water: '有（售卖）', toilet: '有', fee: '—', night: '禁止过夜', cap: 0,
    wind: '极大', note: '华山全线禁止露营，南峰只可夜间观日出后下山。护栏外即悬崖，切勿翻越。',
    tags: ['禁露营', '看日出']
  },
  {
    id: 'c20', rid: 21, wp: '草甸鞍部', name: '万时山·三省界营地', city: '韶关', kind: '高山草甸',
    fire: '限指定区域', water: '山泉（季节性）', toilet: '无', fee: '免费', night: '可过夜', cap: 12,
    wind: '大', note: '粤湘赣三省交界草甸，鞍部背风。旱季水源不稳，建议从城口镇背足 3L。',
    tags: ['三省界', '水源不稳']
  },
  {
    id: 'c21', rid: 35, wp: '酃峰', name: '酃峰·山顶营地', city: '株洲', kind: '山顶草甸',
    fire: '禁止', water: '无（需背水）', toilet: '无', fee: '免费', night: '可过夜', cap: 6,
    wind: '极大', note: '湖南最高峰 2115 米，山顶风大无遮挡。看日出首选，但只适合有经验队伍。',
    tags: ['湖南最高', '无水源']
  },
  {
    id: 'c22', rid: 37, wp: '壶瓶山主峰', name: '壶瓶山·主峰营地', city: '常德', kind: '山顶草甸',
    fire: '禁止', water: '无（需背水）', toilet: '无', fee: '免费', night: '需报备', cap: 6,
    wind: '极大', note: '湖南屋脊 2099 米，保护区核心区，须提前报备。全程无补给，重装 3 天水量。',
    tags: ['需报备', '重装']
  }
]

export const camps = RAW.map((c) => {
  const r = R[c.rid]
  return {
    ...c,
    routeName: r ? r.name : '',
    ...at(c.rid, c.wp),
    photo: cover(c.rid)
  }
})

export const CAMP_FILTERS = {
  fire: ['允许', '限指定区域', '禁止'],
  night: ['可过夜', '需报备', '限指定营地', '禁止过夜'],
  water: ['有水源', '无水源']
}

export const campStats = {
  total: camps.length,
  free: camps.filter((c) => c.fee === '免费').length,
  fireOk: camps.filter((c) => c.fire === '允许' || c.fire === '限指定区域').length,
  water: camps.filter((c) => !c.water.startsWith('无')).length,
  toilet: camps.filter((c) => c.toilet !== '无').length,
  nightOk: camps.filter((c) => c.night === '可过夜' || c.night === '限指定营地').length
}
