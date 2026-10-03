from app.db.session import SessionLocal
from app.models.user import User
from app.services.rag import rag_answer

db = SessionLocal()
try:
    # 换成你自己的用户名
    user = db.query(User).filter(User.username == "lisi").first()
    if user is None:
        print("找不到 bob，改成你的用户名")
        raise SystemExit

    # 问题 1：知识库里应该有答案
    q1 = "出差住宿标准是多少钱？"
    print("Q:", q1)
    r1 = rag_answer(db, user_id=user.id, question=q1)
    print("A:", r1["answer"])
    print("sources:", r1["sources"])
    print()

    # 问题 2：知识库里没有 → 应该老实说没有
    q2 = "公司今年营业额是多少？"
    print("Q:", q2)
    r2 = rag_answer(db, user_id=user.id, question=q2)
    print("A:", r2["answer"])

finally:
    db.close()