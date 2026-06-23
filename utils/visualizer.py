"""visualizer.py — 可视化模块"""

import matplotlib
matplotlib.use("Agg")  # 无界面后端
import matplotlib.pyplot as plt
import numpy as np
import os


def plot_volcano(df_volcano, output_path=None, title="Volcano Plot"):
    """
    绘制火山图
    
    Parameters
    ----------
    df_volcano : pd.DataFrame
        需包含 log2fc, -log10_padj, significant 列
    output_path : str
        输出路径
    title : str
        图表标题
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = {"Up": "#E74C3C", "Down": "#3498DB", "NS": "#BDC3C7"}
    
    for status in ["NS", "Up", "Down"]:
        mask = df_volcano["significant"] == status
        ax.scatter(
            df_volcano.loc[mask, "log2fc"],
            df_volcano.loc[mask, "-log10_padj"],
            c=colors[status],
            label=status,
            alpha=0.6 if status == "NS" else 0.8,
            s=8 if status == "NS" else 20
        )
    
    # 标注阈值线
    ax.axhline(-np.log10(0.05), color="gray", linestyle="--", alpha=0.5)
    ax.axvline(1, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(-1, color="gray", linestyle="--", alpha=0.5)
    
    ax.set_xlabel("log2(Fold Change)", fontsize=12)
    ax.set_ylabel("-log10(Adjusted P-value)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend()
    
    # 标注Top基因
    top_genes = df_volcano.nsmallest(10, "padj")
    for _, g in top_genes.iterrows():
        ax.annotate(
            g["gene"],
            (g["log2fc"], g["-log10_padj"]),
            fontsize=7,
            alpha=0.8,
            xytext=(5, 5),
            textcoords="offset points"
        )
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] 火山图已保存: {output_path}")
    
    plt.close()


def plot_cell_type_bar(match_result, output_path=None):
    """
    绘制神经细胞类型匹配柱状图
    
    Parameters
    ----------
    match_result : dict
        neural_matcher的输出
    output_path : str
        输出路径
    """
    results = match_result.get("results", [])
    if not results:
        print("[visualizer] 无匹配结果可绘图")
        return
    
    cell_types = [r["type"] for r in results]
    up_counts = [r["up_count"] for r in results]
    down_counts = [r["down_count"] for r in results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(cell_types))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, up_counts, width, label="Up", color="#E74C3C")
    bars2 = ax.bar(x + width/2, down_counts, width, label="Down", color="#3498DB")
    
    ax.set_xlabel("Cell Type")
    ax.set_ylabel("Matched Marker Genes")
    ax.set_title("Neural Cell Types Affected by DEG")
    ax.set_xticks(x)
    ax.set_xticklabels(cell_types, rotation=45, ha="right")
    ax.legend()
    
    # 标注数值
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f"{int(height)}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f"{int(height)}", ha="center", va="bottom", fontsize=8)
    
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] 细胞类型柱状图已保存: {output_path}")
    
    plt.close()
