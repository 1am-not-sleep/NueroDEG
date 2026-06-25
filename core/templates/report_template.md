# NeuroDEG 差异表达基因分析报告

> 生成时间: {{generated_at}}
> 输入文件: {{input_file}}

---

## 一、数据概览

| 指标 | 数值 |
|:----|:----|
| 总基因数 | {{total_genes}} |
| 显著差异基因 | {{sig_genes}} |
| 上调基因数 | {{up_genes}} |
| 下调基因数 | {{down_genes}} |
| 筛选阈值 | log2FC > {{fc_cutoff}}, padj < {{p_cutoff}} |

---

## 二、神经细胞类型分析

{% for ct in cell_type_analysis %}
### {{ ct.type }}

| 指标 | 数值 |
|:----|:----|
| 匹配标记基因数 | {{ ct.matched }} / {{ ct.total_markers }} |
| 上调标记基因 | {{ ct.up_genes }} |
| 下调标记基因 | {{ ct.down_genes }} |

**受影响的基因:**
{% if ct.affected_genes %}
{% for g in ct.affected_genes %}
- **{{ g.gene }}** ({{ g.function }}) — {{ g.direction == 'up' and '↑ 上调' or '↓ 下调' }}
{% endfor %}
{% else %}
- (无显著差异的标记基因)
{% endif %}

**解读:**
> {{ ct.interpretation }}

{% if ct.disease_hints %}
**疾病关联提示:** {{ ct.disease_hints }}
{% endif %}

{% endfor %}
---

## 三、通路富集分析

{% for pw in pathway_analysis %}
### {{ pw.name }}

- 关联细胞类型: {{ pw.cell_types }}
- 匹配差异基因: {{ pw.matched_genes }}
- 解读: {{ pw.interpretation }}

{% endfor %}
---

## 四、综合结论

{{ summary }}

---

## 五、推测与假设

{% for hypothesis in hypotheses %}
- {{ hypothesis }}
{% endfor %}

---

## 六、局限性

1. 本分析基于内置神经细胞知识库，受知识库覆盖范围限制
2. DEG结果仅为相关性分析，因果推断需进一步验证
3. 单数据集分析可能受批次效应影响
4. 报告解读基于规则引擎，仅供参考

---

*NeuroDEG — 神经细胞基因表达差异分析工具*
