import os
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables from the project-root .env file
load_dotenv()

# Pull the Google API key for Gemini authentication
api_key = os.getenv("GOOGLE_API_KEY")

# Gemini 2.5 Flash handles long-form report generation well within context limits
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=api_key,
    max_retries=2,
    temperature=0.7,
)


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
                final_response = response.content.strip()
                break                 # Clean response — exit retry loop
            except Exception as inner_e:
                if "429" in str(inner_e) and attempt < 4:
                    time.sleep(25)    # Wait for the Gemini rate-limit window to reset
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
