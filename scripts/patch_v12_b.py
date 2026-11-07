# -*- coding: utf-8 -*-
"""v12 补丁 B：CSS —— 性别/地区特异性修复、弹窗自适应、封面提示、头像可点"""
import io

P = 'src/views/MeView.vue'
s = io.open(P, encoding='utf-8').read()
orig_len = len(s)
applied = []


def rep(old, new, tag, count=1):
    global s
    n = s.count(old)
    assert n == count, f'[{tag}] 期望 {count} 次，实际 {n} 次'
    s = s.replace(old, new)
    applied.append(tag)


# ── 1) .dlg 自适应：限高 + 内滚 ──
rep(
    """.dlg {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 8px;
  padding: 22px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
}""",
    """.dlg {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 8px;
  padding: 22px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}""",
    'D1-dlg-scroll',
)

# ── 2) edit-dlg 宽度跟随视口 ──
rep(
    """.edit-dlg {
  text-align: left;
  max-width: 460px;
}""",
    """.edit-dlg {
  text-align: left;
  width: 100%;
  max-width: min(460px, calc(100vw - 32px));
}""",
    'D2-edit-width',
)

# ── 3) 性别 / 地区：特异性压过 .dlg label span 的 display:block ──
rep(
    """.ed-genders {
  display: flex;
  gap: 6px;
  flex: 1;
}
.ed-genders button {
  flex: 1;
  border: 1px solid var(--line);
  background: #fcfaf5;
  border-radius: 5px;
  padding: 7px 0;
  font-size: 0.72rem;
  color: var(--gray);
  cursor: pointer;
  transition: 0.16s;
}
.ed-genders button.on {
  border-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
}
.ed-region {
  display: flex;
  gap: 6px;
  flex: 1;
}
.ed-region select {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 8px 8px;""",
    """.edit-dlg .ed-genders {
  display: flex;
  gap: 10px;
  flex: 1;
  margin-bottom: 0;
}
.edit-dlg .ed-genders button {
  flex: 1;
  border: 1px solid var(--line);
  background: #fcfaf5;
  border-radius: 5px;
  padding: 7px 0;
  font-size: 0.72rem;
  color: var(--gray);
  cursor: pointer;
  transition: 0.16s;
}
.edit-dlg .ed-genders button.on {
  border-color: var(--forest);
  background: var(--forest-soft);
  color: var(--forest-dark);
}
.edit-dlg .ed-region {
  display: flex;
  gap: 8px;
  flex: 1;
  margin-bottom: 0;
}
.edit-dlg .ed-region select {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 8px 8px;""",
    'D3-gender-region-fix',
)

# ── 4) 新增：封面点击提示 / 头像可点 / 大背景行 / 备注 / 响应式 ──
css = """
/* ══════════ v12：大背景直换 / 头像直点 / 弹窗自适应 ══════════ */
.cover {
  cursor: pointer;
}
.cover button,
.cover a,
.cover figure {
  cursor: pointer;
}
.band-hint {
  position: absolute;
  right: 16px;
  bottom: 12px;
  z-index: 6;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(16, 26, 19, 0.55);
  border: 1px solid rgba(232, 220, 192, 0.32);
  border-radius: 999px;
  padding: 4px 11px;
  opacity: 0;
  transition: 0.2s;
  pointer-events: none;
  letter-spacing: 0.04em;
}
.cover:hover .band-hint {
  opacity: 1;
}
.stamp {
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.stamp:hover {
  border-color: rgba(232, 220, 192, 0.95);
  background: rgba(246, 242, 233, 0.22);
}
.ed-note {
  grid-column: 1 / -1;
  font-size: 0.58rem;
  color: var(--gray-light);
  line-height: 1.8;
  margin-top: 6px;
}
.band-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 13px;
}
.ed-band {
  flex: 1;
  min-width: 0;
}
.ed-band > div {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ed-band .ed-note {
  margin-top: 7px;
}
@media (max-width: 640px) {
  .mask {
    padding: 12px;
  }
  .dlg {
    max-height: calc(100vh - 24px);
  }
  .edit-dlg {
    max-width: calc(100vw - 24px);
  }
  .ed-bgs {
    grid-template-columns: repeat(3, 1fr);
  }
  .ed-ava-row {
    flex-wrap: wrap;
  }
  .band-row {
    flex-direction: column;
    gap: 6px;
  }
}
"""
pos = s.rfind('</style>')
s = s[:pos] + css + '\n' + s[pos:]
applied.append('D4-css')

io.open(P, 'w', encoding='utf-8').write(s)
print('PART-B ok:', ', '.join(applied), f'({orig_len} -> {len(s)})')
