# Part 4 Offline Tool-Entry Tests

`code/mcp/tool_executor.py` defines the single `execute_tool(name, inputs)` entry
point used by the later agent. It dispatches only the three allowlisted domain
tools and serializes the shared `{ok, data, error}` envelope as a JSON string.
Unknown tools, malformed inputs, handler exceptions, and invalid handler return
values are converted to clean error envelopes rather than escaping as crashes.

`code/mcp/test_tool_executor.py` creates a temporary SQLite database and injects
fixture-backed handlers. It does not connect to MySQL and does not invoke an LLM.
The runner covers valid and rejected inputs for each of the three tools, plus an
unknown tool and an injected internal exception, for eight tests total.
