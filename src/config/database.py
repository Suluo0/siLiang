from contextlib import asynccontextmanager
from tortoise import Tortoise
from src.config.settings import settings

_MODULES = {"models": ["src.models"]}


async def init_db():
    await Tortoise.init(db_url=settings.DATABASE_URL, modules=_MODULES)


async def close_db():
    await Tortoise.close_connections()


@asynccontextmanager
async def db_lifespan():
    await init_db()
    try:
        yield
    finally:
        await close_db()
