from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared memory for all nodes in the graph.

    Every node reads from this and returns update to it.
    total=False means all keys are optional, so a key can be missing until a node creates it.
    """

    # Inputs: set once when the run starts
    title: str
    content: str
    email: str
    strict: bool #strick mode by boolean
    task: str

    # Outputs: created by nodes while the graph runs
    planner_proposal: dict[str, Any]
    reviewer_feedback: dict[str, Any]

    # Loop safety: stops the graph from looping forever
    turn_count: int

    # Experiment data: one record per LLM call (Part 4 needs this)
    trace: list[dict[str, Any]]


def initialize_state(
    title: str,
    content: str,
    email: str,
    strict: bool,
    task: str
) -> AgentState:
    """Build a fresh state for one run.

    This is a function, not a variable, so every run gets its own new dict and its own new empty list.
    A module-level variable would be shared by all runs and mix their data together.
    """
    return {
        "title": title,
        "content": content,
        "email": email,
        "strict": strict,
        "task": task,
        # start at 0 so the first increment work
        "turn_count": 0,
        # empty list, filled in by each node as it running
        "trace": []
    }