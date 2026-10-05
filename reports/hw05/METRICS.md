# HW5 Part 5 Agent Metrics

Local model: `qwen3:8b`.

| Scenario | Step count | Stop reason | Tool-call count |
| --- | ---: | --- | ---: |
| search | 2 | normal_completion | 1 |
| detail | 2 | normal_completion | 1 |
| aggregate_allowed | 2 | normal_completion | 1 |
| aggregate_blocked | 1 | safety_rule_block | 1 |
