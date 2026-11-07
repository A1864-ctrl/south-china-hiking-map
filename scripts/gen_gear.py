# -*- coding: utf-8 -*-
"""把 户外装备清单.html 的 74 项装备转成 src/data/gear.js。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(ROOT, 'scripts', '_gear_raw.json'), encoding='utf-8'))

GROUP_ORDER = ['着装系统', '背负系统', '宿营睡眠系统', '行进辅助装备', '饮食水具系统',
               '导航通讯照明电源', '急救与安全防护', '个人杂物洗漱证件']
GROUP_DESC = {
    '着装系统': '三层穿衣：排汗层保持干爽、保暖层锁温、防护层挡风挡雨；鞋子按路线难度选，新鞋一定提前磨合',
    '背负系统': '背包容量按天数选，防雨罩和防水袋是南方多雨的必配',
    '宿营睡眠系统': '只在上山过夜时才需要；温标按当地夜间最低温再留 5℃ 余量',
    '行进辅助装备': '登山杖与护膝直接决定膝盖能用几年，长下坡路线几乎必带',
    '饮食水具系统': '水按里程和爬升估，炊具只在露营时带，气罐不能上高铁和飞机',
    '导航通讯照明电源': '头灯是保命的，手机离线轨迹提前下好，山里没信号是常态',
    '急救与安全防护': '急救包和保温毯体积小、重量轻，没有任何理由不带',
    '个人杂物洗漱证件': '垃圾全部带走；山区没有移动支付，证件和现金要带'
}

lines = ['// 户外徒步装备清单：74 项，按 8 大系统分类，3 种场景',
         '// 数据来源：用户提供的《户外装备清单》，补充了「为什么带」与路线适配逻辑',
         'export const GEAR = [']
for it in raw:
    group, _, sub = it['category'].partition('-')
    lines.append('  { id: %d, group: %r, sub: %r, name: %r, req: %s, scenes: %r, note: %r },'
                 % (it['id'], group, sub, it['name'],
                    'true' if it['required'] else 'false',
                    it['scene'], it['remark']))
lines.append(']')
lines.append('')
lines.append('export const GEAR_GROUPS = %r' % (GROUP_ORDER,))
lines.append('')
lines.append('export const GROUP_DESC = {')
for g in GROUP_ORDER:
    lines.append('  %r: %r,' % (g, GROUP_DESC[g]))
lines.append('}')
lines.append('')
lines.append("export const SCENES = [")
lines.append("  { k: '单日徒步', label: '单日徒步', desc: '当天往返，20-30L 背包，轻装快走' },")
lines.append("  { k: '重装露营', label: '重装露营', desc: '背帐篷睡袋上山过夜，40-60L 背包' },")
lines.append("  { k: '长线高难度', label: '长线高难度', desc: '2 天以上或技术地形，负重与风险都上一档' }")
lines.append("]")
lines.append('')
lines.append('/** 按场景取装备，required 为必带 */')
lines.append('export function gearByScene(scene) {')
lines.append("  return GEAR.filter((it) => !scene || scene === 'all' || it.scenes.includes(scene))")
lines.append('}')
lines.append('')
open(os.path.join(ROOT, 'src', 'data', 'gear.js'), 'w', encoding='utf-8').write('\n'.join(lines))
print('gear.js written', len(raw), 'items')
