#!/bin/bash
# TopicSystem deploy script (server-side)
# 用法:
#   bash scripts/deploy.sh             # 完整部署 (build + migrate via entrypoint + up + healthcheck)
#   SKIP_BUILD=1 bash scripts/deploy.sh   # 跳过 build (复用现有镜像快速重启)
#   COMPOSE_FILE=docker-compose.yml ...  # 切换 compose 文件
#
# 依赖: docker, docker compose v2, curl
# 必备文件: .env (含 POSTGRES_PASSWORD / JWT_SECRET / DATABASE_URL / TS_DS_APIKEY)
set -euo pipefail

# 项目根目录 = 脚本所在目录的上一级
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SKIP_BUILD="${SKIP_BUILD:-0}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.server.yml}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/ping}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"

echo "═══ TopicSystem Deploy ═══"
echo "  ROOT_DIR     = $ROOT_DIR"
echo "  COMPOSE_FILE = $COMPOSE_FILE"
echo "  SKIP_BUILD   = $SKIP_BUILD"

# ── 0. 前置检查 ──
if [ ! -f .env ]; then
    echo "❌ .env not found at $ROOT_DIR/.env"
    [ -f .env.production ] && echo "  → 提示: 可参考 .env.production"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ docker not installed"; exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "❌ docker compose v2 not available"; exit 1
fi

# ── 1. 记录当前 app 镜像（回滚用） ──
PREV_IMAGE_ID=$(docker inspect siliang-app --format '{{.Image}}' 2>/dev/null || echo "")
[ -n "$PREV_IMAGE_ID" ] && echo "  PREV_IMAGE   = $PREV_IMAGE_ID"

# ── 2. Build ──
if [ "$SKIP_BUILD" = "0" ]; then
    echo ""
    echo "═══ [1/3] Building app image ═══"
    if ! docker compose -f "$COMPOSE_FILE" build app; then
        echo "❌ Build failed — aborting (existing container untouched)"
        exit 1
    fi
else
    echo "  [skip] build (SKIP_BUILD=1)"
fi

# ── 3. Up（compose 自动滚动替换；非 app 服务若已 healthy 则不会重启） ──
echo ""
echo "═══ [2/3] Starting services ═══"
docker compose -f "$COMPOSE_FILE" up -d

# ── 4. Health check ──
echo ""
echo "═══ [3/3] Health check (timeout=${HEALTH_TIMEOUT}s) ═══"
SECONDS_WAITED=0
while [ "$SECONDS_WAITED" -lt "$HEALTH_TIMEOUT" ]; do
    if curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        echo "✅ Deploy OK ($HEALTH_URL)"
        # 清理悬空镜像（保持磁盘干净）
        docker image prune -f >/dev/null 2>&1 || true
        exit 0
    fi
    sleep 2
    SECONDS_WAITED=$((SECONDS_WAITED + 2))
    printf "."
done
echo ""

# ── 5. 失败回滚 ──
echo "❌ Health check timeout (${HEALTH_TIMEOUT}s)"
docker compose -f "$COMPOSE_FILE" logs --tail=50 app || true

if [ -n "$PREV_IMAGE_ID" ]; then
    echo ""
    echo "═══ Rolling back to previous image ═══"
    docker tag "$PREV_IMAGE_ID" siliang-app:latest
    docker compose -f "$COMPOSE_FILE" up -d app
    sleep 5
    if curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        echo "⚠️  Rolled back to previous image — check logs for the cause"
    else
        echo "❌ Rollback also failed — manual intervention required"
    fi
else
    echo "  (no previous image to rollback to)"
fi
exit 1
