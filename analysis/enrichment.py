"""enrichment.py — 功能富集分析模块（GO + 本地通路 + Enrichr API）"""

import json
import os
import math
import urllib.request
import urllib.parse

# ====== Core paths ======
_CORE = os.path.join(os.path.dirname(__file__), "..", "core")
_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
_CACHE_PATH = os.path.join(_CORE, "go_enrichment_cache.json")


# ====== GO 富集缓存加载 ======
def _load_go_cache():
    """加载预计算的 GO 神经通路缓存"""
    if not os.path.exists(_CACHE_PATH):
        return None, None
    with open(_CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
    return cache.get("go_terms", {}), cache.get("go_genes", {})


# ====== 超几何检验 ======
def _log_comb(n, k):
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hypergeom_sf(k, N, K, n):
    """P(X >= k) 超几何分布生存函数"""
    if k <= 0:
        return 1.0
    max_i = min(n, K)
    log_probs = []
    for i in range(k, max_i + 1):
        lp = _log_comb(K, i) + _log_comb(N - K, n - i) - _log_comb(N, n)
        log_probs.append(lp)
    if not log_probs:
        return 0.0
    max_lp = max(log_probs)
    total = sum(math.exp(lp - max_lp) for lp in log_probs)
    return math.exp(max_lp + math.log(total))


_BACKGROUND = 38822  # 人类基因总数（来自 GAF 注释）


# ====== GO 富集分析 ======
def run_go_enrichment(deg_genes):
    """
    基于 GO 神经通路缓存的超几何检验 + FDR 校正

    Parameters
    ----------
    deg_genes : list
        差异基因列表

    Returns
    -------
    list
        富集结果（按 adjusted_p_value 排序）
    """
    neuro_terms, go_genes = _load_go_cache()
    if neuro_terms is None or go_genes is None:
        print("[enrichment] GO 缓存不存在，跳过 GO 富集")
        return []

    deg_set = {g.upper() for g in deg_genes}
    n = len(deg_set)
    results = []

    for go_id, term in neuro_terms.items():
        if go_id not in go_genes:
            continue
        gene_list = go_genes[go_id]
        M = len(gene_list)
        if M < 3:
            continue
        overlap = deg_set & set(gene_list)
        k = len(overlap)
        if k < 2:
            continue
        pval = _hypergeom_sf(k, _BACKGROUND, M, n)
        if pval < 0.5:
            results.append({
                "go_id": go_id,
                "go_name": term["name"],
                "namespace": term.get("namespace", ""),
                "overlap_genes": sorted(overlap),
                "overlap_count": k,
                "pathway_size": M,
                "ratio": f"{k}/{M}",
                "p_value": min(pval, 1.0),
                "adjusted_p_value": None,
            })

    if not results:
        print("[enrichment] GO 富集未找到显著结果")
        return []

    # Benjamini-Hochberg FDR
    results.sort(key=lambda x: x["p_value"])
    n_tests = len(results)
    for i, r in enumerate(results):
        r["adjusted_p_value"] = min(r["p_value"] * n_tests / (i + 1), 1.0)
    results.sort(key=lambda x: x["adjusted_p_value"])

    # 返回显著的，或至少 top 30
    sig = [r for r in results if r["adjusted_p_value"] < 0.1]
    if len(sig) >= 5:
        print(f"[enrichment] GO 富集: {len(sig)} 条显著通路")
        return sig
    print(f"[enrichment] GO 富集: 返回 top {min(30, len(results))} 条")
    return results[: min(30, len(results))]


# ====== Enrichr API ======
def enrichr_enrich(genes, gene_set_library="KEGG_2021_Human"):
    """调用 Enrichr API 进行在线富集分析"""
    if len(genes) == 0:
        return None
    try:
        encoded = urllib.parse.quote("\n".join(genes))
        url = f"https://maayanlab.cloud/Enrichr/enrich?geneSetLib={gene_set_library}&list={encoded}"
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
                "adjusted_p_value": item[6] if len(item) > 6 else item[2],
            }
            for item in enriched[:15]
        ]
    except Exception as e:
        print(f"[enrichment] Enrichr API 失败: {e}")
        return None


# ====== 本地通路匹配 ======
def local_pathway_enrichment(deg_genes, pathways_path=None):
    """基于本地 pathways.json 的 overlap 匹配"""
    if pathways_path is None:
        pathways_path = os.path.join(_CORE, "pathways.json")
    with open(pathways_path, "r", encoding="utf-8") as f:
        pw_data = json.load(f)

    deg_upper = {g.upper() for g in deg_genes}
    results = []
    for pw in pw_data["pathways"]:
        pw_set = {g.upper() for g in pw["genes"]}
        overlap = deg_upper & pw_set
        if overlap:
            results.append({
                "pathway_id": pw["id"],
                "pathway_name": pw["name"],
                "name_en": pw.get("name_en", ""),
                "kegg_id": pw.get("kegg_id", ""),
                "associated_cell_types": pw.get("associated_cell_types", []),
                "matched_genes": sorted(overlap),
                "matched_count": len(overlap),
                "pathway_size": len(pw_set),
                "overlap_ratio": f"{len(overlap)}/{len(pw_set)}",
                "biological_process": pw.get("biological_process", ""),
                "relevance": pw.get("relevance", ""),
            })
    results.sort(key=lambda x: x["matched_count"], reverse=True)
    return results


# ====== 统一入口 ======
def run_enrichment(deg_genes, use_api=False):
    """
    统一入口：运行富集分析（GO + 本地 + 可选 API）

    Parameters
    ----------
    deg_genes : list or set
        差异基因列表
    use_api : bool
        是否尝试 Enrichr API

    Returns
    -------
    dict
        {"go": [...], "local": [...], "api": [...] or None}
    """
    if isinstance(deg_genes, set):
        deg_genes = list(deg_genes)

    result = {"go": [], "local": [], "api": None}

    # GO 富集（超几何检验 + FDR）
    print("[enrichment] 运行 GO 神经通路富集...")
    result["go"] = run_go_enrichment(deg_genes)

    # 本地通路匹配
    result["local"] = local_pathway_enrichment(set(deg_genes))

    if use_api:
        print("[enrichment] 调用 Enrichr API...")
        result["api"] = enrichr_enrich(deg_genes)
        if result["api"]:
            print(f"[enrichment] API 获取到 {len(result['api'])} 条通路")
        else:
            print("[enrichment] API 不可用")

    if not result["go"] and not result["local"] and not result["api"]:
        print("[enrichment] 未找到任何富集结果")

    return result
