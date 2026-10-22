# rag.py
import os
from retriever import retrieve
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://puhui.space/v1"
)


DEFAULT_TOP_K = 5
# 余弦距离，越小越相似；先设 0.5 做粗筛，D6 测试后再调
DISTANCE_THRESHOLD = 0.5

SYSTEM_PROMPT = """你是一个企业劳动用工合规问答助手。你的任务是根据提供的法规条文回答用户问题。

必须遵守以下规则：
1. 只能依据【检索到的法规条文】回答，不得使用你已有的知识补充任何法律内容。
2. 每个结论都必须标注来源：法律名称 + 条款编号。
3. 原文摘录必须与检索结果中的条文逐字一致，不得改写、缩写或补全。
4. 如果检索结果不足以回答问题，必须明确回答“当前知识库无法支持该结论”，并说明缺少哪方面的法规依据。
5. 不得编造法律名称、条款编号、原文内容或官方来源。
6. 如果检索结果包含多条相关条文，请分别引用，不要合并成一条。
7. 不要给出法律意见、个案判断或操作建议，只做法规条文层面的说明。

请严格按以下格式回答。如果材料不足以回答问题，只在“回答”中写“当前知识库无法支持该结论”，并说明缺少什么，其余字段留空或写“无”。

回答：
依据的法规：
具体条款：
原文摘录：
适用范围与限制：
"""
def format_hits(hits: list) -> str:
    """把检索结果格式化成 Prompt 里的材料区。"""
    blocks = []
    for h in hits:
        blocks.append(
            f"[{h['rank']}] {h['document_title']} {h['article_number']}\n"
            f"原文：{h['text']}\n"
            f"来源：{h.get('source_url') or '（来源待核验）'}"
        )
    return "\n\n".join(blocks)

def build_user_prompt(question: str, hits: list) -> str:
    materials = format_hits(hits)
    return f"""用户问题：
{question}

检索到的法规条文：
{materials}
"""

def answer(question: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """端到端 RAG：检索 → 证据判断 → 生成。"""
    if not question or not question.strip():
        return {
            "question": question,
            "status": "invalid_question",
            "answer": "问题为空。",
            "hits": [],
        }

    hits = retrieve(question, top_k=top_k)

    # 第一道证据闸门：检索结果为空，或全部距离过远
    if not hits or all(h["distance"] > DISTANCE_THRESHOLD for h in hits):
        return {
            "question": question,
            "status": "insufficient_evidence",
            "answer": "当前知识库无法支持该结论。检索到的条文与问题相关性不足。",
            "hits": hits,
        }

    user_prompt = build_user_prompt(question, hits)

    response=client.responses.create(
        model=os.getenv("OPENAI_MODEL"),
        instructions=SYSTEM_PROMPT,
        input=user_prompt
    )

    return {
        "question": question,
        "status": "ok",
        "answer": response.output_text,
        "hits": hits,
    }


if __name__ == "__main__":
    q = "用人单位与劳动者订立劳动合同，应该遵循哪些原则？"
    result = answer(q)
    print(f"状态: {result['status']}")
    print(result["answer"])
    print("\n--- 检索到的条文 ---")
    for h in result["hits"]:
        print(f"[{h['rank']}] {h['document_title']} {h['article_number']} "
              f"(distance={h['distance']:.4f})")