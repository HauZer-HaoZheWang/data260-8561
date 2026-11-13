from pathlib import Path
import csv
import json
from statistics import mean

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reports/hw10/data"
SHOTS = ROOT / "reports/hw10/screenshots"
OUTPUT = ROOT / "reports/hw10/Wang_HW10.pdf"

def read_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

def read_jsonl(name):
    return [
        json.loads(line)
        for line in (DATA / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

cases = read_json("eval_cases.json")
labels = list(csv.DictReader((DATA / "human_labels.csv").open(encoding="utf-8")))
judge = read_jsonl("judge_results.jsonl")
stages = read_jsonl("evaluation_results.jsonl")
part2 = read_json("part2_metrics.json")
validation = read_json("computed_metrics.json")
latency = read_json("latency_metrics.json")
part4 = read_json("part4_metrics.json")

assert len(cases) == len(labels) == len(stages) == 20
assert len(judge) == 60
assert not any("error" in row for row in judge)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="MainTitleBW", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=12
))
styles.add(ParagraphStyle(
    name="SectionBW", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=14, leading=17,
    spaceBefore=12, spaceAfter=8
))
styles.add(ParagraphStyle(
    name="SubBW", parent=styles["Normal"],
    fontName="Helvetica-Bold", fontSize=12, leading=15,
    spaceBefore=9, spaceAfter=5
))
styles.add(ParagraphStyle(
    name="BodyBW", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=15, spaceAfter=7
))
styles.add(ParagraphStyle(
    name="CaptionBW", parent=styles["Normal"],
    fontName="Helvetica", fontSize=9, leading=12, spaceAfter=8
))
styles.add(ParagraphStyle(
    name="CellBW", parent=styles["Normal"],
    fontName="Helvetica", fontSize=8, leading=10
))

story = []
def text(value, style="BodyBW"):
    story.append(Paragraph(str(value), styles[style]))

def table(rows, widths):
    cells = [
        [Paragraph(str(value), styles["CellBW"]) for value in row]
        for row in rows
    ]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 9))

def shot(filename, caption):
    path = SHOTS / filename
    if not path.exists():
        raise FileNotFoundError(path)
    img = Image(str(path))
    scale = min(6.8 * inch / img.imageWidth,
                7.6 * inch / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    story.append(KeepTogether([
        Paragraph(caption, styles["CaptionBW"]), img
    ]))
    story.append(Spacer(1, 12))

text("DATA 260 Homework 10", "MainTitleBW")
text("Haozhe Wang")
text("Evaluation, judge validation, tracing, latency, and dashboard.")
text("Run date: November 12-13, 2026.")

text("0. Setup", "SectionBW")
text("This work uses the HW8 Kafka agents and the HW9 semantic cache. "
     "The Kafka prefix is s8561. Kafka uses port 9092 and Redis uses "
     "port 6379. The local judge uses Ollama/qwen3:8b. The embedding "
     "model is nomic-embed-text.")
text("The request path is cache lookup, Planner, Writer, Reviewer, "
     "and final answer. The Kafka correlation ID is also used as the trace ID.")

text("1. Streamlit dashboard", "SectionBW")
text("1.1 Summary", "SubBW")
text("The Summary page reads latency_experiment.jsonl. Its time window "
     "is the stored 50-request experiment. All 50 requests were cache "
     "misses, so its hit count is zero by experiment design. This is "
     "not a production cache hit rate.")
text(f"The 50-request pipeline had {part4['pipeline_error_rate']['errors']} "
     f"errors. One separate cache-hit example took "
     f"{part4['cache_hit_latency']['duration_ms']:.3f} ms. "
     "The hit figure is one example, not a p50 measurement.")
shot("01_dashboard_summary.png", "Figure 1. Dashboard Summary page.")
shot("07_latency_50_misses.png", "Figure 2. Stage latency view for 50 cache misses.")

text("1.2 Evaluation and collaboration", "SubBW")
text("The Evaluation page reads evaluation_results.jsonl, "
     "part2_metrics.json, and computed_metrics.json. Each row links "
     "Plan, Draft, and Final with the same trace ID. In this run, "
     "the judge scored every stage 5.0. The page shows the scores, "
     "but these scores cannot show whether the Reviewer improved an answer.")
shot("02_dashboard_evaluation.png", "Figure 3. Evaluation page after the new run.")

text("1.3 Trace lookup", "SubBW")
text("The lookup uses trace_id to find spans in spans.jsonl. "
     "The app uses st.cache_data to read result files. It does not "
     "load a shared model resource, so st.cache_resource is not needed.")
shot("06_dashboard_trace_lookup.png", "Figure 4. Cache-hit lookup.")
shot("09_dashboard_cache_miss_trace.png", "Figure 5. Cache-miss lookup.")
shot("08_dashboard_failed_trace.png", "Figure 6. Client timeout lookup.")

text("2. Automated evaluation", "SectionBW")
text("2.1 Judge method and failures", "SubBW")
text("DeepEval GEval scored Plan Quality, Writer Helpfulness, and "
     "Final Helpfulness. The score conversion is 1 + 4 times the "
     "GEval score on its 0 to 1 scale. The evaluator uses "
     "strict_mode=False. The Ollama request uses temperature 0 "
     "and think=False. The default judge timeout is 180 seconds. "
     "An empty output gets score 1. Judge exceptions are written "
     "as error rows so one bad response does not stop the full run.")
text("This run had 60 judge rows and zero judge error rows. "
     "These facts show that the calls completed; they do not show "
     "that the judge can separate good and weak answers.")

text("2.2 Plan, Draft, and Final", "SubBW")
text("The frozen file now contains a nonempty Plan, Draft, and Final "
     "for all 20 cases. Earlier files omitted Plans and had empty "
     "Drafts; those earlier evaluation numbers are not used here.")
table([
    ["Measure", "Result"],
    ["Plan mean", f"{part2['mean_plan_score']:.1f}"],
    ["Draft mean", f"{part2['mean_writer_score']:.1f}"],
    ["Final mean", f"{part2['mean_final_score']:.1f}"],
    ["Final minus Draft mean", f"{part2['mean_final_minus_draft']:.1f}"],
    ["Improved / unchanged / worse",
     f"{part2['improved_cases']} / {part2['unchanged_cases']} / {part2['worse_cases']}"],
], [3.4*inch, 2.5*inch])
text("Every stage received 5.0 in every case. The raw per-case file "
     "also includes a judge reason for each Plan, Draft, and Final. "
     "The score difference is zero in all 20 cases. This does not "
     "prove the Reviewer made no useful changes: the judge reached "
     "the top score for both versions.")

text("3. Judge validation", "SectionBW")
text("3.1 Frozen labels and settings", "SubBW")
text("The first case set had missing Plans and empty Drafts, so I fixed "
     "case collection and generated new responses. The new cases and "
     "human labels were committed in c6afa7d before the new judge "
     "results in 1b283f4. I had already seen results from the earlier "
     "invalid run, and AI suggestions were used during labeling. "
     "These labels are not fully independent of earlier feedback. "
     "Human scores contain five 4s and fifteen 5s. The local judge "
     "gave 5.0 in all 60 Writer runs. Temperature 0 and think=False "
     "help repeatability but do not prove accurate scoring.")

text("3.2 Raw per-case comparison", "SubBW")
text("The table below uses human_labels.csv and judge_results.jsonl. "
     "It shows all three repeats for each case.")
by_label = {row["case_id"]: row for row in labels}
by_judge = {(row["case_id"], row["repeat"]): row for row in judge}
rows = [["Case", "Human", "Judge 1", "Judge 2", "Judge 3"]]
for case in cases:
    cid = case["case_id"]
    rows.append([
        cid, by_label[cid]["human_score"],
        *[str(by_judge[(cid, i)]["judge_score"]) for i in (1, 2, 3)]
    ])
table(rows, [1.0*inch, 1.0*inch, 1.15*inch, 1.15*inch, 1.15*inch])

text("3.3 Validation result", "SubBW")
text("Spearman correlation cannot be calculated here because every "
     "judge score is the same. The mean absolute difference from "
     f"human scores is {validation['mad']:.2f} on the 1 to 5 scale. "
     "The repeat change rate, mean repeat change, and maximum "
     "repeat change are all zero. The judge is stable in this run "
     "but does not distinguish the answers in this sample.")
text("I would use it for exploratory review, not as the only release "
     "gate. I would first test more cases, clearly weak and strong "
     "answers, different question topics, and settings other than "
     "temperature 0. I would compare its results with independent "
     "human ratings.")

text("4. Tracing and latency", "SectionBW")
text("4.1 Spans and examples", "SubBW")
text("A span records trace_id, stage, start_time, end_time, "
     "duration_ms, status, and error. Queue wait is measured "
     "between sending and receiving a Kafka message.")
text("Cache hit: d2954a0c-0e28-4c24-af0e-556046944189<br/>"
     "Successful miss: 1a3a7b28-af13-4b45-9615-96cf90c5681f<br/>"
     "Client timeout: 46600bfc-9ca3-4726-aea3-57ccb7807cec")
text("The failed request used a five-second caller timeout. "
     "The error stage is client_timeout. The backend agents later "
     "completed their work; this example is a caller timeout, "
     "not a Planner, Writer, or Reviewer crash.")
shot("03_trace_cache_hit.png", "Figure 7. Cache-hit example.")
shot("04_trace_cache_miss.png", "Figure 8. Cache-miss example.")
shot("05_trace_failed.png", "Figure 9. Client timeout example.")

text("4.2 Controlled miss experiment", "SubBW")
text("The experiment has 50 requests, 50 misses, and 50 unique "
     "trace IDs. Its threshold is 0.99 to keep similar template "
     "questions on the miss path. It measures this controlled "
     "path, not the normal cache hit rate. The normal cache threshold "
     "is 0.85; this controlled experiment used 0.99.")
q = part4["queue_wait_total"]
lat_rows = [
    ["Stage", "n", "p50 ms", "p95 ms", "% of E2E"],
    ["Cache lookup", "50", "24.755", "77.694", "0.04%"],
    ["Queue wait total", "50", "20.817", "26.737", "0.02%"],
    ["Planner", "50", "40371.229", "53488.993", "31.67%"],
    ["Writer", "50", "45102.404", "58694.795", "34.62%"],
    ["Reviewer", "50", "39561.836", "55038.915", "31.32%"],
    ["Other gaps/overhead", "-", "-", "-", "2.33%"],
    ["End to end", "50", "130576.366", "160826.213", "100%"],
    ["Evaluation, separate", "60", "4374.217", "5245.925", "N/A"],
]
table(lat_rows, [1.85*inch, .35*inch, 1.0*inch, 1.0*inch, .9*inch])
text("Queue wait total adds the three queue waits within each "
     "request before calculating percentiles. The percentage for "
     "each stage is its mean duration divided by the mean end-to-end "
     "duration of 131500.365 ms. Percentiles cannot be added. The "
     "remaining 2.33 percent is time not covered by these spans. "
     "The Evaluation row is the duration of one Writer GEval call "
     "across 60 calls; it is not the combined Plan, Draft, and Final "
     "evaluation time. GEval ran separately from the 50 cache-miss "
     "requests. Planner, Writer, and Reviewer take most of the "
     "request time. I would first check local model call time, "
     "prompt size, and output length.")

text("5. Conclusion", "SectionBW")
text("The new frozen cases have valid Plan, Draft, and Final text. "
     "The pipeline and tracing work, and the 50 miss requests have "
     "complete stage timing. The local judge completed its calls "
     "but gave every answer the maximum score. The current scores "
     "cannot support a claim that Final is better than Draft. "
     "More varied answers and independent human checks are needed.")

text("AI use", "SectionBW")
text("I used ChatGPT and Claude to understand requirements, "
     "troubleshoot code, and review the report. ChatGPT suggested "
     "scores and notes during human labeling and provided code and "
     "report changes. I ran the experiments and checked the saved "
     "results myself.")

def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(letter[0]/2, .4*inch, str(doc.page))
    canvas.restoreState()

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter,
    leftMargin=.7*inch, rightMargin=.7*inch,
    topMargin=.65*inch, bottomMargin=.65*inch,
    title="DATA 260 Homework 10", author="Haozhe Wang"
)
doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
print("Created:", OUTPUT)
