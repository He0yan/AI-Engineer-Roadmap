# schemas.py
from typing import Literal
from pydantic import BaseModel, Field


class FaultReport(BaseModel):
    """设备故障分析的结构化报告。"""

    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="故障严重程度。low=轻微，medium=中等，high=高，critical=紧急。"
    )
    summary: str = Field(
        description="故障摘要，一句话概括当前状态。"
    )
    possible_causes: list[str] = Field(
        description="可能原因列表，按可能性从高到低排列。"
    )
    recommended_checks: list[str] = Field(
        description="建议核查项列表，每项应具体可操作。"
    )
    missing_information: list[str] = Field(
        description="仍缺少的信息列表，用于补充判断。"
    )
    requires_human_review: bool = Field(
        description="是否需要人工复核。涉及安全风险时必须为 true。"
    )