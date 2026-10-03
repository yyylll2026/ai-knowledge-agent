# AI Knowledge Agent

企业级知识库问答系统。上传文档 → 切块 → 向量化 → 检索 → 大模型据此作答。

- **后端**：FastAPI + MySQL + sqlite-vec（向量库）
- **前端**：React 19 + Vite
- **模型**：硅基流动（`bge-large-zh-v1.5` 做向量化，`Qwen2.5-7B-Instruct` 做问答）

---

## 快速开始

需要 Python 3.10+、Node.js 18+、MySQL 8。

### 1. 后端

```bash
# 装依赖
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 配好 .env（数据库、密钥、API Key）
# 建库（如果还没有）
mysql -uroot -p -e "create database ai_agent"

# 首次启用向量库：把已有文档灌进向量库
.venv\Scripts\python.exe rebuild_vectors.py

# 起服务
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

接口文档：http://127.0.0.1:8000/docs

### 2. 前端

```bash
cd frontend
pnpm install
pnpm dev
```

打开 http://127.0.0.1:5173

### 3. 环境变量

`.env` 里这些是必须的：

```bash
DATABASE_URL=mysql+pymysql://root:密码@localhost:3306/ai_agent
SECRET_KEY=换成一串足够长的随机字符串
EMBEDDING_API_KEY=sk-xxxxx        # 硅基流动的 Key

# 可选
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_DIM=1024                 # 必须和模型输出维度一致！
CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
MIN_SCORE=0.46                     # 检索相似度阈值
VECTOR_ENABLED=true                # 设 false 则退回余弦检索
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 架构

```
┌─────────────┐   /api    ┌──────────────┐
│  React 前端  │ ────────► │   FastAPI    │
│  (5173)     │  代理转发  │   (8000)     │
└─────────────┘           └──────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌───────────────┐        ┌─────────────────┐
            │     MySQL     │        │  SQLite         │
            │  业务数据正本   │        │  (sqlite-vec)   │
            │  用户/文档/文本 │        │  只存向量        │
            └───────────────┘        └─────────────────┘
                    │                         ▲
                    └────── rowid = chunk.id ─┘
```

**关键设计：MySQL 是正本，向量库是索引副本。**

- 先写 MySQL 再写向量库，中间挂了最多索引缺数据，可重建，不会丢正本
- 向量库挂了不影响上传文档，检索自动降级为余弦全表扫描
- 删文档时先删向量再删正本（索引先没比正本先没更安全）

---

## 目录结构

```
app/
├── main.py                  应用入口，含 CORS 配置
├── api/
│   ├── auth.py              注册 / 登录 / 当前用户
│   ├── knowledge.py         上传 / 列表 / 删除 / 检索 / 问答
│   └── deps.py              依赖注入：数据库会话、当前用户
├── core/
│   ├── config.py            所有配置（含 MIN_SCORE 的实测推导）
│   └── security.py          bcrypt 哈希 + JWT
├── models/                  SQLAlchemy 模型
├── services/
│   ├── vector_store.py      ★ sqlite-vec 封装（向量库）
│   ├── search.py            ★ 双路径检索：向量库优先，余弦降级
│   ├── rag.py               检索 → 拼 Prompt → 调模型
│   ├── chunking.py          文本切块（500 字 / 50 字重叠）
│   ├── embedding.py         调硅基流动算向量
│   ├── llm.py               调硅基流动做对话
│   └── document.py          文档入库（含同步写向量库）
└── schemas/                 Pydantic 请求/响应模型

frontend/src/
├── api/client.js            API 封装（token、错误处理、401 自动登出）
├── context/AuthContext.jsx  登录态管理
├── components/
│   ├── Layout.jsx           侧边栏骨架
│   ├── ScoreBar.jsx         相似度可视化 + 空结果解释
│   └── Toast.jsx            轻量提示
├── pages/
│   ├── Login.jsx            登录 / 注册
│   ├── Chat.jsx             ★ RAG 对话（带引用来源卡片）
│   ├── Search.jsx           ★ 向量检索（相似度可视化）
│   └── Documents.jsx        上传 / 列表 / 删除
└── styles/
    ├── theme.css            设计令牌（颜色/间距/圆角/动效）
    └── app.css              组件样式

rebuild_vectors.py           从 MySQL 重建向量库
sample.txt                   测试语料
```

---

## 设计要点

### 检索阈值（MIN_SCORE）

低于阈值的检索结果会被**丢弃**，不喂给大模型。这样问知识库里没有的问题时，
系统会明确回答「知识库中没有相关资料」，而不是拿无关内容硬编。

阈值不是拍脑袋定的，是实测扫出来的。**但要知道它的局限**：

- 向量检索对**措辞非常敏感**。「住宿标准」0.5181，「住宿标准是多少钱？」掉到 0.4137
- 「该命中」和「不该命中」的分数区间是**交叠**的，单一阈值必然有误伤
- 换语料或换模型后必须重新标定

想根本解决需要上 **cross-encoder 重排序**（粗召回 20 条 → 小模型精排）。

### 为什么用 sqlite-vec 而不是 MySQL

MySQL 9.0 社区版**没有** `VECTOR` 类型（只有甲骨文云托管的 HeatWave 支持），
硬塞回 JSON 列仍然要全表扫描。

sqlite-vec 目前**没有 ANN 索引**，是 C + SIMD 的暴力扫描。它提速来自
"省掉网络传输 + 省掉 Python 循环"，不是算法复杂度变低。实测：

| 块数 | 余弦全表 | 向量库 | 提速 |
|---:|---:|---:|---:|
| 500 | 144ms | 3.4ms | 42x |
| 5000 | 1494ms | 15.6ms | 96x |

几万~十几万块够用；上千万条需要 Milvus / Qdrant 这类带索引的服务。

---

## 自动化验证

前端带一个真实浏览器的端到端测试（需要后端和前端都已启动）：

```bash
cd frontend
node verify.mjs
```

它会走完：登录 → RAG 问答 → 拒答 → 检索 → 空状态 → 文档列表 → 上传 → 删除 → 窄屏，
逐步截图到 `shots/`，并报告浏览器控制台错误。

---

## 已知限制

- 上传只支持 `.txt` / `.md`
- 检索是**全量**语义检索，没有关键词过滤 / 分类 / 权限粒度
- 对话不支持流式输出（等模型完整生成后一次性返回）
- 没有分页（文档列表一次性返回全部）
