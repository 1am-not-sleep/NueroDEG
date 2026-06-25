"""neural_matcher.py — 神经细胞类型匹配模块"""

import json
import os
from collections import defaultdict

from agent_core.cell_types import normalize_cell_type


def load_knowledge_base(kb_path=None):
    if kb_path is None:
        kb_path = os.path.join(os.path.dirname(__file__), "..", "core", "knowledge_base.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = json.load(f)

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


def load_panglaodb(panglao_path=None):
    """加载 PanglaoDB 补充标记基因库"""
    if panglao_path is None:
        panglao_path = os.path.join(os.path.dirname(__file__), "..", "core", "panglaodb_supplement.json")
    if not os.path.exists(panglao_path):
        print("[neural_matcher] PanglaoDB 补充库不存在，跳过")
        return {}, {}
    with open(panglao_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cell_type_map = {}
    gene_to_cell = defaultdict(list)
    for ct_name, info in data.get("cell_types", {}).items():
        cell_type_map[ct_name] = {
            "type": ct_name,
            "gene_count": info.get("gene_count", 0),
        }
        for gene in info.get("genes", []):
            gene_to_cell[gene].append(ct_name)

    print(f"[neural_matcher] 加载 PanglaoDB: {len(cell_type_map)} 种细胞类型, {len(gene_to_cell)} 个基因")
    return dict(cell_type_map), dict(gene_to_cell)


def match_panglao_types(deg_up, deg_down, cell_type_map, gene_to_cell):
    """使用 PanglaoDB 进行细胞类型匹配"""
    up_genes = set(deg_up["gene"].str.upper().tolist()) if len(deg_up) > 0 else set()
    down_genes = set(deg_down["gene"].str.upper().tolist()) if len(deg_down) > 0 else set()
    all_deg = up_genes | down_genes

    results = []
    for ct_name, info in cell_type_map.items():
        ct_genes = set(gene_to_cell.keys())  # We'll get specific genes below
        # Actually, we need the gene list from the supplement
        pass  # Will get genes from the supplement JSON

    return {"results": [], "total_matched_types": 0}

def match_neural_types(deg_up, deg_down, kb=None, gene_to_cell=None, use_panglaodb=True):
    """
    匹配神经细胞类型（curated KB + 可选 PanglaoDB 补充）

    Parameters
    ----------
    deg_up : pd.DataFrame
    deg_down : pd.DataFrame
    kb : dict
    gene_to_cell : dict
    use_panglaodb : bool
        是否启用 PanglaoDB 补充匹配
    """
    if kb is None or gene_to_cell is None:
        kb, gene_to_cell = load_knowledge_base()

    up_genes = set(deg_up["gene"].str.upper().tolist()) if len(deg_up) > 0 else set()
    down_genes = set(deg_down["gene"].str.upper().tolist()) if len(deg_down) > 0 else set()

    results = []
    for ct in kb["cell_types"]:
        labels = normalize_cell_type(ct["type"], ct.get("type_en", ""))
        ct_up, ct_down = [], []
        for marker in ct["markers"]:
            g = marker["gene"].upper()
            if g in up_genes:
                ct_up.append(marker)
            elif g in down_genes:
                ct_down.append(marker)

        matched = len(ct_up) + len(ct_down)
        if matched == 0:
            continue

        parts = []
        if ct_up:
            parts.append(f"上调提示: {ct['interpretation']['up']}")
        if ct_down:
            parts.append(f"下调提示: {ct['interpretation']['down']}")

        affected = [{"gene": m["gene"], "function": m["function"], "direction": "up"} for m in ct_up]
        affected += [{"gene": m["gene"], "function": m["function"], "direction": "down"} for m in ct_down]

        results.append({
            "type": ct["type"],
            **labels,
            "matched": matched,
            "total_markers": len(ct["markers"]),
            "up_count": len(ct_up),
            "down_count": len(ct_down),
            "main_direction": "上调为主" if len(ct_up) > len(ct_down) else ("下调为主" if len(ct_down) > len(ct_up) else "混合变化"),
            "affected_genes": affected,
            "up_genes": ", ".join(m["gene"] for m in ct_up),
            "down_genes": ", ".join(m["gene"] for m in ct_down),
            "interpretation": "; ".join(parts),
            "disease_hints": "、".join(ct.get("disease_links", [])),
            "key_functions": ct.get("key_functions", []),
            "source": "Curated Knowledge Base"
        })

    # PanglaoDB 补充匹配
    if use_panglaodb:
        ct_map, g2c = load_panglaodb()
        if ct_map:
            # Load supplement to get actual gene lists
            supp_path = os.path.join(os.path.dirname(__file__), "..", "core", "panglaodb_supplement.json")
            if os.path.exists(supp_path):
                with open(supp_path, "r", encoding="utf-8") as f:
                    supp = json.load(f)
                for ct_name, info in supp.get("cell_types", {}).items():
                    labels = normalize_cell_type(ct_name)
                    genes = set(g.upper() for g in info["genes"])
                    up_matched = up_genes & genes
                    down_matched = down_genes & genes
                    total_matched = len(up_matched) + len(down_matched)
                    if total_matched < 2:  # Require at least 2 matches for PanglaoDB
                        continue
                    # Deduplicate bilingual/synonym labels against curated results.
                    existing_types = {
                        r.get("type_en", r["type"]).lower()
                        for r in results
                    }
                    if labels["type_en"].lower() in existing_types:
                        continue

                    affected = [{"gene": g, "function": "PanglaoDB marker", "direction": "up"} for g in sorted(up_matched)]
                    affected += [{"gene": g, "function": "PanglaoDB marker", "direction": "down"} for g in sorted(down_matched)]

                    results.append({
                        "type": ct_name,
                        **labels,
                        "matched": total_matched,
                        "total_markers": info["gene_count"],
                        "up_count": len(up_matched),
                        "down_count": len(down_matched),
                        "main_direction": "上调为主" if len(up_matched) > len(down_matched) else ("下调为主" if len(down_matched) > len(up_matched) else "混合变化"),
                        "affected_genes": affected,
                        "up_genes": ", ".join(sorted(up_matched)[:8]),
                        "down_genes": ", ".join(sorted(down_matched)[:8]),
                        "interpretation": f"PanglaoDB 单细胞数据库匹配: {ct_name} 相关基因表达改变",
                        "disease_hints": "",
                        "key_functions": [],
                        "source": "PanglaoDB"
                    })

    results.sort(key=lambda x: x["matched"], reverse=True)
    print(f"[neural_matcher] 匹配到 {len(results)} 种细胞类型")
    return {"results": results, "total_matched_types": len(results)}


def match_pathways(deg_genes, pathways_path=None):
    if pathways_path is None:
        pathways_path = os.path.join(os.path.dirname(__file__), "..", "core", "pathways.json")
    with open(pathways_path, "r", encoding="utf-8") as f:
        pw_data = json.load(f)

    deg_upper = {g.upper() for g in deg_genes}
    results = []
    for pw in pw_data["pathways"]:
        pw_genes = {g.upper() for g in pw["genes"]}
        overlap = deg_upper & pw_genes
        if overlap:
            results.append({
                "name": pw["name"],
                "name_en": pw.get("name_en", ""),
                "kegg_id": pw.get("kegg_id", ""),
                "cell_types": pw.get("associated_cell_types", []),
                "matched_genes": ", ".join(sorted(overlap)),
                "matched_count": len(overlap),
                "total_genes": len(pw["genes"]),
                "ratio": f"{len(overlap)}/{len(pw['genes'])}",
                "biological_process": pw.get("biological_process", ""),
                "relevance": pw.get("relevance", "")
            })
    results.sort(key=lambda x: x["matched_count"], reverse=True)
    print(f"[neural_matcher] 通路匹配: {len(results)} 条")
    return results
