-- ============================================================
--  野径 · 旅行社交平台　核心查询集
--  文件：03_queries.sql　（逐条可直接跑，用于答辩演示 / 性能对比）
-- ============================================================
USE yejing;
SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- Q1　登录：校验账号 + 取哈希（应用层再验 Argon2id）
-- ------------------------------------------------------------
SELECT id, nickname, password_hash, status
FROM app_user
WHERE phone = '13800001234' OR email = 'aye@example.com';

-- ------------------------------------------------------------
-- Q2　会话：签发（Redis 同步 SETEX sess:{uid}:{jti} 1800）
-- ------------------------------------------------------------
INSERT INTO user_session (jti, user_id, device_id, ip, ua, expires_at)
VALUES ('a1b2c3d4e5f60718293a4b5c6d7e8f90', 1, 'dev-iphone-15', '113.32.1.10', 'iPhone Safari',
        DATE_ADD(NOW(), INTERVAL 30 MINUTE))
-- 脚本要能反复跑：同一个 jti 再签发时视为「重登」，续期而不是报主键冲突
ON DUPLICATE KEY UPDATE
  last_seen_at = NOW(),
  expires_at   = DATE_ADD(NOW(), INTERVAL 30 MINUTE),
  revoked_at   = NULL;

-- Q2.1　每次请求命中后的滑动续期（MySQL 侧审计；Redis 侧 EXPIRE）
UPDATE user_session
SET last_seen_at = NOW(), expires_at = DATE_ADD(NOW(), INTERVAL 30 MINUTE)
WHERE jti = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
  AND revoked_at IS NULL
  AND expires_at > NOW();

-- Q2.2　清理过期会话（定时任务，每天一次；只保留 7 天用于审计）
DELETE FROM user_session
WHERE expires_at < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- Q2.3　踢下线：某用户全部会话
UPDATE user_session SET revoked_at = NOW()
WHERE user_id = 1 AND revoked_at IS NULL;

-- ------------------------------------------------------------
-- Q3　收藏：切换（存在则删、不存在则插）+ 列表
-- ------------------------------------------------------------
INSERT INTO favorite (user_id, target_type, target_id) VALUES (1, 2, 2)
ON DUPLICATE KEY UPDATE created_at = created_at;          -- 幂等收藏

DELETE FROM favorite WHERE user_id = 1 AND target_type = 2 AND target_id = 2;

SELECT target_type, target_id, title, created_at
FROM v_user_favorite
WHERE user_id = 1
ORDER BY created_at DESC;

-- ------------------------------------------------------------
-- Q4　附近的人：500m / 1km / 3km 分档（先粗筛后精算）
-- ------------------------------------------------------------
SET @me = ST_GeomFromText('POINT(23.106600 113.324500)', 4326);

SELECT
  p.user_id,
  u.nickname,
  u.gender,
  p.city,
  ROUND(ST_Distance_Sphere(p.geom, @me)) AS meters,
  CASE
    WHEN ST_Distance_Sphere(p.geom, @me) <= 500  THEN '500m 内'
    WHEN ST_Distance_Sphere(p.geom, @me) <= 1000 THEN '1km 内'
    WHEN ST_Distance_Sphere(p.geom, @me) <= 3000 THEN '3km 内'
    ELSE '5km 内'
  END AS band
FROM presence p
JOIN app_user u ON u.id = p.user_id
WHERE p.visible = 1
  AND p.updated_at > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
  AND p.user_id <> 1
  AND ST_Distance_Sphere(p.geom, @me) <= 5000
ORDER BY meters
LIMIT 200;

-- Q4.1　同上但先用 geohash 前缀过滤（命中 idx_presence_geo，减少扫描）
SELECT user_id, geohash6
FROM presence
WHERE geohash6 LIKE 'ws0gz%'
  AND visible = 1
  AND updated_at > DATE_SUB(NOW(), INTERVAL 30 MINUTE);

-- ------------------------------------------------------------
-- Q5　找搭子：时间重叠硬过滤 + 加权打分
--     重叠系数 = 重叠天数 / 较短行程天数
-- ------------------------------------------------------------
SET @from = '2026-11-13';
SET @to   = '2026-11-16';

SELECT
  b.id,
  b.owner_id,
  u.nickname,
  b.dest_city,
  b.start_date,
  b.end_date,
  b.slots,
  b.tags,
  DATEDIFF(LEAST(b.end_date, @to), GREATEST(b.start_date, @from)) + 1 AS overlap_days,
  ROUND(
      (DATEDIFF(LEAST(b.end_date, @to), GREATEST(b.start_date, @from)) + 1)
      / (DATEDIFF(b.end_date, b.start_date) + 1), 2) AS overlap_ratio,
  ROUND(
      0.35 * ((DATEDIFF(LEAST(b.end_date, @to), GREATEST(b.start_date, @from)) + 1)
              / (DATEDIFF(b.end_date, b.start_date) + 1))
    + 0.25 * (CASE WHEN b.level_req <= 2 THEN 0.9 ELSE 0.6 END)
    + 0.15 * (CASE WHEN u.last_login_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0.4 END)
    + 0.15 * 0.8
    + 0.10 * EXP(-(ST_Distance_Sphere(b.geom, ST_GeomFromText('POINT(23.1066 113.3245)', 4326)) / 1000) / 50)
  , 3) AS score
FROM buddy_post b
JOIN app_user u ON u.id = b.owner_id
WHERE b.status = 1
  AND b.owner_id <> 1
  AND b.dest_city IN ('萍乡', '长沙')
  AND b.start_date <= @to
  AND b.end_date   >= @from                 -- 时间窗有交集
  AND (b.gender_pref = 0 OR b.gender_pref = 1)
ORDER BY score DESC, b.start_date
LIMIT 20;

-- Q5.1　申请（同一人对同一帖只能申请一次）
INSERT INTO buddy_apply (buddy_id, user_id, message, status)
VALUES (1, 2, '走过两次武功山，装备齐全', 0)
ON DUPLICATE KEY UPDATE message = VALUES(message);

-- Q5.2　同意后建会话（user_a 取小值，保证唯一）
INSERT INTO conversation (user_a, user_b, last_msg_at)
SELECT LEAST(b.owner_id, 2), GREATEST(b.owner_id, 2), NOW()
FROM buddy_post b WHERE b.id = 1
ON DUPLICATE KEY UPDATE last_msg_at = NOW();

-- ------------------------------------------------------------
-- Q6　地图：视野内路线（先用 bbox 走普通索引，再精确判交）
-- ------------------------------------------------------------
SELECT id, name, city, distance_km, climb_m
FROM trail
WHERE min_lat <= 28.25 AND max_lat >= 28.10
  AND min_lng <= 112.95 AND max_lng >= 112.85
  AND ST_Intersects(
        geom,
        ST_GeomFromText('POLYGON((28.10 112.85,28.10 112.95,28.25 112.95,28.25 112.85,28.10 112.85))', 4326)
      )
LIMIT 200;

-- Q6.1　附近 3km 内有路线的入口（用 start_pt 的空间索引）
SELECT id, name, ROUND(ST_Distance_Sphere(start_pt, ST_GeomFromText('POINT(28.1830 112.9384)', 4326))) AS m
FROM trail
WHERE ST_Distance_Sphere(start_pt, ST_GeomFromText('POINT(28.1830 112.9384)', 4326)) <= 3000
ORDER BY m
LIMIT 50;

-- Q6.2　路线长度（球面，单位米；对比表里的 distance_km 做校验）
SELECT id, name,
       ROUND(ST_Length(geom) * 111319.9) AS approx_meters
FROM trail;

-- ------------------------------------------------------------
-- Q7　Feed：我关注的人最近发的帖（推拉结合的「拉」分支）
-- ------------------------------------------------------------
SELECT p.id, p.title, p.cover_key, p.like_cnt, p.created_at, u.nickname
FROM post p
JOIN follow f ON f.followee_id = p.author_id AND f.follower_id = 1
JOIN app_user u ON u.id = p.author_id
WHERE p.status = 1
  AND p.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY p.created_at DESC
LIMIT 20;

-- Q7.1　按标签/正文搜索（ngram 全文索引，中文可用）
SELECT id, title, MATCH(title, body) AGAINST ('桃花岭' IN NATURAL LANGUAGE MODE) AS score
FROM post
WHERE MATCH(title, body) AGAINST ('桃花岭' IN NATURAL LANGUAGE MODE)
ORDER BY score DESC
LIMIT 20;

-- ------------------------------------------------------------
-- Q8　计数校正（异步任务：以明细为准回写冗余计数）
-- ------------------------------------------------------------
UPDATE post p
SET p.like_cnt = (SELECT COUNT(*) FROM post_like l WHERE l.post_id = p.id),
    p.comment_cnt = (SELECT COUNT(*) FROM comment c WHERE c.post_id = p.id AND c.status = 1)
WHERE p.id IN (1, 2, 3, 4);

-- ------------------------------------------------------------
-- Q9　性能自检（答辩时可现场跑）
-- ------------------------------------------------------------
EXPLAIN ANALYZE
SELECT user_id, ST_Distance_Sphere(geom, ST_GeomFromText('POINT(23.1066 113.3245)', 4326)) AS m
FROM presence
WHERE ST_Distance_Sphere(geom, ST_GeomFromText('POINT(23.1066 113.3245)', 4326)) <= 3000
ORDER BY m LIMIT 50;

EXPLAIN ANALYZE
SELECT id, name FROM trail
WHERE min_lat <= 28.25 AND max_lat >= 28.10 AND min_lng <= 112.95 AND max_lng >= 112.85;
