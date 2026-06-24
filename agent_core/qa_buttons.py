"""qa_buttons.py — 结构化追问按钮模块"""

import json
import os

_CORE = os.path.join(os.path.dirname(__file__), "..", "core")


def _load_kb():
    with open(os.path.join(_CORE, "knowledge_base.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_drugs():
    path = os.path.join(_CORE, "drug_targets.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ====== 功能聚类关键词 ======
FUNCTION_CLUSTERS = [
    {
        "name": "神经炎症与免疫应答",
        "icon": "🔴",
        "keywords": [
            "inflammat", "immune", "cytokine", "microglia", "astrocyte activation",
            "gliosis", "toll-like", "nf-kb", "chemokine", "complement",
            "炎症", "免疫", "细胞因子"
        ],
    },
    {
        "name": "突触传递与可塑性",
        "icon": "🟢",
        "keywords": [
            "synapse", "synaptic", "neurotransmitter", "glutamate", "gaba",
            "dopamine", "serotonin", "acetylcholine", "long-term potentiation",
            "long-term depression", "synaptic vesicle", "postsynaptic",
            "突触", "递质", "可塑性"
        ],
    },
    {
        "name": "髓鞘形成与轴突功能",
        "icon": "🟡",
        "keywords": [
            "myelin", "myelination", "oligodendrocyte", "axon", "axonal",
            "node of ranvier", "compact myelin",
            "髓鞘", "轴突"
        ],
    },
    {
        "name": "神经发生与细胞分化",
        "icon": "🔵",
        "keywords": [
            "neurogenesis", "neuron differentiation", "neuron development",
            "neuron migration", "neural crest", "neural tube",
            "neuroblast", "radial glia",
            "神经发生", "分化", "发育"
        ],
    },
    {
        "name": "细胞存活与应激响应",
        "icon": "🟣",
        "keywords": [
            "apoptosis", "autophagy", "oxidative stress", "neurotrophin",
            "cell death", "protein folding", "unfolded protein",
            "自噬", "凋亡", "氧化应激", "神经营养"
        ],
    },
    {
        "name": "离子通道与电活动",
        "icon": "⚡",
        "keywords": [
            "ion channel", "voltage-gated", "potassium channel", "sodium channel",
            "calcium channel", "action potential", "membrane potential",
            "离子通道", "动作电位"
        ],
    },
    {
        "name": "其他神经功能",
        "icon": "⚪",
        "keywords": [
            "learning", "memory", "cognition", "behavior", "circadian",
            "sensory", "locomotory",
            "学习", "记忆", "认知", "行为"
        ],
    },
]


# ====== Button 1: 通路功能解读 ======
def _pathway_insights_en(go_results, match_result, local_results=None):
    lines = ["## Pathway interpretation", ""]
    if not go_results:
        return "\n".join(lines + ["No significant GO term was available for interpretation."])

    lines.append(
        f"The current run contains {len(go_results)} GO results. "
        "The strongest terms and overlapping genes are:"
    )
    for result in go_results[:10]:
        fdr = result.get("adjusted_p_value", result.get("p_value", 1))
        genes = ", ".join(result.get("overlap_genes", [])[:8])
        lines.append(f"- **{result['go_name']}** (FDR={fdr:.2e}): {genes}")

    cell_types = match_result.get("results", [])
    if cell_types:
        labels = ", ".join(
            item.get("type_en", item["type"]) for item in cell_types[:5]
        )
        lines.extend(
            [
                "",
                f"Matched cell-type signals include {labels}. "
                "These associations may reflect cell-state changes or shifts in cellular composition.",
            ]
        )
    lines.extend(
        [
            "",
            "These results are hypothesis-generating and should be reviewed with the study design, "
            "brain region, and independent experimental evidence.",
        ]
    )
    return "\n".join(lines)


def pathway_insights(go_results, match_result, local_results=None, language="zh"):
    """
    将富集通路按功能聚类，给出病理机制解读

    Parameters
    ----------
    go_results : list
        GO 富集结果（含 p_value, adjusted_p_value, go_name, overlap_genes）
    match_result : dict
        细胞类型匹配结果
    local_results : list, optional
        本地通路匹配结果

    Returns
    -------
    str
        格式化后的通路功能解读 Markdown
    """
    if language == "en":
        return _pathway_insights_en(go_results, match_result, local_results)

    lines = []
    lines.append("## 🧬 通路功能解读与潜在病理机制\n")
    lines.append("基于显著富集的 GO 通路，按功能模块聚类分析：\n")

    if not go_results:
        lines.append("_未检测到显著富集的 GO 通路。_\n")
        return "\n".join(lines)

    # Cluster GO results
    clustered = {c["name"]: [] for c in FUNCTION_CLUSTERS}
    other = []

    for g in go_results:
        name = g.get("go_name", "").lower()
        matched = False
        for cluster in FUNCTION_CLUSTERS:
            for kw in cluster["keywords"]:
                if kw in name:
                    clustered[cluster["name"]].append(g)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            other.append(g)

    # Build cell type lookup
    ct_lookup = {}
    for ct in match_result.get("results", []):
        ct_lookup[ct["type"]] = ct

    # Display each cluster
    for cluster in FUNCTION_CLUSTERS:
        results = clustered[cluster["name"]]
        if not results:
            continue
        icon = cluster["icon"]

        # Sort by adjusted_p_value
        results.sort(key=lambda x: x.get("adjusted_p_value", 1))

        # Find best p-value
        best_p = results[0].get("adjusted_p_value", results[0].get("p_value", 1))
        if best_p < 0.001:
            sig_str = "高度显著"
        elif best_p < 0.05:
            sig_str = "显著"
        elif best_p < 0.1:
            sig_str = "边缘显著"
        else:
            sig_str = ""

        # Collect all overlapping genes
        all_genes = set()
        for r in results:
            all_genes.update(r.get("overlap_genes", []))
        genes_str = ", ".join(sorted(all_genes)[:12])

        lines.append(f"{icon} **{cluster['name']}** {f'({sig_str})' if sig_str else ''}")
        lines.append(f"  涉及 {len(results)} 条通路，{len(all_genes)} 个差异基因")
        lines.append(f"  基因: {genes_str}")
        lines.append("")

        # Top pathways
        for r in results[:5]:
            p = r.get("adjusted_p_value", r.get("p_value", 1))
            p_str = f"{p:.2e}" if p < 0.01 else f"{p:.3f}"
            genes_sub = ", ".join(r.get("overlap_genes", [])[:4])
            lines.append(f"  · {r['go_name'][:55]} (p={p_str})")
            lines.append(f"    基因: {genes_sub}")
            lines.append("")
        lines.append("")

        # Cross-reference with cell types
        related_cts = []
        for ct_name, ct_info in ct_lookup.items():
            deg_genes_lower = {g.upper() for g in all_genes}
            ct_genes_up = set(ct_info.get("up_genes", "").upper().split(", ")) if ct_info.get("up_genes") else set()
            ct_genes_down = set(ct_info.get("down_genes", "").upper().split(", ")) if ct_info.get("down_genes") else set()
            ct_genes_all = ct_genes_up | ct_genes_down
            ct_genes_all.discard("")
            if ct_genes_all & deg_genes_lower:
                related_cts.append(ct_name)

        if related_cts:
            dir_strs = []
            for ct_name in related_cts:
                ct = ct_lookup[ct_name]
                d = ct.get("main_direction", "变化")
                dir_strs.append(f"{ct_name}({d})")
            lines.append(f"  关联细胞: {'、'.join(dir_strs)}\n")

    # Other unclustered results
    if other:
        lines.append(f"⚪ **其他显著通路** ({len(other)} 条)")
        for r in other[:5]:
            p = r.get("adjusted_p_value", r.get("p_value", 1))
            p_str = f"{p:.2e}" if p < 0.01 else f"{p:.3f}"
            genes_sub = ", ".join(r.get("overlap_genes", [])[:4])
            lines.append(f"  · {r['go_name'][:55]} (p={p_str})")
            lines.append(f"    基因: {genes_sub}")
            lines.append("")
        lines.append("")

    # Pathogenesis summary
    lines.append("---\n**潜在病理机制推测:**")
    pathogenesis_notes = []
    for cluster in FUNCTION_CLUSTERS:
        results = clustered[cluster["name"]]
        if not results:
            continue
        best_p = min(r.get("adjusted_p_value", r.get("p_value", 1)) for r in results)
        if best_p >= 0.1:
            continue
        name = cluster["name"]
        if name == "神经炎症与免疫应答":
            pathogenesis_notes.append(
                f"- 神经炎症通路显著激活，提示存在免疫-神经互作异常，"
                f"可能驱动神经毒性微环境"
            )
        elif name == "突触传递与可塑性":
            pathogenesis_notes.append(
                f"- 突触功能相关基因表达改变，提示兴奋/抑制(E/I)平衡失调，"
                f"可能影响神经网络信息处理"
            )
        elif name == "髓鞘形成与轴突功能":
            pathogenesis_notes.append(
                f"- 髓鞘形成通路受损，轴突传导效率可能下降，"
                f"影响神经信号快速传递"
            )
        elif name == "神经发生与细胞分化":
            pathogenesis_notes.append(
                f"- 神经发生活动改变，可能反映组织修复/代偿响应或再生能力受损"
            )
        elif name == "细胞存活与应激响应":
            pathogenesis_notes.append(
                f"- 细胞应激/存活通路异常，可能涉及蛋白稳态失衡或氧化损伤，"
                f"与神经退行性过程相关"
            )
        elif name == "离子通道与电活动":
            pathogenesis_notes.append(
                f"- 离子通道功能改变，可能影响神经元兴奋性和放电模式"
            )

    if pathogenesis_notes:
        lines.extend(pathogenesis_notes)
    else:
        lines.append("- 基于当前分析，未形成明确的病理机制假设")

    lines.append("")
    return "\n".join(lines)


# ====== Button 2: 药物-靶点关联 ======
def drug_association(go_results, local_results=None, language="zh"):
    """
    基于富集通路返回潜在靶向药物

    Parameters
    ----------
    go_results : list
    local_results : list, optional

    Returns
    -------
    str
        格式化后的药物关联 Markdown
    """
    drugs = _load_drugs()
    lines = []
    lines.append(
        "## Potential drug-target associations\n"
        if language == "en"
        else "## 💊 潜在靶向药物关联\n"
    )

    if drugs is None:
        lines.append(
            "_The local drug-target database is unavailable._\n"
            if language == "en"
            else "_药物靶点数据库未加载（需要 core/drug_targets.json）_\n"
        )
        lines.append("您也可以自行查询以下在线资源：\n")
        lines.append("- [DrugBank](https://go.drugbank.com/)")
        lines.append("- [DGIdb](https://www.dgidb.org/)")
        return "\n".join(lines)

    # Extract pathway names for matching
    pathway_names = set()
    for r in go_results:
        pathway_names.add(r.get("go_name", "").lower())

    # Match drugs
    matched_drugs = []
    for drug in drugs.get("drugs", []):
        for target_pathway in drug.get("target_pathways", []):
            for pn in pathway_names:
                if target_pathway.lower() in pn or pn in target_pathway.lower():
                    matched_drugs.append(drug)
                    break
            else:
                continue
            break

    if not matched_drugs:
        lines.append(
            "No local drug entry directly matched the enriched pathways.\n"
            if language == "en"
            else "未在本地药物库中找到与当前通路明显匹配的药物。\n"
        )
        lines.append(
            "Reference entries from the local neural drug database:\n"
            if language == "en"
            else "以下为神经领域常用药物供参考：\n"
        )
        for drug in drugs.get("drugs", [])[:8]:
            lines.append(f"- **{drug['name']}**: {drug.get('mechanism', '')}")
        lines.append("")
        return "\n".join(lines)

    lines.append(
        f"Matched {len(matched_drugs)} local drug entries based on pathway keywords:\n"
        if language == "en"
        else f"根据富集通路，匹配到 {len(matched_drugs)} 种潜在相关药物：\n"
    )
    for drug in matched_drugs:
        lines.append(f"- **{drug['name']}**")
        lines.append(
            f"  - {'Mechanism' if language == 'en' else '机制'}: {drug.get('mechanism', '')}"
        )
        lines.append(
            f"  - {'Targets' if language == 'en' else '靶点'}: {', '.join(drug.get('targets', []))}"
        )
        lines.append(
            f"  - {'Database indication' if language == 'en' else '适用'}: {drug.get('indication', '')}"
        )
        lines.append("")

    lines.append(
        "---\n*Computational pathway matching only; this is not a medication recommendation.*"
        if language == "en"
        else "---\n⚠️ *以上仅为基于通路匹配的计算推测，不代表用药建议。*"
    )
    return "\n".join(lines)


# ====== Button 3: 分析摘要导出 ======
def analysis_summary(filter_result, match_result, enrichment_result, quality,
                     input_file="", fc_cutoff=1.0, p_cutoff=0.05, language="zh"):
    """
    生成可供复制分享的分析摘要

    Parameters
    ----------
    filter_result : dict
    match_result : dict
    enrichment_result : dict
    quality : dict
    input_file : str
    fc_cutoff : float
    p_cutoff : float

    Returns
    -------
    str
        格式化的分析摘要文本
    """
    s = filter_result["summary"]
    ct = match_result.get("results", [])
    go_res = enrichment_result.get("go", [])
    local_res = enrichment_result.get("local", [])

    lines = []
    if language == "en":
        lines.append("=" * 50)
        lines.append("NeuroDEG Analysis Summary")
        lines.append("=" * 50)
        lines.append(f"Input: {input_file or 'uploaded table'}")
        lines.append(f"Cutoffs: abs(log2FC) > {fc_cutoff}, adjusted p < {p_cutoff}")
        lines.append(f"Total genes: {s.get('total_genes', '?')}")
        lines.append(f"Significant genes: {s.get('significant', 0)}")
        lines.append(f"  Up: {s.get('up', 0)}")
        lines.append(f"  Down: {s.get('down', 0)}")
        lines.append("")
        lines.append(f"Matched cell types: {match_result.get('total_matched_types', 0)}")
        for cell_type in ct[:5]:
            lines.append(
                f"  - {cell_type.get('type_en', cell_type['type'])} "
                f"({cell_type.get('abbreviation', '')}): "
                f"{cell_type['matched']}/{cell_type['total_markers']} markers"
            )
        lines.append(f"GO results: {len(go_res)}")
        for result in go_res[:5]:
            lines.append(
                f"  - {result['go_name'][:45]}: "
                f"FDR={result.get('adjusted_p_value', 1):.2e}"
            )
        lines.append(f"Quality: {quality.get('grade', '?') if quality else '?'}")
        lines.append("=" * 50)
        return "\n".join(lines)

    lines.append("=" * 50)
    lines.append("NeuroDEG 分析摘要")
    lines.append("=" * 50)
    lines.append(f"样本: {input_file or '（自上传）'}")
    lines.append(f"筛选阈值: |log2FC| > {fc_cutoff}, padj < {p_cutoff}")
    lines.append(f"总基因数: {s.get('total_genes', '?')}")
    lines.append(f"显著差异基因: {s.get('significant', 0)} 个")
    lines.append(f"  ├─ 上调: {s.get('up', 0)}")
    lines.append(f"  └─ 下调: {s.get('down', 0)}")
    lines.append("")
    lines.append(f"神经细胞类型匹配: {match_result.get('total_matched_types', 0)} 种")
    for c in ct[:5]:
        lines.append(f"  · {c['type']}: {c['matched']}/{c['total_markers']} 标记 ({c['up_count']}↑ {c['down_count']}↓)")
    lines.append("")
    if go_res:
        lines.append(f"GO 通路富集: {len(go_res)} 条显著")
        for g in go_res[:5]:
            p = g.get("adjusted_p_value", g.get("p_value", 1))
            lines.append(f"  · {g['go_name'][:40]}: p_adj={p:.2e}")
    if local_res:
        for p in local_res[:3]:
            lines.append(f"  · {p['pathway_name']}: {p.get('overlap_ratio', '')}")
    lines.append("")
    if quality:
        lines.append(f"质量评估: {quality.get('grade', '?')}")
        if quality.get("reasons"):
            for r in quality["reasons"]:
                lines.append(f"  · {r}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("由 NeuroDEG Agent 自动生成")
    lines.append("=" * 50)
    return "\n".join(lines)
