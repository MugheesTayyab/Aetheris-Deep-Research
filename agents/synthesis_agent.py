import os
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


def synthesis_agent(state: dict) -> dict:
    """
    Generate a polished, structured research report from validated findings.

    Combines the original query, full conversation history, and gathered
    research findings into a single LLM prompt that produces a professional
    business report: executive summary, labelled sections, bullet points,
    and key takeaways.

    Args:
        state (dict): LangGraph state containing:
            query             – the original user question
            research_findings – concatenated Tavily search results
            messages          – full conversation history (BaseMessage list)

    Returns:
        dict: Partial state update containing:
            messages       – [AIMessage] with the complete report
            final_response – the report text as a plain string (used by the UI)
    """

    # ── 1. Read the original query and gathered research ────────────────────
    query             = state.get("query", "")
    research_findings = state.get("research_findings", "")

    # ── 2. Build a readable conversation history string ──────────────────────
    # Including the full history lets the LLM avoid re-stating points already
    # covered during clarification and acknowledge any mid-session pivots
    history_lines = []
    for msg in state.get("messages", []):
        if hasattr(msg, "content"):
            # Derive a human-readable label from the LangChain class name
            # e.g. HumanMessage → "Human", AIMessage → "AI"
            role = msg.__class__.__name__.replace("Message", "")
            history_lines.append(f"{role}: {msg.content}")
        elif isinstance(msg, dict):
            # Handle plain-dict messages that may exist in certain graph paths
            role = msg.get("role", "Unknown")
            history_lines.append(f"{role}: {msg.get('content', '')}")

    conversation_history = "\n".join(history_lines)

    # ── 3. Build the synthesis prompt ────────────────────────────────────────
    system_prompt = (
        "You are a professional business research assistant. "
        "Using the research findings and conversation history provided, "
        "write a clear, structured, and comprehensive answer to the user's query. "
        "Format your answer with:\n"
        "  - A short executive summary at the top\n"
        "  - Clearly labelled sections with headers (##)\n"
        "  - Bullet points for key facts and data\n"
        "  - A brief conclusion or key takeaways at the end\n"
        "Be professional, factual, and concise. Do not fabricate information."
    )

    # Truncate research_findings to 6 000 chars to stay within context limits
    synthesis_prompt = (
        f"User query: {query}\n\n"
        f"Conversation history:\n{conversation_history}\n\n"
        f"Research findings:\n{research_findings[:6000]}"
    )

    # ── 4. Call the LLM to generate the final report ─────────────────────────
    try:
        for attempt in range(5):      # Retry up to 5 times on rate-limit errors
            try:
                response = llm.invoke([
                    HumanMessage(content=f"{system_prompt}\n\n{synthesis_prompt}")
                ])
                final_response = _extract_text(response.content).strip()
                break                 # Clean response — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    # Exponential backoff capped at 8 s (stays within Vercel's 10 s limit)
                    wait = min(2 ** (attempt + 1), 8)
                    time.sleep(wait)
                else:
                    raise inner_e
    except Exception as e:
        # Surface the error as the final_response so the user is informed via UI
        final_response = (
            f"Synthesis failed due to an error: {e}\n\n"
            "Please try again or rephrase your query."
        )

    # ── 5. Wrap the answer in an AIMessage so the conversation history is complete
    final_message = AIMessage(content=final_response)

    # ── 6. Return updated state with the completed report ────────────────────
    return {
        "messages": [final_message],
        "final_response": final_response,
    }
