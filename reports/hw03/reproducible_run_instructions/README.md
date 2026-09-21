# HW3 Reproducible Run Instructions

## Repository

Repository URL:

https://github.com/HauZer-HaoZheWang/data260-8561

All commands below begin from the repository root.

## Tested Environment

| Item | Value |
|---|---|
| Operating system | macOS |
| Hardware | Apple M4 with 16 GB memory |
| Python environment | Conda environment named `data260` |
| Python version | Python 3.12 |
| SID4 | 8561 |
| Application port | 8461 |
| Experiment seed | 8561 |
| Verification seed | 268561 |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimensions | 384 |
| Generation model | None |

## 1. Clone and Enter the Repository

    git clone https://github.com/HauZer-HaoZheWang/data260-8561.git
    cd data260-8561

If the repository has already been cloned:

    cd ~/data260-8561

## 2. Activate the Python Environment

    conda activate data260

If the environment does not already exist, create one before installing the requirements:

    conda create -n data260 python=3.12
    conda activate data260

## 3. Install Dependencies

Install the retrieval dependencies:

    cd ~/data260-8561
    python3 -m pip install -r code/rag/requirements.txt

Install the web-application dependencies:

    cd ~/data260-8561
    python3 -m pip install -r code/web_application/requirements.txt

The retrieval experiment uses local Hugging Face embeddings. It does not require an OpenAI API key or a generation model.

The first execution may download the MiniLM model from Hugging Face. An unauthenticated Hugging Face warning does not prevent the experiment from running.

## 4. Build the Corpus

Run the deterministic corpus download script:

    cd ~/data260-8561
    python3 code/rag/scripts/fetch_corpus.py

Expected results:

- 100 text files under `code/rag/corpus/`
- At least 204,800 total bytes
- A corpus manifest at `code/rag/CORPUS_MANIFEST.json`
- A matching manifest copy at `reports/hw03/CORPUS_MANIFEST.json`

Inspect the corpus:

    cd ~/data260-8561
    find code/rag/corpus -maxdepth 1 -type f -name "*.txt" | wc -l
    du -sh code/rag/corpus
    cmp code/rag/CORPUS_MANIFEST.json reports/hw03/CORPUS_MANIFEST.json

## 5. Generate a Local HTTPS Certificate

The certificate directory is excluded from Git, so a fresh clone must generate its own local certificate.

    cd ~/data260-8561

    mkdir -p code/web_application/certs

    openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
      -keyout code/web_application/certs/key.pem \
      -out code/web_application/certs/cert.pem \
      -subj "/CN=localhost" \
      -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

Confirm that both files exist:

    cd ~/data260-8561
    ls -lh \
      code/web_application/certs/key.pem \
      code/web_application/certs/cert.pem

The certificate is self-signed. A browser may display a local certificate warning, which must be accepted for local testing.

## 6. Start the HTTPS Web Application

Run the server from the repository root:

    cd ~/data260-8561

    COOKIE_SECURE=1 \
    SECRET_KEY="data260-hw3-demo-secret" \
    python3 code/web_application/main.py

Expected server address:

    https://127.0.0.1:8461

Demonstration credentials:

    Username: admin
    Password: password

The credentials are hard-coded only for this homework demonstration. A production system should load account data from a protected environment or database and store passwords using a password-hashing scheme such as bcrypt or Argon2.

The application uses:

- A signed session cookie
- `HttpOnly`
- `SameSite=lax`
- `Secure` when `COOKIE_SECURE=1`
- A 3,600-second cookie maximum age
- A 120-second sliding idle timeout

Keep this terminal running while testing the application. Press `Control + C` to stop the server.

## 7. Verify the HTTPS Cookie

While the HTTPS server is running, open a second terminal and execute:

    cd ~/data260-8561

    curl -k -i \
      -X POST \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=admin&password=password" \
      https://127.0.0.1:8461/login \
      2>&1 | tee reports/hw03/RUN_LOG_https.txt

Inspect the cookie:

    cd ~/data260-8561
    grep -i "set-cookie" reports/hw03/RUN_LOG_https.txt

The header should contain:

    httponly
    samesite=lax
    secure
    Max-Age=3600

## 8. Compile the Retrieval Code

    cd ~/data260-8561

    python3 -m py_compile \
      code/rag/pipeline.py \
      code/rag/chunkers.py \
      code/rag/retrieval.py \
      code/rag/run_experiment.py \
      code/rag/scripts/chunk_size_diagnostic.py \
      code/rag/scripts/analyze_retrieval_results.py \
      code/rag/scripts/effective_input_diagnostic.py \
      code/rag/scripts/print_report_output.py \
      code/rag/scripts/verify_hw03.py

No output indicates successful compilation.

## 9. Run the Formal Retrieval Experiment

    cd ~/data260-8561

    python3 code/rag/run_experiment.py \
      --include-tuned \
      2>&1 | tee -a reports/hw03/RUN_LOG.txt

The formal experiment evaluates:

- Token chunking
- Semantic chunking with percentile 95
- Sentence-window chunking
- Semantic chunking with percentile 80 as an additional ablation

Expected raw output files include:

- `reports/hw03/raw/retrieval_results.jsonl`
- `reports/hw03/raw/summary_metrics.csv`
- `reports/hw03/raw/per_query_metrics.csv`
- `reports/hw03/raw/chunk_metrics.csv`
- `reports/hw03/raw/run_metadata.json`

The experiment is retrieval-only. No generation model is used.

## 10. Run Recall@1 and Semantic Top-1 Analysis

    cd ~/data260-8561

    python3 code/rag/scripts/analyze_retrieval_results.py \
      2>&1 | tee -a reports/hw03/RUN_LOG.txt

Expected output files:

- `reports/hw03/raw/recall_at_1.csv`
- `reports/hw03/raw/recall_at_1_summary.csv`
- `reports/hw03/raw/semantic_top1_comparison.csv`

## 11. Run the Effective-Input Diagnostic

    cd ~/data260-8561

    python3 code/rag/scripts/effective_input_diagnostic.py \
      2>&1 | tee reports/hw03/RUN_LOG_effective_input.txt

This diagnostic:

- Uses 254 content tokens as the effective MiniLM text budget
- Counts visible node text
- Counts metadata-inclusive index input
- Validates vector-store scores against `MetadataMode.EMBED`
- Does not overwrite the formal retrieval results

Expected output files:

- `reports/hw03/raw/effective_input_diagnostic.csv`
- `reports/hw03/raw/metadata_score_validation.csv`
- `reports/hw03/RUN_LOG_effective_input.txt`

## 12. Reproduce the Part 2 Display Output

The display script reads saved formal results and does not overwrite them.

    cd ~/data260-8561

    {
      python3 code/rag/scripts/print_report_output.py \
        --technique token \
        --question Q2

      echo
      echo

      python3 code/rag/scripts/print_report_output.py \
        --technique semantic_95 \
        --question Q2

      echo
      echo

      python3 code/rag/scripts/print_report_output.py \
        --technique sentence_window \
        --question Q2
    } 2>&1 | tee reports/hw03/RUN_LOG_part2_display.txt

The output identifies each technique and includes:

- Query embedding dimension
- First eight query-vector values
- Query-vector shape
- Stacked document-vector shape
- Rank
- Vector-store score
- Manual cosine similarity
- Chunk length
- Source file
- Text preview

## 13. Run Core Verification

The core verifier does not require the final PDF or Git tag.

    cd ~/data260-8561

    python3 code/rag/scripts/verify_hw03.py \
      2>&1 | tee -a reports/hw03/RUN_LOG.txt

Expected result:

    Passed: 31
    Failed: 0
    Overall pass: True

A Starlette or TestClient deprecation warning does not count as a failed check.

The verification results are written to:

    reports/hw03/verification.json

## 14. Run Final Verification

After creating `reports/hw03/report.pdf` and the `hw3` Git tag:

    cd ~/data260-8561
    python3 code/rag/scripts/verify_hw03.py --final

The final check additionally verifies:

- `reports/hw03/report.pdf`
- The `hw3` Git tag

## 15. Inspect Key Results

Summary metrics:

    cd ~/data260-8561
    column -s, -t reports/hw03/raw/summary_metrics.csv

Per-query metrics:

    cd ~/data260-8561
    column -s, -t reports/hw03/raw/per_query_metrics.csv

Recall@1:

    cd ~/data260-8561
    column -s, -t reports/hw03/raw/recall_at_1_summary.csv

Effective embedding input:

    cd ~/data260-8561
    column -s, -t reports/hw03/raw/effective_input_diagnostic.csv

Metadata score validation:

    cd ~/data260-8561
    column -s, -t reports/hw03/raw/metadata_score_validation.csv

## 16. Stop the Server

Return to the terminal running the FastAPI application and press:

    Control + C