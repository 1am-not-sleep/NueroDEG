"""loader.py — DEG 文件加载与校验模块"""

import pandas as pd
import os

COLUMN_ALIASES = {
    "gene": ["gene", "genes", "symbol", "gene_symbol", "gene_name", "geneid", "gene_id", "gene name", "name"],
    "log2fc": ["log2fc", "log2_fc", "logfc", "lfc", "fold_change", "fc", "log2 fold change", "log2(fold_change)"],
    "pval": ["pval", "p_val", "pvalue", "p_value", "p value", "p", "pvalue"],
    "padj": ["padj", "p_adj", "adj_pval", "adj_p_value", "adjusted_pvalue",
             "adjusted p value", "fdr", "qvalue", "q_val", "q_value", "bonferroni"]
}


def detect_column(df, col_type):
    aliases = COLUMN_ALIASES[col_type]
    for alias in aliases:
        for col in df.columns:
            if col.strip().lower() == alias.lower():
                return col
    return None


def load_deg(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    sep = '\t' if filepath.endswith(('.tsv', '.txt')) else ','

    try:
        df = pd.read_csv(filepath, sep=sep, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, sep=sep, encoding='gbk')
    except Exception as e:
        raise ValueError(f"无法读取文件: {e}")

    if df.empty:
        raise ValueError("文件为空或未读取到数据")

    df_clean = df.copy()
    df_clean.columns = [c.strip() for c in df_clean.columns]

    gene_col = detect_column(df_clean, "gene")
    lfc_col = detect_column(df_clean, "log2fc")
    pval_col = detect_column(df_clean, "pval")
    padj_col = detect_column(df_clean, "padj")

    if gene_col is None:
        raise ValueError("无法检测到基因名列")
    if lfc_col is None:
        raise ValueError("无法检测到log2FC列")
    if padj_col is None and pval_col is None:
        raise ValueError("无法检测到显著性列(padj或pvalue)")

    result = pd.DataFrame()
    result["gene"] = df_clean[gene_col].astype("string").str.strip()
    result["log2fc"] = pd.to_numeric(df_clean[lfc_col], errors="coerce")
    result["padj"] = pd.to_numeric(df_clean[padj_col], errors="coerce") if padj_col else pd.to_numeric(df_clean[pval_col], errors="coerce")
    result["pval"] = pd.to_numeric(df_clean[pval_col], errors="coerce") if pval_col else result["padj"]

    result.loc[result["gene"].isin(["", "nan", "None"]), "gene"] = pd.NA
    before = len(result)
    result = result.dropna(subset=["gene", "log2fc", "padj"])
    if len(result) == 0:
        raise ValueError("所有基因数据均缺失，请检查文件格式")
    dropped = before - len(result)
    if dropped > 0:
        print(f"[loader] 删除了 {dropped} 行缺失数据")

    invalid_p = (result["padj"] < 0) | (result["padj"] > 1)
    if invalid_p.any():
        raise ValueError("显著性列必须位于 0 到 1 之间")

    duplicates = result["gene"].str.upper().duplicated().sum()
    if duplicates:
        print(f"[loader] 警告: 检测到 {duplicates} 个重复基因条目")

    print(f"[loader] 成功加载 {len(result)} 个基因")
    return result


def summarize_deg(df, fc_cutoff=1.0, p_cutoff=0.05):
    sig_up = len(df[(df["log2fc"] > fc_cutoff) & (df["padj"] < p_cutoff)])
    sig_down = len(df[(df["log2fc"] < -fc_cutoff) & (df["padj"] < p_cutoff)])
    print(f"  ├─ 总基因数: {len(df)}")
    print(f"  ├─ 显著差异: {sig_up + sig_down}")
    print(f"  ├─ 上调: {sig_up}")
    print(f"  └─ 下调: {sig_down}")
