"""guardrails.py - Safety Guardrails"""
import os

MEDICAL_CLAIM_KEYWORDS = [
    chr(0x6CBB)+chr(0x6108), chr(0x6CBB)+chr(0x7597), chr(0x8BCA)+chr(0x65AD), chr(0x786E)+chr(0x8BCA),
    chr(0x6709)+chr(0x6548)+chr(0x836F)+chr(0x7269), chr(0x7597)+chr(0x6548),
    "cure", "treat", "diagnose", "therapeutic", "efficacy"
]

def check_output_guardrails(report_text):
    warnings = []
    text_lower = report_text.lower()
    for kw in MEDICAL_CLAIM_KEYWORDS:
        if isinstance(kw, str) and kw.lower() in text_lower:
            warnings.append({"level": "warning", "message": f"报告含潜在医学声明关键词: {kw}", "keyword": kw})
    return warnings

def check_input_guardrails(filepath):
    warnings = []
    if not os.path.exists(filepath):
        return [{"level": "error", "message": f"文件不存在: {filepath}"}]
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".csv", ".tsv", ".txt"):
        warnings.append({"level": "warning", "message": f"非标准扩展名: {ext}"})
    return warnings