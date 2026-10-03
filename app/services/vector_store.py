"""
向量库（sqlite-vec）封装层
=================================

为什么要有这个文件？
以前的检索是：MySQL 里存 JSON 向量 → 全捞进 Python → 循环算余弦。
问题不在"算得慢"，而在"搬得多"：每个 1024 维向量存成 JSON 要 4KB+ 文本，
10 万块就是 4GB 数据要从 MySQL 过网络进内存。

现在改成：
  MySQL  继续管用户 / 文档 / 文本（业务数据）
  SQLite 只存向量（用 sqlite-vec 扩展）

两者靠 chunk_id 关联 —— 向量库里每一行的 rowid，就是 MySQL 里
document_chunks.id。这条"暗线"是整个设计的关键。

为什么用 SQLite 而不是 MySQL 存向量？
MySQL 9.0 社区版没有 VECTOR 类型（只有甲骨文云托管的 HeatWave 有），
硬塞进 JSON 列还是得全表扫描，等于没改。

⚠️ 一个必须知道的真相：
sqlite-vec 目前【没有 ANN 索引】（HNSW/IVF 都还没实现，见
https://github.com/asg017/sqlite-vec/issues/25 ），它是 C + SIMD 的暴力扫描。
所以它提速靠的是"省掉网络传输 + 省掉 Python 循环"，不是算法复杂度变低。
几万~十几万 chunk 完全够用；上千万条才需要 Milvus/Qdrant 这类带索引的服务。
"""

import sqlite3
import threading
from pathlib import Path

import sqlite_vec

from app.core.config import VECTOR_DB_PATH, VECTOR_ENABLED

# sqlite3 的连接默认不能跨线程共享（uvicorn 是多线程的），
# 所以这里给每个线程单独发一个连接。
_local = threading.local()

# 建表用的 SQL。float[1024] 里的 1024 必须和 embedding 模型的维度一致，
# 否则写入时会直接报错（这其实是好事：能早点发现模型换了）。
_SCHEMA = """
create virtual table if not exists vec_chunks using vec0(
  user_id integer partition key,   -- 按用户分片：搜的时候只扫自己的那片
  embedding float[{dim}],          -- 向量本体
  +content text                    -- 辅助列：原文也存一份，省掉一次 JOIN
);
"""


def _dim() -> int:
    """向量维度。从配置读，改模型时只改 .env。"""
    from app.core.config import EMBEDDING_DIM

    return EMBEDDING_DIM


def get_conn() -> sqlite3.Connection:
    """
    拿到当前线程的 SQLite 连接（没有就建一个）。

    这里做了三件事，缺一不可：
    1. enable_load_extension + sqlite_vec.load —— 把向量扩展挂上去
    2. 建表（if not exists，重复调用无副作用）
    3. 加载完立刻关掉 load_extension —— 安全考虑，防止后面被注入加载恶意扩展
    """
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn

    path = Path(VECTOR_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)   # 加载完就关，别一直开着

    conn.execute(_SCHEMA.format(dim=_dim()))
    conn.commit()

    _local.conn = conn
    return conn


def close_conn() -> None:
    """关掉当前线程的连接（测试或退出时用）。"""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def available() -> bool:
    """
    向量库能不能用。
    search.py 靠这个决定"走向量检索"还是"退回老的余弦检索"。
    """
    if not VECTOR_ENABLED:
        return False
    try:
        get_conn()
        return True
    except Exception:
        # 扩展没装、文件没权限、维度不对……统统算"不可用"，
        # 让调用方优雅降级，而不是把整个搜索接口搞崩
        return False


# ---------------------------------------------------------------
# 写入
# ---------------------------------------------------------------
def upsert_chunks(
    user_id: int,
    items: list[tuple[int, str, list[float]]],
) -> int:
    """
    把若干块向量写进向量库。

    items: [(chunk_id, content, embedding), ...]
        chunk_id 会当作 rowid 用 —— 它就是 MySQL 里 document_chunks.id

    返回真正写入的条数。

    为什么先 delete 再 insert？
    vec0 虚拟表不支持 ON CONFLICT DO UPDATE，所以"覆盖写"只能
    先删同 rowid 的旧行、再插新行。重复上传同一个文件时会走到这里。
    """
    if not items:
        return 0

    conn = get_conn()
    with conn:   # with 块 = 自动 commit / 出错自动 rollback
        for chunk_id, content, vec in items:
            conn.execute("delete from vec_chunks where rowid = ?", (chunk_id,))
            conn.execute(
                """
                insert into vec_chunks(rowid, user_id, embedding, content)
                values (?, ?, ?, ?)
                """,
                (chunk_id, user_id, sqlite_vec.serialize_float32(vec), content),
            )
    return len(items)


def delete_by_document(document_id: int, chunk_ids: list[int]) -> int:
    """
    删掉一篇文档对应的所有向量。

    注意：vec0 表里没有 document_id 列（我们只存了 user_id 分区键），
    所以要靠调用方把 chunk_ids 传进来 —— 它们从 MySQL 查得到。
    """
    if not chunk_ids:
        return 0
    conn = get_conn()
    with conn:
        for cid in chunk_ids:
            conn.execute("delete from vec_chunks where rowid = ?", (cid,))
    return len(chunk_ids)


def reset() -> None:
    """清空整个向量库（重建脚本用）。"""
    conn = get_conn()
    with conn:
        conn.execute("delete from vec_chunks")


# ---------------------------------------------------------------
# 检索
# ---------------------------------------------------------------
def knn_search(
    query_vec: list[float],
    user_id: int,
    top_k: int = 5,
) -> list[dict]:
    """
    向量检索：找出和 query_vec 最像的 top_k 块。

    两个 sqlite-vec 的硬性语法要求（踩过坑，记住）：
      1. `k = ?` 必须和 `match` 写在【同一个 WHERE 子句】里。
         不能包一层子查询再在外层 limit —— 会报
         "A LIMIT or 'k = ?' constraint is required on vec0 knn queries"
      2. `user_id = ?` 是 partition key 约束，sqlite-vec 会识别它并
         只在对应分片里搜，不会全表扫

    distance 是 L2 距离（越小越像），不是余弦相似度。
    为了让老接口的语义不变，这里换算成"相似度分数"返回给上层。
    """
    conn = get_conn()
    rows = conn.execute(
        """
        select rowid, distance, content
        from vec_chunks
        where embedding match ?
          and k = ?
          and user_id = ?
        """,
        (sqlite_vec.serialize_float32(query_vec), top_k, user_id),
    ).fetchall()

    return [
        {
            "chunk_id": rowid,
            "content": content,
            # 距离换成"余弦相似度"，和降级检索的分数口径对齐。
            #
            # 为什么能这么换？因为 bge 系列输出的向量是【单位向量】
            # （实测模长 = 1.000000）。对单位向量有恒等式：
            #     d² = |a-b|² = 2 - 2cosθ
            # 所以 cosθ = 1 - d²/2。实测误差 0.000000。
            #
            # 这一步不是为了好看 —— 是因为 1/(1+d) 那种压缩会把
            # 所有分数挤在 0.5 附近（好问题 0.496~0.522，
            # 坏问题 0.439~0.495，几乎分不开），根本没法拿来定阈值。
            "score": 1.0 - (dist * dist) / 2.0,
            "distance": dist,
        }
        for rowid, dist, content in rows
    ]
