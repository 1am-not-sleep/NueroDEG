#!/usr/bin/env python3
"""NeuroDEG command-line entrypoint."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from agent_core.orchestrator import AnalysisRunError, run_analysis


ROOT = Path(__file__).resolve().parent


def build_parser():
    parser = argparse.ArgumentParser(description="NeuroDEG neural DEG analysis agent")
    parser.add_argument("input_file", nargs="?", default="", help="DEG file (CSV/TSV)")
    parser.add_argument("--fc-cutoff", type=float, default=1.0, help="Absolute log2FC cutoff")
    parser.add_argument("--p-cutoff", type=float, default=0.05, help="Adjusted p-value cutoff")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--use-api", action="store_true", help="Enable optional Enrichr enrichment")
    parser.add_argument("--no-vis", action="store_true", help="Skip plot generation")
    parser.add_argument("--quiet", action="store_true", help="Reduce terminal output")
    parser.add_argument("--streamlit", action="store_true", help="Launch the Streamlit interface")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.streamlit or not args.input_file:
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(ROOT / "streamlit_app.py")]
        )

    if not args.quiet:
        print()
        print("=" * 58)
        print("  NeuroDEG - neural differential-expression analysis agent")
        print("=" * 58)

    try:
        result = run_analysis(
            input_file=args.input_file,
            fc_cutoff=args.fc_cutoff,
            p_cutoff=args.p_cutoff,
            output_dir=args.output_dir,
            use_api=args.use_api,
            generate_visuals=not args.no_vis,
            quiet=args.quiet,
        )
    except AnalysisRunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = result.state.filter_result["summary"]
    print()
    print(f"Run ID: {result.state.run_id}")
    print(f"Total genes: {summary['total_genes']}")
    print(f"Significant genes: {summary['significant']}")
    print(f"Up-regulated genes: {summary['up']}")
    print(f"Down-regulated genes: {summary['down']}")
    print(f"Matched cell types: {result.state.match_result['total_matched_types']}")
    print(f"GO pathways: {len(result.state.enrichment_result.get('go', []))}")
    print(f"Quality grade: {result.quality['grade']}")
    print(f"Output directory: {result.output_dir}")

    if result.state.warnings:
        print("Warnings:")
        for warning in result.state.warnings:
            print(f"- {warning}")

    if not args.quiet:
        print()
        print("Agent Trace")
        print(result.trace.format_table())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
