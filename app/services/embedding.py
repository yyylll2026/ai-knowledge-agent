import json
import urllib.request

from app.core.config import (
    EMBEDDING_API_BASE,
    EMBEDDING_API_KEY,
    EMBEDDING_MODEL,
)

def embed_texts(texts:list[str])->list[list[float]]:
    if not texts:
        return []
    if not EMBEDDING_API_KEY:
        raise RuntimeError(
            "请在 .env 里配置 EMBEDDING_API_KEY"
        )
    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts,  # 一次可以传多句
    }
    req = urllib.request.Request(
        f"{EMBEDDING_API_BASE}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = data["data"]
    items.sort(key=lambda x: x["index"])  # 保证顺序和输入一致
    return [item["embedding"] for item in items]
def embed_query(query: str) -> list[float]:
    """
    给一句话（用户的问题）算指纹
    就是 embed_texts 的单条版
    """
    return embed_texts([query])[0]