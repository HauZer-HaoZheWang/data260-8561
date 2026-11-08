import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

training = [
    {"id": "TR01", "question": "What is the main purpose of Phase I clinical trials?"},
    {"id": "TR02", "question": "Does informed consent guarantee that a clinical trial has no risks?"},
    {"id": "TR03", "question": "What does randomization mean in a clinical trial?"},
    {"id": "TR04", "question": "Is a placebo always an active medication?"},
]

validation = [
    {"id": "VA01", "question": "Are Phase I clinical trials primarily designed to prove treatment effectiveness?"},
    {"id": "VA02", "question": "Can a participant withdraw from a clinical trial after giving consent?"},
    {"id": "VA03", "question": "Does random assignment allow researchers to choose groups based on personal preference?"},
    {"id": "VA04", "question": "Does a placebo necessarily contain the experimental drug?"},
]

test = [
    {"id": "TE01", "question": "What is the primary goal of Phase III clinical trials?"},
    {"id": "TE02", "question": "Can informed consent be withdrawn during a clinical study?"},
    {"id": "TE03", "question": "Why is randomization used in controlled clinical trials?"},
    {"id": "TE04", "question": "Can an inactive placebo be used as a comparison in clinical research?"},
]

reference = {
    "TR01": {
        "expected": "Phase I primarily evaluates safety, tolerability, and dosage.",
        "required_concepts": ["safety", "dose"]
    },
    "TR02": {
        "expected": "No. Informed consent explains risks but does not eliminate them.",
        "required_concepts": ["no", "risk"]
    },
    "TR03": {
        "expected": "Randomization assigns participants to study groups by chance to reduce selection bias.",
        "required_concepts": ["chance", "bias"]
    },
    "TR04": {
        "expected": "No. A placebo may be inactive and need not contain an active medication.",
        "required_concepts": ["no", "inactive"]
    },
    "VA01": {
        "expected": "No. Phase I primarily focuses on safety and dosage, not proving effectiveness.",
        "required_concepts": ["no", "safety"]
    },
    "VA02": {
        "expected": "Yes. Participants may withdraw consent and leave a clinical trial.",
        "required_concepts": ["yes", "withdraw"]
    },
    "VA03": {
        "expected": "No. Random assignment uses chance rather than researcher preference.",
        "required_concepts": ["no", "chance"]
    },
    "VA04": {
        "expected": "No. A placebo need not contain the experimental drug.",
        "required_concepts": ["no", "placebo"]
    },
    "TE01": {
        "expected": "Phase III evaluates effectiveness and safety in larger groups, often comparing with standard care or placebo.",
        "required_concepts": ["effectiveness", "safety"]
    },
    "TE02": {
        "expected": "Yes. Participants can withdraw informed consent during the study.",
        "required_concepts": ["yes", "withdraw"]
    },
    "TE03": {
        "expected": "Randomization reduces selection bias and makes groups more comparable.",
        "required_concepts": ["bias", "groups"]
    },
    "TE04": {
        "expected": "Yes. An inactive placebo can serve as a comparison when ethically appropriate.",
        "required_concepts": ["yes", "placebo"]
    }
}

for filename, records in [
    ("training_data.json", training),
    ("validation_data.json", validation),
    ("test_data.json", test)
]:
    (ROOT / filename).write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n"
    )

(ROOT / "ground_truth.json").write_text(
    json.dumps(reference, indent=2, ensure_ascii=False) + "\n"
)

(ROOT / "lessons.json").write_text("[]\n")

for filename in [
    "training_data.json",
    "validation_data.json",
    "test_data.json"
]:
    records = json.loads((ROOT / filename).read_text())

    assert all(
        set(record.keys()) == {"id", "question"}
        for record in records
    )

all_ids = [
    record["id"]
    for record in training + validation + test
]

assert len(all_ids) == len(set(all_ids)) == 12
assert set(all_ids) == set(reference)

print("Student: Haozhe Wang")
print("DATA 260 HW9 - Part 4")
print("PASS: Training dataset - 4 questions")
print("PASS: Validation dataset - 4 questions")
print("PASS: Test dataset - 4 questions")
print("PASS: Ground truth stored separately")
print("PASS: Input datasets contain no answers")
print("PASS: Lesson memory initialized")
print("=== PART 4 DATASETS READY ===")
