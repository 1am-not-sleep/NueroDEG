"""neural_matcher.py — 神经细胞类型匹配模块"""

import json
import os


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


def match_neural_types(deg_up, deg_down, kb=None, gene_to_cell=None):
    if kb is None or gene_to_cell is None:
        kb, gene_to_cell = load_knowledge_base()

    up_genes = set(deg_up["gene"].str.upper().tolist()) if len(deg_up) > 0 else set()
    down_genes = set(deg_down["gene"].str.upper().tolist()) if len(deg_down) > 0 else set()

    results = []
    for ct in kb["cell_types"]:
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
            "type_en": ct.get("type_en", ""),
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
            "key_functions": ct.get("key_functions", [])
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
