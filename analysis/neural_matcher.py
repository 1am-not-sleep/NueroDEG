"""neural_matcher.py — 神经细胞类型匹配模块"""

import json
import os


def load_knowledge_base(kb_path=None):
    """加载神经细胞知识库"""
    if kb_path is None:
        kb_path = os.path.join(os.path.dirname(__file__), "..", "core", "knowledge_base.json")
    
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    
    # 构建基因→细胞类型反向索引
    gene_to_cell = {}
    for ct in kb["cell_types"]:
        for marker in ct["markers"]:
            gene = marker["gene"].upper()
            if gene not in gene_to_cell:
                gene_to_cell[gene] = []
            gene_to_cell[gene].append({
                "cell_type": ct["type"],
                "cell_type_en": ct["type_en"],
                "function": marker["function"],
                "category": marker.get("category", ""),
                "interpretation": ct["interpretation"],
                "disease_links": ct.get("disease_links", []),
                "key_functions": ct.get("key_functions", [])
            })
    
    return kb, gene_to_cell


def match_neural_types(deg_up, deg_down, kb=None, gene_to_cell=None):
    """
    将差异基因与神经细胞知识库进行匹配
    
    Parameters
    ----------
    deg_up : pd.DataFrame
        上调基因 (需有gene列)
    deg_down : pd.DataFrame
        下调基因 (需有gene列)
    kb : dict
        知识库 (如不传则自动加载)
    gene_to_cell : dict
        基因索引 (如不传则自动加载)
        
    Returns
    -------
    dict
        各细胞类型的匹配结果
    """
    if kb is None or gene_to_cell is None:
        kb, gene_to_cell = load_knowledge_base()
    
    # 提取基因列表（转为大写以匹配）
    up_genes = set(deg_up["gene"].str.upper().tolist()) if len(deg_up) > 0 else set()
    down_genes = set(deg_down["gene"].str.upper().tolist()) if len(deg_down) > 0 else set()
    
    results = []
    
    for ct in kb["cell_types"]:
        ct_name = ct["type"]
        markers = ct["markers"]
        total_markers = len(markers)
        
        # 匹配上调和下调的标记基因
        ct_up = []
        ct_down = []
        
        for marker in markers:
            gene = marker["gene"].upper()
            if gene in up_genes:
                ct_up.append(marker)
            elif gene in down_genes:
                ct_down.append(marker)
        
        matched = len(ct_up) + len(ct_down)
        
        if matched == 0:
            continue  # 跳过无匹配的细胞类型
        
        # 生成解读文本
        up_interpretation = ""
        down_interpretation = ""
        
        if len(ct_up) > 0:
            up_interpretation = ct["interpretation"]["up"]
        if len(ct_down) > 0:
            down_interpretation = ct["interpretation"]["down"]
        
        combined_interpretation_parts = []
        if up_interpretation:
            combined_interpretation_parts.append(f"上调提示: {up_interpretation}")
        if down_interpretation:
            combined_interpretation_parts.append(f"下调提示: {down_interpretation}")
        combined_interpretation = "; ".join(combined_interpretation_parts)
        
        # 整理受影响基因信息
        affected_genes = []
        for m in ct_up:
            affected_genes.append({
                "gene": m["gene"],
                "function": m["function"],
                "direction": "up"
            })
        for m in ct_down:
            affected_genes.append({
                "gene": m["gene"],
                "function": m["function"],
                "direction": "down"
            })
        
        # 判断主要变化方向
        if len(ct_up) > len(ct_down):
            main_direction = "上调为主"
        elif len(ct_down) > len(ct_up):
            main_direction = "下调为主"
        else:
            main_direction = "混合变化"
        
        # 疾病关联提示
        disease_hints = ct.get("disease_links", [])
        
        result = {
            "type": ct_name,
            "type_en": ct.get("type_en", ""),
            "matched": matched,
            "total_markers": total_markers,
            "up_count": len(ct_up),
            "down_count": len(ct_down),
            "main_direction": main_direction,
            "affected_genes": affected_genes,
            "up_genes": ", ".join([m["gene"] for m in ct_up]),
            "down_genes": ", ".join([m["gene"] for m in ct_down]),
            "interpretation": combined_interpretation,
            "disease_hints": "、".join(disease_hints) if disease_hints else "",
            "key_functions": ct.get("key_functions", [])
        }
        
        results.append(result)
    
    # 按匹配数量排序
    results.sort(key=lambda x: x["matched"], reverse=True)
    
    print(f"[neural_matcher] 匹配到 {len(results)} 种神经细胞类型:")
    for r in results:
        print(f"  ├─ {r['type']}: {r['matched']}/{r['total_markers']} 标记基因 ({r['up_count']}↑ {r['down_count']}↓)")
    
    return {
        "results": results,
        "total_matched_types": len(results)
    }


def match_pathways(deg_genes, pathways_path=None):
    """
    将差异基因与通路知识库匹配
    
    Parameters
    ----------
    deg_genes : set
        显著差异基因集合
    pathways_path : str
        通路文件路径
        
    Returns
    -------
    list
        匹配的通路列表
    """
    if pathways_path is None:
        pathways_path = os.path.join(os.path.dirname(__file__), "..", "core", "pathways.json")
    
    with open(pathways_path, "r", encoding="utf-8") as f:
        pw_data = json.load(f)
    
    deg_upper = {g.upper() for g in deg_genes}
    
    results = []
    for pw in pw_data["pathways"]:
        pw_genes_upper = {g.upper() for g in pw["genes"]}
        matched_genes = deg_upper & pw_genes_upper
        
        if len(matched_genes) > 0:
            results.append({
                "name": pw["name"],
                "name_en": pw.get("name_en", ""),
                "kegg_id": pw.get("kegg_id", ""),
                "cell_types": pw.get("associated_cell_types", []),
                "matched_genes": ", ".join(sorted(matched_genes)),
                "matched_count": len(matched_genes),
                "total_genes": len(pw["genes"]),
                "ratio": f"{len(matched_genes)}/{len(pw['genes'])}",
                "biological_process": pw.get("biological_process", ""),
                "relevance": pw.get("relevance", "")
            })
    
    results.sort(key=lambda x: x["matched_count"], reverse=True)
    
    print(f"[neural_matcher] 通路匹配: {len(results)} 条通路被富集")
    for r in results[:5]:
        print(f"  ├─ {r['name']}: {r['ratio']}")
    
    return results
