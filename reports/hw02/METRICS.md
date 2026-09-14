# HW02 Metrics Report

## Configuration

| Item | Value |
|---|---|
| Homework | HW02 |
| SID4 | 8561 |
| PORT_BASE | 8461 |
| PREFIX | s8561 |
| SEED | 8561 |
| VERIFY_SEED | 268561 |
| DOMAIN_ID | 1 |
| Hardware | Apple M4, 16 GB memory |
| Model | qwen3:8b |
| Model runtime | Ollama, running locally |
| Commit | `<fill in after creating the final tag>` |

## Part 4.3 — Schema Validation and Retry Behavior

The workflow was executed 30 times using the standard schema input and a turn ceiling of 6.

| Outcome | Count | Mean latency (ms) |
|---|---:|---:|
| Valid first attempt | 30 | 58,623 |
| Valid after 1 retry | 0 | — |
| Valid after 2+ retries | 0 | — |
| Hit turn ceiling | 0 | — |

All 30 standard runs produced a valid result on the first attempt. No run required a retry or reached the turn ceiling. The mean latency was 58,623 ms.

This result suggests that the Planner prompt and Pydantic validation rules were well aligned for the standard input. The Planner consistently returned exactly three tags, kept each tag within the required character range, and produced a summary of no more than 25 words.

However, because every standard run passed immediately, Part 4.3 alone does not demonstrate the behavior of the retry mechanism. The adversarial experiment in Part 4.5 provides that evidence.

## Part 4.4 — Turn Ceiling Comparison

The workflow was executed 20 times with a ceiling of 2 and another 20 times with a ceiling of 10.

| Ceiling | Completion rate | Mean latency (ms) | SD (ms) | Median (ms) |
|---:|---:|---:|---:|---:|
| 2 | 20/20 = 100% | 62,433 | 12,824 | 63,308 |
| 10 | 20/20 = 100% | 63,643 | 13,622 | 62,166 |

Both ceiling settings achieved an observed completion rate of 100%. The mean latency was 62,433 ms with ceiling 2 and 63,643 ms with ceiling 10, producing a difference of 1,210 ms.

The standard errors of the two means were approximately:

- Ceiling 2: 12,824 / sqrt(20) = 2,868 ms
- Ceiling 10: 13,622 / sqrt(20) = 3,046 ms

SE(difference) = sqrt(2868^2 + 3046^2) ≈ 4,184 ms

1,210 / 4,184 ≈ 0.29 standard errors

The observed mean difference was only 0.29 standard errors. In addition, the ordering of the means and medians was reversed: ceiling 2 had the lower mean, while ceiling 10 had the lower median. Therefore, this experiment did not detect a meaningful latency difference between the two ceiling settings.

The two observed completion rates should not be interpreted as proof that the settings are exactly equivalent. With zero failures in 20 runs, the rule of three gives an approximate 95% upper bound for the true failure rate:

Rule of three: 3 / 20 = 15% upper bound

The appropriate conclusion is that no completion-rate difference was detected with 20 runs per configuration, rather than that their true completion rates are identical.

### Deployment Decision

I would select a turn ceiling of 2 for deployment under the workload represented by the standard input.

Both configurations achieved 100% observed completion, and the latency difference was small relative to its uncertainty. Ceiling 10 did not provide a measurable completion-rate or latency benefit in these experiments because every standard run passed on the first attempt.

Ceiling 2 also places a lower upper bound on worst-case latency, token usage, and computational cost. Ceiling 10 provides five times the turn budget, but the standard experiments never used that additional budget.

This decision applies to the tested standard workload. If adversarial or unusually difficult inputs are common in production, the ceiling should be reconsidered because Part 4.5 shows that additional retries can recover some difficult cases.

## Part 4.5 — Adversarial Input

The workflow was executed five times using an adversarial input.

| Outcome | Count |
|---|---:|
| Valid first attempt | 0 |
| Valid after 1 retry | 2 |
| Valid after 2+ retries | 2 |
| Hit turn ceiling | 1 |

The mean adversarial latency was 372,891 ms.

The adversarial input triggered at least one retry in all five runs, compared with zero retries across the 30 standard runs. Two runs became valid after one retry, two became valid after two or more retries, and one reached the turn ceiling.

Therefore, the retry mechanism recovered four out of five adversarial runs, producing an observed completion rate of 80%. The turn ceiling safely stopped the remaining run instead of allowing the workflow to continue indefinitely.

### Why the Adversarial Input Causes Trouble

The adversarial content explicitly required the Planner to use three controlled-vocabulary tags containing 48, 43, and 56 characters. It also instructed the model not to shorten, abbreviate, paraphrase, or replace those tags.

These content-level instructions directly conflicted with the system requirement that every tag contain between 3 and 30 characters.

The observed output showed that the model attempted to compromise between the conflicting instructions. In one run, it shortened the tags to lengths of 31, 29, and 42 characters. This demonstrated partial correction, but the 31-character and 42-character tags still failed Pydantic validation.

The 31-character result is especially informative because it exceeded the limit by only one character. It suggests that the model understood the request to shorten the tag but did not count the characters accurately enough to satisfy the exact boundary.

The adversarial input therefore caused trouble through a direct instruction conflict:

1. The system prompt required short tags.
2. The content required exact, long tags.
3. Reviewer feedback requested correction.
4. The model shortened some tags but did not always shorten them enough.
5. Pydantic rejected any result that remained outside the exact limit.

### Proposed Fix

One proposed fix is to make the retry feedback more explicit and include a safety margin.

Instead of only reporting:

> Tag has 31 characters; each tag must have between 3 and 30 characters.

the Reviewer could instruct:

> Replace this tag with a semantically equivalent tag containing no more than 25 characters. Do not preserve the original long wording. Verify the length of all three tags before returning the revised JSON.

Using 25 characters as the retry target provides a five-character safety margin below the actual 30-character limit. This reduces the chance that the model will produce another borderline value such as 31 characters.

This approach is preferable to automatically truncating every tag at 30 characters because hard truncation could cut a word in the middle or damage the tag's meaning. Pydantic would remain the authoritative validator, while the stronger feedback would help the Planner converge more reliably.

### Latency Impact

The normal first-attempt mean latency was 58,623 ms, while the adversarial mean latency was 372,891 ms.

372,891 / 58,623 ≈ 6.36

The adversarial input was therefore approximately 6.4 times slower.

This increase is consistent with the additional Planner and Reviewer calls required during repeated validation and revision cycles. The experiment demonstrates both the benefit and cost of retry behavior: retries recovered 80% of the adversarial runs, but substantially increased latency and token usage.

The adversarial input did not cause four out of five runs to hit the ceiling. Instead, it caused all five runs to enter the retry path, while four eventually recovered. This shows that the input successfully stressed the workflow and that the Reviewer feedback and retry mechanism were relatively robust.

## Overall Conclusion

The standard experiments show that the workflow is efficient when the Planner receives a clear and ordinary input. All 30 standard runs passed immediately, and changing the ceiling from 2 to 10 produced no detectable improvement in completion rate or latency.

The adversarial experiment produced a different result. Every adversarial run required at least one retry, four out of five runs eventually recovered, and one reached the ceiling. The mean latency increased by approximately 6.4 times.

These results show that retries add little value for easy inputs that already pass immediately, but can recover difficult inputs at the cost of higher latency, token usage, and computational expense.

## Notes on Data Collection

- The main batch process was terminated by the operating system because of memory pressure during run 17.
- Ollama was restarted, and the remaining 53 runs were then completed.
- The adversarial batch became stuck during its third run because the LLM request had no timeout.
- The stuck process was terminated, and the remaining two adversarial runs were completed afterward.
- Restarting the scripts caused some `run_number` values to appear more than once.
- Results were therefore analyzed by CSV row order rather than by assuming that `run_number` was globally unique.
- A robustness limitation was identified in `model_client.py`: the `ollama.chat()` call does not define a timeout. If an LLM request hangs, the workflow can remain blocked indefinitely.
- The experiment scripts wrote each completed result to CSV immediately, so completed runs were preserved when later runs failed or were terminated.