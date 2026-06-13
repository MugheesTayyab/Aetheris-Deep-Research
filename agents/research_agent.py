import os
import json
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables from the project-root .env file
load_dotenv(override=True)

# Pull the Google API key for Gemini authentication
api_key = os.getenv("GOOGLE_API_KEY")

# Gemini 3.5 Flash balances speed and quality for multi-step research tasks
model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
llm = ChatGoogleGenerativeAI(
    model=model_name,
    google_api_key=api_key,
    max_retries=2,       # Built-in LangChain retry for transient failures
    temperature=0.7,
)

# Tavily is a search engine built specifically for LLM agents; it returns
# structured {url, content} dicts instead of raw HTML, making parsing trivial
search_tool = TavilySearchResults(
    max_results=5,                               # Cap at 5 results per search
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
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


def _run_search(query: str) -> str:
    """
    Execute one Tavily search and return the results as a numbered string.

    Each result is formatted as "[n] <url>\n<content>" so downstream prompts
    can reference sources by their index number.

    Args:
        query (str): The search string sent to Tavily.

    Returns:
        str: Numbered results joined by blank lines, or an error message string.
    """
    try:
        results = search_tool.invoke(query)    # Returns a list of result dicts
        formatted = []
        for i, result in enumerate(results, 1):
            url     = result.get("url", "N/A")
            content = result.get("content", "").strip()
            # "[n] URL\ncontent" format makes sources easy for the LLM to cite
            formatted.append(f"[{i}] {url}\n{content}")
        return "\n\n".join(formatted)
    except Exception as e:
        # Return an informative error string — callers concatenate this into
        # research_findings rather than crashing the entire graph
        return f"Search failed for '{query}': {e}"


def research_agent(state: dict) -> dict:
    """
    Gather live web evidence for the user's query and score its completeness.

    Runs three targeted Tavily searches (latest news, financials, recent
    developments), concatenates all results, then asks the LLM to rate how
    well those findings answer the original query on a 0–10 scale.

    Args:
        state (dict): LangGraph state containing 'query', 'messages', and 'attempts'.

    Returns:
        dict: Partial state update containing:
            messages          – [AIMessage] summarising the research pass
            research_findings – concatenated raw search results (all three queries)
            confidence_score  – integer 0–10 rating of finding completeness
            attempts          – incremented retry counter (graph caps this at 3)
    """

    # ── 1. Resolve the query from state ─────────────────────────────────────
    query = state.get("query", "")
    if not query:
        # Fallback: walk messages in reverse and use the first non-empty content
        for msg in reversed(state.get("messages", [])):
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if content:
                query = content
                break

    # First 6 words act as a compact company/entity label for building
    # focused search strings without repeating the full verbose query
    company_snippet = " ".join(query.split()[:6])

    # ── 2. Run 3 targeted Tavily searches ───────────────────────────────────
    # Three complementary angles — news, financials, general developments —
    # maximise the chance of capturing all relevant facts in one pass
    search_queries = [
        f"{company_snippet} latest news",
        f"{company_snippet} financials 2024",
        f"{company_snippet} recent developments",
    ]

    all_findings = []
    for sq in search_queries:
        result_text = _run_search(sq)
        # Label each block so the LLM knows which query produced which results
        all_findings.append(f"=== Search: {sq} ===\n{result_text}")

    # Merge into a single text block passed through the rest of the pipeline
    research_findings = "\n\n".join(all_findings)

    # ── 3. Ask the LLM to score confidence (0–10) ───────────────────────────
    # Truncate to 4 000 chars to stay comfortably within Gemini's context window
    confidence_prompt = (
        "You are a research quality assessor. "
        "Given the user's original query and the raw search findings below, "
        "rate how complete and relevant the data is on a scale from 0 to 10. "
        "10 means the findings fully answer the query; 0 means completely irrelevant.\n"
        "Respond ONLY with valid JSON — no markdown, no extra text:\n"
        '{"confidence_score": <integer 0-10>, "reasoning": "<brief explanation>"}\n\n'
        f"User query: {query}\n\n"
        f"Research findings:\n{research_findings[:4000]}"
    )

    raw_conf = ""
    reasoning = ""
    try:
        for attempt in range(5):     # Retry up to 5 times on rate-limit errors
            try:
                conf_response = llm.invoke([HumanMessage(content=confidence_prompt)])
                raw_conf = _extract_text(conf_response.content).strip()
                break                # Success — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    # Exponential backoff capped at 8 s (stays within Vercel's 10 s limit)
                    wait = min(2 ** (attempt + 1), 8)
                    time.sleep(wait)
                else:
                    raise inner_e
    except Exception as e:
        reasoning = f"LLM confidence scoring failed: {e}"

    # ── 4. Parse the confidence JSON safely ─────────────────────────────────
    try:
        # Strip any markdown code fences the model added despite instructions
        if raw_conf.startswith("```"):
            raw_conf = raw_conf.split("```")[1]
            if raw_conf.startswith("json"):
                raw_conf = raw_conf[4:]

        conf_parsed     = json.loads(raw_conf)
        confidence_score = int(conf_parsed.get("confidence_score", 5))
        reasoning        = conf_parsed.get("reasoning", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        # Default to 5 (mid-range) so the graph can continue rather than stall
        confidence_score = 5
        reasoning = "Could not parse confidence score; defaulting to 5."

    # Clamp to [0, 10] in case the model returns an out-of-range integer
    confidence_score = max(0, min(10, confidence_score))

    # ── 5. Increment the retry counter ──────────────────────────────────────
    # The conditional edge in graph.py uses this to enforce a 3-attempt cap
    attempts = state.get("attempts", 0) + 1

    # ── 6. Build an AI message summarising the research outcome ─────────────
    summary_message = AIMessage(
        content=(
            f"Research complete (attempt {attempts}).\n"
            f"Confidence score: {confidence_score}/10 — {reasoning}\n\n"
            f"Findings summary (first 500 chars):\n{research_findings[:500]}..."
        )
    )

    # ── 7. Return updated state ──────────────────────────────────────────────
    return {
        "messages": [summary_message],
        "research_findings": research_findings,
        "confidence_score": confidence_score,
        "attempts": attempts,
    }
