from __future__ import annotations

from collections.abc import Sequence

from tools.deg_filter import DegSummary
from tools.neural_classifier import ModuleHit


def answer_followup(question: str, summary: DegSummary, module_hits: Sequence[ModuleHit], report: str) -> str:
    normalized = question.lower()

    if any(term in normalized for term in ["microglia", "inflammation", "小胶质", "炎症"]):
        hits = [hit for hit in module_hits if hit.module == "Microglia"]
        if hits:
            genes = ", ".join(hits[0].matched_genes)
            return (
                f"Microglia/neuroinflammation is supported by {hits[0].direction.lower()}-regulated marker genes: "
                f"{genes}. This supports an exploratory neuroinflammatory interpretation, not a causal proof."
            )
        return "This run did not detect a direct microglia marker module in the significant DEG lists."

    if any(term in normalized for term in ["myelin", "oligodendro", "髓鞘", "少突"]):
        hits = [hit for hit in module_hits if hit.module in {"Oligodendrocyte", "OPC"}]
        if hits:
            genes = ", ".join(hits[0].matched_genes)
            return (
                f"Myelination-related interpretation is supported by {hits[0].direction.lower()}-regulated genes: "
                f"{genes}. DEG evidence alone cannot prove functional demyelination."
            )
        return "This run did not detect a direct oligodendrocyte/myelination marker module."

    if any(term in normalized for term in ["synapse", "synaptic", "neuron", "突触", "神经元"]):
        hits = [hit for hit in module_hits if hit.module in {"Synapse", "Neuron", "Excitatory neuron", "Inhibitory neuron"}]
        if hits:
            lines = [f"- {hit.label}: {', '.join(hit.matched_genes)} ({hit.direction})" for hit in hits]
            return "Detected neuronal/synaptic signals:\n" + "\n".join(lines)
        return "This run did not detect direct neuronal or synaptic marker modules."

    if any(term in normalized for term in ["limitation", "risk", "局限", "不足"]):
        return (
            "Main limitations: DEG results cannot prove protein-level or functional change; bulk tissue can reflect "
            "cell-composition shifts; the MVP marker dictionary is small; GO/KEGG enrichment should be added for a stronger version."
        )

    if any(term in normalized for term in ["count", "多少", "summary", "概况"]):
        return (
            f"This run analyzed {summary.total_genes} genes, with {summary.up_count} significant up-regulated and "
            f"{summary.down_count} significant down-regulated genes under the configured cutoffs."
        )

    if any(term in normalized for term in ["next", "validate", "验证", "下一步"]):
        return (
            "Recommended next steps: validate key genes by qPCR/immunostaining, compare with independent datasets, "
            "check cell-type composition, and add GO/KEGG enrichment or single-cell reference signatures."
        )

    return (
        "I can answer questions about detected modules, key genes, limitations, validation, and summary counts for this run. "
        "For details, use the Report and Agent Trace tabs."
    )
