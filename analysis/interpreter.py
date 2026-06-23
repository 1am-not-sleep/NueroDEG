"""interpreter.py — 结果解读与报告生成模块"""

import json
import os
import datetime
from string import Template


def generate_interpretations(filter_result, match_result, pathway_result):
    """
    综合分析结果，生成解读文本
    
    Parameters
    ----------
    filter_result : dict
        筛选结果
    match_result : dict
        神经细胞匹配结果
    pathway_result : list
        通路匹配结果
        
    Returns
    -------
    dict
        包含解读文本和报告的字典
    """
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    pathways = pathway_result
    
    # 构建综合结论
    conclusion_parts = []
    hypotheses = []
    
    # 1. 整体概况
    conclusion_parts.append(
        f"共检测到 {summary['significant']} 个显著差异表达基因，"
        f"其中 {summary['up']} 个上调，{summary['down']} 个下调。"
    )
    
    # 2. 神经细胞类型分析
    if cell_types:
        top_types = cell_types[:3]
        type_names = "、".join([t["type"] for t in top_types])
        conclusion_parts.append(
            f"在神经细胞层面，主要影响 {type_names} "
            f"等 {len(cell_types)} 种细胞类型的基因表达。"
        )
        
        # 生成假设
        for ct in cell_types[:3]:
            if ct["up_count"] > ct["down_count"]:
                hypotheses.append(
                    f"{ct['type']}相关基因以上调为主（{ct['up_genes']}），"
                    f"可能提示{ct['type']}活性增强，"
                    f"可能与{ct.get('disease_hints', '神经功能调节')}相关。"
                )
            elif ct["down_count"] > ct["up_count"]:
                hypotheses.append(
                    f"{ct['type']}相关基因以下调为主（{ct['down_genes']}），"
                    f"可能提示{ct['type']}功能受损或数量减少，"
                    f"需结合{ct.get('disease_hints', '相关疾病')}背景考虑。"
                )
    else:
        conclusion_parts.append("未检测到显著的神经细胞类型特异性表达变化。")
    
    # 3. 通路分析
    if pathways:
        top_pathways = pathways[:3]
        pw_names = "、".join([p["pathway_name"] for p in top_pathways])
        conclusion_parts.append(
            f"通路分析显示，{pw_names} 等 {len(pathways)} 条神经相关通路受到显著影响。"
        )
        
        for pw in top_pathways:
            if "上调" in pw.get("relevance", "") or "增强" in pw.get("relevance", ""):
                direction = "上调"
            elif "受损" in pw.get("relevance", "") or "减弱" in pw.get("relevance", ""):
                direction = "下调"
            else:
                direction = "改变"
            hypotheses.append(
                f"{pw['pathway_name']}中 {pw['matched_genes']} 等基因表达{direction}，"
                f"可能影响{pw.get('biological_process', '相关生物学过程')[:30]}。"
            )
    else:
        conclusion_parts.append("未发现显著富集的神经相关通路。")
    
    # 4. 总体判断
    total_up = summary["up"]
    total_down = summary["down"]
    if total_up > total_down * 2:
        conclusion_parts.append("总体以上调信号为主，可能与细胞激活、应激或炎症反应相关。")
    elif total_down > total_up * 2:
        conclusion_parts.append("总体以下调信号为主，可能与细胞功能抑制或退化过程相关。")
    elif total_up > 0 and total_down > 0:
        ratio = total_up / max(total_down, 1)
        conclusion_parts.append(
            f"上/下调比例约为 {ratio:.1f}:1，"
            f"提示存在双向调控，可能反映复杂的细胞响应机制。"
        )
    
    # 5. 如果没匹配到神经细胞
    if not cell_types:
        hypotheses.append(
            "当前差异基因中未检测到显著的神经细胞标记基因变化，"
            "可能原因：样本非神经组织、知识库覆盖不足、或阈值过于严格。"
        )
    
    return {
        "summary": "".join(conclusion_parts),
        "hypotheses": hypotheses
    }


def load_template(template_path=None):
    """加载报告模板"""
    if template_path is None:
        template_path = os.path.join(
            os.path.dirname(__file__), "..", "core", "templates", "report_template.md"
        )
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def render_report(
    filter_result, match_result, pathway_result,
    input_file="", output_path=None, template_path=None
):
    """
    渲染完整的分析报告
    
    Parameters
    ----------
    filter_result : dict
        筛选结果
    match_result : dict
        匹配结果
    pathway_result : list
        通路分析结果
    input_file : str
        输入文件名
    output_path : str
        输出路径（默认output/目录）
    template_path : str
        模板路径
        
    Returns
    -------
    str
        渲染后的报告文本
    """
    summary = filter_result["summary"]
    cell_types = match_result.get("results", [])
    pathways = pathway_result
    
    # 生成解读
    interpretations = generate_interpretations(
        filter_result, match_result, pathway_result
    )
    
    # 构建报告内容（简单的字符串模板，可扩展为jinja2）
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report_parts = []
    report_parts.append(f"# NeuroDEG 差异表达基因分析报告\n")
    report_parts.append(f"\n> 生成时间: {now}")
    report_parts.append(f"> 输入文件: {input_file}\n")
    
    # 一、数据概览
    report_parts.append("---\n")
    report_parts.append("## 一、数据概览\n")
    report_parts.append(f"| 指标 | 数值 |")
    report_parts.append(f"|:----|:----|")
    report_parts.append(f"| 总基因数 | {summary['total_genes']} |")
    report_parts.append(f"| 显著差异基因 | {summary['significant']} |")
    report_parts.append(f"| 上调基因数 | {summary['up']} |")
    report_parts.append(f"| 下调基因数 | {summary['down']} |")
    report_parts.append(f"| 筛选阈值 | log2FC > {summary['fc_cutoff']}, padj < {summary['p_cutoff']} |")
    report_parts.append("")
    
    # Top 差异基因
    if summary["top_up"]:
        report_parts.append("**Top 10 上调基因:**")
        for g in summary["top_up"]:
            report_parts.append(f"- {g['gene']}: log2FC = {g['log2fc']:.2f}, padj = {g['padj']:.2e}")
    if summary["top_down"]:
        report_parts.append("\n**Top 10 下调基因:**")
        for g in summary["top_down"]:
            report_parts.append(f"- {g['gene']}: log2FC = {g['log2fc']:.2f}, padj = {g['padj']:.2e}")
    report_parts.append("")
    
    # 二、神经细胞类型分析
    report_parts.append("---\n")
    report_parts.append("## 二、神经细胞类型分析\n")
    
    if not cell_types:
        report_parts.append("未检测到显著的神经细胞标记基因变化。\n")
    else:
        for ct in cell_types:
            report_parts.append(f"### {ct['type']}\n")
            report_parts.append(f"| 指标 | 数值 |")
            report_parts.append(f"|:----|:----|")
            report_parts.append(f"| 匹配标记基因数 | {ct['matched']} / {ct['total_markers']} |")
            report_parts.append(f"| 上调标记基因 | {ct['up_genes'] or '无'} |")
            report_parts.append(f"| 下调标记基因 | {ct['down_genes'] or '无'} |")
            report_parts.append(f"| 主要变化方向 | {ct['main_direction']} |")
            report_parts.append("")
            
            report_parts.append("**受影响的基因:**")
            if ct['affected_genes']:
                for g in ct['affected_genes']:
                    direction_symbol = "↑" if g['direction'] == 'up' else "↓"
                    report_parts.append(f"- **{g['gene']}** ({g['function']}) — {direction_symbol}")
            else:
                report_parts.append("- (无)")
            report_parts.append("")
            
            report_parts.append("**功能关联:** " + "、".join(ct.get("key_functions", [])))
            report_parts.append("")
            
            report_parts.append("**解读:**")
            report_parts.append(f"> {ct['interpretation']}\n")
            
            if ct['disease_hints']:
                report_parts.append(f"**疾病关联提示:** {ct['disease_hints']}")
            report_parts.append("")
    
    # 三、通路富集分析
    report_parts.append("---\n")
    report_parts.append("## 三、通路富集分析\n")
    
    if not pathways:
        report_parts.append("未发现显著富集的神经相关通路。\n")
    else:
        for pw in pathways:
            report_parts.append(f"### {pw['pathway_name']}\n")
            report_parts.append(f"- **关联细胞类型:** {', '.join(pw.get('associated_cell_types', []))}")
            report_parts.append(f"- **匹配差异基因 ({pw.get('overlap_ratio', pw.get('matched_count', 0))}):** {pw.get('matched_genes', '')}")
            report_parts.append(f"- **生物学过程:** {pw.get('biological_process', '')}")
            report_parts.append(f"- **临床意义:** {pw.get('relevance', '')}")
            report_parts.append("")
    
    # 四、综合结论
    report_parts.append("---\n")
    report_parts.append("## 四、综合结论\n")
    report_parts.append(interpretations["summary"] + "\n")
    
    # 五、推测与假设
    report_parts.append("---\n")
    report_parts.append("## 五、推测与假设\n")
    if interpretations["hypotheses"]:
        for h in interpretations["hypotheses"]:
            report_parts.append(f"- {h}")
    else:
        report_parts.append("- 基于当前数据暂无明确推测")
    report_parts.append("")
    
    # 六、局限性
    report_parts.append("---\n")
    report_parts.append("## 六、局限性\n")
    report_parts.append("1. 本分析基于内置神经细胞知识库，受知识库覆盖范围限制")
    report_parts.append("2. DEG结果仅为相关性分析，因果推断需进一步验证")
    report_parts.append("3. 单数据集分析可能受批次效应影响")
    report_parts.append("4. 报告解读基于规则引擎，仅供参考\n")
    
    report_parts.append("---\n")
    report_parts.append("*NeuroDEG — 神经细胞基因表达差异分析工具*\n")
    
    report_text = "\n".join(report_parts)
    
    # 保存报告
    if output_path is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"NeuroDEG_report_{timestamp}.md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(f"[interpreter] 报告已保存至: {output_path}")
    
    return report_text
