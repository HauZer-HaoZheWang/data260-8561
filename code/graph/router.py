from __future__ import annotations

import os

from .state import AgentState


DEFAULT_MAX_TURNS = 6


def router_logic(state: AgentState) -> str:
    #Read the ceiling from environment variable, default is 6
    max_turns = int(
        os.getenv("MAX_TURNS", str(DEFAULT_MAX_TURNS))
    )

    #Read the values needed for routing
    turn_count = state.get("turn_count", 0)
    proposal = state.get("planner_proposal")
    feedback = state.get("reviewer_feedback")

    #If Reviewer approved the proposal, finish as success.
    if feedback is not None and feedback.get("approved") is True:
        return "END"

    #If proposal is waiting for review, let Reviewer finish it
    if proposal and feedback is None:
        return "reviewer"

    #If it is not approved and reaches ceiling, stop retrying.
    if turn_count >= max_turns:
        return "END"

    #If there is no proposal, go to Planner
    if not proposal:
        return "planner"

    #There is feedback and approved is False, retry Planner.
    return "planner"