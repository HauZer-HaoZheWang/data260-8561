from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

# make code importable so i can reuse HW1 helpers
CODE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = CODE_DIR.parent / "src"
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(SRC_DIR))

from model_client import complete
from agents_demo import extract_json_block, parse_and_coerce

from .state import AgentState

def planner_node(state: AgentState) -> dict[str, Any]: 
    print("-------NODE: Planner------")

    #Because the "class AgentState(TypedDict, total=False):"
    #total=False means there may be null
    #So i use ".get()" function ranther than "x = state["x"]" which may cause "KeyError: 'strict'"
    title = state.get("title", "") #dictionary.get("key", default_value)
    content = state.get("content", "")
    strict = state.get("strict", False)
    feedback = state.get("reviewer_feedback") # There is nothing when 1st running, 
    #and if feedback is not None:
    #print("Reviewer feedback")
    #else:
    #print("This is first time run")
    #Read existed trace, if not exist, use empty list
    old_trace = state.get("trace", [])

    #Tell model the Planner's tasks, output format and limitations.
    system_text = (
        "You are the Planner in a planner-reviewer workflow. "
        "Read the title and content, then generate exactly three topical tags "
        "and one short summary. "
        "Return only one valid JSON object. "
        "Use exactly this JSON structure: "
        '{"thought": "string", '
        '"message": "string", '
        '"data": {'
        '"tags": ["string", "string", "string"], '
        '"summary": "string", '
        '"issues": []'
        "}}. "
        "The message must not be empty, must contain no code, "
        "and must contain no more than 60 words. "
        "The tags array must contain exactly three string tags. "
        "Each tag must contain between 3 and 30 characters. "
        "The summary must contain no more than 25 words "
        "and must not contain an ellipsis. "
        "The issues field must be an array. "
        "Do not include Markdown, code fences, "
        "or any text outside the JSON object."
    )

    #Put the exact title and content itno user_text
    user_text = f"Title: {title}\nContent: {content}"

    #If there do has feedback by Reviewer
    if feedback is not None:
    #Change Python dictionary into a valid JSON string.
        feedback_text = json.dumps(
        feedback,
        ensure_ascii=False
        )

    #Put Reviewer feedback into user_text
        user_text += (
        "\n\nThe previous proposal did not pass review."
        "\nPlease revise it according to this reviewer feedback:"
        f"\n{feedback_text}"
        "\n\nReturn a corrected proposal using the same JSON structure."
        )
    #Put all the text together into a list for sending to model.
    messages = [
        {
            "role": "system",
            "content": system_text
        },
        {
            "role": "user",
            "content": user_text
        }
    ]

    #Before use model, record time.
    start_time = time.time()

    #Use model amd save the returned result. 
    result = complete(messages)

    #Record time after finished call the model.
    end_time = time.time()

    #Calculate lantency by ms.
    latency_ms = (end_time - start_time) * 1000


    #Result[“text”] is the text returned by the model.
    #Parse_and_coerce() already extracts the JSON internally,
    #So there is no need to call extract_json_block again here.
    planner_proposal = parse_and_coerce(result["text"], title, content, strict)

    #Create the trace for this running.
    new_trace = {
        "node": "planner",
        "strict": strict,
        "latency_ms": round(latency_ms, 2),
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }

    return {
        "planner_proposal": planner_proposal,
        #Planner has consumed the feedback, so clear it
        #Otherwise, the router keeps seeing approved=False and routes back to Planner forever.
        "reviewer_feedback": None,
        "trace": old_trace + [new_trace],
    }



def reviewer_node(state: AgentState) -> dict[str, Any]:
    print("-------NODE: Reviewer------")

    #Read Planner's proposal, if not exist, use empty dictionary
    proposal = state.get("planner_proposal", {})

    #Read existed trace, it should already have Planner's trace.
    old_trace = state.get("trace", [])

    #Tell model the Reviewer's tasks, output format and limitations
    system_text = (
        "You are the Reviewer in a planner-reviewer workflow. "
        "Your job is to check the Planner proposal, not generate a new proposal. "
        "Check these three requirements: "
        "the tags array must contain exactly three string tags; "
        "each tag must contain between 3 and 30 characters; "
        "and the summary must contain no more than 25 words. "
        "Return only one valid JSON object. "
        "Use exactly this JSON structure: "
        '{"approved": true, "issues": ["string"]}. '
        "If all requirements pass, set approved to true "
        "and return an empty issues array. "
        "If any requirement fails, set approved to false "
        "and explain every problem in the issues array. "
        "Do not include Markdown, code fences, "
        "or any text outside the JSON object."
    )

    #Change Python dictionary into a valid JSON string
    proposal_text = json.dumps(
        proposal,
        ensure_ascii=False
    )

    #Put Planner's proposal into user_text.
    user_text = (
        "Review the following Planner proposal:\n"
        f"{proposal_text}"
    )

    #Put all the text together into a list for sending to model
    messages = [
        {
            "role": "system",
            "content": system_text
        },
        {
            "role": "user",
            "content": user_text
        }
    ]

    #Before use model, record time.
    start_time = time.time()

    #Use model and save the returned result
    result = complete(messages)

    #Record time after finished calling the model.
    end_time = time.time()

    #Calculate latency by ms
    latency_ms = (end_time - start_time) * 1000

    #Try to extract JSON and change it into a Python dictionary.
    try:
        reviewer_json_text = extract_json_block(result["text"])
        reviewer_feedback = json.loads(reviewer_json_text)

        #Check whether the whole result is a dictionary
        if not isinstance(reviewer_feedback, dict):
            raise ValueError(
                "Reviewer output must be a dictionary."
            )

        #Check whether approved exists and is Boolean.
        if not isinstance(reviewer_feedback.get("approved"), bool):
            raise ValueError(
                "Reviewer output must contain a Boolean approved field."
            )

        #Check whether issues exists and is a list
        if not isinstance(reviewer_feedback.get("issues"), list):
            raise ValueError(
                "Reviewer output must contain an issues list."
            )

        #Check every issue in the list is a string.
        if not all(
            isinstance(issue, str)
            for issue in reviewer_feedback["issues"]
        ):
            raise ValueError(
                "Every issue must be a string."
            )

    #If parsing failed, make a safe feedback and send it back to Planner
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        reviewer_feedback = {
            "approved": False,
            "issues": [
                f"Reviewer output could not be parsed: {error}"
            ]
        }

    #Create the trace for this running.
    new_trace = {
        "node": "reviewer",
        "latency_ms": round(latency_ms, 2),
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }

    #Return Reviewer feedback and a new trace list
    return {
        "reviewer_feedback": reviewer_feedback,
        "trace": old_trace + [new_trace],
    }


def supervisor_node(state: AgentState) -> dict[str, Any]:
    print("-------NODE: Supervisor------")

    #Read turn_count and return its value plus one.
    return {"turn_count": state.get("turn_count", 0) + 1}


