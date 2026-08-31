import sys
sys.path.insert(0, "src")
from model_client import complete

SYSTEM = open("AGENT.md").read()

messages = [{"role": "system", "content": SYSTEM}]
turn = 0
cum_in = 0
cum_out = 0


def history_tokens(msgs):
    """Estimate serialized conversation-history length (~4 chars per token)."""
    text = "".join(m["content"] for m in msgs)
    return len(text) // 4


def show_stats():
    print("--- STATS ---")
    print("turns                     :", turn)
    print("cumulative input tokens   :", cum_in)
    print("cumulative output tokens  :", cum_out)
    print("serialized history length :", history_tokens(messages), "(estimated)")
    print("-------------")


print("hw1_client — type /stats for statistics, /exit to quit")

while True:
    user = input("\n> ").strip()

    if user == "/stats":
        show_stats()
        continue
    if user in ("/exit", "/quit"):
        break
    if not user:
        continue

    messages.append({"role": "user", "content": user})
    r = complete(messages)
    messages.append({"role": "assistant", "content": r["text"]})

    turn += 1
    cum_in += r["input_tokens"]
    cum_out += r["output_tokens"]

    print("\n" + r["text"])
    print(f"\n[turn {turn}] input={r['input_tokens']} "
          f"output={r['output_tokens']} "
          f"total={r['input_tokens'] + r['output_tokens']}")

print("\n=== SESSION SUMMARY ===")
show_stats()
