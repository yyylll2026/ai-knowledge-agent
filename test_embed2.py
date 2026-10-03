from app.services.embedding import embed_query, embed_texts

# 1. 批量
vecs = embed_texts([
    "住宿标准是每晚 500 元",
    "住宿一晚能报销多少钱",
    "今天午饭吃什么",
])

print("数量 =", len(vecs))
print("每个指纹长度 =", len(vecs[0]))

def closeness(a, b):
    return sum(x * y for x, y in zip(a, b))

print()
print("句0 vs 句1（都是住宿）:", round(closeness(vecs[0], vecs[1]), 3))
print("句0 vs 句2（午饭，无关）:", round(closeness(vecs[0], vecs[2]), 3))

# 2. 单条（模拟用户提问）
q = embed_query("出差住宿标准是多少")
print()
print("问题指纹长度 =", len(q))