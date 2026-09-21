"""Fetch clinical trial records from ClinicalTrials.gov API v2
and render them as plain text documents for the RAG corpus.

DOMAIN_ID = 1
SEED = 8561
"""

import hashlib
import json
import time
from pathlib import Path

import requests


#Get the code/rag folder
BASE_DIR = Path(__file__).resolve().parent.parent

#Get the repository root folder
REPO_DIR = BASE_DIR.parent.parent

#Store rendered text files here
CORPUS_DIR = BASE_DIR / "corpus"

#Store the original API response here
RAW_DIR = BASE_DIR / "raw_json"

#Store required homework report files here
REPORTS_DIR = REPO_DIR / "reports" / "hw03"

#ClinicalTrials.gov API v2 endpoint
API = "https://clinicaltrials.gov/api/v2/studies"

#Use fixed query settings for the experiment
QUERY = {
    "query.cond": "diabetes OR lung cancer OR hypertension",
    "filter.overallStatus": "RECRUITING",
    "pageSize": 100,
    "format": "json",
}


def render(study: dict) -> tuple[str, str]:
    """Turn one study record into a filename and plain text"""

    #Get the main protocol section
    protocol = study.get(
        "protocolSection",
        {}
    )

    #Get each module from the study record
    identification = protocol.get(
        "identificationModule",
        {}
    )
    status = protocol.get(
        "statusModule",
        {}
    )
    design = protocol.get(
        "designModule",
        {}
    )
    description = protocol.get(
        "descriptionModule",
        {}
    )
    conditions = protocol.get(
        "conditionsModule",
        {}
    )
    interventions = protocol.get(
        "armsInterventionsModule",
        {}
    )
    eligibility = protocol.get(
        "eligibilityModule",
        {}
    )
    outcomes = protocol.get(
        "outcomesModule",
        {}
    )
    sponsors = protocol.get(
        "sponsorCollaboratorsModule",
        {}
    )

    #Use the NCT number as the filename
    nct_number = identification.get(
        "nctId",
        "UNKNOWN"
    )

    #Build a readable plain text document
    lines = [
        f"NCT Number: {nct_number}",
        f"Title: {identification.get('briefTitle', '')}",
        f"Official Title: {identification.get('officialTitle', '')}",
        (
            "Lead Sponsor: "
            f"{sponsors.get('leadSponsor', {}).get('name', '')}"
        ),
        f"Overall Status: {status.get('overallStatus', '')}",
        (
            "Start Date: "
            f"{status.get('startDateStruct', {}).get('date', '')}"
        ),
        f"Study Type: {design.get('studyType', '')}",
        f"Phases: {', '.join(design.get('phases', []))}",
        (
            "Enrollment: "
            f"{design.get('enrollmentInfo', {}).get('count', '')}"
        ),
        (
            "Conditions: "
            f"{', '.join(conditions.get('conditions', []))}"
        ),
        "",
        "Brief Summary:",
        description.get(
            "briefSummary",
            ""
        ),
        "",
        "Detailed Description:",
        description.get(
            "detailedDescription",
            ""
        ),
        "",
        "Interventions:",
    ]

    #Add every intervention
    for intervention in interventions.get(
        "interventions",
        []
    ):
        intervention_type = intervention.get(
            "type",
            ""
        )
        intervention_name = intervention.get(
            "name",
            ""
        )
        intervention_description = intervention.get(
            "description",
            ""
        )

        lines.append(
            f"- {intervention_type}: "
            f"{intervention_name}. "
            f"{intervention_description}"
        )

    #Add eligibility information
    lines += [
        "",
        "Eligibility Criteria:",
        eligibility.get(
            "eligibilityCriteria",
            ""
        ),
        (
            "Minimum Age: "
            f"{eligibility.get('minimumAge', '')}"
        ),
        (
            "Maximum Age: "
            f"{eligibility.get('maximumAge', '')}"
        ),
        f"Sex: {eligibility.get('sex', '')}",
        "",
        "Primary Outcome Measures:",
    ]

    #Add every primary outcome
    for outcome in outcomes.get(
        "primaryOutcomes",
        []
    ):
        measure = outcome.get(
            "measure",
            ""
        )
        time_frame = outcome.get(
            "timeFrame",
            ""
        )
        outcome_description = outcome.get(
            "description",
            ""
        )

        lines.append(
            f"- {measure} "
            f"[Time Frame: {time_frame}] "
            f"{outcome_description}"
        )

    #Join all fields into one plain text document
    text = "\n".join(
        line
        for line in lines
        if line is not None
    )

    return f"{nct_number}.txt", text


def main():
    """Download, render, and document the clinical trial corpus"""

    #Create all output folders
    CORPUS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    #Remove old generated files before rebuilding the corpus
    for old_file in CORPUS_DIR.glob("*.txt"):
        old_file.unlink()

    #Download studies from ClinicalTrials.gov
    response = requests.get(
        API,
        params=QUERY,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()

    #Keep the original response for verification
    raw_response_path = RAW_DIR / "api_response.json"
    raw_response_path.write_text(
        json.dumps(
            data,
            indent=2
        ),
        encoding="utf-8"
    )

    manifest = []
    total_bytes = 0

    #Sort by NCT number to keep file order stable
    studies = sorted(
        data.get(
            "studies",
            []
        ),
        key=lambda study: (
            study.get(
                "protocolSection",
                {}
            )
            .get(
                "identificationModule",
                {}
            )
            .get(
                "nctId",
                ""
            )
        )
    )

    #Render every study as one text file
    for study in studies:
        filename, text = render(study)

        #Skip records with too little useful text
        if len(text) < 1500:
            continue

        file_path = CORPUS_DIR / filename

        file_path.write_text(
            text,
            encoding="utf-8"
        )

        file_bytes = file_path.read_bytes()
        byte_count = len(file_bytes)
        sha256 = hashlib.sha256(
            file_bytes
        ).hexdigest()

        manifest.append(
            {
                "filename": filename,
                "bytes": byte_count,
                "sha256": sha256,
            }
        )

        total_bytes += byte_count

    #Find the smallest and largest rendered files
    file_sizes = [
        item["bytes"]
        for item in manifest
    ]

    smallest_file_bytes = min(
        file_sizes,
        default=0
    )
    largest_file_bytes = max(
        file_sizes,
        default=0
    )

    #Show the corpus size in the terminal
    print(
        f"{len(manifest)} files, "
        f"{total_bytes} bytes "
        f"({total_bytes / 1024:.1f} KB)"
    )

    print(
        f"Size range: "
        f"{smallest_file_bytes} to "
        f"{largest_file_bytes} bytes"
    )

    #Warn when the graded corpus is too small
    if total_bytes < 200 * 1024:
        print(
            "Warning: Corpus is smaller than 200 KB. "
            "Add more studies before running the graded experiment."
        )
    else:
        print(
            "Corpus size requirement satisfied."
        )

    #Create the machine readable corpus manifest
    manifest_data = {
        "generated_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        ),
        "source": API,
        "query": QUERY,
        "file_count": len(manifest),
        "total_bytes": total_bytes,
        "smallest_file_bytes": smallest_file_bytes,
        "largest_file_bytes": largest_file_bytes,
        "files": manifest,
    }

    manifest_text = json.dumps(
        manifest_data,
        indent=2
    )

    #Keep one manifest beside the corpus
    local_manifest_path = (
        BASE_DIR / "CORPUS_MANIFEST.json"
    )
    local_manifest_path.write_text(
        manifest_text,
        encoding="utf-8"
    )

    #Keep one manifest in the required report folder
    report_manifest_path = (
        REPORTS_DIR / "CORPUS_MANIFEST.json"
    )
    report_manifest_path.write_text(
        manifest_text,
        encoding="utf-8"
    )

    print(
        f"Local manifest saved to "
        f"{local_manifest_path}"
    )

    print(
        f"Report manifest saved to "
        f"{report_manifest_path}"
    )


if __name__ == "__main__":
    main()