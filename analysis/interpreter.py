"""interpreter.py — 结果解读与报告生成模块"""

import datetime
import os


def generate_interpretations(filter_result, match_result, enrichment_result):
    """
    综合分析结果，生成解读文本

    Parameters
    ----------
    filter_result : dict
        筛选结果
    match_result : dict
        神经细胞匹配结果
    enrichment_result : dict
        富集结果，含 "go", "local", "api" 三个 key
    """
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    go_results = enrichment_result.get("go", [])
    local_results = enrichment_result.get("local", [])
    api_results = enrichment_result.get("api")

    conclusion_parts = []
    hypotheses = []

    # 1. 整体概况
    conclusion_parts.append(
        f"共检测到 {summary['significant']} 个显著差异表达基因，"
        f"其中 {summary['up']} 个上调，{summary['down']} 个下调。"
    )

    # 2. 神经细胞类型
    if cell_types:
        top = cell_types[:3]
        conclusion_parts.append(
            f"主要影响 {'、'.join(t['type'] for t in top)} "
            f"等 {len(cell_types)} 种细胞类型。"
        )
        for ct in cell_types[:3]:
            direction = "上调为主" if ct["up_count"] > ct["down_count"] else "下调为主"
            genes = ct["up_genes"] if ct["up_count"] > ct["down_count"] else ct["down_genes"]
            hypotheses.append(
                f"{ct['type']}相关基因以{direction}（{genes}），"
                f"可能提示{ct['type']}功能改变。"
            )
    else:
        conclusion_parts.append("未检测到显著的神经细胞标记基因变化。")

    # 3. GO 富集分析
    if go_results:
        top = go_results[:5]
        conclusion_parts.append(
            f"GO 富集分析发现 {len(go_results)} 条神经相关通路显著富集"
            f"（超几何检验 + FDR 校正），其中 {', '.join(g['go_name'][:20] for g in top[:3])} 等。"
        )
        for g in top[:5]:
            p = g["adjusted_p_value"]
            genes = ", ".join(g["overlap_genes"][:5])
            hypotheses.append(
                f"{g['go_name']}（p_adj={p:.2e}，{g['ratio']} 基因重叠），"
                f"涉及 {genes} 等基因。"
            )

    # 4. 本地通路
    if local_results:
        pw_names = "、".join(p["pathway_name"] for p in local_results[:3])
        conclusion_parts.append(
            f"本地通路匹配显示 {pw_names} 等 {len(local_results)} 条通路受影响。"
        )

    # 5. 总体方向
    total_up, total_down = summary["up"], summary["down"]
    if total_up > total_down * 2:
        conclusion_parts.append("总体以上调为主，可能与激活/应激/炎症相关。")
    elif total_down > total_up * 2:
        conclusion_parts.append("总体以下调为主，可能与功能抑制/退化相关。")
    elif total_up > 0 and total_down > 0:
        conclusion_parts.append(
            f"上/下调比约 {total_up / max(total_down, 1):.1f}:1，提示双向调控。"
        )

    return {"summary": "".join(conclusion_parts), "hypotheses": hypotheses}


def render_report(filter_result, match_result, enrichment_result,
                  input_file="", output_path=None):
    """
    渲染完整的分析报告

    Parameters
    ----------
    filter_result : dict
    match_result : dict
    enrichment_result : dict
        含 "go", "local", "api" 三个 key
    input_file : str
    output_path : str
    """
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    go_results = enrichment_result.get("go", [])
    local_results = enrichment_result.get("local", [])
    interp = generate_interpretations(filter_result, match_result, enrichment_result)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# NeuroDEG 差异表达基因分析报告\n")
    lines.append(f"> 生成时间: {now}")
    lines.append(f"> 输入文件: {input_file}\n")
    lines.append("---\n")
    lines.append("## 一、数据概览\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|:----|:----|")
    lines.append(f"| 总基因数 | {summary['total_genes']} |")
    lines.append(f"| 显著差异基因 | {summary['significant']} |")
    lines.append(f"| 上调基因数 | {summary['up']} |")
    lines.append(f"| 下调基因数 | {summary['down']} |")
    lines.append(f"| 筛选阈值 | log2FC > {summary['fc_cutoff']}, padj < {summary['p_cutoff']} |\n")
    if summary["top_up"]:
        lines.append("**Top 10 上调基因:**")
        for g in summary["top_up"]:
            lines.append(f"- {g['gene']}: log2FC={g['log2fc']:.2f}, padj={g['padj']:.2e}")
    if summary["top_down"]:
        lines.append("\n**Top 10 下调基因:**")
        for g in summary["top_down"]:
            lines.append(f"- {g['gene']}: log2FC={g['log2fc']:.2f}, padj={g['padj']:.2e}")
    lines.append("")

    # 神经细胞类型
    lines.append("---\n## 二、神经细胞类型分析\n")
    if not cell_types:
        lines.append("未检测到显著的神经细胞标记基因变化。\n")
    else:
        for ct in cell_types:
            lines.append(f"### {ct['type']}\n")
            lines.append("| 指标 | 数值 |")
            lines.append("|:----|:----|")
            lines.append(f"| 匹配标记基因数 | {ct['matched']}/{ct['total_markers']} |")
            lines.append(f"| 上调标记基因 | {ct['up_genes'] or '无'} |")
            lines.append(f"| 下调标记基因 | {ct['down_genes'] or '无'} |\n")
            lines.append("**受影响的基因:**")
            for g in ct['affected_genes']:
                sym = "↑" if g['direction'] == 'up' else "↓"
                lines.append(f"- **{g['gene']}** ({g['function']}) — {sym}")
            lines.append(f"\n**功能关联:** {'、'.join(ct.get('key_functions', []))}")
            lines.append(f"\n**解读:**\n> {ct['interpretation']}\n")
            if ct['disease_hints']:
                lines.append(f"**疾病关联提示:** {ct['disease_hints']}")
            lines.append("")

    # GO 富集
    lines.append("---\n## 三、GO 神经通路富集分析\n")
    if go_results:
        lines.append(f"基于 GO 知识库的超几何检验 + FDR 校正，共发现 {len(go_results)} 条显著富集的神经相关通路：\n")
        lines.append("| GO ID | 通路名称 | 重叠 | P 值 | 校正 P 值 |")
        lines.append("|:------|:---------|:----:|:----:|:--------:|")
        for g in go_results[:20]:
            lines.append(
                f"| {g['go_id']} | {g['go_name'][:40]} | {g['ratio']} "
                f"| {g['p_value']:.2e} | {g['adjusted_p_value']:.2e} |"
            )
        lines.append("")
        lines.append("**详细基因重叠:**")
        for g in go_results[:10]:
            genes_str = ", ".join(g["overlap_genes"][:8])
            lines.append(f"- {g['go_name']}: {genes_str}")
        lines.append("")
    else:
        lines.append("未发现显著富集的 GO 神经通路。\n")

    # 本地通路
    lines.append("---\n## 四、本地通路匹配\n")
    if local_results:
        for pw in local_results[:10]:
            lines.append(f"### {pw['pathway_name']}\n")
            lines.append(f"- **关联细胞类型:** {', '.join(pw.get('associated_cell_types', []))}")
            lines.append(f"- **匹配基因 ({pw.get('overlap_ratio', '')}):** {pw.get('matched_genes', '')}")
            lines.append(f"- **生物学过程:** {pw.get('biological_process', '')}")
            lines.append(f"- **临床意义:** {pw.get('relevance', '')}\n")
    else:
        lines.append("未发现匹配的本地神经通路。\n")

    # 综合结论
    lines.append("---\n## 五、综合结论\n")
    lines.append(interp["summary"] + "\n")

    # 推测与假设
    lines.append("---\n## 六、推测与假设\n")
    for h in interp["hypotheses"]:
        lines.append(f"- {h}")
    lines.append("")

    # 局限性
    lines.append("---\n## 七、局限性\n")
    lines.append("1. GO 富集基于关键字过滤的神经相关 GO terms，非全库 GO 扫描")
    lines.append("2. DEG 结果仅为相关性分析，因果推断需进一步验证")
    lines.append("3. 单数据集分析可能受批次效应影响")
    lines.append("4. 报告解读基于规则引擎，仅供参考\n")
    lines.append("---\n*NeuroDEG — 神经细胞基因表达差异分析工具*\n")

    report = "\n".join(lines)

    if output_path is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"NeuroDEG_report_{ts}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[interpreter] 报告已保存: {output_path}")
    return report
