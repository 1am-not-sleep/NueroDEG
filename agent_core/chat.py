"""chat.py -- Ask Agent 追问接口"""

import json
import os

from agent_core.cell_types import find_cell_type_label, normalize_cell_type


def load_kb():
    path = os.path.join(os.path.dirname(__file__), "..", "core", "knowledge_base.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_gene(gene: str, kb: dict = None) -> str:
    if kb is None:
        kb = load_kb()
    gene = gene.upper()
    for ct in kb["cell_types"]:
        for m in ct["markers"]:
            if m["gene"].upper() == gene:
                return (
                    f"**{m['gene']}** ({m.get('alias', '')}) -- {m['function']}\n"
                    f"> 细胞类型: {ct['type']}\n"
                    f"> 分类: {m.get('category', '未分类')}\n"
                    f"> 上调: {ct['interpretation']['up']}\n"
                    f"> 下调: {ct['interpretation']['down']}"
                )
    return f"知识库中未找到基因 {gene}"


def query_cell_type(cell_type: str, direction: str = "", kb: dict = None) -> str:
    if kb is None:
        kb = load_kb()
    for ct in kb["cell_types"]:
        labels = normalize_cell_type(ct["type"], ct.get("type_en", ""))
        aliases = {
            ct["type"].lower(),
            ct.get("type_en", "").lower(),
            labels["type_en"].lower(),
            labels["abbreviation"].lower(),
        }
        aliases.discard("")
        query = cell_type.strip().lower()
        if (
            query in aliases
            or any(alias in query for alias in aliases)
            or query in ct["type"].lower()
            or query in labels["type_en"].lower()
        ):
            text = (
                f"**{labels['display_name']}**\n"
                f"> {ct['description']}\n"
                f"> 关键功能: {', '.join(ct.get('key_functions', []))}\n"
                f"> 疾病关联: {', '.join(ct.get('disease_links', []))}"
            )
            if direction == "up":
                text += f"\n> **上调解读:** {ct['interpretation']['up']}"
            elif direction == "down":
                text += f"\n> **下调解读:** {ct['interpretation']['down']}"
            else:
                text += f"\n> 上调: {ct['interpretation']['up']}\n> 下调: {ct['interpretation']['down']}"
            return text
    fallback = find_cell_type_label(cell_type)
    if fallback:
        return (
            f"**{fallback['display_name']}**\n"
            "> 该名称来自 NeuroDEG 标准细胞类型词表或 PanglaoDB 补充分类。\n"
            "> 当前 curated 功能知识库中没有更详细的功能描述；"
            "如该类型在本次 DEG 结果中匹配，可在 Cell types 页面查看 marker overlap。"
        )
    return f"知识库中未找到细胞类型: {cell_type}"
