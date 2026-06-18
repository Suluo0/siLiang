# TopicSystem 测试 / 开发统一入口
.PHONY: help install test test-fast test-all test-unit test-integration test-e2e cov lint fmt clean setup-test-db deploy deploy-skip-build deploy-logs deploy-rollback docker-build

VENV_BIN := .venv/bin
PY := $(VENV_BIN)/python
PYTEST := $(VENV_BIN)/python -m pytest

# 自动加载 .env.test (如果存在)
-include .env.test
export

help: ## 显示本帮助
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## 装依赖到 .venv
	@uv venv --python 3.13 .venv 2>/dev/null || true
	@. $(VENV_BIN)/activate && uv pip install -r requirements.txt pytest pytest-asyncio pytest-cov pytest-mock pytest-timeout ruff httpx
	@echo "✅ 依赖装好"

setup-test-db: ## 建本地测试库 topic_test
	@psql -U postgres -h localhost -c "SELECT 1 FROM pg_database WHERE datname='topic_test'" -t 2>&1 | grep -q 1 \
		&& echo "✅ topic_test 已存在" \
		|| (psql -U postgres -h localhost -c "CREATE DATABASE topic_test;" && echo "✅ 创建 topic_test")

test: test-fast ## 默认快测(unit + integration,排除 e2e/slow)

test-fast: ## 快速测试(默认 addopts 配置)
	@$(PYTEST)

test-unit: ## 只跑 unit
	@$(PYTEST) -m unit

test-integration: ## 只跑 integration
	@$(PYTEST) -m integration

test-e2e: ## 跑 e2e + slow(需要本地 Milvus + LLM 真实 key)
	@$(PYTEST) -m "e2e or slow" --override-ini="addopts=-v --tb=short --strict-markers"

test-all: ## 全测,包括 e2e
	@$(PYTEST) --override-ini="addopts=-v --tb=short --strict-markers"

cov: ## 跑测 + 覆盖率(html 在 htmlcov/)
	@$(PYTEST) --cov=src --cov-report=term-missing:skip-covered --cov-report=html
	@echo "📊 HTML 报告: file://$(shell pwd)/htmlcov/index.html"

cov-open: cov ## 跑测 + 自动开浏览器看报告
	@open htmlcov/index.html

lint: ## ruff check
	@$(VENV_BIN)/ruff check src tests

fmt: ## ruff format
	@$(VENV_BIN)/ruff format src tests

clean: ## 清缓存
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov .coverage .ruff_cache
	@echo "✅ 清理完成"

baseline: ## 跑一次 baseline,输出到 /tmp/test_baseline.log
	@$(PYTEST) --tb=line 2>&1 | tee /tmp/test_baseline.log
	@echo "📝 Baseline saved: /tmp/test_baseline.log"

# ─────────── 部署 ───────────
DEPLOY_HOST ?= root@115.190.161.132
DEPLOY_PATH ?= /opt/siLiang

RSYNC_EXCLUDES := \
	--exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' \
	--exclude='.pytest_cache/' --exclude='.ruff_cache/' --exclude='htmlcov/' \
	--exclude='.coverage' --exclude='.env' --exclude='.env.test' --exclude='.env.local' \
	--exclude='.opencode/' --exclude='node_modules/' \
	--exclude='TOPICSYSTEM_Web/dist/' --exclude='TOPICSYSTEM_Web/node_modules/' \
	--exclude='relay-server/' --exclude='test_output/' \
	--exclude='.DS_Store' --exclude='._.*'

docker-build: ## 本地试构建 app 镜像（不推送）
	@docker build -t siliang-app:dev .

deploy: ## 推代码到服务器 + 构建 + 重启 + 健康检查
	@echo "═══ rsync → $(DEPLOY_HOST):$(DEPLOY_PATH) ═══"
	@rsync -az --delete $(RSYNC_EXCLUDES) ./ $(DEPLOY_HOST):$(DEPLOY_PATH)/
	@echo "═══ remote deploy ═══"
	@ssh $(DEPLOY_HOST) "cd $(DEPLOY_PATH) && bash scripts/deploy.sh"

deploy-skip-build: ## 只重启 app(不重新 build,适合调环境变量后快速生效)
	@rsync -az --delete $(RSYNC_EXCLUDES) ./ $(DEPLOY_HOST):$(DEPLOY_PATH)/
	@ssh $(DEPLOY_HOST) "cd $(DEPLOY_PATH) && SKIP_BUILD=1 bash scripts/deploy.sh"

deploy-logs: ## 查看线上 app 容器最近 200 行日志
	@ssh $(DEPLOY_HOST) "cd $(DEPLOY_PATH) && docker compose -f docker-compose.server.yml logs --tail=200 app"

deploy-rollback: ## 紧急回滚到 :rollback tag(若存在)
	@ssh $(DEPLOY_HOST) "docker tag siliang-app:rollback siliang-app:latest && cd $(DEPLOY_PATH) && SKIP_BUILD=1 bash scripts/deploy.sh"
