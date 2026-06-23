from __future__ import annotations

import pandas as pd

from tools.deg_filter import DegSummary
from tools.input_checker import InputCheckResult
from tools.neural_classifier import ModuleHit


def _format_gene_list(df: pd.DataFrame, limit: int = 8) -> str:
    if df.empty:
        return "None"
    top = df.sort_values(["p_adj", "log2FC"], ascending=[True, False]).head(limit)
    return ", ".join(str(gene) for gene in top["gene"].tolist())


def _module_sentence(hit: ModuleHit) -> str:
    genes = ", ".join(hit.matched_genes)
    direction = "up-regulated" if hit.direction == "Up" else "down-regulated"
    return (
        f"- **{hit.label} ({hit.direction})**: matched {direction} genes: {genes}. "
        f"{hit.interpretation}"
    )


def generate_report(
    comparison_info: str,
    species: str,
    input_result: InputCheckResult,
    deg_summary: DegSummary,
    module_hits: list[ModuleHit],
    enrichment_table: pd.DataFrame,
    knowledge_notes: dict[str, str],
    run_id: str = "",
    confidence: str = "medium",
    agent_decisions: list[str] | None = None,
    human_review_reasons: list[str] | None = None,
) -> str:
    comparison = comparison_info.strip() or "Not specified"
    warnings = input_result.warnings or []
    decisions = agent_decisions or []
    review_reasons = human_review_reasons or []
    warning_block = "\n".join(f"- {warning}" for warning in warnings) if warnings else "- No input warnings."
    decision_block = "\n".join(f"- {decision}" for decision in decisions) if decisions else "- Fixed MVP workflow."
    review_block = (
        "\n".join(f"- {reason}" for reason in review_reasons)
        if review_reasons
        else "- No human review trigger was raised by the rule-based agent."
    )

    if deg_summary.significant_genes < 5:
        signal_note = (
            "The number of significant genes is small, so pathway-level interpretation should be treated as exploratory."
        )
    else:
        signal_note = "The significant gene set is sufficient for a first-pass marker/module interpretation."

    if module_hits:
        module_block = "\n".join(_module_sentence(hit) for hit in module_hits)
    else:
        module_block = (
            "- No predefined neural marker module was strongly detected in the significant DEG lists. "
            "This does not rule out neural biology; it means the MVP marker dictionary did not find a direct match."
        )

    if enrichment_table.empty:
        enrichment_block = (
            "No marker-set overrepresentation terms were detected. For a final project version, run GO/KEGG enrichment with GSEApy."
        )
    else:
        enrichment_rows = []
        for _, row in enrichment_table.head(10).iterrows():
            p_value = float(row["p_value"])
            fdr = float(row["fdr"])
            enrichment_rows.append(
                f"- {row['direction']} | {row['term']} | overlap={row['overlap_count']} | "
                f"p={p_value:.3g} | FDR={fdr:.3g} | genes={row['overlap_genes']}"
            )
        enrichment_block = "\n".join(enrichment_rows)

    knowledge_block = "\n\n".join(
        f"### {title.replace('_', ' ').title()}\n{content}" for title, content in knowledge_notes.items()
    )

    return f"""# NeuroDEG-Agent Report

## 1. Agent Run Summary

- Run ID: {run_id or "Not recorded"}
- Agent confidence: {confidence}

Agent decisions:

{decision_block}

Human review triggers:

{review_block}

## 2. Data Summary

- Comparison: {comparison}
- Species: {species}
- Total genes: {deg_summary.total_genes}
- Significant up-regulated genes: {deg_summary.up_count}
- Significant down-regulated genes: {deg_summary.down_count}
- Cutoffs: log2FC > {deg_summary.logfc_cutoff} or < -{deg_summary.logfc_cutoff}; p_adj < {deg_summary.padj_cutoff}

{signal_note}

## 3. Input Quality Notes

{warning_block}

## 4. Differential Genes

- Top up-regulated genes: {_format_gene_list(deg_summary.up)}
- Top down-regulated genes: {_format_gene_list(deg_summary.down)}

## 5. MVP Enrichment Results

The current MVP uses curated neural marker-set overrepresentation with a hypergeometric test and Benjamini-Hochberg FDR correction. It is not a replacement for full GO/KEGG enrichment, but it gives a statistically grounded demo result without requiring online databases.

{enrichment_block}

## 6. Neural Functional Interpretation

{module_block}

## 7. Biological Interpretation

This report should be read as a hypothesis-generating interpretation of an already computed DEG table. Up-regulated immune or glial marker genes may suggest activation or compositional shifts, while down-regulated neuronal or myelin genes may suggest reduced neuronal/synaptic or oligodendrocyte-related transcriptional programs. These conclusions depend on the original experimental design, normalization method, cell composition, and statistical model.

## 8. Knowledge Base Notes

{knowledge_block}

## 9. Limitations

- DEG results alone cannot prove protein-level change or functional impairment.
- Bulk tissue DEG can reflect cell-type composition changes as well as within-cell transcriptional changes.
- The MVP marker dictionary is intentionally small and should be expanded for real biological use.
- GO/KEGG enrichment should be added for a stronger final version.

## 10. Suggested Validation

- Validate key genes with qPCR, western blot, immunostaining, or independent datasets.
- Check whether marker changes match expected brain region and disease biology.
- Compare results against cell-type reference datasets or single-cell signatures when available.
"""
