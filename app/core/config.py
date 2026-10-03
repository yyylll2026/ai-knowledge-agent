import os

from dotenv import load_dotenv

load_dotenv()

# =========================
# 数据库
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# JWT / 安全
# =========================
# 从 .env 读取；没配置就退回开发用默认值
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

# =========================
# 应用
# =========================
APP_NAME = os.getenv("APP_NAME", "AI Knowledge Agent")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# 一张卡片最多 500 字
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))

# 相邻卡片重叠 50 字
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# =========================
# 向量化（Embedding）
# =========================
# 硅基流动的接口地址
EMBEDDING_API_BASE = os.getenv(
    "EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1"
)

# 你的 API Key（在 .env 里配）
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")

# 用哪个模型算指纹
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"
)

# 向量维度。必须和上面 EMBEDDING_MODEL 的输出维度一致！
# bge-large-zh-v1.5 = 1024；换成别的模型记得改这里，
# 否则写入向量库时会报维度不匹配。
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

# =========================
# 向量库（sqlite-vec）
# =========================
# 向量单独存一个 SQLite 文件，和 MySQL 分开：
# MySQL 管业务数据（用户/文档/文本），SQLite 管向量。
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vectors.db")

# 总开关。设成 false 就完全退回老的余弦检索（方便对比 / 排障）
VECTOR_ENABLED = os.getenv("VECTOR_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)

# =========================
# 检索质量
# =========================
# 相似度低于这个分数的块，直接丢掉，不喂给大模型。
#
# 为什么需要它？没有阈值时，问"公司今年营业额是多少"这种知识库里
# 根本没有的问题，照样会硬塞几段无关资料给模型。虽然 system prompt
# 说了"资料里没有就说没有"，但给了无关资料，模型更容易顺着编。
#
# 这个数怎么来的：拿真实用户问法在 sample.txt 上实测。
#
# 第一轮（用自造的、措辞贴近文档的问题）扫出 0.48，看着很完美：
#     0.48 → 命中 8/8，误放 0/8
# 但换成真实口语化问法后，0.48 明显偏高，会误伤正常问题：
#     住宿费上限是多少？      0.4215  被砍
#     年假可以休几天？        0.4662  被砍
#     加班有加班费吗？        0.4681  被砍
# 第二轮（真实问法）重扫：
#     0.40 → 命中 6/6，误放 1/4
#     0.44 → 命中 5/6，误放 1/4
#     0.46 → 命中 5/6，误放 0/4   ← 拐点：再多命中一个，且安全侧不退化
#     0.48 → 命中 3/6，误放 0/4
#
# ⚠️ 必须知道的两件事：
#   1. 两个区间是【交叠】的 —— 「年假可以休几天」(该命中) 0.4662
#      竟然低于「公司今年营业额」(不该命中) 0.4477 的近邻。
#      这说明单一全局阈值【必然】会误伤，调参只能取舍，无法根治。
#   2. 长疑问句会稀释相似度：「住宿标准是多少钱？」0.4137，
#      加了「出差」变 0.4898，砍成「住宿标准」反而 0.5181。
#      同一个意思，措辞一变分数差 0.1 —— 阈值卡在中间就是灾难。
#
# 真正稳的做法是 cross-encoder 重排序（粗召回 20 条 → 小模型精排），
# 它直接对(问题,文档)成对打分，不受这种"措辞稀释"影响。
# 这里的阈值是"低成本挡掉大部分噪声"，不是完美方案。
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.46"))

# =========================
# 前端跨域（CORS）
# =========================
# 前端跑在 Vite（默认 5173），后端跑在 8000，属于不同源。
# 浏览器会先发 OPTIONS 预检请求，后端不回 CORS 头就直接拦掉。
# 多个来源用英文逗号分隔。
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if o.strip()
]

# =========================
# 大模型（对话）
# =========================
CHAT_API_BASE = os.getenv(
    "CHAT_API_BASE", "https://api.siliconflow.cn/v1"
)
CHAT_MODEL = os.getenv(
    "CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct"
)
# Key 和 embedding 用同一个
CHAT_API_KEY = EMBEDDING_API_KEY