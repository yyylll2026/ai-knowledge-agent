from datetime import datetime

from sqlalchemy import(
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id:Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False,  # txt / md
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,  # 提取出来的纯全文
    )
    meta: Mapped[dict] = mapped_column(
        JSON, default=dict,  # 乱七八糟的附加信息，先放这儿
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
    )

    # 语法糖：文档. 能直接拿到它下面所有块
    # delete-orphan = 删文档时，块跟着一起删
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True,
    )
    # 这块属于哪篇文档 → 指向 documents.id
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False,   # 第几块，0 开始
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,      # 这一块的原文
    )
    # 先占个位！今天不填内容，后面「向量化」那步才用
    embedding: Mapped[list] = mapped_column(
        JSON, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
    )

    # 反过来：块.document 能找到它属于哪篇
    document: Mapped["Document"] = relationship(
        back_populates="chunks",
    )