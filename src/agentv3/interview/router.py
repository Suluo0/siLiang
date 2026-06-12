"""
路由决策 — 根据评分结果决定下一轮面试路线
"""

MAX_ROUNDS = 10
MAX_CONSECUTIVE_LOW = 2

ROUTE_DERIVATIVE = "derivative"
ROUTE_EXTENSION = "extension"
ROUTE_PREREQUISITE = "prerequisite"
ROUTE_SUMMARY = "summary"


def decide_route(total_score: float, round_number: int, consecutive_low: int = 0) -> str:
    """
    根据总分和轮次决定下一轮面试路线。

    Args:
        total_score: 加权总分 0-1
        round_number: 当前轮次号（1-based）
        consecutive_low: 连续低分轮数（total < 0.30）

    Returns:
        "derivative" | "extension" | "prerequisite" | "summary"
    """
    if round_number >= MAX_ROUNDS:
        return ROUTE_SUMMARY

    if consecutive_low >= MAX_CONSECUTIVE_LOW:
        return ROUTE_SUMMARY

    if total_score >= 0.80:
        return ROUTE_DERIVATIVE
    elif total_score >= 0.50:
        return ROUTE_EXTENSION
    elif total_score >= 0.30:
        return ROUTE_PREREQUISITE
    else:
        return ROUTE_SUMMARY


def get_next_consecutive_low(total_score: float, current_consecutive_low: int) -> int:
    """更新连续低分计数"""
    if total_score < 0.30:
        return current_consecutive_low + 1
    return 0
