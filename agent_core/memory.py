"""memory.py — Run Memory + Manifest 输出"""

import json
import os
import datetime

def make_run_id():
    return "run_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def save_run(state, trace, quality, output_dir=None):
    run_id = make_run_id()
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "results", run_id)
    os.makedirs(output_dir, exist_ok=True)

    if state.report:
        with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
            f.write(state.report)

    if state.filter_result:
        state.filter_result["up"].to_csv(os.path.join(output_dir, "up_genes.csv"), index=False)
        state.filter_result["down"].to_csv(os.path.join(output_dir, "down_genes.csv"), index=False)

    manifest = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "params": state.params,
        "summary": state.filter_result["summary"] if state.filter_result else {},
        "quality": quality,
        "trace": trace.to_list(),
        "errors": state.errors,
        "warnings": state.warnings,
        "input_file": state.input_file
    }
    with open(os.path.join(output_dir, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[memory] 运行记录已保存: {output_dir}")
    return output_dir
