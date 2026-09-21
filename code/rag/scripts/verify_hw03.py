"""Verify the DATA 260 HW3 submission.

This script checks:
- Corpus size, file count, byte sizes, and SHA-256 hashes
- Questions and expected source files
- Retrieval raw outputs and vector dimensions
- Summary metrics and Recall@1 results
- Required report files and screenshots
- FastAPI authentication and CRUD routes
- Question commit time before the graded experiment
- Final report and Git tag when --final is used

The result is saved to reports/hw03/verification.json.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from fastapi.testclient import TestClient


#Get the repository root folder
REPO_DIR = Path(__file__).resolve().parents[3]

#Main project folders
RAG_DIR = REPO_DIR / "code" / "rag"
WEB_DIR = REPO_DIR / "code" / "web_application"
REPORTS_DIR = REPO_DIR / "reports" / "hw03"
CORPUS_DIR = RAG_DIR / "corpus"
RAW_DIR = REPORTS_DIR / "raw"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

#Required files
MANIFEST_PATH = REPORTS_DIR / "CORPUS_MANIFEST.json"
QUESTIONS_PATH = REPORTS_DIR / "questions.yaml"
METRICS_PATH = REPORTS_DIR / "METRICS.md"
SOURCES_PATH = REPORTS_DIR / "SOURCES.md"
RUN_LOG_PATH = REPORTS_DIR / "RUN_LOG.txt"
HTTPS_LOG_PATH = REPORTS_DIR / "RUN_LOG_https.txt"
VERIFICATION_PATH = REPORTS_DIR / "verification.json"
REPORT_PDF_PATH = REPORTS_DIR / "report.pdf"


checks = []


def add_check(
    name,
    passed,
    detail
):
    """Add one verification result"""

    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "detail": str(detail),
        }
    )

    status = (
        "PASS"
        if passed
        else "FAIL"
    )

    print(
        f"[{status}] {name}: {detail}"
    )


def file_sha256(
    file_path
):
    """Calculate the SHA-256 hash of one file"""

    hasher = hashlib.sha256()

    with file_path.open(
        "rb"
    ) as input_file:
        while True:
            block = input_file.read(
                1024 * 1024
            )

            if not block:
                break

            hasher.update(
                block
            )

    return hasher.hexdigest()


def check_required_files():
    """Check required homework files"""

    required_files = [
        MANIFEST_PATH,
        QUESTIONS_PATH,
        METRICS_PATH,
        SOURCES_PATH,
        RUN_LOG_PATH,
        HTTPS_LOG_PATH,
        RAG_DIR / "pipeline.py",
        RAG_DIR / "chunkers.py",
        RAG_DIR / "retrieval.py",
        RAG_DIR / "run_experiment.py",
        RAG_DIR / "requirements.txt",
        WEB_DIR / "main.py",
        WEB_DIR / "routers" / "auth.py",
        WEB_DIR / "templates" / "index.html",
        WEB_DIR / "templates" / "login.html",
        WEB_DIR / "templates" / "dashboard.html",
    ]

    missing_files = [
        str(path.relative_to(REPO_DIR))
        for path in required_files
        if not path.exists()
    ]

    add_check(
        "required_files",
        not missing_files,
        (
            "All required files exist"
            if not missing_files
            else f"Missing: {missing_files}"
        )
    )


def check_corpus():
    """Verify corpus size and manifest hashes"""

    if not MANIFEST_PATH.exists():
        add_check(
            "corpus_manifest",
            False,
            "Manifest does not exist"
        )
        return

    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    manifest_files = manifest.get(
        "files",
        []
    )

    manifest_total = manifest.get(
        "total_bytes",
        0
    )

    add_check(
        "corpus_file_count",
        len(manifest_files) >= 1,
        f"{len(manifest_files)} files listed"
    )

    add_check(
        "corpus_minimum_size",
        manifest_total >= 200 * 1024,
        (
            f"{manifest_total} bytes; "
            f"minimum is {200 * 1024}"
        )
    )

    errors = []
    actual_total = 0

    for item in manifest_files:
        filename = item.get(
            "filename",
            ""
        )

        file_path = (
            CORPUS_DIR
            / filename
        )

        if not file_path.exists():
            errors.append(
                f"{filename}: missing"
            )
            continue

        file_bytes = file_path.stat().st_size
        actual_total += file_bytes

        expected_bytes = item.get(
            "bytes"
        )

        expected_hash = item.get(
            "sha256",
            ""
        )

        actual_hash = file_sha256(
            file_path
        )

        if file_bytes != expected_bytes:
            errors.append(
                f"{filename}: byte mismatch"
            )

        if actual_hash != expected_hash:
            errors.append(
                f"{filename}: SHA-256 mismatch"
            )

    if actual_total != manifest_total:
        errors.append(
            "Total byte count does not match manifest"
        )

    add_check(
        "corpus_hashes",
        not errors,
        (
            f"Verified {len(manifest_files)} files"
            if not errors
            else "; ".join(errors[:10])
        )
    )

    local_manifest = (
        RAG_DIR
        / "CORPUS_MANIFEST.json"
    )

    manifests_match = (
        local_manifest.exists()
        and local_manifest.read_bytes()
        == MANIFEST_PATH.read_bytes()
    )

    add_check(
        "manifest_copies_match",
        manifests_match,
        (
            "Local and report manifests match"
            if manifests_match
            else "Manifest copies are missing or different"
        )
    )


def check_questions():
    """Validate questions.yaml"""

    if not QUESTIONS_PATH.exists():
        add_check(
            "questions",
            False,
            "questions.yaml does not exist"
        )
        return

    question_data = yaml.safe_load(
        QUESTIONS_PATH.read_text(
            encoding="utf-8"
        )
    )

    questions = question_data.get(
        "questions",
        []
    )

    add_check(
        "question_count",
        len(questions) >= 5,
        f"{len(questions)} questions"
    )

    missing_fields = []
    missing_sources = []
    single_source_count = 0

    required_fields = [
        "id",
        "question",
        "expected_answer",
        "expected_source",
    ]

    for question in questions:
        question_id = question.get(
            "id",
            "unknown"
        )

        for field in required_fields:
            value = question.get(
                field
            )

            if value is None or value == "":
                missing_fields.append(
                    f"{question_id}.{field}"
                )

        expected_source = question.get(
            "expected_source"
        )

        if expected_source:
            source_path = (
                CORPUS_DIR
                / expected_source
            )

            if not source_path.exists():
                missing_sources.append(
                    expected_source
                )

        if question.get(
            "single_source"
        ):
            single_source_count += 1

    add_check(
        "question_required_fields",
        not missing_fields,
        (
            "All questions have required fields"
            if not missing_fields
            else f"Missing: {missing_fields}"
        )
    )

    add_check(
        "question_sources_exist",
        not missing_sources,
        (
            "All expected source files exist"
            if not missing_sources
            else f"Missing: {missing_sources}"
        )
    )

    add_check(
        "single_source_questions",
        single_source_count >= 2,
        (
            f"{single_source_count} questions "
            f"marked as single source"
        )
    )


def check_raw_results():
    """Validate retrieval output files"""

    required_raw_files = [
        RAW_DIR / "chunk_metrics.csv",
        RAW_DIR / "chunk_size_diagnostic.csv",
        RAW_DIR / "per_query_metrics.csv",
        RAW_DIR / "recall_at_1.csv",
        RAW_DIR / "recall_at_1_summary.csv",
        RAW_DIR / "retrieval_results.jsonl",
        RAW_DIR / "run_metadata.json",
        RAW_DIR / "semantic_top1_comparison.csv",
        RAW_DIR / "summary_metrics.csv",
    ]

    missing_raw = [
        path.name
        for path in required_raw_files
        if not path.exists()
    ]

    add_check(
        "raw_output_files",
        not missing_raw,
        (
            "All raw output files exist"
            if not missing_raw
            else f"Missing: {missing_raw}"
        )
    )

    techniques = [
        "token",
        "semantic_95",
        "sentence_window",
        "semantic_tuned_80",
    ]

    result_errors = []
    result_count = 0

    for technique in techniques:
        for question_number in range(
            1,
            6
        ):
            result_path = (
                RAW_DIR
                / technique
                / f"Q{question_number}.json"
            )

            if not result_path.exists():
                result_errors.append(
                    f"Missing {technique}/Q{question_number}.json"
                )
                continue

            result_count += 1

            result = json.loads(
                result_path.read_text(
                    encoding="utf-8"
                )
            )

            if result.get(
                "query_embedding_dimension"
            ) != 384:
                result_errors.append(
                    f"{technique}/Q{question_number}: "
                    "wrong embedding dimension"
                )

            if result.get(
                "query_vector_shape"
            ) != [384]:
                result_errors.append(
                    f"{technique}/Q{question_number}: "
                    "wrong query shape"
                )

            if result.get(
                "document_vectors_shape"
            ) != [5, 384]:
                result_errors.append(
                    f"{technique}/Q{question_number}: "
                    "wrong document shape"
                )

            if len(
                result.get(
                    "results",
                    []
                )
            ) != 5:
                result_errors.append(
                    f"{technique}/Q{question_number}: "
                    "expected five results"
                )

            if not result.get(
                "expected_source"
            ):
                result_errors.append(
                    f"{technique}/Q{question_number}: "
                    "expected source is missing"
                )

    add_check(
        "retrieval_result_structure",
        not result_errors,
        (
            f"Verified {result_count} result files"
            if not result_errors
            else "; ".join(result_errors[:10])
        )
    )


def check_metrics():
    """Verify summary metric values"""

    summary_path = (
        RAW_DIR
        / "summary_metrics.csv"
    )

    if not summary_path.exists():
        add_check(
            "summary_metrics",
            False,
            "summary_metrics.csv does not exist"
        )
        return

    with summary_path.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as csv_file:
        rows = list(
            csv.DictReader(
                csv_file
            )
        )

    techniques = {
        row.get(
            "technique"
        )
        for row in rows
    }

    required_techniques = {
        "token",
        "semantic_95",
        "sentence_window",
    }

    add_check(
        "main_techniques",
        required_techniques.issubset(
            techniques
        ),
        f"Techniques found: {sorted(techniques)}"
    )

    recall_values = []

    for row in rows:
        if row.get(
            "technique"
        ) in required_techniques:
            recall_values.append(
                float(
                    row.get(
                        "recall_at_k",
                        0
                    )
                )
            )

    add_check(
        "recall_at_5_values",
        (
            len(recall_values) == 3
            and all(
                value == 1.0
                for value in recall_values
            )
        ),
        f"Main Recall@5 values: {recall_values}"
    )

    recall_one_path = (
        RAW_DIR
        / "recall_at_1_summary.csv"
    )

    if recall_one_path.exists():
        with recall_one_path.open(
            "r",
            encoding="utf-8",
            newline=""
        ) as csv_file:
            recall_one_rows = list(
                csv.DictReader(
                    csv_file
                )
            )

        recall_one = {
            row["technique"]: float(
                row["recall_at_1"]
            )
            for row in recall_one_rows
        }

        expected_recall_one = {
            "token": 0.8,
            "semantic_95": 0.8,
            "sentence_window": 0.6,
            "semantic_tuned_80": 0.8,
        }

        add_check(
            "recall_at_1_values",
            recall_one == expected_recall_one,
            f"Recall@1 values: {recall_one}"
        )


def check_semantic_comparison():
    """Verify identical Semantic Top-1 chunks"""

    comparison_path = (
        RAW_DIR
        / "semantic_top1_comparison.csv"
    )

    if not comparison_path.exists():
        add_check(
            "semantic_top1_comparison",
            False,
            "Comparison CSV does not exist"
        )
        return

    with comparison_path.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as csv_file:
        rows = list(
            csv.DictReader(
                csv_file
            )
        )

    identical_rows = [
        row
        for row in rows
        if (
            row.get(
                "same_text"
            ) == "True"
            and row.get(
                "same_source"
            ) == "True"
            and row.get(
                "same_store_score"
            ) == "True"
            and row.get(
                "same_manual_cosine"
            ) == "True"
        )
    ]

    add_check(
        "semantic_top1_comparison",
        (
            len(rows) == 5
            and len(identical_rows) == 5
        ),
        (
            f"{len(identical_rows)}/"
            f"{len(rows)} identical Top-1 chunks"
        )
    )


def check_metrics_document():
    """Check required METRICS.md sections"""

    if not METRICS_PATH.exists():
        add_check(
            "metrics_document",
            False,
            "METRICS.md does not exist"
        )
        return

    metrics_text = METRICS_PATH.read_text(
        encoding="utf-8"
    )

    required_sections = [
        "## Main Retrieval Comparison",
        "## Recall Saturation",
        "## Chunk Size Diagnostic",
        "## Semantic Threshold Ablation",
        "## Confidently Scored Incorrect Retrieval",
        "## Sentence-Window Q3 Failure Analysis",
        "## Observations",
        "## Conclusion",
        "## AI Use",
    ]

    missing_sections = [
        section
        for section in required_sections
        if section not in metrics_text
    ]

    add_check(
        "metrics_document_sections",
        not missing_sections,
        (
            "All required sections found"
            if not missing_sections
            else f"Missing: {missing_sections}"
        )
    )


def load_web_application():
    """Load the FastAPI application from its real folder"""

    os.environ[
        "COOKIE_SECURE"
    ] = "0"

    os.environ[
        "SECRET_KEY"
    ] = "verification-secret-key"

    if str(WEB_DIR) not in sys.path:
        sys.path.insert(
            0,
            str(WEB_DIR)
        )

    module_path = (
        WEB_DIR
        / "main.py"
    )

    module_spec = (
        importlib.util.spec_from_file_location(
            "hw3_web_main",
            module_path
        )
    )

    web_module = (
        importlib.util.module_from_spec(
            module_spec
        )
    )

    module_spec.loader.exec_module(
        web_module
    )

    return web_module


def check_web_application():
    """Test authentication and CRUD routes"""

    try:
        web_module = load_web_application()

        import routers.auth as auth_module

        client = TestClient(
            web_module.app,
            base_url="http://testserver"
        )

        home_response = client.get(
            "/"
        )

        add_check(
            "web_home",
            (
                home_response.status_code == 200
                and "Clinical Trials Portal"
                in home_response.text
            ),
            f"Status {home_response.status_code}"
        )

        invalid_response = client.post(
            "/login",
            data={
                "username": "wrong",
                "password": "wrong",
            },
            follow_redirects=False
        )

        add_check(
            "invalid_login",
            (
                invalid_response.status_code == 302
                and "error=invalid"
                in invalid_response.headers.get(
                    "location",
                    ""
                )
            ),
            (
                f"Status {invalid_response.status_code}; "
                f"location="
                f"{invalid_response.headers.get('location')}"
            )
        )

        login_response = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "password",
            },
            follow_redirects=False
        )

        set_cookie = login_response.headers.get(
            "set-cookie",
            ""
        ).lower()

        add_check(
            "valid_login",
            (
                login_response.status_code == 302
                and login_response.headers.get(
                    "location"
                ) == "/dashboard"
            ),
            (
                f"Status {login_response.status_code}; "
                f"location="
                f"{login_response.headers.get('location')}"
            )
        )

        add_check(
            "local_cookie_attributes",
            (
                "httponly" in set_cookie
                and "samesite=lax"
                in set_cookie
            ),
            set_cookie
        )

        dashboard_response = client.get(
            "/dashboard"
        )

        add_check(
            "protected_dashboard",
            (
                dashboard_response.status_code == 200
                and "Welcome"
                in dashboard_response.text
            ),
            f"Status {dashboard_response.status_code}"
        )

        trials_response = client.get(
            "/trials"
        )

        add_check(
            "trials_frontend",
            trials_response.status_code == 200,
            f"Status {trials_response.status_code}"
        )

        api_response = client.get(
            "/api/trials"
        )

        add_check(
            "crud_get",
            (
                api_response.status_code == 200
                and isinstance(
                    api_response.json(),
                    list
                )
            ),
            f"Status {api_response.status_code}"
        )

        create_response = client.post(
            "/api/trials",
            json={
                "brief_title": "Verification Trial",
                "sponsor": "Verification Sponsor",
            }
        )

        created_trial = (
            create_response.json()
            if create_response.status_code == 201
            else {}
        )

        created_id = created_trial.get(
            "id"
        )

        add_check(
            "crud_create",
            (
                create_response.status_code == 201
                and created_id is not None
            ),
            f"Status {create_response.status_code}"
        )

        if created_id is not None:
            update_response = client.put(
                f"/api/trials/{created_id}",
                json={
                    "brief_title": "Updated Verification Trial",
                    "sponsor": "Updated Verification Sponsor",
                }
            )

            add_check(
                "crud_update",
                update_response.status_code == 200,
                f"Status {update_response.status_code}"
            )

            delete_response = client.delete(
                f"/api/trials/{created_id}"
            )

            add_check(
                "crud_delete",
                delete_response.status_code == 200,
                f"Status {delete_response.status_code}"
            )

        logout_response = client.get(
            "/logout",
            follow_redirects=False
        )

        blocked_response = client.get(
            "/dashboard",
            follow_redirects=False
        )

        add_check(
            "logout_blocks_reuse",
            (
                logout_response.status_code == 302
                and blocked_response.status_code == 302
                and blocked_response.headers.get(
                    "location"
                ) == "/login"
            ),
            (
                f"Logout {logout_response.status_code}; "
                f"dashboard location="
                f"{blocked_response.headers.get('location')}"
            )
        )

        client.post(
            "/login",
            data={
                "username": "admin",
                "password": "password",
            },
            follow_redirects=False
        )

        original_timeout = (
            auth_module.IDLE_TIMEOUT_SECONDS
        )

        auth_module.IDLE_TIMEOUT_SECONDS = -1

        expired_response = client.get(
            "/dashboard",
            follow_redirects=False
        )

        auth_module.IDLE_TIMEOUT_SECONDS = (
            original_timeout
        )

        add_check(
            "idle_timeout",
            (
                expired_response.status_code == 302
                and expired_response.headers.get(
                    "location"
                ) == "/login?error=expired"
            ),
            (
                f"Status {expired_response.status_code}; "
                f"location="
                f"{expired_response.headers.get('location')}"
            )
        )

    except Exception as error:
        add_check(
            "web_application_tests",
            False,
            repr(error)
        )


def check_https_evidence():
    """Check HTTPS cookie evidence"""

    if not HTTPS_LOG_PATH.exists():
        add_check(
            "https_cookie_evidence",
            False,
            "RUN_LOG_https.txt does not exist"
        )
        return

    log_text = HTTPS_LOG_PATH.read_text(
        encoding="utf-8"
    ).lower()

    required_attributes = [
        "secure",
        "httponly",
        "samesite=lax",
    ]

    missing_attributes = [
        attribute
        for attribute in required_attributes
        if attribute not in log_text
    ]

    add_check(
        "https_cookie_evidence",
        not missing_attributes,
        (
            "Secure, HttpOnly, and SameSite=lax found"
            if not missing_attributes
            else f"Missing: {missing_attributes}"
        )
    )


def check_screenshots():
    """Check screenshot evidence filenames"""

    if not SCREENSHOTS_DIR.exists():
        add_check(
            "screenshots",
            False,
            "Screenshots folder does not exist"
        )
        return

    screenshot_names = [
        path.name.lower()
        for path in SCREENSHOTS_DIR.glob(
            "*.png"
        )
    ]

    required_patterns = [
        "home_logged_out",
        "login_form",
        "login_invalid",
        "dashboard",
        "trials_crud",
        "session_expired",
        "logout",
        "set_cookie",
        "templates_directory",
        "run_log",
    ]

    missing_patterns = [
        pattern
        for pattern in required_patterns
        if not any(
            pattern in name
            for name in screenshot_names
        )
    ]

    add_check(
        "screenshots",
        not missing_patterns,
        (
            f"{len(screenshot_names)} screenshots found"
            if not missing_patterns
            else f"Missing screenshot patterns: {missing_patterns}"
        )
    )


def check_git_order():
    """Verify questions were committed before graded run"""

    run_metadata_path = (
        RAW_DIR
        / "run_metadata.json"
    )

    if not run_metadata_path.exists():
        add_check(
            "questions_before_run",
            False,
            "run_metadata.json does not exist"
        )
        return

    run_metadata = json.loads(
        run_metadata_path.read_text(
            encoding="utf-8"
        )
    )

    run_started = datetime.fromisoformat(
        run_metadata[
            "started_at"
        ]
    )

    git_result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--format=%cI",
            "--",
            str(
                QUESTIONS_PATH.relative_to(
                    REPO_DIR
                )
            ),
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True
    )

    commit_text = git_result.stdout.strip()

    if not commit_text:
        add_check(
            "questions_before_run",
            False,
            "No commit found for questions.yaml"
        )
        return

    question_commit_time = (
        datetime.fromisoformat(
            commit_text
        )
    )

    add_check(
        "questions_before_run",
        question_commit_time < run_started,
        (
            f"Question commit: {question_commit_time.isoformat()}; "
            f"run start: {run_started.isoformat()}"
        )
    )


def check_final_artifacts():
    """Check report and Git tag in final mode"""

    report_exists = (
        REPORT_PDF_PATH.exists()
        and REPORT_PDF_PATH.stat().st_size
        > 10_000
    )

    add_check(
        "final_report_pdf",
        report_exists,
        (
            f"{REPORT_PDF_PATH.stat().st_size} bytes"
            if REPORT_PDF_PATH.exists()
            else "report.pdf does not exist"
        )
    )

    tag_result = subprocess.run(
        [
            "git",
            "tag",
            "--list",
            "hw3",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True
    )

    has_tag = (
        tag_result.stdout.strip()
        == "hw3"
    )

    add_check(
        "git_tag_hw3",
        has_tag,
        (
            "Tag hw3 exists"
            if has_tag
            else "Tag hw3 does not exist"
        )
    )


def save_verification(
    final_mode
):
    """Save verification.json"""

    passed_count = sum(
        1
        for check in checks
        if check["passed"]
    )

    failed_count = (
        len(checks)
        - passed_count
    )

    git_commit = subprocess.run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    output = {
        "verified_at": (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        ),
        "mode": (
            "final"
            if final_mode
            else "core"
        ),
        "sid4": 8561,
        "verify_seed": 268561,
        "domain_id": 1,
        "git_commit": git_commit,
        "overall_pass": (
            failed_count == 0
        ),
        "passed_checks": passed_count,
        "failed_checks": failed_count,
        "checks": checks,
    }

    VERIFICATION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    VERIFICATION_PATH.write_text(
        json.dumps(
            output,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "=" * 80
    )

    print(
        f"Passed: {passed_count}"
    )

    print(
        f"Failed: {failed_count}"
    )

    print(
        f"Overall pass: "
        f"{output['overall_pass']}"
    )

    print(
        f"Saved to: {VERIFICATION_PATH}"
    )

    print(
        "=" * 80
    )

    return output[
        "overall_pass"
    ]


def main():
    """Run all verification checks"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--final",
        action="store_true",
        help="Also require report.pdf and Git tag hw3"
    )

    arguments = parser.parse_args()

    print(
        "DATA 260 HW3 verification"
    )

    print(
        f"Repository: {REPO_DIR}"
    )

    print(
        f"Mode: "
        f"{'final' if arguments.final else 'core'}"
    )

    print()

    check_required_files()
    check_corpus()
    check_questions()
    check_raw_results()
    check_metrics()
    check_semantic_comparison()
    check_metrics_document()
    check_web_application()
    check_https_evidence()
    check_screenshots()
    check_git_order()

    if arguments.final:
        check_final_artifacts()

    overall_pass = save_verification(
        arguments.final
    )

    if not overall_pass:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()