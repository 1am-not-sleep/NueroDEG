from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


NEURAL_MODULES: dict[str, dict[str, object]] = {
    "Neuron": {
        "label": "Pan-neuronal identity",
        "markers": ["RBFOX3", "SNAP25", "SYT1", "MAP2", "TUBB3"],
        "interpretation": "Changes in broad neuronal markers may indicate altered neuronal abundance, integrity, or transcriptional state.",
    },
    "Excitatory neuron": {
        "label": "Excitatory neuron / glutamatergic signaling",
        "markers": ["SLC17A7", "SLC17A6", "CAMK2A", "GRIN1", "GRIA1"],
        "interpretation": "Matched genes point to glutamatergic neurons or excitatory synaptic signaling.",
    },
    "Inhibitory neuron": {
        "label": "Inhibitory neuron / GABAergic signaling",
        "markers": ["GAD1", "GAD2", "SLC32A1", "PVALB", "SST"],
        "interpretation": "Matched genes point to inhibitory interneurons or GABAergic signaling.",
    },
    "Astrocyte": {
        "label": "Astrocyte activation",
        "markers": ["GFAP", "AQP4", "ALDH1L1", "SLC1A3", "VIM"],
        "interpretation": "Astrocyte marker changes may suggest astrocyte reactivity, homeostatic changes, or altered astrocyte representation.",
    },
    "Oligodendrocyte": {
        "label": "Oligodendrocyte / myelination",
        "markers": ["MBP", "MOG", "PLP1", "MAG", "OLIG2", "MOBP"],
        "interpretation": "Myelin-related gene changes may suggest altered oligodendrocyte function or myelination-related processes.",
    },
    "OPC": {
        "label": "Oligodendrocyte precursor cells",
        "markers": ["PDGFRA", "CSPG4", "OLIG1", "VCAN", "SOX10"],
        "interpretation": "OPC marker changes may indicate altered oligodendrocyte lineage dynamics.",
    },
    "Microglia": {
        "label": "Microglia / neuroinflammation",
        "markers": ["AIF1", "CX3CR1", "P2RY12", "C1QA", "C1QB", "C1QC", "TYROBP", "TREM2"],
        "interpretation": "Microglial and complement-related genes often support a neuroinflammatory or immune activation interpretation.",
    },
    "Endothelial": {
        "label": "Vascular / endothelial signal",
        "markers": ["PECAM1", "CLDN5", "VWF", "KDR", "FLT1"],
        "interpretation": "Endothelial marker changes may reflect vascular or blood-brain-barrier related signals.",
    },
    "Synapse": {
        "label": "Synaptic transmission",
        "markers": ["SYN1", "SYP", "DLG4", "SNAP25", "SYT1", "GRIN1", "GRIA1"],
        "interpretation": "Synaptic gene changes may suggest altered synaptic transmission or neuronal connectivity.",
    },
}


@dataclass
class ModuleHit:
    module: str
    label: str
    direction: str
    matched_genes: list[str]
    score: int
    interpretation: str


def _gene_set(df: pd.DataFrame) -> set[str]:
    if df.empty:
        return set()
    return {str(gene).upper() for gene in df["gene"].dropna().tolist()}


def _classify_one_direction(df: pd.DataFrame, direction: str) -> list[ModuleHit]:
    genes = _gene_set(df)
    hits: list[ModuleHit] = []

    for module, config in NEURAL_MODULES.items():
        markers = [str(marker).upper() for marker in config["markers"]]
        matched = sorted(genes.intersection(markers))
        if matched:
            hits.append(
                ModuleHit(
                    module=module,
                    label=str(config["label"]),
                    direction=direction,
                    matched_genes=matched,
                    score=len(matched),
                    interpretation=str(config["interpretation"]),
                )
            )

    return sorted(hits, key=lambda hit: (-hit.score, hit.label, hit.direction))


def classify_neural_modules(up: pd.DataFrame, down: pd.DataFrame) -> list[ModuleHit]:
    hits = _classify_one_direction(up, "Up") + _classify_one_direction(down, "Down")
    return sorted(hits, key=lambda hit: (-hit.score, hit.direction, hit.label))


def module_hits_to_frame(hits: list[ModuleHit]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "direction": hit.direction,
                "module": hit.module,
                "label": hit.label,
                "matched_genes": ", ".join(hit.matched_genes),
                "score": hit.score,
                "interpretation": hit.interpretation,
            }
            for hit in hits
        ]
    )
