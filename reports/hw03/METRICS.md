# HW3 Retrieval Metrics

## Configuration

- SID4: 8561
- PREFIX: s8561
- SEED: 8561
- VERIFY_SEED: 268561
- DOMAIN_ID: 1
- Domain: Clinical Trial Listings
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimension: 384
- Generation model: None
- Retrieval top-k: 5
- Corpus documents: 100
- Corpus size: 548,872 bytes
- Graded run date: 2026-09-20
- Graded run start: 2026-09-20T18:08:58-07:00
- Questions correction commit: `1f29b0d`

## Metric Definitions

- **Chunks**: Total nodes produced from the 100 corpus documents.
- **Average chunk length**: Mean length of `node.text` in characters.
- **Top-1 cosine**: Highest manually calculated cosine similarity among the
  returned top five nodes. The table reports the mean across five questions.
- **Mean@5 cosine**: Mean manual cosine similarity of the five retrieved nodes,
  averaged across all five questions.
- **Recall@5**: A binary value for each question. It is 1 when at least one
  retrieved node has a `source_file` matching the question's
  `expected_source`, and 0 otherwise. The summary reports the mean across
  questions.
- **Retrieval latency**: Time spent in the in-memory similarity search. Query
  embedding time and explicit document re-embedding time are excluded.
- **Sentence-window length**: The indexed single-sentence node length. The
  neighboring window is retained in metadata for display and is not used for
  manual cosine calculation.
- **Chunking and indexing time**: Measured after the embedding model was loaded.
  Initial model download and loading time are excluded.

## Main Retrieval Comparison

| Technique | Chunks | Avg chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency |
|---|---:|---:|---:|---:|---:|---:|
| Token | 692 | 916.327 chars | 0.695357 | 0.597878 | 1.000 | 5.231 ms |
| Semantic 95 | 299 | 1,833.659 chars | 0.651176 | 0.542636 | 1.000 | 2.291 ms |
| Sentence-window | 3,233 | 169.584 chars | 0.684724 | 0.611694 | 1.000 | 24.063 ms |

## Chunking and Indexing Cost

| Technique | Chunking time | Indexing time |
|---|---:|---:|
| Token | 0.348 s | 2.332 s |
| Semantic 95 | 8.016 s | 0.990 s |
| Sentence-window | 0.087 s | 7.109 s |
| Semantic tuned 80 | 7.642 s | 2.447 s |

Semantic splitting is slower during chunk creation because it embeds sentences
to identify semantic boundaries. Token and sentence-window splitting are
rule-based. Sentence-window has the highest indexing cost because it creates
3,233 nodes, more than four times the Token count and more than ten times the
Semantic 95 count.

Semantic 95 has the lowest retrieval latency because its index contains only
299 nodes. Sentence-window is the slowest because its index contains 3,233
single-sentence nodes.

## Per-Question Main Results

### Top-1 Cosine

| Question | Token | Semantic 95 | Sentence-window |
|---|---:|---:|---:|
| Q1 | 0.639076 | 0.586228 | 0.720197 |
| Q2 | 0.808809 | 0.740519 | 0.800927 |
| Q3 | 0.600887 | 0.574956 | 0.574956 |
| Q4 | 0.688238 | 0.708671 | 0.724010 |
| Q5 | 0.739773 | 0.645509 | 0.603529 |

Token had the highest Top-1 cosine on Q2, Q3, and Q5. Sentence-window had the
highest Top-1 cosine on Q1 and Q4.

### Mean@5 Cosine

| Question | Token | Semantic 95 | Sentence-window |
|---|---:|---:|---:|
| Q1 | 0.533401 | 0.474282 | 0.590039 |
| Q2 | 0.660311 | 0.569848 | 0.706505 |
| Q3 | 0.558540 | 0.510237 | 0.552801 |
| Q4 | 0.650957 | 0.618898 | 0.675762 |
| Q5 | 0.586181 | 0.539913 | 0.533362 |

Sentence-window had the highest overall Mean@5 cosine, but Token had the highest
Mean@5 score on Q3 and Q5. All three techniques achieved Recall@5 of 1.0 on
all five questions.

## Chunk Size Diagnostic

MiniLM truncates inputs longer than its 256-token input limit. Token counts were
measured with the MiniLM tokenizer across the full corpus.

| Technique | Nodes | Median tokens | P90 tokens | Max tokens | Over 256 | Over-limit rate | Estimated truncated tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Token | 692 | 213 | 229 | 257 | 1 | 0.14% | 1 |
| Semantic 95 | 299 | 324 | 863 | 1,760 | 181 | 60.54% | 58,858 |
| Semantic tuned 80 | 750 | 104 | 382 | 1,039 | 156 | 20.80% | 25,998 |
| Sentence-window | 3,233 | 25 | 73 | 806 | 30 | 0.93% | 4,655 |

The estimated truncated-token count is an approximation based on the
256-token limit. It is not a direct measurement of tokens discarded inside the
model.

Token chunking was almost completely within the MiniLM limit. Semantic 95
produced the fewest chunks, but 60.54% exceeded the embedding model's input
limit. Sentence-window was normally well below the limit, although a small
number of long eligibility paragraphs were treated as single sentences.

## Semantic Threshold Ablation

An additional Semantic Splitter experiment used percentile 80. This is an
ablation and is not part of the required three-technique main comparison.

| Technique | Chunks | Avg chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@5 | Mean latency |
|---|---:|---:|---:|---:|---:|---:|
| Semantic 95 | 299 | 1,833.659 chars | 0.651176 | 0.542636 | 1.000 | 2.291 ms |
| Semantic tuned 80 | 750 | 731.019 chars | 0.651176 | 0.571094 | 1.000 | 5.789 ms |

Changing the percentile from 95 to 80 reduced the over-limit rate from 60.54%
to 20.80% and reduced estimated truncated tokens from 58,858 to 25,998. Mean@5
cosine improved from 0.542636 to 0.571094, while mean Top-1 cosine remained
unchanged.

Lower threshold tests on a ten-document sample showed that reducing the
percentile did not enforce a maximum chunk size. Node count increased sharply,
but the longest semantically coherent blocks remained over the MiniLM limit.
Percentile 80 was retained as a compromise that reduced truncation exposure
without reducing most semantic chunks to near-sentence size.

## Confidently Scored Incorrect Retrieval

Q4 asked:

> What is the minimum age requirement for the lung cancer genetic analysis
> study sponsored by Massachusetts General Hospital?

The correct answer is 18 Years from `NCT00471978.txt`. However, every main
technique ranked a different lung-cancer study, `NCT07465848.txt`, above the
correct source.

| Technique | Wrong result rank | Wrong source | Wrong age | Store score | Manual cosine |
|---|---:|---|---:|---:|---:|
| Token | 1 | NCT07465848.txt | 45 Years | 0.665644 | 0.666341 |
| Semantic 95 | 1 | NCT07465848.txt | 45 Years | 0.700266 | 0.708671 |
| Sentence-window | 1 | NCT07465848.txt | 45 Years | 0.720796 | 0.708041 |

This result is confidently scored but incorrect. The corpus contains highly
repetitive clinical-trial language, and the exact line
`Minimum Age: 18 Years` occurs in 78 of the 100 documents. Both the requested
study and the incorrect result discuss lung-cancer eligibility. The embedding
model captured the shared topic and eligibility language but did not reliably
bind the sponsor and age value to the correct NCT record.

This also demonstrates that source Recall@5 does not guarantee that the
highest-ranked node contains the correct answer. The expected source appeared
somewhere in the top five for every technique, but the incorrect 45-year result
was ranked first.

## Store Score and Manual Cosine

Store scores and manually calculated cosine similarities were both recorded as
required. They are close but are not always identical, and their ordering can
differ.

The manual cosine calculation embeds only `node.text` with
`MetadataMode.NONE`. The vector index may include metadata in the representation
used during indexing. This difference in embedded content is the likely main
reason that the store score and manually calculated cosine do not always match.
No LLM or retrieval postprocessor was used.

## Observations

Token chunking produced the strongest overall balance. It achieved the highest
mean Top-1 cosine, perfect source Recall@5, a 5.231 ms mean retrieval latency,
and almost no MiniLM truncation. Fixed-size chunks also prevented long source
documents from producing unbounded individual nodes, although longer documents
still created more candidate chunks than shorter documents.

Sentence-window produced the highest Mean@5 cosine because short sentence
nodes focused embeddings on specific facts, while neighboring sentences were
retained in metadata for context. It also created 3,233 nodes and had the
highest retrieval latency. Semantic 95 produced only 299 nodes and had the
fastest search, but its large coherent chunks frequently exceeded MiniLM's
input limit. The threshold ablation improved Semantic Mean@5 quality, but it
did not solve the lack of a hard maximum chunk size.

The corpus itself is uneven: document sizes range from 1,933 to 25,209 bytes.
Long documents create more Token and Sentence-window nodes and therefore have
more opportunities to appear in top-k results. Repeated eligibility templates
also cause unrelated studies to receive high similarity scores.

## Conclusion

Token chunking is the best overall technique for this corpus. It produced the
highest mean Top-1 cosine, perfect Recall@5, low retrieval latency, and almost
no embedding truncation. Sentence-window is useful when broader top-k semantic
coverage matters, but it requires a much larger index and slower retrieval.
Semantic splitting was fastest at search time, but its uncontrolled chunk
lengths caused substantial MiniLM truncation and lower retrieval quality.

## AI Use

### 1. What was an AI assistant used for, and what did I do myself?

I used an AI assistant to interpret the homework requirements, review project
structure, draft code modules, suggest test commands, and help explain the
retrieval measurements. I selected the clinical-trial domain data, ran every
command locally, inspected the generated corpus, verified unique question
anchors, reviewed terminal output, and checked the final files and Git history.

### 2. What AI-produced output was wrong or unsuitable, or what did I independently verify?

The first pilot version of Q4 was unsuitable because it asked for a minimum age
without naming a specific trial and had `expected_source: None`. That question
could not have one objectively correct source and therefore did not satisfy the
assignment requirement.

### 3. How did I detect or verify the problem?

I detected the issue in the pilot retrieval output. Every technique printed
`Expected source: None` and `Recall@5: 0` for Q4. I compared that output with the
assignment requirement that every question record an expected answer and
expected source file.

### 4. What did I change, and why does it work now?

I replaced Q4 with a study-specific question naming the lung-cancer genetic
analysis study and Massachusetts General Hospital. I set the expected answer to
18 Years and the expected source to `NCT00471978.txt`. I committed the correction
as commit `1f29b0d` before starting the graded run. The corrected question has
one valid source, all techniques achieved source Recall@5 of 1, and it also
produced the required high-confidence incorrect retrieval example.