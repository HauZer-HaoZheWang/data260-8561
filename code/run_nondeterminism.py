import json, subprocess, sys, time

CASE = "reports/hw01/cases/nondeterminism_input.json"
OUT  = "reports/hw01/raw/nondeterminism_runs.json"

case = json.load(open(CASE))
title, content = case["title"], case["content"]

results = []

for temp in [0.7, 0.0]:
    for i in range(20):
        cmd = [sys.executable, "code/agents_demo.py",
               "--title", title,
               "--content", content,
               "--temperature", str(temp)]

        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        t1 = time.time()
        ms = int((t1 - t0) * 1000)

        tags = None
        try:
            block = r.stdout.split("Publish Package")[-1].strip()
            pkg = json.loads(block)
            tags = pkg["agents"]["final"]["tags"]
        except Exception as e:
            print("  parse failed:", e)

        results.append({
            "run": i + 1,
            "temperature": temp,
            "tags": tags,
            "latency_ms": ms,
        })

        json.dump(results, open(OUT, "w"), indent=2)
        print(f"[temp={temp}] run {i+1}/20  {ms}ms  {tags}", flush=True)

print("DONE", len(results), "runs")
