#!/bin/sh
# TopicSystem container entrypoint
# 1) 跑 aerich 数据库迁移（首次安装也会走 init-db / upgrade）
# 2) 启动 uvicorn
set -e

echo "[entrypoint] $(date -Iseconds) aerich upgrade ..."
# 迁移失败时不立刻退出 — 允许首次干净启动；真实异常会在 uvicorn 启动后
# 通过 /ping 健康检查暴露
if aerich upgrade; then
    echo "[entrypoint] migration OK"
else
    echo "[entrypoint] migration skipped/failed (continuing)"
fi

WORKERS="${UVICORN_WORKERS:-2}"
echo "[entrypoint] starting uvicorn (workers=${WORKERS}) ..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
