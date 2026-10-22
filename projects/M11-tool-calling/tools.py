# tools.py

from datetime import date
from pydantic import BaseModel, Field, ConfigDict, StrictStr, model_validator


# ---------- Pydantic 参数模型 ----------

class DeviceStatusArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: StrictStr = Field(min_length=1)


class DeviceHistoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: StrictStr = Field(min_length=1)
    hours: int = Field(ge=1, le=168)


class CountFaultsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_date_order(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date 不能早于 start_date")
        return self


# ---------- 模拟数据库 ----------

_DEVICE_DB = {
    "001": {"device_id": "001", "status": "running", "temperature": 72.3},
    "002": {"device_id": "002", "status": "stopped", "temperature": 25.1},
    "003": {"device_id": "003", "status": "maintenance", "temperature": 30.0},
    "004": {"device_id": "004", "status": "running", "temperature": 68.5},
    "005": {"device_id": "005", "status": "stopped", "temperature": 24.0},
}

_HISTORY_DB = {
    "001": [
        {"timestamp": "2026-10-13T10:00", "temperature": 70.1, "vibration": 1.2},
        {"timestamp": "2026-10-13T11:00", "temperature": 71.5, "vibration": 1.3},
        {"timestamp": "2026-10-13T12:00", "temperature": 72.0, "vibration": 1.1},
        {"timestamp": "2026-10-13T13:00", "temperature": 72.3, "vibration": 1.0},
    ],
    "002": [
        {"timestamp": "2026-10-13T10:00", "temperature": 25.0, "vibration": 0.1},
        {"timestamp": "2026-10-13T11:00", "temperature": 25.1, "vibration": 0.1},
    ],
}

_FAULT_DB = [
    {"date": "2026-10-07", "device_id": "001", "fault_type": "overheat"},
    {"date": "2026-10-08", "device_id": "002", "fault_type": "vibration"},
    {"date": "2026-10-09", "device_id": "001", "fault_type": "overheat"},
    {"date": "2026-10-10", "device_id": "003", "fault_type": "communication"},
    {"date": "2026-10-13", "device_id": "001", "fault_type": "overheat"},
]


# ---------- 工具函数 ----------

def get_device_status(device_id: str) -> dict:
    if device_id not in _DEVICE_DB:
        return {"error": f"设备 {device_id} 不存在"}
    return _DEVICE_DB[device_id]


def get_device_history(device_id: str, hours: int) -> dict:
    if device_id not in _HISTORY_DB:
        return {"error": f"设备 {device_id} 没有历史数据"}
    samples = _HISTORY_DB[device_id]
    # 简化：直接返回全部，实际可按 hours 过滤
    return {
        "device_id": device_id,
        "hours": hours,
        "samples": samples[-hours:] if hours < len(samples) else samples,
    }


def count_faults(start_date: date, end_date: date) -> dict:
    count = 0
    for fault in _FAULT_DB:
        fault_date = date.fromisoformat(fault["date"])
        if start_date <= fault_date <= end_date:
            count += 1
    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "count": count,
    }