"""
test.py — end-to-end demo of the LangGraph research assistant.

Demonstrates:
  1. Human-in-the-loop: ambiguous query triggers interrupt(); the terminal
     asks for clarification and resumes the graph with the user's answer.
  2. Multi-turn memory: a follow-up question reuses the same thread_id so
     the graph inherits the full conversation history from the checkpointer.
"""

from dotenv import load_dotenv
load_dotenv()  # Must happen before importing graph so API keys are available

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from graph import app  # Compiled graph with MemorySaver checkpointer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pending_interrupt(config: dict) -> str | None:
    """
    After an invoke() call, check whether the graph is paused at an interrupt().
    Returns the interrupt value (the clarification question) or None if the
    graph ran to completion.

    LangGraph stores pending interrupts in the state snapshot's tasks list.
    Each task that hit an interrupt() call has a non-empty .interrupts list.
    """
    snapshot = app.get_state(config)
    for task in snapshot.tasks:
        if task.interrupts:
            # .value is whatever was passed to interrupt() in the node
            return task.interrupts[0].value
    return None


def run_query(query: str, config: dict) -> str | None:
    """
    Submit a query to the graph.  Handles the interrupt/resume cycle
    automatically: if the graph pauses for clarification, prompts the user
    in the terminal and resumes.

    Returns the final_response string, or None if something unexpected happened.
    """
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")

    # ── First invoke ────────────────────────────────────────────────────────
    # Pass the user query as both the 'query' field and as a HumanMessage so
    # agents that read state["messages"] also see it.
    initial_input = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        # Initialise counter/status fields so nodes don't hit KeyError on
        # first access (TypedDict doesn't enforce defaults at runtime).
        "attempts": 0,
        "clarity_status": "",
        "confidence_score": 0,
        "validation_result": "",
        "clarification_question": "",
        "final_response": "",
        "research_findings": "",
    }

    result = app.invoke(initial_input, config=config)

    # ── Interrupt / clarification loop ──────────────────────────────────────
    # If the clarity_agent decided the query is ambiguous, the graph pauses
    # at human_feedback_node via interrupt().  We detect this, prompt the
    # user, and resume with Command(resume=answer).
    #
    # The loop handles the edge-case where a second clarification is needed
    # after the first answer (e.g. the user gives another vague reply).
    while True:
        question = _get_pending_interrupt(config)
        if question is None:
            # No pending interrupt — the graph ran to completion.
            break

        print(f"\n[Clarification needed]")
        print(f"  {question}")
        user_answer = input("  Your answer: ").strip()

        if not user_answer:
            user_answer = query  # Fall back to original if user hits Enter

        # Resume the paused graph with the human's answer.
        # Command(resume=value) is passed instead of a new input dict;
        # LangGraph injects the value as the return of interrupt() inside
        # human_feedback_node and replays execution from that point.
        result = app.invoke(Command(resume=user_answer), config=config)

    # ── Extract and display the final answer ────────────────────────────────
    final = result.get("final_response", "")
    if final:
        print(f"\n{'-'*60}")
        print("FINAL RESPONSE:")
        print(f"{'-'*60}")
        print(final)
    else:
        print("\n[No final_response in state — check agent logs above]")

    return final or None


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    # A single thread_id ties all invoke() calls together.
    # MemorySaver keyed by this id, so the conversation accumulates across turns.
    thread_id = "demo-thread-001"
    config = {"configurable": {"thread_id": thread_id}}

    # ── Turn 1: ambiguous query — should trigger interrupt ───────────────────
    # "Tell me about Apple" names a company but gives no specific goal,
    # so clarity_agent should return needs_clarification.
    run_query("Tell me about Apple", config)

    # ── Turn 2: follow-up using the SAME thread_id ───────────────────────────
    # The checkpointer already holds the full conversation history from Turn 1.
    # Agents that read state["messages"] will see both turns automatically.
    #
    # Because this is a new invoke() on an existing thread, LangGraph merges
    # the new input into the existing state rather than starting fresh.
    print(f"\n{'='*60}")
    print("FOLLOW-UP (same thread — memory inherited from Turn 1)")
    print(f"{'='*60}")
    run_query("What about their main competitors?", config)


if __name__ == "__main__":
    main()
