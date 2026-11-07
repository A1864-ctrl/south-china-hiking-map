# 野径 · MySQL 内容库（`yejing_content`）

把站里现在写死在前端的那份数据，原样搬进 MySQL：**24 城 / 76 点位 / 53 条路线 / 74 件装备 / 218 个关键点 / 39113 个轨迹点**，外加账号、会话、收藏三张表。

和 `../db/` 不是一回事，两套各管一段，别混着导：

| | `sql/`（本目录，库名 `yejing_content`） | `../db/`（库名 `yejing`） |
|---|---|---|
| 定位 | **内容库**：站点现有的全部真实数据 | **平台库**：社交 / 组队 / 私信 / 审核的完整 23 表设计 |
| 表数 | 14 张表 + 3 个视图 | 23 张表 + 2 个视图 + 3 个触发器 |
| 数据 | 全量真实数据（从 `src/data/*.js` 生成，1.7 MB） | 十几行演示数据，够看结构 |
| 坐标 | `DECIMAL(9,6)` 两列（够画轨迹，MySQL 5.7 也能跑） | `POINT/LINESTRING SRID 4326` + 空间索引 |
| 适合 | 答辩时演示「前端数据怎么落库」、给静态站接 API | 讲清「要做成社交平台，库该怎么设计」 |

## 一键导入

```bash
mysql -u root -p < sql/01_schema.sql                 # 建库 + 14 表 + 3 视图
mysql -u root -p yejing_content < sql/02_seed.sql    # 全量数据（约 1.7 MB）
```

Workbench 里按顺序打开两个文件执行也行。`01_schema.sql` 只 `DROP TABLE`，不会删库；`02_seed.sql` 开头先 `TRUNCATE`，可以反复重导。

## 数据改了怎么办

种子文件不要手改。改完 `src/data/routes.js` / `spots.js` / `gear.js` 后重跑：

```bash
node scripts/export_mysql.mjs     # 重新生成 sql/02_seed.sql
```

脚本会顺手校验：景点或路线的城市在 `cities` 里找不到就直接报错，不让 `NULL` 混进 `city_id`。

## 表清单

| 表 | 行数 | 说明 |
|---|---|---|
| `cities` | 24 | 11 座站内主推城市 + 13 座只在路线里出现的城市（无中心点） |
| `spots` | 76 | 点位，`UNIQUE(city_id,name)`，`(city_id,type)` + `heat DESC` 两个索引 |
| `spot_tags` | 228 | 点位标签，拆表为了「按标签反查」 |
| `routes` | 53 | 路线，`access` 四种接驳拉平成四列，`naming_json` 存起终点勘误 |
| `route_waypoints` | 218 | 关键点，`UNIQUE(route_id,seq)` |
| `route_track` | 39113 | 轨迹点，主键 `(route_id,seq)` |
| `route_gear` | 416 | 每条线的专属装备（文本，可能不在 `gear_items` 里） |
| `route_risks` | 159 | 风险提示 |
| `gear_items` | 74 | 八大系统装备总表，`id` 沿用站内编号 |
| `gear_scenes` | 157 | 装备 × 场景多对多 |
| `users` / `auth_sessions` | 1 / 0 | 账号与会话，盐值与前端 `randomHex(8)` 同长（16 位 hex） |
| `favorites` | 2 | 景点按名称、路线按 id，跟站内行为一致 |
| `app_versions` | 2 | `/versions` 页的数据源 |

演示账号：手机号 `13800000000`，密码 `yejing2026`（哈希是 `sha256("salt::password")`，和前端 `src/stores/auth.js` 的 `digest()` 完全一致，接后端时可以直接复用这套校验）。

## 几条常用查询

```sql
-- 1. 某城市的路线列表，按热度排（对应 /routes 的筛选）
SELECT name, level_text, distance_km, climb_m, days, heat
FROM routes WHERE city_id = (SELECT id FROM cities WHERE name = '深圳')
ORDER BY heat DESC;

-- 2. 路线详情页要的三块：关键点 + 装备 + 风险
SELECT seq, name, ele, supply, note FROM route_waypoints WHERE route_id = 23 ORDER BY seq;
SELECT item FROM route_gear WHERE route_id = 23 ORDER BY seq;
SELECT risk FROM route_risks WHERE route_id = 23 ORDER BY seq;

-- 3. 画轨迹（一次拿全，前端按 seq 连折线）
SELECT seq, lat, lng FROM route_track WHERE route_id = 23 ORDER BY seq;

-- 4. 城市榜：每个城市热度前三的点位（窗口函数，走 v_spot_heat_rank）
SELECT * FROM v_spot_heat_rank WHERE heat_rank <= 3 ORDER BY city, heat_rank;

-- 5. 某个账号收藏了什么（走 v_user_favorite_detail）
SELECT kind, target_name, city, created_at
FROM v_user_favorite_detail WHERE user_id = 1 ORDER BY created_at DESC;
```

## 校验到哪一步

- 语法：`sqlglot` 以 MySQL 方言解析，`01_schema.sql` 37/37 条、`02_seed.sql` 119/119 条通过。
- 数据：行数与站点封面数字对齐（76 / 53 / 74），轨迹点 39113 个与 `routes.js` 里 `track` 总长一致。
- **没有真跑过**：本机没有 MySQL 服务，`mysql -u root -p` 这步没执行。导入时如报错，优先看 `sql_mode` 和字符集（文件头已 `SET NAMES utf8mb4`）。

## 前端怎么接

| 现在（localStorage） | 换成 |
|---|---|
| `yj.users`（注册信息） | `users` + `POST /api/register` |
| `yj.session`（jti + 过期时间） | `auth_sessions`，过期判断挪到服务端 |
| `yj.fav.<userId>`（收藏桶） | `favorites` + `GET/POST /api/favorites` |
| `src/data/spots.js` 等静态数组 | `GET /api/spots`、`/api/routes/:id` |

注意：在线链接（`south-china-hiking.app.workbuddy.host`）是纯静态托管，**没有数据库**，这套 SQL 只能跑在你自己的服务器或云 MySQL 上。前端要真接，得先有后端 API（见 `docs/旅游社交平台-系统设计-MySQL版.md` 第 12 节接口清单）。
