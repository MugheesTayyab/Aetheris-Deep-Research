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
    max_retries=2,
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
                raw_text = _extract_text(response.content).strip()
                break                 # Clean response — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    # Exponential backoff capped at 8 s (stays within Vercel's 10 s limit)
                    wait = min(2 ** (attempt + 1), 8)
                    time.sleep(wait)
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
