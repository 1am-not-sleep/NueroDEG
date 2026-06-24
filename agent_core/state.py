"""state.py - Agent State"""


class AgentState:
    def __init__(self, input_file, params=None, run_id="", output_dir=""):
        self.input_file = input_file
        self.params = params or {}
        self.run_id = run_id
        self.output_dir = output_dir
        self.steps = []
        self.input_df = None
        self.filter_result = None
        self.match_result = None
        self.enrichment_result = None
        self.report = None
        self.artifacts = {}
        self.errors = []
        self.warnings = []

    def to_dict(self):
        return {
            "input_file": self.input_file,
            "params": self.params,
            "run_id": self.run_id,
            "output_dir": self.output_dir,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "warnings": self.warnings,
        }
