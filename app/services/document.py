from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services import vector_store
from app.services.chunking import split_text
from app.services.embedding import embed_texts

def ingest_text(
    db: Session,
    user: User,
    filename: str,
    text: str,
    file_type: str = "txt",
) -> Document:
    """
    把一篇纯文字存进知识库

    参数：
        db        数据库会话
        user      谁存的
        filename  文件叫什么名（比如「差旅制度.txt」）
        text      全文
        file_type 文件类型 txt / md

    返回：
        存好的 Document（里面有 id）
    """

    # ---- 1. 先把「整篇文档」存进 documents 表 ----
    doc = Document(
        user_id=user.id,
        filename=filename,
        file_type=file_type,
        content=text,                # 全文先存着
        meta={},
    )
    db.add(doc)
    db.flush()   # 先拿到 doc.id，但还不提交事务

    # ---- 2. 用剪刀切块 ----
    pieces = split_text(text)
    if not pieces:
        raise ValueError("文本为空，切不出任何块")

    # ---- 3. 一次把所有块发去算指纹 ----
    vectors = embed_texts(pieces)

    # ---- 4. 每一块连同指纹，存进 document_chunks 表 ----
    #        顺手记下 id，等会儿要拿它们去写向量库
    chunk_rows: list[DocumentChunk] = []
    for i, (piece, vec) in enumerate(zip(pieces, vectors)):
        row = DocumentChunk(
            document_id=doc.id,   # 挂到这篇文档下
            chunk_index=i,        # 第几块，从 0 数
            content=piece,        # 这块的文字
            embedding=vec,        # 这块的指纹（留着，降级检索要用）
        )
        db.add(row)
        chunk_rows.append(row)

    # ---- 5. 补个元信息，方便以后看 ----
    doc.meta = {
        "char_count": len(text),     # 全文多少字
        "chunk_count": len(pieces),  # 切了几块
    }

    # ---- 6. 真正写入 MySQL（上面都是暂存）----
    #        必须先 commit 拿到自增 id，向量库的 rowid 要用它
    db.commit()
    db.refresh(doc)

    # ---- 7. 同步写进向量库 ----
    #        注意这里的顺序：MySQL 是"正本"，向量库是"索引副本"。
    #        先落正本再建索引，万一中间挂了，最多是索引缺数据
    #        ——可以跑 rebuild_vectors.py 重建，不会丢正本。
    _sync_to_vector_store(user_id=user.id, chunks=chunk_rows)

    return doc


def _sync_to_vector_store(user_id: int, chunks: list[DocumentChunk]) -> None:
    """
    把块写进向量库。

    这一步【故意】不抛异常：向量库是可选的加速层，
    它挂了不该让"上传文档"整个失败 —— 文本已经安全存进 MySQL 了，
    后面重建索引就能补上。所以失败只提示，不影响上传结果。
    """
    if not vector_store.available():
        print("[vector_store] 不可用，跳过向量写入（检索会走余弦降级）")
        return
    try:
        vector_store.upsert_chunks(
            user_id=user_id,
            items=[
                (c.id, c.content, c.embedding)
                for c in chunks
                if c.embedding
            ],
        )
    except Exception as e:
        print(f"[vector_store] 写入失败，检索将走余弦降级：{e}")