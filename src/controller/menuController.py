from fastapi import APIRouter
from src.models import Menu
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/menu", tags=["菜单"])


class MenuItem(BaseModel):
    id: int
    name: str
    path: str
    icon: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int
    is_visible: bool
    component: Optional[str] = None

    class Config:
        from_attributes = True


class MenuTreeItem(MenuItem):
    children: List["MenuTreeItem"] = []


@router.get("/list", response_model=List[MenuItem])
async def get_menu_list():
    """获取菜单列表"""
    menus = await Menu.filter(is_visible=True).order_by("sort_order")
    return menus


@router.get("/tree", response_model=List[MenuTreeItem])
async def get_menu_tree():
    """获取菜单树"""
    menus = await Menu.filter(is_visible=True).order_by("sort_order")
    
    # 构建树形结构
    menu_dict = {m.id: MenuTreeItem(
        id=m.id,
        name=m.name,
        path=m.path,
        icon=m.icon,
        parent_id=m.parent_id,
        sort_order=m.sort_order,
        is_visible=m.is_visible,
        component=m.component,
        children=[]
    ) for m in menus}
    
    root_menus = []
    for menu in menus:
        menu_item = menu_dict[menu.id]
        if menu.parent_id and menu.parent_id in menu_dict:
            menu_dict[menu.parent_id].children.append(menu_item)
        elif not menu.parent_id:
            root_menus.append(menu_item)
    
    return root_menus
