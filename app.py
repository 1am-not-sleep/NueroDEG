#!/usr/bin/env python3
"""NeuroDEG -- 神经细胞基因表达差异分析 Agent
CLI 主入口（增强版，整合 agent_core）

用法:
    python app.py data/example_neuro_deg.csv
    python app.py data/example_neuro_deg.csv --fc-cutoff 1.5 --p-cutoff 0.01
    python app.py data/example_neuro_deg.csv --use-api --output-dir ./my_results
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.loader import load_deg, summarize_deg
from analysis.filter import filter_degs, get_volcano_data
from analysis.neural_matcher import load_knowledge_base, match_neural_types, match_pathways
from analysis.enrichment import run_enrichment
from analysis.interpreter import render_report
from agent_core.state import AgentState
from agent_core.trace import TraceRecorder
from agent_core.guardrails import check_input_guardrails, check_output_guardrails
from agent_core.quality import QualityEvaluator
from agent_core.memory import save_run


def main():
    parser = argparse.ArgumentParser(description="NeuroDEG -- 神经DEG分析Agent")
    parser.add_argument("input_file", nargs="?", default="", help="DEG文件 (CSV/TSV)")
    parser.add_argument("--fc-cutoff", type=float, default=1.0, help="|log2FC| 阈值")
    parser.add_argument("--p-cutoff", type=float, default=0.05, help="校正p值阈值")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    parser.add_argument("--use-api", action="store_true", help="启用Enrichr API")
    parser.add_argument("--no-vis", action="store_true", help="跳过可视化")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--streamlit", action="store_true", help="启动网页界面")
    args = parser.parse_args()

    if args.streamlit or not args.input_file:
        sp = os.path.join(os.path.dirname(__file__), "streamlit_app.py")
        os.system(f"streamlit run {sp}")
        return

    state = AgentState(args.input_file, {
        "fc_cutoff": args.fc_cutoff,
        "p_cutoff": args.p_cutoff,
        "use_api": args.use_api,
        "no_vis": args.no_vis
    })
    trace = TraceRecorder()

    print()
    print("=" * 55)
    print("  NeuroDEG -- 神经细胞基因表达差异分析")
    print("=" * 55)
    print()

    # Step 1: 输入检查
    print("[1/7] 输入检查...")
    step1 = trace.start("Input Checker", {"file": args.input_file})
    gw_in = check_input_guardrails(args.input_file)
    if any(w["level"] == "error" for w in gw_in):
        print(f"  错误: {gw_in}")
        state.errors.append(str(gw_in))
        trace.finish(step1, "failed")
        return
    try:
        state.input_df = load_deg(args.input_file)
        summarize_deg(state.input_df, args.fc_cutoff, args.p_cutoff)
        trace.finish(step1, "success", {"genes": len(state.input_df)})
    except Exception as e:
        state.errors.append(str(e))
        trace.finish(step1, "failed", {"error": str(e)})
        print(f"  错误: {e}")
        return

    # Step 2: DEG筛选
    print()
    print("[2/7] 筛选差异表达基因...")
    step2 = trace.start("DEG Filter", {"fc_cutoff": args.fc_cutoff, "p_cutoff": args.p_cutoff})
    state.filter_result = filter_degs(state.input_df, args.fc_cutoff, args.p_cutoff)
    trace.finish(step2, "success", state.filter_result["summary"])

    if state.filter_result["summary"]["significant"] == 0:
        msg = "未检测到显著差异基因，请尝试放宽阈值"
        print(f"  [警告] {msg}")
        state.warnings.append(msg)

    # Step 3: 可视化
    if not args.no_vis:
        print()
        print("[3/7] 生成可视化...")
        step3 = trace.start("Visualization", {})
        try:
            from utils.visualizer import plot_volcano, plot_cell_type_bar
            vdata = get_volcano_data(state.input_df, args.fc_cutoff, args.p_cutoff)
            vis_dir = args.output_dir or os.path.join(os.path.dirname(__file__), "output")
            os.makedirs(vis_dir, exist_ok=True)
            plot_volcano(vdata, os.path.join(vis_dir, "volcano.png"), fc_cutoff=args.fc_cutoff, p_cutoff=args.p_cutoff)
            if state.match_result:
                plot_cell_type_bar(state.match_result, os.path.join(vis_dir, "cell_type_bar.png"))
            trace.finish(step3, "success")
        except Exception as e:
            print(f"  [可视化] 跳过: {e}")
            trace.finish(step3, "skipped", {"error": str(e)})

    # Step 4: 条件决策
    sig_count = state.filter_result["summary"]["significant"]
    if sig_count >= 10:
        print()
        print("[4/7] 匹配神经细胞类型...")
        step4 = trace.start("Neural Matcher", {}, decision=f"显著基因{sig_count}>=10")
        kb, g2c = load_knowledge_base()
        state.match_result = match_neural_types(
            state.filter_result["up"], state.filter_result["down"], kb, g2c
        )
        trace.finish(step4, "success", {"matched_types": state.match_result["total_matched_types"]})
    else:
        msg = f"显著基因({sig_count})不足10个，跳过"
        print()
        print(f"[4/7] 跳过: {msg}")
        state.warnings.append(msg)
        step4 = trace.start("Neural Matcher", {}, decision=msg)
        trace.finish(step4, "skipped")
        state.match_result = {"results": [], "total_matched_types": 0}

    # Step 5: 通路富集
    if sig_count >= 10:
        print()
        print("[5/7] 通路富集分析...")
        step5 = trace.start("Enrichment", {}, decision=f"显著基因{sig_count}>=10")
        all_genes = set(state.filter_result["all"]["gene"].tolist())
        state.enrichment_result = run_enrichment(list(all_genes), use_api=args.use_api)
        trace.finish(step5, "success", {"local_pathways": len(state.enrichment_result["local"])})
    else:
        step5 = trace.start("Enrichment", {}, decision="跳过: 显著基因不足")
        trace.finish(step5, "skipped")
        state.enrichment_result = {"local": [], "api": None}

    # Step 6: 报告
    print()
    print("[6/7] 生成分析报告...")
    step6 = trace.start("Report Generator", {})
    state.report = render_report(
        state.filter_result, state.match_result, state.enrichment_result,
        input_file=args.input_file, output_path=None
    )
    trace.finish(step6, "success")

    # Guardrails
    gw_out = check_output_guardrails(state.report)
    if gw_out:
        print()
        print("[Guardrails] 输出检查发现潜在问题:")
        for w in gw_out:
            print(f"  ! {w['message']}")
        state.warnings.extend([w["message"] for w in gw_out])

    # Step 7: 质量评估
    print()
    print("[7/7] 质量评估...")
    qe = QualityEvaluator()
    quality = qe.evaluate(state.filter_result, state.match_result, gw_in + gw_out)
    print(f"  质量等级: {quality['grade']} ({'; '.join(quality['reasons'])})")

    # 保存
    save_run(state, trace, quality, args.output_dir)

    # 输出 Trace
    if not args.quiet:
        print()
        print("=" * 55)
        print("  Agent Trace")
        print("=" * 55)
        print(trace.format_table())
        print()
        print("=" * 55)
        print(f"  质量: {quality['grade']}")
        if state.warnings:
            print("  警告:")
            for w in state.warnings:
                print(f"    ! {w}"[:70])
        print("=" * 55)
        print()


if __name__ == "__main__":
    main()
