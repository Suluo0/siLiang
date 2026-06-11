#!/bin/bash
set -e

echo "═══ TopicSystem Deploy ═══"

# 1. 拉取最新代码
cd /opt/siLiang
git pull origin main 2>/dev/null || echo "  [skip] git pull (no updates)"

# 2. 环境变量
if [ ! -f .env ]; then
    cp .env.production .env
    echo "  [warn] .env not found, copied from .env.production — please edit"
    exit 1
fi

# 3. 构建镜像
echo "  Building app image..."
docker compose build app 2>&1 | tail -3

# 4. 数据库迁移
echo "  Running migrations..."
docker compose run --rm --no-deps app aerich upgrade 2>&1 | tail -3 || echo "  [warn] migrate skipped (may be first run)"

# 5. 启动服务
echo "  Starting services..."
docker compose up -d 2>&1 | tail -5

# 6. 健康检查
echo "  Health check..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/ping > /dev/null 2>&1; then
        echo "  ✅ Deploy OK (http://localhost:8000/ping)"
        exit 0
    fi
    sleep 2
done
echo "  ❌ Deploy timeout"
exit 1
