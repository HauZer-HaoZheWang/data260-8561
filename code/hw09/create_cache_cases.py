import json
from pathlib import Path

seeds = [
    "What is informed consent in a clinical trial?",
    "What happens during Phase I of a clinical trial?",
    "What is a placebo in a clinical trial?",
    "What is randomization in a clinical trial?",
    "What are inclusion criteria in a clinical trial?",
    "How is drug safety measured in a clinical trial?",
    "What does a clinical trial sponsor do?",
    "What is an adverse event in a clinical trial?",
    "How do participants enroll in a clinical trial?",
    "Why are clinical trials registered publicly?",
]

paraphrases = [
    "Explain informed consent for someone joining a clinical study.",
    "What is the purpose of the first phase of clinical testing?",
    "Explain the meaning of placebo in medical research.",
    "How are people randomly assigned to clinical trial groups?",
    "Which requirements must someone meet to join a clinical study?",
    "How do researchers evaluate the safety of a trial drug?",
    "What responsibilities does the sponsor of a clinical study have?",
    "What does adverse event mean during medical research?",
    "What steps are needed to join a clinical research study?",
    "Why must researchers put their clinical studies in a public registry?",
]

hard_negatives = [
    "What is parental permission for a child in a clinical trial?",
    "What happens during Phase IV of a clinical trial?",
    "What is an active comparator in a clinical trial?",
    "What is blinding in a clinical trial?",
    "What are exclusion criteria in a clinical trial?",
    "How is drug efficacy measured in a clinical trial?",
    "What does an institutional review board do?",
    "What is a serious adverse event in a clinical trial?",
    "How do participants withdraw from a clinical trial?",
    "How is personal health information protected in a clinical trial?",
]

unrelated = [
    "How does a gasoline engine work?",
    "What causes the seasons on Earth?",
    "How do I make a loaf of sourdough bread?",
    "What is the capital of Argentina?",
    "How does a computer graphics card work?",
    "Why do ocean tides occur?",
    "What is the history of classical jazz music?",
    "How do electric vehicle charging stations operate?",
    "What are the rules of basketball?",
    "How does a telescope magnify distant objects?",
]

path = Path("code/hw09/cache_cases.yaml")

def quote(value):
    return json.dumps(value, ensure_ascii=False)

lines = [
    "# DATA 260 HW9 - Part 3",
    "# Student: Haozhe Wang",
    "# Freeze and commit BEFORE executing threshold evaluation.",
    "student: " + quote("Haozhe Wang"),
    "thresholds: [0.75, 0.80, 0.85, 0.90, 0.95]",
    "seeds:",
]

for i, question in enumerate(seeds, 1):
    lines.extend([
        f"  - id: S{i:02d}",
        f"    question: {quote(question)}",
    ])

lines.append("cases:")

groups = [
    ("exact", seeds, True),
    ("paraphrase", paraphrases, True),
    ("hard_negative", hard_negatives, False),
    ("unrelated", unrelated, False),
]

case_number = 0
for category, questions, expected in groups:
    for i, question in enumerate(questions, 1):
        case_number += 1
        lines.extend([
            f"  - id: C{case_number:02d}",
            f"    category: {category}",
            f"    target_seed: S{i:02d}",
            f"    expected_hit: {str(expected).lower()}",
            f"    question: {quote(question)}",
        ])

path.write_text("\n".join(lines) + "\n", encoding="utf-8")

assert case_number == 40
assert len(seeds) == 10
assert len(paraphrases) == 10
assert len(hard_negatives) == 10
assert len(unrelated) == 10

print("Student: Haozhe Wang")
print("PASS: 10 cache seeds")
print("PASS: 10 exact duplicates")
print("PASS: 10 paraphrases")
print("PASS: 10 hard negatives")
print("PASS: 10 unrelated questions")
print("PASS: 40 fixed test cases")
print("PASS: 5 thresholds")
print(f"Created: {path}")
