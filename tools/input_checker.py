from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


REQUIRED_COLUMNS = ["gene", "log2FC", "p_adj"]

ALIASES = {
    "gene": {"gene", "genes", "symbol", "gene_symbol", "genesymbol"},
    "log2FC": {"log2fc", "logfc", "avg_log2fc", "log2foldchange", "log2_fold_change"},
    "p_adj": {"p_adj", "padj", "adj_p_val", "adjusted_p_value", "fdr", "qvalue", "p.adjust"},
}


@dataclass
class InputCheckResult:
    valid: bool
    message: str
    df: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)


def _normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    normalized = df.copy()
    normalized.columns = [str(col).strip() for col in normalized.columns]

    lowercase_to_original = {col.lower(): col for col in normalized.columns}
    rename_map: dict[str, str] = {}
    warnings: list[str] = []

    for canonical, aliases in ALIASES.items():
        if canonical in normalized.columns:
            continue
        for alias in aliases:
            if alias in lowercase_to_original:
                source = lowercase_to_original[alias]
                rename_map[source] = canonical
                warnings.append(f"Column '{source}' was interpreted as '{canonical}'.")
                break

    if rename_map:
        normalized = normalized.rename(columns=rename_map)

    return normalized, warnings


def check_input(df: pd.DataFrame) -> InputCheckResult:
    if df is None or df.empty:
        return InputCheckResult(False, "Input table is empty.")

    clean_df, warnings = _normalize_columns(df)
    missing = [col for col in REQUIRED_COLUMNS if col not in clean_df.columns]
    if missing:
        return InputCheckResult(
            False,
            f"Missing required columns: {', '.join(missing)}.",
            missing_columns=missing,
            warnings=warnings,
        )

    clean_df = clean_df[REQUIRED_COLUMNS].copy()
    clean_df["gene"] = clean_df["gene"].astype("string").str.strip()

    if clean_df["gene"].isna().any() or (clean_df["gene"] == "").any():
        return InputCheckResult(False, "Some gene names are missing.", warnings=warnings)

    for numeric_col in ["log2FC", "p_adj"]:
        clean_df[numeric_col] = pd.to_numeric(clean_df[numeric_col], errors="coerce")
        if clean_df[numeric_col].isna().any():
            return InputCheckResult(
                False,
                f"Column '{numeric_col}' contains non-numeric or missing values.",
                warnings=warnings,
            )

    if ((clean_df["p_adj"] < 0) | (clean_df["p_adj"] > 1)).any():
        return InputCheckResult(False, "Column 'p_adj' must be between 0 and 1.", warnings=warnings)

    duplicate_count = int(clean_df["gene"].str.upper().duplicated().sum())
    if duplicate_count:
        warnings.append(f"{duplicate_count} duplicate gene symbol rows were detected.")

    clean_df = clean_df.sort_values(["p_adj", "gene"], ascending=[True, True]).reset_index(drop=True)
    return InputCheckResult(True, "Input file is valid.", df=clean_df, warnings=warnings)
