#!/usr/bin/env python3
"""
补偿脚本: 回填 one_liner + 8 关联表数据 (for existing topics)
用法: docker exec topicsystem-app python3 /app/scripts/backfill_relations.py
"""
import asyncio, json, sys, os, time
sys.path.insert(0, "/app")

from src.config.database import db_lifespan

CHECKPOINT = "/app/scripts/.backfill_checkpoint.json"
BATCH = 200
CONCURRENT = 8

_RELATION_MODELS = [
    ("src.models.topic_prerequisite", "TopicPrerequisite", "prerequisites",
     {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_core_concept", "TopicCoreConcept", "core_concepts",
     {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_derivative", "TopicDerivative", "derivatives",
     {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_extension", "TopicExtension", "extensions",
     {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_evaluation_anchor", "TopicEvaluationAnchor", "evaluation_anchors",
     {"content": "content", "sort_order": "sort_order"}),
    ("src.models.topic_similar_question", "TopicSimilarQuestion", "similar_questions",
     {"question": "question", "answer_hint": "answer_hint", "sort_order": "sort_order"}),
    ("src.models.topic_advanced_question", "TopicAdvancedQuestion", "advanced_questions",
     {"question": "question", "answer_hint": "answer_hint", "sort_order": "sort_order"}),
    ("src.models.topic_reference", "TopicReference", "references",
     {"title": "title", "url": "url", "description": "description", "sort_order": "sort_order"}),
]


def load_checkpoint():
    if not os.path.exists(CHECKPOINT):
        return set()
    with open(CHECKPOINT) as f:
        return set(json.load(f))


def save_checkpoint(s):
    with open(CHECKPOINT, "w") as f:
        json.dump(list(s), f)


async def main():
    async with db_lifespan():
        from src.agentv3.capabilities.register import register_all
    register_all()
    from src.agentv3.capabilities.generate import generate_topic
    from src.models.topic import Topic

    all_topics = await Topic.all()
    existing_ids = load_checkpoint()

    # Filter: topics missing one_liner or relations
    todo = []
    for t in all_topics:
        tid = str(t.id)
        if tid in existing_ids:
            continue
        # Check if one_liner is missing (use this as the signal)
        if not t.one_liner:
            todo.append((tid, t.topic, t.domain))
        else:
            existing_ids.add(tid)

    if not todo:
        print(f"All {len(all_topics)} topics complete")
        return

    print(f"Backfill: {len(todo)} topics missing data (total: {len(all_topics)})")
    sem = asyncio.Semaphore(CONCURRENT)
    stats = {"ok": 0, "fail": 0}
    start = time.time()

    async def process(tid, name, domain):
        async with sem:
            try:
                data = await generate_topic(name, domain, [])
                t = await Topic.filter(id=tid).first()
                if t:
                    t.one_liner = data.get("topic", {}).get("one_liner", "")
                    await t.save()

                # Write 8 relation tables
                for mod_path, model_name, json_key, field_map in _RELATION_MODELS:
                    items = data.get(json_key, [])
                    if not items:
                        continue
                    try:
                        import importlib
                        mod = importlib.import_module(mod_path)
                        model_cls = getattr(mod, model_name)
                        # Check if already exists
                        existing_count = await model_cls.filter(topic_id=tid).count()
                        if existing_count > 0:
                            continue
                        import uuid as _uuid
                        records = []
                        for idx, item in enumerate(items):
                            rec = {"id": str(_uuid.uuid4()), "topic_id": tid}
                            for db_col, json_col in field_map.items():
                                rec[db_col] = item.get(json_col)
                            rec.setdefault("sort_order", idx)
                            records.append(rec)
                        await model_cls.bulk_create([model_cls(**r) for r in records])
                    except Exception:
                        pass

                stats["ok"] += 1
                existing_ids.add(tid)
                save_checkpoint(existing_ids)
                elapsed = time.time() - start
                rate = stats["ok"] / (elapsed / 60) if elapsed > 0 else 0
                print(f"  [{stats['ok']}/{len(todo)}] {rate:.0f}/min: {name[:40]}")
            except Exception as e:
                stats["fail"] += 1
                print(f"  FAIL: {name[:40]} - {str(e)[:80]}")

    tasks = [process(tid, name, domain) for tid, name, domain in todo]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"\nDone in {(time.time()-start)/60:.1f}min: {stats['ok']} ok, {stats['fail']} fail")


if __name__ == "__main__":
    asyncio.run(main())
