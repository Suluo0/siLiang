import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import register_tortoise
from src.config.settings import settings
from src.api.topic_api import router as topic_router
from src.api.healthcheck import router as healthcheck_router
from src.api.menu_api import router as menu_router
from src.auth.api import router as auth_router
from src.api.interview_api import router as interview_router
from src.middleware import auth_middleware, quota_middleware, security_headers_middleware
from src.agentv3.capabilities.register import register_all
from src.agentv3.registry import CapabilityRegistry
import asyncio
import logging

logger = logging.getLogger(__name__)

register_all()
CapabilityRegistry.freeze()

app = FastAPI(title="TopicSystem v3", version="0.3.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器：隐藏内部错误细节，返回稳定错误码"""
    logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error_code": "INTERNAL_ERROR"},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """处理参数验证错误"""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ── 全局中间件 ──
app.middleware("http")(quota_middleware)
app.middleware("http")(auth_middleware)
app.middleware("http")(security_headers_middleware)

app.include_router(topic_router)
app.include_router(healthcheck_router)
app.include_router(auth_router)
app.include_router(menu_router)
app.include_router(interview_router)


@app.get("/")
async def root():
    return {"service": "TopicSystem v3", "status": "ok", "capabilities": len(CapabilityRegistry.list_ids())}


register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["src.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


@app.on_event("startup")
async def _startup_sync_table_schemas():
    """启动时将表结构元数据同步到 Milvus table_schemas 集合"""
    try:
        from src.tools.schema_manager import sync_table_schemas_to_milvus
        count = sync_table_schemas_to_milvus()
        if count:
            import logging
            logging.getLogger("uvicorn").info(f"Table schemas synced to Milvus: {count} tables")
    except Exception:
        pass


@app.on_event("startup")
async def _start_outbox_worker():
    """启动 outbox 补偿 & 清理 Worker"""
    from src.workers.outbox_worker import run_outbox_worker
    asyncio.create_task(run_outbox_worker())


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
