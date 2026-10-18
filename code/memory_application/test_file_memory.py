from __future__ import annotations

from pathlib import Path

try:
    from .agent_rules import generate_trial_summary, verify_agent_rules
    from .file_memory import consolidate_memory
except ImportError:  # direct script execution
    from agent_rules import generate_trial_summary, verify_agent_rules
    from file_memory import consolidate_memory


def test_consolidation_and_agent_rules() -> None:
    fixture = Path(__file__).resolve().parents[2] / "reports" / "hw06" / "raw" / "MEMORY_original_55.md"
    result = consolidate_memory(fixture.read_text(encoding="utf-8"))
    assert result["before"] == 55
    assert result["after"] < 40
    assert result["duplicates_merged"] >= 1
    assert len(result["conflicts"]) >= 3
    assert verify_agent_rules(generate_trial_summary("A trial", "active", "observational"))["flat_bullets"]


if __name__ == "__main__":
    test_consolidation_and_agent_rules()
    print("PASS - file memory consolidation and AGENT rules")
