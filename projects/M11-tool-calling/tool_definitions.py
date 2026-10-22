# tool_definitions.py

TOOLS = [
    {
        "type": "function",
        "name": "get_device_status",
        "description": (
            "查询指定设备当前的实时状态，包括运行状态、当前温度。"
            "当用户询问某台设备现在、当前、此刻是否运行、当前状态、实时温度时调用。"
            "device_id 是设备编号，例如 '001'。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "设备编号，例如 '001'。必须是字符串。"
                }
            },
            "required": ["device_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "get_device_history",
        "description": (
            "查询指定设备最近一段时间的历史运行数据，返回温度、振动等时间序列。"
            "当用户询问某台设备最近 N 小时的变化、趋势、历史数据时调用。"
            "不要用于查询当前实时状态。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "设备编号，例如 '001'。必须是字符串。"
                },
                "hours": {
                    "type": "integer",
                    "description": "回溯小时数，1 到 168 之间。例如 24 表示最近 24 小时。",
                    "minimum": 1,
                    "maximum": 168
                }
            },
            "required": ["device_id", "hours"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "count_faults",
        "description": (
            "统计指定日期范围内发生的故障总次数。"
            "记录故障设备的id及故障类型。"
            "当用户询问设备故障相关问题时可以调用。"
            "start_date 和 end_date 均为日期，格式 YYYY-MM-DD，包含起止日期。"
            "不要用于查询单台设备的实时状态或历史数据。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD，例如 '2026-10-07'。包含当天。"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD，例如 '2026-10-13'。包含当天。"
                }
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False
        },
        "strict": True
    }
]

