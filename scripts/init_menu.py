"""
初始化菜单数据
"""
import asyncio
import os
from dotenv import load_dotenv
from tortoise import Tortoise
from src.models import Menu

load_dotenv()

MENU_DATA = [
    # 一级菜单
    {"id": 1, "name": "首页", "path": "/dashboard", "icon": "HomeFilled", "parent_id": None, "sort_order": 1, "is_visible": True, "component": "/dashboard/index"},
    {"id": 2, "name": "用户管理", "path": "/user", "icon": "User", "parent_id": None, "sort_order": 2, "is_visible": True, "component": None},
    {"id": 3, "name": "主题管理", "path": "/topic", "icon": "Collection", "parent_id": None, "sort_order": 3, "is_visible": True, "component": None},
    {"id": 4, "name": "技能生成", "path": "/skill", "icon": "Cpu", "parent_id": None, "sort_order": 4, "is_visible": True, "component": None},
    {"id": 5, "name": "系统设置", "path": "/system", "icon": "Setting", "parent_id": None, "sort_order": 5, "is_visible": True, "component": None},
    
    # 用户管理子菜单
    {"id": 21, "name": "用户列表", "path": "/user/list", "icon": None, "parent_id": 2, "sort_order": 21, "is_visible": True, "component": "/user/List"},
    {"id": 22, "name": "用户等级", "path": "/user/level", "icon": None, "parent_id": 2, "sort_order": 22, "is_visible": True, "component": "/user/Level"},
    
    # 主题管理子菜单
    {"id": 31, "name": "主题列表", "path": "/topic/list", "icon": None, "parent_id": 3, "sort_order": 31, "is_visible": True, "component": "/topic/List"},
    {"id": 32, "name": "主题分类", "path": "/topic/category", "icon": None, "parent_id": 3, "sort_order": 32, "is_visible": True, "component": "/topic/Category"},
    
    # 系统设置子菜单
    {"id": 51, "name": "菜单管理", "path": "/system/menu", "icon": None, "parent_id": 5, "sort_order": 51, "is_visible": True, "component": "/system/Menu"},
    {"id": 52, "name": "权限管理", "path": "/system/permission", "icon": None, "parent_id": 5, "sort_order": 52, "is_visible": True, "component": "/system/Permission"},
]


async def init_menus():
    """初始化菜单数据"""
    db_url = os.getenv("DATABASE_URL")
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["src.models"]},
    )
    await Tortoise.generate_schemas()
    
    # 清空现有菜单
    await Menu.all().delete()
    
    # 插入新菜单
    for menu_data in MENU_DATA:
        await Menu.create(**menu_data)
    
    print("菜单数据初始化完成！")
    
    # 验证
    menus = await Menu.all()
    for m in menus:
        print(f"  - {m.name}: {m.path}")
    
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(init_menus())
