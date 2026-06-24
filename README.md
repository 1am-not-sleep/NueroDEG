# NeuroDEG — 神经细胞基因表达差异分析 Agent

> 🧬 课程作业项目 · 基于 NeuroDEG + NeuroDEG-2 两个原型分支合并重构

---

## 项目定位

根据用户上传的 DEG（差异表达基因）文件，自动识别神经细胞相关基因的差异化表达，结合内置的神经细胞知识库进行生物学解读，通过 **Agent 化管道** 展示每一步的分析决策和中间结果，最终输出结构化分析报告。

---

## 合并背景

| 来源 | 核心优势 | 贡献内容 |
|:----|:---------|:---------|
| **NeuroDEG（本分支）** | 知识库扎实，分析逻辑完整 | knowledge_base.json（9种细胞类型，~80标记基因，含方向性解读、疾病关联）；pathways.json（15条通路含KEGG ID）；列名自动识别；双可视化（火山图+柱状图）；报告模板 |
| **NeuroDEG-2（合作分支）** | Agent架构设计清晰，展示友好 | Streamlit交互界面；Agent Trace追踪框架；Guardrails安全机制；Quality Evaluator质量评估；Run Memory运行记录 |

---

## Agent 分析管道

```
┌──────────────────────────────────────────────┐
│              ① 输入检查 (Input Checker)        │
│  ┌─────────────────────────────────────────┐ │
│  │  自动识别列名 / 校验必填列 / 缺失值处理  │ │
│  └─────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│              ② DEG 筛选 (DEG Filter)          │
│  ┌─────────────────────────────────────────┐ │
│  │  |log2FC| > threshold, padj < cutoff   │ │
│  │  分离上调/下调 → 统计摘要                │ │
│  └─────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│              ③ 可视化 (Visualization)          │
│  ┌─────────────────────────────────────────┐ │
│  │  火山图 + 细胞类型柱状图                 │ │
│  └─────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   ↓
       ╔═══════════════════════════════╗
       ║  条件决策：显著基因数量是否足够？  ║
       ║  - 足够 → 继续到④              ║  ← Agent 化分支
       ║  - 不足 → 跳过④⑤，直接到⑦      ║
       ╚═══════════════════════════════╝
              │                  │
              ↓ (足够)           ↓ (不足)
┌────────────────────┐    ┌──────────────────────┐
│ ④ 神经细胞类型匹配   │    │ ⑦ 报告生成 (报提示)  │
│ (neural_matcher)   │    │ ┌────────────────┐  │
└─────────┬──────────┘    │ │ 提示: 显著基因少  │  │
          ↓               │ │ 解释有限        │  │
┌────────────────────┐    │ └────────────────┘  │
│ ⑤ 通路富集分析      │    └──────────────────────┘
│ (local + API)      │
└─────────┬──────────┘
          ↓
┌──────────────────────────────────────────────┐
│              ⑥ 结果解读 (Interpreter)          │
│  ┌─────────────────────────────────────────┐ │
│  │  规则引擎 + 知识库 → Markdown 报告       │ │
│  └─────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   ↓
       ╔═══════════════════════════════╗
       ║  Guardrails：医学声明安全检查    ║
       ║  - 含"治愈/治疗/诊断"等词 → 警告 ║
       ╚═══════════════════════════════╝
                   ↓
       ╔═══════════════════════════════╗
       ║  Quality Evaluator：质量评估   ║
       ║  ready / review / blocked     ║
       ╚═══════════════════════════════╝
                   ↓
┌──────────────────────────────────────────────┐
│              ⑧ 输出报告 + Run Memory          │
│  ┌─────────────────────────────────────────┐ │
│  │  results/<run_id>/                      │ │
│  │  ├── report.md                          │ │
│  │  ├── volcano.png                        │ │
│  │  ├── cell_type_bar.png                  │ │
│  │  ├── filter_results.csv                 │ │
│  │  └── run_manifest.json (含 trace)       │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

## 目录结构

```
NeuroDEG-new/
│
├── README.md                          ← 项目说明
│
├── core/                              ← 知识库核心
│   ├── knowledge_base.json            ← 9种细胞类型，完整标记基因库
│   ├── pathways.json                  ← 15条通路 + KEGG ID
│   └── templates/
│       └── report_template.md         ← 报告模板
│
├── analysis/                          ← 核心分析模块
│   ├── __init__.py
│   ├── loader.py                      ← 读取/校验DEG，列名自动识别
│   ├── filter.py                      ← 差异基因筛选
│   ├── neural_matcher.py              ← 神经细胞类型 + 通路匹配
│   ├── enrichment.py                  ← 本地 + Enrichr API 富集
│   └── interpreter.py                 ← 结果解读 + 报告生成
│
├── utils/                             ← 工具模块
│   ├── __init__.py
│   └── visualizer.py                  ← 火山图 + 柱状图
│
├── agent_core/                        ← Agent 框架
│   ├── __init__.py
│   ├── state.py                       ← 运行状态管理
│   ├── trace.py                       ← Tool trace 记录
│   ├── guardrails.py                  ← 医学声明安全检查
│   ├── quality.py                     ← 质量评估 (ready/review/blocked)
│   ├── memory.py                      ← Run memory + manifest
│   └── chat.py                        ← Ask Agent 追问接口
│
├── app.py                             ← CLI 主入口（增强版）
├── streamlit_app.py                   ← Streamlit 网页界面
│
├── data/                              ← 测试数据
│   ├── example_neuro_deg.csv          ← 正常输入
│   ├── missing_p_adj.csv              ← 缺列测试
│   └── few_significant_genes.csv      ← 临界案例
│
├── input/                             ← 用户放置DEG文件
│   └── .gitkeep
│
├── output/                            ← 输出目录
│   └── .gitkeep
│
├── results/                           ← 带时间戳的运行记录
│   └── .gitkeep
│
├── tests/                             ← 单元测试
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_filter.py
│   ├── test_neural_matcher.py
│   ├── test_guardrails.py
│   └── test_quality.py
│
├── docs/                              ← 文档
│   ├── AGENT_ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── SOURCES.md
│
└── requirements.txt                   ← 依赖
```

---

## 模块设计

### 1. core/ — 知识库核心

**knowledge_base.json** — 9种细胞类型，每种包含：
- 标记基因列表（gene, alias, function, category）
- 疾病关联 (disease_links)
- 上调/下调方向性解读 (interpretation.up / interpretation.down)

| 细胞类型 | 标记基因示例 | 基因数 |
|:---------|:------------|:------:|
| 兴奋性神经元 | SLC17A7, CAMK2A, SATB2, NRGN, SYT1, GRIN1, GRIA1 | ~13 |
| 抑制性神经元 | GAD1, GAD2, PVALB, SST, CALB1, VIP, NPY | ~12 |
| 星形胶质细胞 | GFAP, S100B, AQP4, ALDH1L1, SLC1A2, GLUL | ~10 |
| 小胶质细胞 | AIF1, CD68, TMEM119, CX3CR1, CSF1R, TREM2 | ~11 |
| 少突胶质细胞 | MBP, OLIG2, MOG, PLP1, CNP, SOX10, MAG | ~10 |
| 神经干细胞 | SOX2, NES, PAX6, MKI67, DCX, ASCL1 | ~8 |
| 多巴胺能神经元 | TH, SLC6A3, DRD2, DRD1, DDC, NR4A2 | ~8 |
| 胆碱能神经元 | CHAT, ACHE, SLC5A7, CHRM1, CHRNA4 | ~8 |
| 血清素能神经元 | TPH2, SLC6A4, HTR1A, HTR2A, DDC | ~7 |

**pathways.json** — 15条神经通路 + KEGG ID + 关联细胞类型

| 通路 | KEGG ID | 关联细胞类型 |
|:----|:--------|:------------|
| 谷氨酸能突触 | hsa04724 | 兴奋性神经元 |
| GABA能突触 | hsa04727 | 抑制性神经元 |
| 多巴胺能突触 | hsa04728 | 多巴胺能神经元 |
| 胆碱能突触 | hsa04725 | 胆碱能神经元 |
| 5-羟色胺能突触 | hsa04726 | 血清素能神经元 |
| 长时程增强(LTP) | hsa04720 | 兴奋性神经元 |
| 神经营养因子 | hsa04722 | 所有神经细胞 |
| 神经炎症 | — | 小胶质、星形胶质细胞 |
| 反应性胶质增生 | — | 星形胶质、小胶质细胞 |
| 髓鞘形成 | — | 少突胶质细胞 |
| 神经发生 | — | 神经干细胞 |
| 突触囊泡循环 | hsa04721 | 所有神经元 |
| 钙信号 | hsa04020 | 所有神经细胞 |
| 自噬-溶酶体 | hsa04140 | 兴奋性、多巴胺能神经元 |
| 氧化应激 | — | 所有神经细胞 |

### 2. analysis/ — 核心分析模块

| 文件 | 输入 | 输出 | 关键逻辑 |
|:----|:-----|:-----|:---------|
| loader.py | CSV/TSV路径 | 标准化DataFrame | 自动检测列别名，处理编码差异 |
| filter.py | DataFrame+阈值 | 上调/下调/全部+摘要 | 基于padj和log2FC筛选 |
| neural_matcher.py | 上下调基因 | 细胞类型+通路匹配 | 基因名大写归一化，反向索引 |
| enrichment.py | 基因列表 | 本地+在线富集 | Enrichr API超时回退本地 |
| interpreter.py | 所有结果 | Markdown报告 | 规则引擎生成结论+假设 |

### 3. utils/ — 可视化

火山图（Top10基因标注）+ 细胞类型柱状图。matplotlib Agg后端。

### 4. agent_core/ — Agent 框架

**state.py** — 贯穿管线的运行状态
```python
class AgentState:
    def __init__(self, input_file, params):
        self.params = params
        self.steps = []          # 步骤记录
        self.input_df = None
        self.filter_result = None
        self.match_result = None
        self.enrichment_result = None
        self.report = None
        self.errors = []
        self.warnings = []
```

**trace.py** — Tool Trace
```python
class StepRecord:
    def __init__(self, tool_name, input_snapshot, decision):
        self.tool = tool_name
        self.status = "running"  # → success|skipped|failed
        self.input = input_snapshot
        self.decision = decision
        self.duration_ms = 0
```
TraceRecorder类：维护步骤列表，序列化供manifest输出。

**guardrails.py** — 医学声明检查
- 输入检查：文件是否存在、能否被loader读取
- 输出检查：报告文本是否含禁忌关键词（"治愈""治疗""cure""diagnose"等）

**quality.py** — 质量评估
| 等级 | 条件 |
|:----|:------|
| ready | 显著>50 + 匹配≥3种 + 无guardrail警告 |
| review | 显著10-50 或 匹配<3 或 有轻微警告 |
| blocked | 显著<10 或 严重guardrail警告或加载失败 |

**memory.py** — 运行记录
```
results/run_20260624_184200/
├── report.md, up_genes.csv, down_genes.csv
├── volcano.png, cell_type_bar.png
└── run_manifest.json
```
manifest包含时间戳、参数、摘要、trace、quality等级、guardrails。

**chat.py** — Ask Agent追问（三级）
1. "XX基因是什么？" → 查knowledge_base
2. "上调的XX细胞意味着什么？" → 查interpretation
3. "总体上说明了什么？" → 复用conclusion

### 5. app.py — CLI主入口

完整执行流程：
```
1. 初始化AgentState + TraceRecorder
2. input_checker()     → loader + trace
3. deg_filter()        → filter + trace
4. volcano_plot()      → 可视化 + trace
5. if 显著 > 10:
       neural_matcher()
       enrichment()      ← 条件执行
   else: warning
6. report_generator()  → interpreter + trace
7. guardrails()
8. quality_evaluator()
9. memory.save_run()
```

用法：
```bash
# 基本
python app.py data/example_neuro_deg.csv
# 自定义阈值
python app.py data/example_neuro_deg.csv --fc-cutoff 1.5 --p-cutoff 0.01
# 启用在线富集
python app.py data/example_neuro_deg.csv --use-api
# 启动网页
python app.py --streamlit
```

### 6. streamlit_app.py — 网页界面

Tab分页：火山图 | Agent Trace | 神经细胞类型 | 通路富集 | 完整报告 | 质量评估 | Ask Agent

---

## 技术栈

| 组件 | 选择 |
|:----|:-----|
| 语言 | Python 3.8+ |
| 数据处理 | pandas, numpy |
| 可视化 | matplotlib, seaborn |
| Web界面 | streamlit |
| 在线富集 | requests (Enrichr API) |
| 输出格式 | Markdown + PNG |
| 测试 | unittest |

---

## 开发优先级

### Phase 1 — 基础设施 (Day1上午)
- core/ + analysis/ + utils/ → 从原NeuroDEG迁移 ✅ 代码已就绪
- 验证app.py跑通example.csv ✅ 已就绪
- requirements.txt ✅ 已声明

### Phase 2 — Agent核心 (Day1下午)
| 文件 | 工时 |
|:----|:----|
| state.py | 30min |
| trace.py | 45min |
| guardrails.py | 30min |
| quality.py | 30min |
| memory.py | 45min |
| 整合app.py | 1h |

### Phase 3 — Web界面 (Day2上午)
- Streamlit主框架 1.5h
- Tab布局 1h
- 文件上传+参数 30min

### Phase 4 — 收尾 (Day2下午)
- 测试数据 30min
- 单元测试 1h
- 文档 30min
- Bug fix + 展示准备 1h

---

## 交付物清单

- [x] 完整知识库 (core/)
- [x] 核心分析模块 (analysis/)
- [x] 可视化模块 (utils/visualizer.py)
- [x] CLI主入口初版 (app.py)
- [ ] Agent核心框架 (agent_core/) — **优先开发**
- [ ] Streamlit网页界面 (streamlit_app.py)
- [ ] 测试数据 (data/)
- [ ] 单元测试 (tests/)
- [ ] 文档 (docs/)

---

## 局限性

1. 使用marker-set overlap，非正式GO/KEGG超几何富集
2. DEG不能直接证明蛋白水平或功能变化
3. bulk RNA-seq可能受细胞比例变化影响
4. 报告解读基于规则引擎，仅供参考
5. Guardrails使用关键词匹配，不能替代专业审核

---

## 知识库来源

| 来源 | 用途 |
|:----|:-----|
| CellMarker数据库 | 细胞类型标记基因 |
| Allen Brain Atlas | 脑细胞分类体系 |
| GeneCards / NCBI | 基因功能概述 |
| KEGG | 神经相关通路 |

---

## License

课程作业，仅限学习用途。
