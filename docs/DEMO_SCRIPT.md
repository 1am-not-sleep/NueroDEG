# Demo Script

## 1. 项目介绍

NeuroDEG-Agent 面向已经计算好的神经相关 DEG 表格，自动完成输入检查、差异基因筛选、火山图绘制、神经模块识别、知识库解释和报告生成。

## 2. 启动方式

```bash
streamlit run app.py
```

## 3. 正常案例

使用：

```text
data/example_neuro_deg.csv
```

预期展示：

- Total genes: 40
- Significant up-regulated genes: 9
- Significant down-regulated genes: 11
- 火山图
- Microglia / neuroinflammation 上调
- Oligodendrocyte / myelination 下调
- Synaptic transmission 下调
- Markdown report

## 4. 错误输入案例

使用：

```text
data/missing_p_adj.csv
```

预期：

```text
Missing required columns: p_adj.
```

## 5. 显著基因过少案例

使用：

```text
data/few_significant_genes.csv
```

预期：

- 系统不崩溃
- 仍然生成报告
- 报告提示 significant genes 数量太少，解释应谨慎

## 6. 汇报重点

强调它不是普通 chatbot，而是具有工具调用流程的 biomedical agent：

- 会检查输入
- 会筛选 DEG
- 会绘图
- 会做 marker-set 富集
- 会结合神经知识库解释
- 会给出局限性和验证建议
