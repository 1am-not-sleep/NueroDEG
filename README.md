# NeuroDEG — 神经细胞基因表达差异分析 Agent

> 🧬 本科生课程作业项目 | 两人团队 | 两天工期

## 项目定位

根据用户上传的 DEG（差异表达基因）文件，自动识别神经细胞相关基因的差异化表达，结合内置的神经细胞知识库对结果进行生物学解读，最终输出结构化分析报告。

---

## 分析流程

```
  ┌─────────────────────────────┐
  │  ① 输入：DEG 文件（CSV）      │  ← 用户上传
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ② 数据加载与校验（loader）    │  ← 自动识别列名
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ③ 差异基因筛选（filter）      │  ← |log2FC| > 1, padj < 0.05
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ④ 神经细胞类型匹配            │  ← 与内置知识库交叉比对
  │     (neural_matcher)         │
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ⑤ 功能富集分析（enrichment）  │  ← 本地预置通路 + Enrichr API
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ⑥ 结果解读（interpreter）     │  ← 规则引擎 + 知识库
  └─────────────┬───────────────┘
                ↓
  ┌─────────────────────────────┐
  │  ⑦ 输出报告（Markdown）       │  ← 可直接阅读或转为PDF
  └─────────────────────────────┘
```

---

## 知识库架构

知识库采用 JSON 格式，分三层设计：

### 第一层：基因标记库（core/knowledge_base.json）

为核心匹配层，存储每个神经细胞类型的：
- **标记基因列表**（约 80-100 个精选基因）
- **基因功能描述**（一两句话）
- **失调解读提示**（上调/下调分别意味着什么）

覆盖 8-10 种主要神经细胞类型：

| 细胞类型 | 核心标记基因示例 |
|---------|----------------|
| 兴奋性神经元 | SLC17A7, CAMK2A, SATB2 |
| 抑制性神经元 | GAD1, GAD2, PVALB, SST |
| 星形胶质细胞 | GFAP, S100B, AQP4, ALDH1L1 |
| 小胶质细胞 | AIF1, CD68, TMEM119, CX3CR1 |
| 少突胶质细胞 | MBP, OLIG2, MOG, PLP1 |
| 神经干细胞 | SOX2, NES, PAX6 |
| 多巴胺能神经元 | TH, SLC6A3, DRD2 |
| 胆碱能神经元 | CHAT, ACHE, SLC5A7 |

### 第二层：通路关联（core/pathways.json）

为富集分析提供本地 fallback：
- 预关联 ~15 条核心神经通路
- 每条通路标注涉及的基因和细胞类型
- 有网时优先调 Enrichr API，无网时回退本地

### 第三层：报告模板（core/templates/）

Markdown 模板 + 规则引擎，自动填充分析结果。

### 知识库来源

| 来源 | 用途 |
|:----|:-----|
| CellMarker 数据库 | 细胞类型标记基因 |
| Allen Brain Atlas | 脑细胞分类体系 |
| GeneCards / NCBI | 基因功能概述 |
| KEGG | 神经相关通路 |

---

## 目录结构

```
NeuroDEG/
│
├── README.md                   ← 项目说明
│
├── core/                       ← 知识库核心
│   ├── knowledge_base.json     ← 完整知识库（整合版）
│   ├── pathways.json           ← 通路关联数据
│   └── templates/              ← 报告模板
│       └── report_template.md
│
├── input/                      ← 用户放置DEG文件
│   └── example.csv             ← 示例数据
│
├── analysis/                   ← 核心分析模块
│   ├── __init__.py
│   ├── loader.py               ← 读取/校验DEG文件
│   ├── filter.py               ← 差异基因筛选
│   ├── neural_matcher.py       ← 神经细胞类型匹配
│   ├── enrichment.py           ← 富集分析
│   └── interpreter.py          ← 结果解读与报告生成
│
├── utils/                      ← 工具模块
│   ├── __init__.py
│   └── visualizer.py           ← 可视化（火山图等）
│
├── output/                     ← 输出目录
│   └── .gitkeep
│
└── app.py                      ← 主入口
```

---

## 技术栈

| 组件 | 选择 |
|:----|:-----|
| 语言 | Python 3.8+ |
| 核心库 | pandas, numpy |
| 可视化 | matplotlib, seaborn |
| 网络API（可选） | requests (调 Enrichr) |
| 输出格式 | Markdown |

---

## 运行方式

### 基本用法
```bash
python app.py input/my_deg_file.csv
```

### 可选参数
```bash
python app.py input/my_deg_file.csv \
    --use-api          # 启用Enrichr API富集分析
    --p-cutoff 0.01    # 自定义p值阈值（默认0.05）
    --fc-cutoff 1.5    # 自定义log2FC阈值（默认1.0）
    --output-dir ./my_results  # 指定输出目录
```

---

## 团队分工建议

### 成员 A — 数据处理 + 后端逻辑
- 搭建 knowledge_base.json
- loader.py — 读取、校验、清洗DEG数据
- filter.py — 差异筛选逻辑
- neural_matcher.py — 基因-细胞类型匹配算法

### 成员 B — 分析 + 解读 + 输出
- pathways.json — 通路数据整理
- enrichment.py — 富集分析
- interpreter.py — 规则引擎 + 报告填充
- visualizer.py — 可视化图表
- app.py — 主入口组装

---

## 交付物清单

- [ ] 完整的知识库（core/）
- [ ] 核心分析模块（analysis/）
- [ ] 可视化模块（utils/visualizer.py）
- [ ] 主入口脚本（app.py）
- [ ] 示例 DEG 数据
- [ ] 示例输出报告
- [ ] 上机演示（>15分钟全流程跑通）

---

## 许可证

课程作业，仅限学习用途。
