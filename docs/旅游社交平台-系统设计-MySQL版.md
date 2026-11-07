# 野径 · 旅行社交平台　系统设计（MySQL 版）

> 基线：2026-11-06 10:21 线上版（纯前端内容站：76 点位 / 53 路线 / 74 装备）
> 本次：在同一套内容与视觉体系上，补齐账号、收藏、社交与组队，后端落到 **Python + MySQL 8 + Redis**
> 配套数据库：`db/01_schema.sql`（23 表）、`db/02_seed.sql`（演示数据）、`db/03_queries.sql`（核心查询）

---

## 1. 产品定位与角色

一句话：把「查路线」变成「查 → 收藏 → 约人 → 一起走 → 回来发帖」。

| 角色 | 核心诉求 | 对应模块 |
|---|---|---|
| 游客 | 看内容、比路线 | 免登录浏览 / 搜索 / 地图 |
| 注册用户 | 存下来、留痕 | 收藏、足迹、我的页 |
| 内容作者 | 表达、涨粉 | 发帖、评论、点赞、关注、Feed |
| 组队者 | 找到强度匹配的人 | 找搭子、附近的人、私信 |
| 运营 | 审核、推荐、风控 | 后台审核、榜单、限流 |

## 2. 总体架构

```
客户端      Vue 3 SPA（PWA）       微信小程序（同源 API）
              │ HTTPS
接入层      CDN（静态 + 图片多规格）→ Nginx（TLS / gzip / limit_req / 灰度）
              │
应用层      FastAPI 单体分模块：auth | content | social | match | track | media
              │
中间层      Redis 7（会话 / 缓存 / GEO / 限流 / 队列）   Celery Worker（转码 / 扩散 / 审核）
              │
存储层      MySQL 8.0（InnoDB + 空间索引 + ngram 全文）   对象存储（原图 / GPX / geobuf）
```

单体优先，模块间用 `app/modules/*` 隔离，按领域边界预留拆分点。

## 3. 数据库设计（MySQL 8.0）

### 3.1 为什么从 PostgreSQL 改成 MySQL

| 维度 | PostgreSQL + PostGIS | MySQL 8.0（本次） |
|---|---|---|
| 空间能力 | PostGIS 最全（ST_DWithin、栅格、拓扑） | 空间索引 + `ST_Distance_Sphere` 足够覆盖「附近 / 视野 / 距离」三类需求 |
| 中文全文 | 需 zhparser 扩展 | 内置 `ngram` 分词器，开箱可用 |
| 部署与运维 | 需要装扩展、调参 | 云厂商 RDS 默认支持，答辩环境更易复现 |
| 代价 | — | 分区表不支持外键；空间函数只对点精确 |

结论：本系统的地理需求是「点附近、线相交、线长度」，MySQL 8 能覆盖，且部署成本更低。

### 3.2 表结构要点

完整 DDL 见 `db/01_schema.sql`，这里只讲设计取舍：

- **空间字段三件套**：`poi.geom POINT SRID 4326`、`trail.geom LINESTRING SRID 4326`、`trail.start_pt POINT SRID 4326`。
  额外存 `start_pt` 是因为 `ST_Distance_Sphere` 只对点精确，路线要参与「附近」排序就得有代表点。
- **bbox 四列**：`min_lat/max_lat/min_lng/max_lng`，让「视野内路线」先走普通 B-Tree，再对少量候选做 `ST_Intersects`。
- **多态收藏**：`favorite(user_id, target_type, target_id)` 联合主键，一张表覆盖景点 / 路线 / 帖子。
- **会话双写**：`user_session` 存 MySQL（持久 + 审计），`sess:{uid}:{jti}` 存 Redis（热路径）。
- **计数冗余**：`post.like_cnt / comment_cnt` 由触发器维护，另有定时任务按明细校正。
- **全文索引**：`FULLTEXT ... WITH PARSER ngram` 同时覆盖 `poi.name`、`trail.name`、`post.body`。

### 3.3 三条必须知道的限制

1. `SPATIAL INDEX` 的列必须 `NOT NULL`；
2. InnoDB 分区表不支持外键 —— `post` 暂不分区，量大后按 `created_at` 分区时需去掉 `fk_post_author`；
3. `ST_Distance_Sphere` 只接受点，线要用 bbox / 起点 / `ST_Length` 组合。

## 4. 前端设计

### 4.1 UI 思路

- 色彩沿用现有站点的自然色系：森林绿 `#2D5A3D`、砂岩 `#C4A35A`、米白 `#F6F2E9`，升级不断层。
- 8pt 栅格（8/16/24/32），内容最大宽 1320，正文行宽 ≤ 72ch，两档字重（400/500）+ 三档字号（13/15/20）。
- 组件用 Design Token（CSS 变量）+ 原子组件（Button / Card / Tag / Sheet / Skeleton），地图、编辑器、图集三个重组件单独分包。
- 暗色模式走 Token 双值 + `prefers-color-scheme`，图片加 6% 暗遮罩避免刺眼。

### 4.2 动效

| 场景 | 手段 | 参数 |
|---|---|---|
| 路由切换 | View Transitions API，降级 CSS fade + 6px 上移 | 180ms，`out-in` |
| 列表增删 / 筛选重排 | FLIP（First-Last-Invert-Play） | 240ms |
| 图片加载 | blurhash 占位 → 模糊图 → 原图，`content-visibility: auto` | LCP ≤ 2.5s |
| 滚动显现 | IntersectionObserver 一次性触发 | 12px + opacity |
| 点赞 | 心跳缩放 + Canvas 粒子 | 90ms，`prefers-reduced-motion` 关闭 |
| 双击看图 | LightBox 0.94 → 1 缩放入场 | 180ms，与现有站点一致 |

原则：动效只解释状态变化，全部 ≤ 300ms 且可被滚动打断。

### 4.3 交互

- 服务端状态用 TanStack Query（缓存 / 失效 / 重试），本地 UI 用 Pinia，两者不混。
- 乐观更新：点赞、收藏先改本地，失败回滚 + toast。
- 离线：发帖草稿写 IndexedDB，联网后 Background Sync 补发；地图瓦片 LRU。
- 长列表：无限滚动 + 虚拟列表（只渲染视口 ± 2 屏）。
- 无障碍：焦点环、`aria-live` 播报、键盘可达、`prefers-reduced-motion`。
- 性能预算：首屏 JS ≤ 180KB（gzip），图片 AVIF/WebP + srcset，CDN 预热。

## 5. 账号体系

### 5.1 注册与登录

```
POST /api/v1/auth/sms/code     → 60s 一次，验证码存 Redis sms:{phone}（哈希）TTL 300s
POST /api/v1/auth/register     → 昵称 / 手机或邮箱 / 密码（≥6 位）
POST /api/v1/auth/login        → 密码或验证码
POST /api/v1/auth/refresh      → 用 refresh 换新 access
POST /api/v1/auth/logout
```

- 密码 **Argon2id**（`time_cost=3, memory_cost=64MB, parallelism=4`），只存哈希。
- 账号唯一性由 `uk_user_phone` / `uk_user_email` 兜底，捕获 `Duplicate entry` 转成友好提示。
- 验证码错误 5 次锁 15 分钟（`rl:sms:{phone}`）。

### 5.2 双 Token

| 令牌 | 形态 | 有效期 | 存放 |
|---|---|---|---|
| access_token | JWT（`sub / jti / dev / exp`） | 15 分钟 | 内存（Pinia），不进 localStorage |
| refresh_token | 256bit 随机串 | 7 天（记住我 30 天） | HttpOnly + Secure + SameSite=Lax Cookie |

refresh **旋转**：换新时旧值立即失效；旧值被二次使用视为盗用，整设备下线。

### 5.3 会话在后端怎么持久化

**MySQL 存账、Redis 存热**，同一个 `jti` 串起来：

```sql
-- 登录：写入持久会话
INSERT INTO user_session (jti, user_id, device_id, ip, ua, expires_at)
VALUES (?, ?, ?, ?, ?, DATE_ADD(NOW(), INTERVAL 30 MINUTE));

-- 每次请求命中后的滑动续期（异步，不阻塞请求）
UPDATE user_session
SET last_seen_at = NOW(), expires_at = DATE_ADD(NOW(), INTERVAL 30 MINUTE)
WHERE jti = ? AND revoked_at IS NULL AND expires_at > NOW();
```

### 5.4 Redis 会话保持（30 分钟滑动过期）

```
登录成功
  ├─ Redis: SETEX sess:{uid}:{jti} 1800 {device, ip, ua, last_seen}
  └─ 返回 access + refresh

每次请求
  ├─ 验签 → 查 sess:{uid}:{jti}
  │    ├─ 命中 → EXPIRE 1800（滑动：只要 30 分钟内有访问就不断）
  │    └─ 未命中 → 401 → 前端静默 refresh
  └─ 放行

30 分钟无请求 → key 过期 → access 失效
  ├─ refresh 未过期 → 静默换新，用户无感
  └─ refresh 也过期 → 跳登录页，带 redirect 参数

Redis 故障 → 回源 user_session 重建键，登录态不丢
```

不用纯 JWT 的原因：JWT 自包含、无法撤销。改成「JWT 只验签 + Redis 存会话位」，同时获得无状态校验的性能与**踢人、在线统计、限并发**能力。

## 6. 社交功能

### 6.1 收藏

- 接口：`POST /favorites`（存在即忽略，幂等）、`DELETE /favorites`、`GET /favorites?type=&cursor=`
- 计数：Redis `HINCRBY cnt:fav {type}:{id}`，Celery 每 30s 批量落库；读优先缓存。
- 列表：游标分页（`created_at, id` 复合游标），避免深 `OFFSET`。

### 6.2 发帖与 Feed

- 发布：正文 + ≤9 图 + 关联路线/景点；图片预签名直传对象存储，异步转三档尺寸。
- **推拉结合**：
  - 粉丝 < 5000：写扩散到粉丝 `feed:{uid}` ZSet（score=时间戳），最多推 5000 人；
  - 大 V：不推，读时拉其最近 N 条；
  - 读：`ZREVRANGE feed:{uid} 0 49` + 拉取大 V 列表 → 时间归并 → 批量取详情。
- 冷启动 / 新用户：按兴趣标签召回热门帖兜底。

## 7. 找搭子匹配

**第一段：硬过滤（SQL 走索引）**

```sql
SELECT * FROM buddy_post
WHERE status = 1
  AND dest_city = :city
  AND start_date <= :to AND end_date >= :from          -- 时间窗有交集
  AND gender_pref IN (0, :my_gender)
ORDER BY start_date
LIMIT 200;                                             -- 候选池上限，避免全表打分
```

**第二段：打分排序（应用层，200 条内计算）**

```
score = 0.35 × 时间重叠度（重叠天数 / 较短行程天数）
      + 0.25 × 偏好相似（标签 Jaccard + 强度差惩罚）
      + 0.15 × 活跃度（7 日内登录 / 发帖，归一化）
      + 0.15 × 信誉分（完成率、举报扣分、实名加分）
      + 0.10 × 距离衰减 exp(-d / 50km)
```

- 时间重叠为 0 直接丢弃；结果按 `城市:日期:强度` 缓存 5 分钟。
- **双向同意**才开聊：申请 → 对方同意 → 建 `conversation`；每日打招呼配额 10 次。

## 8. 地图与轨迹

- 底图沿用现有站点：高德矢量（GCJ-02，需纠偏）+ 天地图影像（WGS84，不纠偏），**切换必须重算坐标并重绘**，否则整体偏移 300–600m。
- 轨迹入库：GPX 解析 → 去跳点 / 去静止漂移 → Douglas-Peucker 抽稀（ε=4m，山地 6m）→
  - MySQL 存 `LINESTRING` 简化线（≤2000 点，供列表 / 预览 / 空间检索）
  - 全量 geobuf 存对象存储（详情、导出 GPX）
  - 需要按点分析时再写 `trail_track_point`
- 检索：`bbox` 四列 B-Tree 预筛 → `ST_Intersects` 精判；长度用 `ST_Length(geom) × 111319.9` 换算成米。

### 8.1 落到 MySQL 时的三个实做细节

**① 轴序：SRID 4326 是纬度在前**

这是把设计稿落成 SQL 时最先撞的墙。GPS 圈和前端习惯写 `[lat, lng]`，而地理 SQL 文档里常见 `POINT(lng lat)`（x-y 顺序），
MySQL 8 却按 EPSG:4326 的**标准轴序**解释，于是 `POINT(113.3245 23.1066)` 会被读成「纬度 113.32」，直接报：

```
ERROR 3617 (22S03): Latitude 113.324500 is out of range in function st_geomfromtext
```

三种写法里选一种并全库统一：

```sql
-- 方案 A（本项目采用）：按标准轴序写，纬度在前
ST_GeomFromText('POINT(23.106600 113.324500)', 4326)

-- 方案 B：显式声明轴序，保留 lng-lat 的书写直觉
ST_GeomFromText('POINT(113.324500 23.106600)', 4326, 'axis-order=long-lat')
```

风险点在于**只有空间函数会报错，普通 `DECIMAL(9,6)` 的 `lat`/`lng` 列不会**——所以库里同时存在两种表示时，
一定要在字段注释里写清哪个是 WGS84 轴序、哪个是习惯顺序，否则半年后没人分得清。

**② `ST_Length` 返回的是度数，不是米**

`ST_Length(geom)` 在 SRID 4326 下返回沿线的角度单位。乘 `111319.9`（赤道每度米数）只是**近似**，
在高纬或长距离上误差可达千分之几。要更准就用 `ST_Length(CAST(geom AS GEOGRAPHY))` 的思路（MySQL 无 GEOGRAPHY 类型，
只能选球面近似或自己在应用层按点累加 `ST_Distance_Sphere`）。本项目路线多在华南（北纬 22–30°），
用 `× 111319.9 × cos(lat)` 修正后的误差已小于 0.3%，够用。

**③ 空间索引必须 NOT NULL，且不支持前缀**

`SPATIAL KEY` 要求列 `NOT NULL` 且是 `GEOMETRY` 家族完整值——`buddy_post.geom` 初版写成 `DEFAULT NULL`，
建表直接失败。所以「找搭子」的坐标从「可选」变成「发起招募必须选目的地坐标」，
这反而是更合理的产品约束：没有目的地的招募帖，本来也没法做距离匹配。

## 9. 后端技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 语言 / 框架 | Python 3.12 + FastAPI | 异步 IO、Pydantic v2、OpenAPI 自动文档 |
| ASGI | Uvicorn + Gunicorn（uvloop） | 4 worker 单机可扛约 3k QPS 简单接口 |
| ORM | SQLAlchemy 2.0 async + asyncmy | 协程驱动，连接池可控 |
| 迁移 | Alembic | 版本化 DDL，与 `db/01_schema.sql` 对齐 |
| 数据库 | MySQL 8.0.32+（InnoDB） | 空间索引 + ngram 全文 + 分区 |
| 缓存 | Redis 7 | 会话 / 缓存 / GEO / 限流 / 队列 |
| 异步 | Celery + Redis broker | 转码、Feed 扩散、审核、计数落库 |
| 对象存储 | MinIO / S3 / COS | 原图、GPX、geobuf |
| 观测 | OpenTelemetry + Prometheus + Grafana + Sentry | 链路 + 指标 + 错误聚合 |
| 部署 | Docker Compose（开发）/ K8s（生产）+ Nginx | 无状态水平扩展 |

```
app/
  main.py
  core/      config, security, db, redis, deps
  modules/
    auth/     register, login, session
    content/  poi, trail
    social/   post, comment, favorite, follow
    match/    buddy, nearby
    media/    upload, transcode
  workers/    celery_app, tasks
```

## 10. 高并发设计

| 问题 | 方案 |
|---|---|
| 读多写少 | 三级缓存：本地 LRU（秒级）→ Redis → MySQL，热点 key 本地兜 80% |
| 缓存穿透 | 空值缓存 60s + 布隆过滤器（景点 / 路线 id） |
| 缓存击穿 | `SET NX` 单飞，只允许一个请求回源 |
| 缓存雪崩 | TTL ±10% 抖动 + 启动分批预热 + Redis 主从哨兵 |
| 写热点 | 点赞计数进 Redis，30s 批量落库；失败重试 |
| 限流 | Nginx `limit_req`（IP 级）+ 应用层 Redis 令牌桶（用户级，Lua 原子） |
| 削峰 | 发帖 / 转码入队，接口只校验 + 落库即返回 |
| 大表 | `post` 按月 RANGE 分区（需去外键）；`favorite` 按 user_id 哈希分 16 片（预案） |
| 扩展 | API 无状态 + K8s HPA；WebSocket 走 Redis Pub/Sub |
| 降级 | Redis 故障关计数与推荐，只保核心读；匹配降级为「热门搭子」 |

容量估算（10 万 DAU）：读峰值 ≈800 QPS、写 ≈50 QPS；Redis 约 2GB；MySQL 一年约 15GB（含索引）。

## 11. 附近的人：怎么算得准又不泄露位置

### 11.1 四步流水线

```
① 脱敏上报   客户端给 WGS84 → 吸附 geohash6 网格中心（约 1.2km × 0.6km）+ ±150m 抖动
② GEO 粗筛   Redis GEOSEARCH nearby:{city} BYRADIUS 5km COUNT 200
③ 精算       MySQL ST_Distance_Sphere(geom, :me) 取米级距离 + 可见性/时效过滤
④ 重排       score = 0.4×距离衰减(exp(-d/1.5km)) + 0.3×兴趣 Jaccard + 0.2×活跃度 + 0.1×信誉
```

### 11.2 精度的关键处理

1. **坐标脱敏**：库里存的是网格中心 + 抖动，**不是真实点**，拖库也无法还原。
2. **距离分档**：「500m 内 / 1km / 3km / 5km」，不给精确米数，防三角定位。
3. **双向授权**：双方都点「可见位置」才交换精确点；聊天中默认只显示区域。
4. **时效**：30 分钟过期（Redis TTL + `presence.updated_at` 双保险）。
5. **反作弊**：位置跳变（>200km/h）丢弃并降权、同设备多账号聚类、虚拟定位特征识别。
6. **隐私开关**：默认只对同性别或已互关可见，可完全关闭。

### 11.3 为什么 Redis GEO 与 MySQL 双写

Redis 负责**低延迟粗筛**（`GEOSEARCH`，O(log N + M)），MySQL 负责**可审计的精算与联合查询**（例如「3km 内、标注过露营点、近 7 天活跃」）。前者是热路径，后者是一致性来源。

## 12. 接口清单（节选）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 密码 / 验证码登录 |
| POST | `/api/v1/auth/refresh` | 刷新 access |
| GET | `/api/v1/me` | 当前用户 + 设备列表 |
| POST | `/api/v1/favorites` | 收藏 / 取消 |
| GET | `/api/v1/feed?cursor=` | 关注流 |
| POST | `/api/v1/posts` | 发帖 |
| GET | `/api/v1/trails?bbox=` | 视野内路线 |
| GET | `/api/v1/trails/{id}/track` | 全量轨迹（geobuf） |
| GET | `/api/v1/buddies?city=&from=&to=` | 找搭子 |
| POST | `/api/v1/buddies/{id}/apply` | 申请加入 |
| GET | `/api/v1/nearby?radius=3000` | 附近的人 |

## 13. 与 10:21 版的差异

| 维度 | 10:21 版（基线） | 本次设计 |
|---|---|---|
| 数据存储 | 前端 `src/data/*.js` 写死 | MySQL 23 表 + Redis 缓存 |
| 账号 | 无 | 手机 / 邮箱 / 微信，双 Token + Redis 会话 |
| 内容 | 单向浏览 | 收藏、发帖、评论、关注、Feed |
| 社交 | 无 | 找搭子匹配、附近的人、私信 |
| 地图 | Leaflet 双底图 | 保留，新增空间检索与轨迹入库 |
| 部署 | 纯静态 | 容器化 API + MySQL + Redis + 对象存储 |

---

## 附：可直接跑的东西

```bash
mysql -uroot -p < db/01_schema.sql     # 建库建表（23 表 / 2 视图 / 3 触发器）
mysql -uroot -p < db/02_seed.sql       # 演示数据
mysql -uroot -p yejing < db/03_queries.sql   # 附近的人 / 找搭子 / Feed / 性能自检
python db/verify_sql.py                # 79 条语句离线语法校验
```
