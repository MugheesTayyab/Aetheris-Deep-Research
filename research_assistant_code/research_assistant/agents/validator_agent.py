import os
import json
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables from the project-root .env file
load_dotenv()

# Pull the Google API key for Gemini authentication
api_key = os.getenv("GOOGLE_API_KEY")

# Same model as the other agents — keeps inference behaviour consistent
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=api_key,
    max_retries=2,
    temperature=0.7,
)


def validator_agent(state: dict) -> dict:
    """
    Audit whether the collected research is sufficient to answer the user's query.

    Reads research_findings from state, submits them to the LLM with an
    assessment prompt, and returns one of two verdicts:
      - "sufficient"   → synthesis can proceed
      - "insufficient" → graph routes back to research_agent for another pass

    The graph caps retries at 3 via the 'attempts' field; this agent only
    decides sufficiency — the retry cap is enforced in route_after_validation.

    Args:
        state (dict): LangGraph state containing 'query' and 'research_findings'.

    Returns:
        dict: Partial state update containing:
            messages          – [AIMessage] with the validation verdict and reason
            validation_result – "sufficient" | "insufficient"
    """

    # ── 1. Read the original query and gathered findings from state ──────────
    query             = state.get("query", "")
    research_findings = state.get("research_findings", "")

    # Fallback: if research_findings is absent, try the last non-empty message
    if not research_findings:
        for msg in reversed(state.get("messages", [])):
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if content:
                research_findings = content
                break

    if not research_findings:
        # Nothing to validate — force the graph back to research_agent
        return {
            "validation_result": "insufficient",
            "messages": [
                AIMessage(content="Validation failed: no research findings were found.")
            ],
        }

    # ── 2. Build the validation prompt ──────────────────────────────────────
    # The LLM is instructed to evaluate factual depth, recency, and relevance
    system_prompt = (
        "You are a research validation specialist. "
        "Your job is to assess whether the provided research findings contain "
        "enough relevant, accurate, and complete information to fully answer "
        "the user's query. Consider factual depth, recency, and relevance.\n"
        "Respond ONLY with valid JSON — no markdown, no extra text:\n"
        '{"validation_result": "sufficient" or "insufficient", '
        '"reason": "<brief explanation of your assessment>"}'
    )

    # Truncate to 5 000 chars to stay within the model's practical context window
    validation_prompt = (
        f"User query: {query}\n\n"
        f"Research findings:\n{research_findings[:5000]}"
    )

    # ── 3. Call the LLM with retry on rate-limit errors ─────────────────────
    try:
        for attempt in range(5):      # Up to 5 tries before giving up
            try:
                response = llm.invoke([
                    HumanMessage(content=f"{system_prompt}\n\n{validation_prompt}")
                ])
                raw_text = response.content.strip()
                break                 # Clean response — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    time.sleep(25)    # Back off before the next attempt
                else:
                    raise inner_e
    except Exception as e:
        # LLM failure — default to insufficient so research is retried
        return {
            "validation_result": "insufficient",
            "messages": [
                AIMessage(content=f"Validation LLM call failed: {e}. Retrying research.")
            ],
        }

    # ── 4. Parse the JSON response safely ───────────────────────────────────
    try:
        # Strip markdown code fences if the model added them despite instructions
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]    # Remove the "json" language tag

        parsed            = json.loads(raw_text)
        validation_result = parsed.get("validation_result", "insufficient")
        reason            = parsed.get("reason", "")

        # Normalise any unexpected value — only two legal outputs exist
        if validation_result not in ("sufficient", "insufficient"):
            validation_result = "insufficient"
            reason = f"Unexpected validation_result value; defaulting to insufficient. Raw: {raw_text}"

    except (json.JSONDecodeError, KeyError):
        validation_result = "insufficient"
        reason = f"Could not parse validation response. Raw output: {raw_text[:200]}"

    # ── 5. Build an AI message recording the verdict ─────────────────────────
    verdict_message = AIMessage(
        content=f"Validation result: {validation_result.upper()}. Reason: {reason}"
    )

    # ── 6. Return updated state ──────────────────────────────────────────────
    return {
        "messages": [verdict_message],
        "validation_result": validation_result,
    }
