-- ============================================================
--  野径 · 旅行社交平台　应用账号（最小权限）
--  文件：04_user.sql
--  说明：应用不该用 root 连库。这里建两个只有数据权限的账号，
--        没有 DDL / DROP / GRANT，误操作也删不掉表。
--
--  【本机实测记录 2026-11-06】
--  一开始账号名用的是 yejing_app，建出来后 mysql.user 里 hash、
--  host、属性全对，但无论怎么 FLUSH PRIVILEGES / RENAME / 改密码，
--  登录始终 1045 Access denied；同样密码换成 yj_app 立刻能登。
--  查过 HEX(user) 无隐藏字符、User_attributes 为 NULL、无 role、
--  account_locked=N、password_expired=N，SHOW CREATE USER 两条定义逐字相同。
--  属于该实例的 ACL 残留（未重启服务，无管理员权限，没法验证重启后是否恢复）。
--  所以最终账号名定为 yj_app / yj_ro —— 名字短一点，也避开这个坑。
--  换一台机器部署时若 yejing_app 正常，把下面三处名字改回去即可。
-- ============================================================

-- 读写账号：给 API 服务用
CREATE USER IF NOT EXISTS 'yj_app'@'localhost' IDENTIFIED BY 'YeJing2026_App';
GRANT SELECT, INSERT, UPDATE, DELETE ON yejing.* TO 'yj_app'@'localhost';

-- 只读账号：给报表 / 答辩演示用，避免误改数据
CREATE USER IF NOT EXISTS 'yj_ro'@'localhost' IDENTIFIED BY 'YeJing2026_Read';
GRANT SELECT ON yejing.* TO 'yj_ro'@'localhost';

FLUSH PRIVILEGES;

SELECT '应用账号已就绪' AS msg,
       'yj_app（读写）/ yj_ro（只读）' AS accounts;
