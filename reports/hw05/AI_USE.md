# HW5 AI Use

## 1. What I used an AI assistant for and what I did myself

I used an AI assistant to help plan the implementation, draft small code changes,
suggest test cases, and organize the required evidence. I ran every command locally,
inspected the database and API results, exercised the MCP tools in Inspector, captured
the screenshots, and verified the final behavior myself.

## 2. One AI-produced output that was wrong or unsuitable

The first Part 5 agent scenario prompt was unsuitable. In the blocked aggregate
scenario, the local model changed `min_trials=1` to `min_trials=5`, so the run ended
normally instead of exercising the safety boundary. A later search scenario also tried
to call a second, unrelated tool after receiving its first tool result.

## 3. How I detected or verified the problem

I detected both problems from the structured console output and `agent_runs.jsonl`.
The reported stop reason was `normal_completion` instead of `safety_rule_block`, and
the tool-call count was larger than expected. I added assertions for the expected stop
reason and exactly one tool call per scenario, then reran all four scenarios.

## 4. What I changed and why it works now

I clarified that exact user-supplied inputs must reach application validation unchanged
and that the model must return a final action immediately after one tool result. The
scenario runner now fails instead of printing PASS when a stop reason or tool-call count
is wrong. The final run recorded three normal completions and one safety-rule block,
with exactly one tool call in every scenario.
