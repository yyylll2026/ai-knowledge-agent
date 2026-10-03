from app.services.llm import chat
from app.services.search import search_chunks

SYSTEM_PROMPT = """\
你是一个企业知识库问答助手。

规则（必须遵守）：
1. 只能根据【参考资料】回答，不得编造。
2. 资料里没有的答案，直接说「知识库中没有相关资料」。
3. 回答要简短、用中文。
4. 不要在回答里写"资料来源""出处""参考"之类的字样 ——
   系统会自动在回答下方列出引用来源，你写了就重复了。
"""

TEMPLATE = """\
【参考资料】
{context}

【用户问题】
{question}

请按系统规则回答。\
"""

def build_prompt(hits: list[dict], question: str) -> str:
    if not hits:
        # 没搜到东西：给模型一个「空资料」，让它老实说没有
        context = "（没有检索到任何资料）"
    else:
        parts = []
        for i, h in enumerate(hits, start=1):
            # 资料带上来源，方便模型在结尾引用
            source = f"{h['filename']} 第{h['chunk_index']}块"
            parts.append(f"[{i}]（{source}）\n{h['content']}")
        context = "\n\n".join(parts)

    return TEMPLATE.format(context=context, question=question)

def rag_answer(
    db,
    user_id: int,
    question: str,
    top_k: int = 3,
) -> dict:
    """
    完整 RAG 三步：检索 → 拼 Prompt → 让模型回答
    还没挂接口，先在脚本里用
    """
    # 1. 检索
    #    过了 MIN_SCORE 阈值才留得下来；一条都没有 = 返回空列表
    hits = search_chunks(db, question, top_k=top_k, user_id=user_id)

    # 1.5 一条都没够格 —— 直接给固定回复，不调大模型。
    #     两个好处：
    #       a. 省钱省时间（这种问题本来就不该花一次 LLM 调用）
    #       b. 绝对不会编 —— 模型连资料都没机会看到
    #     注意这个判断是必要的：虽然 build_prompt 也能处理空资料，
    #     但"让模型自己说不知道"总不如"根本不让它说话"来得可靠。
    if not hits:
        return {
            "question": question,
            "answer": "知识库中没有相关资料。",
            "sources": [],
        }

    # 2. 拼 Prompt
    user_msg = build_prompt(hits, question)

    # 3. 调大模型
    answer = chat(
        system=SYSTEM_PROMPT,
        user=user_msg,
        temperature=0.2,   # 低一点：更老实照资料答
    )

    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "filename": h["filename"],
                "chunk_index": h["chunk_index"],
                "score": round(h["score"], 3),
                # 把原文也带上：前端要展示"这段到底说了什么"，
                # 只给文件名的话用户还得自己去翻文档。
                # 注意这里是命中的那几段（top_k 通常 3~8），量很小。
                "content": h["content"],
            }
            for h in hits
        ],
    }