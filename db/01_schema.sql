-- ============================================================
--  野径 · 旅行社交平台　MySQL 8.0 数据库
--  文件：01_schema.sql（建库 + 建表 + 索引 + 视图 + 触发器）
--  字符集：utf8mb4 / utf8mb4_0900_ai_ci　时区：UTC
--  空间字段统一 SRID 4326（WGS84），距离用 ST_Distance_Sphere 按米算
-- ============================================================

DROP DATABASE IF EXISTS yejing;
CREATE DATABASE yejing
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE yejing;

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ------------------------------------------------------------
-- 1. 账号
-- ------------------------------------------------------------
CREATE TABLE app_user (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  phone         VARCHAR(20)     DEFAULT NULL COMMENT '手机号，与邮箱二选一',
  email         VARCHAR(120)    DEFAULT NULL,
  password_hash VARCHAR(255)    NOT NULL COMMENT 'Argon2id 输出，含盐与参数',
  nickname      VARCHAR(32)     NOT NULL,
  avatar_key    VARCHAR(160)    DEFAULT NULL COMMENT '对象存储 key',
  gender        TINYINT         NOT NULL DEFAULT 0 COMMENT '0 未知 1 男 2 女',
  bio           VARCHAR(200)    DEFAULT NULL,
  city          VARCHAR(32)     DEFAULT NULL,
  status        TINYINT         NOT NULL DEFAULT 1 COMMENT '1 正常 2 禁言 3 封禁',
  last_login_at DATETIME        DEFAULT NULL,
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_phone (phone),
  UNIQUE KEY uk_user_email (email),
  KEY idx_user_city (city),
  CONSTRAINT ck_user_gender CHECK (gender IN (0, 1, 2)),
  CONSTRAINT ck_user_status CHECK (status IN (1, 2, 3))
) ENGINE = InnoDB COMMENT = '用户';

-- 第三方登录（微信 / 小程序 openid）
CREATE TABLE user_oauth (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     BIGINT UNSIGNED NOT NULL,
  provider    VARCHAR(20)     NOT NULL COMMENT 'wechat / wxapp / apple',
  open_id     VARCHAR(64)     NOT NULL,
  union_id    VARCHAR(64)     DEFAULT NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_oauth (provider, open_id),
  KEY idx_oauth_user (user_id),
  CONSTRAINT fk_oauth_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '第三方账号绑定';

-- 设备（判定异地登录、踢下线）
CREATE TABLE user_device (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  device_id  VARCHAR(64)     NOT NULL COMMENT '前端生成的设备指纹',
  ua         VARCHAR(255)    DEFAULT NULL,
  last_ip    VARCHAR(45)     DEFAULT NULL,
  last_city  VARCHAR(32)     DEFAULT NULL,
  last_seen  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_device (user_id, device_id),
  CONSTRAINT fk_device_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '登录设备';

-- 会话（MySQL 是持久层，Redis 是热缓存；两者用同一个 jti 关联）
CREATE TABLE user_session (
  jti          CHAR(32)        NOT NULL COMMENT '会话 id（UUID 去掉横线）',
  user_id      BIGINT UNSIGNED NOT NULL,
  device_id    VARCHAR(64)     DEFAULT NULL,
  ip           VARCHAR(45)     DEFAULT NULL,
  ua           VARCHAR(255)    DEFAULT NULL,
  issued_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at   DATETIME        NOT NULL COMMENT '滑动过期：每次访问 +30 分钟',
  revoked_at   DATETIME        DEFAULT NULL COMMENT '非空表示已登出/被踢',
  PRIMARY KEY (jti),
  KEY idx_sess_user (user_id),
  KEY idx_sess_expire (expires_at),
  CONSTRAINT fk_sess_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '登录会话（冷备，Redis 掉电后可恢复）';

-- ------------------------------------------------------------
-- 2. 内容：景点 / 路线 / 轨迹
-- ------------------------------------------------------------
CREATE TABLE poi (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name        VARCHAR(64)     NOT NULL,
  city        VARCHAR(32)     NOT NULL,
  district    VARCHAR(32)     DEFAULT NULL,
  category    VARCHAR(20)     NOT NULL COMMENT '山峰/古镇/湖泊/丹霞…',
  heat        SMALLINT        NOT NULL DEFAULT 0,
  ticket      VARCHAR(40)     DEFAULT NULL,
  suggest_hrs VARCHAR(20)     DEFAULT NULL,
  geom        POINT SRID 4326 NOT NULL,
  intro       TEXT,
  status      TINYINT         NOT NULL DEFAULT 1,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_poi_city (city, category),
  FULLTEXT KEY ft_poi_name (name, intro) WITH PARSER ngram,
  SPATIAL KEY sp_poi_geom (geom)
) ENGINE = InnoDB COMMENT = '景点';

CREATE TABLE poi_photo (
  id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  poi_id    BIGINT UNSIGNED NOT NULL,
  object_key VARCHAR(160)   NOT NULL,
  season    TINYINT         DEFAULT NULL COMMENT '1 春 2 夏 3 秋 4 冬，NULL 表示不限',
  slot      TINYINT         DEFAULT NULL COMMENT '1 日出 2 日落 3 夜景',
  width     SMALLINT        DEFAULT NULL,
  height    SMALLINT        DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_poi_photo (poi_id, season, slot),
  CONSTRAINT fk_photo_poi FOREIGN KEY (poi_id) REFERENCES poi (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '景点图片（四季 / 时段）';

CREATE TABLE trail (
  id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  name        VARCHAR(80)      NOT NULL,
  province    VARCHAR(20)      NOT NULL,
  city        VARCHAR(32)      NOT NULL,
  terrain     VARCHAR(20)      NOT NULL,
  level       TINYINT          NOT NULL COMMENT '1 入门 2 进阶 3 顶级',
  days        TINYINT          NOT NULL DEFAULT 1,
  distance_km DECIMAL(6,2)     NOT NULL,
  climb_m     SMALLINT         NOT NULL DEFAULT 0,
  season      VARCHAR(20)      DEFAULT NULL,
  loop_type   TINYINT          NOT NULL DEFAULT 0 COMMENT '0 穿越 1 环线',
  geom        LINESTRING SRID 4326 NOT NULL COMMENT '抽稀后的预览线（≤2000 点）',
  track_key   VARCHAR(160)     DEFAULT NULL COMMENT '全量 geobuf 在对象存储的 key',
  start_pt    POINT SRID 4326  NOT NULL COMMENT '起点，用于附近路线检索',
  min_lat     DECIMAL(9,6)     NOT NULL,
  max_lat     DECIMAL(9,6)     NOT NULL,
  min_lng     DECIMAL(9,6)     NOT NULL,
  max_lng     DECIMAL(9,6)     NOT NULL,
  desc_text   TEXT,
  created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_trail_area (min_lat, max_lat, min_lng, max_lng),
  KEY idx_trail_city (city, level),
  FULLTEXT KEY ft_trail_name (name, desc_text) WITH PARSER ngram,
  SPATIAL KEY sp_trail_geom (geom),
  SPATIAL KEY sp_trail_start (start_pt),
  CONSTRAINT ck_trail_level CHECK (level IN (1, 2, 3))
) ENGINE = InnoDB COMMENT = '徒步路线';

CREATE TABLE trail_waypoint (
  id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  trail_id  BIGINT UNSIGNED NOT NULL,
  seq       SMALLINT        NOT NULL,
  name      VARCHAR(64)     NOT NULL,
  lat       DECIMAL(9,6)    NOT NULL,
  lng       DECIMAL(9,6)    NOT NULL,
  ele       SMALLINT        DEFAULT NULL,
  km        DECIMAL(5,1)    DEFAULT NULL COMMENT '距起点的公里数',
  supply    VARCHAR(120)    DEFAULT NULL COMMENT '补给 / 水源说明',
  geom      POINT SRID 4326 NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_wp (trail_id, seq),
  SPATIAL KEY sp_wp_geom (geom),
  CONSTRAINT fk_wp_trail FOREIGN KEY (trail_id) REFERENCES trail (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '途经点';

-- 装备：全局 74 项 + 每条路线专属
CREATE TABLE gear_item (
  id        SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  category  VARCHAR(20)      NOT NULL COMMENT '着装/背负/宿营/行进/饮食/导航/急救/杂物',
  name      VARCHAR(40)      NOT NULL,
  must      TINYINT(1)       NOT NULL DEFAULT 0,
  scenes    SET('day','camp','long') NOT NULL DEFAULT 'day,camp,long',
  note      VARCHAR(120)     DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_gear_cat (category)
) ENGINE = InnoDB COMMENT = '装备条目';

CREATE TABLE trail_gear (
  trail_id  BIGINT UNSIGNED  NOT NULL,
  gear_id   SMALLINT UNSIGNED NOT NULL,
  reason    VARCHAR(160)     DEFAULT NULL COMMENT '为什么这条线要带',
  PRIMARY KEY (trail_id, gear_id),
  CONSTRAINT fk_tg_trail FOREIGN KEY (trail_id) REFERENCES trail (id) ON DELETE CASCADE,
  CONSTRAINT fk_tg_gear FOREIGN KEY (gear_id) REFERENCES gear_item (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '路线专属装备';

-- 轨迹点（可选：需要按点检索/海拔分析时用；全量仍放对象存储）
CREATE TABLE trail_track_point (
  trail_id BIGINT UNSIGNED NOT NULL,
  seq      INT UNSIGNED    NOT NULL,
  lat      DECIMAL(9,6)    NOT NULL,
  lng      DECIMAL(9,6)    NOT NULL,
  ele      SMALLINT        DEFAULT NULL,
  km       DECIMAL(6,2)    DEFAULT NULL,
  PRIMARY KEY (trail_id, seq),
  CONSTRAINT fk_tp_trail FOREIGN KEY (trail_id) REFERENCES trail (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '轨迹采样点';

-- ------------------------------------------------------------
-- 3. 社交：收藏 / 帖子 / 评论 / 点赞 / 关注
-- ------------------------------------------------------------
CREATE TABLE favorite (
  user_id     BIGINT UNSIGNED NOT NULL,
  target_type TINYINT         NOT NULL COMMENT '1 景点 2 路线 3 帖子',
  target_id   BIGINT UNSIGNED NOT NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, target_type, target_id),
  KEY idx_fav_target (target_type, target_id, created_at),
  CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '收藏（多态）';

CREATE TABLE post (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  author_id   BIGINT UNSIGNED NOT NULL,
  trail_id    BIGINT UNSIGNED DEFAULT NULL,
  poi_id      BIGINT UNSIGNED DEFAULT NULL,
  title       VARCHAR(120)    DEFAULT NULL,
  body        TEXT            NOT NULL,
  cover_key   VARCHAR(160)    DEFAULT NULL,
  like_cnt    INT UNSIGNED    NOT NULL DEFAULT 0,
  comment_cnt INT UNSIGNED    NOT NULL DEFAULT 0,
  fav_cnt     INT UNSIGNED    NOT NULL DEFAULT 0,
  status      TINYINT         NOT NULL DEFAULT 1 COMMENT '1 已发布 2 审核中 3 驳回',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_post_author (author_id, created_at),
  KEY idx_post_trail (trail_id),
  KEY idx_post_time (created_at),
  FULLTEXT KEY ft_post_body (title, body) WITH PARSER ngram,
  CONSTRAINT fk_post_author FOREIGN KEY (author_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '帖子（量大了再按 created_at 做 RANGE 分区；InnoDB 分区表不支持外键，届时需去掉 fk_post_author，改用应用层约束 + 定时校验）';

CREATE TABLE post_image (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  post_id    BIGINT UNSIGNED NOT NULL,
  seq        TINYINT         NOT NULL,
  object_key VARCHAR(160)    NOT NULL,
  width      SMALLINT        DEFAULT NULL,
  height     SMALLINT        DEFAULT NULL,
  blurhash   VARCHAR(40)     DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_pi_post (post_id, seq),
  CONSTRAINT fk_pi_post FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '帖子图片';

CREATE TABLE post_like (
  user_id    BIGINT UNSIGNED NOT NULL,
  post_id    BIGINT UNSIGNED NOT NULL,
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, post_id),
  KEY idx_like_post (post_id),
  CONSTRAINT fk_like_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_like_post FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '点赞';

CREATE TABLE comment (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  post_id    BIGINT UNSIGNED NOT NULL,
  user_id    BIGINT UNSIGNED NOT NULL,
  parent_id  BIGINT UNSIGNED DEFAULT NULL,
  body       VARCHAR(500)    NOT NULL,
  status     TINYINT         NOT NULL DEFAULT 1,
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cm_post (post_id, created_at),
  CONSTRAINT fk_cm_post FOREIGN KEY (post_id) REFERENCES post (id) ON DELETE CASCADE,
  CONSTRAINT fk_cm_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '评论';

CREATE TABLE follow (
  follower_id BIGINT UNSIGNED NOT NULL,
  followee_id BIGINT UNSIGNED NOT NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, followee_id),
  KEY idx_follow_followee (followee_id),
  CONSTRAINT fk_fl_follower FOREIGN KEY (follower_id) REFERENCES app_user (id) ON DELETE CASCADE,
  CONSTRAINT fk_fl_followee FOREIGN KEY (followee_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '关注';

-- ------------------------------------------------------------
-- 4. 找搭子
-- ------------------------------------------------------------
CREATE TABLE buddy_post (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  owner_id    BIGINT UNSIGNED NOT NULL,
  dest_city   VARCHAR(32)     NOT NULL,
  trail_id    BIGINT UNSIGNED DEFAULT NULL,
  start_date  DATE            NOT NULL,
  end_date    DATE            NOT NULL,
  level_req   TINYINT         NOT NULL DEFAULT 2,
  budget      INT             DEFAULT NULL COMMENT '人均预算（元）',
  gender_pref TINYINT         NOT NULL DEFAULT 0 COMMENT '0 不限 1 男 2 女',
  slots       TINYINT         NOT NULL DEFAULT 1 COMMENT '还差几人',
  tags        VARCHAR(120)    DEFAULT NULL COMMENT '逗号分隔兴趣标签',
  intro       VARCHAR(300)    DEFAULT NULL,
  geom        POINT SRID 4326 NOT NULL COMMENT '目的地坐标；空间索引要求 NOT NULL，发起招募必须选点',
  status      TINYINT         NOT NULL DEFAULT 1 COMMENT '1 招募中 2 已满 3 关闭',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_buddy_city_date (dest_city, start_date, end_date),
  KEY idx_buddy_owner (owner_id),
  SPATIAL KEY sp_buddy_geom (geom),
  CONSTRAINT fk_buddy_owner FOREIGN KEY (owner_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '找搭子招募帖';

CREATE TABLE buddy_apply (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  buddy_id   BIGINT UNSIGNED NOT NULL,
  user_id    BIGINT UNSIGNED NOT NULL,
  message    VARCHAR(200)    DEFAULT NULL,
  status     TINYINT         NOT NULL DEFAULT 0 COMMENT '0 待处理 1 同意 2 拒绝',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_apply (buddy_id, user_id),
  KEY idx_apply_user (user_id),
  CONSTRAINT fk_apply_buddy FOREIGN KEY (buddy_id) REFERENCES buddy_post (id) ON DELETE CASCADE,
  CONSTRAINT fk_apply_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '搭子申请（双向同意才开聊）';

-- ------------------------------------------------------------
-- 5. 私信
-- ------------------------------------------------------------
CREATE TABLE conversation (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_a      BIGINT UNSIGNED NOT NULL COMMENT '小的 user_id',
  user_b      BIGINT UNSIGNED NOT NULL COMMENT '大的 user_id',
  last_msg_at DATETIME        DEFAULT NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_conv (user_a, user_b),
  KEY idx_conv_time (last_msg_at)
) ENGINE = InnoDB COMMENT = '会话（user_a < user_b 去重）';

CREATE TABLE message (
  id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  conv_id  BIGINT UNSIGNED NOT NULL,
  from_id  BIGINT UNSIGNED NOT NULL,
  body     VARCHAR(1000)   NOT NULL,
  read_at  DATETIME        DEFAULT NULL,
  created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_msg_conv (conv_id, created_at),
  CONSTRAINT fk_msg_conv FOREIGN KEY (conv_id) REFERENCES conversation (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '私信';

-- ------------------------------------------------------------
-- 6. 附近的人（模糊位置）
-- ------------------------------------------------------------
CREATE TABLE presence (
  user_id     BIGINT UNSIGNED NOT NULL,
  geohash6    CHAR(6)         NOT NULL COMMENT '约 1.2km × 0.6km 网格',
  geom        POINT SRID 4326 NOT NULL COMMENT '网格中心 + ±150m 抖动后的模糊点',
  city        VARCHAR(32)     DEFAULT NULL,
  visible     TINYINT(1)      NOT NULL DEFAULT 1,
  updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  KEY idx_presence_geo (geohash6),
  SPATIAL KEY sp_presence_geom (geom),
  KEY idx_presence_time (updated_at),
  CONSTRAINT fk_presence_user FOREIGN KEY (user_id) REFERENCES app_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '附近的人（30 分钟过期）';

-- ------------------------------------------------------------
-- 7. 审计与计数
-- ------------------------------------------------------------
CREATE TABLE audit_log (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED DEFAULT NULL,
  action     VARCHAR(40)     NOT NULL COMMENT 'login / logout / post / apply …',
  ip         VARCHAR(45)     DEFAULT NULL,
  ua         VARCHAR(255)    DEFAULT NULL,
  payload    JSON            DEFAULT NULL,
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_audit_user (user_id, created_at)
) ENGINE = InnoDB COMMENT = '审计日志';

-- 触发器：点赞 / 评论后维护计数（异步任务会做一次校正）
DELIMITER $$

CREATE TRIGGER trg_like_after_insert
AFTER INSERT ON post_like
FOR EACH ROW
BEGIN
  UPDATE post SET like_cnt = like_cnt + 1 WHERE id = NEW.post_id;
END$$

CREATE TRIGGER trg_like_after_delete
AFTER DELETE ON post_like
FOR EACH ROW
BEGIN
  UPDATE post SET like_cnt = IF(like_cnt > 0, like_cnt - 1, 0) WHERE id = OLD.post_id;
END$$

CREATE TRIGGER trg_comment_after_insert
AFTER INSERT ON comment
FOR EACH ROW
BEGIN
  UPDATE post SET comment_cnt = comment_cnt + 1 WHERE id = NEW.post_id;
END$$

DELIMITER ;

-- 视图：路线卡片（列表页直接用，省掉多表拼装）
CREATE OR REPLACE VIEW v_trail_card AS
SELECT
  t.id,
  t.name,
  t.city,
  t.province,
  t.terrain,
  t.level,
  t.days,
  t.distance_km,
  t.climb_m,
  t.season,
  t.loop_type,
  (SELECT COUNT(*) FROM favorite f WHERE f.target_type = 2 AND f.target_id = t.id) AS fav_cnt,
  (SELECT COUNT(*) FROM post p WHERE p.trail_id = t.id AND p.status = 1)          AS post_cnt
FROM trail t;

-- 视图：用户收藏（景点 + 路线，带名称，供 /me 页一次取回）
CREATE OR REPLACE VIEW v_user_favorite AS
SELECT f.user_id, f.target_type, f.target_id, f.created_at,
       CASE f.target_type WHEN 1 THEN p.name WHEN 2 THEN t.name ELSE NULL END AS title
FROM favorite f
LEFT JOIN poi   p ON f.target_type = 1 AND p.id = f.target_id
LEFT JOIN trail t ON f.target_type = 2 AND t.id = f.target_id;
