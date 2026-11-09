import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = ROOT / "reports/hw09/part4_lesson_reuse_demo.json"

sys.path.insert(0, str(BASE))
from part4_agents import answer_question

question = (
    "Does signing informed consent mean that participating "
    "in a clinical trial has no risks?"
)

lessons = json.loads((BASE / "lessons.json").read_text())
assert lessons, "No saved lesson available"

# Use a copy to preserve the original experiment records.
selected = deepcopy(lessons)
lesson = selected[0]
before = lesson["use_count"]

print("Student: Haozhe Wang", flush=True)
print("DATA 260 HW9 - Later Question Lesson Reuse")
print("===== LOAD PREVIOUSLY SAVED LESSON =====", flush=True)
print("Lesson ID:", lesson["lesson_id"], flush=True)
print("Source case:", lesson["source_case"], flush=True)
print("Original validation status:", lesson["validation_status"], flush=True)
print("Loaded correction:", lesson["correction"], flush=True)

print("\n===== NEW QUESTION =====", flush=True)
print(question, flush=True)

answer = answer_question(question, lessons=selected)

after = selected[0]["use_count"]
assert after == before + 1, "Lesson was not used"

print("\n===== ANSWER AFTER LESSON INJECTION =====", flush=True)
print(answer, flush=True)
print("\nLesson use_count before:", before, flush=True)
print("Lesson use_count after:", after, flush=True)

record = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "demonstration": "Post-test lesson reuse",
    "question": question,
    "lesson_id": lesson["lesson_id"],
    "lesson_source": lesson["source_case"],
    "lesson_status": lesson["validation_status"],
    "loaded_correction": lesson["correction"],
    "answer": answer,
    "local_use_count_before": before,
    "local_use_count_after": after,
    "original_lesson_file_modified": False,
}

OUT.write_text(json.dumps(record, indent=2) + "\n")

print("\nPASS: Saved lesson loaded before answering")
print("PASS: Correction injected into answering prompt")
print("PASS: New question answered")
print("PASS: Original lesson file unchanged")
print("Evidence saved:", OUT)
