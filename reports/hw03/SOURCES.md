# Corpus Sources - DATA 260 HW3

## Personal Configuration

- SID4: 8561
- PREFIX: s8561
- SEED: 8561
- DOMAIN_ID: 1
- Domain: Clinical Trial Listings

## Source

- Provider: ClinicalTrials.gov, U.S. National Library of Medicine
- API endpoint: https://clinicaltrials.gov/api/v2/studies
- API version: v2
- Access date: 2026-09-20
- Terms and conditions: https://clinicaltrials.gov/about-site/terms-conditions

The corpus uses publicly available ClinicalTrials.gov study records. Use of the
data follows the official ClinicalTrials.gov terms and conditions.

## Query Used

```text
query.cond = "diabetes OR lung cancer OR hypertension"
filter.overallStatus = "RECRUITING"
pageSize = 100
format = "json"
```

## Retrieval Procedure

1. `code/rag/scripts/fetch_corpus.py` sends the query above to the
   ClinicalTrials.gov API v2 endpoint.
2. The original API response is stored without modification at
   `code/rag/raw_json/api_response.json`.
3. Each study record is rendered as one plain text file named with its NCT
   number.
4. The rendered files are stored under `code/rag/corpus/`.
5. Records shorter than 1,500 characters are skipped because they do not
   contain enough useful information for the retrieval experiment.
6. `code/rag/CORPUS_MANIFEST.json` is stored beside the corpus.
7. An identical submission copy is stored at
   `reports/hw03/CORPUS_MANIFEST.json`.
8. Both manifest files record the filename, byte size, and SHA-256 hash of
   every rendered document.

## Why Plain Text Is Used

The retrieval experiment compares token, semantic, and sentence-window
chunking. These techniques split documents according to textual boundaries.

Raw JSON contains braces, field names, quotation marks, and other structural
syntax. Indexing the raw JSON could cause chunks to follow JSON syntax instead
of meaningful clinical trial content. This would make the comparison less
fair, especially for `SemanticSplitterNodeParser`, which uses sentence
embeddings to locate semantic boundaries.

The download script therefore converts each API record into a consistent,
human-readable plain text document before chunking and indexing.

## Corpus Fields

Each rendered study can contain:

- NCT number
- Brief title
- Official title
- Lead sponsor
- Overall status
- Start date
- Study type
- Study phase
- Enrollment
- Conditions
- Brief summary
- Detailed description
- Interventions
- Eligibility criteria
- Minimum and maximum age
- Sex
- Primary outcome measures
- Primary outcome time frames

Blank fields are preserved when the source study does not provide a value.
For example, an observational study may not have a study phase or an
intervention. A blank field therefore reflects the source data and is not
treated as a rendering error.

## Corpus Summary

- Files: 100
- Total size: 548,872 bytes (536.0 KB)
- Size range: 1,933 to 25,209 bytes
- Minimum requirement: 204,800 bytes
- Requirement status: Satisfied (approximately 2.7 times the minimum)

## Known Corpus Characteristics

Two properties of this corpus are relevant to the retrieval comparison and
are analyzed further in `METRICS.md`.

1. **Length spread.** Documents range from 1,933 to 25,209 bytes, which is
   approximately a 13 times difference. Fixed token chunking produces many
   chunks for long records and few chunks for short records. Long documents
   therefore have more opportunities to occupy positions in the top-k
   retrieval results.

2. **Boilerplate eligibility text.** The exact line
   `Minimum Age: 18 Years` appears in 78 of the 100 documents. Similar
   eligibility language across unrelated trials is expected to produce
   high-similarity retrievals that may not belong to the requested study.
   Question Q2 in `questions.yaml` is designed to test this behavior.