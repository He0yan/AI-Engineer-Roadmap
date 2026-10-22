import os
import sys
from pyexpat.errors import messages
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://puhui.space/v1"
)

def explain_fault(fault_description: str) -> str:
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL"),
        instructions=(
            "你是一名工业设备故障解释助手。"
            "根据用户提供的设备与故障信息，解释可能原因和检查方向。"
            "不得把推测描述为已确认的故障事实；"
            "证据不足时，明确说明需要补充哪些信息。"
            "涉及停机、复位或维修操作时，必须提醒由专业人员按现场安全规程判断。"
        ),
      
        input=(
            f"故障描述：{fault_description}\n"
            "请给出：可能原因、建议核查项、建议补充的信息。"
        ),
        temperature=0.2
    )
    
    # 1. 遍历 output 数组，查找推理内容
    reasoning_text = ""
    for item in response.output:
        if item.type == "reasoning":
            # 推理内容通常在 summary 字段里
            # 注意：具体字段名可能因模型/平台而异，可能是 item.summary 或 item.text
            # 根据搜索结果，通常是 summary[].text
            if hasattr(item, 'summary') and item.summary:
                reasoning_text = "".join(part.text for part in item.summary if hasattr(part, 'text'))
            elif hasattr(item, 'text'):
                reasoning_text = item.text
            break # 找到第一个推理块就退出

    if reasoning_text:
        print("\n=== 模型思考过程 ===")
        print(reasoning_text)

    if response.usage:
        print("输入 Token：", response.usage.input_tokens)
        print("输出 Token：", response.usage.output_tokens)
        print("总 Token：", response.usage.total_tokens)

    return response.output_text


def main():
    if len(sys.argv) > 1:
        fault_description = " ".join(sys.argv[1:]).strip()
    else:
        fault_description = input("请输入设备故障描述：").strip()

    if not fault_description:
        print("故障描述不能为空。")
        return

    try:
        result = explain_fault(fault_description)
    except Exception as exc:
        print(f"调用失败：{type(exc).__name__}: {exc}")
        return

    print("\n=== 模型回复 ===")
    print(result)


if __name__ == "__main__":
    main()