"""
模型生成器
根据表名自动生成 Tortoise ORM 模型文件

用法:
    python scripts/model_generator.py user_level
    python scripts/model_generator.py user_level --module user
"""

import os
import re
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from jinja2 import Environment, FileSystemLoader


# PostgreSQL 类型映射到 Tortoise 字段类型
TYPE_MAPPING = {
    "uuid": "UUIDField",
    "character varying": "CharField",
    "varchar": "CharField",
    "text": "TextField",
    "integer": "IntField",
    "bigint": "IntField",
    "smallint": "IntField",
    "boolean": "BooleanField",
    "timestamp without time zone": "DatetimeField",
    "timestamp with time zone": "DatetimeField",
    "date": "DateField",
    "time": "TimeField",
    "numeric": "FloatField",
    "double precision": "FloatField",
    "real": "FloatField",
    "json": "JSONField",
    "jsonb": "JSONField",
    "bytea": "BinaryField",
}


def snake_to_camel(name: str) -> str:
    """snake_case 转 CamelCase"""
    components = name.split("_")
    return "".join(x.title() for x in components)


def snake_to_snake(name: str) -> str:
    """保持 snake_case"""
    return name.lower()


async def get_table_columns(
    conn: asyncpg.Connection,
    schema: str,
    table_name: str
) -> list[dict]:
    """获取表的所有列信息"""
    query = """
        SELECT
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END as is_primary_key,
            CASE WHEN fk.column_name IS NOT NULL THEN TRUE ELSE FALSE END as is_foreign_key,
            fk.foreign_table_name,
            fk.foreign_column_name,
            fk.foreign_table_schema
        FROM information_schema.columns c
        LEFT JOIN (
            SELECT ku.table_name, ku.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage ku
                ON tc.constraint_name = ku.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = $1
        ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
        LEFT JOIN (
            SELECT
                kcu.column_name,
                kcu.table_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                ccu.table_schema AS foreign_table_schema
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = $1
        ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
        WHERE c.table_schema = $1 AND c.table_name = $2
        ORDER BY c.ordinal_position
    """
    rows = await conn.fetch(query, schema, table_name)
    return [dict(row) for row in rows]


def get_reverse_relations(
    conn: asyncpg.Connection,
    schema: str,
    table_name: str,
    module_name: str
) -> list[dict]:
    """获取一对多反向关系"""
    query = """
        SELECT
            tc.table_name AS child_table,
            kcu.column_name AS foreign_column,
            ccu.table_name AS parent_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = $1
            AND ccu.table_name = $2
    """
    rows = asyncio.run(conn.fetch(query, schema, table_name))
    relations = []
    for row in rows:
        relations.append({
            "name": snake_to_snake(row["child_table"].replace(f"{module_name}_", "")),
            "target": snake_to_camel(row["child_table"])
        })
    return relations


def map_field_type(pg_type: str, nullable: bool, default: str, is_pk: bool, is_fk: bool, max_length: Optional[int] = None) -> tuple[str, str]:
    """映射字段类型和参数"""
    field_type = TYPE_MAPPING.get(pg_type, "TextField")
    params = []

    if is_pk and pg_type == "uuid":
        return "UUIDField", "pk=True"

    if is_fk:
        return "ForeignKeyField", f'"models.{{ target_class }}", related_name="{{ related_name }}"'

    if pg_type in ("character varying", "varchar") and max_length:
        params.append(f"max_length={max_length}")

    if nullable:
        params.append("null=True")

    # 处理默认值
    if default:
        if "gen_random_uuid" in default:
            params.append("default=fields.UUIDField.default")
        elif "current_timestamp" in default.lower():
            if "auto_now_add" not in params:
                params.append("auto_now_add=True")
        elif "now()" in default.lower():
            if "auto_now" not in params:
                params.append("auto_now=True")
        elif "true" in default.lower():
            params.append("default=True")
        elif "false" in default.lower():
            params.append("default=False")

    return field_type, ", ".join(params) if params else ""


def generate_model(
    schema: str,
    table_name: str,
    columns: list[dict],
    reverse_relations: list[dict],
    module_name: str
) -> dict:
    """生成模型数据"""
    class_name = snake_to_camel(table_name)

    fields = []
    fk_map = {}  # 存储外键信息用于后续渲染

    for col in columns:
        pg_type = col["data_type"]
        field_type, params = map_field_type(
            pg_type,
            col["is_nullable"] == "YES",
            col["column_default"] or "",
            col["is_primary_key"],
            col["is_foreign_key"],
            col.get("character_maximum_length")
        )

        if col["is_foreign_key"]:
            fk_target = snake_to_camel(col["foreign_table_name"])
            fk_map[col["column_name"]] = {
                "target_class": fk_target,
                "related_name": f"{snake_to_snake(table_name)}_{col['column_name'].replace('_id', '')}s"
            }

        field_entry = {
            "name": col["column_name"],
            "type": field_type,
            "params": params
        }
        fields.append(field_entry)

    # 替换外键字段的实际参数
    for field in fields:
        if field["name"] in fk_map:
            fk_info = fk_map[field["name"]]
            field["params"] = f'"{module_name}.models.{fk_info["target_class"]}", related_name="{fk_info["related_name"]}"'

    return {
        "class_name": class_name,
        "table_name": table_name,
        "schema": schema,
        "fields": fields,
        "reverse_relations": reverse_relations
    }


async def generate_model_file(
    db_url: str,
    schema: str,
    table_name: str,
    module_name: str,
    output_dir: Path
):
    """生成单个模型文件"""
    # 连接数据库
    conn = await asyncpg.connect(db_url)

    try:
        # 获取表结构
        columns = await get_table_columns(conn, schema, table_name)
        if not columns:
            print(f"❌ 表 '{schema}.{table_name}' 不存在")
            return

        # 获取反向关系
        reverse_relations = await conn.fetch("""
            SELECT
                tc.table_name AS child_table,
                kcu.column_name AS foreign_column,
                ccu.table_name AS parent_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = $1
                AND ccu.table_name = $2
        """, schema, table_name)

        reverse_relations = [
            {
                "name": snake_to_snake(row["child_table"].replace(f"{module_name}_", "")),
                "target": snake_to_camel(row["child_table"])
            }
            for row in reverse_relations
        ]

        # 生成模型数据
        model_data = generate_model(schema, table_name, columns, reverse_relations, module_name)

        # 渲染模板
        template_dir = project_root / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("model.py.j2")
        content = template.render(**model_data)

        # 写入文件
        output_path = output_dir / "models" / f"{table_name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        print(f"✅ 已生成: {output_path}")

        # 更新 models/__init__.py（手动模式，跳过自动更新）
        # 用户需要在 src/models/__init__.py 中手动添加导入
        if init_file.exists():
            existing = init_file.read_text()
            if f"# {module_name} 模块模型" not in existing:
                init_content = existing + init_content

        # 收集所有模型文件
        model_files = []
        for f in sorted(output_path.parent.glob("*.py")):
            if f.name != "__init__.py":
                model_files.append(f.stem)

        # 生成导入语句
        imports = [f"from .{f.lower()} import {snake_to_camel(f)}" for f in model_files]
        if imports:
            init_content = "from . import *\n# noqa\n"

        init_file.write_text(init_content)
        print(f"📝 已更新: {init_file}")

    finally:
        await conn.close()


async def generate_from_table_list(
    db_url: str,
    schema: str,
    tables: list[str],
    module_name: str,
    output_dir: Path
):
    """从表名列表批量生成"""
    for table_name in tables:
        await generate_model_file(db_url, schema, table_name, module_name, output_dir)


def main():
    parser = argparse.ArgumentParser(description="根据表名生成 Tortoise ORM 模型")
    parser.add_argument("tables", nargs="+", help="表名列表")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"), help="数据库连接 URL")
    parser.add_argument("--schema", default="topic", help="数据库 schema")
    parser.add_argument("--module", default="topic", help="模块名（如 topic, user）")
    parser.add_argument("--output", default="src", help="输出目录")
    args = parser.parse_args()

    if not args.db_url:
        print("❌ 请提供 --db-url 或设置 DATABASE_URL 环境变量")
        return

    output_dir = project_root / args.output
    asyncio.run(generate_from_table_list(
        args.db_url,
        args.schema,
        args.tables,
        args.module,
        output_dir
    ))


if __name__ == "__main__":
    main()
