# 手动 benchmark / 全链路脚本

这些是**手动执行**的性能分析与端到端验证脚本,不参与 pytest 自动收集。

## 运行方式
```bash
# 需要本地起 PG + Milvus 服务
source .venv/bin/activate
python scripts/manual_tests/full_pipeline_test.py
python scripts/manual_tests/single_topic_test.py
python scripts/manual_tests/profile_upsert.py
python scripts/manual_tests/profile_upsert2.py

# api_test.py 需要先起 uvicorn:
# uvicorn src.main:app --reload &
python scripts/manual_tests/api_test.py
```

## 文件说明
- `full_pipeline_test.py` — 10 道题全链路(PG + Milvus)
- `single_topic_test.py`  — 单题全链路 + 时间日志
- `profile_upsert.py`     — 逐知识点 upsert 耗时分析
- `profile_upsert2.py`    — upsert 三层拆解 profile
- `api_test.py`           — POST /api/topic/generate 黑盒
