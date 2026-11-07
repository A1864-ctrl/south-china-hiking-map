# 野径 · MySQL 数据库

MySQL 8.0.32+ 可直接导入的完整库：23 张表、2 个视图、3 个触发器、6 个空间索引、3 个中文全文索引。
坐标统一 **WGS84 / SRID 4326**，**字段顺序是 `POINT(lat lng)`——纬度在前**（MySQL 8 按 OGC 标准轴序，见下文「坑 1」）。

**已在本机 MySQL 8.0.46 实跑通过**：建库 → 导入 4 用户 / 6 景点 / 3 路线 / 14 装备 / 4 帖 / 3 搭子帖 / 4 位置，核心查询集零错误。

## 一键导入

```bash
# 推荐：脚本自动完成建库 + 数据 + 账号 + 验收
MYSQL_PWD='你的root密码' python db/setup.py

# 或手动按顺序执行
mysql -uroot -p < 01_schema.sql     # 建库建表 + 视图 + 触发器
mysql -uroot -p < 02_seed.sql       # 演示数据
mysql -uroot -p < 04_user.sql       # 应用账号（最小权限）
mysql -uroot -p yejing < 03_queries.sql   # 核心查询（答辩演示 / 性能对比）
```

`setup.py` 会打印结构验收（表 / 视图 / 触发器 / 空间索引 / 外键 / 全文索引）与三条功能验证查询，末尾给出连接串。

## 本机实测踩到的两个坑

### 坑 1：SRID 4326 的轴序是 (纬度, 经度)

第一次导入直接报：

```
ERROR 3617 (22S03): Latitude 113.324500 is out of range
in function st_geomfromtext. It must be within [-90.000000, 90.000000].
```

原因：MySQL 8 对 SRID 4326 采用 **EPSG:4326 的标准轴序 = lat, lon**，而 GIS 圈日常口头说的 `POINT(lng lat)` 是 x-y 顺序。
写成 `POINT(113.32 23.10)` 时 MySQL 把 113.32 当纬度，直接越界。

正确写法（全库已按此改）：

```sql
ST_GeomFromText('POINT(23.106600 113.324500)', 4326)   -- 广州塔：lat 在前
```

LINESTRING / POLYGON 里每一对坐标同样要 lat 在前。若确实想按 lng-lat 写，可以显式带轴序选项：

```sql
ST_GeomFromText('POINT(113.3245 23.1066)', 4326, 'axis-order=long-lat')
```

两种写法等价，项目里统一用前者（少一个参数，不容易漏）。

### 坑 2：`yejing_app` 这个账号名在本机认证不上

账号建好后 `mysql.user` 里 hash、host、属性全对，`SHOW CREATE USER` 与能登录的 `yj_app` **逐字相同**，
但无论 `FLUSH PRIVILEGES` / `RENAME USER` / 改密码都返回 `1045 Access denied`；同一密码换成 `yj_app` 立刻能登。
查过 `HEX(user)` 无隐藏字符、`User_attributes` 为 NULL、无 role、`account_locked=N`、`password_expired=N`。
判断为该实例的 ACL 残留（无管理员权限，没能重启服务复验）。所以最终账号名取 **`yj_app` / `yj_ro`**。
换机器部署时若没这问题，把 `04_user.sql` 里的名字改回 `yejing_app` 即可。

## 表清单（23 张）

| 分组 | 表 | 作用 |
|---|---|---|
| 账号 | `app_user` | 用户主体，手机 / 邮箱唯一 |
| | `user_oauth` | 微信 / 小程序 openid 绑定 |
| | `user_device` | 设备指纹，判异地登录与踢下线 |
| | `user_session` | 会话冷备（jti、过期时间、撤销时间） |
| 内容 | `poi` | 景点，`POINT SRID 4326` + 空间索引 |
| | `poi_photo` | 景点图片（四季 / 时段） |
| | `trail` | 路线，`LINESTRING SRID 4326` + 起点 `POINT` + bbox 四列 |
| | `trail_waypoint` | 途经点（里程、海拔、补给） |
| | `trail_track_point` | 轨迹采样点（需要按点分析时用，全量仍放对象存储） |
| | `gear_item` / `trail_gear` | 74 项装备 + 每条路线专属装备与理由 |
| 社交 | `favorite` | 多态收藏（景点 / 路线 / 帖子） |
| | `post` / `post_image` | 帖子与图片 |
| | `post_like` / `comment` / `follow` | 点赞 / 评论 / 关注 |
| 组队 | `buddy_post` | 找搭子招募（时间窗、强度、预算、偏好） |
| | `buddy_apply` | 申请（**双向同意**才开聊） |
| 私信 | `conversation` / `message` | 会话（`user_a < user_b` 去重）与消息 |
| 位置 | `presence` | 附近的人，模糊点 + geohash6 |
| 审计 | `audit_log` | 登录、发帖、申请等行为留痕 |

视图：`v_trail_card`（列表页一次取回卡片数据）、`v_user_favorite`（我的收藏）。
触发器：点赞 / 取消赞 / 评论后维护 `post.like_cnt`、`comment_cnt`。

## MySQL 怎么做地理查询

| 需求 | 写法 | 说明 |
|---|---|---|
| 两点距离（米） | `ST_Distance_Sphere(a.geom, b.geom)` | 球面计算，误差 < 0.5%，比自写 Haversine 快 |
| 构造坐标 | `ST_GeomFromText('POINT(lat lng)', 4326)` | **纬度在前**，写反会报 3617 Latitude out of range |
| 范围检索 | `ST_Distance_Sphere(...) <= 3000` | 点在 3km 内；配合 `SPATIAL INDEX` 或 geohash 前缀先粗筛 |
| 视野内路线 | `min_lat/max_lat/min_lng/max_lng` 先走普通 B-Tree，再 `ST_Intersects(geom, 多边形)` | 避免全表算空间函数 |
| 附近路线入口 | 用 `start_pt` 的 `SPATIAL KEY` | `ST_Distance_Sphere` 只接受点，所以路线额外存起点 |
| 路线长度 | `ST_Length(geom) * 111319.9` | 4326 下 `ST_Length` 返回度数，乘赤道米/度换算 |
| 中文搜索 | `FULLTEXT ... WITH PARSER ngram` | 8.0 内置 ngram，中文无需外挂分词 |

**三条硬约束（导入前必读）**

1. `SPATIAL INDEX` 的列必须 `NOT NULL` —— 所以 `poi.geom`、`trail.geom`、`trail.start_pt`、`presence.geom`、`buddy_post.geom` 全部声明为 `NOT NULL`（初版 `buddy_post.geom` 写成 `DEFAULT NULL`，建表时直接报 `All parts of a SPATIAL index must be NOT NULL`）。
2. InnoDB **分区表不支持外键** —— 所以 `post` 当前不分区；量级上来后按 `created_at` 做 RANGE 分区时，要去掉 `fk_post_author`，改用应用层约束 + 定时校验（注释里已写明）。
3. `ST_Distance_Sphere` 只对**点**精确 —— 路线距离先用 bbox / 起点近似，精确的沿线距离用 `ST_Length`。

## Redis 与会话（和 MySQL 的分工）

| Key | 类型 | TTL | 用途 |
|---|---|---|---|
| `sess:{uid}:{jti}` | String(JSON) | 1800s，**每次请求 EXPIRE 续期** | 热会话，鉴权只看它 |
| `rt:{uid}:{jti}` | String | 7d | refresh token 白名单（旋转后旧值删除） |
| `sms:{phone}` | String | 300s | 短信验证码（存哈希，不存明文） |
| `rl:{uid}:{api}` | String(计数) | 60s | 用户级限流（Lua 令牌桶） |
| `geo:nearby:{city}` | GEO | — | `GEOADD` / `GEOSEARCH BYRADIUS`，附近的人粗筛 |
| `feed:{uid}` | ZSet | 7d | 关注流收件箱（写扩散） |
| `cnt:like:{postId}` | String | 10min | 点赞计数缓冲，定时批量落 MySQL |

**登录 → 会话保持**

```
登录成功
  ├─ 生成 jti（32 位 hex）
  ├─ MySQL: INSERT user_session(jti, user_id, device_id, ip, ua, expires_at = now+30min)
  ├─ Redis: SETEX sess:{uid}:{jti} 1800 {device, ip, ua, last_seen}
  └─ 返回 access_token(15min, JWT) + refresh_token(7d, HttpOnly Cookie)

每次请求
  ├─ 验 JWT 签名 → 取 uid + jti
  ├─ 查 Redis sess:{uid}:{jti}
  │    ├─ 命中 → EXPIRE 1800（滑动续期）+ 异步 UPDATE user_session.last_seen_at
  │    └─ 未命中 → 401
  └─ 放行

Redis 挂了
  └─ 回源 MySQL user_session（jti 未撤销且未过期）→ 重建 Redis 键，用户无感
```

MySQL 是**持久层**（重启、Redis 掉电都不丢登录态），Redis 是**热路径**（只看它，QPS 压力小一个数量级）。

## 实测结果（MySQL 8.0.46 / Windows）

```
mysql  Ver 8.0.46 for Win64 on x86_64

结构验收
  表数量            23
  视图数量           2
  触发器数量          3
  空间索引数量         6
  外键数量           22
  ngram 全文索引     3

数据行数   app_user 4 · poi 6 · trail 3 · trail_waypoint 10 · gear_item 14
          favorite 6 · post 4 · comment 4 · buddy_post 3 · presence 4

功能验证
  附近的人（500m 内）   山野阿野 39m · 小满 263m
  找搭子（11/12–11/16） 桂林 11-12 · 萍乡 11-14 · 长沙 11-15
  路线卡片视图          武功山 26.0km/↑1590 · 漓江 20.0km/↑210 · 岳麓山 12.6km/↑300

触发器  点赞前 2 → 插入后 3 → 取消后 2（不会减到负数）
全文索引  MATCH('岳麓山') 命中 1 条，相关度 0.725
账号权限  yj_app 读写通；yj_ro 写入被拒（ERROR 1142）
```

`python db/verify_sql.py` 另做一层静态校验（sqlglot 按 MySQL 方言解析 79 条语句），
可在没有 MySQL 服务的机器上先查语法。解析前对 `SRID 4326`、`POINT/LINESTRING` 做等价替换，
因为 sqlglot 尚未建模这些 MySQL 8 空间语法——这只影响它的解析，不影响 SQL 在真实 MySQL 上执行。
