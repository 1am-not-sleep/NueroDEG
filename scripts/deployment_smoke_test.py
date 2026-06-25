"""Validate files and execute a minimal cloud-style NeuroDEG run."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_core.orchestrator import run_analysis

REQUIRED_FILES = [
    ROOT / "streamlit_app.py",
    ROOT / "requirements.txt",
    ROOT / ".streamlit" / "config.toml",
    ROOT / "core" / "knowledge_base.json",
    ROOT / "core" / "go_enrichment_cache.json",
    ROOT / "core" / "panglaodb_supplement.json",
    ROOT / "data" / "example_neuro_deg.csv",
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        print("Missing deployment files:")
        for path in missing:
            print(f"- {path}")
        return 1

    with tempfile.TemporaryDirectory(prefix="neurodeg_deploy_test_") as output_dir:
        run = run_analysis(
            ROOT / "data" / "example_neuro_deg.csv",
            output_dir=output_dir,
            generate_visuals=False,
            quiet=True,
            report_language="en",
        )
        if run.quality["grade"] != "ready":
            print(f"Unexpected quality grade: {run.quality['grade']}")
            return 1
        if not run.state.report.startswith("# NeuroDEG Differential-Expression Report"):
            print("English report was not generated.")
            return 1

    print("Deployment smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
