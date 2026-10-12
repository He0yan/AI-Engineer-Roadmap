import os
import time
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")

if not api_key or not model:
    raise RuntimeError("请在 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL")

client = OpenAI(
    api_key=api_key,
    base_url="https://puhui.space/v1"
)

# 统一输入
case = {
    "device_type": "离心泵",
    "symptoms": "近期振动和轴承温度均出现上升趋势，流量略有下降。",
    "measurements": (
        "轴承温度从65°C升至78°C；"
        "振动速度RMS从4.5升至7.2 mm/s；"
        "流量从100降至92 m³/h；"
        "出口压力从0.80降至0.76 MPa。"
    ),
    "background": "连续运行约3个月，最近更换过联轴器。",
}

INSTRUCTIONS = (
    "你是一名工业设备故障解释助手。"
    "仅根据已有信息分析，不得把推测描述为已确认的故障事实。"
    "证据不足时，必须明确列出需要补充的信息。"
    "涉及停机、复位或维修操作时，必须提醒由专业人员按现场安全规程判断。"
)

INPUT_TEXT = (
    f"设备：{case['device_type']}\n"
    f"现象：{case['symptoms']}\n"
    f"监测数据：{case['measurements']}\n"
    f"背景：{case['background']}\n\n"
    "请给出：可能原因、建议核查项、仍缺少的信息。"
)

def stream_call() -> dict:
    """流式调用：逐段接收模型输出。"""
    print("=" * 80)
    print("流式调用")
    print("=" * 80)

    start = time.time()
    first_token_time = None
    chunks = []
    final_response = None

    try:
        with client.responses.stream(
            model=model,
            instructions=INSTRUCTIONS,
            input=INPUT_TEXT,
            temperature=0.2
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    if first_token_time is None:
                        first_token_time = time.time() - start
                    chunks.append(event.delta)
                    print(event.delta, end="", flush=True)

                elif event.type == "response.failed":
                    print("\n流式响应失败。")
                    break

                elif event.type == "error":
                    print(f"\n流式错误：{event.error}")
                    break

            final_response = stream.get_final_response()

        elapsed = time.time() - start
        content = "".join(chunks)
        usage = final_response.usage if final_response else None

        print()
        print()
        print(f"首字延迟：{first_token_time:.2f} 秒" if first_token_time else "未收到文本增量")
        print(f"总耗时：{elapsed:.2f} 秒")
        if usage:
            print(
                f"Token：输入 {usage.input_tokens} / "
                f"输出 {usage.output_tokens} / "
                f"总计 {usage.total_tokens}"
            )

        return {
            "mode": "stream",
            "elapsed": elapsed,
            "first_token": first_token_time,
            "content": content,
            "usage": usage,
            "error": None,
        }

    except KeyboardInterrupt:
        elapsed = time.time() - start
        print("\n用户中断了流式输出。")
        return {
            "mode": "stream",
            "elapsed": elapsed,
            "first_token": first_token_time,
            "content": "".join(chunks),
            "usage": None,
            "error": "KeyboardInterrupt",
        }

    except Exception as exc:
        elapsed = time.time() - start
        print(f"\n流式调用失败：{type(exc).__name__}: {exc}")
        return {
            "mode": "stream",
            "elapsed": elapsed,
            "first_token": first_token_time,
            "content": "".join(chunks),
            "usage": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():
    stream_call()


if __name__ == "__main__":
    main()