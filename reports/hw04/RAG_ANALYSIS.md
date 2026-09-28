# HW4 Part 4: RAG Evaluation

## Experimental Setup

The corpus contains 100 clinical-trial documents. Token chunking produced
692 chunks with a chunk size of 256 and overlap of 32. Embeddings used
sentence-transformers/all-MiniLM-L6-v2, and generation used
google/flan-t5-small.

Configuration A answered without retrieved context. Configuration B used
the top three retrieved chunks with a basic prompt. Configuration C sorted
retrieved chunks by similarity, included source names, filtered weak
evidence, required grounding, and used an explicit refusal rule.

## Evaluation Table

| Configuration | k | Automatic correct | Rate | Notes |
|---|---:|---:|---:|---|
| A: no retrieved context | 0 | 3/6 | 50.0% | Relied on model knowledge |
| B: basic RAG | 3 | 2/6 | 33.3% | Distracting context reduced quality |
| C: context engineered | 3 | 5/6 | 83.3% | Best automatic result; both refusals correct |

## k-Sweep for Configuration C

| k | Automatic correct | Rate |
|---:|---:|---:|
| 1 | 4/6 | 66.7% |
| 3 | 5/6 | 83.3% |
| 5 | 5/6 | 83.3% |

## Analysis

The experiment shows that retrieval alone does not guarantee better
generation. Configuration A answered without corpus evidence and achieved
50.0% under the automatic token-overlap measure. Configuration B added the
top three chunks, but its result fell to 33.3%. This happened because a
basic prompt passed several chunks to a small generation model without
telling it how to prioritize evidence, cite sources, or reject unsupported
questions. Retrieved text can therefore become noise rather than useful
context.

Configuration C performed best. It ordered chunks by similarity, attached
source filenames, filtered low-scoring evidence, restricted the model to
the supplied context, and supplied an exact refusal response. Its automatic
score at k=3 was 83.3%. Most importantly, Q5 and Q6 were both refused.
Q5 requested an exact survival statistic that was absent from the corpus,
while Q6 requested individualized treatment advice that trial listings
cannot support. These results demonstrate that explicit grounding and
refusal instructions reduce unsupported generation.

The k-sweep also shows a precision-recall tradeoff. With k=1, the system
had too little context and scored 66.7%. Increasing k to 3 raised the score
to 83.3% because more relevant evidence became available. Increasing k to
5 did not improve the automatic score, indicating that additional chunks
mainly added redundant or distracting material. Therefore, k=3 is the best
setting for this corpus and model.

Automatic scoring must be interpreted cautiously. It uses word overlap
rather than full semantic correctness. For example, the C answer for Q3
identified the correct ARO-ALK7 study and phase but omitted the planned
enrollment of 150 participants. Q1 also selected an incorrect time frame.
A strict human review therefore rates the output lower than the automatic
metric. The main limitation is the small FLAN-T5 model combined with
fragmented 256-token chunks. Future work should use a stronger generator,
reranking, and answer verification against the cited source before
returning the final response.
