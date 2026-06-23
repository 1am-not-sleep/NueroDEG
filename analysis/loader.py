"""loader.py — DEG 文件加载与校验模块"""

import pandas as pd
import os
import sys

# 标准DEG文件列名映射
COLUMN_ALIASES = {
    "gene": ["gene", "genes", "symbol", "gene_symbol", "gene_name", "geneid", "gene_id", "gene name", "name"],
    "log2fc": ["log2fc", "log2_fc", "logfc", "lfc", "fold_change", "fc", "log2 fold change", "log2(fold_change)"],
    "pval": ["pval", "p_val", "pvalue", "p_value", "p value", "p", "pvalue"],
    "padj": ["padj", "p_adj", "adj_pval", "adj_p_value", "adjusted_pvalue", 
             "adjusted p value", "fdr", "qvalue", "q_val", "q_value", "bonferroni"]
}


def detect_column(df, col_type):
    """自动检测指定类型的列名"""
    aliases = COLUMN_ALIASES[col_type]
    for alias in aliases:
        for col in df.columns:
            if col.strip().lower() == alias.lower():
                return col
    return None


def load_deg(filepath):
    """
    加载DEG文件，自动检测列名并标准化
    
    Parameters
    ----------
    filepath : str
        CSV或TSV文件路径
        
    Returns
    -------
    pd.DataFrame
        标准化后的DEG数据框，包含gene, log2fc, pval, padj列
        
    Raises
    ------
    FileNotFoundError
        文件不存在
    ValueError
        无法识别必要列
    """
    # 检查文件是否存在
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 自动判断分隔符
    if filepath.endswith('.tsv') or filepath.endswith('.txt'):
        sep = '\\t'
    else:
        sep = ','
    
    try:
        df = pd.read_csv(filepath, sep=sep, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, sep=sep, encoding='gbk')
    except Exception as e:
        raise ValueError(f"无法读取文件: {e}")
    
    if df.empty:
        raise ValueError("文件为空或未读取到数据")
    
    # 标准化列名（转小写并去除空白）
    df_clean = df.copy()
    df_clean.columns = [c.strip() for c in df_clean.columns]
    
    # 检测必要列
    gene_col = detect_column(df_clean, "gene")
    lfc_col = detect_column(df_clean, "log2fc")
    pval_col = detect_column(df_clean, "pval")
    padj_col = detect_column(df_clean, "padj")
    
    if gene_col is None:
        raise ValueError("无法检测到基因名列。期望的列名: gene, symbol, gene_name 等")
    if lfc_col is None:
        raise ValueError("无法检测到log2FC列。期望的列名: log2FC, log2_fc, fold_change 等")
    if padj_col is None and pval_col is None:
        raise ValueError("无法检测到显著性列(padj或pvalue)")
    
    # 构建标准化数据框
    result = pd.DataFrame()
    result["gene"] = df_clean[gene_col].astype(str).str.strip()
    result["log2fc"] = pd.to_numeric(df_clean[lfc_col], errors="coerce")
    
    if padj_col:
        result["padj"] = pd.to_numeric(df_clean[padj_col], errors="coerce")
    else:
        result["padj"] = pd.to_numeric(df_clean[pval_col], errors="coerce")
    
    if pval_col:
        result["pval"] = pd.to_numeric(df_clean[pval_col], errors="coerce")
    else:
        result["pval"] = result["padj"]
    
    # 删除缺失关键数据的行
    before = len(result)
    result = result.dropna(subset=["gene", "log2fc"])
    after = len(result)
    
    if after == 0:
        raise ValueError("所有基因数据均缺失，请检查文件格式")
    
    dropped = before - after
    if dropped > 0:
        print(f"[警告] 删除了 {dropped} 行缺失数据")
    
    print(f"[loader] 成功加载 {len(result)} 个基因的表达数据")
    return result


def summarize_deg(df, fc_cutoff=1.0, p_cutoff=0.05):
    """打印DEG数据摘要"""
    sig_up = len(df[(df["log2fc"] > fc_cutoff) & (df["padj"] < p_cutoff)])
    sig_down = len(df[(df["log2fc"] < -fc_cutoff) & (df["padj"] < p_cutoff)])
    
    print(f"  ├─ 总基因数: {len(df)}")
    print(f"  ├─ 显著差异: {sig_up + sig_down}")
    print(f"  ├─ 上调: {sig_up}")
    print(f"  └─ 下调: {sig_down}")
    print(f"  └─ log2FC范围: [{df['log2fc'].min():.2f}, {df['log2fc'].max():.2f}]")


if __name__ == "__main__":
    # 测试用
    if len(sys.argv) > 1:
        df = load_deg(sys.argv[1])
        summarize_deg(df)
    else:
        print("用法: python loader.py <deg_file.csv>")
