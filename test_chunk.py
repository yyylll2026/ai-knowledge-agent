import os
import json
import urllib.request

# Set EMBEDDING_API_KEY in the environment before running this test.
API_KEY = os.getenv("EMBEDDING_API_KEY")
if not API_KEY:
    raise SystemExit("请先设置环境变量 EMBEDDING_API_KEY，再运行此测试")

# 硅基流动的接口
url = "https://api.siliconflow.cn/v1/embeddings"

# 试用免费的中文 embedding 模型（先试这个）
payload = {
    "model": "BAAI/bge-large-zh-v1.5",
    "input": [
        "住宿标准是每晚500元",
        "住宿一晚能报销多少钱",
        "今天午饭吃什么",
    ],
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    vecs = [item["embedding"] for item in data["data"]]
    print("✅ 成功！模型：", payload["model"])
    print("指纹长度 =", len(vecs[0]))
    print("一共算了", len(vecs), "个指纹")

    def closeness(a, b):
        return sum(x * y for x, y in zip(a, b))

    print()
    print("句0 vs 句1（都是住宿）:", round(closeness(vecs[0], vecs[1]), 3))
    print("句0 vs 句2（午饭，无关）:", round(closeness(vecs[0], vecs[2]), 3))

except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print("❌ 服务返回错误，状态码:", e.code)
    print("原文:", body)
    print()
    print("→ 把上面「原文」两行发我，我判断是没余额还是模型名不对")

except Exception as e:
    print("❌ 网络或其他问题:", e)
