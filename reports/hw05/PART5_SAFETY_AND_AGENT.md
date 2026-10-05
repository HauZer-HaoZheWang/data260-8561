# Part 5 Safety Rule and Agent Loop

The domain safety rule is enforced inside `execute_tool`, not in the language
model. Sponsor aggregate calls require `min_trials >= 5`; smaller requests return
`{ok: false, data: null, error: "safety rule: ..."}` without querying the database.

`run_agent(user_input)` uses the local `qwen3:8b` Ollama model to select among the
three allowlisted domain tools. The harness owns tool execution, records every
model action and tool result, and stops on normal completion, a safety block, a
model error, or the `max_steps` ceiling. Each run is appended as one JSON object
to `reports/hw05/agent_runs.jsonl`.

The offline test runner uses `MockModel` to verify the `max_steps` stop without
Ollama, MySQL, an external API, or an API key.
