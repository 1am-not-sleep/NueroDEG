"""filter.py — 差异表达基因筛选模块"""

import pandas as pd
import numpy as np


def filter_degs(df, fc_cutoff=1.0, p_cutoff=0.05):
    df = df.copy()
    df["log2fc"] = pd.to_numeric(df["log2fc"], errors="coerce")
    df["padj"] = pd.to_numeric(df["padj"], errors="coerce")
    df = df.dropna(subset=["log2fc", "padj"])

    sig_mask = (df["padj"] < p_cutoff) & (df["log2fc"].abs() > fc_cutoff)
    sig_genes = df[sig_mask].copy().sort_values("padj")
    up_genes = sig_genes[sig_genes["log2fc"] > 0].sort_values("log2fc", ascending=False)
    down_genes = sig_genes[sig_genes["log2fc"] < 0].sort_values("log2fc", ascending=True)
    sig_genes["direction"] = np.where(sig_genes["log2fc"] > 0, "up", "down")

    summary = {
        "total_genes": len(df),
        "significant": len(sig_genes),
        "up": len(up_genes),
        "down": len(down_genes),
        "fc_cutoff": fc_cutoff,
        "p_cutoff": p_cutoff,
        "top_up": up_genes.head(10)[["gene", "log2fc", "padj"]].to_dict("records") if len(up_genes) > 0 else [],
        "top_down": down_genes.head(10)[["gene", "log2fc", "padj"]].to_dict("records") if len(down_genes) > 0 else []
    }

    print(f"[filter] 筛选完成: {summary['significant']} 显著 ({summary['up']}↑ {summary['down']}↓)")
    return {"up": up_genes, "down": down_genes, "all": sig_genes, "summary": summary}


def get_volcano_data(df, fc_cutoff=1.0, p_cutoff=0.05):
    result = df[["gene", "log2fc", "padj"]].copy()
    result["-log10_padj"] = -np.log10(result["padj"].clip(lower=1e-300))
    result["significant"] = "NS"
    result.loc[(result["log2fc"] > fc_cutoff) & (result["padj"] < p_cutoff), "significant"] = "Up"
    result.loc[(result["log2fc"] < -fc_cutoff) & (result["padj"] < p_cutoff), "significant"] = "Down"
    return result
