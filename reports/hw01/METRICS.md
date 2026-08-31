# METRICS - HW1

## Configuration

| Key | Value |
|---|---|
| SID4 | 8561 |
| PORT_BASE | 8461 |
| PREFIX | s8561 |
| SEED | 8561 |
| VERIFY_SEED | 268561 |
| DOMAIN_ID | 1 (Clinical trial listings) |
| Hardware | MacBook Pro 14, Apple M4, 16 GB |
| Local model | qwen3:8b (Ollama) |

## Part 3 - Non-determinism (40 runs)

Fixed input: reports/hw01/cases/nondeterminism_input.json

| Metric | Temp 0.7 | Temp 0.0 |
|---|---|---|
| Distinct tag sets | 13 | 1 |
| Tags in all 20 runs | Deep Brain Stimulation | Deep Brain Stimulation, Local Field Potentials, Neurological Disorders |
| Tags in exactly 1 run | 9 | 0 |
| Latency p50 / p95 / p99 (ms) | 92533 / 153022 / 180020 | 78362 / 81361 / 84505 |

### Observation

At temperature 0.7 the pipeline produced 13 different tag sets out of 20 runs.
Only "Deep Brain Stimulation" appeared in every run. Variation was almost
entirely in near-synonyms: Movement Disorders / Neurological Disorders /
Neurological Conditions, and Local Field Potentials / Electrophysiological
Recordings / Neurophysiological Data. The model was stable about what the text
is about, but unstable about which words to use.

At temperature 0.0 all 20 runs produced an identical tag set and latency varied
by under 7 percent. In this configuration greedy decoding was fully
reproducible. This is an empirical result, not a guarantee: reproducibility at
temperature 0 depends on hardware, batching and floating-point reduction order,
so a different machine or backend could still show variation.

## Part 4 - Token accounting (5-turn session)

| Turn | Input | Output | Total |
|---|---|---|---|
| 1 | 112 | 493 | 605 |
| 2 | 212 | 522 | 734 |
| 3 | 308 | 900 | 1208 |
| 4 | 431 | 467 | 898 |
| 5 | 549 | 561 | 1110 |

### /stats after turn 3

    turns                     : 3
    cumulative input tokens   : 632
    cumulative output tokens  : 1915
    serialized history length : 411 (estimated)

### /stats after turn 5

    turns                     : 5
    cumulative input tokens   : 1612
    cumulative output tokens  : 2943
    serialized history length : 647 (estimated)

### Observation

Cumulative input tokens grew 2.55x between turn 3 and turn 5, while the
serialized history length grew only 1.57x. These are different quantities:
cumulative input accumulates the full history once per turn, so it grows
quadratically, while the history itself grows linearly.

Note: serialized history length is estimated at about 4 characters per token,
since the qwen3 tokenizer was not available client-side.
