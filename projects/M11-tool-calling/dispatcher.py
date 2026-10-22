# dispatcher.py

import json
from pydantic import ValidationError
from tools import (
    DeviceStatusArgs,
    DeviceHistoryArgs,
    CountFaultsArgs,
    get_device_status,
    get_device_history,
    count_faults,
)

TOOL_REGISTRY = {
    "get_device_status": (DeviceStatusArgs, get_device_status),
    "get_device_history": (DeviceHistoryArgs, get_device_history),
    "count_faults": (CountFaultsArgs, count_faults),
}


def dispatch_tool_call(name: str, arguments_json: str) -> str:
    """
    统一分发工具调用。
    返回字符串形式的结果，用于回传模型。
    """
    # 1. 检查工具是否注册
    if name not in TOOL_REGISTRY:
        return json.dumps(
            {"error": f"未知工具：{name}"},
            ensure_ascii=False
        )

    model_cls, func = TOOL_REGISTRY[name]

    # 2. 解析 JSON
    try:
        raw = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return json.dumps(
            {"error": f"参数不是合法 JSON：{e}"},
            ensure_ascii=False
        )

    # 3. Pydantic 校验
    try:
        args = model_cls.model_validate(raw)
    except ValidationError as e:
        return json.dumps(
            {"error": "参数校验失败", "details": e.errors()},
            ensure_ascii=False,
            default=str
        )

    # 4. 执行函数
    try:
        result = func(**args.model_dump())
    except Exception as e:
        return json.dumps(
            {"error": f"工具执行失败：{e}"},
            ensure_ascii=False
        )

    # 5. 序列化结果
    return json.dumps(result, ensure_ascii=False, default=str)