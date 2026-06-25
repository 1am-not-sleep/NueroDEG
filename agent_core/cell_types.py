"""Canonical bilingual labels and abbreviations for neural cell types."""

from __future__ import annotations


CELL_TYPE_LABELS = {
    "兴奋性神经元": ("兴奋性神经元", "Excitatory neuron", "ExN"),
    "Excitatory Neuron": ("兴奋性神经元", "Excitatory neuron", "ExN"),
    "Glutaminergic neurons": ("谷氨酸能神经元", "Glutamatergic neuron", "GluN"),
    "抑制性神经元": ("抑制性神经元", "Inhibitory neuron", "InN"),
    "Inhibitory Neuron": ("抑制性神经元", "Inhibitory neuron", "InN"),
    "GABAergic neurons": ("GABA能神经元", "GABAergic neuron", "GABA-N"),
    "星形胶质细胞": ("星形胶质细胞", "Astrocyte", "Astro"),
    "Astrocyte": ("星形胶质细胞", "Astrocyte", "Astro"),
    "Astrocytes": ("星形胶质细胞", "Astrocyte", "Astro"),
    "小胶质细胞": ("小胶质细胞", "Microglia", "MG"),
    "Microglia": ("小胶质细胞", "Microglia", "MG"),
    "少突胶质细胞": ("少突胶质细胞", "Oligodendrocyte", "Oligo"),
    "Oligodendrocyte": ("少突胶质细胞", "Oligodendrocyte", "Oligo"),
    "Oligodendrocytes": ("少突胶质细胞", "Oligodendrocyte", "Oligo"),
    "Oligodendrocyte progenitor cells": (
        "少突胶质前体细胞",
        "Oligodendrocyte progenitor cell",
        "OPC",
    ),
    "神经干细胞/前体细胞": (
        "神经干细胞/前体细胞",
        "Neural stem/progenitor cell",
        "NSC/NPC",
    ),
    "Neural Stem/Progenitor Cell": (
        "神经干细胞/前体细胞",
        "Neural stem/progenitor cell",
        "NSC/NPC",
    ),
    "多巴胺能神经元": ("多巴胺能神经元", "Dopaminergic neuron", "DA-N"),
    "Dopaminergic Neuron": ("多巴胺能神经元", "Dopaminergic neuron", "DA-N"),
    "Dopaminergic neurons": ("多巴胺能神经元", "Dopaminergic neuron", "DA-N"),
    "胆碱能神经元": ("胆碱能神经元", "Cholinergic neuron", "ChN"),
    "Cholinergic Neuron": ("胆碱能神经元", "Cholinergic neuron", "ChN"),
    "Cholinergic neurons": ("胆碱能神经元", "Cholinergic neuron", "ChN"),
    "血清素能神经元": ("血清素能神经元", "Serotonergic neuron", "5-HT-N"),
    "Serotonergic Neuron": ("血清素能神经元", "Serotonergic neuron", "5-HT-N"),
    "Serotonergic neurons": ("血清素能神经元", "Serotonergic neuron", "5-HT-N"),
    "Interneurons": ("中间神经元", "Interneuron", "IN"),
    "Motor neurons": ("运动神经元", "Motor neuron", "MN"),
    "Pyramidal cells": ("锥体细胞", "Pyramidal neuron", "PyrN"),
    "Purkinje neurons": ("浦肯野神经元", "Purkinje neuron", "PC"),
    "Purkinje fiber cells": ("浦肯野纤维细胞", "Purkinje fiber cell", "PF"),
    "Radial glia cells": ("放射状胶质细胞", "Radial glial cell", "RGC"),
    "Bergmann glia": ("伯格曼胶质细胞", "Bergmann glia", "BG"),
    "Satellite glial cells": ("卫星胶质细胞", "Satellite glial cell", "SGC"),
    "Neuroblasts": ("神经母细胞", "Neuroblast", "NB"),
    "Immature neurons": ("未成熟神经元", "Immature neuron", "ImmN"),
    "Adrenergic neurons": ("肾上腺素能神经元", "Adrenergic neuron", "AdrN"),
    "Noradrenergic neurons": ("去甲肾上腺素能神经元", "Noradrenergic neuron", "NA-N"),
    "Glycinergic neurons": ("甘氨酸能神经元", "Glycinergic neuron", "GlyN"),
    "Enteric neurons": ("肠神经元", "Enteric neuron", "EN"),
    "Enteric glia cells": ("肠胶质细胞", "Enteric glial cell", "EGC"),
    "Neuroendocrine cells": ("神经内分泌细胞", "Neuroendocrine cell", "NEC"),
    "Trigeminal neurons": ("三叉神经元", "Trigeminal neuron", "TriN"),
    "Neurons": ("神经元", "Neuron", "Neu"),
}


def normalize_cell_type(type_name, type_en=""):
    """Return stable Chinese, English, abbreviation, and display labels."""
    key = type_name if type_name in CELL_TYPE_LABELS else type_en
    if key in CELL_TYPE_LABELS:
        type_zh, normalized_en, abbreviation = CELL_TYPE_LABELS[key]
    else:
        normalized_en = type_en or type_name
        type_zh = type_name if any("\u4e00" <= char <= "\u9fff" for char in type_name) else ""
        abbreviation = "".join(
            word[0].upper()
            for word in normalized_en.replace("/", " ").replace("-", " ").split()
            if word
        )[:6] or normalized_en[:6]

    display_name = (
        f"{type_zh} | {normalized_en} ({abbreviation})"
        if type_zh
        else f"{normalized_en} ({abbreviation})"
    )
    return {
        "type_zh": type_zh,
        "type_en": normalized_en,
        "abbreviation": abbreviation,
        "display_name": display_name,
    }


def find_cell_type_label(query):
    """Find a canonical cell-type label by Chinese name, English name, or abbreviation."""
    normalized_query = query.strip().lower()
    seen = set()
    for source_name, values in CELL_TYPE_LABELS.items():
        type_zh, type_en, abbreviation = values
        identity = (type_zh, type_en, abbreviation)
        if identity in seen:
            continue
        seen.add(identity)
        aliases = {
            source_name.lower(),
            type_zh.lower(),
            type_en.lower(),
            abbreviation.lower(),
        }
        aliases.discard("")
        if normalized_query in aliases or any(alias in normalized_query for alias in aliases):
            return normalize_cell_type(source_name, type_en)
    return None
