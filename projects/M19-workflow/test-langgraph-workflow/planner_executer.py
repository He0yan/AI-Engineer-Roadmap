"""
Planner / Executor 完整示例
运行前需要：pip install langgraph langchain-openai pydantic
"""

import operator
from typing import Annotated, Literal, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field


# ============================================================
# 1. 定义 State
# ============================================================

class PlanExecuteState(TypedDict):
    user_query: str

    # Planner 写入
    plan: dict

    # Validator 写入
    plan_errors: list[str]

    # Executor 并行节点写入（每个字段只有一个写者，不需要 Reducer）
    device_status: dict
    sensor_data: dict
    knowledge_results: list

    # 多个并行节点共同追加，必须配 Reducer
    evidence_log: Annotated[list, operator.add]

    # 最终汇总
    diagnosis: str


# ============================================================
# 2. Planner：LLM 结构化输出，生成受约束的计划
# ============================================================

Metric = Literal["vibration", "temperature", "pressure", "current"]


class DiagnosisPlan(BaseModel):
    need_device_status: bool = Field(description="是否需要查询设备当前状态")
    need_sensor_history: bool = Field(description="是否需要查询传感器历史数据")
    need_knowledge_search: bool = Field(description="是否需要检索维修知识")
    metrics: list[Metric] = Field(
        default_factory=list,
        description="需要查询的传感器指标，只允许 vibration/temperature/pressure/current",
    )
    time_range_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="查询历史数据的时间范围，单位小时",
    )


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_planner = llm.with_structured_output(DiagnosisPlan)


def plan_node(state: PlanExecuteState) -> dict:
    """Planner 节点：只负责生成计划，不执行任何查询。"""
    system_prompt = (
        "你是一个工业设备诊断任务规划器。根据用户问题，判断需要哪些证据，"
        "输出结构化的执行计划。只规划，不执行。"
    )
    plan = structured_planner.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_query"]},
    ])
    return {"plan": plan.model_dump()}


# ============================================================
# 3. Validator：纯 Python 校验，Planner 和 Executor 之间的闸门
# ============================================================

ALLOWED_METRICS = {"vibration", "temperature", "pressure", "current"}


def validate_plan(state: PlanExecuteState) -> dict:
    """校验计划的结构完整性和安全边界。不通过时把错误写入 State。"""
    plan = state.get("plan", {})
    errors = []

    if plan.get("need_sensor_history") and not plan.get("metrics"):
        errors.append("需要传感器历史，但 metrics 为空")

    unknown = set(plan.get("metrics", [])) - ALLOWED_METRICS
    if unknown:
        errors.append(f"不支持的指标: {unknown}")

    if plan.get("time_range_hours", 0) <= 0:
        errors.append("time_range_hours 必须大于 0")

    return {"plan_errors": errors}


def route_after_validate(state: PlanExecuteState) -> Literal["execute_fanout", "plan_rejected"]:
    """条件边：校验通过则进入执行，否则进入拒绝分支。"""
    if state.get("plan_errors"):
        return "plan_rejected"
    return "execute_fanout"


def plan_rejected(state: PlanExecuteState) -> dict:
    return {"diagnosis": f"计划未通过校验：{state['plan_errors']}"}


# ============================================================
# 4. Executor 并行 fan-out：用 Send 按计划动态派发任务
# ============================================================

def execute_fanout(state: PlanExecuteState):
    """
    根据 plan 中的布尔标志，生成一组 Send。
    每个 Send 派发一个独立的 worker 实例，LangGraph 并行执行。
    """
    plan = state["plan"]
    sends = []

    if plan.get("need_device_status"):
        sends.append(Send("query_device", {"device_id": state.get("device_id", "D-102")}))

    if plan.get("need_sensor_history"):
        sends.append(Send("query_sensor", {
            "device_id": state.get("device_id", "D-102"),
            "metrics": plan.get("metrics", []),
            "time_range_hours": plan.get("time_range_hours", 24),
        }))

    if plan.get("need_knowledge_search"):
        sends.append(Send("retrieve_knowledge", {
            "device_id": state.get("device_id", "D-102"),
            "metrics": plan.get("metrics", []),
        }))

    return sends


# ============================================================
# 5. 三个并行 Worker：各写各的字段，同时向 evidence_log 追加
# ============================================================

def query_device(payload: dict) -> dict:
    device_id = payload["device_id"]
    # 模拟外部服务调用
    status = {"device_id": device_id, "status": "warning", "temperature": 85}
    return {
        "device_status": status,
        "evidence_log": [f"device: {device_id} 状态查询完成"],
    }


def query_sensor(payload: dict) -> dict:
    device_id = payload["device_id"]
    metrics = payload["metrics"]
    # 模拟外部服务调用
    data = {m: [70 + i for i in range(5)] for m in metrics}
    return {
        "sensor_data": data,
        "evidence_log": [f"sensor: {device_id} {metrics} 历史查询完成"],
    }


def retrieve_knowledge(payload: dict) -> dict:
    device_id = payload["device_id"]
    metrics = payload["metrics"]
    # 模拟 RAG 检索
    results = [f"{device_id} 的 {m} 异常可能原因：轴承磨损" for m in metrics]
    return {
        "knowledge_results": results,
        "evidence_log": [f"knowledge: {device_id} 知识检索完成"],
    }


# ============================================================
# 6. 汇总节点：fan-in，读取所有并行结果
# ============================================================

def diagnose(state: PlanExecuteState) -> dict:
    """
    所有并行分支完成后触发一次。
    这里用简单拼接模拟综合分析；Day 6 会替换为 M18 Agent。
    """
    parts = ["诊断汇总："]
    if state.get("device_status"):
        parts.append(f"设备状态={state['device_status']}")
    if state.get("sensor_data"):
        parts.append(f"传感器数据={state['sensor_data']}")
    if state.get("knowledge_results"):
        parts.append(f"知识检索={state['knowledge_results']}")
    parts.append(f"证据链={state.get('evidence_log', [])}")
    return {"diagnosis": "\n".join(parts)}


# ============================================================
# 7. 构建 Graph
# ============================================================

builder = StateGraph(PlanExecuteState)

builder.add_node("plan", plan_node)
builder.add_node("validate", validate_plan)
builder.add_node("plan_rejected", plan_rejected)
builder.add_node("execute_fanout", execute_fanout)
builder.add_node("query_device", query_device)
builder.add_node("query_sensor", query_sensor)
builder.add_node("retrieve_knowledge", retrieve_knowledge)
builder.add_node("diagnose", diagnose)

builder.add_edge(START, "plan")
builder.add_edge("plan", "validate")

builder.add_conditional_edges(
    "validate",
    route_after_validate,
    {
        "execute_fanout": "execute_fanout",
        "plan_rejected": "plan_rejected",
    },
)

# execute_fanout 本身是一个“路由节点”，它返回多个 Send
# LangGraph 根据 Send 的 target 并行派发 worker
builder.add_conditional_edges(
    "execute_fanout",
    lambda state: state,   # 占位：Send 已在 execute_fanout 的返回值中
    ["query_device", "query_sensor", "retrieve_knowledge"],
)

# fan-in：三个 worker 都连到 diagnose
builder.add_edge("query_device", "diagnose")
builder.add_edge("query_sensor", "diagnose")
builder.add_edge("retrieve_knowledge", "diagnose")

builder.add_edge("diagnose", END)
builder.add_edge("plan_rejected", END)

graph = builder.compile()


# ============================================================
# 8. 运行示例
# ============================================================

if __name__ == "__main__":
    initial_state = {
        "user_query": "D-102 振动和温度都异常，帮我分析原因。",
        "plan": {},
        "plan_errors": [],
        "device_status": {},
        "sensor_data": {},
        "knowledge_results": [],
        "evidence_log": [],
        "diagnosis": "",
    }

    result = graph.invoke(initial_state)
    print(result["diagnosis"])
    print("\n--- evidence_log ---")
    for item in result["evidence_log"]:
        print(item)