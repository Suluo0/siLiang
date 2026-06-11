-- 数据库角色权限初始化
-- 三角色: topic_admin (DDL), topic_app (读写), topic_read (只读)

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_admin') THEN
        CREATE ROLE topic_admin WITH LOGIN PASSWORD 'Top1cAdm1n#2026';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_app') THEN
        CREATE ROLE topic_app WITH LOGIN PASSWORD 'Top1cApp#2026';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_read') THEN
        CREATE ROLE topic_read WITH LOGIN PASSWORD 'Top1cRead#2026';
    END IF;
END
$$;

-- 赋权
GRANT ALL PRIVILEGES ON DATABASE topic TO topic_admin;
GRANT CONNECT ON DATABASE topic TO topic_app, topic_read;

GRANT USAGE ON SCHEMA public TO topic_app, topic_read;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO topic_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO topic_read;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO topic_app;

-- 新表自动继承
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO topic_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO topic_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO topic_app;
