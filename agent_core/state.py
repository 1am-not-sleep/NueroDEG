"""state.py - Agent State"""
class AgentState:
    def __init__(self, input_file, params=None):
        self.input_file = input_file
        self.params = params or {}
        self.steps = []
        self.input_df = None
        self.filter_result = None
        self.match_result = None
        self.enrichment_result = None
        self.report = None
        self.errors = []
        self.warnings = []

    def to_dict(self):
        return {
            "input_file": self.input_file,
            "params": self.params,
            "errors": self.errors,
            "warnings": self.warnings,
        }