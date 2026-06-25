"""Rule-based bilingual report generation for NeuroDEG."""

from __future__ import annotations

import datetime
import os


def generate_interpretations(filter_result, match_result, enrichment_result, language="zh"):
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    go_results = enrichment_result.get("go", [])
    local_results = enrichment_result.get("local", [])
    conclusion_parts = []
    hypotheses = []

    if language == "en":
        conclusion_parts.append(
            f"The analysis detected {summary['significant']} significant genes "
            f"({summary['up']} up-regulated and {summary['down']} down-regulated). "
        )
        if cell_types:
            top_names = ", ".join(
                item.get("type_en", item["type"]) for item in cell_types[:3]
            )
            conclusion_parts.append(
                f"Marker overlap was strongest for {top_names}, with "
                f"{len(cell_types)} matched cell types in total. "
            )
            for cell_type in cell_types[:3]:
                direction = (
                    "up-regulated"
                    if cell_type["up_count"] > cell_type["down_count"]
                    else "down-regulated"
                )
                genes = (
                    cell_type["up_genes"]
                    if cell_type["up_count"] > cell_type["down_count"]
                    else cell_type["down_genes"]
                )
                hypotheses.append(
                    f"{cell_type.get('type_en', cell_type['type'])} markers were mainly "
                    f"{direction} ({genes}), suggesting a possible change in the associated "
                    "cell-state or cellular composition."
                )
        else:
            conclusion_parts.append(
                "No neural cell-type marker pattern passed the current matching criteria. "
            )

        if go_results:
            top_names = ", ".join(item["go_name"][:30] for item in go_results[:3])
            conclusion_parts.append(
                f"GO overrepresentation identified {len(go_results)} neural terms, "
                f"including {top_names}. "
            )
            for item in go_results[:5]:
                genes = ", ".join(item["overlap_genes"][:5])
                hypotheses.append(
                    f"{item['go_name']} (FDR={item['adjusted_p_value']:.2e}, "
                    f"overlap {item['ratio']}) involved {genes}."
                )
        if local_results:
            names = ", ".join(
                item.get("name_en") or item["pathway_name"]
                for item in local_results[:3]
            )
            conclusion_parts.append(
                f"Curated pathway matching also highlighted {names}. "
            )
        return {"summary": "".join(conclusion_parts), "hypotheses": hypotheses}

    conclusion_parts.append(
        f"共检测到 {summary['significant']} 个显著差异表达基因，"
        f"其中 {summary['up']} 个上调，{summary['down']} 个下调。"
    )
    if cell_types:
        top = cell_types[:3]
        conclusion_parts.append(
            f"主要影响 {'、'.join(item.get('display_name', item['type']) for item in top)} "
            f"等 {len(cell_types)} 种细胞类型。"
        )
        for cell_type in cell_types[:3]:
            direction = (
                "上调为主"
                if cell_type["up_count"] > cell_type["down_count"]
                else "下调为主"
            )
            genes = (
                cell_type["up_genes"]
                if cell_type["up_count"] > cell_type["down_count"]
                else cell_type["down_genes"]
            )
            hypotheses.append(
                f"{cell_type.get('display_name', cell_type['type'])}相关基因以"
                f"{direction}（{genes}），可能提示该细胞类型功能或组成发生变化。"
            )
    else:
        conclusion_parts.append("未检测到显著的神经细胞标记基因变化。")

    if go_results:
        top = go_results[:5]
        conclusion_parts.append(
            f"GO 富集分析发现 {len(go_results)} 条神经相关通路显著富集，"
            f"其中 {', '.join(item['go_name'][:20] for item in top[:3])} 等。"
        )
        for item in top:
            genes = ", ".join(item["overlap_genes"][:5])
            hypotheses.append(
                f"{item['go_name']}（FDR={item['adjusted_p_value']:.2e}，"
                f"重叠 {item['ratio']}），涉及 {genes}。"
            )
    if local_results:
        names = "、".join(item["pathway_name"] for item in local_results[:3])
        conclusion_parts.append(
            f"本地通路匹配显示 {names} 等 {len(local_results)} 条通路受影响。"
        )
    return {"summary": "".join(conclusion_parts), "hypotheses": hypotheses}


def _render_english(filter_result, match_result, enrichment_result, input_file, now):
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    go_results = enrichment_result.get("go", [])
    local_results = enrichment_result.get("local", [])
    interpretation = generate_interpretations(
        filter_result, match_result, enrichment_result, language="en"
    )

    lines = [
        "# NeuroDEG Differential-Expression Report",
        "",
        f"> Generated: {now}",
        f"> Input: {input_file}",
        "",
        "---",
        "## 1. Data Summary",
        "",
        "| Metric | Value |",
        "|:--|--:|",
        f"| Total genes | {summary['total_genes']} |",
        f"| Significant genes | {summary['significant']} |",
        f"| Up-regulated | {summary['up']} |",
        f"| Down-regulated | {summary['down']} |",
        f"| Cutoffs | abs(log2FC) > {summary['fc_cutoff']}, adjusted p < {summary['p_cutoff']} |",
        "",
    ]
    if summary["top_up"]:
        lines.append("**Top up-regulated genes**")
        lines.extend(
            f"- {item['gene']}: log2FC={item['log2fc']:.2f}, adjusted p={item['padj']:.2e}"
            for item in summary["top_up"]
        )
    if summary["top_down"]:
        lines.extend(["", "**Top down-regulated genes**"])
        lines.extend(
            f"- {item['gene']}: log2FC={item['log2fc']:.2f}, adjusted p={item['padj']:.2e}"
            for item in summary["top_down"]
        )

    lines.extend(["", "---", "## 2. Neural Cell-Type Signals", ""])
    if not cell_types:
        lines.append("No neural cell-type marker pattern passed the matching criteria.")
    else:
        for cell_type in cell_types:
            lines.extend(
                [
                    f"### {cell_type.get('display_name', cell_type['type'])}",
                    "",
                    f"- Source: {cell_type.get('source', '')}",
                    f"- Matched markers: {cell_type['matched']}/{cell_type['total_markers']}",
                    f"- Up-regulated markers: {cell_type['up_genes'] or 'None'}",
                    f"- Down-regulated markers: {cell_type['down_genes'] or 'None'}",
                    "",
                ]
            )

    lines.extend(["---", "## 3. GO Overrepresentation", ""])
    if go_results:
        lines.extend(
            [
                "| GO ID | Term | Overlap | P value | FDR |",
                "|:--|:--|:--:|--:|--:|",
            ]
        )
        lines.extend(
            f"| {item['go_id']} | {item['go_name'][:50]} | {item['ratio']} | "
            f"{item['p_value']:.2e} | {item['adjusted_p_value']:.2e} |"
            for item in go_results[:20]
        )
    else:
        lines.append("No GO term passed the configured criteria.")

    lines.extend(["", "---", "## 4. Curated Pathway Matches", ""])
    if local_results:
        for pathway in local_results[:10]:
            lines.extend(
                [
                    f"### {pathway.get('name_en') or pathway['pathway_name']}",
                    f"- Matched genes: {', '.join(pathway.get('matched_genes', []))}",
                    f"- Overlap: {pathway.get('overlap_ratio', '')}",
                    "",
                ]
            )
    else:
        lines.append("No curated pathway overlap was detected.")

    lines.extend(
        [
            "---",
            "## 5. Integrated Interpretation",
            "",
            interpretation["summary"],
            "",
            "## 6. Evidence-Based Hypotheses",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in interpretation["hypotheses"])
    lines.extend(
        [
            "",
            "---",
            "## 7. Limitations",
            "",
            "1. Cell-type signals are based on marker overlap and are not a deconvolution result.",
            "2. Differential expression supports association, not causality.",
            "3. Bulk tissue results may reflect cell-composition changes.",
            "4. The rule-based interpretation requires expert review.",
            "",
            "*For research and educational use only.*",
        ]
    )
    return "\n".join(lines)


def _render_chinese(filter_result, match_result, enrichment_result, input_file, now):
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    go_results = enrichment_result.get("go", [])
    local_results = enrichment_result.get("local", [])
    interpretation = generate_interpretations(
        filter_result, match_result, enrichment_result, language="zh"
    )

    lines = [
        "# NeuroDEG 差异表达基因分析报告",
        "",
        f"> 生成时间: {now}",
        f"> 输入文件: {input_file}",
        "",
        "---",
        "## 一、数据概览",
        "",
        "| 指标 | 数值 |",
        "|:--|--:|",
        f"| 总基因数 | {summary['total_genes']} |",
        f"| 显著差异基因 | {summary['significant']} |",
        f"| 上调基因数 | {summary['up']} |",
        f"| 下调基因数 | {summary['down']} |",
        f"| 筛选阈值 | abs(log2FC) > {summary['fc_cutoff']}, padj < {summary['p_cutoff']} |",
        "",
    ]
    if summary["top_up"]:
        lines.append("**Top 上调基因**")
        lines.extend(
            f"- {item['gene']}: log2FC={item['log2fc']:.2f}, padj={item['padj']:.2e}"
            for item in summary["top_up"]
        )
    if summary["top_down"]:
        lines.extend(["", "**Top 下调基因**"])
        lines.extend(
            f"- {item['gene']}: log2FC={item['log2fc']:.2f}, padj={item['padj']:.2e}"
            for item in summary["top_down"]
        )

    lines.extend(["", "---", "## 二、神经细胞类型分析", ""])
    if not cell_types:
        lines.append("未检测到符合当前标准的神经细胞 marker 模式。")
    else:
        for cell_type in cell_types:
            lines.extend(
                [
                    f"### {cell_type.get('display_name', cell_type['type'])}",
                    "",
                    f"- 数据来源: {cell_type.get('source', '')}",
                    f"- 匹配 marker: {cell_type['matched']}/{cell_type['total_markers']}",
                    f"- 上调 marker: {cell_type['up_genes'] or '无'}",
                    f"- 下调 marker: {cell_type['down_genes'] or '无'}",
                    f"- 解读: {cell_type['interpretation']}",
                    "",
                ]
            )

    lines.extend(["---", "## 三、GO 神经通路富集", ""])
    if go_results:
        lines.extend(
            [
                "| GO ID | 通路名称 | 重叠 | P 值 | FDR |",
                "|:--|:--|:--:|--:|--:|",
            ]
        )
        lines.extend(
            f"| {item['go_id']} | {item['go_name'][:50]} | {item['ratio']} | "
            f"{item['p_value']:.2e} | {item['adjusted_p_value']:.2e} |"
            for item in go_results[:20]
        )
    else:
        lines.append("未发现符合当前标准的 GO 神经通路。")

    lines.extend(["", "---", "## 四、本地通路匹配", ""])
    if local_results:
        for pathway in local_results[:10]:
            lines.extend(
                [
                    f"### {pathway['pathway_name']}",
                    f"- 匹配基因: {', '.join(pathway.get('matched_genes', []))}",
                    f"- 重叠比例: {pathway.get('overlap_ratio', '')}",
                    f"- 生物学过程: {pathway.get('biological_process', '')}",
                    "",
                ]
            )
    else:
        lines.append("未发现本地精选通路重叠。")

    lines.extend(
        [
            "---",
            "## 五、综合结论",
            "",
            interpretation["summary"],
            "",
            "## 六、证据支持的假设",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in interpretation["hypotheses"])
    lines.extend(
        [
            "",
            "---",
            "## 七、局限性",
            "",
            "1. 细胞类型信号基于 marker overlap，不等同于细胞比例反卷积。",
            "2. DEG 结果反映相关性，不能直接支持因果推断。",
            "3. Bulk 组织结果可能受到细胞组成变化影响。",
            "4. 规则引擎生成的解释仍需专业人员复核。",
            "",
            "*仅用于科研与教学展示。*",
        ]
    )
    return "\n".join(lines)


def render_report(
    filter_result,
    match_result,
    enrichment_result,
    input_file="",
    output_path=None,
    language="zh",
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if language == "en":
        report = _render_english(
            filter_result, match_result, enrichment_result, input_file, now
        )
    else:
        report = _render_chinese(
            filter_result, match_result, enrichment_result, input_file, now
        )

    if output_path is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"NeuroDEG_report_{timestamp}.md")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"[interpreter] 报告已保存: {output_path}")
    return report
