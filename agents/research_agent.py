import os
import json
import time

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables from the project-root .env file
load_dotenv(override=True)

# Pull the OpenRouter API key
api_key = os.getenv("OPENROUTER_API_KEY")

# OpenRouter Model
model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")

# OpenRouter Base URL (overrideable for custom gateways like Unify AI)
base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    max_retries=2,       # Built-in LangChain retry for transient failures
    temperature=0.7,
    timeout=8.0,
)

# Tavily search config (we query the API directly via HTTP post with a strict timeout)
TAVILY_API_URL = "https://api.tavily.com/search"


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
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Search failed: TAVILY_API_KEY is not set."
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": 5
        }
        res = requests.post(TAVILY_API_URL, json=payload, timeout=3.0)
        res.raise_for_status()
        results = res.json().get("results", [])
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


def _generate_queries(query: str, feedback: str = None) -> list[str]:
    """
    Generate exactly 3 highly relevant and specific search queries using the LLM.
    Uses feedback if executing on a retry pass. Falls back to static queries on error.
    """
    if feedback:
        prompt = (
            "You are an expert search query generator.\n"
            "The previous research findings were marked as insufficient.\n"
            f"Original user query: {query}\n"
            f"Validator feedback explaining what is missing: {feedback}\n\n"
            "Generate exactly 3 highly specific search queries to retrieve the missing information.\n"
            "Respond ONLY with valid JSON — no markdown, no extra text — in this exact format:\n"
            '{"queries": ["query 1", "query 2", "query 3"]}'
        )
    else:
        prompt = (
            "You are an expert search query generator.\n"
            f"User query: {query}\n\n"
            "Generate exactly 3 highly relevant and specific search queries to retrieve information from the web that will help answer the user's query.\n"
            "Respond ONLY with valid JSON — no markdown, no extra text — in this exact format:\n"
            '{"queries": ["query 1", "query 2", "query 3"]}'
        )

    try:
        for attempt in range(3):
            try:
                res = llm.invoke([HumanMessage(content=prompt)])
                raw_res = _extract_text(res.content).strip()
                if raw_res.startswith("```"):
                    raw_res = raw_res.split("```")[1]
                    if raw_res.startswith("json"):
                        raw_res = raw_res[4:]
                parsed_res = json.loads(raw_res)
                generated_queries = parsed_res.get("queries", [])
                if len(generated_queries) == 3:
                    return generated_queries
            except Exception:
                pass
    except Exception:
        pass

    # Fallback to static queries
    company_snippet = " ".join(query.split()[:6])
    return [
        f"{company_snippet} latest news",
        f"{company_snippet} key details timeline",
        f"{company_snippet} recent developments",
    ]


def research_agent(state: dict) -> dict:
    """
    Gather live web evidence for the user's query and score its completeness.

    Runs three targeted Tavily searches (generated dynamically), concatenates all
    results, then asks the LLM to rate how well those findings answer the original
    query on a 0–10 scale.

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

    attempts = state.get("attempts", 0)

    # Dynamic search query generation based on feedback if we are in a retry loop
    feedback = ""
    if attempts > 0:
        for msg in reversed(state.get("messages", [])):
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if "Validation result:" in content:
                feedback = content
                break

    from concurrent.futures import ThreadPoolExecutor

    search_queries = _generate_queries(query, feedback if attempts > 0 else None)

    with ThreadPoolExecutor(max_workers=3) as executor:
        search_results = list(executor.map(_run_search, search_queries))

    all_findings = [
        f"=== Search: {sq} ===\n{res}"
        for sq, res in zip(search_queries, search_results)
    ]

    current_findings = "\n\n".join(all_findings)

    # Accumulate findings across attempts so we don't lose previous search details
    previous_findings = state.get("research_findings", "")
    if previous_findings:
        research_findings = previous_findings + f"\n\n=== Retry Pass {attempts + 1} ===\n\n" + current_findings
    else:
        research_findings = current_findings

    # ── 3. Ask the LLM to score confidence (0–10) ───────────────────────────
    # Truncate to 25 000 chars to fit within context limits
    confidence_prompt = (
        "You are a research quality assessor. "
        "Given the user's original query and the raw search findings below, "
        "rate how complete and relevant the data is on a scale from 0 to 10. "
        "10 means the findings fully answer the query; 0 means completely irrelevant.\n"
        "Respond ONLY with valid JSON — no markdown, no extra text:\n"
        '{"confidence_score": <integer 0-10>, "reasoning": "<brief explanation>"}\n\n'
        f"User query: {query}\n\n"
        f"Research findings:\n{research_findings[:25000]}"
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
