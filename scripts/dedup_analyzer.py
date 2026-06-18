#!/usr/bin/env python3
"""
线上数据去重分析工具
L1: SQL 精确匹配（同 topic 名 / 近似名） 
L2: Milvus 语义聚类（余弦 ≥0.70 视为高度相似）
L3: 内容级对比（one_liner 或 detailed_explanation 相似度）
输出：JSON 去重报告 + 待清理 topic_id 列表
"""
import sys, json, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.database import init_db, close_db
from src.models import Topic
from collections import defaultdict


async def l1_sql_duplicates():
    """L1: SQL 层查重 — 同名前缀 / 短名包含关系"""
    print("\n=== L1: SQL 近似匹配 ===")
    all_topics = await Topic.all()
    names = [(t.id, t.topic) for t in all_topics]
    
    # 按名称排序找出高度相似的
    sorted_names = sorted(names, key=lambda x: x[1])
    dup_groups = []
    for i in range(len(sorted_names) - 1):
        a_id, a_name = sorted_names[i]
        b_id, b_name = sorted_names[i + 1]
        
        # 规则1: 一个名完全包含另一个（子串关系）
        if (a_name in b_name or b_name in a_name) and len(a_name) / len(b_name) > 0.5:
            dup_groups.append({
                "type": "substring",
                "pair": [{"id": str(a_id), "name": a_name}, {"id": str(b_id), "name": b_name}],
            })
            continue
        
        # 规则2: 前N字相同且后部分仅差后缀词（——源码、——最佳实践等）
        min_len = min(len(a_name), len(b_name))
        common = 0
        for j in range(min_len):
            if a_name[j] == b_name[j]:
                common += 1
            else:
                break
        if common >= max(6, min_len * 0.6):
            dup_groups.append({
                "type": "prefix",
                "pair": [{"id": str(a_id), "name": a_name}, {"id": str(b_id), "name": b_name}],
            })
    
    print(f"  Found {len(dup_groups)} L1 duplicate groups")
    for g in dup_groups[:10]:
        print(f"  [{g['type']}] {g['pair'][0]['name'][:40]} ↔ {g['pair'][1]['name'][:40]}")
    if len(dup_groups) > 10:
        print(f"  ... and {len(dup_groups) - 10} more")
    
    return dup_groups


async def l2_milvus_similarity():
    """L2: Milvus 语义聚类 — 对每条题目做 cosine 检索，收集 ≥0.70 的配对"""
    print("\n=== L2: Milvus 语义聚类 ===")
    
    try:
        from src.tools.embedding import EmbeddingEncoder
        from src.tools.milvus_client import MilvusClient
        encoder = EmbeddingEncoder.get_instance()
        milvus = MilvusClient.get_instance()
    except Exception as e:
        print(f"  Milvus 不可用: {e}")
        return []
    
    all_topics = await Topic.all()
    print(f"  Total topics: {len(all_topics)}")
    
    dup_pairs = []
    seen_pairs = set()
    
    for t in all_topics:
        try:
            vec = encoder.encode(t.topic)
            hits = milvus.search_dense(vec.tolist(), top_k=3)
        except Exception:
            continue
        
        for hit in hits:
            score = hit.get("score", 0)
            other_id = hit.get("topic_id", "")
            if score >= 0.70 and str(t.id) != str(other_id):
                pair_key = tuple(sorted([str(t.id), str(other_id)]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    dup_pairs.append({
                        "cosine": round(score, 4),
                        "pair": [
                            {"id": str(t.id), "name": t.topic},
                            {"id": str(other_id), "name": hit.get("core_concept", "?")},
                        ],
                    })
    
    dup_pairs.sort(key=lambda x: -x["cosine"])
    print(f"  Found {len(dup_pairs)} L2 similar pairs (cosine ≥0.70)")
    for p in dup_pairs[:15]:
        print(f"  [{p['cosine']:.3f}] {p['pair'][0]['name'][:35]} ↔ {p['pair'][1]['name'][:35]}")
    if len(dup_pairs) > 15:
        print(f"  ... and {len(dup_pairs) - 15} more")
    
    return dup_pairs


async def l3_content_similarity():
    """L3: 内容级对比 — one_liner 或 detailed_explanation 前100字余弦"""
    print("\n=== L3: 内容级相似 ===")
    
    try:
        from src.tools.embedding import EmbeddingEncoder
        encoder = EmbeddingEncoder.get_instance()
    except Exception as e:
        print(f"  Encoder 不可用: {e}")
        return []
    
    all_topics = await Topic.filter(one_liner__not_isnull=True).all()
    if len(all_topics) < 2:
        print(f"  Only {len(all_topics)} topics with content, skip")
        return []
    
    print(f"  Topics with content: {len(all_topics)}")
    dup_pairs = []
    seen_pairs = set()
    
    for i, t1 in enumerate(all_topics):
        text1 = (t1.one_liner or "")[:100]
        if not text1.strip():
            continue
        v1 = encoder.encode(text1)
        
        for j, t2 in enumerate(all_topics):
            if j <= i:
                continue
            text2 = (t2.one_liner or "")[:100]
            if not text2.strip():
                continue
            
            # 快速 name 相似度预筛
            words1 = set(t1.topic.replace("与", " ").replace("——", " ").split())
            words2 = set(t2.topic.replace("与", " ").replace("——", " ").split())
            common_words = words1 & words2
            if not common_words:
                continue
            
            v2 = encoder.encode(text2)
            from src.utils import cosine
            sim = cosine(v1, v2)
            
            if sim >= 0.75:
                pair_key = tuple(sorted([str(t1.id), str(t2.id)]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    dup_pairs.append({
                        "cosine": round(float(sim), 4),
                        "pair": [
                            {"id": str(t1.id), "name": t1.topic},
                            {"id": str(t2.id), "name": t2.topic},
                        ],
                    })
    
    dup_pairs.sort(key=lambda x: -x["cosine"])
    print(f"  Found {len(dup_pairs)} L3 content-similar pairs (cosine ≥0.75)")
    for p in dup_pairs[:10]:
        print(f"  [{p['cosine']:.3f}] {p['pair'][0]['name'][:35]} ↔ {p['pair'][1]['name'][:35]}")
    
    return dup_pairs


async def generate_report(l1, l2, l3, output_path: str):
    """汇总分析报告"""
    # 标记所有涉重 ID
    dup_ids = set()
    for g in l1:
        for p in g["pair"]:
            dup_ids.add(p["id"])
    for p in l2:
        for pair in p["pair"]:
            dup_ids.add(pair["id"])
    for p in l3:
        for pair in p["pair"]:
            dup_ids.add(pair["id"])
    
    # 按涉重次数排序
    dup_count = defaultdict(int)
    for id_ in dup_ids:
        dup_count[id_] = 0
    for g in l1:
        for p in g["pair"]:
            dup_count[p["id"]] += 1
    for p in l2:
        for pair in p["pair"]:
            dup_count[pair["id"]] += 1
    
    # 建议删除的 ID（每个 L2 组只保留最高分的一个）
    to_remove = []
    processed = set()
    for p in l2:
        pair_ids = [pair["id"] for pair in p["pair"]]
        if set(pair_ids) & processed:
            continue
        # 保留第一个（或名字较长的），删除其余
        names = [(pid, dup_count[pid]) for pid in pair_ids]
        names.sort(key=lambda x: -x[1])  # 含重复多的优先删
        keep = pair_ids[0]  # 保留一个
        for pid in pair_ids[1:]:
            if pid not in processed:
                to_remove.append(pid)
        processed.update(pair_ids)
    
    report = {
        "total_topics": len(await Topic.all()),
        "l1_groups": len(l1),
        "l2_pairs": len(l2),
        "l3_pairs": len(l3),
        "unique_dup_ids": len(dup_ids),
        "duplicate_rate": f"{len(dup_ids) / max(len(await Topic.all()), 1) * 100:.1f}%",
        "suggested_remove_ids": to_remove[:50],  # 第一批最多50个
        "l1_sample": l1[:5],
        "l2_sample": l2[:5],
        "l3_sample": l3[:3],
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📊 去重分析报告")
    print(f"{'='*60}")
    print(f"  总题目数: {report['total_topics']}")
    print(f"  L1 近似名: {report['l1_groups']} 组")
    print(f"  L2 语义相似: {report['l2_pairs']} 对")
    print(f"  L3 内容相似: {report['l3_pairs']} 对")
    print(f"  涉重题目数: {report['unique_dup_ids']} ({report['duplicate_rate']})")
    print(f"  建议删除: {len(to_remove)} 个")
    print(f"  报告已写入: {output_path}")


async def main():
    await init_db()
    l1 = await l1_sql_duplicates()
    l2 = await l2_milvus_similarity()
    l3 = await l3_content_similarity()
    output = str(Path(__file__).resolve().parent / "dedup_report.json")
    await generate_report(l1, l2, l3, output)
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
