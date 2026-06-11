from tortoise import fields
from tortoise.models import Model


class Menu(Model):
    """菜单模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="菜单名称")
    path = fields.CharField(max_length=255, description="路由路径")
    icon = fields.CharField(max_length=100, null=True, description="图标")
    parent_id = fields.IntField(null=True, description="父级菜单ID")
    sort_order = fields.IntField(default=0, description="排序")
    is_visible = fields.BooleanField(default=True, description="是否显示")
    component = fields.CharField(max_length=255, null=True, description="组件路径")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "menu"
