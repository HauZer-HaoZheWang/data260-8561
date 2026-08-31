# DOMAIN_SCHEMA — ClinicalTrials

## Configuration

| Key | Value |
|---|---|
| SID4 | 8561 |
| PORT_BASE | 8461 |
| PREFIX | s8561 |
| SEED | 8561 |
| VERIFY_SEED | 268561 |
| DOMAIN_ID | 1 |

## Entity


**Entity name:** 'Clinical Trial Registration'

This entity is the list of clinical trials.

## Use case

The application of people who wants to upload a new trial.

## Fields

| Field name | HTML type | Required | Placeholder | Notes |
|---|---|---|---|---|
| 'briefTitle' | 'text' | Yes | 'Please type in the brief title of trial description which can be easily read by people.' | 'This is primary field and can make your trial be easily find and read by others.' |
| 'sponsor' | 'text' | Yes | 'Please type in the sponsor of trial, e.g. University of Colorado, Denver.' | 'This is the information of the sponsor of this trial.' |
| 'submitterEmail'| 'email' | Yes | 'Please type in the email address to contact submitter.' | 'This is the submission metadata for contacting the submitter, not part of trial record.' |
| 'detailedDescription' | 'textarea' | Yes | 'Please type in the detailed description of trial' | 'This describe the details of trial.' |
| 'funderType'| 'select' | Yes | - | 'This is a drop-down menu for showing where the fund from. See the details below.'|
| 'agreeTerms'| 'checkbox' | Yes | - | 'I agree to the terms and conditions.'|
| 'submitBtn'| 'submit' | - | - | 'Submit Trial!' |

**Primary field:** `briefTitle` — This is the brief title which makes the trial can be rapidly read and understand by people.

**Secondary field:** `sponsor` — This can show people who is or was sponsored for this trial.

## Category values

**Field:** 'Funder Type'

| Value | Meaning |
|---|---|
| 'NIH' | U.S. National Institutes of Health |
| 'Other U.S. federal agency' | For example, Food and Drug Administration, Centers for Disease Control and Prevention, or U.S. Department of Veterans Affairs |
| 'Industry' | for example: pharmaceutical and device companies |
| 'All others (individuals, universities, organizations)' | including individuals, universities, and community-based organizations |

### Why this axis

In this domain, where the research fund from is vital, which decide whether this experiment is fair, impartial, and objective or not.
For example, when pharmaceutical companies fund research on their own drugs, there is a structural conflict of interest; publication bias leads to negative results not being disclosed.

### Alternatives considered and rejected

| Axis | Why rejected |
|---|---|
| 'Study Type' | There are only 3 values in real website's axis. |
| 'Medical vs Surgical' | Does not meet the MECE criteria: drug trials, behavioral interventions, and diagnostic tests cannot be categorized. |
| 'NCT Number' | If use it as a primary field, it has not been generated yet during the application submission process. Besides, this is the code for computers to identify, humans can not understand it. |

## Validation rules

- detailedDescription: more than 25 characters (required by assignment)
- agreeTerms: must be checked (required by assignment)
- briefTitle: at most 50 words (custom rule)