from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.knowledge import router as knowledge_router
from app.core.config import CORS_ORIGINS
from app.db.base import Base
from app.db.session import engine

# 下面这两行 import 不能删——删了建表时会「忘了」这些表
from app.models.user import User                # noqa: F401
from app.models.document import Document, DocumentChunk  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI Knowledge Agent",
    description="企业级 AI 知识与决策智能体",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：前端在 5173 端口（Vite），后端在 8000，浏览器默认会拦跨域请求。
# 没有这段，前端发出去的请求会在预检（OPTIONS）阶段就被浏览器挡掉。
# 允许的来源在 .env 的 CORS_ORIGINS 里配，默认带上 Vite 常用的几个端口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(knowledge_router)

@app.get("/")
def root():
    return {"message": "AI Knowledge Agent API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}