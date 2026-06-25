# Agent 架构设计

## 概览

NeuroDEG Agent 采用顺序管道式架构，其中每个步骤由独立的 tool 函数执行，通过 `agent_core` 进行编排和追踪。

## 核心组件

| 组件 | 职责 |
|:----|:------|
| AgentState | 贯穿全管线的运行状态容器 |
| TraceRecorder | 记录每个 tool 调用的决策、耗时和结果 |
| Guardrails | 输入/输出的安全检查 |
| QualityEvaluator | 分析结果的质量分级 |
| RunMemory | 保存运行记录和manifest |

## 决策树



## 数据流

所有结果以 dict 形式在模块间传递，最终持久化到 results/ 目录。
