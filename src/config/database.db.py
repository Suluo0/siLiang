import os
from tortoise import Tortoise

# 独立出配置，方便 Aerich 识别
DB_CONFIG = {
    "connections": {"default": os.getenv("DATABASE_URL")},
    "apps": {
        "models": {
            # 这里的 models 依然指向 infra，实现解耦
            "models": ["src.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

async def init_db():
    # 纯手工初始化，或者被 main.py 的 register_tortoise 调用
    await Tortoise.init(**DB_CONFIG)  # 使用两个星号解包字典