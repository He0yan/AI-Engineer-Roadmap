# main.py
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from tool_definitions import TOOLS
from dispatcher import dispatch_tool_call

load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://puhui.space/v1"
)

MAX_TOOL_ROUNDS = 5  # 防止无限循环


def run(user_input: str) -> str:
    # 1. 初始消息
    input_messages = [
        {"role": "user", "content": user_input}
    ]

    for round_idx in range(MAX_TOOL_ROUNDS):
        # 2. 调用模型
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL"),
            input=input_messages,
            tools=TOOLS,
        )

        # 3. 检查是否有工具调用
        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            # 没有工具调用，直接返回最终回答
            return response.output_text

        # 4. 把模型这一轮的输出加入消息历史
        input_messages += response.output

        # 5. 逐个执行工具并回传结果
        for call in tool_calls:
            print(f"[工具调用] name={call.name} args={call.arguments} call_id={call.call_id}")

            result_str = dispatch_tool_call(call.name, call.arguments)

            print(f"[工具结果] {result_str}")

            input_messages.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result_str,
            })

        # 6. 进入下一轮，把工具结果交给模型

    return "已达最大工具调用轮数，已停止。"


if __name__ == "__main__":
    question = "001号设备最近 7 天出了哪些故障？哪种故障出现得最多？"
    answer = run(question)
    print("\n最终回答：")
    print(answer)