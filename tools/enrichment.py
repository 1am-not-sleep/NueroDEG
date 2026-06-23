from __future__ import annotations

import math

import pandas as pd
from scipy.stats import hypergeom

from tools.neural_classifier import NEURAL_MODULES


def _bh_fdr(p_values: list[float]) -> list[float]:
    if not p_values:
        return []

    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [math.nan] * len(p_values)
    prev = 1.0
    m = len(p_values)

    for rank, (idx, p_value) in reversed(list(enumerate(indexed, start=1))):
        value = min(prev, p_value * m / rank)
        adjusted[idx] = min(value, 1.0)
        prev = value

    return adjusted


def run_marker_enrichment(up: pd.DataFrame, down: pd.DataFrame, background: pd.DataFrame) -> pd.DataFrame:
    universe = {str(gene).upper() for gene in background["gene"].dropna().tolist()}
    if not universe:
        return pd.DataFrame(
            columns=[
                "direction",
                "term",
                "overlap_count",
                "set_size",
                "query_size",
                "background_size",
                "p_value",
                "fdr",
                "overlap_genes",
                "method",
            ]
        )

    rows: list[dict[str, object]] = []
    for direction, df in [("Up", up), ("Down", down)]:
        genes = {str(gene).upper() for gene in df["gene"].dropna().tolist()} if not df.empty else set()
        genes = genes.intersection(universe)
        query_size = len(genes)
        if query_size == 0:
            continue

        for module, config in NEURAL_MODULES.items():
            markers = {str(marker).upper() for marker in config["markers"]}.intersection(universe)
            overlap = sorted(genes.intersection(markers))
            if not overlap:
                continue
            background_size = len(universe)
            set_size = len(markers)
            overlap_count = len(overlap)
            p_value = float(hypergeom.sf(overlap_count - 1, background_size, set_size, query_size))
            rows.append(
                {
                    "direction": direction,
                    "term": str(config["label"]),
                    "overlap_count": overlap_count,
                    "set_size": set_size,
                    "query_size": query_size,
                    "background_size": background_size,
                    "p_value": p_value,
                    "fdr": math.nan,
                    "overlap_genes": ", ".join(overlap),
                    "method": "Hypergeometric marker-set overrepresentation",
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "direction",
                "term",
                "overlap_count",
                "set_size",
                "query_size",
                "background_size",
                "p_value",
                "fdr",
                "overlap_genes",
                "method",
            ]
        )

    result = pd.DataFrame(rows)
    result["fdr"] = _bh_fdr(result["p_value"].tolist())
    return result.sort_values(["fdr", "p_value", "overlap_count"], ascending=[True, True, False]).reset_index(drop=True)
