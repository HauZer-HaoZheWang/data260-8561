import ollama

MODEL = "qwen3:8b"


def complete(messages, tools=None):
    """Unified model adapter. All model calls go through this function."""
    resp = ollama.chat(model=MODEL, messages=messages)

    text = resp.message.content
    thinking = getattr(resp.message, "thinking", None) or ""

    return {
        "text": text,
        "thinking": thinking,
        "input_tokens": resp.get("prompt_eval_count", 0),
        "output_tokens": resp.get("eval_count", 0),
    }
