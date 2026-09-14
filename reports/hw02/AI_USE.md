# AI Use Disclosure

## 1. What I Used AI For and What I Did Myself

I used both Claude and ChatGPT/Codex while completing this assignment.

Claude helped me understand the assignment requirements, plan the implementation order, reason about the LangGraph state and routing logic, and diagnose bugs. It also helped identify issues such as stale reviewer feedback, the turn-ceiling routing order, JSON formatting, file paths, and the need to write CSV rows immediately.

ChatGPT/Codex produced the first draft of `verify_hw02.py` and the first draft of `METRICS.md`, including its structure and most of the analysis text. I supplied the deployment decision, the proposed fix, and the instruction-conflict analysis, and I verified every number against the raw CSV files. I also reviewed and adjusted the generated drafts to match my repository paths, experiment results, hardware, configuration, and actual observations.

I manually created, typed, integrated, and tested the following application files:

- `state.py`
- `nodes.py`
- `router.py`
- `workflow.py`
- `schema.py`
- `main.py`
- `app.js`
- `styles.css`

I wrote the `classify_result` logic in `run_batch.py`, including counting Planner entries in the trace and separating successful runs into first-attempt, one-retry, and two-or-more-retry categories.

The first draft of `verify_hw02.py` and substantial parts of `METRICS.md` were generated with AI assistance. I reviewed and adjusted them to match my repository paths, experiment results, hardware, configuration, and actual observations.

I personally performed the final integration and verification. This included:

- Running the FastAPI server
- Testing endpoints with curl and `/docs`
- Testing the frontend in the browser
- Inspecting Console and Network results
- Testing the page at a width of 375 pixels
- Running the standard, ceiling, and adversarial experiments
- Collecting screenshots and CSV results
- Checking the calculated means, medians, standard deviations, and completion rates
- Confirming that the final report matched the observed data
- Making the final architecture and deployment decisions

I also used AI tutoring to learn JavaScript concepts (closures, this binding, fetch, and async/await) before writing the frontend code.

## 2. Example of an Incorrect or Inappropriate AI Output

During an adversarial run, the LLM Reviewer reported that a summary contained 27 words. The deterministic Pydantic validator counted 30 words for the same summary.

The LLM therefore understood that the summary was too long, but its exact numerical count was incorrect. This showed that an LLM can perform approximate semantic review but should not be trusted to enforce exact numeric constraints such as word or character limits.

## 3. How I Discovered the Problem

I compared the issues produced by the LLM Reviewer with the issues produced by Pydantic for the same Planner proposal.

The Pydantic validator counted words using:

`len(summary.split())`

This returned 30 words, while the LLM Reviewer stated that the summary had 27 words. Because the code applied the same deterministic operation every time, I used the Pydantic result as the authoritative result.

I also inspected the actual Planner proposal and independently counted the words using the program rather than relying only on the model's explanation.

## 4. What I Changed and Why the Result Is Now Correct

I kept two validation layers in `reviewer_node`.

The LLM Reviewer performs semantic review and can identify problems related to meaning or topical relevance. Pydantic separately enforces the exact structural requirements:

- The output must contain exactly three tags.
- Every tag must contain between 3 and 30 characters.
- The summary must contain no more than 25 words.

If Pydantic raises a `ValidationError`, the code appends its error messages to `reviewer_feedback["issues"]` and sets:

`reviewer_feedback["approved"] = False`

This means that Pydantic can override an incorrect approval from the LLM. However, a successful Pydantic result does not remove issues reported by the LLM, because the LLM may have identified a semantic problem that is not represented by the schema.

The result is now more reliable because exact constraints are enforced by deterministic Python code, while the LLM is used for the type of semantic judgment it is better suited to perform.