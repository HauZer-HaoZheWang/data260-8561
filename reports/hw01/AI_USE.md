# AI_USE

## 1. What I used an AI assistant for, and what I did myself

Used AI for: explaining concepts (HTML form semantics, closures, temperature and
sampling, tokenization, context windows), debugging shell and Python errors,
and getting file skeletons with blanks to fill in.

Did myself: all design decisions (entity definition, primary/secondary field
choice, the Funder Type category axis and the rejected alternatives), the
coerce_reply implementation, all filled-in code, running every experiment, and
interpreting the results.

## 2. One AI-produced output that was wrong or unsuitable

The provided course skeleton used `from langchain_community.chat_models import
ChatOllama`. On langchain 1.3.18 this import fails: ChatOllama has been moved
out of langchain-community into the standalone langchain-ollama package.

An AI assistant also predicted that qwen3's thinking mode would corrupt JSON
parsing in the agent pipeline. That prediction turned out to be wrong for this
setup.

## 3. How I detected the problem or verified the result

For the import: running the script produced
`ImportError: cannot import name 'ChatOllama' from 'langchain_community.chat_models'`,
plus a deprecation warning stating langchain-community is being sunset.

For the thinking mode: I ran `ollama run qwen3:8b` directly and observed a large
`<think>` block before the answer. I then added a temporary debug print of the
raw model output inside SimpleAgent.respond and inspected it. The raw output was
clean JSON with no think block, because ChatOllama was configured with
`format="json"`, which suppresses it.

I also found a real bug this way. In the five-turn client session, turn 3
returned the bullet "The code is invalid due to the /think suffix." The model was
reviewing a `/think` marker that I never typed, meaning the thinking-mode control
token leaked into the user message it received.

## 4. What I changed and why it works now

Changed the import to `from langchain_ollama import ChatOllama` after installing
langchain-ollama. This is the maintained standalone integration package and is
the one referenced in the assignment reading materials.

Kept `format="json"` in the ChatOllama constructor, since the raw-output check
confirmed it already suppresses the think block, so no stripping logic was
needed in extract_json_block.

The direct ollama.chat call in src/model_client.py returns thinking in a separate
`message.thinking` field, so `message.content` is clean. Token counts come from
`prompt_eval_count` and `eval_count`; note that eval_count includes the thinking
tokens, so reported output tokens are substantially higher than the visible reply.
