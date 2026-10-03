import math

from sqlalchemy.orm import Session

from app.core.config import MIN_SCORE
from app.models.document import Document, DocumentChunk
from app.services.embedding import embed_query
from app.services import vector_store

def cosine(a: list[float], b: list[float]) -> float:
    """
    算两串指纹有多像
    返回 1.0 = 一模一样，0 = 完全无关，负数 = 反着来
    """
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)

def _search_by_cosine(
    db: Session,
    q_vec: list[float],
    top_k: int,
    user_id: int | None,
) -> list[dict]:
    """
    老办法：把候选块全捞进内存，一条条算余弦。

    现在它有两个身份：
      1. 降级方案 —— 向量库没装 / 坏了的时候自动顶上
      2. 对照组   —— 你可以拿它和向量检索比速度和效果

    缺点就一句话：数据量越大越慢，而且是"搬数据"的慢，不是"算"的慢。
    """
    # 从库里把卡片都捞出来（要带上是哪篇文档、叫什么名）
    stmt = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
    )
    if user_id is not None:
        stmt = stmt.filter(Document.user_id == user_id)

    rows = stmt.all()

    scored = []
    for chunk, doc in rows:
        score = cosine(q_vec, chunk.embedding or [])
        scored.append({
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "filename": doc.filename,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": score,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

def _search_by_vector(
    db: Session,
    q_vec: list[float],
    top_k: int,
    user_id: int,
) -> list[dict]:
    """
    新办法：向量库只返回最像的 top_k 个 chunk_id，
    我们再回 MySQL 补上"文件名 / 第几块"这些业务字段。

    这就是"向量库 + 关系库"的标准配合姿势：
      向量库负责"找得准、找得快"，不负责存业务数据。
    代价是一次按 id 的批量查询 —— 只有 top_k 条（通常 3~20），
    相比以前捞全表，这点开销可以忽略。
    """
    hits = vector_store.knn_search(q_vec, user_id=user_id, top_k=top_k)
    if not hits:
        return []

    ids = [h["chunk_id"] for h in hits]

    # 一次查完，别在循环里逐条查库（N+1 问题）
    rows = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(DocumentChunk.id.in_(ids))
        .all()
    )
    meta = {
        chunk.id: {
            "document_id": doc.id,
            "filename": doc.filename,
            "chunk_index": chunk.chunk_index,
            # 原文以 MySQL 为准。向量库辅助列里也存了一份，
            # 但那只是为了省 JOIN，不作为真相来源。
            "content": chunk.content,
        }
        for chunk, doc in rows
    }

    result = []
    for h in hits:
        info = meta.get(h["chunk_id"])
        if info is None:
            # 向量库里有、MySQL 里没有 → 数据不同步（比如删文档时漏删向量）。
            # 跳过而不是报错，保证搜索仍然能用。
            continue
        result.append({
            "chunk_id": h["chunk_id"],
            "document_id": info["document_id"],
            "filename": info["filename"],
            "chunk_index": info["chunk_index"],
            "content": info["content"],
            "score": h["score"],
        })
    return result

def _above_threshold(hits: list[dict]) -> list[dict]:
    """
    把分数太低的块滤掉。

    注意顺序：一定是在【取出 top_k 之后】才过滤，不是过滤完再取 top_k。
    如果反过来，"库里前 5 条都不及格"会导致明明有第 6 条及格的也返回空 ——
    我们要的是"最好的几条里哪些够格"，不是"够格的里面最好的几条"。

    两条检索路径的 score 现在口径统一（都是余弦），所以能共用一个阈值。
    """
    return [h for h in hits if h["score"] >= MIN_SCORE]

def search_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    user_id: int | None = None,
) -> list[dict]:
    """
    在知识库里找和问题最相关的几块

    query    用户的问题
    top_k    返回几条（默认 5）
    user_id  只搜这个人的文档（数据隔离）

    返回的可能是【空列表】——那不是出错，是"知识库里确实没有相关内容"。
    rag.py 会据此让模型老实说"没有相关资料"，而不是硬编。

    优先级：向量库 > 余弦降级。
    向量库出任何问题都不会让接口挂掉 —— 这是故意的，搜索引擎
    不该因为一个可选组件挂掉就彻底不可用。
    """

    # 1. 先把问题算成指纹（这一步两种方案都要做）
    q_vec = embed_query(query)

    # 2. 优先走向量库。
    #    注意 user_id 为 None 时不能走向量库：分区键必须给出具体值，
    #    否则没法限定分片（这时候退回余弦全表才有意义）
    if user_id is not None and vector_store.available():
        try:
            hits = _search_by_vector(db, q_vec, top_k, user_id)
            filtered = _above_threshold(hits)
            if filtered:
                return filtered
            # 三种情况会走到这里：
            #   a. 向量库是空的（历史数据还没 rebuild）
            #   b. 有结果但全部低于阈值
            # 分不清是哪种，所以让余弦再算一次 —— 如果余弦也判"不够格"，
            # 说明确实是 (b)，返回空是对的；如果是 (a)，余弦能救回来。
        except Exception:
            pass   # 向量库抽风 → 静默降级，别把 500 抛给用户

    # 3. 降级：老的余弦检索
    return _above_threshold(_search_by_cosine(db, q_vec, top_k, user_id))
