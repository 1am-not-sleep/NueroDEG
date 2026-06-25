"""trace.py - Tool Trace"""
import time

class StepRecord:
    def __init__(self, tool_name, input_snapshot=None, decision=""):
        self.tool = tool_name
        self.status = "running"
        self.input = input_snapshot or {}
        self.output = None
        self.decision = decision
        self.start_time = time.time()
        self.duration_ms = 0
        self.warnings = []

    def finish(self, status="success", output=None):
        self.status = status
        self.output = output
        self.duration_ms = int((time.time() - self.start_time) * 1000)

    def to_dict(self):
        return {
            "tool": self.tool,
            "status": self.status,
            "decision": self.decision,
            "duration_ms": self.duration_ms,
            "warnings": self.warnings,
        }


class TraceRecorder:
    def __init__(self):
        self.steps = []

    def start(self, tool_name, input_snapshot=None, decision=""):
        step = StepRecord(tool_name, input_snapshot, decision)
        self.steps.append(step)
        return step

    def finish(self, step, status="success", output=None):
        step.finish(status, output)

    def to_list(self):
        return [s.to_dict() for s in self.steps]

    def format_table(self):
        lines = ["| Tool | Status | Decision | Duration |",
                 "|:----|:------|:---------|:---------|"]
        icons = {"success": chr(0x2705), "skipped": chr(0x23ED)+chr(0xFE0F),
                 "failed": chr(0x274C), "running": chr(0x23F3)}
        for s in self.steps:
            d = s.to_dict()
            icon = icons.get(d["status"], d["status"])
            dec = d["decision"][:30] if d["decision"] else "-"
            lines.append(f'| {d["tool"]} | {icon} | {dec} | {d["duration_ms"]}ms |')
        return "\n".join(lines)