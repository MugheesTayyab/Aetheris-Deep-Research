from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ResearchState(TypedDict):
    # Full conversation history; add_messages merges incoming messages
    # rather than overwriting, so the list grows incrementally each node run.
    messages: Annotated[list[BaseMessage], add_messages]

    # The user's raw research query, set at graph entry and carried forward
    # unchanged so every agent always has access to the original question.
    query: str

    # Set by the clarity_agent to signal whether the query is unambiguous
    # ("clear") or too vague to research reliably ("needs_clarification").
    clarity_status: str  # "clear" | "needs_clarification"

    # Numeric confidence (0–10) that the research_agent assigns to its own
    # findings; drives the conditional edge into the validator.
    confidence_score: int

    # Set by the validator_agent after auditing the research output.
    # "sufficient" lets the graph proceed to synthesis; "insufficient"
    # sends it back to the research_agent for another pass.
    validation_result: str  # "sufficient" | "insufficient"

    # Counts how many times the research_agent has executed in this run.
    # The conditional edge caps retries to prevent infinite loops.
    attempts: int

    # Populated by the clarity_agent when clarity_status is
    # "needs_clarification"; surfaced to the user before any research starts.
    clarification_question: str

    # Raw search results concatenated by research_agent; read by validator
    # and synthesis_agent. Empty string until research_agent runs.
    research_findings: str

    # The polished, citation-rich answer produced by the synthesis_agent;
    # empty string until synthesis completes successfully.
    final_response: str
