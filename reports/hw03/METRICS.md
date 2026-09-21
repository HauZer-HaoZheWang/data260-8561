# HW3 Retrieval Metrics and Analysis

## Configuration

| Item | Value |
|---|---|
| SID4 | 8561 |
| Prefix | s8561 |
| Port | 8461 |
| Experiment seed | 8561 |
| Verification seed | 268561 |
| Domain ID | 1 |
| Domain | Clinical Trial Listings |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimensions | 384 |
| Generation model | None |
| Retrieval mode | Retrieval only |
| Retrieval depth | Top 5 |
| Hardware | Apple M4, 16 GB memory |
| Main techniques | Token, Semantic 95, Sentence-window |
| Additional ablation | Semantic tuned 80 |

`Settings.llm` was set to `None`. No generation model, reranker, or retrieval postprocessor was used.

The embedding model was configured before constructing any index or semantic splitter. This prevented LlamaIndex from attempting to use its default OpenAI embedding configuration.

## Dataset

The corpus contains 100 ClinicalTrials.gov records related to recruiting studies involving diabetes, lung cancer, or hypertension.

| Property | Value |
|---|---:|
| Files | 100 |
| Total bytes | 548,872 |
| Total UTF-8 characters | 548,264 |
| Minimum file size | 1,933 bytes |
| Maximum file size | 25,209 bytes |
| Required minimum | 204,800 bytes |
| Requirement status | Satisfied |
| Size relative to minimum | Approximately 2.7 times |

The difference between the byte and character counts is caused by multibyte UTF-8 characters in organization names and other clinical-trial text.

The corpus has two important characteristics.

First, document size varies by approximately thirteen times. Fixed token chunking therefore creates many chunks for long documents and fewer chunks for short documents.

Second, the records contain repeated structured fields and boilerplate eligibility language. For example, `Minimum Age: 18 Years` appears in many records. Similar language from unrelated trials can therefore produce high embedding similarity without identifying the requested study.

The corpus manifest is stored in both locations:

- `code/rag/CORPUS_MANIFEST.json`
- `reports/hw03/CORPUS_MANIFEST.json`

The verification script confirmed that the two manifest copies match and that all 100 corpus hashes are valid.

## Experiment Design

Five questions were registered before the graded experiment. Each question has one expected source document.

| ID | Question purpose | Expected source |
|---|---|---|
| Q1 | Lung-cancer germline polymorphisms and outcome time frame | NCT00471978.txt |
| Q2 | ARV-6723 dose-limiting toxicity assessment period | NCT07749586.txt |
| Q3 | Arrowhead obesity and type 2 diabetes enrollment and phase | NCT06937203.txt |
| Q4 | Minimum age for the Massachusetts General Hospital lung-cancer genetic study | NCT00471978.txt |
| Q5 | Resistant hypertension and mortality over ten-year follow-up | NCT06160921.txt |

The questions were committed before the formal experiment. Q4 was corrected before the graded run because its earlier version did not identify a unique source and could not be scored consistently with the other questions.

For each technique, the experiment performed the following operations:

1. Load the same 100 source documents.
2. Split the documents using the selected chunking technique.
3. Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
4. Build a LlamaIndex vector index.
5. Embed each query.
6. Retrieve the top five nodes.
7. Re-embed each returned node's visible text with the same model.
8. Compute manual cosine similarity between the query embedding and each visible-text embedding.
9. Record rank, vector-store score, manual cosine, chunk length, source file, preview, and retrieval latency.
10. Calculate Recall@5, Recall@1, Top-1 cosine, and Mean@5 cosine.

Raw outputs were saved as JSON, JSONL, and CSV files under `reports/hw03/raw/`.

## Chunking Parameters

### Token

| Parameter | Value |
|---|---:|
| Splitter | TokenTextSplitter |
| Chunk size | 256 |
| Chunk overlap | 32 |

MiniLM accepts 256 total sequence positions, including special tokens. `TokenTextSplitter` does not use exactly the same tokenizer as MiniLM's WordPiece tokenizer, so 256 is a near-limit target for visible chunk text rather than a strict guarantee. Metadata added by LlamaIndex can also make the actual embedding input longer than the visible text.

### Semantic 95

| Parameter | Value |
|---|---:|
| Splitter | SemanticSplitterNodeParser |
| Buffer size | 1 |
| Breakpoint percentile | 95 |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |

A buffer size of one compares neighboring sentences. The 95th-percentile threshold creates boundaries only at the largest semantic changes within each document.

### Sentence-window

| Parameter | Value |
|---|---:|
| Splitter | SentenceWindowNodeParser |
| Window size | 3 |
| Window metadata key | window |
| Original sentence key | original_sentence |

Each searchable node is normally one sentence. A three-sentence window on each side is retained in metadata for context.

### Semantic Tuned 80 Ablation

| Parameter | Value |
|---|---:|
| Splitter | SemanticSplitterNodeParser |
| Buffer size | 1 |
| Breakpoint percentile | 80 |
| Experiment group | Additional ablation |

Semantic 80 is an additional ablation configuration and is not one of the three required main techniques.

## Metric Definitions

### Recall@5

Recall@5 is one when the expected source document appears anywhere among the five returned chunks and zero otherwise.

For each technique:

`Recall@5 = questions with expected source in top five / total questions`

### Recall@1

Recall@1 is one when the vector store's rank-one chunk belongs to the expected source document.

### Top-1 Cosine

Top-1 cosine follows the assignment definition: it is the highest manual visible-text cosine among the top-five returned results. It is therefore not necessarily the manual cosine of the vector store's rank-one chunk.

The vector store ranks metadata-inclusive embeddings, whereas the manual cosine calculation re-embeds only the visible chunk text.

### Mean@5 Cosine

Mean@5 cosine is the arithmetic mean of the five manual visible-text cosine similarities returned for a question. The reported technique value is the mean across all five questions.

### Retrieval Latency

Retrieval latency measures the retrieval operation after index construction. The reported values are descriptive measurements from one five-query experiment. Each query was not repeated enough times to establish a stable latency benchmark or remove all warm-up effects.

### Chunking and Indexing Time

Chunking time and indexing time were recorded separately. Semantic splitting embeds sentences while determining boundaries, so its chunking time includes additional embedding work.

## Main Retrieval Comparison

| Technique | Chunks | Average chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@1 | Recall@5 | Mean retrieval latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Token | 692 | 916.327 characters | 0.695357 | 0.597878 | 0.800 | 1.000 | 5.231 ms |
| Semantic 95 | 299 | 1,833.659 characters | 0.651176 | 0.542636 | 0.800 | 1.000 | 2.291 ms |
| Sentence-window | 3,233 | 169.584 characters | 0.684724 | 0.611694 | 0.600 | 1.000 | 24.063 ms |
| Semantic tuned 80 | 750 | 731.019 characters | 0.651176 | 0.571094 | 0.800 | 1.000 | 5.789 ms |

Semantic tuned 80 is shown for comparison but is not included as one of the three required main techniques.

Token produced the highest mean Top-1 cosine among the required techniques. Sentence-window produced the highest Mean@5 cosine. Semantic 95 produced the fewest nodes and the lowest observed lookup latency. All techniques reached saturated Recall@5, while Recall@1 separated sentence-window from the other configurations.

## Chunking and Indexing Cost

| Technique | Chunking time | Indexing time | Total preparation time |
|---|---:|---:|---:|
| Token | 0.348 s | 2.332 s | 2.680 s |
| Semantic 95 | 8.016 s | 0.990 s | 9.006 s |
| Sentence-window | 0.087 s | 7.109 s | 7.196 s |
| Semantic tuned 80 | 7.642 s | 2.447 s | 10.089 s |

Token used rule-based splitting and had moderate indexing cost.

Semantic 95 had the highest required-technique chunking cost because semantic boundary selection embedded sentences during splitting. Its smaller 299-node index was then inexpensive to construct and search.

Sentence-window had negligible splitting cost but generated 3,233 nodes. Embedding and indexing this larger node collection required 7.109 seconds.

## Per-Question Top-1 Cosine

| Question | Token | Semantic 95 | Sentence-window | Semantic tuned 80 | Highest required technique |
|---|---:|---:|---:|---:|---|
| Q1 | 0.639076 | 0.586228 | 0.720197 | 0.586228 | Sentence-window |
| Q2 | 0.808809 | 0.740519 | 0.800927 | 0.740519 | Token |
| Q3 | 0.600887 | 0.574956 | 0.574956 | 0.574956 | Token |
| Q4 | 0.688238 | 0.708671 | 0.724010 | 0.708671 | Sentence-window |
| Q5 | 0.739773 | 0.645509 | 0.603529 | 0.645509 | Token |

The best technique differed by question. Sentence-window led on Q1 and Q4, while Token led on Q2, Q3, and Q5.

Sentence-window's Q4 lead did not produce the correct rank-one source. Its highest-ranked result belonged to another lung-cancer trial.

Semantic 95 and sentence-window both report a Q3 Top-1 cosine of `0.574956`. This is not a transcription error. The corresponding chunks had different full text but shared the same first 254 visible content tokens, so MiniLM discarded the trailing differences when producing their visible-text embeddings.

## Per-Question Mean@5 Cosine

| Question | Token | Semantic 95 | Sentence-window | Semantic tuned 80 |
|---|---:|---:|---:|---:|
| Q1 | 0.533401 | 0.474282 | 0.590039 | 0.495156 |
| Q2 | 0.660311 | 0.569848 | 0.706505 | 0.645153 |
| Q3 | 0.558540 | 0.510237 | 0.552801 | 0.520055 |
| Q4 | 0.650957 | 0.618898 | 0.675762 | 0.649833 |
| Q5 | 0.586181 | 0.539913 | 0.533362 | 0.545273 |

Sentence-window achieved the highest overall Mean@5 cosine because its short searchable nodes often contained less unrelated visible text. However, this did not give it the highest Recall@1.

## Recall Saturation

Recall@5 was `1.0` for all three required methods and the Semantic 80 ablation.

| Technique | Group | Recall@5 |
|---|---|---:|
| Token | Main | 1.0 |
| Semantic 95 | Main | 1.0 |
| Sentence-window | Main | 1.0 |
| Semantic tuned 80 | Ablation | 1.0 |

This result does not establish that the techniques were equally effective. The corpus contained only 100 documents, each query allowed five returned positions, and several questions contained distinctive terms such as `ARV-6723`, `Arrowhead Pharmaceuticals`, and a specific sequence of gene names.

Recall@1 provided more discrimination:

| Technique | Group | Top-1 hits | Questions | Recall@1 |
|---|---|---:|---:|---:|
| Token | Main | 4 | 5 | 0.8 |
| Semantic 95 | Main | 4 | 5 | 0.8 |
| Sentence-window | Main | 3 | 5 | 0.6 |
| Semantic tuned 80 | Ablation | 4 | 5 | 0.8 |

Token and Semantic 95 placed the expected source first for four of five questions. Sentence-window did so for three questions. All configurations failed at rank one on Q4, while sentence-window also failed at rank one on Q3.

Recall@5 is therefore saturated at this corpus size and value of k. Recall@1, cosine similarity, truncation behavior, latency, and manual result inspection provide more useful distinctions.

## Chunk Size Diagnostic

### Effective Embedding Input and Truncation Diagnostic

The original exploratory diagnostic counted visible chunk text and treated 256 content tokens as the threshold. A stricter follow-up diagnostic corrected two issues.

First, MiniLM's 256-position sequence includes `[CLS]` and `[SEP]`, leaving an effective maximum of 254 content tokens. Second, LlamaIndex embeds `node.get_content(metadata_mode=MetadataMode.EMBED)` unless metadata fields are excluded. This representation includes metadata in addition to the visible text.

The follow-up diagnostic measured both representations:

- **Visible text:** `MetadataMode.NONE`, corresponding to displayed chunk text and the report's manual cosine calculation.
- **Index input:** `MetadataMode.EMBED`, corresponding to the content embedded when LlamaIndex built the vector index.

| Technique | Content measured | Nodes | Median tokens | P90 tokens | Maximum | Over 254 | Over-limit rate | Estimated truncated tokens |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Token | Visible text | 692 | 213 | 229 | 257 | 3 | 0.43% | 6 |
| Token | Index input | 692 | 264 | 281 | 309 | 483 | 69.80% | 7,944 |
| Semantic 95 | Visible text | 299 | 324 | 863 | 1,760 | 182 | 60.87% | 59,221 |
| Semantic 95 | Index input | 299 | 374 | 913 | 1,812 | 202 | 67.56% | 69,073 |
| Sentence-window | Visible text | 3,233 | 25 | 73 | 806 | 32 | 0.99% | 4,719 |
| Sentence-window | Index input | 3,233 | 76 | 124 | 858 | 43 | 1.33% | 6,563 |
| Semantic tuned 80 | Visible text | 750 | 104 | 382 | 1,039 | 157 | 20.93% | 26,312 |
| Semantic tuned 80 | Index input | 750 | 156 | 434 | 1,089 | 224 | 29.87% | 35,945 |

The visible-text results show that fixed token chunking controlled document text much more tightly than Semantic 95. Only 3 of 692 Token chunks exceeded 254 visible tokens, compared with 182 of 299 Semantic 95 chunks.

However, the actual index-input results qualify that advantage. Metadata increased the Token median from 213 to 264 tokens and caused 483 of 692 Token index inputs to exceed the effective limit.

The metadata overhead was especially important for Token because its visible chunks were already close to the limit. Sentence-window remained mostly within the limit after metadata was included because its nodes were usually short. Semantic 95 had the largest total estimated truncation loss at 69,073 tokens.

The estimated truncated-token value sums `max(0, token_count - 254)` across all nodes. It measures potential input discarded by the model and should be treated as an estimate rather than an exact reconstruction of internal attention sequences.

### Direct Evidence of MiniLM Truncation

The Q3 results provide direct evidence of truncation.

The Semantic 95 chunk from `NCT06937203.txt` contained 1,084 characters and 292 visible content tokens. The sentence-window header chunk from the same document contained 1,027 characters and 277 visible content tokens.

The diagnostic produced:

    semantic_95 token count: 292
    sentence_window token count: 277
    full text identical: False
    first 254 tokens identical: True
    semantic characters: 1084
    sentence-window characters: 1027

Both chunks produced the same manual cosine, `0.574956`, despite their different full lengths. They also produced the same store score, `0.580185`.

Their shared prefix filled MiniLM's effective visible-text input window, so the different trailing text did not affect the manual embedding. The indexed representation also included metadata before the text. Because both nodes came from the same source document, their metadata and initial header text were also identical.

## Semantic Threshold Ablation

Semantic 80 was evaluated as an additional ablation rather than one of the required main techniques.

| Technique | Chunks | Average chunk length | Mean Top-1 cosine | Mean@5 cosine | Recall@1 | Recall@5 | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semantic 95 | 299 | 1,833.659 characters | 0.651176 | 0.542636 | 0.800 | 1.000 | 2.291 ms |
| Semantic tuned 80 | 750 | 731.019 characters | 0.651176 | 0.571094 | 0.800 | 1.000 | 5.789 ms |

Changing the breakpoint percentile from 95 to 80:

- Increased the number of chunks from 299 to 750.
- Reduced average chunk length from 1,833.659 to 731.019 characters.
- Reduced the visible-text over-limit rate from 60.87% to 20.93%.
- Reduced the index-input over-limit rate from 67.56% to 29.87%.
- Reduced estimated metadata-inclusive truncation from 69,073 to 35,945 tokens.
- Improved Mean@5 cosine from 0.542636 to 0.571094.
- Did not change mean Top-1 cosine.
- Did not change Recall@1 or Recall@5.
- Increased observed retrieval latency from 2.291 ms to 5.789 ms.

The lower percentile created more boundaries and smaller typical chunks. However, it did not impose a hard maximum size. Semantically consistent passages could still remain larger than MiniLM's input window.

## Why Semantic 95 and Semantic 80 Have the Same Top-1 Score

Semantic 95 and Semantic 80 produced exactly the same mean Top-1 cosine of `0.651176`.

The saved results were compared using complete chunk text and SHA-256 hashes. For all five questions, the two configurations had:

- The same Top-1 source file.
- The same Top-1 visible text.
- The same chunk length.
- The same SHA-256 text hash.
- The same vector-store score.
- The same manual cosine.

The breakpoint percentile changed many lower-ranked and less-relevant chunks but did not split the five most relevant passages. These passages were semantically cohesive enough to remain intact at both thresholds.

This shows that lowering the semantic percentile changed corpus-wide chunk statistics without changing the most highly scored chunk for any registered question.

## Confidently Scored Incorrect Retrieval

Q4 asked:

> What is the minimum age requirement for the lung cancer genetic analysis study sponsored by Massachusetts General Hospital?

The expected source was `NCT00471978.txt`, whose minimum age was 18 years. All configurations returned another lung-cancer trial, `NCT07465848.txt`, at rank one.

| Technique | Rank-one source | Store score | Manual cosine | Correct rank-one document? |
|---|---|---:|---:|---|
| Token | NCT07465848.txt | 0.665644 | 0.666341 | No |
| Semantic 95 | NCT07465848.txt | 0.700266 | 0.708671 | No |
| Sentence-window | NCT07465848.txt | 0.720796 | 0.708041 | No |
| Semantic tuned 80 | NCT07465848.txt | 0.700266 | 0.708671 | No |

The incorrect trial had a minimum age of 45 years. It still received high similarity because it was another lung-cancer study with similar structured eligibility language.

The question's general terms, including “minimum age,” “lung cancer,” and “study,” matched the wrong eligibility block strongly. The sponsor and exact study identity were not weighted strongly enough to place the expected document first.

This is the clearest confidently scored error in the experiment. Sentence-window achieved the highest Q4 Top-1 cosine among the required techniques, but its vector-store rank-one result belonged to the wrong study. High cosine similarity therefore did not guarantee that the result contained the answer from the requested source.

## Sentence-Window Q3 Failure Analysis

Q3 asked:

> What is the planned enrollment and trial phase of the Arrowhead Pharmaceuticals study in obesity and type 2 diabetes?

The expected source was `NCT06937203.txt`.

Sentence-window returned:

| Rank | Source | Store score | Chunk length |
|---:|---|---:|---:|
| 1 | NCT07296484.txt | 0.599353 | 441 |
| 2 | NCT06937203.txt | 0.594625 | 855 |
| 3 | NCT06937203.txt | 0.580185 | 1,027 |
| 4 | NCT06323538.txt | 0.540817 | 279 |
| 5 | NCT07588438.txt | 0.540615 | 259 |

The incorrect rank-one result was the CAPTAIN-T2D study. Its header used the same structured fields as the expected document:

- NCT Number
- Title
- Official Title
- Lead Sponsor
- Overall Status
- Start Date
- Study Type
- Phases
- Enrollment
- Conditions

This failure was not caused by the answer being split into an isolated short sentence. The source header contained few sentence-ending punctuation marks, so the sentence parser retained a long field block as one node.

The wrong and correct records both concerned type 2 diabetes and used almost identical field ordering. The competing CAPTAIN-T2D block was therefore slightly closer in the metadata-inclusive vector space even though it did not contain the requested sponsor.

The correct document still appeared at ranks two and three. The score difference between the wrong rank-one result and the first result from the correct document was only `0.004728`.

This suggests that document-level aggregation could improve retrieval. Two chunks from `NCT06937203.txt` appeared within the first three positions, providing stronger combined evidence for that document than the single CAPTAIN-T2D result.

## Verified Explanation of Store Score and Manual Cosine Differences

The vector-store score and the report's manual cosine are based on different embedding inputs.

The manual cosine calculation re-embeds visible chunk text:

    visible_text = node.get_content(
        metadata_mode=MetadataMode.NONE
    )

    visible_embedding = embed_model.get_text_embedding(
        visible_text
    )

    manual_cosine = cosine_similarity(
        query_embedding,
        visible_embedding
    )

LlamaIndex builds the vector index from:

    node.get_content(
        metadata_mode=MetadataMode.EMBED
    )

Unless metadata keys are excluded, this representation contains metadata in addition to visible text. The attached metadata included:

- `creation_date`
- `file_name`
- `file_path`
- `file_size`
- `file_type`
- `last_modified_date`
- `source_file`

A follow-up validation rebuilt the Token index and independently embedded both representations for the five Q2 results.

| Rank | Source | Store score | Visible-text cosine | Metadata-content cosine | Store − visible | Store − metadata |
|---:|---|---:|---:|---:|---:|---:|
| 1 | NCT07749586.txt | 0.786970 | 0.808809 | 0.786970 | -0.021839 | 0.000000 |
| 2 | NCT05902988.txt | 0.653576 | 0.654454 | 0.653576 | -0.000878 | 0.000000 |
| 3 | NCT07244835.txt | 0.650841 | 0.639441 | 0.650841 | 0.011400 | 0.000000 |
| 4 | NCT05379985.txt | 0.643924 | 0.600620 | 0.643924 | 0.043304 | 0.000000 |
| 5 | NCT05902988.txt | 0.637148 | 0.598231 | 0.637148 | 0.038917 | -0.000000 |

The maximum absolute difference between the store score and metadata-content cosine was `0.0000000053`, which is ordinary floating-point error. The maximum difference between the store score and visible-text cosine was `0.0433040638`.

This verifies that the vector store ranked nodes using the `MetadataMode.EMBED` representation, while the report's manual cosine used visible chunk text. The two columns therefore measure related but different representations and are not expected to be identical.

This also reveals a methodological limitation. Fields such as `file_name`, `file_path`, and `source_file` contain document identifiers, including NCT numbers. These fields may influence retrieval and consume part of the model's input window.

A future experiment should retain `source_file` for Recall scoring while excluding file-system and source-identity fields from embedding input through `excluded_embed_metadata_keys`. The formal experiment was not rerun after this diagnostic so that its recorded results remain unchanged and auditable.

No LLM, reranker, or retrieval postprocessor was used.

## Observations

Token chunking gave the best empirical balance among the three required techniques. It achieved the highest mean Top-1 cosine (`0.695`), tied Semantic 95 for the best Recall@1 (`0.8`), and had moderate observed retrieval latency (`5.2 ms`). Its visible text was tightly controlled: 689 of 692 chunks fit within the effective 254-content-token limit. However, the follow-up diagnostic showed that metadata increased the median actual index input to 264 tokens, causing 483 of 692 inputs to exceed the limit. Semantic 95 produced the fewest chunks and the lowest observed lookup latency, but 67.56% of its metadata-inclusive inputs exceeded the limit and it had the largest estimated truncation loss. Sentence-window had the highest Mean@5 cosine (`0.612`) and kept 98.67% of its index inputs within the limit, but its 3,233-node index produced the slowest observed retrieval and the lowest Recall@1 (`0.6`).

The best technique differed by question. Token produced the highest Top-1 cosine for Q2, Q3, and Q5, while sentence-window led on Q1 and Q4. The sentence-window Q4 lead did not produce the correct rank-one document: its highest-ranked chunk came from `NCT07465848.txt`, not the expected `NCT00471978.txt`. Recall@5 was saturated at `1.0` for all three required techniques, so Recall@1, per-query cosine values, and manual inspection were needed to expose differences. The latency results are descriptive rather than conclusive because each of the five queries was timed only once and no dedicated repeated-query benchmark was performed.

## Detailed Analysis

### Chunk-Size Control

The semantic percentile parameter controls relative boundary placement rather than an absolute maximum length. Lowering the threshold from 95 to 80 increased the number of chunks from 299 to 750, but 29.87% of the tuned configuration's metadata-inclusive inputs still exceeded 254 tokens.

The five Top-1 chunks were identical between Semantic 95 and Semantic 80. The most relevant passages were semantically cohesive enough to remain unsplit at both thresholds.

Token chunking controlled visible text effectively, but it did not control complete embedding input because LlamaIndex prepended metadata. Sentence-window normally produced the shortest complete inputs, although punctuation-free headers and eligibility blocks remained as unusually large nodes.

### Template-Like Records

Clinical-trial records repeatedly use the same header and eligibility structures. This caused unrelated but structurally similar chunks to compete.

For Q3, sentence-window ranked the CAPTAIN-T2D header first even though two chunks from the correct Arrowhead document appeared at ranks two and three. For Q4, all required techniques ranked a different lung-cancer study first, and sentence-window assigned that incorrect result its highest Q4 cosine.

These cases demonstrate that high embedding similarity does not guarantee that a chunk contains the requested fact. The model sometimes captured the general clinical domain and template structure more strongly than the question's specific sponsor or study identity.

### Metadata Effects

The score validation proved that LlamaIndex embedded metadata together with text. This explains the difference between vector-store scores and visible-text manual cosine values.

File identifiers may have contributed to retrieval, while metadata also reduced the text space available inside MiniLM's input window. The formal run remains valid as a record of the implemented system, but this behavior is an important limitation.

A future controlled comparison should exclude file-system and source identifiers from embedding input while retaining `source_file` as non-embedded metadata for Recall scoring.

### Latency Limitation

The reported retrieval latency was calculated from five queries in one run. Semantic 95 had the lowest observed mean latency while searching 299 vectors, whereas sentence-window searched 3,233 vectors.

The experiment did not repeat each query enough times to estimate a stable median or remove warm-up effects. The latency values therefore describe this run but should not be treated as a general performance benchmark.

## Discussion and Future Work

Four changes would strengthen a future experiment:

1. Exclude `file_name`, `file_path`, `source_file`, timestamps, file size, and file type from embedding input while retaining `source_file` for Recall scoring.
2. Add a maximum-token postprocessing step after semantic splitting so that semantically cohesive but oversized chunks cannot exceed the embedding model's input window.
3. Repeat each retrieval query multiple times, discard a warm-up run, and report median and percentile latency.
4. Aggregate chunk-level evidence by source document so multiple strong chunks from one document can collectively outrank a single competing chunk.

Document-level aggregation is particularly relevant to sentence-window Q3. The correct document occupied ranks two and three, while the incorrect document appeared only once at rank one. Aggregating evidence could therefore recover the expected document even when its highest individual chunk is narrowly outranked.

## Conclusion

Token chunking was the best empirical technique for this corpus because it produced the highest mean Top-1 cosine among the required methods, tied for the best Recall@1, and maintained moderate observed retrieval latency. However, its original input-length advantage applied only to visible chunk text: metadata caused 69.80% of its actual index inputs to exceed MiniLM's effective 254-content-token limit. Semantic chunking suffered the largest estimated truncation loss, while sentence-window created the largest index and lowest Recall@1 despite achieving the highest Mean@5 cosine. Overall, the experiment shows that chunk boundaries, embedded metadata, model truncation, and document-template repetition must all be controlled when evaluating retrieval over structured clinical-trial records.

## AI Use

### 1. What was an AI assistant used for, and what did I do myself?

I used OpenAI ChatGPT/Codex as a development assistant for initial code structure, debugging suggestions, experimental-design discussion, and report organization.

The AI assistant proposed initial structures for the shared retrieval pipeline, chunking functions, authentication router, experiment runner, diagnostic scripts, and report sections. It also suggested possible explanations for unexpected retrieval results.

I independently inspected the repository, executed every command, reviewed all generated files, tested the application, ran the retrieval experiments, and verified the numerical claims against saved raw outputs.

My independent work included:

- Inspecting the repository before selecting final file locations.
- Building and checking the 100-document corpus.
- Preserving deterministic corpus ordering.
- Recording corpus hashes and manifests.
- Registering and correcting the five evaluation questions.
- Extending semantic threshold testing beyond the initially suggested values.
- Running the formal four-configuration retrieval experiment.
- Checking MiniLM token counts with its own tokenizer.
- Verifying Recall@1 from saved result files.
- Comparing Semantic 95 and Semantic 80 Top-1 chunks using SHA-256 hashes.
- Identifying the sentence-window Q3 failure mechanism.
- Verifying metadata-inclusive vector-store scoring.
- Writing and running the 31-check verification script.
- Testing login, logout, idle expiration, HTTPS cookies, and CRUD behavior.
- Capturing and reviewing the required evidence screenshots.

### 2. What AI-produced output was wrong or unsuitable, or what did I independently verify?

The most important unsuitable output was the original Q4 design. Its first version had no expected source, which made it unsuitable for source-based Recall scoring and did not satisfy the single-source question requirement.

An early directory instruction also proposed creating `routers/auth.py` under a `routers/` directory at the repository root. The actual FastAPI application was located under `code/web_application/`. The proposed command failed because the root-level directory did not exist. I inspected the repository and placed the router at `code/web_application/routers/auth.py`.

Another suggested edit temporarily risked placing a second `if __name__ == "__main__"` block next to the existing application startup block. I inspected `main.py` and consolidated startup behavior rather than retaining conflicting blocks.

The initial estimate suggested that full semantic splitting could require tens of minutes. A three-document pilot and the full run showed that it completed much faster on the Apple M4.

The initial chunk-size interpretation also treated 256 visible tokens as the complete input limit. I later verified that two sequence positions were used by special tokens and that LlamaIndex metadata was included in the indexed embedding input.

### 3. How did I detect or verify the problems?

I detected the Q4 problem after the pilot run by comparing every question with the assignment requirement and its `expected_source` field. The null expected source made the question inconsistent with the other four and impossible to score as a required single-source query.

I detected the directory problem when the proposed root-level `routers/auth.py` command failed. Instead of creating a new root-level application structure, I inspected the existing tree and confirmed that `main.py`, templates, and application requirements were under `code/web_application/`.

I tested semantic runtime using a small sample before running the complete corpus. The measured pilot time contradicted the earlier estimate.

I detected the Semantic 95 and Semantic 80 score coincidence by comparing their saved Top-1 results. A dedicated script confirmed that all five pairs had identical source files, text, scores, lengths, and SHA-256 hashes.

I verified the effective token limit using the MiniLM tokenizer with special tokens excluded from the count. I then counted both visible node text and `MetadataMode.EMBED` content across every node.

Finally, I rebuilt the Token index for Q2 and independently embedded both representations. The metadata-inclusive cosine reproduced the vector-store score with a maximum error of only `0.0000000053`, while the visible-text cosine differed by as much as `0.0433040638`.

### 4. What did I change, and why does it work now?

I changed Q4 to ask for the minimum age of the lung-cancer genetic analysis study sponsored by Massachusetts General Hospital and set its expected source to `NCT00471978.txt`. This made it a valid single-source question while preserving its value as a difficult template-confusion example. The correction was committed before the formal graded run.

I moved the authentication router into `code/web_application/routers/auth.py`, matching the application's package structure and template paths.

I retained Semantic 95 as the required main configuration and classified Semantic 80 as an additional ablation. This avoided changing the required three-technique comparison while still measuring the effect of a more aggressive semantic threshold.

I added Recall@1 because Recall@5 was saturated. This revealed a difference between Token and Semantic 95 at `0.8` and sentence-window at `0.6`.

I added effective-input and metadata-score diagnostics. The report now distinguishes visible text from actual metadata-inclusive index input, uses 254 content tokens as the effective threshold, and explains the store-score difference with measured evidence rather than speculation.

All important claims are supported by saved CSV, JSON, JSONL, log, screenshot, manifest, or verification evidence.

## Machine-Readable Evidence

The following files support the reported results:

- `reports/hw03/raw/summary_metrics.csv`
- `reports/hw03/raw/per_query_metrics.csv`
- `reports/hw03/raw/retrieval_results.jsonl`
- `reports/hw03/raw/chunk_metrics.csv`
- `reports/hw03/raw/chunk_size_diagnostic.csv`
- `reports/hw03/raw/recall_at_1.csv`
- `reports/hw03/raw/recall_at_1_summary.csv`
- `reports/hw03/raw/semantic_top1_comparison.csv`
- `reports/hw03/raw/effective_input_diagnostic.csv`
- `reports/hw03/raw/metadata_score_validation.csv`
- `reports/hw03/raw/run_metadata.json`
- `reports/hw03/RUN_LOG.txt`
- `reports/hw03/RUN_LOG_https.txt`
- `reports/hw03/RUN_LOG_effective_input.txt`
- `reports/hw03/RUN_LOG_part2_display.txt`
- `reports/hw03/verification.json`

The verification script is stored at:

- `code/rag/scripts/verify_hw03.py`

The diagnostic scripts are stored at:

- `code/rag/scripts/chunk_size_diagnostic.py`
- `code/rag/scripts/analyze_retrieval_results.py`
- `code/rag/scripts/effective_input_diagnostic.py`

The complete retrieval implementation is stored under:

- `code/rag/pipeline.py`
- `code/rag/chunkers.py`
- `code/rag/retrieval.py`
- `code/rag/run_experiment.py`

The pre-registered questions are stored at:

- `reports/hw03/questions.yaml`