import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
REPORT = BASE.parents[1] / "reports/hw09"
REPORT.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("HW09_MODEL", "qwen3:8b")
URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
CLIENT = requests.Session()

LESSON_TOPICS = {
    "TR01": ("Phase I objectives", "Distinguish early safety and dose finding from later efficacy testing."),
    "TR02": ("Informed consent risks", "Informed consent explains risks and rights; it never guarantees that research is risk-free."),
    "TR03": ("Randomization", "Random allocation uses chance to reduce selection bias."),
    "TR04": ("Placebo", "An inactive placebo need not contain an active medication."),
}


def save(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def call_model(prompt, json_mode=False):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 220,
        },
    }
    if json_mode:
        payload["format"] = "json"

    response = CLIENT.post(URL, json=payload, timeout=300)
    response.raise_for_status()
    output = response.json().get("response", "").strip()
    if not output:
        raise RuntimeError("Ollama returned an empty response")
    return output


def answer_question(question, lessons=None, feedback=None):
    prompt = (
        "You are an accurate clinical research education agent.\n"
        "Answer the user's question briefly and directly in plain English.\n"
        "Distinguish safety, efficacy, consent, and research ethics.\n"
        "Do not invent trial-specific facts.\n"
    )

    if lessons:
        prompt += "\nPreviously learned corrections:\n"
        for lesson in lessons:
            prompt += f"- {lesson['correction']}\n"
            lesson["use_count"] += 1

    if feedback:
        prompt += (
            "\nYour previous answer failed evaluation.\n"
            f"Evaluator feedback: {feedback}\n"
            "Correct the mistake in your next answer.\n"
        )

    prompt += f"\nQuestion: {question}\nAnswer:"
    return call_model(prompt)


def evaluate(question, answer, reference):
    prompt = (
        "You are a separate clinical-trial answer Evaluator Agent.\n"
        "Evaluate the candidate answer against the provided reference.\n"
        "Judge meaning and factual correctness, not exact wording.\n"
        "Reject contradictions, missing central facts, and incorrect yes/no claims.\n"
        "Return ONLY a JSON object with keys 'correct' (boolean) "
        "and 'feedback' (short string).\n\n"
        f"Question: {question}\n"
        f"Reference: {reference['expected']}\n"
        f"Candidate answer: {answer}\n"
    )

    raw = call_model(prompt, json_mode=True)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise RuntimeError(f"Invalid evaluator JSON: {raw}")
        result = json.loads(match.group())

    if not isinstance(result.get("correct"), bool):
        raise RuntimeError(f"Evaluator omitted boolean correctness: {result}")

    feedback = str(result.get("feedback", "")).strip()
    if not feedback:
        feedback = "Check the central facts against the reference."

    return {
        "correct": result["correct"],
        "feedback": feedback,
    }


def run_case(record, reference, mode, lessons=None, force_error=False):
    start = time.perf_counter()
    history = []
    feedback = None
    attempts_allowed = 2 if mode == "repair" else 1

    for attempt in range(1, attempts_allowed + 1):
        if force_error and attempt == 1:
            # Controlled error: intentional, declared, and logged.
            answer = (
                "Yes. Once informed consent is signed, "
                "a clinical trial is guaranteed to have no risks."
            )
            source = "controlled_incorrect_answer"
        else:
            answer = answer_question(
                record["question"],
                lessons=lessons,
                feedback=feedback,
            )
            source = "qwen3"

        judgment = evaluate(
            record["question"], answer, reference
        )
        history.append({
            "attempt": attempt,
            "source": source,
            "answer": answer,
            "correct": judgment["correct"],
            "feedback": judgment["feedback"],
        })

        print(
            f"  attempt={attempt} "
            f"correct={judgment['correct']} "
            f"source={source}",
            flush=True,
        )

        if judgment["correct"]:
            break

        feedback = judgment["feedback"]

    return {
        "id": record["id"],
        "question": record["question"],
        "mode": mode,
        "correct": history[-1]["correct"],
        "attempts": len(history),
        "latency_ms": round(
            (time.perf_counter() - start) * 1000, 2
        ),
        "history": history,
    }


def training():
    records = load(BASE / "training_data.json")
    references = load(BASE / "ground_truth.json")
    results = []
    lessons = []

    print("===== TRAINING AND CONTROLLED REVISION =====", flush=True)

    for record in records:
        print(f"TRAIN {record['id']}", flush=True)
        result = run_case(
            record,
            references[record["id"]],
            mode="repair",
            force_error=(record["id"] == "TR02"),
        )
        results.append(result)
        save(REPORT / "part4_training_results.json", results)

        if any(not h["correct"] for h in result["history"]):
            topic, correction = LESSON_TOPICS[record["id"]]
            lessons.append({
                "lesson_id": f"L{len(lessons) + 1:02d}",
                "source_case": record["id"],
                "failure_pattern": topic,
                "correction": correction,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "use_count": 0,
                "validation_status": "pending",
            })
            save(BASE / "lessons.json", lessons)

        if record["id"] == "TR02":
            print("===== CONTROLLED REVISION SEQUENCE =====")
            print(json.dumps(
                result, indent=2, ensure_ascii=False
            ), flush=True)

    save(BASE / "lessons.json", lessons)
    print(f"Lessons created: {len(lessons)}")
    print("=== PART 4 TRAINING COMPLETE ===", flush=True)


def validation():
    records = load(BASE / "validation_data.json")
    references = load(BASE / "ground_truth.json")
    lessons = load(BASE / "lessons.json")
    results = []

    print("===== LESSON VALIDATION =====", flush=True)

    for record in records:
        print(f"VALIDATE {record['id']} baseline", flush=True)
        baseline = run_case(
            record, references[record["id"]], mode="baseline"
        )

        print(f"VALIDATE {record['id']} lesson", flush=True)
        memory = run_case(
            record,
            references[record["id"]],
            mode="lesson_memory",
            lessons=lessons,
        )

        results.append({
            "id": record["id"],
            "baseline": baseline,
            "lesson_memory": memory,
        })
        save(REPORT / "part4_validation_results.json", results)
        save(BASE / "lessons.json", lessons)

    regressions = sum(
        item["baseline"]["correct"]
        and not item["lesson_memory"]["correct"]
        for item in results
    )
    improvements = sum(
        not item["baseline"]["correct"]
        and item["lesson_memory"]["correct"]
        for item in results
    )

    # Reject lessons when no measurable improvement was observed.
    accepted = bool(lessons) and regressions == 0 and improvements > 0

    for lesson in lessons:
        lesson["validation_status"] = (
            "accepted" if accepted else "rejected"
        )
    save(BASE / "lessons.json", lessons)

    decision = {
        "validation_cases": len(records),
        "regressions": regressions,
        "improvements": improvements,
        "lessons_accepted": accepted,
        "policy": "Accept only with positive improvement and zero regressions",
    }
    save(REPORT / "part4_validation_decision.json", decision)

    print("===== VALIDATION DECISION =====")
    print(json.dumps(decision, indent=2), flush=True)
    print("=== PART 4 VALIDATION COMPLETE ===", flush=True)


def testing():
    records = load(BASE / "test_data.json")
    references = load(BASE / "ground_truth.json")
    lessons = load(BASE / "lessons.json")

    variants = [
        "Baseline",
        "Evaluator Repair",
        "Lesson Memory",
        "Validated Improvement",
    ]
    results = {v: [] for v in variants}

    print("===== HELD-OUT TEST COMPARISON =====", flush=True)

    for variant in variants:
        print(f"\nVARIANT: {variant}", flush=True)

        for record in records:
            print(f"TEST {record['id']}", flush=True)

            selected_lessons = None
            if variant == "Lesson Memory":
                selected_lessons = lessons
            elif variant == "Validated Improvement":
                selected_lessons = [
                    lesson for lesson in lessons
                    if lesson["validation_status"] == "accepted"
                ]

            mode = (
                "repair" if variant == "Evaluator Repair"
                else "baseline" if selected_lessons is None
                else "lesson_memory"
            )

            result = run_case(
                record,
                references[record["id"]],
                mode,
                lessons=selected_lessons,
            )
            results[variant].append(result)

            save(REPORT / "part4_test_results.json", results)
            save(BASE / "lessons.json", lessons)

    summary = []
    for variant, rows in results.items():
        correct = sum(r["correct"] for r in rows)
        summary.append({
            "variant": variant,
            "correct": correct,
            "incorrect": len(rows) - correct,
            "total_attempts": sum(r["attempts"] for r in rows),
            "avg_attempts": round(
                sum(r["attempts"] for r in rows) / len(rows), 2
            ),
            "avg_latency_ms": round(
                sum(r["latency_ms"] for r in rows) / len(rows), 2
            ),
        })

    save(REPORT / "part4_comparison.json", summary)

    print("\n===== FOUR VARIANTS COMPARISON =====")
    for row in summary:
        print(json.dumps(row, ensure_ascii=False), flush=True)

    print("PASS: 4 held-out test questions")
    print("PASS: 4 variants compared")
    print("=== PART 4 TEST COMPLETE ===", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=["train", "validate", "test"],
    )
    args = parser.parse_args()

    print("Student: Haozhe Wang", flush=True)
    print(f"DATA 260 HW9 Part 4 - {args.stage}", flush=True)
    print(f"Model: {MODEL}", flush=True)

    if args.stage == "train":
        training()
    elif args.stage == "validate":
        validation()
    else:
        testing()
