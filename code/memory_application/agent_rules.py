from __future__ import annotations


def generate_trial_summary(title: str, status: str, category: str) -> str:
    return f"- Trial: {title.strip()[:100]}\n- Status: {status}\n- Category: {category}"


def verify_agent_rules(output: str) -> dict:
    lines = [line for line in output.splitlines() if line.strip()]
    return {"flat_bullets": all(line.startswith("- ") for line in lines), "max_six_lines": len(lines) <= 6, "no_secret_marker": "MYSQL_ROOT_PASSWORD" not in output}
