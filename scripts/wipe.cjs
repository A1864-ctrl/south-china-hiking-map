/**
 * wipe.js —— 逐文件清空指定目录（用于整体转运失败的缓存目录）。
 * 用法：node scripts/wipe.js <目录1> [目录2] ...
 * 只清指定目录，不做任何递归外溢；删除前打印目标。
 */
const fs = require('fs')
const path = require('path')

function walkFiles(d) {
  let out = []
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name)
    if (e.isDirectory()) out = out.concat(walkFiles(p))
    else out.push(p)
  }
  return out
}

function rmdirDeep(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name)
    if (e.isDirectory()) rmdirDeep(p)
    else fs.rmSync(p, { force: true })
  }
  fs.rmdirSync(d)
}

const targets = process.argv.slice(2)
for (const t of targets) {
  const abs = path.resolve(t)
  if (!fs.existsSync(abs)) {
    console.log('SKIP(不存在)', t)
    continue
  }
  const st = fs.statSync(abs)
  if (st.isFile()) {
    fs.rmSync(abs, { force: true })
    console.log('OK(文件)', t)
    continue
  }
  const files = walkFiles(abs)
  let ok = 0
  let fail = 0
  let failSample = ''
  for (const f of files) {
    try {
      fs.rmSync(f, { force: true })
      ok++
    } catch (e) {
      fail++
      if (!failSample) failSample = `${f} :: ${e.code || e.message.slice(0, 50)}`
    }
  }
  if (fail === 0) {
    try {
      rmdirDeep(abs)
      console.log(`OK ${t}（${ok} 个文件已清，目录已移除）`)
    } catch (e) {
      console.log(`PARTIAL ${t}（文件已清 ${ok} 个，空目录壳移除失败：${e.code || e.message.slice(0, 40)}）`)
    }
  } else {
    console.log(`PARTIAL ${t}（ok=${ok} fail=${fail} 样例: ${failSample}）`)
  }
}
