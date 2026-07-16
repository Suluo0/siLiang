-- 数据库角色权限初始化
-- 三角色: topic_admin (DDL), topic_app (读写), topic_read (只读)
-- 用法: psql -v admin_password="$DB_ADMIN_PASSWORD" -v app_password="$DB_APP_PASSWORD" \
--            -v read_password="$DB_READ_PASSWORD" -f scripts/init_db_roles.sql
\if :{?admin_password}
\else
  \echo 'missing psql variable: admin_password'
  \quit
\endif
\if :{?app_password}
\else
  \echo 'missing psql variable: app_password'
  \quit
\endif
\if :{?read_password}
\else
  \echo 'missing psql variable: read_password'
  \quit
\endif

SELECT format('CREATE ROLE topic_admin WITH LOGIN PASSWORD %L', :'admin_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_admin') \gexec
SELECT format('CREATE ROLE topic_app WITH LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_app') \gexec
SELECT format('CREATE ROLE topic_read WITH LOGIN PASSWORD %L', :'read_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'topic_read') \gexec

SELECT format('ALTER ROLE topic_admin PASSWORD %L', :'admin_password') \gexec
SELECT format('ALTER ROLE topic_app PASSWORD %L', :'app_password') \gexec
SELECT format('ALTER ROLE topic_read PASSWORD %L', :'read_password') \gexec

-- 赋权
GRANT ALL PRIVILEGES ON DATABASE topic TO topic_admin;
GRANT CONNECT ON DATABASE topic TO topic_app, topic_read;

GRANT USAGE ON SCHEMA public TO topic_app, topic_read;
REVOKE CREATE ON SCHEMA public FROM topic_read;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO topic_app;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM topic_read;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO topic_app;

-- NL-to-SQL 只读角色仅能访问经审核的业务表。
DO $$
DECLARE
    table_name text;
    allowed_tables text[] := ARRAY[
        'topic', 'topic_prerequisite', 'topic_core_concept', 'topic_derivative',
        'topic_extension', 'topic_evaluation_anchor', 'topic_similar_question',
        'topic_advanced_question', 'topic_reference', 'topic_review_log',
        'knowledge_dict', 'knowledge_alias', 'user_topic_status',
        'user_topic_progress', 'job_position', 'interview_persona',
        'interview_room', 'interview_round', 'interview_summary'
    ];
BEGIN
    FOREACH table_name IN ARRAY allowed_tables LOOP
        IF to_regclass(format('public.%I', table_name)) IS NOT NULL THEN
            EXECUTE format('GRANT SELECT ON TABLE public.%I TO topic_read', table_name);
        END IF;
    END LOOP;
END
$$;

-- 新表自动继承
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO topic_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO topic_app;
