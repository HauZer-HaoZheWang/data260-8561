from __future__ import annotations

from .state import AgentState


MAX_TURNS = 6


def router_logic(state: AgentState) -> str:
    #Read the values needed for routing
    turn_count = state.get("turn_count", 0)
    proposal = state.get("planner_proposal")
    feedback = state.get("reviewer_feedback")

    #If Reviewer approved the proposal, finish as success.
    #Check this before MAX_TURNS so an approval on turn 6 still counts.
    if feedback is not None and feedback.get("approved") is True:
        return "END"

    #If it is not approved and reaches the ceiling, stop retrying
    if turn_count >= MAX_TURNS:
        return "END"

    #If Planner has not created a proposal, go to Planner.
    if not proposal:
        return "planner"

    #If there is a proposal but no feedback, go to Reviewer
    if feedback is None:
        return "reviewer"

    #There is feedback and approved is False, go back to Planner.
    return "planner"