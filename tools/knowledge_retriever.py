from __future__ import annotations

from pathlib import Path

from tools.neural_classifier import ModuleHit


MODULE_TO_FILE = {
    "Microglia": "neuroinflammation.md",
    "Astrocyte": "astrocyte_activation.md",
    "Oligodendrocyte": "myelination.md",
    "OPC": "myelination.md",
    "Synapse": "synaptic_transmission.md",
    "Excitatory neuron": "synaptic_transmission.md",
    "Inhibitory neuron": "synaptic_transmission.md",
    "Neuron": "neuron_markers.md",
    "Endothelial": "rna_seq_interpretation.md",
}


def retrieve_knowledge(hits: list[ModuleHit], knowledge_dir: str | Path = "knowledge_base") -> dict[str, str]:
    knowledge_dir = Path(knowledge_dir)
    selected_files = []
    for hit in hits:
        filename = MODULE_TO_FILE.get(hit.module)
        if filename and filename not in selected_files:
            selected_files.append(filename)

    if "rna_seq_interpretation.md" not in selected_files:
        selected_files.append("rna_seq_interpretation.md")

    notes: dict[str, str] = {}
    for filename in selected_files:
        path = knowledge_dir / filename
        if path.exists():
            notes[path.stem] = path.read_text(encoding="utf-8").strip()

    return notes
