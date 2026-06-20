import os
import json
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables from the project-root .env file
load_dotenv(override=True)

# Pull the OpenRouter API key
api_key = os.getenv("OPENROUTER_API_KEY")

# OpenRouter Model
model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    max_retries=2,      # LangChain retries once on transient network errors
    temperature=0.7,
)


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"):
                text_parts.append(part.text)
            elif hasattr(part, "get") and part.get("text"):
                text_parts.append(part.get("text"))
        return "".join(text_parts)
    return str(content)


def clarity_agent(state: dict) -> dict:
    """
    Decide whether the user's query is specific enough to research immediately.

    Reads the most recent message from the LangGraph state, submits it to
    the LLM with a strict JSON-response instruction, and returns one of two
    outcomes:
      - "clear"               → research can begin straight away
      - "needs_clarification" → the graph pauses for human input

    Args:
        state (dict): Current LangGraph state. Must contain a 'messages' list
                      of BaseMessage objects (or plain dicts with a 'content' key).

    Returns:
        dict: Partial state update containing:
            messages             – [AIMessage] summarising the clarity decision
            query                – raw query string, passed through for downstream agents
            clarity_status       – "clear" | "needs_clarification"
            clarification_question – follow-up question for the user (empty when clear)
    """

    # ── 1. Extract the latest user message ──────────────────────────────────
    messages = state.get("messages", [])
    if not messages:
        # No messages means there is nothing to evaluate — ask the user to start
        return {
            "clarity_status": "needs_clarification",
            "clarification_question": "Please enter a research query with a company name and a specific goal.",
        }

    # The most recent message is at the tail; add_messages appends, not prepends
    latest_message = messages[-1]

    # Handle both LangChain BaseMessage objects and plain dict messages
    if hasattr(latest_message, "content"):
        user_query = latest_message.content
    else:
        user_query = latest_message.get("content", "")

    # Persist the raw query string so downstream agents can read it directly
    # without iterating through the messages list themselves
    query = state.get("query", user_query)

    # ── 2. Build the evaluation prompt ──────────────────────────────────────
    # Strict JSON-only instruction minimises the chance of the model adding
    # prose or markdown that would break json.loads below
    system_prompt = (
        "You are a query analysis assistant. "
        "Evaluate whether the following user query clearly names a real company "
        "AND has a specific, researchable goal (e.g. financials, recent news, "
        "leadership, products, competitors). "
        "Respond ONLY with valid JSON — no markdown, no extra text — in this exact format:\n"
        '{"clarity_status": "clear" or "needs_clarification", '
        '"clarification_question": "question to ask the user if unclear, else empty string"}'
    )

    evaluation_prompt = f"User query: {user_query}"

    # ── 3. Call the LLM with retry on rate-limit errors ─────────────────────
    try:
        for attempt in range(5):      # Maximum 5 attempts before giving up
            try:
                response = llm.invoke([
                    HumanMessage(content=f"{system_prompt}\n\n{evaluation_prompt}")
                ])
                raw_text = _extract_text(response.content).strip()
                break                 # Clean response received — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    # Exponential backoff capped at 8 s (stays within Vercel's 10 s limit)
                    wait = min(2 ** (attempt + 1), 8)
                    time.sleep(wait)
                else:
                    raise inner_e     # Non-rate-limit error: propagate immediately
    except Exception as e:
        # All retries exhausted or unrecoverable error — surface it as a
        # clarification prompt so the user knows what went wrong
        return {
            "clarity_status": "needs_clarification",
            "clarification_question": f"There was an error evaluating your query ({e}). Please rephrase and try again.",
            "query": query,
        }

    # ── 4. Parse the JSON response safely ───────────────────────────────────
    try:
        # Strip markdown code fences if the model wrapped the JSON anyway
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]   # Remove the "json" language tag

        parsed = json.loads(raw_text)
        clarity_status = parsed.get("clarity_status", "needs_clarification")
        clarification_question = parsed.get("clarification_question", "")
    except (json.JSONDecodeError, KeyError):
        # Unparseable response — default to asking the user to rephrase
        clarity_status = "needs_clarification"
        clarification_question = (
            "Could not parse the clarity evaluation. "
            "Please make sure your query names a company and a specific research goal."
        )

    # ── 5. Add an AI message summarising the outcome ─────────────────────────
    if clarity_status == "clear":
        agent_message = AIMessage(
            content=f"Query is clear. Proceeding to research: '{user_query}'"
        )
    else:
        agent_message = AIMessage(
            content=f"Clarification needed: {clarification_question}"
        )

    # ── 6. Return the updated state fields ──────────────────────────────────
    return {
        "messages": [agent_message],
        "query": query,
        "clarity_status": clarity_status,
        "clarification_question": clarification_question,
    }
