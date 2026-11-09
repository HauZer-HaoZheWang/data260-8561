#!/usr/bin/env python3
"""Generate DATA 260 HW9 PDF from actual local logs and screenshots.
Run from anywhere inside project: python scripts/build_hw09_report.py
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, KeepTogether)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports' / 'hw09'
SHOTS = REPORT / 'screenshots'
OUTPUT = REPORT / 'Wang_HW9.pdf'

required = ['part2_summary.json', 'part3_threshold_results.json',
            'part3_invalidation.txt', 'part4_training_results.json',
            'part4_validation_decision.json', 'part4_comparison.json']
missing = [str(REPORT / name) for name in required if not (REPORT / name).is_file()]
images = []
for i in range(14):
    matches = sorted(SHOTS.glob(f'{i:02d}_*.png'))
    if not matches:
        missing.append(f'screenshot {i:02d}')
    else:
        images.append(matches[0])
if missing:
    raise SystemExit('Missing required evidence:\n' + '\n'.join(missing))

def load(name):
    return json.loads((REPORT / name).read_text(encoding='utf-8'))

styles = {
    'title': ParagraphStyle('HW9Title', fontName='Helvetica-Bold', fontSize=14, leading=19, spaceAfter=12),
    'h1': ParagraphStyle('HW9Heading', fontName='Helvetica-Bold', fontSize=14, leading=18, spaceBefore=16, spaceAfter=8, keepWithNext=True),
    'h2': ParagraphStyle('HW9Subheading', fontName='Helvetica-Bold', fontSize=12, leading=16, spaceBefore=10, spaceAfter=6, keepWithNext=True),
    'body': ParagraphStyle('HW9Body', fontName='Helvetica', fontSize=11, leading=15.5, spaceAfter=9),
    'cell': ParagraphStyle('HW9Cell', fontName='Helvetica', fontSize=9, leading=12),
    'caption': ParagraphStyle('HW9Caption', fontName='Helvetica', fontSize=9, leading=12, spaceAfter=7),
}

def P(value, kind='body'):
    return Paragraph(escape(str(value)), styles[kind])

story=[]
def add(value, kind='body'):
    story.append(P(value,kind))

def fmt(value, digits=2):
    if value is None: return 'N/A'
    return f'{float(value):,.{digits}f}'

def add_table(headers, rows, widths):
    data = [[P(v, 'cell') for v in headers]]
    data.extend([[P(v,'cell') for v in row] for row in rows])
    t=Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.4,colors.grey),
        ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    story.append(t)
    story.append(Spacer(1,10))

p2=load('part2_summary.json')
p3=load('part3_threshold_results.json')
training=load('part4_training_results.json')
validation=load('part4_validation_decision.json')
comparison=load('part4_comparison.json')

add('DATA 260 - Homework 9', 'title')
add('Student: Haozhe Wang')
add('Domain: Clinical Trials | Prefix: s8561 | Domain ID: 1 | Seed: 8561')
add('Repository branch: hw9-work')
add('Report: Redis Counter, Semantic Cache, Threshold Evaluation, and Agent Lesson Memory')

add('Executive Summary', 'h1')
add('This project extends the clinical-trial application with a Redis view counter, semantic caching at the ingress of a Kafka-based multi-agent question-answering workflow, cache-threshold evaluation, stale-data invalidation, and lesson memory with separate answering and evaluator agents.')
add('All numerical results below come from the saved homework experiment outputs. The threshold-sweep latency and monetary cost are clearly identified as estimates, not individual request measurements or billed charges.')

add('Environment and Technology', 'h1')
add_table(['Technology','Use'], [
    ('Python / Docker / Git','Implementation, containerized services, and reproducible version history'),
    ('MySQL / SQLAlchemy','Clinical-trial records and durable view-count storage'),
    ('Redis Stack','Atomic INCR counter, cached responses, and vector similarity search'),
    ('Apache Kafka / aiokafka','Asynchronous Planner, Writer, Reviewer, and final-response messages'),
    ('Ollama / Qwen3:8b','Local response generation and separate evaluator judgments'),
    ('nomic-embed-text','Local text embeddings for semantic cache lookup'),
], [152,388])

add('Part 1 - Redis-Backed Trial View Counter', 'h1')
add('Each access to an existing trial atomically increments a prefixed Redis counter with INCR. The application synchronizes the counter to the s8561_rel MySQL database after every 10 increments, reducing database write frequency.')
add('Observed 25-access test: Redis view count = 25; persisted MySQL view count = 20. The remaining five accesses have not yet reached the next synchronization boundary. This batching policy trades write reduction for possible loss of unsynchronized counts after a crash.')
add('Implementation excerpt: count = redis_client.incr(key); if count % 10 == 0: UPDATE trials SET view_count = :count WHERE id = :id.', 'body')

add('Part 2 - Semantic Response Cache', 'h1')
add('The question is embedded with nomic-embed-text, and Redis Stack searches for the nearest cached embedding by cosine distance. At threshold 0.85, an eligible version-matching result returns the stored answer. On a miss, the real HW8 Kafka Planner -> Writer -> Reviewer pipeline generates a response that is cached for later reuse.')
add_table(['Metric','Measured result'], [
    ('Total queries', str(p2['total_queries'])),
    ('Cache hits', str(p2['cache_hits'])),
    ('Cache misses', str(p2['cache_misses'])),
    ('Hit rate', fmt(p2['hit_rate_percent']) + '%'),
    ('Mean cache-hit latency', fmt(p2['avg_hit_latency_ms']) + ' ms'),
    ('Mean cache-miss latency', fmt(p2['avg_miss_latency_ms']) + ' ms'),
], [238,302])
add('The 10-query benchmark included exact duplicates, paraphrases, and new questions. A paraphrase with cosine similarity approximately 0.8404 missed at threshold 0.85, while one at approximately 0.9262 hit. Exact duplicates consistently hit after their corresponding initial miss.')

cost_decision = json.loads((REPORT / 'part3_cost_decision.json').read_text())

add('Part 3 - Precommitted Cases and Threshold Sweep','h1')
add('The 40 evaluation cases were committed in Git before threshold testing (commit 190f0bd). The labeled dataset contains 10 exact duplicates, 10 paraphrases, 10 hard negatives, and 10 unrelated questions. Five thresholds (0.75, 0.80, 0.85, 0.90, 0.95) were evaluated by offline cosine similarity using real Ollama embedding vectors against 10 seed questions.')
add_table(['Threshold','Hit rate','False hits','Negative false-hit rate','Estimated latency','Total cost*'], [
    (fmt(x['threshold']), fmt(x['hit_rate_percent'])+'%', str(x['false_hits']),
     fmt(x['negative_false_hit_rate_percent'])+'%', fmt(x['estimated_avg_latency_ms'])+' ms',
     '$'+fmt(next(r['total_cost_usd'] for r in cost_decision['results'] if abs(r['threshold']-x['threshold']) < 1e-9),5))
    for x in p3['threshold_summary']
], [68,70,68,112,124,98])
add('Hit/miss classifications use actual embedding scores, not generated decisions. Estimated latency applies the Part 2 measured hit/miss averages to each predicted cache outcome. Estimated monetary cost uses the explicit hypothetical per-hit/per-miss model, not local Ollama billing. This is an offline replay, not five separate Redis FT.SEARCH benchmark runs.')


cost_decision = json.loads((REPORT / 'part3_cost_decision.json').read_text())

add('Part 3.4 - Cost Model and Deployment Decision','h2')
add(
    'The cost model assigns $0.00001 to a cache hit, '
    '$0.002 to a cache miss, and an additional $0.01 '
    'penalty to a false hit. A hit uses inexpensive cache '
    'operations, a miss runs the agent pipeline, and a '
    'false hit may require extra checking and correction. '
    'These are hypothetical cost weights, not actual '
    'Ollama charges or measured clinical harm.'
)
add(
    'Total cost = (hits x $0.00001) + '
    '(misses x $0.002) + (false hits x $0.01).'
)

add_table(
    ['Threshold', 'Hits', 'Misses', 'False hits', 'Total cost'],
    [
        (
            fmt(r['threshold']),
            str(r['hits']),
            str(r['misses']),
            str(r['false_hits']),
            '$' + fmt(r['total_cost_usd'], 5),
        )
        for r in cost_decision['results']
    ],
    [100, 90, 100, 110, 140]
)

add(
    'Selected deployment threshold: 0.95. '
    'On the frozen 40-case dataset, it produced zero '
    'observed false hits and the lowest modeled total '
    'cost ($0.06010). This conservative threshold '
    'reduces incorrect answer reuse but also reduces '
    'the hit rate to 25%, primarily exact duplicates. '
    'The choice is sensitive to the assumed false-hit '
    'penalty and requires further evaluation on more data.'
)


add(
    '* Total cost in both threshold tables includes the '
    'additional false-hit penalty. These are modeled '
    'USD-equivalent costs, not actual Ollama charges.'
)
add(
    'Cost sensitivity: let P be the additional penalty per '
    'false hit. Comparing all five candidate thresholds, '
    '0.95 is a minimum-cost choice when P is at least '
    '$0.00597. At P = $0, 0.75 is cheapest. '
    'The selected P = $0.01 exceeds this crossover.'
)

examples=p3.get('false_hit_examples',[])
if examples:
    ex=examples[0]
    add('False-Hit Example','h2')
    add(f"Case {ex['id']}, threshold {ex['threshold']}, similarity {fmt(ex['similarity'],6)}. Incoming question: {ex['question']} Nearest cached question: {ex['nearest_question']}")
    add('Although both questions concern clinical-trial consent, parental permission for a child and general informed consent call for materially different explanations. At a lower threshold, a plausible nearest neighbor can produce an incorrect reuse.')

false_hit_actual = json.loads((REPORT / 'part3_false_hit_actual.json').read_text())

add('Actual Redis False-Hit Answer and Correct Reference','h2')
add(
    'This controlled experiment used a temporary Redis FT.SEARCH '
    'index and an explicitly seeded cached answer. '
    'It reproduced case C21 at threshold 0.75.'
)
add(
    'Incoming question: ' +
    false_hit_actual['incoming_question']
)
add(
    'Nearest cached question: ' +
    false_hit_actual['cached_question']
)
add(
    'Measured cosine similarity: ' +
    fmt(false_hit_actual['similarity'], 6)
)
add(
    'Actual answer returned by Redis: ' +
    false_hit_actual['actual_cached_answer']
)
add(
    'Correct reference answer: ' +
    false_hit_actual['correct_reference_answer']
)
add(
    'The cached response explains general informed consent '
    'but does not correctly answer the question about parental '
    'permission and possible child assent. This is a false hit.'
)

add('Stale Answer and Cache Invalidation','h2')

invalidation_log = (
    REPORT / 'part3_invalidation.txt'
).read_text(encoding='utf-8')

import re

def log_value(label):
    for line in invalidation_log.splitlines():
        line = line.strip()
        if line.startswith(label):
            return line[len(label):].strip()
    raise RuntimeError(
        'Missing invalidation log field: ' + label
    )

add('Actual Trial Record and Before/After Answers','h2')
add(
    'Cached question template: Database trial [trial_id] '
    'participant count verification [unique token]. '
    'The random token was generated during execution but '
    'was not printed in the saved log.'
)
add('Actual MySQL trial ID: ' + log_value('trial_id:'))
add('Original participant count: ' + log_value('participant_count:'))
add('Updated participant count: ' + log_value('Updated participant_count:'))
add('Stale cached answer: ' + log_value('Redis cached answer:'))
add('Refreshed answer: ' + log_value('Refreshed answer:'))
add('Original cached version: ' + log_value('Cached version:'))
add('Updated record version: ' + log_value('Current version:'))
add(
    'The same question originally returned a participant '
    'count of 0, although MySQL had been updated to 1. '
    'A content-hash version mismatch identified this stale '
    'response. The old Redis entry was deleted, and the '
    'refreshed answer returned the new count of 1. '
    'The original database value and temporary Redis '
    'records were restored or removed after the experiment.'
)


add('The database-grounded demonstration cached an answer using a real trial participant count, modified the MySQL record, and observed that the old Redis answer remained. A record-content version hash detected the mismatch, after which the stale hash was deleted and a refreshed answer inserted. Temporary Redis entries were removed and the original MySQL count was restored.')
add('Scope: this controlled demonstration does not automatically integrate the record-aware invalidation mechanism into every call of the existing general semantic-cache answer() method, which still uses a fixed version string.')

add(
    'Trade-off of record-content hashing: checking the current '
    'MySQL record and computing its content hash before serving '
    'a cached answer improves freshness and detects changes '
    'without manually incrementing a version number. However, '
    'it introduces database reads and hash computation, '
    'increasing latency and database load. It also reduces '
    'the performance benefit of caching and requires the '
    'same canonical record fields to be hashed consistently. '
    'The controlled demonstration implements this mechanism; '
    'the general semantic-cache answer path still uses a '
    'fixed version string.'
)


add('Part 4 - Evaluator Repair and Lesson Memory','h1')
add('An Answering Agent uses local Qwen3 to answer clinical-trial questions, while a separate Evaluator Agent uses the question and reference answer to judge factual correctness and provide feedback. A failed answer may be revised one time (maximum two attempts). Input-only training, validation, and held-out test datasets are stored separately from ground-truth references.')
add('Controlled Incorrect Answer and Revision','h2')
control=next((x for x in training if x['id']=='TR02'),None)
if control:
    for a in control['history']:
        add(f"Attempt {a['attempt']} ({a['source']}); evaluator correct={a['correct']}. Answer: {a['answer']} Feedback: {a['feedback']}")
add('Lesson Validation','h2')
add(f"Validation questions: {validation['validation_cases']}; regressions: {validation['regressions']}; improvements: {validation['improvements']}; lessons accepted: {validation['lessons_accepted']}.")

add(
    'The original validation implementation required a positive '
    'improvement and zero regressions. This was stricter than the '
    'assignment requirement, which permits failure cases to improve '
    'or remain unchanged, provided previously correct answers remain '
    'correct and unrelated questions do not receive unsupported answers.'
)
add(
    'The original validation recorded zero regressions and zero '
    'improvements. All four baseline questions were already correct. '
    'The original program therefore marked the lesson as rejected. '
    'That historical decision and the held-out test results have '
    'not been changed.'
)

audit = json.loads((REPORT / 'part4_lesson_audit.json').read_text())

add('Supplemental Lesson Safety Audit','h2')
add(
    'After the original held-out test, two additional safety questions '
    'were evaluated using Lesson Memory. These were supplemental audit '
    'questions, not additions to the frozen validation or test datasets.'
)
add(
    'Original validation regressions: ' +
    str(audit['regressions']) +
    '; original validation improvements: ' +
    str(audit['improvements']) +
    '; original baseline failures: ' +
    str(audit['original_baseline_failures']) + '.'
)

for item in audit['unrelated_checks']:
    add('Audit question: ' + item['question'])
    add('Agent response: ' + item['answer'])
    add(
        'Evaluator safety judgment: ' +
        str(item['safe']) +
        '. Reason: ' + item['reason']
    )

add(
    'The supplemental audit found no unsupported answers in its two '
    'questions, and the original validation found no regressions. '
    'However, the original validation contained no failed baseline '
    'cases, so the failure-case criterion was not meaningfully tested. '
    'The audit also occurred after the held-out comparison. '
    'These limitations prevent claiming a fully validated '
    'pre-test lesson-retention decision.'
)

add('Part 4 Data, Agent Communication, and Lesson Reuse','h2')
add(
    'The input files training_data.json, validation_data.json, '
    'and test_data.json contain question IDs and question text only. '
    'ground_truth.json stores reference answers separately for '
    'the Evaluator Agent. lessons.json stores lesson_id, '
    'failure_pattern, correction, created_at, use_count, '
    'and validation status.'
)
add(
    'The two agents communicate through Python function calls in '
    'part4_agents.py. The Answering Agent generates a response with '
    'Qwen3:8b. The Evaluator Agent receives the question, candidate '
    'answer, and reference answer, then returns a correctness judgment '
    'and feedback. A failed answer can be revised once, for a maximum '
    'of two attempts.'
)
add(
    'Lesson Memory is selected from lessons.json and inserted into '
    'the answering prompt as a previously learned correction. '
    'The use_count field is incremented when a lesson is used. '
    'The original Validated Improvement variant included only '
    'lessons marked accepted by the original validation policy.'
)


add('Part 4 Implementation Evidence - Actual Code Excerpts','h2')

add('Answering Agent','h2')
add(
    'Source: code/hw09/part4_agents.py, answer_question(). '
    'The answering prompt instructs Qwen3:8b not to invent '
    'trial-specific facts. When Lesson Memory is enabled, '
    'each stored correction is inserted before the question.'
)
add(
    "Implementation: prompt += "
    "'\\nPreviously learned corrections:\\n'; "
    "for lesson in lessons: "
    "prompt += f\"- {lesson['correction']}\\n\"; "
    "lesson['use_count'] += 1."
)

add('Evaluator Agent','h2')
add(
    'Source: part4_agents.py, evaluate(). The separate '
    'evaluator receives the question, candidate answer, '
    'and the expected reference answer. It requests a '
    'JSON correctness decision and textual feedback.'
)
add(
    "Implementation: raw = call_model(prompt, json_mode=True); "
    "result = json.loads(raw); "
    "return {'correct': result['correct'], "
    "'feedback': feedback}."
)

add('Revision and Agent Communication','h2')
add(
    'Source: part4_agents.py, run_case(). Both agents are '
    'called by Python functions. The function sends the '
    'question to the Answering Agent, forwards the answer '
    'to the Evaluator Agent, and passes evaluator feedback '
    'back into the next answering prompt when revision is '
    'allowed. Ollama communication uses HTTP POST requests. '
    'This Part 4 workflow does not use Kafka.'
)
add(
    "Implementation: attempts_allowed = 2 if mode == "
    "'repair' else 1. The loop calls answer_question(), "
    "then evaluate(), saves the result in history, "
    "and retries with feedback only after an incorrect answer."
)

add('Lesson Creation and Retention','h2')
add(
    'Training creates a lesson when an answer attempt fails. '
    'The stored object contains lesson_id, source_case, '
    'failure_pattern, correction, created_at, use_count, '
    'and validation_status. The correction for L01 states '
    'that informed consent explains risks and rights but '
    'never guarantees risk-free research.'
)
add(
    'Actual stored status: L01 was rejected by the original '
    'validation policy, which required improvements greater '
    'than zero. The later supplemental safety audit passed, '
    'but did not change the historical validation decision.'
)
add(
    'Lesson Memory injects the saved correction directly '
    'into the prompt without semantic relevance filtering. '
    'Validated Improvement only loads lessons whose status '
    'is accepted. Since L01 was rejected, that variant '
    'did not inject L01 in the recorded held-out test.'
)

add('Dataset Separation and Evaluation Limits','h2')
add(
    'Training, validation, and test each contain four '
    'question-only records. Their reference answers are '
    'stored separately in ground_truth.json. A reference '
    'entry contains expected answer text and required_concepts. '
    'The evaluator prompt uses the expected answer text '
    'for its model-based correctness judgment.'
)
add(
    'The held-out test produced 4/4 correct answers for '
    'each of the four variants. No accuracy improvement '
    'or correction-rate gain was established on this '
    'small test set.'
)


add('Supplemental Lesson Reuse - Later Question','h2')

reuse = json.loads(
    (REPORT / 'part4_lesson_reuse_demo.json').read_text(
        encoding='utf-8'
    )
)

add(
    'This post-test demonstration explicitly loaded an '
    'existing lesson before answering a later question. '
    'It used a copy of the saved lessons and did not alter '
    'the historical validation decision.'
)
add('Lesson ID: ' + reuse['lesson_id'])
add('Source training case: ' + reuse['lesson_source'])
add('Original lesson status: ' + reuse['lesson_status'])
add('Loaded correction: ' + reuse['loaded_correction'])
add('Later question: ' + reuse['question'])
add('Actual Qwen3 answer: ' + reuse['answer'])
add(
    'Lesson use count in the demonstration: ' +
    str(reuse['local_use_count_before']) +
    ' to ' +
    str(reuse['local_use_count_after']) + '.'
)
add(
    'This demonstrates prompt-level lesson reuse, '
    'not an accuracy gain measured on the original '
    'held-out test dataset.'
)

add('Required Dataset Content and Artifacts','h2')

data_dir = (
    Path(__file__).resolve().parents[1] / 'code' / 'hw09'
)

for filename, heading in [
    ('training_data.json', 'Training Input Dataset'),
    ('validation_data.json', 'Validation Input Dataset'),
    ('test_data.json', 'Held-Out Test Input Dataset'),
]:
    records = json.loads(
        (data_dir / filename).read_text(encoding='utf-8')
    )
    add(heading + ' - ' + filename, 'h2')
    add('Number of questions: ' + str(len(records)))
    for record in records:
        add(record['id'] + ': ' + record['question'])

references = json.loads(
    (data_dir / 'ground_truth.json').read_text(
        encoding='utf-8'
    )
)

add('Reference Dataset - ground_truth.json', 'h2')
add(
    'Reference answers are stored separately from the '
    'question-only input datasets and are supplied to '
    'the Evaluator Agent.'
)
for case_id, reference in references.items():
    add(case_id + ' reference: ' + reference['expected'])
    add(
        'Required concepts: ' +
        ', '.join(map(str, reference.get('required_concepts', [])))
    )

lessons = json.loads(
    (data_dir / 'lessons.json').read_text(encoding='utf-8')
)

add('Persistent Lesson Memory - lessons.json', 'h2')
for lesson in lessons:
    add(
        'Lesson ' + lesson['lesson_id'] +
        '; source: ' + lesson['source_case'] +
        '; failure pattern: ' + lesson['failure_pattern']
    )
    add('Correction: ' + lesson['correction'])
    add(
        'Created: ' + lesson['created_at'] +
        '; use_count: ' + str(lesson['use_count']) +
        '; validation_status: ' + lesson['validation_status']
    )

add('Frozen Semantic Cache Dataset - cache_cases.yaml', 'h2')

try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        'PyYAML is required to include the frozen YAML dataset. '
        'Install it with: python -m pip install pyyaml'
    ) from exc

cache_dataset = yaml.safe_load(
    (data_dir / 'cache_cases.yaml').read_text(
        encoding='utf-8'
    )
)

add(
    'This dataset was committed before threshold evaluation. '
    'It contains 10 seed questions and 40 labeled cases: '
    '10 exact, 10 paraphrase, 10 hard-negative, and '
    '10 unrelated.'
)

add('Seed Questions','h2')
for seed in cache_dataset['seeds']:
    add(seed['id'] + ': ' + seed['question'])

add('Labeled Evaluation Cases','h2')
for category in ['exact', 'paraphrase', 'hard_negative', 'unrelated']:
    subset = [
        case for case in cache_dataset['cases']
        if case['category'].replace('-', '_') == category
    ]
    if subset:
        add(category.replace('_', ' ').title(), 'h2')
    for case in subset:
        target = case.get('target_seed')
        expected = case.get('expected_hit')
        add(
            case['id'] + ': ' + case['question'] +
            ' | target=' + str(target) +
            ' | expected_hit=' + str(expected)
        )

add(
    'The source files remain available in code/hw09. '
    'The report lists the data records for review but '
    'does not reproduce the full implementation source code.'
)

add('Held-Out Four-Variant Comparison','h2')
add_table(['Variant','Correct','Incorrect','Avg. attempts','Avg. latency'], [
    (x['variant'],str(x['correct']),str(x['incorrect']),fmt(x['avg_attempts']),fmt(x['avg_latency_ms'])+' ms')
    for x in comparison
], [162,68,75,100,135])
add('All four variants answered 4 of 4 held-out questions correctly at the first attempt. The experiment therefore does not establish a gain in accuracy from evaluator repair or lessons on this small test set; latency differences should not be interpreted as stable speed rankings.')

add('Limitations, Tradeoffs, and Interpretation','h1')
add('Lower similarity thresholds increase cache reuse but can create semantically incorrect hits. Higher thresholds suppress false reuse while producing more expensive misses. Periodic counter synchronization risks losing recent unflushed increments. Fixed data-version markers risk stale answers. Agent evaluation is based on four held-out questions and model-based correctness judgments, which limits generalization.')
add('AI Use Statement','h1')
add(
    'I used AI tools during this homework and report preparation.'
)
add(
    'I used ChatGPT to help plan the experiments, generate and '
    'revise Python code and terminal commands for Parts 1-4, '
    'troubleshoot technical problems, and draft and organize the report.'
)
add(
    'I used Claude to review the report against the homework '
    'instructions, identify missing requirements, and suggest '
    'improvements to the explanations and evaluation methods.'
)
add(
    'I used Ollama with Qwen3:8b as the local language model '
    'for the answering and evaluator agents in my experiments.'
)
add(
    'I ran the experiments on my computer, checked the results, '
    'collected the screenshots, and reviewed the final report. '
    'I have disclosed these tools and their roles to make '
    'my AI use transparent.'
)

add('Evidence Appendix - 14 Original Terminal Screenshots','h1')
add('The following labeled evidence images are sourced from reports/hw09/screenshots. They retain the original screenshot content, including student identification where captured.')
CAPTIONS=[
    'Environment readiness','Redis view counter: 25 accesses','Redis / MySQL counter synchronization',
    'Semantic cache miss','Semantic cache hit','Ten-query cache benchmark',
    '40 cases frozen in Git','Threshold sweep','False-hit example',
    'Stale answer, invalidation, and cleanup','Controlled incorrect answer and revision',
    'Lesson memory reuse','Validation result and decision','Four-variant test comparison',
]
for i,path in enumerate(images):
    story.append(PageBreak())
    add(f'Evidence {i:02d} - {CAPTIONS[i]}','h2')
    add(path.name,'caption')
    iw,ih=ImageReader(str(path)).getSize()
    scale=min(530/iw,650/ih)
    img=Image(str(path),width=iw*scale,height=ih*scale)
    img.hAlign='CENTER'
    story.append(img)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica',8)
    canvas.drawString(36,25,'DATA 260 HW9 | Haozhe Wang')
    canvas.drawRightString(576,25,f'Page {doc.page}')
    canvas.restoreState()

REPORT.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=36,
                      rightMargin=36, topMargin=40, bottomMargin=44,
                      title='DATA 260 HW9 - Haozhe Wang')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Student: Haozhe Wang')
print('PASS: Final English PDF generated')
print(f'Evidence screenshots included: {len(images)}')
print(f'PDF: {OUTPUT}')
