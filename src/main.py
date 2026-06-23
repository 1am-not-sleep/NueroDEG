from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import run_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NeuroDEG-Agent on a DEG CSV file.")
    parser.add_argument("csv", nargs="?", default="data/example_neuro_deg.csv", help="Input DEG CSV path.")
    parser.add_argument("--comparison", default="Alzheimer's disease cortex vs control cortex")
    parser.add_argument("--species", default="human", choices=["human", "mouse"])
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--logfc-cutoff", type=float, default=1.0)
    parser.add_argument("--padj-cutoff", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.csv)
    df = pd.read_csv(input_path)
    result = run_agent(
        df,
        comparison_info=args.comparison,
        species=args.species,
        output_dir=args.output_dir,
        logfc_cutoff=args.logfc_cutoff,
        padj_cutoff=args.padj_cutoff,
    )

    if not result.success:
        print(f"ERROR: {result.message}")
        return 1

    assert result.deg_summary is not None
    print(result.message)
    print(f"Run ID: {result.run_id}")
    print(f"Total genes: {result.deg_summary.total_genes}")
    print(f"Up-regulated genes: {result.deg_summary.up_count}")
    print(f"Down-regulated genes: {result.deg_summary.down_count}")
    if result.state:
        print(f"Agent confidence: {result.state.confidence}")
    if result.quality:
        print(f"Quality grade: {result.quality.grade} ({result.quality.score})")
    print("Output files:")
    for name, path in result.output_paths.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
