"""Generate 20 Writer drafts and blank human labels.

Human labels must be assigned manually before evaluate.py is run.
"""
from __future__ import annotations
import asyncio, csv, json, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hw08_kafka"))
from common import INBOX, FINAL, BOOTSTRAP, dumps, loads
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

QUESTIONS = [
    "What is the purpose of a randomized controlled clinical trial?",
    "What is the difference between inclusion and exclusion criteria?",
    "Why is informed consent important in a clinical trial?",
    "What does a placebo control help researchers measure?",
    "What is the role of a study sponsor?",
    "What is an adverse event in a clinical trial?",
    "Why are trial participants monitored after treatment?",
    "What does a trial's primary outcome measure?",
    "How is a secondary outcome different from a primary outcome?",
    "What is randomization intended to reduce?",
    "What is blinding in a clinical trial?",
    "Why do trials define a participant count?",
    "What is a protocol deviation?",
    "What is the purpose of a data monitoring committee?",
    "What does trial recruitment mean?",
    "Why must trial data be recorded consistently?",
    "What is the difference between efficacy and safety?",
    "What is a clinical trial completion date?",
    "Why are eligibility criteria applied before enrollment?",
    "What should a clear trial summary include?",
]

async def main():
    data = Path(__file__).resolve().parents[2] / "reports/hw10/data"
    data.mkdir(parents=True, exist_ok=True)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    consumer = AIOKafkaConsumer(FINAL, bootstrap_servers=BOOTSTRAP,
                                group_id=f"hw10-freeze-{uuid.uuid4()}", auto_offset_reset="latest")
    await producer.start(); await consumer.start()
    cases = []
    try:
        for i, question in enumerate(QUESTIONS, 1):
            cid = str(uuid.uuid4())
            await producer.send_and_wait(INBOX, dumps({"correlation_id": cid, "question": question,
                                                       "hw10_case_id": f"case-{i:02d}",
                                                       "produced_at": __import__('time').time()}))
            async for msg in consumer:
                result = loads(msg.value)
                if result.get("correlation_id") == cid:
                    cases.append({"case_id": f"case-{i:02d}", "correlation_id": cid,
                                  "question": question,
                                  "plan": result.get("plan", ""),
                                  "draft": result.get("draft", ""),
                                  "final": result.get("answer", ""),
                                  "reference": ""})
                    break
    finally:
        await consumer.stop(); await producer.stop()
    (data / "eval_cases.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
    with (data / "human_labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["case_id", "human_score", "notes"])
        w.writerows([[c["case_id"], "", ""] for c in cases])
    print("Created eval_cases.json and blank human_labels.csv. Assign labels manually, then commit both before running evaluate.py.")

if __name__ == "__main__": asyncio.run(main())
