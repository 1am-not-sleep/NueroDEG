# 开发路线图

## 一期 (已完成)
- [x] 知识库构建 (9种细胞类型, 15条通路)
- [x] 核心分析管道 (加载→筛选→匹配→富集→报告)
- [x] 可视化 (火山图 + 柱状图)
- [x] CLI入口

## 二期 (已完成)
- [x] Agent状态管理 (agent_core/state.py)
- [x] Tool Trace记录 (agent_core/trace.py)
- [x] Guardrails安全机制 (agent_core/guardrails.py)
- [x] 质量评估 (agent_core/quality.py)
- [x] Run Memory (agent_core/memory.py)
- [x] Streamlit网页界面 (streamlit_app.py)
- [x] 中英界面、输入/产出预览和 Cell type 标准标签

## 三期 (当前版本)
- [x] 对话式 Ask Agent 和自然语言阈值重跑
- [x] 可选 OpenAI tool calling + 离线自动回退
- [x] Streamlit Community Cloud 部署配置和冒烟测试
- [ ] 在线Enrichr API稳定性与限流完善
- [ ] 单细胞参考数据集成
- [ ] PubMed文献检索集成
- [ ] 支持更多DEG输入格式
