# NeuroDEG-Agent

NeuroDEG-Agent 是一个用于解释神经相关差异表达基因表的生物医学 AI Agent demo。用户上传已经计算好的 DEG CSV，系统会检查输入、筛选显著上调/下调基因、绘制火山图、识别神经细胞类型/功能模块，并生成 Markdown 解释报告。

当前版本已经从固定 pipeline 升级为规则型 agent：它会记录 tool trace、根据中间结果做条件决策、运行 guardrails、给出质量评分，并把每次运行保存为 JSON manifest。

## MVP 功能

- 输入检查：必须包含 `gene`, `log2FC`, `p_adj`
- DEG 筛选：默认 `abs(log2FC) > 1` 且 `p_adj < 0.05`
- 输出上调/下调基因表
- 生成火山图
- 基于 marker gene 识别 neuron、microglia、astrocyte、oligodendrocyte、synapse 等模块
- 基于 `scipy` 对神经 marker set 做超几何富集检验和 FDR 校正
- 生成结构化解释报告
- Streamlit 网页演示
- Agent trace：展示每一步 tool call 的决策和观察结果
- Guardrails：检查输入和报告是否有过度医学结论
- Quality evaluator：给出 `ready / review / blocked` 质量等级
- Run memory：保存 `results/runs/<run_id>/run_manifest.json`
- Ask Agent：基于当前分析结果回答 follow-up 问题

## 项目结构

```text
.
├── app.py
├── agent.py
├── src/main.py
├── tools/
│   ├── input_checker.py
│   ├── deg_filter.py
│   ├── plotting.py
│   ├── enrichment.py
│   ├── neural_classifier.py
│   ├── knowledge_retriever.py
│   └── report_generator.py
├── agent_core/
│   ├── state.py
│   ├── planner.py
│   ├── guardrails.py
│   ├── quality.py
│   ├── memory.py
│   └── chat.py
├── data/
│   ├── example_neuro_deg.csv
│   ├── missing_p_adj.csv
│   └── few_significant_genes.csv
├── knowledge_base/
├── results/
└── requirements.txt
```

## 安装

```bash
python3 -m pip install -r requirements.txt
```

## 命令行运行

```bash
python3 src/main.py data/example_neuro_deg.csv
```

输出文件会写入 `results/`：

```text
results/up_genes.csv
results/down_genes.csv
results/annotated_genes.csv
results/volcano_plot.png
results/neural_modules.csv
results/marker_enrichment.csv
results/report.md
```

## 网页运行

```bash
streamlit run app.py
```

打开 Streamlit 给出的本地地址后，上传 CSV 或直接使用示例数据，点击 `Analyze` 即可生成结果。

页面包含：

```text
Volcano
Agent Trace
Neural Modules
Enrichment
Report
Quality
Ask Agent
Output Files
```

## 输入格式

CSV 必须包含：

| column | meaning |
| --- | --- |
| `gene` | gene symbol |
| `log2FC` | log2 fold change |
| `p_adj` | adjusted p-value / FDR |

示例：

```csv
gene,log2FC,p_adj
SNAP25,-1.4,0.004
MBP,-2.1,0.001
C1QA,1.4,0.02
GFAP,1.6,0.01
```

## 两天协作建议

### Day 1

- 工程：跑通 `input_checker -> deg_filter -> plotting -> report`
- 生物内容：完善 `data/example_neuro_deg.csv` 和 `knowledge_base/*.md`
- 晚上：合并到 `main` 后必须能运行 `python3 src/main.py`

### Day 2

- 工程：完善 Streamlit 页面和错误处理
- 生物内容：检查报告解释是否准确，准备 PPT
- 展示前：只修 bug，不再新增大功能

## GitHub 协作规则

- `main` 只保留可运行版本
- 每个人在自己的 feature 分支开发
- 不直接 push 到 `main`
- 合并前至少用 `data/example_neuro_deg.csv` 跑一次
- 不要两个人同时改同一个文件，尤其是 `app.py` 和 `README.md`

推荐分支：

```text
feature/core-app
feature/bio-assets
feature/report-template
fix/demo-bugs
```

PR 描述模板：

```text
完成内容：
-

测试方式：
-

是否影响其他模块：
-
```

## Demo 测试用例

| 文件 | 目的 | 期望 |
| --- | --- | --- |
| `data/example_neuro_deg.csv` | 正常输入 | 生成完整结果 |
| `data/missing_p_adj.csv` | 缺少必要列 | 返回缺列错误 |
| `data/few_significant_genes.csv` | 显著基因很少 | 报告提示解释有限 |

本地测试：

```bash
python3 -m unittest discover -s tests
```

## Agent 化设计

当前 agent 的主流程：

```text
Input Checker
→ DEG Filter
→ conditional decision: run or skip enrichment
→ Volcano Plot Tool
→ Neural Module Classifier
→ Marker Enrichment Tool
→ Knowledge Retriever
→ Report Generator
→ Output Guardrails
→ Quality Evaluator
→ Run Memory
```

详细说明见：

```text
docs/AGENT_ARCHITECTURE.md
docs/ROADMAP.md
docs/SOURCES.md
```

## 展示讲法

一句话总结：

> NeuroDEG-Agent combines DEG filtering, volcano visualization, neural marker recognition, local knowledge retrieval, and report generation to support interpretation of neural transcriptomic DEG results.

局限性：

- 当前 MVP 使用 marker-set overlap，不是正式 GO/KEGG 统计富集
- DEG 不能直接证明蛋白水平或功能变化
- bulk RNA-seq 结果可能受到细胞比例变化影响
- 后续可接入 GSEApy、PubMed、Allen Brain Map 或单细胞参考数据
