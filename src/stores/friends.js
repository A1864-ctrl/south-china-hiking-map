/**
 * 好友系统：搜索山友 → 发申请 → 对方同意 → 成为好友。
 * 数据在云数据库 friendships 表（0 待处理 / 1 已同意 / 2 已拒绝），资料摘要来自 user_profiles 公开读。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { cloud } from '../services/cloud.js'
import { useAuthStore } from './auth.js'
import { regionShort } from '../data/regions.js'

/** avatar_path → 签名 URL 的会话级缓存 */
const urlCache = new Map()
async function avatarOf(path) {
  if (!path) return ''
  if (urlCache.has(path)) return urlCache.get(path)
  try {
    const signed = await cloud.storage.createSignedUrl(path, 3600)
    const url = signed?.data?.signedUrl || signed?.data?.url || ''
    urlCache.set(path, url)
    return url
  } catch {
    return ''
  }
}

/** 把 user_profiles 行转成展示摘要 */
function toSummary(row) {
  return {
    id: row.owner_id,
    nickname: row.nickname || '山友',
    bio: row.bio || '',
    region: regionShort(row.region_province, row.region_city),
    gender: row.gender || 0,
    avatarPath: row.avatar_path || ''
  }
}

export const useFriendsStore = defineStore('friends', () => {
  const auth = useAuthStore()

  const list = ref([]) // 好友 [{ uid, summary, since }]
  const incoming = ref([]) // 收到的申请 [{ rid, uid, summary, at }]
  const outgoing = ref([]) // 我发出的申请 [{ rid, uid, summary, at }]
  const loaded = ref(false)
  const loading = ref(false)

  const searching = ref(false)
  const results = ref([]) // 搜索结果 [{ uid, summary, state: none|pending_out|pending_in|friends|self }]
  const searched = ref(false)

  const count = computed(() => list.value.length)

  /** 拉一份资料摘要（批量），返回 { id -> summary } */
  async function profilesOf(ids) {
    const out = {}
    if (!ids.length) return out
    const { data, error } = await cloud.database
      .from('user_profiles')
      .select('owner_id,nickname,bio,region_province,region_city,gender,avatar_path')
      .in('owner_id', ids)
    if (!error && data) {
      for (const row of data) {
        out[row.owner_id] = toSummary(row)
      }
    }
    // 没建资料行的用户兜底显示
    for (const id of ids) {
      if (!out[id]) out[id] = { id, nickname: '山友', bio: '', region: '', gender: 0, avatarPath: '' }
    }
    await Promise.all(Object.values(out).map(async (s) => (s.avatar = await avatarOf(s.avatarPath))))
    return out
  }

  /** 加载我的好友与申请 */
  async function load() {
    if (!auth.isLogged) return
    loading.value = true
    try {
      const me = auth.account
      const { data, error } = await cloud.database
        .from('friendships')
        .select('*')
        .or(`requester_id.eq.${me},addressee_id.eq.${me}`)
      if (error) throw error
      const rows = data || []
      const otherIds = [...new Set(rows.map((r) => (r.requester_id === me ? r.addressee_id : r.requester_id)))]
      const profiles = await profilesOf(otherIds)

      const friends = []
      const inReq = []
      const outReq = []
      for (const r of rows) {
        const otherId = r.requester_id === me ? r.addressee_id : r.requester_id
        if (r.status === 1) {
          friends.push({ uid: otherId, summary: profiles[otherId], since: r.responded_at || r.created_at })
        } else if (r.status === 0) {
          if (r.addressee_id === me) inReq.push({ rid: r.id, uid: otherId, summary: profiles[otherId], at: r.created_at })
          else outReq.push({ rid: r.id, uid: otherId, summary: profiles[otherId], at: r.created_at })
        }
        // status 2（已拒绝）不留存展示
      }
      friends.sort((a, b) => String(b.since).localeCompare(String(a.since)))
      list.value = friends
      incoming.value = inReq
      outgoing.value = outReq
      loaded.value = true
    } catch {
      /* 网络问题下次再拉 */
    } finally {
      loading.value = false
    }
  }

  /**
   * 搜索山友：昵称模糊匹配或账号 ID 精确匹配（登录用户可读 user_profiles）。
   * 返回带关系状态的结果，供按钮展示「加好友 / 已申请 / 已是好友 / 同意」。
   */
  async function search(q) {
    const kw = String(q || '').trim()
    results.value = []
    searched.value = true
    if (!kw) return
    searching.value = true
    try {
      const me = auth.account
      const isId = /^\d{10,}$/.test(kw)
      const { data, error } = isId
        ? await cloud.database.from('user_profiles').select('*').eq('owner_id', kw).limit(10)
        : await cloud.database.from('user_profiles').select('*').ilike('nickname', `%${kw}%`).limit(20)
      if (error) throw error
      const rows = (data || []).filter((r) => r.owner_id !== me)
      if (isId) {
        // 按精确 ID 搜但对方没建过资料行：也允许发起申请
        if (!rows.length) rows.push({ owner_id: kw, nickname: '山友', bio: '', region_province: '', region_city: '', gender: 0, avatar_path: '' })
      }
      const summaries = await profilesOf(rows.map((r) => r.owner_id))
      const friendIds = new Set(list.value.map((f) => f.uid))
      const outIds = new Set(outgoing.value.map((o) => o.uid))
      const inIds = new Set(incoming.value.map((o) => o.uid))
      results.value = rows.map((r) => ({
        uid: r.owner_id,
        summary: summaries[r.owner_id],
        state: friendIds.has(r.owner_id) ? 'friends' : outIds.has(r.owner_id) ? 'pending_out' : inIds.has(r.owner_id) ? 'pending_in' : 'none'
      }))
    } finally {
      searching.value = false
    }
  }

  /** 发送好友申请；重复申请 / 已是好友 / 对方已申请我都给可读提示 */
  async function add(uid) {
    const me = auth.account
    if (uid === me) throw new Error('不能添加自己为好友')
    const mine = list.value.some((f) => f.uid === uid)
    if (mine) throw new Error('你们已经是好友了')
    // 对方已向我申请：直接替对方同意，两步并一步
    const reverse = incoming.value.find((o) => o.uid === uid)
    if (reverse) {
      await respond(reverse.rid, 1)
      return { autoAccepted: true }
    }
    const { error } = await cloud.database
      .from('friendships')
      .insert({ requester_id: me, addressee_id: uid, status: 0 })
      .select()
      .single()
    if (error) {
      if (/duplicate|unique/i.test(error.message || '')) throw new Error('已经发送过好友申请，等对方处理')
      throw error
    }
    await load()
  }

  /** 处理收到的申请：1 同意 / 2 拒绝 */
  async function respond(rid, status) {
    const { error } = await cloud.database
      .from('friendships')
      .update({ status, responded_at: new Date().toISOString() })
      .eq('id', rid)
    if (error) throw error
    await load()
  }

  /** 删除好友 / 撤回我的申请 */
  async function removeFriend(uid) {
    const me = auth.account
    const { error } = await cloud.database
      .from('friendships')
      .delete()
      .or(`and(requester_id.eq.${me},addressee_id.eq.${uid}),and(requester_id.eq.${uid},addressee_id.eq.${me})`)
    if (error) throw error
    await load()
  }

  /** 清空（退出登录时） */
  function reset() {
    list.value = []
    incoming.value = []
    outgoing.value = []
    results.value = []
    searched.value = false
    loaded.value = false
  }

  return {
    list,
    incoming,
    outgoing,
    loaded,
    loading,
    searching,
    results,
    searched,
    count,
    load,
    search,
    add,
    respond,
    removeFriend,
    reset
  }
})
