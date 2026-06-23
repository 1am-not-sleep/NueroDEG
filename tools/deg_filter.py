from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DegSummary:
    annotated: pd.DataFrame
    up: pd.DataFrame
    down: pd.DataFrame
    total_genes: int
    significant_genes: int
    up_count: int
    down_count: int
    logfc_cutoff: float
    padj_cutoff: float


def filter_deg(df: pd.DataFrame, logfc_cutoff: float = 1.0, padj_cutoff: float = 0.05) -> DegSummary:
    annotated = df.copy()
    annotated["direction"] = "Not significant"

    up_mask = (annotated["log2FC"] > logfc_cutoff) & (annotated["p_adj"] < padj_cutoff)
    down_mask = (annotated["log2FC"] < -logfc_cutoff) & (annotated["p_adj"] < padj_cutoff)

    annotated.loc[up_mask, "direction"] = "Up"
    annotated.loc[down_mask, "direction"] = "Down"

    up = annotated.loc[up_mask].sort_values(["p_adj", "log2FC"], ascending=[True, False]).copy()
    down = annotated.loc[down_mask].sort_values(["p_adj", "log2FC"], ascending=[True, True]).copy()

    return DegSummary(
        annotated=annotated,
        up=up,
        down=down,
        total_genes=int(len(annotated)),
        significant_genes=int(up_mask.sum() + down_mask.sum()),
        up_count=int(up_mask.sum()),
        down_count=int(down_mask.sum()),
        logfc_cutoff=float(logfc_cutoff),
        padj_cutoff=float(padj_cutoff),
    )
