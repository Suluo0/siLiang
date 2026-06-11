"""
提示词模板表
存储可复用的提示词模板配置
"""
from tortoise import fields
from tortoise.models import Model


class PromptTemplate(Model):
    """提示词模板"""
    
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True, description="模板名称")
    description = fields.TextField(null=True, description="模板描述")
    system_prompt = fields.TextField(null=True, description="系统提示词")
    user_prompt_template = fields.TextField(description="用户提示词模板，支持 {param} 占位符")
    version = fields.IntField(default=1, description="版本号")
    is_active = fields.BooleanField(default=True, description="是否启用")
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    class Meta:
        table = "prompt_template"
        table_description = "提示词模板配置表"
