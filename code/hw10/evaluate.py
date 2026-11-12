"""Run Part 2 and Part 3 GEval evaluations from frozen JSON cases."""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from local_judge import OllamaJudge
from hw10.trace import span

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "reports/hw10/data"
TIMEOUT = int(os.getenv("HW10_JUDGE_TIMEOUT", "180"))

def metric(name, criteria, params):
    return GEval(name=name, criteria=criteria, evaluation_params=params,
                 model=OllamaJudge(timeout=TIMEOUT), strict_mode=False)

def score_one(m, case, actual=None):
    actual_text = actual if actual is not None else case.get("draft", "")
    if not actual_text or not actual_text.strip():
        return 1.0, "Empty output; assigned the minimum 1-5 score."
    test = LLMTestCase(input=case.get("question", ""),
                       actual_output=actual_text,
                       expected_output=case.get("reference", ""))
    m.measure(test)
    # GEval returns 0..1. Convert to the required 1..5 scale.
    score = 1.0 + 4.0 * float(m.score)
    return round(score, 4), m.reason

def run():
    cases = json.loads((DATA / "eval_cases.json").read_text(encoding="utf-8"))
    writer = metric("Writer Helpfulness",
               "Score whether the draft is accurate, useful, relevant, and complete for the question. 1 is very poor and 5 is excellent.",
               [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT])
    plan = metric("Plan Quality", "Score whether the plan is useful, logically ordered, and appropriate for answering the question. 1 is very poor and 5 is excellent.",
                   [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT])
    final = metric("Final Helpfulness", "Score whether the final answer is accurate, relevant, complete, and helpful for the question. 1 is very poor and 5 is excellent.",
                   [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT])
    out = DATA / "judge_results.jsonl"
    stage_out = DATA / "evaluation_results.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for repeat in (1, 2, 3):
            for case in cases:
                try:
                    with span(case.get("correlation_id", case["case_id"]), "evaluation", repeat=repeat):
                        score, reason = score_one(writer, case)
                    f.write(json.dumps({"case_id": case["case_id"], "repeat": repeat,
                                    "judge_score": score, "reason": reason,
                                    "judge_model": writer.model.get_model_name()}, ensure_ascii=False) + "\n")
                except Exception as exc:
                    f.write(json.dumps({"case_id": case["case_id"], "repeat": repeat,
                                        "error": repr(exc)}, ensure_ascii=False) + "\n")
    with stage_out.open("w", encoding="utf-8") as f:
        for case in cases:
            try:
                plan_score, plan_reason = score_one(plan, case, case.get("plan", ""))
                writer_score, writer_reason = score_one(writer, case, case.get("draft", ""))
                final_score, final_reason = score_one(final, case, case.get("final", ""))
                row = {"case_id": case["case_id"], "trace_id": case.get("correlation_id"),
                       "plan_score": plan_score, "plan_reason": plan_reason,
                       "writer_score": writer_score, "writer_reason": writer_reason,
                       "final_score": final_score, "final_reason": final_reason,
                       "final_minus_draft": round(final_score - writer_score, 4)}
            except Exception as exc:
                row = {"case_id": case["case_id"], "trace_id": case.get("correlation_id"), "error": repr(exc)}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {out}")

if __name__ == "__main__": run()
