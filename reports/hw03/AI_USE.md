# AI Use Statement — DATA 260 HW3

**Student:** Haozhe Wang  
**SID4:** 8561  
**Domain ID:** 1 — Clinical Trial Listings  
**Repository:** `data260-8561`

## Q1. How Was AI Used, and What Work Did I Complete Myself?

I used ChatGPT as a programming and debugging assistant during this assignment. AI was primarily used to propose initial structures, explain unfamiliar library behavior, suggest diagnostic procedures, and help organize the written analysis. I did not treat AI output as automatically correct. I ran the code locally, inspected the generated data, compared the results with the assignment requirements, and revised incorrect or unsuitable suggestions before the graded experiment.

### Work Supported by AI

AI helped with the following tasks:

1. It proposed the initial organization for the FastAPI authentication code, including separating the authentication routes into `routers/auth.py` and using Jinja2 templates for the home, login, and dashboard pages.

2. It suggested the general structure of the shared RAG modules, including `pipeline.py`, `chunkers.py`, `retrieval.py`, and `run_experiment.py`.

3. It explained that LlamaIndex uses OpenAI embeddings by default unless a local embedding model is configured explicitly. This led to the use of `sentence-transformers/all-MiniLM-L6-v2` and the explicit setting of `Settings.llm = None`.

4. It helped identify the difference between an absolute cookie lifetime and a sliding idle timeout. The final authentication implementation stores `last_seen` in the session, checks it on protected requests, and refreshes it after valid activity.

5. It suggested experimental diagnostics for comparing token, semantic, and sentence-window chunking, including chunk counts, average lengths, retrieval latency, Recall@k, and manual cosine similarity.

6. It suggested running a semantic-splitter threshold ablation after the default semantic chunks were found to exceed MiniLM’s 256-token input limit.

7. It helped organize the analysis of the retrieval failures, including the Q4 high-confidence false retrieval and the sentence-window Q3 failure.

8. It provided draft code and checklists for the verification process. I reviewed these checks, ran them locally, and used the results to identify missing evidence.

9. It helped organize and edit the written sections of `METRICS.md` and this AI-use statement.

### Work I Completed and Verified

I completed the following work directly:

1. I ran all installation, corpus-generation, diagnostic, retrieval, authentication, HTTPS, and verification commands in my local `data260` environment.

2. I used the ClinicalTrials.gov API v2 to obtain the source data and verified the rendered corpus. The final corpus contains 100 plain-text study records totaling 548,872 bytes.

3. I inspected individual corpus documents to confirm that fields such as titles, sponsors, eligibility criteria, enrollment, trial phase, and outcome measures were rendered correctly.

4. I maintained the corpus manifest, checked byte sizes and SHA-256 hashes, and confirmed that the manifest copies in `code/rag/` and `reports/hw03/` match.

5. I expanded the semantic threshold diagnostic beyond the initial values. I tested thresholds of 95, 90, 80, 70, 60, 50, and 40 to determine whether lowering the percentile could control chunk length.

6. I verified chunk sizes using the MiniLM tokenizer with truncation disabled. This was necessary because silent truncation would hide the true number of tokens excluded from an embedding.

7. I selected percentile 80 for the semantic ablation. It reduced the over-limit percentage substantially without reducing the median chunk length as aggressively as thresholds 70, 60, 50, or 40.

8. I discovered and corrected the invalid original Q4 design before the formal graded run.

9. I ran the final experiment and preserved the raw results, per-query JSON files, CSV summaries, terminal logs, and run metadata.

10. I manually inspected retrieval outputs instead of relying only on aggregate metrics. This inspection identified why sentence-window failed on Q3 and why every technique failed at rank one on Q4.

11. I verified that the Semantic 95 and Semantic 80 Top-1 chunks were exactly identical for all five questions by comparing their source files, text, lengths, scores, and SHA-256 hashes.

12. I tested the web application using both the browser and the automated verifier. This included invalid login, valid login, protected dashboard access, CRUD operations, logout, prevention of session reuse, idle expiration, and HTTPS cookie attributes.

13. I generated HTTPS evidence with `curl` and confirmed that the session cookie includes `Secure`, `HttpOnly`, and `SameSite=lax`.

14. I reviewed the verification output and corrected missing submission evidence instead of changing working application code unnecessarily.

All final conclusions in the report are based on the saved experimental outputs rather than on unverified AI predictions.

## Q2. Describe One AI Output That Was Incorrect or Not Suitable

The most important unsuitable AI-assisted output was the original design of question Q4.

The original Q4 was approximately:

> What is the minimum age requirement for participation in this trial?

It did not identify a particular trial, and its `expected_source` value was null. This made the question ambiguous because the corpus contains many clinical-trial records with minimum-age fields. In fact, the exact string `Minimum Age: 18 Years` appears in 78 of the 100 corpus documents.

This question was not suitable for the graded evaluation for two reasons:

1. It could not be scored consistently against one expected source document.

2. It did not satisfy the assignment requirement that questions depend on information found in a specified source document.

A null expected source would also make Recall@k misleading. A retrieval system cannot receive a correct source hit when no correct source has been defined.

There were several smaller AI outputs that also required correction:

- AI initially instructed me to create `routers/auth.py` under a `routers/` directory at the repository root. The actual application structure places the router at `code/web_application/routers/auth.py`. Following the original command caused `cat > routers/auth.py` to fail because the proposed root-level directory did not exist. I stopped, inspected the repository structure, confirmed where `main.py` and the web application files were located, and then created `routers/` under `code/web_application/`. This prevented the authentication module from being placed outside the application package.

- An early edit left overlapping `if __name__ == "__main__":` startup logic, which had to be consolidated into one valid startup block.

- AI initially warned that full semantic chunking might require tens of minutes. On my hardware, the completed full experiment took approximately 33–34 seconds, while semantic chunk construction itself took about eight seconds after model loading.

- An early explanation described `TokenTextSplitter(chunk_size=256)` as being precisely aligned with MiniLM’s 256-token limit. This was too strong because LlamaIndex’s token splitter and MiniLM’s WordPiece tokenizer are not guaranteed to use the same tokenization. The full diagnostic found one token chunk at 257 MiniLM tokens, confirming that the setting was close to, but not exactly identical to, the model limit.

These issues show why AI-generated explanations, file paths, and code require inspection and empirical verification before they are accepted.

## Q3. How Did I Detect the Problem?

I detected the Q4 problem during the pilot stage by reviewing `questions.yaml` against the assignment requirements and by inspecting the first retrieval results.

The expected source for Q4 was null, while the other questions named specific source files. That immediately showed that Q4 could not participate in the same source-based Recall@k calculation.

I also compared the question with the corpus itself. The question contained no NCT number, sponsor, treatment name, institution, or other unique identifier. Therefore, it did not specify which trial’s minimum age should be retrieved.

The corpus inspection made the ambiguity measurable:

```text
Minimum Age: 18 Years
```

appears in 78 of the 100 documents. A high-scoring result could therefore contain a plausible age field without answering a uniquely defined question.

The correction was made before the formal graded experiment. The relevant Git and run sequence is:

- `37fba41` — initial pre-registration of the five questions
- `1f29b0d` — correction of Q4 and its expected source
- Corrected question commit time: `2026-09-20T18:08:46-07:00`
- Formal experiment start: `2026-09-20T18:08:58-07:00`

The corrected question was committed approximately twelve seconds before the formal run began. The automated verification script confirms that the question commit predates the graded run.

I detected the directory problem separately when the proposed `cat > routers/auth.py` command failed because the root-level `routers/` directory did not exist. Instead of creating the directory immediately at the repository root, I inspected the existing project tree. That showed that the FastAPI application lived under `code/web_application/`, so the correct destination was `code/web_application/routers/auth.py`.

I detected the other issues through similar checks:

- Python compilation exposed the duplicated startup-block problem.

- Running the semantic splitter on a small sample showed that the original runtime estimate was too pessimistic.

- Comparing LlamaIndex chunk sizes with MiniLM token counts exposed the tokenizer mismatch and the semantic truncation problem.

- Inspecting full retrieved text, rather than only scores, exposed the template-driven Q3 and Q4 failures.

## Q4. What Did I Change, and Why Is the Final Version Correct?

I replaced the ambiguous Q4 with a trial-specific question:

> What is the minimum age requirement for the lung cancer genetic analysis study sponsored by Massachusetts General Hospital?

The final expected answer is:

```text
18 Years
```

The final expected source is:

```text
NCT00471978.txt
```

This version is valid because it includes multiple identifying details:

- lung cancer
- genetic analysis
- Massachusetts General Hospital

Together, these details identify the intended clinical-trial document. The expected source is now defined explicitly, so the question can be included in Recall@1 and Recall@5 calculations.

The correction also preserved the intended retrieval challenge. Although the expected source is unambiguous, the answer field itself is highly repetitive across the corpus. This produced a useful failure case:

- Token Top-1 source: `NCT07465848.txt`
- Semantic 95 Top-1 source: `NCT07465848.txt`
- Sentence-window Top-1 source: `NCT07465848.txt`
- Semantic 80 ablation Top-1 source: `NCT07465848.txt`

The incorrect Top-1 document reports a minimum age of 45 years. However, its eligibility content is highly similar to the expected lung-cancer trial, so every tested configuration ranked it above the correct source at rank one.

This result demonstrates that embedding similarity can capture the general clinical-trial topic and document structure without preserving the precise factual identity requested by the question. The corrected Q4 is therefore both scorable and analytically useful.

The correction also helped reveal that Recall@5 was saturated. All three main techniques achieved Recall@5 of 1.0, but Recall@1 provided additional separation.

### Main Chunking Techniques

- Token: 0.8
- Semantic 95: 0.8
- Sentence-window: 0.6

### Additional Ablation

- Semantic 80: 0.8

Semantic 80 is an additional ablation configuration and is not one of the three required main techniques.

The corrected Q4 contributes a real rank-one failure while still placing the expected source within the Top-5 results. This makes it useful for explaining why Recall@5 alone was not sufficiently discriminative for this corpus and question set.

## Final Reflection

AI was useful for accelerating implementation, suggesting diagnostics, and organizing the report, but several suggestions were incomplete, overly confident, or unsuitable for the exact assignment requirements.

The most important part of the process was not generating code quickly. It was checking each suggestion against:

- the assignment specification
- the actual repository structure
- the actual package behavior
- the corpus contents
- the saved retrieval results
- reproducible terminal evidence
- Git history

The final submission reflects the locally executed and verified system. AI did not participate in the retrieval pipeline itself. The experiment uses only the local `sentence-transformers/all-MiniLM-L6-v2` embedding model, and no generation model is used for retrieval or answer generation.