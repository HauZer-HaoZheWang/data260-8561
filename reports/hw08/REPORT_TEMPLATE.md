# DATA 260 Homework 8

**Student:** Haozhe Wang  
**SID4:** 8561  
**Repository:** paste GitHub URL here  
**Hardware:** Apple Silicon Mac, paste exact model/RAM here  
**Local model:** qwen3:8b through Ollama  
**Tagged commit:** paste `git rev-parse hw8` here  

## Section 0 - Configuration

| Value | Result |
|---|---:|
| SID4 | 8561 |
| PORT_BASE | 8461 |
| PREFIX | s8561 |
| SEED | 8561 |
| VERIFY_SEED | 268561 |
| DOMAIN_ID | 1 |

## Part 1 - Kafka Trial request/response

Explain that the client creates one correlation ID, sends it unchanged through
the request topic, worker, response topic, and final client response. Insert
screenshots `P1_01` through `P1_05` from the checklist.

## Part 2 - Three-agent pipeline

Describe the four topics and insert `P2_01` and `P2_02`.

## Part 3 - Failure behavior

| Failure scenario | Before fix | After fix | Screenshot/raw evidence |
|---|---|---|---|
| Duplicate delivery | paste real observation | paste real observation | P3_01 / raw file |
| Consumer killed mid-work | paste real observation | paste real observation | P3_02 / raw file |
| Poison message | paste real observation | paste real observation | P3_03 / raw file |
| Two partitions/two consumers | paste real observation | paste real observation | P3_04 / raw file |

Kafka benefits: independent scaling and decoupled failure. New
responsibilities: duplicate handling and ordering/offset management.

## Verification and submission

Insert `P4_01`. Confirm `verification.json` contains the tagged commit and the
real pass/fail results. Include the AI_USE answers in the final PDF.
