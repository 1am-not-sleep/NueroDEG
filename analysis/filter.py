"""filter.py — 差异表达基因筛选模块"""

import pandas as pd
import numpy as np


def filter_degs(df, fc_cutoff=1.0, p_cutoff=0.05):
    """
    筛选显著差异表达基因
    
    Parameters
    ----------
    df : pd.DataFrame
        标准化DEG数据（需包含 gene, log2fc, padj 列）
    fc_cutoff : float
        |log2FC| 阈值（默认1.0，即2倍变化）
    p_cutoff : float
        校正p值阈值（默认0.05）
        
    Returns
    -------
    dict
        {
            "up": DataFrame(上调基因),
            "down": DataFrame(下调基因),
            "all": DataFrame(全部显著基因),
            "summary": dict(统计摘要)
        }
    """
    # 确保数值列正确
    df = df.copy()
    df["log2fc"] = pd.to_numeric(df["log2fc"], errors="coerce")
    df["padj"] = pd.to_numeric(df["padj"], errors="coerce")
    
    # 过滤有效数值
    df = df.dropna(subset=["log2fc", "padj"])
    
    # 筛选显著基因
    sig_mask = (df["padj"] < p_cutoff) & (df["log2fc"].abs() > fc_cutoff)
    sig_genes = df[sig_mask].copy().sort_values("padj")
    
    # 分离上调和下调
    up_genes = sig_genes[sig_genes["log2fc"] > 0].sort_values("log2fc", ascending=False)
    down_genes = sig_genes[sig_genes["log2fc"] < 0].sort_values("log2fc", ascending=True)
    
    # 添加方向标签
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
    
    print(f"[filter] 筛选完成:")
    print(f"  ├─ 总基因: {summary['total_genes']}")
    print(f"  ├─ 显著差异: {summary['significant']}")
    print(f"  │  ├─ 上调: {summary['up']}")
    print(f"  │  └─ 下调: {summary['down']}")
    print(f"  └─ 阈值: |log2FC| > {fc_cutoff}, padj < {p_cutoff}")
    
    return {
        "up": up_genes,
        "down": down_genes,
        "all": sig_genes,
        "summary": summary
    }


def get_top_genes(deg_result, n=20):
    """获取top N差异基因（按padj排序）"""
    return deg_result["all"].head(n)


def get_volcano_data(df):
    """整理火山图所需数据"""
    result = df[["gene", "log2fc", "padj"]].copy()
    result["-log10_padj"] = -np.log10(result["padj"].clip(lower=1e-300))
    result["significant"] = "NS"
    result.loc[(result["log2fc"] > 1) & (result["padj"] < 0.05), "significant"] = "Up"
    result.loc[(result["log2fc"] < -1) & (result["padj"] < 0.05), "significant"] = "Down"
    return result
