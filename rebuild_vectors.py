"""
把 MySQL 里已有的向量，重建进 sqlite-vec 向量库
================================================

什么时候要跑这个？
  1. 第一次启用向量库 —— 之前上传的文档只存在 MySQL 里，向量库是空的
  2. 向量库文件被删了 / 损坏了
  3. 换了 embedding 模型或维度，需要全部重算

它做的事很简单：把 MySQL 里所有 chunk 的 id / user_id / 向量 / 原文
读出来，灌进 SQLite。因为 MySQL 一直存着 embedding 字段（那是给降级
检索用的），所以这里【不用重新调 API 算向量】，纯本地搬运，很快。

用法：
    .venv\\Scripts\\python.exe rebuild_vectors.py
"""

from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk
from app.services import vector_store


def main() -> None:
    print("=" * 56)
    print("重建向量库")
    print("=" * 56)

    if not vector_store.available():
        print("[错误] 向量库不可用。检查：")
        print("   1. pip install sqlite-vec 装了吗")
        print("   2. .env 里 VECTOR_ENABLED 是不是 false")
        print("   3. EMBEDDING_DIM 和实际向量维度对得上吗")
        raise SystemExit(1)

    db = SessionLocal()
    try:
        # 一次查完：块的向量 + 它属于哪个用户
        # user_id 在 documents 表上，所以要 JOIN 一下
        rows = (
            db.query(DocumentChunk, Document.user_id)
            .join(Document, DocumentChunk.document_id == Document.id)
            .all()
        )

        total = len(rows)
        print(f"MySQL 里共 {total} 块")

        if total == 0:
            print("没有数据，不用重建。先上传一篇文档吧。")
            return

        # 维度自检：这是最容易踩的坑，提前拦住比事后报错友好得多
        dims = {len(c.embedding) for c, _ in rows if c.embedding}
        print(f"向量维度：{dims}")
        from app.core.config import EMBEDDING_DIM

        if dims and EMBEDDING_DIM not in dims:
            print(f"[错误] 维度不一致！配置里是 {EMBEDDING_DIM}，数据里是 {dims}")
            print("   请把 .env 的 EMBEDDING_DIM 改成正确值，再重新跑。")
            raise SystemExit(1)

        # 清空重来，避免残留脏数据
        print("清空旧向量……")
        vector_store.reset()

        # 按用户分组。向量表按 user_id 分区，同一次写入必须属于同一个用户。
        groups: dict[int, list] = {}
        for chunk, uid in rows:
            if chunk.embedding:
                groups.setdefault(uid, []).append(
                    (chunk.id, chunk.content, chunk.embedding)
                )

        written = 0
        for uid, items in groups.items():
            written += vector_store.upsert_chunks(user_id=uid, items=items)
            print(f"  用户 {uid}：写入 {len(items)} 块（累计 {written}/{total}）")

        print(f"[OK] 重建完成，共 {written} 块向量")

        # 做个抽样自检：向量库里的条数对不对
        conn = vector_store.get_conn()
        count = conn.execute("select count(*) from vec_chunks").fetchone()[0]
        print(f"   向量库里现在有 {count} 行")
        if count != written:
            print("[警告] 行数和写入数不一致，可能有问题，检查一下")

    finally:
        db.close()


if __name__ == "__main__":
    main()
