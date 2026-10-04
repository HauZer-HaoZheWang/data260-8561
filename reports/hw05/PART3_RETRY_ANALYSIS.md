# Part 3 Retry Policy Analysis

VERIFY_SEED = 268561. Each failure rate used 50 calls, for 150 calls total. The policy used 3 maximum attempts, a 0.5-second timeout, and bounded exponential backoff from 5 ms to 20 ms.

| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |
| ---: | ---: | ---: | ---: |
| 0% | 100.0% | 0.040 | 0.110 |
| 20% | 100.0% | 1.050 | 6.385 |
| 50% | 94.0% | 5.152 | 18.880 |

The policy is suitable for an interactive assistant because three bounded attempts recover most transient failures while keeping worst-case waiting short. The 50% condition shows the tradeoff: retries improve reliability but increase tail latency and still cannot guarantee success.

For batch processing, I would allow more attempts and longer timeouts because throughput and eventual completion matter more than immediate feedback. I would also increase the maximum backoff and add jitter so many workers do not retry at the same time.
