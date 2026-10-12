# structured_call.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from schemas import FaultReport

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")

if not api_key or not model:
    raise RuntimeError("请在 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL")

client = OpenAI(
    api_key=api_key,
    base_url="https://puhui.space/v1"
)


def analyze_fault(
    device_type: str,
    symptoms: str,
    measurements: str,
    background: str,
) -> FaultReport:
    """调用模型，返回结构化故障报告。"""

    input_text = (
        f"设备：{device_type}\n"
        f"现象：{symptoms}\n"
        f"监测数据：{measurements}\n"
        f"背景：{background}\n\n"
    )

    response = client.responses.parse(
        model=model,
        instructions=(
            "你是一名工业设备故障解释助手。"
            "仅根据已有信息分析，不得编造不存在的数值或维修记录。"
            "证据不足时，明确列出信息缺口。"
            "涉及停机、复位或维修操作时，必须提醒人工复核。"
        ),
        input=input_text,
        text_format=FaultReport,
    )

    report = response.output_parsed

    if report is None:
        raise RuntimeError(
            "模型未返回可解析的结构化结果。"
            f"可能的拒绝原因：{response.output}"
        )

    return report


def main():
    # 用 pump_001 案例测试
    try:
        report = analyze_fault(
            device_type="离心泵",
            symptoms="近期振动和轴承温度均出现上升趋势，流量略有下降。",
            measurements=(
                "轴承温度从65°C升至78°C；"
                "振动速度RMS从4.5升至7.2 mm/s；"
                "流量从100降至92 m³/h；"
                "出口压力从0.80降至0.76 MPa。"
            ),
            background="连续运行约3个月，最近更换过联轴器。",
        )
    except ValidationError as exc:
        print(f"结构校验失败：{exc}")
        return
    except RuntimeError as exc:
        print(f"解析失败：{exc}")
        return

    print("=== 结构化故障报告 ===")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()