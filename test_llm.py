from app.services.llm import chat

reply = chat(
    system="你是一个简洁的助手，只用一句话回答。",
    user="用一句话介绍你自己。",
)

print("模型说：", reply)