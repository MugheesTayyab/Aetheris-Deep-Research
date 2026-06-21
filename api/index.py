import os
import sys
import uuid
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add parent directory to sys.path so we can import state, graph, and agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(override=True)

# ── Startup validation ────────────────────────────────────────────────────────
# Fail with a clear message if the required secrets are not in the environment.
# On Vercel these MUST be set in Project Settings → Environment Variables.
_STARTUP_ERROR: Optional[str] = None

_required = {
    "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
}
_missing = [k for k, v in _required.items() if not v]
if _missing:
    _STARTUP_ERROR = (
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Set them in your Vercel Project Settings → Environment Variables."
    )

# ── Import the research graph ─────────────────────────────────────────────────
if not _STARTUP_ERROR:
    try:
        from langchain_core.messages import HumanMessage
        from langgraph.types import Command
        from graph import app as research_graph
    except Exception as _import_err:
        _STARTUP_ERROR = f"Failed to load research graph: {_import_err}"
else:
    research_graph = None  # type: ignore
    HumanMessage = None    # type: ignore
    Command = None         # type: ignore

app = FastAPI(title="Aetheris API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler — always returns JSON, never a plain-text 500 ────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    clarification_answer: Optional[str] = None
    original_query: Optional[str] = None

class AgentStatus(BaseModel):
    name: str
    icon: str
    sub: str
    status: str

class ChatResponse(BaseModel):
    thread_id: str
    is_clarifying: bool
    clarification_question: str
    final_response: str
    confidence_score: int
    validation_result: str
    attempts: int
    completion: int
    agents: List[AgentStatus]

def _completion_percentage(vals: dict) -> int:
    pts = 0
    if vals.get("clarity_status"):       pts += 20
    if vals.get("confidence_score", 0):  pts += 30
    if vals.get("validation_result"):    pts += 20
    if vals.get("final_response"):       pts += 30
    return min(pts, 100)

def _get_agent_list(vals: dict) -> list:
    clarity = vals.get("clarity_status", "")
    conf    = vals.get("confidence_score", 0)
    vr      = vals.get("validation_result", "")
    fr      = vals.get("final_response", "")
    return [
        {
            "icon": "Q", "name": "Query Analyzer",
            "sub":  "Clear" if clarity == "clear" else ("Needs clarification" if clarity else "Awaiting query"),
            "status": "complete" if clarity else "idle",
        },
        {
            "icon": "L", "name": "Literature Scraper",
            "sub":  f"Confidence {conf}/10" if conf else "Awaiting query",
            "status": "complete" if conf else "idle",
        },
        {
            "icon": "F", "name": "Fact-Check Validator",
            "sub":  vr.title() if vr else "Awaiting data",
            "status": "complete" if vr else "idle",
        },
        {
            "icon": "D", "name": "Drafting Engine",
            "sub":  "Report ready" if fr else "Idle · Awaiting data",
            "status": "complete" if fr else "idle",
        },
    ]

@app.get("/api/health")
def health_check():
    if _STARTUP_ERROR:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": _STARTUP_ERROR})
    return {"status": "healthy", "service": "Aetheris Deep Research Backend"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # Surface startup errors immediately with a clear message
    if _STARTUP_ERROR:
        raise HTTPException(status_code=503, detail=_STARTUP_ERROR)

    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Decide whether we are resuming via stateless query combination or running a fresh query
        if request.clarification_answer and request.original_query:
            combined = f"Original query: {request.original_query}\nClarification: {request.clarification_answer}"
            initial_input = {
                "query": combined,
                "messages": [HumanMessage(content=combined)],
                "attempts": 0,
            }
            event_stream = research_graph.astream(initial_input, config=config, stream_mode="updates")
        else:
            initial_input = {
                "query": request.query,
                "messages": [HumanMessage(content=request.query)],
                "attempts": 0,
            }
            event_stream = research_graph.astream(initial_input, config=config, stream_mode="updates")

        import asyncio
        import json
        from fastapi.responses import StreamingResponse

        async def event_generator():
            try:
                # Iterate through the stream asynchronously from LangGraph
                async for update in event_stream:
                    # Extract the node name
                    node_name = list(update.keys())[0]
                    # Yield an event telling the UI which node is running
                    yield f"data: {json.dumps({'event': 'update', 'node': node_name})}\n\n"
                    await asyncio.sleep(0.05)

                # Retrieve updated state asynchronously
                updated_snapshot = await research_graph.aget_state(config)
                state_values = updated_snapshot.values or {}

                # Check if graph paused for clarification
                is_clarifying = bool(updated_snapshot.next and "human_feedback" in updated_snapshot.next)
                clarification_question = ""
                if is_clarifying:
                    if updated_snapshot.tasks and updated_snapshot.tasks[0].interrupts:
                        clarification_question = str(updated_snapshot.tasks[0].interrupts[0].value)
                    else:
                        clarification_question = state_values.get("clarification_question", "Please clarify your request:")

                final_response = state_values.get("final_response", "")
                confidence_score = state_values.get("confidence_score", 0)
                validation_result = state_values.get("validation_result", "")
                attempts = state_values.get("attempts", 0)
                completion = _completion_percentage(state_values)
                agents = _get_agent_list(state_values)

                final_data = {
                    "event": "final",
                    "thread_id": thread_id,
                    "is_clarifying": is_clarifying,
                    "clarification_question": clarification_question,
                    "final_response": final_response,
                    "confidence_score": confidence_score,
                    "validation_result": validation_result,
                    "attempts": attempts,
                    "completion": completion,
                    "agents": agents,
                    "research_findings": state_values.get("research_findings", "")
                }
                yield f"data: {json.dumps(final_data)}\n\n"
            except Exception as inner_e:
                yield f"data: {json.dumps({'event': 'error', 'detail': str(inner_e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {type(e).__name__}: {e}")

# Serve static files from the project root directory for local execution
from fastapi.staticfiles import StaticFiles
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/", StaticFiles(directory=root_dir, html=True), name="static")
