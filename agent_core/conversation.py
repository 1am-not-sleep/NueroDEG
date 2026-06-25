"""Conversational tool router for the NeuroDEG analysis agent."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field

from agent_core.cell_types import find_cell_type_label
from agent_core.chat import query_cell_type, query_gene
from agent_core.orchestrator import AnalysisRun, AnalysisRunError, run_analysis
from agent_core.qa_buttons import analysis_summary, drug_association, pathway_insights


@dataclass
class ConversationAction:
    tool: str
    reason: str
    observation: str
    status: str = "success"


@dataclass
class ConversationReply:
    content: str
    actions: list[ConversationAction] = field(default_factory=list)
    updated_run: AnalysisRun | None = None


def _contains(text, *terms):
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _extract_thresholds(prompt, current_run, default_fc=1.0, default_p=0.05):
    fc_cutoff = (
        current_run.state.params.get("fc_cutoff", default_fc)
        if current_run
        else default_fc
    )
    p_cutoff = (
        current_run.state.params.get("p_cutoff", default_p)
        if current_run
        else default_p
    )

    fc_match = re.search(
        r"(?:log2fc|fold\s*change|fc|倍数|阈值)[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)",
        prompt,
        flags=re.IGNORECASE,
    )
    p_match = re.search(
        r"(?:padj|p_adj|adjusted\s*p|fdr|p\s*value|p值)[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)",
        prompt,
        flags=re.IGNORECASE,
    )
    if fc_match:
        fc_cutoff = float(fc_match.group(1))
    if p_match:
        p_cutoff = float(p_match.group(1))
    return fc_cutoff, p_cutoff


def _action(language, tool, reason_zh, reason_en, observation_zh, observation_en, status="success"):
    return ConversationAction(
        tool,
        reason_zh if language == "zh" else reason_en,
        observation_zh if language == "zh" else observation_en,
        status=status,
    )


def _is_analysis_request(prompt):
    normalized = prompt.strip().lower()
    chinese_actions = (
        "重新分析",
        "开始分析",
        "分析当前",
        "分析这个",
        "分析数据",
        "分析文件",
        "运行分析",
        "执行分析",
        "按这个阈值",
        "用这个阈值",
    )
    english_actions = (
        "analyze",
        "analyse",
        "rerun",
        "run analysis",
        "re-run",
    )
    return any(term in normalized for term in chinese_actions + english_actions)


def _analysis_reply(run, language):
    summary = run.state.filter_result["summary"]
    if language == "zh":
        return (
            f"分析完成。共检查 {summary['total_genes']} 个基因，筛选出 "
            f"{summary['significant']} 个显著 DEG（{summary['up']} 上调，"
            f"{summary['down']} 下调），匹配到 "
            f"{run.state.match_result['total_matched_types']} 种细胞类型和 "
            f"{len(run.state.enrichment_result.get('go', []))} 条 GO 结果。"
        )
    return (
        f"Analysis completed for {summary['total_genes']} genes. The agent detected "
        f"{summary['significant']} significant DEGs ({summary['up']} up, "
        f"{summary['down']} down), "
        f"{run.state.match_result['total_matched_types']} cell-type signals, and "
        f"{len(run.state.enrichment_result.get('go', []))} GO results."
    )


def _matched_cell_type_reply(prompt, run, language):
    for item in run.state.match_result.get("results", []):
        aliases = {
            item.get("type", "").lower(),
            item.get("type_zh", "").lower(),
            item.get("type_en", "").lower(),
            item.get("abbreviation", "").lower(),
        }
        aliases.discard("")
        if any(alias in prompt.lower() for alias in aliases):
            direction = "up" if item["up_count"] > item["down_count"] else "down"
            knowledge = query_cell_type(
                item.get("abbreviation") or item.get("type_en") or item["type"],
                direction=direction,
            )
            if language == "zh":
                result = (
                    f"{knowledge}\n\n本次数据匹配到 {item['matched']}/{item['total_markers']} "
                    f"个 marker：上调 {item['up_count']} 个、下调 {item['down_count']} 个。"
                )
            else:
                result = (
                    f"**{item.get('display_name', item['type'])}**\n\n"
                    f"This run matched {item['matched']}/{item['total_markers']} markers "
                    f"({item['up_count']} up and {item['down_count']} down). "
                    f"Up markers: {item['up_genes'] or 'None'}. "
                    f"Down markers: {item['down_genes'] or 'None'}."
                )
            return result, item.get("display_name", item["type"])

    label = find_cell_type_label(prompt)
    if label:
        return query_cell_type(label["abbreviation"]), label["display_name"]
    return None, None


def _gene_reply(prompt, run, language):
    significant = {
        gene.upper(): row
        for _, row in run.state.filter_result["all"].iterrows()
        for gene in [str(row["gene"])]
    }
    candidates = re.findall(r"\b[A-Za-z][A-Za-z0-9-]{1,15}\b", prompt)
    for token in candidates:
        upper = token.upper()
        if upper in significant:
            row = significant[upper]
            knowledge = query_gene(upper)
            if language == "zh":
                return (
                    f"{knowledge}\n\n本次结果：log2FC={row['log2fc']:.2f}，"
                    f"padj={row['padj']:.2e}，方向={row['direction']}。"
                ), upper
            return (
                f"**{upper}** is significant in this run: log2FC={row['log2fc']:.2f}, "
                f"adjusted p={row['padj']:.2e}, direction={row['direction']}."
            ), upper
    return None, None


def handle_message(
    prompt,
    current_run=None,
    input_file=None,
    language="zh",
    fc_cutoff=1.0,
    p_cutoff=0.05,
    use_api=False,
):
    """Plan and execute one conversational agent turn."""
    actions: list[ConversationAction] = []
    wants_analysis = _is_analysis_request(prompt)

    if wants_analysis:
        source_file = current_run.state.input_file if current_run else input_file
        if not source_file:
            message = (
                "请先选择示例数据或上传 DEG 文件。"
                if language == "zh"
                else "Select example data or upload a DEG file first."
            )
            return ConversationReply(
                message,
                [
                    _action(
                        language,
                        "Input Context",
                        "分析前先确认数据来源。",
                        "Resolve the data source before analysis.",
                        "没有可用的输入文件。",
                        "No input file is available.",
                        status="blocked",
                    )
                ],
            )

        requested_fc, requested_p = _extract_thresholds(
            prompt,
            current_run,
            default_fc=fc_cutoff,
            default_p=p_cutoff,
        )
        api_requested = use_api or _contains(prompt, "enrichr", "在线富集", "online enrichment")
        actions.append(
            _action(
                language,
                "Planner",
                "用户要求执行分析或调整筛选阈值。",
                "The user requested an analysis or threshold change.",
                f"计划使用 |log2FC|>{requested_fc}、调整后 p<{requested_p} 运行 DEG 分析。",
                f"Plan: run DEG analysis with abs(log2FC)>{requested_fc}, adjusted p<{requested_p}.",
            )
        )
        try:
            output_dir = tempfile.mkdtemp(prefix="neurodeg_agent_turn_")
            new_run = run_analysis(
                source_file,
                fc_cutoff=requested_fc,
                p_cutoff=requested_p,
                output_dir=output_dir,
                use_api=api_requested,
                generate_visuals=True,
                quiet=True,
                report_language=language,
            )
        except AnalysisRunError as exc:
            actions.append(
                _action(
                    language,
                    "NeuroDEG Analysis",
                    "执行用户要求的分析。",
                    "Execute the requested analysis.",
                    str(exc),
                    str(exc),
                    status="failed",
                )
            )
            return ConversationReply(
                f"{'分析失败' if language == 'zh' else 'Analysis failed'}: {exc}",
                actions,
            )

        summary = new_run.state.filter_result["summary"]
        actions.append(
            _action(
                language,
                "NeuroDEG Analysis",
                "依次调用输入校验、DEG 筛选、细胞类型匹配、富集、绘图和报告工具。",
                "Execute validation, DEG filtering, cell matching, enrichment, plots, and report tools.",
                f"得到 {summary['significant']} 个显著基因；质量等级为 {new_run.quality['grade']}。",
                f"{summary['significant']} significant genes; quality={new_run.quality['grade']}.",
            )
        )
        return ConversationReply(
            _analysis_reply(new_run, language),
            actions,
            updated_run=new_run,
        )

    if current_run is None:
        return ConversationReply(
            (
                "我还没有分析结果。你可以说“分析当前数据”或“用 log2FC 1.5、padj 0.01 分析”。"
                if language == "zh"
                else "No analysis is available yet. Try: “Analyze the current data” or "
                "“Analyze with log2FC 1.5 and padj 0.01.”"
            ),
            [
                _action(
                    language,
                    "Planner",
                    "判断该问题是否依赖已有分析上下文。",
                    "Determine whether the question requires existing analysis context.",
                    "当前没有可供查询的分析结果。",
                    "The requested context is not available.",
                    status="blocked",
                )
            ],
        )

    if _contains(prompt, "summary", "总结", "概括", "概览", "多少"):
        actions.append(
            _action(
                language,
                "Analysis Summary",
                "用户要求汇总当前结构化结果。",
                "Summarize the current structured outputs.",
                "已读取 DEG 数量、细胞类型匹配、GO 结果和质量等级。",
                "Read DEG counts, cell-type matches, GO results, and quality grade.",
            )
        )
        return ConversationReply(
            analysis_summary(
                current_run.state.filter_result,
                current_run.state.match_result,
                current_run.state.enrichment_result,
                current_run.quality,
                input_file=current_run.state.input_file,
                fc_cutoff=current_run.state.params["fc_cutoff"],
                p_cutoff=current_run.state.params["p_cutoff"],
                language=language,
            ),
            actions,
        )

    if _contains(prompt, "通路", "pathway", "go term", "go结果", "enrichment"):
        actions.append(
            _action(
                language,
                "Pathway Interpreter",
                "问题涉及富集的生物过程或通路。",
                "The question asks about enriched biological processes.",
                f"读取到 {len(current_run.state.enrichment_result.get('go', []))} 条 GO 结果。",
                f"Retrieved {len(current_run.state.enrichment_result.get('go', []))} GO results.",
            )
        )
        return ConversationReply(
            pathway_insights(
                current_run.state.enrichment_result.get("go", []),
                current_run.state.match_result,
                current_run.state.enrichment_result.get("local", []),
                language=language,
            ),
            actions,
        )

    if _contains(prompt, "药", "drug", "target", "靶点"):
        actions.append(
            _action(
                language,
                "Drug-Target Matcher",
                "问题要求查找通路相关药物或靶点线索。",
                "The question asks for pathway-linked drug-target references.",
                "已将富集通路与本地药物靶点知识库匹配。",
                "Matched enriched pathway names against the local drug-target knowledge base.",
            )
        )
        return ConversationReply(
            drug_association(
                current_run.state.enrichment_result.get("go", []),
                current_run.state.enrichment_result.get("local", []),
                language=language,
            ),
            actions,
        )

    if _contains(prompt, "局限", "限制", "风险", "limitation", "caveat", "risk"):
        actions.append(
            _action(
                language,
                "Safety Guardrail",
                "用户要求说明不确定性和解释边界。",
                "The user asks for uncertainty and limitations.",
                "已检查 DEG、marker overlap、bulk 组织和因果推断的限制。",
                "Retrieved interpretation boundaries for DEG, marker overlap, and bulk tissue.",
            )
        )
        content = (
            "主要局限：\n\n"
            "1. Cell type 结果来自 marker overlap，不是细胞比例反卷积。\n"
            "2. Bulk DEG 可能同时反映细胞组成和细胞内表达变化。\n"
            "3. 富集结果是统计关联，不证明因果机制。\n"
            "4. 转录变化不等同于蛋白或功能变化，仍需实验验证。"
            if language == "zh"
            else (
                "Main limitations:\n\n"
                "1. Cell-type results use marker overlap, not deconvolution.\n"
                "2. Bulk DEG signals may reflect both composition and within-cell changes.\n"
                "3. Enrichment is associative and does not establish causality.\n"
                "4. Transcript changes do not prove protein or functional changes."
            )
        )
        return ConversationReply(content, actions)

    if _contains(prompt, "trace", "步骤", "为什么", "decision", "怎么分析"):
        actions.append(
            _action(
                language,
                "Trace Reader",
                "用户要求解释 Agent 如何得到当前结果。",
                "Explain how the agent reached the current output.",
                f"读取到 {len(current_run.trace.steps)} 条工具执行记录。",
                f"Retrieved {len(current_run.trace.steps)} tool execution records.",
            )
        )
        return ConversationReply(current_run.trace.format_table(), actions)

    cell_reply, cell_name = _matched_cell_type_reply(prompt, current_run, language)
    if cell_reply:
        actions.append(
            _action(
                language,
                "Cell-Type Interpreter",
                "问题中识别到神经细胞类型名称或缩写。",
                "A neural cell type or abbreviation was detected in the question.",
                f"已读取 {cell_name} 的 marker overlap 和知识库解释。",
                f"Retrieved marker overlap and knowledge for {cell_name}.",
            )
        )
        return ConversationReply(cell_reply, actions)

    gene_reply, gene_name = _gene_reply(prompt, current_run, language)
    if gene_reply:
        actions.append(
            _action(
                language,
                "Gene Inspector",
                "问题中识别到本次结果里的显著基因。",
                "A significant gene symbol was detected in the question.",
                f"已读取 {gene_name} 的 DEG 统计和 marker 知识。",
                f"Retrieved DEG statistics and marker knowledge for {gene_name}.",
            )
        )
        return ConversationReply(gene_reply, actions)

    actions.append(
        _action(
            language,
            "Planner",
            "将问题与当前可用的 NeuroDEG 工具进行匹配。",
            "Classify the request against available NeuroDEG tools.",
            "没有识别到高置信度的工具路由。",
            "No high-confidence tool route was identified.",
            status="review",
        )
    )
    help_text = (
        "我可以执行或回答：\n\n"
        "- “用 log2FC 1.5、padj 0.01 重新分析”\n"
        "- “解释 MG / Astrocyte / OPC”\n"
        "- “GFAP 在本次结果中如何变化？”\n"
        "- “总结最显著的 GO 通路”\n"
        "- “有哪些局限性？”\n"
        "- “展示 Agent 的分析步骤”"
        if language == "zh"
        else (
            "I can handle requests such as:\n\n"
            "- “Reanalyze with log2FC 1.5 and padj 0.01”\n"
            "- “Explain MG / Astrocyte / OPC”\n"
            "- “How did GFAP change in this run?”\n"
            "- “Summarize the top GO pathways”\n"
            "- “What are the limitations?”\n"
            "- “Show the agent decision trace”"
        )
    )
    return ConversationReply(help_text, actions)
