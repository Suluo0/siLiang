"""
全局请求上下文 —— 通过 ContextVar 在协程链路中无感知传递 trace_id / caller / budget
挂载点：
  - ReAct Agent: master.py.handle() 入口
  - InterviewSession: interview_api.py 端点入口
  - SlaveSession: slave.py.execute() 入口
"""
from contextvars import ContextVar
from typing import Optional

current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")
current_caller: ContextVar[str] = ContextVar("current_caller", default="unknown")
current_budget: ContextVar[Optional[object]] = ContextVar("current_budget", default=None)
