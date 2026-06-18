# syntax=docker/dockerfile:1.6
# 单阶段（依赖全是 PyPI 预编译 wheel，不需要 build-essential）
FROM python:3.13-slim

WORKDIR /app

# 国内 PyPI 镜像（debian apt 源不动它，运行时只需要 curl，base 镜像已带）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 运行期工具：curl 用于 HEALTHCHECK；libpq5 备用（asyncpg 不强依赖，但留着省心）
# 切阿里云源 → 加快 apt-get（debian 官方源国内拉不动）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null \
    || true \
 && apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -u 1000 app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 业务代码 + 迁移配置 + entrypoint（chown 一次）
COPY --chown=app:app src/ ./src/
COPY --chown=app:app aerich.ini ./
COPY --chown=app:app migrations/ ./migrations/
COPY --chown=app:app scripts/entrypoint.sh ./scripts/entrypoint.sh

RUN chmod +x ./scripts/entrypoint.sh && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fs http://localhost:8000/ping || exit 1

ENTRYPOINT ["./scripts/entrypoint.sh"]
