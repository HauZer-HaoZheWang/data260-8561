# HW3 Retrieval Metrics

## Configuration

- SID4: 8561
- PORT_BASE: 8461
- PREFIX: s8561
- SEED: 8561
- VERIFY_SEED: 268561
- DOMAIN_ID: 1
- Domain: Clinical Trial Listings
- Hardware: Apple M4 with 16 GB unified memory
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimension: 384
- Generation model: None
- Experiment type: Retrieval only
- Retrieval top-k: 5
- Corpus documents: 100
- Corpus size: 548,872 bytes
- Graded run date: 2026-09-20
- Graded run start: 2026-09-20T18:08:58-07:00
- Questions correction commit: `1f29b0d`
- Experiment code commit: `11dd151`

## Dataset

The graded corpus contains 100 local plain-text snapshots generated from
ClinicalTrials.gov API v2 records.

Each study is stored as one text file named with its NCT number. The rendered
documents contain fields such as title, sponsor, condition, phase, enrollment,
eligibility criteria, interventions, primary outcomes, and outcome time
frames.

The original API response is preserved under:

```text
code/rag/raw_json/api_response.json
```

The rendered corpus is stored under:

```text
code/rag/corpus/
```

The corpus manifests are stored at:

```text
code/rag/CORPUS_MANIFEST.json
reports/hw03/CORPUS_MANIFEST.json
```

The corpus contains 548,872 bytes, approximately 2.7 times the required minimum
of 204,800 bytes.

## Experiment Design

The experiment compares three required LlamaIndex chunking techniques:

1. Token chunking using `TokenTextSplitter`
2. Semantic chunking using `SemanticSplitterNodeParser`
3. Sentence-window chunking using `SentenceWindowNodeParser`

An additional Semantic Splitter configuration with percentile 80 is included
as an ablation experiment. It is not treated as a fourth required technique.

All techniques use the same local embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

No generation model is used. The application sets:

```python
Settings.embed_model = embed_model
Settings.llm = None
```

The following message appeared during each experiment:

```text
LLM is explicitly disabled. Using MockLLM.
```

This confirms that the experiment is retrieval only and does not use a
generative LLM.

## Chunking Parameters

### Token

```text
chunk_size = 256
chunk_overlap = 32
```

### Semantic 95

```text
buffer_size = 1
breakpoint_percentile_threshold = 95
```

### Sentence-window

```text
window_size = 3
window_metadata_key = window
original_text_metadata_key = original_sentence
```

Each Sentence-window node contains one indexed sentence. Three neighboring
sentences on each side are retained in metadata for contextual display.

### Semantic Tuned 80 Ablation

```text
buffer_size = 1
breakpoint_percentile_threshold = 80
```

Percentile 80 was selected as a compromise that reduces truncation exposure
without reducing most semantic chunks to near-sentence size.

## Metric Definitions

- **Chunks**: Total nodes produced from the 100 corpus documents.
- **Average chunk length**: Mean length of `node.text` in characters.
- **Top-1 cosine**: Highest manually calculated cosine similarity among the
  returned five nodes. The summary reports the mean across five questions.
- **Mean@5 cosine**: Mean manually calculated cosine similarity of the five
  retrieved nodes, averaged across all five questions.
- **Recall@1**: A binary value for each question. It is 1 when the first-ranked
  result comes from the expected source and 0 otherwise.
- **Recall@5**: A binary value for each question. It is 1 when at least one of
  the five returned nodes has a `source_file` matching the question's
  `expected_source`.
- **Retrieval latency**: Time spent in the in-memory similarity search. Query
  embedding time and explicit document re-embedding time are excluded.
- **Sentence-window length**: Length of the indexed single-sentence node. The
  neighboring window is retained in metadata and is not used for manual cosine
  calculation.
- **Chunking and indexing time**: Measured after the embedding model was
  loaded. Initial model download and model-loading time are excluded.

## Main Retrieval Comparison

| Technique | Chunks | Avg chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@1 | Recall@5 | Mean retrieval latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Token | 692 | 916.327 chars | 0.695357 | 0.597878 | 0.800 | 1.000 | 5.231 ms |
| Semantic 95 | 299 | 1,833.659 chars | 0.651176 | 0.542636 | 0.800 | 1.000 | 2.291 ms |
| Sentence-window | 3,233 | 169.584 chars | 0.684724 | 0.611694 | 0.600 | 1.000 | 24.063 ms |

## Chunking and Indexing Cost

| Technique | Chunking time | Indexing time |
|---|---:|---:|
| Token | 0.348 s | 2.332 s |
| Semantic 95 | 8.016 s | 0.990 s |
| Sentence-window | 0.087 s | 7.109 s |
| Semantic tuned 80 | 7.642 s | 2.447 s |

Semantic splitting is slower during chunk creation because it embeds sentences
to identify semantic boundaries. Token and Sentence-window splitting are
rule-based.

Sentence-window has the highest indexing cost because it creates 3,233 nodes,
more than four times the Token count and more than ten times the Semantic 95
count.

Semantic 95 has the lowest retrieval latency because its index contains only
299 nodes. Sentence-window is the slowest because its index contains 3,233
single-sentence nodes.

## Per-Question Top-1 Cosine

| Question | Token | Semantic 95 | Sentence-window |
|---|---:|---:|---:|
| Q1 | 0.639076 | 0.586228 | 0.720197 |
| Q2 | 0.808809 | 0.740519 | 0.800927 |
| Q3 | 0.600887 | 0.574956 | 0.574956 |
| Q4 | 0.688238 | 0.708671 | 0.724010 |
| Q5 | 0.739773 | 0.645509 | 0.603529 |

Token had the highest Top-1 cosine on Q2, Q3, and Q5. Sentence-window had the
highest Top-1 cosine on Q1 and Q4.

## Per-Question Mean@5 Cosine

| Question | Token | Semantic 95 | Sentence-window |
|---|---:|---:|---:|
| Q1 | 0.533401 | 0.474282 | 0.590039 |
| Q2 | 0.660311 | 0.569848 | 0.706505 |
| Q3 | 0.558540 | 0.510237 | 0.552801 |
| Q4 | 0.650957 | 0.618898 | 0.675762 |
| Q5 | 0.586181 | 0.539913 | 0.533362 |

Sentence-window had the highest overall Mean@5 cosine. Token had the highest
Mean@5 cosine on Q3 and Q5.

## Recall Saturation

All three required techniques achieved Recall@5 of 1.0. This confirms that the
expected source appeared somewhere in the top five, but it does not distinguish
the techniques on this corpus.

The corpus contains only 100 documents, and several questions contain highly
distinctive anchors such as `GSTP1`, `ARV-6723`, and Arrowhead Pharmaceuticals.
These terms make it relatively easy for the correct document to appear
somewhere in five retrieved results.

Recall@1 provides more discrimination:

| Technique | Top-1 source hits | Recall@1 |
|---|---:|---:|
| Token | 4 of 5 | 0.800 |
| Semantic 95 | 4 of 5 | 0.800 |
| Sentence-window | 3 of 5 | 0.600 |
| Semantic tuned 80 | 4 of 5 | 0.800 |

Token and Semantic retrieved the expected source first for four questions.
Sentence-window retrieved the expected source first for three questions.

Recall@5 is therefore saturated at this corpus size and value of k. Cosine
similarity, Recall@1, latency, and truncation behavior provide more useful
distinctions among the techniques.

The only failure unique to Sentence-window was Q3. Q4 was missed at rank one by
all four configurations and was intentionally retained as the high-similarity
incorrect retrieval example.

## Chunk Size Diagnostic

MiniLM truncates inputs longer than its 256-token input limit. Token counts were
measured with the MiniLM tokenizer across the complete 100-document corpus.

| Technique | Nodes | Median tokens | P90 tokens | Max tokens | Over 256 | Over-limit rate | Estimated truncated tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Token | 692 | 213 | 229 | 257 | 1 | 0.14% | 1 |
| Semantic 95 | 299 | 324 | 863 | 1,760 | 181 | 60.54% | 58,858 |
| Semantic tuned 80 | 750 | 104 | 382 | 1,039 | 156 | 20.80% | 25,998 |
| Sentence-window | 3,233 | 25 | 73 | 806 | 30 | 0.93% | 4,655 |

The estimated truncated-token count is an approximation based on the
256-token limit. It is not a direct measurement of tokens discarded internally
by the model.

Token chunking was almost completely within the MiniLM limit. Only one Token
chunk exceeded the limit, and it exceeded it by one token.

Semantic 95 produced the fewest chunks, but 60.54% exceeded the embedding
model's input limit. This means the embedding did not represent the end of many
Semantic chunks.

Sentence-window was normally well below the limit. A small number of long
headers and Eligibility sections were treated as single sentences because the
source text did not contain normal sentence-ending punctuation.

## Semantic Threshold Exploration

The Semantic Splitter percentile was tested on a ten-document sample.

| Percentile | Nodes | Median tokens | P90 tokens | Max tokens | Over-limit rate | Estimated truncated tokens |
|---:|---:|---:|---:|---:|---:|---:|
| 95 | 24 | 324 | 680 | 894 | 70.8% | 4,153 |
| 90 | 34 | 260 | 653 | 894 | 50.0% | 3,276 |
| 80 | 54 | 133 | 354 | 680 | 25.9% | 1,771 |
| 70 | 73 | 80 | 299 | 632 | 16.4% | 1,384 |
| 60 | 93 | 61 | 257 | 632 | 10.8% | 858 |
| 50 | 110 | 43 | 233 | 632 | 7.3% | 820 |
| 40 | 130 | 30 | 202 | 632 | 5.4% | 803 |

Lowering the percentile creates more and smaller chunks. However, the maximum
chunk length remained 632 tokens from percentile 70 through percentile 40.

This occurs because `breakpoint_percentile_threshold` controls relative
semantic boundaries rather than imposing a hard maximum chunk size. A long and
semantically consistent paragraph can remain intact even when the percentile
is reduced.

Below percentile 60, additional splitting sharply reduced the median chunk
length but produced little improvement in estimated truncated tokens.
Percentile 80 was therefore retained as a compromise ablation.

## Semantic Threshold Ablation

The additional Semantic 80 experiment is not part of the required
three-technique comparison.

| Technique | Chunks | Avg chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@1 | Recall@5 | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semantic 95 | 299 | 1,833.659 chars | 0.651176 | 0.542636 | 0.800 | 1.000 | 2.291 ms |
| Semantic tuned 80 | 750 | 731.019 chars | 0.651176 | 0.571094 | 0.800 | 1.000 | 5.789 ms |

Changing the percentile from 95 to 80:

- Increased chunks from 299 to 750
- Reduced average chunk length from 1,833.659 to 731.019 characters
- Reduced the over-limit rate from 60.54% to 20.80%
- Reduced estimated truncated tokens from 58,858 to 25,998
- Improved Mean@5 cosine from 0.542636 to 0.571094
- Did not change mean Top-1 cosine
- Did not change Recall@1 or Recall@5
- Increased retrieval latency from 2.291 ms to 5.789 ms

## Why Semantic 95 and Semantic 80 Have the Same Top-1 Score

Semantic 95 and Semantic 80 produced exactly the same mean Top-1 cosine of
0.651176. This was independently checked using the complete saved chunk text.

For all five questions, both configurations had:

- The same Top-1 source file
- The same Top-1 chunk length
- Identical Top-1 chunk text
- The same SHA-256 hash
- The same store score
- The same manually calculated cosine similarity

| Question | Top-1 source | Chunk length | Identical text |
|---|---|---:|---|
| Q1 | NCT00471978.txt | 1,661 | Yes |
| Q2 | NCT07749586.txt | 2,163 | Yes |
| Q3 | NCT06937203.txt | 1,084 | Yes |
| Q4 | NCT07465848.txt | 376 | Yes |
| Q5 | NCT06160921.txt | 784 | Yes |

The saved SHA-256 hashes were identical between configurations for every
question.

This confirms that the percentile parameter was applied correctly. The two
configurations produced different total node counts and different Mean@5
cosine values. However, the most relevant semantic region for each question
was sufficiently cohesive to remain unbroken at both thresholds.

The percentile change affected lower-ranked candidates and improved Mean@5,
but it did not change any Top-1 chunk.

## Confidently Scored Incorrect Retrieval

Q4 asked:

> What is the minimum age requirement for the lung cancer genetic analysis
> study sponsored by Massachusetts General Hospital?

The correct answer is 18 Years from:

```text
NCT00471978.txt
```

However, every required technique ranked a different lung-cancer study,
`NCT07465848.txt`, above the correct source.

The incorrect study reported a minimum age of 45 Years.

| Technique | Wrong result rank | Wrong source | Wrong age | Store score | Manual cosine |
|---|---:|---|---:|---:|---:|
| Token | 1 | NCT07465848.txt | 45 Years | 0.665644 | 0.666341 |
| Semantic 95 | 1 | NCT07465848.txt | 45 Years | 0.700266 | 0.708671 |
| Sentence-window | 1 | NCT07465848.txt | 45 Years | 0.720796 | 0.708041 |

This result is confidently scored but incorrect.

The corpus contains highly repetitive clinical-trial language, and the exact
line:

```text
Minimum Age: 18 Years
```

appears in 78 of the 100 documents. Both the requested study and the incorrect
result discuss lung-cancer eligibility.

The embedding model captured shared topic and eligibility language but did not
reliably bind Massachusetts General Hospital, the correct age, and the target
NCT record.

This also shows that source Recall@5 does not guarantee that the highest-ranked
node contains the answer. The correct source appeared somewhere in the top five
for every technique, but the incorrect 45-year result was ranked first.

## Sentence-Window Q3 Failure Analysis

Q3 asked for the enrollment and phase of the Arrowhead Pharmaceuticals study
in obesity and type 2 diabetes.

The correct source was:

```text
NCT06937203.txt
```

Sentence-window returned:

| Rank | Source | Store score | Chunk length | Description |
|---:|---|---:|---:|---|
| 1 | NCT07296484.txt | 0.599353 | 441 | Incorrect CAPTAIN-T2D header block |
| 2 | NCT06937203.txt | 0.594625 | 855 | Correct document, but an eligibility block |
| 3 | NCT06937203.txt | 0.580185 | 1,027 | Correct header containing phase and enrollment |

The incorrect rank-1 result and correct rank-3 result were both structured
header blocks beginning with fields such as:

```text
NCT Number
Title
Official Title
Lead Sponsor
Overall Status
Study Type
Phases
Enrollment
Conditions
```

Sentence-window normally creates one node per sentence. However, these
newline-separated fields do not contain normal sentence-ending punctuation.
The sentence parser therefore treated the complete header region as one long
sentence instead of splitting individual fields.

The incorrect CAPTAIN-T2D header and the correct Arrowhead header have nearly
identical field structure and both contain type 2 diabetes terminology. The
unique identifier `Arrowhead Pharmaceuticals` was only one field inside a much
larger template-like block, so its contribution to the embedding was diluted.

The incorrect result scored 0.599353, while the correct header scored 0.580185,
a difference of only 0.019168.

This failure was not caused by the node being too small. It was caused by the
header being treated as one oversized, structurally repetitive sentence. The
same underlying corpus property also affected Q4, where repetitive Eligibility
blocks confused trials with different minimum-age values.

The correct document occupied both rank 2 and rank 3. A document-level
aggregation method that combines scores from multiple chunks belonging to the
same source could promote the correct document.

A simple maximum-score aggregation would not fix this example because the
incorrect document's maximum score was still higher. A top-n sum or another
multi-chunk aggregation method would be required and is outside the scope of
this retrieval-only comparison.

## Store Score and Manual Cosine

Store scores and manually calculated cosine similarities were both recorded as
required.

They are close but are not always identical, and their ordering can differ.

The manual cosine calculation explicitly embeds only:

```text
node.text
```

using `MetadataMode.NONE`.

The vector index may include embedding metadata in the representation used
during indexing. This difference in embedded content is the likely main reason
the store score and manual cosine do not always match.

The differences occur in both directions. For example, Token Q1 had a store
score of 0.636421 and a manual cosine of 0.599561 for its first result, while
Token Q2 had a store score of 0.786970 and a manual cosine of 0.808809.

This pattern is not consistent with one simple constant scaling factor. It is
more consistent with the indexed and manually re-embedded inputs containing
slightly different text or metadata.

No LLM, reranker, or retrieval postprocessor was used.

## Observations

### 1. Semantic Boundaries Do Not Control Chunk Size

Semantic splitting optimizes boundary coherence rather than enforcing a
maximum chunk length.

Semantic 95 produced only 299 chunks, but 60.54% exceeded MiniLM's 256-token
input limit. The estimated truncation exposure was 58,858 tokens.

Lowering the percentile to 80 increased the node count to 750 and reduced
estimated truncation to 25,998 tokens. However, it did not impose a hard size
limit.

Sample experiments from percentile 95 through percentile 40 showed that the
longest chunk remained above 600 tokens even while the median dropped from 324
to 30 tokens.

The percentile is calculated from relative semantic distances. A long,
semantically consistent paragraph may therefore remain intact at multiple
thresholds. Lowering the threshold eventually fragments ordinary text while
providing little additional improvement for the longest coherent blocks.

Semantic 95 and Semantic 80 also returned exactly the same Top-1 chunk for all
five questions. Complete text and SHA-256 comparison confirmed that the five
pairs were identical.

The threshold change affected lower-ranked results and improved Mean@5 cosine,
but the most relevant semantic region for each question remained unbroken at
both thresholds.

### 2. Template-Like Clinical Records Cause Structurally Similar Chunks to Compete

The main retrieval errors were caused by repeated document structure.

For Q4, every main technique ranked the Eligibility section of
`NCT07465848.txt` above the expected `NCT00471978.txt`. The wrong result stated
a minimum age of 45 Years, while the expected answer was 18 Years.

Both documents discussed lung-cancer eligibility, and the corpus contained many
nearly identical age and eligibility fields.

Q3 showed the same mechanism in the document header. Sentence-window treated
the newline-separated header fields as one sentence because they lacked normal
sentence-ending punctuation.

The incorrect CAPTAIN-T2D header and correct Arrowhead header had the same
field order and shared type 2 diabetes terminology. The unique sponsor field
was diluted inside the larger template block.

These failures occurred in different parts of the records, Eligibility and
header fields, but had the same cause: structurally similar template text
received high embedding similarity even when the trial-specific entity or
numeric answer was wrong.

The corpus also has a 13-times document-size range. Long records create more
Token and Sentence-window nodes and therefore have more opportunities to appear
in top-k results.

### 3. High Similarity Does Not Guarantee That a Chunk Contains the Answer

Sentence-window achieved the highest Mean@5 cosine at 0.611694, but it had the
lowest Recall@1 at 0.600. Token and Semantic 95 both achieved Recall@1 of
0.800.

Sentence-window produced highly focused embeddings for ordinary sentences, as
shown by its strong Q1 and Q2 scores. However, the method depends on the
sentence parser identifying meaningful boundaries.

Header fields and some Eligibility sections did not contain normal punctuation,
so they became large single nodes instead of fine-grained sentence nodes.

The Q3 incorrect result scored 0.599353, only 0.019168 above the correct header.
The Q4 incorrect result scored 0.720796 even though it contained the wrong
minimum age.

These cases demonstrate that a confident embedding score measures semantic and
structural similarity, not factual correctness.

Recall@5 was 1.0 for every method and was therefore saturated on this
100-document corpus. Distinctive anchors made it relatively easy for the
correct source to appear somewhere in five results.

Recall@1, cosine measurements, latency, and truncation behavior provided more
useful discrimination.

### Overall Comparison

Token chunking provided the strongest balance. It achieved the highest mean
Top-1 cosine, Recall@1 of 0.800, perfect Recall@5, a mean latency of 5.231 ms,
and almost no MiniLM truncation.

Semantic 95 searched fastest because it created only 299 nodes, but its large
chunks caused severe truncation and produced the lowest cosine measurements.

Semantic 80 improved Mean@5 and reduced truncation exposure, but it did not
change any Top-1 result.

Sentence-window achieved the highest Mean@5 cosine, but it created 3,233 nodes,
had the highest latency, and achieved the lowest Recall@1. Its expected
fine-grained behavior also failed on punctuation-free structured fields.

## Conclusion

Token chunking is the best overall technique for this clinical-trial corpus.
It achieved the highest mean Top-1 cosine, Recall@1 of 0.800, perfect Recall@5,
low retrieval latency, and almost no embedding truncation.

Sentence-window produced the highest Mean@5 cosine but the lowest Recall@1. Its
main failure occurred when newline-separated header fields were treated as one
long sentence, allowing a structurally similar but incorrect trial to rank
above the correct Arrowhead study.

Semantic 95 matched Token's Recall@1 and had the fastest search, but its
uncontrolled chunk lengths caused substantial MiniLM truncation. Semantic 80
reduced truncation and improved lower-ranked results, but all five Top-1 chunks
remained identical to Semantic 95.

The dominant difficulty was not only chunk size. Repetitive ClinicalTrials.gov
headers and Eligibility templates caused semantically similar chunks from
different trials to compete.

Future work could combine chunk retrieval with document-level top-n score
aggregation or metadata-aware filtering, but those postprocessing methods are
outside the required retrieval-only comparison.

## AI Use

### 1. What was an AI assistant used for, and what did I do myself?

I used an AI assistant to interpret the homework requirements, review the
project structure, draft code modules, suggest test commands, and help explain
retrieval measurements.

I selected the clinical-trial corpus, ran every command locally, inspected the
rendered documents, identified unique question anchors, verified corpus sizes
and hashes, reviewed terminal output, and checked the final files and Git
history.

I also independently decided which unexpected results required additional
validation, including Recall@1, the Semantic Top-1 equality, and the
Sentence-window Q3 failure.

### 2. What AI-produced output was wrong or unsuitable, or what did I independently verify?

The first pilot version of Q4 was unsuitable because it asked for a minimum age
without naming a specific trial and had:

```text
expected_source: None
```

That question could not have one objectively correct source and did not satisfy
the assignment requirement.

The initial estimate that Semantic splitting might require tens of minutes was
also too high. The measured full-corpus Semantic chunking time was approximately
eight seconds after the embedding model was loaded.

The initial explanation for Sentence-window's Q3 failure was also incomplete.
The failure was first attributed to overly small chunks. Inspection of the
actual returned text showed the opposite: newline-separated header fields were
treated as one large sentence.

I also independently verified the unexpected result that Semantic 95 and
Semantic 80 had exactly the same mean Top-1 cosine.

### 3. How did I detect or verify the problem?

I detected the Q4 issue in the pilot retrieval output. Every technique printed:

```text
Expected source: None
Recall@5: 0
```

I compared this output with the assignment requirement that every question
record an expected answer and expected source file.

I verified the Semantic Top-1 equality by comparing complete saved chunk text,
source filenames, chunk lengths, store scores, cosine similarities, and SHA-256
hashes. All five Top-1 chunks were identical between Semantic 95 and Semantic
80.

I inspected the complete Sentence-window Q3 results. The incorrect rank-1 block
and correct rank-3 block were both large structured headers rather than short
isolated fields. This showed that missing sentence punctuation, not excessive
fragmentation, caused the failure.

I also measured actual Semantic runtime instead of relying on the original
estimate.

### 4. What did I change, and why does it work now?

I replaced Q4 with a study-specific question naming the lung-cancer genetic
analysis study and Massachusetts General Hospital.

I set:

```text
Expected answer: 18 Years
Expected source: NCT00471978.txt
```

I committed this correction as commit `1f29b0d` before starting the graded
retrieval run. The corrected question has one valid source, and all techniques
achieved source Recall@5 of 1.

I added Recall@1 because Recall@5 was saturated. Recall@1 distinguishes the
techniques and shows that Token and Semantic 95 retrieved the expected source
first for four questions, while Sentence-window did so for three.

I retained Semantic 80 as an ablation because it reduces estimated truncation
while preserving more semantic context than lower percentiles. The saved
Top-1 comparison confirms that its unchanged Top-1 score is a genuine result,
not a parameter or implementation bug.

I replaced the initial Sentence-window explanation with one supported by the
actual retrieved chunks. The final explanation identifies punctuation-free,
template-like header blocks as the cause of Q3's incorrect Top-1 result.

## Machine-Readable Evidence

The experiment produced:

```text
reports/hw03/raw/chunk_metrics.csv
reports/hw03/raw/chunk_size_diagnostic.csv
reports/hw03/raw/per_query_metrics.csv
reports/hw03/raw/recall_at_1.csv
reports/hw03/raw/recall_at_1_summary.csv
reports/hw03/raw/retrieval_results.jsonl
reports/hw03/raw/run_metadata.json
reports/hw03/raw/semantic_top1_comparison.csv
reports/hw03/raw/summary_metrics.csv
```

Per-question JSON files are stored under:

```text
reports/hw03/raw/token/
reports/hw03/raw/semantic_95/
reports/hw03/raw/semantic_tuned_80/
reports/hw03/raw/sentence_window/
```