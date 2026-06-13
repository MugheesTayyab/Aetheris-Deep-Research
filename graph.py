from __future__ import annotations
import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt, Command

from state import ResearchState
# Import the actual function names defined in each agent file
from agents.clarity_agent import clarity_agent
from agents.research_agent import research_agent
from agents.validator_agent import validator_agent
from agents.synthesis_agent import synthesis_agent


# ---------------------------------------------------------------------------
# Human-in-the-loop node
# ---------------------------------------------------------------------------

def human_feedback_node(state: ResearchState) -> dict:
    """
    Pause the graph and surface the clarification question to the caller.

    How interrupt() works:
      1. interrupt(value) suspends the graph immediately.
      2. The runtime serialises the current state into the checkpointer and
         returns control to the caller (invoke() / stream() returns early).
      3. The caller reads the interrupt value via app.get_state(config),
         collects the human answer, then calls
             app.invoke(Command(resume=answer), config=config)
      4. The graph resumes HERE — interrupt() returns the resumed value —
         and execution continues normally from this point.
    """
    question = state.get("clarification_question") or "Please clarify your query:"

    # interrupt() pauses and hands `question` back to the caller.
    # When the caller resumes with Command(resume=answer), interrupt()
    # returns `answer` here.
    user_answer: str = interrupt(question)

    # Store the clarified text as the new query so clarity_agent
    # re-evaluates it on the next pass.
    from langchain_core.messages import HumanMessage
    return {
        "query": user_answer,
        "messages": [HumanMessage(content=user_answer)],
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_clarity(state: ResearchState) -> str:
    """Pause for human input when the query is too vague; otherwise research."""
    if state.get("clarity_status") == "needs_clarification":
        return "human_feedback"
    return "research_agent"


def route_after_research(state: ResearchState) -> str:
    """High-confidence findings skip the validator and go straight to synthesis."""
    if state.get("confidence_score", 0) >= 6:
        return "synthesis_agent"
    return "validator_agent"


def route_after_validation(state: ResearchState) -> str:
    """Retry research until sufficient or the attempt cap (3) is hit."""
    if state.get("validation_result") == "insufficient" and state.get("attempts", 0) < 3:
        return "research_agent"
    return "synthesis_agent"


# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

graph = StateGraph(ResearchState)

# ---- Nodes ----------------------------------------------------------------
graph.add_node("clarity_agent",   clarity_agent)
graph.add_node("human_feedback",  human_feedback_node)
graph.add_node("research_agent",  research_agent)
graph.add_node("validator_agent", validator_agent)
graph.add_node("synthesis_agent", synthesis_agent)

# ---- Edges ----------------------------------------------------------------

# 1. Every run starts with a clarity check.
graph.add_edge(START, "clarity_agent")

# 2. clarity_agent → human_feedback (needs_clarification) or research_agent (clear)
graph.add_conditional_edges(
    "clarity_agent",
    route_after_clarity,
    {
        "human_feedback": "human_feedback",
        "research_agent": "research_agent",
    },
)
# After the user answers, re-run clarity_agent to validate the updated query.
graph.add_edge("human_feedback", "clarity_agent")

# 3. research_agent → synthesis_agent (confidence >= 6) or validator_agent
graph.add_conditional_edges(
    "research_agent",
    route_after_research,
    {
        "synthesis_agent": "synthesis_agent",
        "validator_agent": "validator_agent",
    },
)

# 4. validator_agent → research_agent (retry) or synthesis_agent (done / cap hit)
graph.add_conditional_edges(
    "validator_agent",
    route_after_validation,
    {
        "research_agent": "research_agent",
        "synthesis_agent": "synthesis_agent",
    },
)

# 5. synthesis_agent is always the terminal node.
graph.add_edge("synthesis_agent", END)

# ---------------------------------------------------------------------------
# Compile
# SqliteSaver persists checkpoints to disk, keyed by thread_id.
# On Vercel /tmp is the only writable directory; locally we use the project root.
# Pass {"configurable": {"thread_id": "<id>"}} to every invoke() call so
# the same thread accumulates history across multiple turns.
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join(
    "/tmp" if os.environ.get("VERCEL") else os.path.dirname(os.path.abspath(__file__)),
    "aetheris_checkpoints.db",
)
# SqliteSaver.from_conn_string() is a context manager — pass an open connection instead
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
app = graph.compile(checkpointer=SqliteSaver(_conn))
