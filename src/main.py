import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from src.config.settings import settings
from src.api.topic_api import router as topic_v1_router
from src.api.topic_api_v2 import router as topic_v2_router
from src.api.topic_api_v3 import router as topic_v3_router
from src.api.healthcheck import router as healthcheck_router
from src.controller.menuController import router as menu_router
from src.auth.api import router as auth_router
from src.agentv3.capabilities.register import register_all
from src.agentv3.registry import CapabilityRegistry

register_all()
CapabilityRegistry.freeze()

app = FastAPI(title="TopicSystem v3", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topic_v1_router)
app.include_router(topic_v2_router)
app.include_router(topic_v3_router)
app.include_router(healthcheck_router)
app.include_router(auth_router)  # 鉴权
app.include_router(menu_router)


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

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
