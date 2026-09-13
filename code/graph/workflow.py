from __future__ import annotations

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import planner_node, reviewer_node, supervisor_node
from .router import router_logic


def build_workflow():
    #Create a workflow using AgentState
    workflow = StateGraph(AgentState)

    #Add three nodes into the workflow.
    workflow.add_node("planner", planner_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("supervisor", supervisor_node)

    #Use Supervisor as entry, so turn_count will add 1 first, then router decides where to go.
    workflow.set_entry_point("supervisor")
    #Use router_logic to decide where to go after Supervisor.
    workflow.add_conditional_edges(
        "supervisor",
        router_logic,
        {
            "planner": "planner",
            "reviewer": "reviewer",
            "END": END,
        }
    )

    #After Planner finishes, always go back to Supervisor.
    workflow.add_edge("planner", "supervisor")

    #After Reviewer finishes, always go back to Supervisor
    workflow.add_edge("reviewer", "supervisor")

    #Compile and return the finished workflow.
    return workflow.compile()