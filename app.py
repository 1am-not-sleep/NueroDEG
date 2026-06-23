#!/usr/bin/env python3
"""NeuroDEG — 神经细胞基因表达差异分析 Agent
主入口脚本

用法:
    python app.py input/disease_vs_control.csv
    python app.py input/disease_vs_control.csv --fc-cutoff 1.5 --p-cutoff 0.01
    python app.py input/disease_vs_control.csv --use-api
"""

import sys
import os
import argparse

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.loader import load_deg, summarize_deg
from analysis.filter import filter_degs, get_volcano_data
from analysis.neural_matcher import load_knowledge_base, match_neural_types, match_pathways
from analysis.enrichment import run_enrichment
from analysis.interpreter import generate_interpretations, render_report


def main():
    parser = argparse.ArgumentParser(
        description="NeuroDEG — 神经细胞基因表达差异分析 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python app.py input/example.csv
  python app.py input/example.csv --fc-cutoff 1.5 --p-cutoff 0.01
  python app.py input/example.csv --use-api --output-dir ./my_results
        """
    )
    parser.add_argument("input_file", help="DEG文件 (CSV或TSV格式)")
    parser.add_argument("--fc-cutoff", type=float, default=1.0,
                        help="|log2FC| 阈值 (默认: 1.0)")
    parser.add_argument("--p-cutoff", type=float, default=0.05,
                        help="校正p值阈值 (默认: 0.05)")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录 (默认: output/)")
    parser.add_argument("--use-api", action="store_true",
                        help="启用Enrichr API在线富集分析")
    parser.add_argument("--no-vis", action="store_true",
                        help="跳过可视化图表生成")
    
    args = parser.parse_args()
    
    # ========================================
    # 步骤 1: 加载DEG数据
    # ========================================
    print("\n" + "="*55)
    print("  NeuroDEG — 神经细胞基因表达差异分析")
    print("="*55 + "\n")
    
    print("[1/5] 加载DEG文件...")
    df = load_deg(args.input_file)
    summarize_deg(df)
    
    # ========================================
    # 步骤 2: 筛选差异基因
    # ========================================
    print("\n[2/5] 筛选差异表达基因...")
    filter_result = filter_degs(df, args.fc_cutoff, args.p_cutoff)
    
    if filter_result["summary"]["significant"] == 0:
        print("\n[警告] 未检测到显著差异基因，请尝试放宽筛选阈值")
        return
    
    # ========================================
    # 步骤 3: 神经细胞类型匹配
    # ========================================
    print("\n[3/5] 匹配神经细胞类型...")
    kb, gene_to_cell = load_knowledge_base()
    match_result = match_neural_types(
        filter_result["up"],
        filter_result["down"],
        kb, gene_to_cell
    )
    
    # ========================================
    # 步骤 4: 通路分析
    # ========================================
    print("\n[4/5] 通路富集分析...")
    all_sig_genes = set(filter_result["all"]["gene"].tolist())
    
    # 传递参数
    enrichment_result = run_enrichment(list(all_sig_genes), use_api=args.use_api)
    pathway_result = enrichment_result["local"]
    
    # ========================================
    # 步骤 5: 生成报告
    # ========================================
    print("\n[5/5] 生成分析报告...")
    
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
    
    report = render_report(
        filter_result, match_result, pathway_result,
        input_file=args.input_file,
        output_path=None
    )
    
    # ========================================
    # 可视化
    # ========================================
    if not args.no_vis:
        try:
            from utils.visualizer import plot_volcano, plot_cell_type_bar
            
            volcano_data = get_volcano_data(df)
            plot_volcano(
                volcano_data,
                output_path=os.path.join(output_dir, "volcano.png"),
                title=f"Volcano Plot (|log2FC|>{args.fc_cutoff}, padj<{args.p_cutoff})"
            )
            
            plot_cell_type_bar(
                match_result,
                output_path=os.path.join(output_dir, "cell_type_bar.png")
            )
        except ImportError as e:
            print(f"[可视化] 跳过图表生成 (缺少依赖: {e})")
        except Exception as e:
            print(f"[可视化] 图表生成失败: {e}")
    
    print("\n" + "="*55)
    print("  分析完成!")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
