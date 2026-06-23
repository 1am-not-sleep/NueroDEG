from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

MPLCONFIGDIR = Path(os.environ.get("MPLCONFIGDIR", Path.cwd() / ".cache" / "matplotlib")).resolve()
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_volcano(
    df: pd.DataFrame,
    output_path: str | Path,
    logfc_cutoff: float = 1.0,
    padj_cutoff: float = 0.05,
    top_n_labels: int = 8,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.copy()
    plot_df["safe_p_adj"] = plot_df["p_adj"].clip(lower=1e-300)
    plot_df["neg_log10_padj"] = -np.log10(plot_df["safe_p_adj"])

    up_mask = (plot_df["log2FC"] > logfc_cutoff) & (plot_df["p_adj"] < padj_cutoff)
    down_mask = (plot_df["log2FC"] < -logfc_cutoff) & (plot_df["p_adj"] < padj_cutoff)
    other_mask = ~(up_mask | down_mask)

    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(8.5, 6.2), dpi=160)

    ax.scatter(
        plot_df.loc[other_mask, "log2FC"],
        plot_df.loc[other_mask, "neg_log10_padj"],
        s=24,
        c="#9ca3af",
        alpha=0.65,
        label="Not significant",
        linewidths=0,
    )
    ax.scatter(
        plot_df.loc[down_mask, "log2FC"],
        plot_df.loc[down_mask, "neg_log10_padj"],
        s=34,
        c="#2563eb",
        alpha=0.86,
        label="Down",
        linewidths=0,
    )
    ax.scatter(
        plot_df.loc[up_mask, "log2FC"],
        plot_df.loc[up_mask, "neg_log10_padj"],
        s=34,
        c="#dc2626",
        alpha=0.86,
        label="Up",
        linewidths=0,
    )

    ax.axvline(logfc_cutoff, color="#52525b", linestyle="--", linewidth=1)
    ax.axvline(-logfc_cutoff, color="#52525b", linestyle="--", linewidth=1)
    ax.axhline(-np.log10(padj_cutoff), color="#52525b", linestyle="--", linewidth=1)

    label_df = plot_df.loc[up_mask | down_mask].copy()
    if not label_df.empty and top_n_labels > 0:
        label_df["rank_score"] = label_df["neg_log10_padj"] + label_df["log2FC"].abs()
        for _, row in label_df.nlargest(top_n_labels, "rank_score").iterrows():
            ax.annotate(
                str(row["gene"]),
                (row["log2FC"], row["neg_log10_padj"]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
                color="#111827",
            )

    ax.set_title("Volcano plot", fontsize=14, pad=12)
    ax.set_xlabel("log2 fold change")
    ax.set_ylabel("-log10(adjusted p-value)")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path
