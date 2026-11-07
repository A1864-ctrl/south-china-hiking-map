-- ============================================================================
-- 野径 · 华南徒步图鉴 —— MySQL 8.0 数据结构
-- ----------------------------------------------------------------------------
-- 用途：把站点里现在写死在前端的静态数据（11 城 / 76 点位 / 53 路线 / 74 装备）
--       和只存在浏览器 localStorage 的账号、会话、收藏，搬到一个真正的服务端库里。
--
-- 执行：
--   mysql -u root -p < sql/01_schema.sql
--   mysql -u root -p yejing < sql/02_seed.sql      -- 真实数据（由 scripts/export_mysql.mjs 生成）
--
-- 字符集：utf8mb4 / utf8mb4_0900_ai_ci（MySQL 8 默认，中文与 emoji 都能存）
-- 引擎：InnoDB；坐标用 DECIMAL(9,6)（约 0.11 m 精度，够画轨迹，不必上 PostGIS）
-- ============================================================================

CREATE DATABASE IF NOT EXISTS yejing_content
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE yejing_content;

SET NAMES utf8mb4;

-- 先关外键再按依赖倒序删，方便反复重建
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS auth_sessions;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS gear_scenes;
DROP TABLE IF EXISTS gear_items;
DROP TABLE IF EXISTS route_risks;
DROP TABLE IF EXISTS route_gear;
DROP TABLE IF EXISTS route_track;
DROP TABLE IF EXISTS route_waypoints;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS spot_tags;
DROP TABLE IF EXISTS spots;
DROP TABLE IF EXISTS app_versions;
DROP TABLE IF EXISTS cities;
SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================================
-- 1. 地理与内容
-- ============================================================================

CREATE TABLE cities (
  id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name        VARCHAR(32)      NOT NULL COMMENT '城市名，如「桂林」',
  province    VARCHAR(16)      NOT NULL COMMENT '省 / 自治区',
  center_lat  DECIMAL(9,6)     DEFAULT NULL COMMENT '城市中心纬度（WGS84）',
  center_lng  DECIMAL(9,6)     DEFAULT NULL COMMENT '城市中心经度（WGS84）',
  tagline     VARCHAR(160)     DEFAULT NULL COMMENT '一句话印象，卡片副标题',
  best_season VARCHAR(32)      DEFAULT NULL COMMENT '推荐季节',
  PRIMARY KEY (id),
  UNIQUE KEY uk_city_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='城市。11 座站内主推城市有中心点；只被路线提到、没有内容页的城市 center 为空';


CREATE TABLE spots (
  id       SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name     VARCHAR(64)       NOT NULL,
  city_id  TINYINT UNSIGNED  NOT NULL,
  district VARCHAR(32)       DEFAULT NULL COMMENT '区 / 县 / 县级市',
  type     VARCHAR(16)       NOT NULL COMMENT '类型：山峰、海岸、丹霞、古镇…',
  heat     TINYINT UNSIGNED  NOT NULL DEFAULT 0 COMMENT '热度 0-100，站内排序用',
  ticket   VARCHAR(16)       DEFAULT NULL COMMENT '票价，可能是「免费」这种文本',
  hours    VARCHAR(16)       DEFAULT NULL COMMENT '建议游玩时长',
  reason   VARCHAR(400)      DEFAULT NULL COMMENT '推荐理由，80 字上下',
  lat      DECIMAL(9,6)      NOT NULL,
  lng      DECIMAL(9,6)      NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_spot_city_name (city_id, name),
  KEY idx_spot_city_type (city_id, type),
  KEY idx_spot_heat (heat DESC),
  CONSTRAINT fk_spot_city FOREIGN KEY (city_id) REFERENCES cities (id) ON DELETE CASCADE,
  CONSTRAINT ck_spot_heat CHECK (heat BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='景点点位：76 条。原站按城市筛选 + 类型筛选 + 热度排序，索引按这个顺序建';


CREATE TABLE spot_tags (
  spot_id SMALLINT UNSIGNED NOT NULL,
  seq     TINYINT UNSIGNED  NOT NULL,
  tag     VARCHAR(16)       NOT NULL COMMENT '标签，如「竹筏」「免费」「亲子」',
  PRIMARY KEY (spot_id, tag),
  KEY idx_tag (tag),
  CONSTRAINT fk_tag_spot FOREIGN KEY (spot_id) REFERENCES spots (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='点位标签，一个点位 2-3 个。拆表是为了能「按标签反查」';


CREATE TABLE routes (
  id          SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name        VARCHAR(64)       NOT NULL,
  province    VARCHAR(16)       NOT NULL,
  city_id     TINYINT UNSIGNED  NOT NULL,
  terrain     VARCHAR(24)       NOT NULL COMMENT '地形：高山草甸、海岸线、峰林…',
  level       ENUM('easy','mid','hard') NOT NULL COMMENT '难度档位',
  level_text  VARCHAR(16)       NOT NULL COMMENT '难度中文：入门 / 进阶 / 硬核',
  distance_km DECIMAL(5,1)      NOT NULL COMMENT '标称里程，km',
  climb_m     SMALLINT UNSIGNED NOT NULL COMMENT '累计爬升，m',
  days        VARCHAR(8)        NOT NULL COMMENT '建议天数：「1天」「2天」',
  season      VARCHAR(24)       DEFAULT NULL COMMENT '最佳季节',
  heat        TINYINT UNSIGNED  NOT NULL DEFAULT 0,
  is_loop     TINYINT(1)        NOT NULL DEFAULT 0 COMMENT '是否环线',
  hours_text  VARCHAR(16)       DEFAULT NULL COMMENT '按里程 + 爬升估的耗时',
  real_km     DECIMAL(5,1)      DEFAULT NULL COMMENT '按轨迹点算的实际长度',
  max_ele     SMALLINT          DEFAULT NULL COMMENT '轨迹最高海拔',
  min_ele     SMALLINT          DEFAULT NULL COMMENT '轨迹最低海拔',
  `desc`      TEXT              COMMENT '线路描述',
  tips        TEXT              COMMENT '注意事项',
  access_hsr  VARCHAR(255)      DEFAULT NULL COMMENT '高铁接驳',
  access_rail VARCHAR(255)      DEFAULT NULL COMMENT '普速 / 火车接驳',
  access_bus  VARCHAR(255)      DEFAULT NULL COMMENT '公交 / 班车接驳',
  access_car  VARCHAR(255)      DEFAULT NULL COMMENT '自驾与停车',
  naming_json JSON              DEFAULT NULL COMMENT '命名勘误（起终点与地名对不上时才有）',
  PRIMARY KEY (id),
  UNIQUE KEY uk_route_name (name),
  KEY idx_route_city (city_id),
  KEY idx_route_level (level, distance_km),
  KEY idx_route_heat (heat DESC),
  CONSTRAINT fk_route_city FOREIGN KEY (city_id) REFERENCES cities (id),
  CONSTRAINT ck_route_distance CHECK (distance_km > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='徒步路线：53 条。access 四种接驳方式拉平成四列，比一张 1:1 附表好查';


CREATE TABLE route_waypoints (
  id       INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  route_id SMALLINT UNSIGNED NOT NULL,
  seq      TINYINT UNSIGNED NOT NULL COMMENT '走线顺序，从 0 开始',
  name     VARCHAR(64)      NOT NULL,
  lat      DECIMAL(9,6)     NOT NULL,
  lng      DECIMAL(9,6)     NOT NULL,
  ele      SMALLINT         DEFAULT NULL COMMENT '海拔，m',
  supply   VARCHAR(255)     DEFAULT NULL COMMENT '补给 / 水源 / 撤离说明',
  note     VARCHAR(255)     DEFAULT NULL COMMENT '路书备注',
  photo    VARCHAR(255)     DEFAULT NULL COMMENT '拍照点说明',
  is_camp  TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '是否营地',
  PRIMARY KEY (id),
  UNIQUE KEY uk_wp_route_seq (route_id, seq),
  KEY idx_wp_route (route_id, seq),
  CONSTRAINT fk_wp_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE,
  CONSTRAINT ck_wp_ele CHECK (ele IS NULL OR ele BETWEEN -200 AND 9000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='路线关键点：218 个。详情页「分段路书」按 seq 顺序读';


CREATE TABLE route_track (
  route_id SMALLINT UNSIGNED NOT NULL,
  seq      SMALLINT UNSIGNED NOT NULL COMMENT '轨迹点序号，从 0 开始',
  lat      DECIMAL(9,6)      NOT NULL,
  lng      DECIMAL(9,6)      NOT NULL,
  PRIMARY KEY (route_id, seq),
  CONSTRAINT fk_track_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='轨迹点：约 3.9 万个。整条线一次 SELECT 出来按 seq 排序即可画线';


CREATE TABLE route_gear (
  route_id SMALLINT UNSIGNED NOT NULL,
  seq      TINYINT UNSIGNED  NOT NULL,
  item     VARCHAR(64)       NOT NULL COMMENT '该线专属装备（文本，可能不在 gear_items 里）',
  PRIMARY KEY (route_id, seq),
  KEY idx_rg_item (item),
  CONSTRAINT fk_rg_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='每条路线的专属装备清单：原来写死在 routes.js 的 gear 数组';


CREATE TABLE route_risks (
  route_id SMALLINT UNSIGNED NOT NULL,
  seq      TINYINT UNSIGNED  NOT NULL,
  risk     VARCHAR(64)       NOT NULL COMMENT '风险点：落石、失温、塌方…',
  PRIMARY KEY (route_id, seq),
  CONSTRAINT fk_risk_route FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='路线风险提示';


CREATE TABLE gear_items (
  id          SMALLINT UNSIGNED NOT NULL COMMENT '沿用原站 id，方便前端对照',
  group_name  VARCHAR(24)       NOT NULL COMMENT '八大系统：着装、背负、宿营…',
  sub_group   VARCHAR(24)       DEFAULT NULL COMMENT '子系统，如「排汗内层」',
  name        VARCHAR(64)       NOT NULL,
  is_required TINYINT(1)        NOT NULL DEFAULT 0 COMMENT '是否必带',
  note        VARCHAR(255)      DEFAULT NULL COMMENT '为什么带',
  PRIMARY KEY (id),
  KEY idx_gear_group (group_name, sub_group),
  KEY idx_gear_required (is_required)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='装备总表：74 项，八大系统';


CREATE TABLE gear_scenes (
  gear_id SMALLINT UNSIGNED NOT NULL,
  scene   VARCHAR(16)       NOT NULL COMMENT '单日徒步 / 重装露营 / 长线高难度',
  PRIMARY KEY (gear_id, scene),
  KEY idx_scene (scene),
  CONSTRAINT fk_scene_gear FOREIGN KEY (gear_id) REFERENCES gear_items (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='装备适用场景：多对多，按场景筛清单走这张表';


-- ============================================================================
-- 2. 账号、会话、收藏（现在都在浏览器 localStorage 里）
-- ============================================================================

CREATE TABLE users (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nickname      VARCHAR(32)     NOT NULL,
  phone         VARCHAR(20)     DEFAULT NULL COMMENT '手机号或邮箱二选一',
  email         VARCHAR(120)    DEFAULT NULL,
  salt          CHAR(16)        NOT NULL COMMENT '每账号独立盐值：8 字节 hex，与前端 randomHex(8) 一致',
  password_hash CHAR(64)        NOT NULL COMMENT 'sha256("salt::password") 的 hex，与前端 digest() 一致',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME        DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_phone (phone),
  UNIQUE KEY uk_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='账号。密码只存 salt + 哈希；生产环境建议换成 bcrypt/argon2（见 docs）';


CREATE TABLE auth_sessions (
  jti        CHAR(24)        NOT NULL COMMENT '会话 id：12 字节 hex，与前端 randomHex(12) 一致',
  user_id    BIGINT UNSIGNED NOT NULL,
  issued_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME        NOT NULL COMMENT '滑动过期：每次访问顺延 30 分钟',
  revoked_at DATETIME        DEFAULT NULL COMMENT '登出时间，非空即失效',
  user_agent VARCHAR(255)    DEFAULT NULL,
  PRIMARY KEY (jti),
  KEY idx_sess_user (user_id, expires_at),
  CONSTRAINT fk_sess_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='会话。取代现在前端存的「30 分钟滑动会话」，改由服务端判过期';


CREATE TABLE favorites (
  id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  user_id     BIGINT UNSIGNED  NOT NULL,
  kind        ENUM('spot','route') NOT NULL,
  target_id   INT UNSIGNED     DEFAULT NULL COMMENT '路线用 routes.id',
  target_name VARCHAR(64)      DEFAULT NULL COMMENT '景点按名称收藏，保留原名防改名后失效',
  created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_fav (user_id, kind, target_id, target_name),
  KEY idx_fav_user (user_id, created_at DESC),
  CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='收藏。景点按名称、路线按 id，跟站内现在的行为一致';


-- ============================================================================
-- 3. 版本记录（versions.js 的落库版）
-- ============================================================================

CREATE TABLE app_versions (
  id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code        VARCHAR(8)       NOT NULL COMMENT 'v1 / v2 / v3…',
  released_at DATETIME         NOT NULL,
  tag         VARCHAR(16)      DEFAULT NULL COMMENT '本次 / 上一次',
  title       VARCHAR(120)     NOT NULL,
  summary     TEXT,
  snapshot    VARCHAR(32)      DEFAULT NULL COMMENT '代码快照目录名',
  live_url    VARCHAR(255)     DEFAULT NULL,
  metrics     JSON             DEFAULT NULL COMMENT '页面上的指标卡，原样存 JSON',
  PRIMARY KEY (id),
  UNIQUE KEY uk_ver_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='/versions 版本对比页的数据源';


-- ============================================================================
-- 4. 视图：把详情页最常用的几条联表查询固定下来
-- ============================================================================

CREATE OR REPLACE VIEW v_route_overview AS
SELECT
  r.id,
  r.name,
  c.name                AS city,
  r.level_text,
  r.terrain,
  r.distance_km,
  r.climb_m,
  r.days,
  r.heat,
  COUNT(DISTINCT w.id)   AS waypoint_count,
  COUNT(DISTINCT g.item) AS gear_count,
  COUNT(DISTINCT k.risk) AS risk_count
FROM routes r
JOIN cities c            ON c.id = r.city_id
LEFT JOIN route_waypoints w ON w.route_id = r.id
LEFT JOIN route_gear g      ON g.route_id = r.id
LEFT JOIN route_risks k     ON k.route_id = r.id
GROUP BY r.id, r.name, c.name, r.level_text, r.terrain,
         r.distance_km, r.climb_m, r.days, r.heat;

CREATE OR REPLACE VIEW v_spot_heat_rank AS
SELECT
  s.id,
  s.name,
  c.name AS city,
  s.type,
  s.heat,
  RANK() OVER (PARTITION BY s.city_id ORDER BY s.heat DESC) AS heat_rank
FROM spots s
JOIN cities c ON c.id = s.city_id;

CREATE OR REPLACE VIEW v_user_favorite_detail AS
SELECT
  f.id,
  f.user_id,
  u.nickname,
  f.kind,
  COALESCE(s.name, r.name, f.target_name) AS target_name,
  COALESCE(c1.name, c2.name)              AS city,
  f.created_at
FROM favorites f
JOIN users u       ON u.id = f.user_id
LEFT JOIN spots s   ON f.kind = 'spot'  AND s.name = f.target_name
LEFT JOIN cities c1 ON c1.id = s.city_id
LEFT JOIN routes r  ON f.kind = 'route' AND r.id = f.target_id
LEFT JOIN cities c2 ON c2.id = r.city_id;

-- ============================================================================
-- 常用写法备忘（不是表，抄走直接用）：
--   收藏切换（点一下加、再点一下删）：
--     INSERT INTO favorites (user_id, kind, target_id, target_name)
--     VALUES (?, 'route', ?, NULL)
--     ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP;
--   会话滑动续期：
--     UPDATE auth_sessions SET expires_at = NOW() + INTERVAL 30 MINUTE
--     WHERE jti = ? AND revoked_at IS NULL AND expires_at > NOW();
-- ============================================================================
