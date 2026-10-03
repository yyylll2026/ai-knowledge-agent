import json
import urllib.request

from app.core.config import (
    CHAT_API_BASE,
    CHAT_API_KEY,
    CHAT_MODEL,
)

def chat(
    system: str,
    user: str,
    temperature: float = 0.3,
) -> str:
    """
    跟大模型说一句话，拿回它的回答

    system  系统指令：先告诉模型「你是谁、守什么规矩」
    user    用户真正的问题
    temperature  0=老老实实照资料答，1=更发散（回答知识库问题用 0.3 就好）
    """

    if not CHAT_API_KEY:
        raise RuntimeError("请在 .env 里配置 EMBEDDING_API_KEY")

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }

    req = urllib.request.Request(
        f"{CHAT_API_BASE}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {CHAT_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # 返回里我们只要这一句
    return data["choices"][0]["message"]["content"]