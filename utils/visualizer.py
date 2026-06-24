"""visualizer.py — 可视化模块"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

# ====== 中文字体配置 ======
_CN_FONT_SET = False


def _setup_cn_font():
    """自动探测并设置中文字体，支持 Windows / macOS / Linux"""
    global _CN_FONT_SET
    if _CN_FONT_SET:
        return
    _CN_FONT_SET = True

    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "DejaVu Sans",
    ]
    from matplotlib.font_manager import findfont
    for font in candidates:
        try:
            findfont(font, fallback_to_default=False)
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            print(f"[visualizer] 中文字体: {font}")
            return
        except Exception:
            continue
    # fallback
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "PingFang SC",
        "Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans"
    ]
    plt.rcParams["axes.unicode_minus"] = False


_setup_cn_font()


def plot_volcano(df_volcano, output_path=None, title="Volcano Plot", fc_cutoff=1.0, p_cutoff=0.05):
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = {"Up": "#E74C3C", "Down": "#3498DB", "NS": "#BDC3C7"}
    for status in ["NS", "Up", "Down"]:
        mask = df_volcano["significant"] == status
        ax.scatter(df_volcano.loc[mask, "log2fc"], df_volcano.loc[mask, "-log10_padj"],
                   c=colors[status], label=status, alpha=0.6 if status=="NS" else 0.8, s=8 if status=="NS" else 20)
    ax.axhline(-np.log10(p_cutoff), color="gray", linestyle="--", alpha=0.5)
    ax.axvline(fc_cutoff, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(-fc_cutoff, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("log2(Fold Change)", fontsize=12)
    ax.set_ylabel("-log10(Adjusted P-value)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend()
    for _, g in df_volcano.nsmallest(10, "padj").iterrows():
        ax.annotate(g["gene"], (g["log2fc"], g["-log10_padj"]), fontsize=7, alpha=0.8, xytext=(5,5), textcoords="offset points")
    plt.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] 火山图已保存: {output_path}")
    plt.close()


def plot_cell_type_bar(match_result, output_path=None):
    results = match_result.get("results", [])
    if not results:
        return
    ct_names = [r["type"] for r in results]
    up = [r["up_count"] for r in results]
    down = [r["down_count"] for r in results]
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(ct_names))
    b1 = ax.bar(x - 0.175, up, 0.35, label="Up", color="#E74C3C")
    b2 = ax.bar(x + 0.175, down, 0.35, label="Down", color="#3498DB")
    ax.set_xticks(x)
    ax.set_xticklabels(ct_names, rotation=45, ha="right")
    ax.set_ylabel("Matched Marker Genes")
    ax.set_title("Affected Neural Cell Types")
    ax.legend()
    for bar in b1:
        if h := bar.get_height():
            ax.text(bar.get_x()+bar.get_width()/2, h, f"{int(h)}", ha="center", va="bottom", fontsize=8)
    for bar in b2:
        if h := bar.get_height():
            ax.text(bar.get_x()+bar.get_width()/2, h, f"{int(h)}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] 柱状图已保存: {output_path}")
    plt.close()