# Aetheris Deep Research - Development Log

This log documents the architecture, component design, and integration decisions made during the building of Aetheris Deep Research.

## 1. LangGraph State Machine

The core of the research agent is built using LangGraph's `StateGraph`. The graph orchestrates control flow between four specialized agent nodes (`Clarity`, `Research`, `Validator`, `Synthesis`) and a `Human Feedback` node, with conditional edges routing state dynamically based on metrics.

## 2. Clarity Agent Node

The Clarity Agent evaluates whether the user's research query contains a specific target company and an explicit goal. If vague, it sets the state to `needs_clarification` and triggers a Human-in-the-Loop interrupt.

## 3. Research Agent Node

The Research Agent uses Tavily Search API. It generates three independent search queries, gathers the web results, consolidates findings, and computes a 0-10 confidence score regarding information completeness.

## 4. Validator Agent Node

When search confidence is low (< 6), the Validator Agent reviews findings against the user's goal. It either marks them as `sufficient` or flags missing details as `insufficient`, looping back to research up to 3 times.

## 5. Synthesis Agent Node

The Synthesis Agent compiles the collected research findings and drafts the final markdown report. It structures findings with headings, bullet points, and source citations.

## 6. Graph State Definition (`state.py`)

The global graph state is defined as a `TypedDict` in `state.py`. It tracks the raw query, messages array, research findings, attempt counts, confidence scores, and clarity/validation statuses.

## 7. Human-in-the-Loop (HITL) Interrupts

We leverage LangGraph's `interrupt()` in `graph.py` to halt the state graph mid-execution when a query is unclear, persisting state parameters to the checkpoint database and waiting for user input.

## 8. MemorySaver Migration

Migrated from SQLite checkpointer to LangGraph's in-memory `MemorySaver`. This prevents write failures in serverless environments like Vercel where the filesystem is read-only.

## 9. FastAPI API Server (`api/index.py`)

Serves `/api/health` and `/api/chat`. The chat endpoint uses LangGraph's `astream()` to yield progress updates in real-time, ending with a JSON object containing the final results.

## 10. Server-Sent Events (SSE) Streaming

The API streams node updates to the frontend client using event-stream format (`text/event-stream`). This lets the UI highlight which agent is currently running.

## 11. HTML/JS/CSS Frontend Client

The frontend client lives in the root directory. It is built as a single-page application utilizing pure vanilla JS and CSS, styled with an earth/parchment theme and sleek glassmorphism panels.

## 12. Robust JSON Line Stream Parsing

Fixed syntax parsing in `script.js` to handle malformed SSE lines robustly by catching syntax errors during parsing and continuing rather than crashing the client UI.

## 13. Tavily Search API Integration

Tavily Search is configured via `TavilySearchResults` to return clean snippets and URLs. We cap results at 5 per query to remain within token context boundaries.

## 14. OpenRouter LLM Gateway

All agent nodes utilize `ChatOpenAI` pointed to the OpenRouter gateway. It defaults to `openai/gpt-oss-120b:free` but allows customized overrides via environment variables.

## 15. Exponential Backoff and Error Resilience

API rate limits are mitigated in agent nodes using exponential/static backoffs. If a 429 rate limit is encountered, the agent pauses before retrying the invocation.

## 16. Vercel Serverless Function Config (`vercel.json`)

`vercel.json` maps `/api/(.*)` to the python entry point `api/index.py`. It specifies a `maxDuration` of 60 seconds and excludes unnecessary media folders from the build.

## 17. Static Asset Serving on Vercel CDN

FastAPI mounts the root directory for local static file serving only when NOT on Vercel. In production, Vercel serves the root static assets directly via its edge CDN.

## 18. Multi-Turn Session Memory

The graph state checkpointer associates conversational history with a unique `thread_id` UUID, enabling users to carry out multi-turn follow-up research.

## 19. Local Running Instructions

Local development requires running `uvicorn api.index:app --host 127.0.0.1 --port 8000` with variables configured in `.env`. The UI can be opened at `http://127.0.0.1:8000`.

## 20. Future Scaling and Optimizations

Future scalability improvements include implementing Redis/PostgreSQL checkpoints for persistent multi-node scaling and caching web results to reduce API overhead.
