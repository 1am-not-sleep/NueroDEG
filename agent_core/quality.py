"""quality.py - Quality Evaluator"""
class QualityEvaluator:
    def __init__(self):
        self.grade = "blocked"
        self.reasons = []

    def evaluate(self, filter_result, match_result, guardrail_warnings):
        summary = filter_result.get("summary", {})
        sig = summary.get("significant", 0)
        matched = match_result.get("total_matched_types", 0)
        errors = [w for w in guardrail_warnings if w.get("level") == "error"]
        warnings = [w for w in guardrail_warnings if w.get("level") == "warning"]

        if errors or sig <= 5:
            self.grade = "blocked"
            self.reasons = []
            if errors: self.reasons.append("存在严重错误")
            if sig <= 5: self.reasons.append(f"显著基因过少({sig})")
        elif sig < 10 or matched < 1 or warnings:
            self.grade = "review"
            self.reasons = []
            if sig < 10: self.reasons.append(f"显著基因较少({sig})")
            if matched < 1: self.reasons.append("未匹配到神经细胞类型")
            if warnings: self.reasons.append(f"存在{len(warnings)}条guardrail警告")
        else:
            self.grade = "ready"
            self.reasons = ["输入、细胞类型匹配与安全检查均达到展示标准"]

        return {"grade": self.grade, "reasons": self.reasons}
