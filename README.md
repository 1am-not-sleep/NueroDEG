# NeuroDEG — 神经细胞基因表达差异分析 Agent

> 🧬 课程作业项目 | 基于 DEG 数据的神经生物学智能分析工具

---

## 项目简介

NeuroDEG 是一个基于规则引擎的 Agent 系统，用户上传差异表达基因（DEG）表格后，系统自动完成以下流程：

- 数据校验与标准化
- 差异基因筛选（可自定义阈值）
- 神经细胞类型匹配（基于标记基因知识库）
- GO 神经通路富集（超几何检验 + FDR 校正）
- 结果可视化（火山图、细胞类型柱状图）
- 结构化 Markdown 报告生成
- Tool Trace 追踪 + Guardrails 安全机制 + 质量评估

---

## 数据来源

### 标记基因知识库（core/knowledge_base.json）

| 来源 | 用途 |
|:----|:------|
| CellMarker 数据库 | 细胞类型标记基因手工整理 |
| Allen Brain Atlas | 脑细胞分类体系参考 |
| GeneCards / NCBI | 基因功能概述与别名核对 |

覆盖 **9 种神经细胞类型**，共 **87 个精选标记基因**，每个基因标注了功能描述、功能分类、上调解读、下调解读及疾病关联。

| 细胞类型 | 标记基因数 | 示例标记基因 |
|:---------|:----------:|:------------|
| 兴奋性神经元 | 13 | SLC17A7, CAMK2A, SATB2, GRIN1, GRIA1 |
| 抑制性神经元 | 12 | GAD1, GAD2, PVALB, SST, VIP |
| 星形胶质细胞 | 10 | GFAP, S100B, AQP4, ALDH1L1, GLUL |
| 小胶质细胞 | 11 | AIF1, CD68, TMEM119, CX3CR1, TREM2 |
| 少突胶质细胞 | 10 | MBP, OLIG2, MOG, PLP1, MAG |
| 神经干细胞/前体细胞 | 8 | SOX2, NES, PAX6, DCX, ASCL1 |
| 多巴胺能神经元 | 8 | TH, SLC6A3, DRD2, DRD1, NR4A2 |
| 胆碱能神经元 | 8 | CHAT, ACHE, SLC5A7, CHRM1, CHRNA4 |
| 血清素能神经元 | 7 | TPH2, SLC6A4, HTR1A, HTR2A |

### 通路数据

**本地通路库（core/pathways.json）**

15 条手工整理的神经相关通路，含 KEGG ID：

| 通路 | KEGG ID | 关联细胞类型 |
|:----|:--------|:------------|
| 谷氨酸能突触 | hsa04724 | 兴奋性神经元 |
| GABA能突触 | hsa04727 | 抑制性神经元 |
| 多巴胺能突触 | hsa04728 | 多巴胺能神经元 |
| 胆碱能突触 | hsa04725 | 胆碱能神经元 |
| 5-羟色胺能突触 | hsa04726 | 血清素能神经元 |
| 长时程增强(LTP) | hsa04720 | 兴奋性神经元 |
| 突触囊泡循环 | hsa04721 | 所有神经元 |
| 钙信号通路 | hsa04020 | 所有神经细胞 |
| 自噬-溶酶体通路 | hsa04140 | 兴奋性、多巴胺能神经元 |
| 其他 7 条神经通路... | — | — |

**GO 神经通路富集（data/go.obo + data/goa_human.gaf.gz）**

- 从 GO 本体（Gene Ontology）中过滤出 **~2371 条**神经相关的 GO terms（biological process + molecular function）
- 使用 **超几何检验** 计算富集显著性
- 采用 **Benjamini-Hochberg 方法** 进行多重假设检验校正
- 背景基因集：人类基因组 ~38,822 个注释基因
- 分析结果中包含 p 值和校正后 p 值

### 在线富集（可选）

支持通过 Enrichr API（https://maayanlab.cloud/Enrichr/）进行在线 KEGG 通路富集，当网络可用时使用 `--use-api` 参数启用。

---

## 分析方法

### 分析流程

```
Input Checker (列名自动识别/校验)
  → DEG Filter (|log2FC| > threshold, padj < cutoff)
  → Volcano Plot + Cell Type Bar Chart
  → [条件决策] 显著基因 ≥ 10?
    → 是: Neural Cell Type Matching + GO Enrichment + Local Pathway Match
    → 否: 跳过富集，报告提示
  → Report Generator (规则引擎 + 知识库)
  → Guardrails (医学声明安全检查)
  → Quality Evaluator (ready / review / blocked)
  → Run Memory (results/<run_id>/run_manifest.json)
```

### 差异基因筛选标准

- 默认阈值：`|log2FC| > 1.0`, `padj < 0.05`
- 用户可自定义 `--fc-cutoff` 和 `--p-cutoff`

### 细胞类型识别方法

基于标记基因 overlap 匹配：将上调和下调的差异基因列表与内置知识库中每种细胞类型的标记基因集合进行交叉比对，统计每种细胞类型中有多少标记基因发生了显著变化。

### GO 通路富集方法

使用超几何分布检验：

```
p = P(X ≥ k) = Σᵢ₌ₖᵐᶦⁿ⁽ⁿ,ᴹ⁾ C(M,i)·C(N-M,n-i) / C(N,n)

其中：
  N = 背景基因总数 (38,822)
  M = 通路中的基因数
  n = 差异基因总数
  k = 差异基因中属于该通路的基因数
```

多重检验校正使用 Benjamini-Hochberg FDR 方法。

---

## 目录结构

```
NeuroDEG/
│
├── core/                          ← 知识库核心
│   ├── knowledge_base.json        ← 9种细胞类型标记基因库
│   ├── pathways.json              ← 15条神经通路
│   ├── go_enrichment_cache.json   ← GO 富集预计算缓存
│   └── templates/report_template.md
│
├── analysis/                      ← 核心分析模块
│   ├── loader.py                  ← DEG 文件加载/校验/列名自动识别
│   ├── filter.py                  ← 差异基因筛选
│   ├── neural_matcher.py          ← 神经细胞类型 + 通路匹配
│   ├── enrichment.py              ← GO 富集 + 本地通路 + Enrichr API
│   └── interpreter.py             ← 结果解读 + 报告生成
│
├── utils/
│   └── visualizer.py              ← 火山图 + 细胞类型柱状图
│
├── agent_core/                    ← Agent 框架
│   ├── state.py                   ← 运行状态管理
│   ├── trace.py                   ← Tool Trace 记录
│   ├── guardrails.py              ← 医学声明安全检查
│   ├── quality.py                 ← 质量评估 (ready/review/blocked)
│   ├── memory.py                  ← Run memory + manifest
│   └── chat.py                    ← Ask Agent 追问
│
├── data/                          ← 数据文件
│   ├── example_neuro_deg.csv      ← 示例 DEG 数据
│   ├── go.obo                     ← GO 本体（~35 MB）
│   ├── goa_human.gaf.gz           ← 人类基因-GO 注释（~15 MB）
│   ├── missing_p_adj.csv          ← 缺列测试数据
│   └── few_significant_genes.csv  ← 临界测试数据
│
├── app.py                         ← CLI 主入口
├── streamlit_app.py               ← Streamlit 网页界面
├── requirements.txt               ← 依赖
├── tests/                         ← 单元测试
└── docs/                          ← 文档
```

---

## 安装与使用

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 命令行运行

```bash
# 使用示例数据（默认阈值）
python app.py data/example_neuro_deg.csv

# 自定义筛选阈值
python app.py data/example_neuro_deg.csv --fc-cutoff 1.5 --p-cutoff 0.01

# 启用在线富集 API
python app.py data/example_neuro_deg.csv --use-api

# 指定输出目录
python app.py data/example_neuro_deg.csv --output-dir results/my_analysis
```

### 网页界面

```bash
streamlit run streamlit_app.py
```

浏览器打开后：
1. 在侧边栏选择"示例数据"或上传自定义 DEG 文件
2. 调整筛选阈值（可选）
3. 点击 **开始分析**
4. 查看 7 个 Tab 的分析结果

### 运行测试

```bash
python -m unittest discover -s tests -v
```

### 输入数据格式

CSV 文件必须包含以下列（列名自动识别，不区分大小写）：

| 列 | 说明 | 支持的列名示例 |
|:---|:-----|:-------------|
| 基因 | Gene symbol | gene, Gene, symbol, gene_name |
| 差异倍数 | log2 Fold Change | log2FC, log2_fc, fold_change, FC |
| 校正 P 值 | Adjusted p-value | padj, p_adj, fdr, qvalue, adjusted_p_value |

示例：

```csv
gene,log2FC,p_adj
SNAP25,-1.4,0.004
MBP,-2.1,0.001
GFAP,1.6,0.01
AIF1,2.3,0.0005
```

---

## 输出说明

### CLI 输出

运行完成后在 `output/` 或指定目录下生成：

| 文件 | 内容 |
|:----|:-----|
| `report.md` | 完整分析报告（Markdown 格式） |
| `volcano.png` | 火山图 |
| `cell_type_bar.png` | 细胞类型匹配柱状图 |
| `up_genes.csv` | 上调基因列表 |
| `down_genes.csv` | 下调基因列表 |

### Agent Manifest

每次运行记录保存在 `results/<run_id>/run_manifest.json`，包含：

- 运行参数与时间戳
- Tool Trace（每个步骤的决策、耗时、状态）
- 质量评估等级与原因
- Guardrails 检查结果
- 数据统计摘要

---

## 局限性

1. 细胞类型识别基于标记基因 overlap，非单细胞反卷积方法
2. DEG 分析结果为相关性，不能直接证明蛋白水平或功能变化
3. Bulk RNA-seq 结果可能受细胞比例变化影响
4. GO 富集基于关键字过滤的神经相关子集，非全库扫描
5. 报告解读基于规则引擎，仅供研究参考，不构成医学建议

---

## 技术栈

| 组件 | 选择 |
|:----|:-----|
| 语言 | Python 3.8+ |
| 数据处理 | pandas, numpy |
| 可视化 | matplotlib, seaborn |
| Web 界面 | streamlit |
| 统计检验 | 纯 Python 实现（math.lgamma） |
| 在线富集 | requests (Enrichr API) |
| 测试 | unittest |