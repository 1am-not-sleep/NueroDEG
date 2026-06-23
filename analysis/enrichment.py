"""enrichment.py — 功能富集分析模块"""

import json
import os
import urllib.request
import urllib.parse
import time


# Enrichr API 基础URL
ENRICHR_ADD_URL = "https://maayanlab.cloud/Enrichr/enrich"
ENRICHR_GET_URL = "https://maayanlab.cloud/Enrichr/geneSetLibrary"
ENRICHR_RL2020 = "RNA-Seq_Disease_Association_and_Tissue_Signatures"


def enrichr_enrich(genes, gene_set_library="KEGG_2021_Human"):
    """
    调用Enrichr API进行富集分析
    
    Parameters
    ----------
    genes : list
        基因列表
    gene_set_library : str
        基因集库名称
        
    Returns
    -------
    dict or None
        富集结果，失败返回None
    """
    if len(genes) == 0:
        return None
    
    try:
        # Step 1: 提交基因列表
        payload = {
            "list": (None, "\\n".join(genes)),
            "description": (None, "NeuroDEG analysis")
        }
        data = urllib.parse.urlencode({"list": "\\n".join(genes)}).encode("utf-8")
        
        req = urllib.request.Request(
            f"{ENRICHR_ADD_URL}?list={urllib.parse.quote(chr(10).join(genes))}",
            method="POST"
        )
        
        # 简化API调用 - 用更直接的方式
        encoded_genes = urllib.parse.quote("\\n".join(genes))
        url = f"https://maayanlab.cloud/Enrichr/enrich?geneSetLib={gene_set_library}&list={encoded_genes}"
        
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        
        if gene_set_library not in result:
            return None
        
        enriched = result[gene_set_library]
        return [
            {
                "term": item[1],
                "p_value": item[2],
                "z_score": item[3],
                "combined_score": item[4],
                "overlapping_genes": item[5] if len(item) > 5 else "",
                "adjusted_p_value": item[6] if len(item) > 6 else item[2]
            }
            for item in enriched[:15]  # 取前15个
        ]
        
    except Exception as e:
        print(f"[enrichment] Enrichr API调用失败: {e}")
        return None


def local_pathway_enrichment(deg_genes, pathways_path=None):
    """
    基于本地通路知识库的富集分析
    
    Parameters
    ----------
    deg_genes : set
        差异基因集合
    pathways_path : str
        通路JSON文件路径
        
    Returns
    -------
    list
        匹配结果（按匹配基因数排序）
    """
    if pathways_path is None:
        pathways_path = os.path.join(os.path.dirname(__file__), "..", "core", "pathways.json")
    
    with open(pathways_path, "r", encoding="utf-8") as f:
        pw_data = json.load(f)
    
    deg_upper = {g.upper() for g in deg_genes}
    
    results = []
    for pw in pw_data["pathways"]:
        pw_genes_set = {g.upper() for g in pw["genes"]}
        overlap = deg_upper & pw_genes_set
        
        if len(overlap) > 0:
            results.append({
                "pathway_id": pw["id"],
                "pathway_name": pw["name"],
                "name_en": pw.get("name_en", ""),
                "kegg_id": pw.get("kegg_id", ""),
                "associated_cell_types": pw.get("associated_cell_types", []),
                "matched_genes": sorted(overlap),
                "matched_count": len(overlap),
                "pathway_size": len(pw_genes_set),
                "overlap_ratio": f"{len(overlap)}/{len(pw_genes_set)}",
                "biological_process": pw.get("biological_process", ""),
                "relevance": pw.get("relevance", ""),
                "p_value_estimate": None  # 本地分析无法计算精确p值
            })
    
    results.sort(key=lambda x: x["matched_count"], reverse=True)
    return results


def run_enrichment(deg_genes, use_api=False):
    """
    统一入口：运行富集分析
    
    Parameters
    ----------
    deg_genes : list or set
        差异基因列表
    use_api : bool
        是否尝试在线Enrichr API
        
    Returns
    -------
    dict
        {"local": [...], "api": [...] or None}
    """
    if isinstance(deg_genes, set):
        deg_genes = list(deg_genes)
    
    result = {"local": [], "api": None}
    
    # 本地通路分析（始终执行）
    result["local"] = local_pathway_enrichment(set(deg_genes))
    
    if use_api:
        print("[enrichment] 正在调用Enrichr API进行在线富集分析...")
        api_result = enrichr_enrich(deg_genes)
        if api_result:
            print(f"[enrichment] API富集成功，获取到 {len(api_result)} 条通路")
            result["api"] = api_result
        else:
            print("[enrichment] API不可用，使用本地结果")
    
    return result
