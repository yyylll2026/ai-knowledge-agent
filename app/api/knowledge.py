from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.models.user import User
from app.services import vector_store
from app.services.document import ingest_text
from pydantic import BaseModel, Field
from app.services.search import search_chunks
from app.services.rag import rag_answer

class SearchIn(BaseModel):
    """检索接口收的 JSON"""
    query: str = Field(..., min_length=1, max_length=200, description="用户的问题")
    top_k: int = Field(5, ge=1, le=20, description="返回几条")

class ChatIn(BaseModel):
    """问答接口收的 JSON"""
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="用户的问题",
    )
    top_k: int = Field(3, ge=1, le=10, description="参考几段原文")

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["知识库"],
)

@router.post(
    "/documents",
    status_code=status.HTTP_201_CREATED,
    summary="上传一篇文档",
)
async def upload_document(
    file: UploadFile = File(...,description="txt 或 md 文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or "untitled.txt"
    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件需要有扩展名，例如 note.txt",
        )
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("txt", "md", "markdown"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目前只支持 .txt 或 .md 文件",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件是空的",
        )
    text = None
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="读不出文字，请另存为 UTF-8 编码",
        )
    try:
        doc = ingest_text(
            db=db,
            user=current_user,
            filename=filename,
            text=text,
            file_type=ext,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

        # ---- 4. 回话给前端 ----
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "meta": doc.meta,
        "created_at": doc.created_at.isoformat(),
    }

@router.get("/documents", summary="列出当前用户的文档")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    列出自己的文档（不含全文，只给元信息 —— 全文可能很大，
    前端列表页不需要）。
    """
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "total": len(docs),
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "meta": d.meta or {},
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    }

@router.delete(
    "/documents/{document_id}",
    summary="删除一篇文档（连带它的块和向量）",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删文档要动三个地方，顺序很重要：
      1. 先收集 MySQL 里的 chunk_id（删完就查不到了）
      2. 删向量库
      3. 删 MySQL（cascade 会自动带走 chunks）

    先删向量再删正本：万一中间挂了，是"索引先没了、正本还在"，
    重新跑 rebuild_vectors.py 就能补回来，不会出现"正本没了、
    向量还留着"这种无法恢复的脏数据。
    """
    doc = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,   # 只能删自己的
        )
        .first()
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在，或不属于你",
        )

    # 1. 趁数据还在，先记下 chunk_id
    chunk_ids = [c.id for c in doc.chunks]

    # 2. 删向量（失败不影响删除流程，可以事后重建）
    try:
        if vector_store.available():
            vector_store.delete_by_document(document_id, chunk_ids)
    except Exception as e:
        print(f"[vector_store] 删除向量失败（可跑 rebuild_vectors.py 修正）：{e}")

    # 3. 删正本。relationship 上配了 cascade="all, delete-orphan"，
    #    所以 chunks 会跟着一起删
    db.delete(doc)
    db.commit()

    return {"deleted": True, "id": document_id, "chunks_removed": len(chunk_ids)}

@router.post("/search", summary="在知识库里找相关内容")
def search(
    payload: SearchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hits = search_chunks(
        db,
        query=payload.query,
        top_k=payload.top_k,
        user_id=current_user.id,   # 只搜自己的文档
    )
    return {"query": payload.query, "hits": hits}

@router.post("/chat", summary="知识库问答（RAG）")
def chat_with_kb(
    payload: ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    三步：搜资料 → 拼 Prompt → 大模型按资料回答
    """
    result = rag_answer(
        db=db,
        user_id=current_user.id,
        question=payload.question,
        top_k=payload.top_k,
    )
    return result