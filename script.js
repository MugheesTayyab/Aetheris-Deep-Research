// ═══════════════════════════════════════════════════════════════
// STATE MANAGEMENT & CONFIGURATION
// ═══════════════════════════════════════════════════════════════
const STATE = {
  threadId: null,
  isClarifying: false,
  clarificationQuestion: "",
  displayHistory: [],
  sessionTitle: "Synthesis Workspace",
  activeNode: null // Tracks current active agent node
};

const VIEWS = {
  RESEARCH: "research",
  SYNTHESIS: "synthesis",
  PIPELINE: "pipeline",
  KNOWLEDGE: "knowledge",
  ARCHIVE: "archive"
};

// ═══════════════════════════════════════════════════════════════
// DOM ELEMENTS
// ═══════════════════════════════════════════════════════════════
const DOM = {
  chatFeed: document.getElementById("chat-feed"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  submitBtn: document.getElementById("submit-btn"),
  emptyState: document.getElementById("empty-state"),
  sessionTitle: document.getElementById("session-title"),
  activeAgentsBadge: document.getElementById("active-agents-badge"),
  newSynthesisBtn: document.getElementById("new-synthesis-btn"),
  haltSynthesisBtn: document.getElementById("halt-synthesis-btn"),
  loadingOverlay: document.getElementById("loading-overlay"),

  // Metrics
  completionText: document.getElementById("completion-text"),
  completionBar: document.getElementById("completion-bar"),
  confidenceSection: document.getElementById("confidence-section"),
  confidenceText: document.getElementById("confidence-text"),
  confidenceBar: document.getElementById("confidence-bar"),
  agentsList: document.getElementById("agents-list"),
  validationPill: document.getElementById("validation-pill")
};

// ═══════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════
function init() {
  // Restore or generate unique thread_id
  STATE.threadId = sessionStorage.getItem("aetheris_thread_id") || generateUUID();
  sessionStorage.setItem("aetheris_thread_id", STATE.threadId);

  // Restore history if any
  const cachedHistory = sessionStorage.getItem("aetheris_history");
  if (cachedHistory) {
    try {
      STATE.displayHistory = JSON.parse(cachedHistory);
      STATE.isClarifying = sessionStorage.getItem("aetheris_is_clarifying") === "true";
      STATE.clarificationQuestion = sessionStorage.getItem("aetheris_clarification_question") || "";
      STATE.sessionTitle = sessionStorage.getItem("aetheris_session_title") || "Synthesis Workspace";

      // Restore metrics state
      const cachedMetrics = sessionStorage.getItem("aetheris_metrics");
      if (cachedMetrics) {
        updateMetricsUI(JSON.parse(cachedMetrics));
      }
    } catch (e) {
      clearSession();
    }
  }

  renderFeed();
  setupEventListeners();
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// ═══════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════
function setupEventListeners() {
  DOM.chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSubmit();
  });

  // Expand text input dynamically
  DOM.chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight - 16) + "px";
  });

  // Form submission on Enter (without Shift)
  DOM.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      DOM.chatForm.dispatchEvent(new Event("submit"));
    }
  });

  DOM.newSynthesisBtn.addEventListener("click", clearSession);
  DOM.haltSynthesisBtn.addEventListener("click", clearSession);

  // Nav Tab Click Handlers
  document.getElementById("nav-research").addEventListener("click", (e) => { e.preventDefault(); switchView(VIEWS.RESEARCH); });
  document.getElementById("nav-synthesis").addEventListener("click", (e) => { e.preventDefault(); switchView(VIEWS.SYNTHESIS); });
  document.getElementById("nav-pipeline").addEventListener("click", (e) => { e.preventDefault(); switchView(VIEWS.PIPELINE); });
  document.getElementById("nav-knowledge").addEventListener("click", (e) => { e.preventDefault(); switchView(VIEWS.KNOWLEDGE); });
  document.getElementById("nav-archive").addEventListener("click", (e) => { e.preventDefault(); switchView(VIEWS.ARCHIVE); });

  // Search input change handler
  document.getElementById("knowledge-search").addEventListener("input", filterKnowledgeTable);
}

const AGENT_EXPLANATIONS = {
  "clarity_agent": {
    name: "Query Analyzer",
    desc: "Evaluating company name and research goal..."
  },
  "research_agent": {
    name: "Literature Scraper",
    desc: "Executing parallel Tavily searches and gathering web documentation..."
  },
  "validator_agent": {
    name: "Fact-Check Validator",
    desc: "Auditing findings factuality and completeness against query..."
  },
  "synthesis_agent": {
    name: "Drafting Engine",
    desc: "Compiling final structured, publication-ready report..."
  }
};

function updateLoadingStatus(node) {
  STATE.activeNode = node;
  renderFeed();

  const explanation = AGENT_EXPLANATIONS[node];
  if (explanation) {
    const loadingTextEl = document.getElementById("loading-text");
    if (loadingTextEl) {
      loadingTextEl.textContent = `[${explanation.name}] - ${explanation.desc}`;
    }

    const agentItems = DOM.agentsList.querySelectorAll(".agent-item");
    agentItems.forEach(item => {
      const nameEl = item.querySelector(".agent-name");
      const statusEl = item.querySelector(".agent-status");
      const avatarEl = item.querySelector(".agent-avatar");

      if (nameEl && nameEl.textContent === explanation.name) {
        avatarEl.className = "agent-avatar status-busy";
        statusEl.textContent = explanation.desc;
      } else {
        if (avatarEl && avatarEl.classList.contains("status-busy")) {
          avatarEl.className = "agent-avatar status-complete";
          statusEl.textContent = "Complete";
        }
      }
    });
  }
}

function handleFinalData(data, originalQuery) {
  STATE.activeNode = null;
  STATE.isClarifying = !!data.is_clarifying;
  STATE.clarificationQuestion = data.clarification_question || "";
  sessionStorage.setItem("aetheris_is_clarifying", String(STATE.isClarifying));
  sessionStorage.setItem("aetheris_clarification_question", STATE.clarificationQuestion);

  if (STATE.isClarifying) {
    STATE.displayHistory.push({
      role: "clarification",
      content: STATE.clarificationQuestion
    });
    DOM.chatInput.placeholder = "Provide clarification to continue research...";
  } else if (data.final_response) {
    const tags = extractTags(originalQuery);
    STATE.displayHistory.push({
      role: "assistant",
      title: "Literature Review Summary",
      content: data.final_response,
      confidence: data.confidence_score || 0,
      tags: tags
    });
    if (data.research_findings) {
      sessionStorage.setItem("aetheris_findings", data.research_findings);
    }
    saveToArchive(data, originalQuery);
    DOM.chatInput.placeholder = "Instruct agents to pivot research focus or synthesize specific findings...";
  } else {
    STATE.displayHistory.push({
      role: "assistant",
      title: "System Notice",
      content: "Research complete, but no final response was drafted. Please refine your query."
    });
    DOM.chatInput.placeholder = "Instruct agents to pivot research focus or synthesize specific findings...";
  }

  renderFeed();
  updateMetricsUI(data);
  saveSessionState();
  sessionStorage.setItem("aetheris_metrics", JSON.stringify(data));
}

async function handleSubmit() {
  if (STATE.activeNode) return; // Prevent duplicate submissions during active synthesis

  const query = DOM.chatInput.value.trim();
  if (!query) return;

  // Clear input
  DOM.chatInput.value = "";
  DOM.chatInput.style.height = "auto";

  // Cache title if first message
  if (STATE.displayHistory.length === 0) {
    STATE.sessionTitle = query.length > 50 ? query.substring(0, 48) + "…" : query;
    DOM.sessionTitle.textContent = STATE.sessionTitle;
    sessionStorage.setItem("aetheris_session_title", STATE.sessionTitle);
  }

  // Add user bubble
  STATE.displayHistory.push({ role: "user", content: query });

  // Set active node to initialize real-time visual feedback
  STATE.activeNode = "clarity_agent";

  // Disable user input to maintain pipeline integrity
  DOM.chatInput.disabled = true;
  DOM.submitBtn.disabled = true;

  renderFeed();
  saveSessionState();

  // Reset loading text
  const loadingTextEl = document.getElementById("loading-text");
  if (loadingTextEl) {
    loadingTextEl.textContent = "Orchestrating agent workflows...";
  }

  // Keep full-screen overlay hidden for a clean, non-blocking visual flow

  try {
    const payload = {
      query: query,
      thread_id: STATE.threadId
    };

    if (STATE.isClarifying) {
      payload.clarification_answer = query;
      // Extract the first user message as the original query
      const originalUserMsg = STATE.displayHistory.find(m => m.role === "user");
      if (originalUserMsg) {
        payload.original_query = originalUserMsg.content;
      }
    }


    let response;
    try {
      response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
    } catch (netErr) {
      throw new Error(
        "Cannot reach the Aetheris API server. Ensure the FastAPI backend is running (e.g., 'uvicorn api.index:app') and the SPA is served from the same origin."
      );
    }

    if (!response.ok) {
      let errorMsg = `HTTP ${response.status}`;
      try {
        const errBody = await response.json();
        errorMsg = errBody.detail || errBody.error || errBody.message || errorMsg;
      } catch (_) {
        errorMsg = response.statusText || errorMsg;
      }
      throw new Error(errorMsg);
    }

    if (!response.body) {
      throw new Error("Response body is empty. The API may not support streaming.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }

      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop();

      for (const line of lines) {
        const cleaned = line.trim();
        if (!cleaned) continue;

        if (cleaned.startsWith("data: ")) {
          const rawData = cleaned.substring(6);
          try {
            const data = JSON.parse(rawData);
            if (data.event === "update") {
              updateLoadingStatus(data.node);
            } else if (data.event === "final") {
              handleFinalData(data, payload.query);
            } else if (data.event === "error") {
              throw new Error(data.detail || "Unknown pipeline error");
            }
          } catch (e) {
            if (e.message && e.message !== "Unknown pipeline error") {
              console.error("Failed to parse JSON line:", cleaned, e);
            } else {
              throw e;
            }
          }
        }
      }

      if (done) {
        if (buffer && buffer.trim().startsWith("data: ")) {
          const cleaned = buffer.trim();
          const rawData = cleaned.substring(6);
          try {
            const data = JSON.parse(rawData);
            if (data.event === "update") {
              updateLoadingStatus(data.node);
            } else if (data.event === "final") {
              handleFinalData(data, payload.query);
            } else if (data.event === "error") {
              throw new Error(data.detail);
            }
          } catch (e) {
            if (!(e instanceof SyntaxError)) throw e;
            console.error("Failed to parse remaining buffer:", e);
          }
        }
        break;
      }
    }

  } catch (err) {
    console.error(err);
    STATE.displayHistory.push({
      role: "assistant",
      title: "System Error",
      content: `Failed to communicate with research graph: ${err.message}`
    });
  } finally {
    STATE.activeNode = null;
    DOM.chatInput.disabled = false;
    DOM.submitBtn.disabled = false;
    renderFeed();
  }
}

function clearSession() {
  sessionStorage.removeItem("aetheris_thread_id");
  sessionStorage.removeItem("aetheris_history");
  sessionStorage.removeItem("aetheris_is_clarifying");
  sessionStorage.removeItem("aetheris_clarification_question");
  sessionStorage.removeItem("aetheris_session_title");
  sessionStorage.removeItem("aetheris_metrics");
  sessionStorage.removeItem("aetheris_findings");

  STATE.threadId = generateUUID();
  sessionStorage.setItem("aetheris_thread_id", STATE.threadId);
  STATE.isClarifying = false;
  STATE.clarificationQuestion = "";
  STATE.displayHistory = [];
  STATE.sessionTitle = "Synthesis Workspace";

  DOM.sessionTitle.textContent = STATE.sessionTitle;
  DOM.chatInput.placeholder = "Instruct agents to pivot research focus or synthesize specific findings...";
  DOM.activeAgentsBadge.innerHTML = "";

  // Reset metrics
  DOM.completionText.textContent = "0%";
  DOM.completionBar.style.width = "0%";
  DOM.confidenceSection.classList.add("hidden");
  DOM.validationPill.classList.add("hidden");

  DOM.agentsList.innerHTML = `
    <div class="agent-item">
      <div class="agent-avatar status-idle">Q</div>
      <div>
        <div class="agent-name">Query Analyzer</div>
        <div class="agent-status">Awaiting query</div>
      </div>
    </div>
    <div class="agent-item">
      <div class="agent-avatar status-idle">L</div>
      <div>
        <div class="agent-name">Literature Scraper</div>
        <div class="agent-status">Awaiting query</div>
      </div>
    </div>
    <div class="agent-item">
      <div class="agent-avatar status-idle">F</div>
      <div>
        <div class="agent-name">Fact-Check Validator</div>
        <div class="agent-status">Awaiting data</div>
      </div>
    </div>
    <div class="agent-item">
      <div class="agent-avatar status-idle">D</div>
      <div>
        <div class="agent-name">Drafting Engine</div>
        <div class="agent-status">Idle · Awaiting data</div>
      </div>
    </div>
  `;

  renderFeed();
  switchView(VIEWS.RESEARCH);
}

// ═══════════════════════════════════════════════════════════════
// RENDERING FUNCTIONS
// ═══════════════════════════════════════════════════════════════
function renderFeed() {
  if (STATE.displayHistory.length === 0) {
    DOM.emptyState.classList.remove("hidden");
    DOM.chatFeed.querySelectorAll(".chat-bubble-user, .report-card, .clarify-banner").forEach(el => el.remove());
    return;
  }

  DOM.emptyState.classList.add("hidden");

  // Keep track of existing DOM elements to avoid redrawing everything
  const existingElements = DOM.chatFeed.querySelectorAll(".chat-bubble-user, .report-card, .clarify-banner, .agent-status-bubble");
  existingElements.forEach(el => el.remove());

  STATE.displayHistory.forEach((msg) => {
    let el;
    if (msg.role === "user") {
      el = document.createElement("div");
      el.className = "chat-bubble-user";
      el.textContent = msg.content;
    } else if (msg.role === "clarification") {
      el = document.createElement("div");
      el.className = "clarify-banner";
      el.innerHTML = `
        <div class="clarify-icon">🤔</div>
        <div>
          <div class="clarify-title">Clarification Needed</div>
          <div class="clarify-question">${escapeHtml(msg.content)}</div>
        </div>
      `;
      // Update placeholder
      DOM.chatInput.placeholder = "Provide clarification to continue research...";
    } else {
      // Assistant Report Card
      el = document.createElement("div");
      el.className = "report-card";

      // Confidence badge
      let badgeHtml = "";
      if (msg.confidence !== undefined && msg.confidence > 0) {
        if (msg.confidence >= 7) {
          badgeHtml = `<span class="confidence-badge-hi">✅ High Confidence (${msg.confidence}/10)</span>`;
        } else if (msg.confidence >= 4) {
          badgeHtml = `<span class="confidence-badge-md">⚠️ Medium Confidence (${msg.confidence}/10)</span>`;
        }
      }

      // Tags block
      let tagsHtml = "";
      if (msg.tags && msg.tags.length > 0) {
        tagsHtml = `<div class="report-tags">` +
          msg.tags.map(t => `<span class="report-tag">${escapeHtml(t)}</span>`).join("") +
          `</div>`;
      }

      // Simple Markdown-to-HTML formatter for headers and lists
      const formattedContent = formatReportMarkdown(msg.content);

      el.innerHTML = `
        <div class="report-header">
          <div class="report-title-container">
            <div class="report-icon">📋</div>
            <span class="report-title">${escapeHtml(msg.title || "Synthesis Report")}</span>
          </div>
          ${badgeHtml}
        </div>
        <div class="report-body">${formattedContent}</div>
        ${tagsHtml}
      `;

      // Reset input placeholder
      DOM.chatInput.placeholder = "Instruct agents to pivot research focus or synthesize specific findings...";
    }

    DOM.chatFeed.appendChild(el);
  });

  // Inject a real-time agent status card at the bottom of the feed if an agent is currently active
  if (STATE.activeNode) {
    const explanation = AGENT_EXPLANATIONS[STATE.activeNode];
    if (explanation) {
      const statusEl = document.createElement("div");
      statusEl.className = "agent-status-bubble";
      statusEl.innerHTML = `
        <div class="status-avatar status-busy-pulse">${escapeHtml(explanation.name.charAt(0))}</div>
        <div class="status-details">
          <div class="status-agent-name">${escapeHtml(explanation.name)} is active...</div>
          <div class="status-desc">${escapeHtml(explanation.desc)}</div>
        </div>
        <div class="status-loading-dots">
          <span></span><span></span><span></span>
        </div>
      `;
      DOM.chatFeed.appendChild(statusEl);
    }
  }

  // Scroll to bottom
  DOM.chatFeed.scrollTop = DOM.chatFeed.scrollHeight;
}

function updateMetricsUI(data) {
  if (!data) return;

  const completion = data.completion || 0;
  DOM.completionText.textContent = `${completion}%`;
  DOM.completionBar.style.width = `${completion}%`;

  const agents = Array.isArray(data.agents) ? data.agents : [];
  const activeCount = agents.filter(a => a && a.status === "complete").length;
  if (activeCount > 0) {
    DOM.activeAgentsBadge.innerHTML = `
      <span class="badge-active">
        <span class="badge-dot"></span>
        ${activeCount} Agent${activeCount > 1 ? 's' : ''} Complete
      </span>
    `;
  } else {
    DOM.activeAgentsBadge.innerHTML = "";
  }

  const confidence = data.confidence_score || 0;
  if (confidence > 0) {
    DOM.confidenceSection.classList.remove("hidden");
    DOM.confidenceText.textContent = `${confidence}/10`;
    DOM.confidenceBar.style.width = `${confidence * 10}%`;
  } else {
    DOM.confidenceSection.classList.add("hidden");
  }

  DOM.agentsList.innerHTML = agents.map(a => {
    if (!a) return "";
    let statusClass = "status-idle";
    if (a.status === "complete") statusClass = "status-complete";
    if (a.status === "busy") statusClass = "status-busy";

    return `
      <div class="agent-item">
        <div class="agent-avatar ${statusClass}">${escapeHtml(a.icon || "?")}</div>
        <div>
          <div class="agent-name">${escapeHtml(a.name || "Unknown")}</div>
          <div class="agent-status">${escapeHtml(a.sub || "")}</div>
        </div>
      </div>
    `;
  }).join("");

  if (data.validation_result) {
    DOM.validationPill.classList.remove("hidden");
    DOM.validationPill.className = `validation-banner ${data.validation_result}`;
    DOM.validationPill.innerHTML = data.validation_result === "sufficient"
      ? `<span>✅ Validation: Sufficient</span>`
      : `<span>⚠️ Validation: Insufficient (Retrying Scraper)</span>`;
  } else {
    DOM.validationPill.classList.add("hidden");
  }
}

// ═══════════════════════════════════════════════════════════════
// CACHING & UTILS
// ═══════════════════════════════════════════════════════════════
function saveSessionState() {
  sessionStorage.setItem("aetheris_history", JSON.stringify(STATE.displayHistory));
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function extractTags(query) {
  const stopWords = new Set(["the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has", "not", "but", "its", "about", "what"]);
  const words = query.split(/\s+/)
    .map(w => w.replace(/[.,!?;:":']/g, "").trim())
    .filter(w => w.length > 4 && !stopWords.has(w.toLowerCase()))
    .map(w => w.charAt(0).toUpperCase() + w.slice(1));

  return [...new Set(words)].slice(0, 4);
}

function formatReportMarkdown(text) {
  if (!text) return "";
  if (typeof marked !== 'undefined') {
    try {
      return marked.parse(text);
    } catch (e) {
      console.warn("Marked parse failed, using fallback:", e);
    }
  }
  let html = escapeHtml(text);
  html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^\s*-\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/^\s*\*\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/^(<li>.*)(\n<li>.*)*/m, function (m) {
    return '<ul>' + m + '</ul>';
  });
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/\n{2,}/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

// ═══════════════════════════════════════════════════════════════
// MULTI-VIEW SPA ROUTING & FEATURE MANAGEMENT
// ═══════════════════════════════════════════════════════════════

function switchView(viewName) {
  // Update nav UI active class
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(el => el.classList.remove("active"));

  // Hide all view content wrappers
  document.querySelector(".main-content").classList.add("hidden");
  document.querySelector(".metrics-panel").classList.add("hidden");
  document.getElementById("synthesis-view").classList.add("hidden");
  document.getElementById("pipeline-view").classList.add("hidden");
  document.getElementById("knowledge-view").classList.add("hidden");
  document.getElementById("archive-view").classList.add("hidden");

  // Show the selected view wrapper
  if (viewName === VIEWS.RESEARCH) {
    document.getElementById("nav-research").classList.add("active");
    document.querySelector(".main-content").classList.remove("hidden");
    document.querySelector(".metrics-panel").classList.remove("hidden");
  } else if (viewName === VIEWS.SYNTHESIS) {
    document.getElementById("nav-synthesis").classList.add("active");
    document.getElementById("synthesis-view").classList.remove("hidden");
    renderSynthesisView();
  } else if (viewName === VIEWS.PIPELINE) {
    document.getElementById("nav-pipeline").classList.add("active");
    document.getElementById("pipeline-view").classList.remove("hidden");
    renderPipelineView();
  } else if (viewName === VIEWS.KNOWLEDGE) {
    document.getElementById("nav-knowledge").classList.add("active");
    document.getElementById("knowledge-view").classList.remove("hidden");
    renderKnowledgeView();
  } else if (viewName === VIEWS.ARCHIVE) {
    document.getElementById("nav-archive").classList.add("active");
    document.getElementById("archive-view").classList.remove("hidden");
    renderArchiveView();
  }
}

// ── 1. Data Synthesis View Rendering & Chart ──────────────────────────
function renderSynthesisView() {
  const cachedMetrics = sessionStorage.getItem("aetheris_metrics");
  const assistantReport = [...STATE.displayHistory].reverse().find(m => m.role === "assistant" && m.title !== "System Error" && m.title !== "System Notice");

  if (!cachedMetrics || !assistantReport) {
    document.getElementById("synthesis-empty").classList.remove("hidden");
    document.getElementById("synthesis-content").classList.add("hidden");
    document.getElementById("synthesis-actions").classList.add("hidden");
    return;
  }

  document.getElementById("synthesis-empty").classList.add("hidden");
  document.getElementById("synthesis-content").classList.remove("hidden");
  document.getElementById("synthesis-actions").classList.remove("hidden");

  const metrics = JSON.parse(cachedMetrics);

  // Fill text fields
  const query = STATE.displayHistory.find(m => m.role === "user")?.content || "General Query";
  document.getElementById("synth-query").textContent = query;
  document.getElementById("synth-confidence").textContent = `${metrics.confidence_score || 0}/10`;
  document.getElementById("synth-attempts").textContent = metrics.attempts || 1;

  // Extract tables from HTML
  const parser = new DOMParser();
  const reportHtml = typeof marked !== 'undefined' ? marked.parse(assistantReport.content) : assistantReport.content;
  const parsedHtml = parser.parseFromString(reportHtml, 'text/html');
  const tables = parsedHtml.querySelectorAll('table');

  const tablesContainer = document.getElementById("extracted-tables-container");
  if (tables.length > 0) {
    let tablesHtml = "";
    tables.forEach((table, idx) => {
      tablesHtml += `<h4 style="font-family:'Outfit', sans-serif; font-size:15px; margin-top:24px; margin-bottom:12px; color:var(--sage-dark);">Table ${idx + 1} - Extracted Data Grid</h4>` + table.outerHTML;
    });
    tablesContainer.innerHTML = tablesHtml;
  } else {
    tablesContainer.innerHTML = `<p class="empty-state-subtitle" style="text-align:center; padding: 40px 0;">No structured table grids were found in the final synthesis report text. Review the full report layout in the Research Hub.</p>`;
  }

  // Draw chart after layout is complete
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      drawSynthesisChart(metrics.completion || 100, metrics.confidence_score || 5);
    });
  });

  // Hook exports (removing any old duplicate listeners)
  const exportMdBtn = document.getElementById("export-md-btn");
  const exportJsonBtn = document.getElementById("export-json-btn");
  const printReportBtn = document.getElementById("print-report-btn");

  exportMdBtn.replaceWith(exportMdBtn.cloneNode(true));
  exportJsonBtn.replaceWith(exportJsonBtn.cloneNode(true));
  printReportBtn.replaceWith(printReportBtn.cloneNode(true));

  document.getElementById("export-md-btn").addEventListener("click", () => {
    downloadTextFile(assistantReport.content, `Aetheris_Deep_Research_${metrics.thread_id.substring(0, 8)}.md`);
  });

  document.getElementById("export-json-btn").addEventListener("click", () => {
    const sessionData = {
      thread_id: metrics.thread_id,
      query: query,
      timestamp: new Date().toISOString(),
      confidence_score: metrics.confidence_score,
      attempts: metrics.attempts,
      final_response: assistantReport.content,
      findings: sessionStorage.getItem("aetheris_findings") || ""
    };
    downloadTextFile(JSON.stringify(sessionData, null, 2), `Aetheris_Deep_Research_${metrics.thread_id.substring(0, 8)}.json`);
  });

  document.getElementById("print-report-btn").addEventListener("click", () => {
    window.print();
  });
}

function roundRect(ctx, x, y, w, h, r) {
  if (typeof ctx.roundRect === 'function') {
    ctx.roundRect(x, y, w, h, r);
  } else {
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
}

function drawSynthesisChart(completion, confidence) {
  const canvas = document.getElementById("synthesis-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  const bars = [
    { label: "Completeness", val: completion, color: "#6B8470" },
    { label: "Confidence", val: confidence * 10, color: "#C09E73" }
  ];

  ctx.font = "11px Inter, sans-serif";
  bars.forEach((bar, idx) => {
    const barY = 24 + idx * 60;

    ctx.fillStyle = "#5E6960";
    ctx.fillText(bar.label, 10, barY + 14);

    ctx.fillStyle = "#EDEAE3";
    ctx.beginPath();
    roundRect(ctx, 95, barY, w - 145, 18, 5);
    ctx.fill();

    ctx.fillStyle = bar.color;
    ctx.beginPath();
    const fillWidth = ((w - 145) * bar.val) / 100;
    roundRect(ctx, 95, barY, fillWidth, 18, 5);
    ctx.fill();

    ctx.fillStyle = "#273029";
    ctx.font = "bold 11px Inter, sans-serif";
    ctx.fillText(`${bar.val}%`, w - 40, barY + 14);
    ctx.font = "11px Inter, sans-serif";
  });
}

function downloadTextFile(text, filename) {
  const element = document.createElement("a");
  element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(text));
  element.setAttribute("download", filename);
  element.style.display = "none";
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

// ── 2. Interactive Pipeline Graph Trace ──────────────────────────────
const NODE_SPECIFICATIONS = {
  "start": {
    name: "Pipeline Entrance",
    type: "System entrypoint",
    engine: "Graph trigger boundary",
    tools: "None",
    state: "Accepts raw user prompt and starts the graph execution.",
    prompt: "Loads thread state from local checkpointer and transitions control to the Query Analyzer."
  },
  "clarity": {
    name: "Query Analyzer (Clarity Agent)",
    type: "Autonomous LLM router",
    engine: "ChatOpenAI (gateway-claude-opus-4-8) | Temp: 0.7",
    tools: "None",
    state: "Reads: query. Writes: clarity_status, clarification_question.",
    prompt: "Evaluate if the user's research query contains a specific company/entity name and research goal.\nIf ambiguous or vague, output: {\"clarity_status\": \"needs_clarification\", \"clarification_question\": \"<question>\"}.\nIf clear, output: {\"clarity_status\": \"clear\"}."
  },
  "research": {
    name: "Literature Scraper (Research Agent)",
    type: "Web search aggregator",
    engine: "ChatOpenAI (gateway-claude-opus-4-8) | Temp: 0.7",
    tools: "Tavily Search Engine API (Parallel invocation)",
    state: "Reads: query, attempts, validator feedback. Writes: research_findings, confidence_score, attempts.",
    prompt: "Generate exactly 3 search queries to find the most relevant information.\nScrape the web results, format source URLs and contents, then evaluate research completeness on a 0-10 scale.\nRespond in JSON format: {\"confidence_score\": <score>, \"reasoning\": \"<explanation>\"}."
  },
  "validator": {
    name: "Fact-Check Validator (Validator Agent)",
    type: "Audit & validation agent",
    engine: "ChatOpenAI (gateway-claude-opus-4-8) | Temp: 0.7",
    tools: "None",
    state: "Reads: query, research_findings. Writes: validation_result.",
    prompt: "Assess whether the gathered search findings contain enough facts, dates, and numbers to fully satisfy the query.\nRespond in JSON format:\n{\"validation_result\": \"sufficient\" or \"insufficient\", \"reason\": \"<explanation>\"}."
  },
  "synthesis": {
    name: "Drafting Engine (Synthesis Agent)",
    type: "Business report compiler",
    engine: "ChatOpenAI (gateway-claude-opus-4-8) | Temp: 0.7",
    tools: "None",
    state: "Reads: query, research_findings, conversation history. Writes: final_response.",
    prompt: "Synthesize the gathered evidence into a clear, formatted report:\n1. Short Executive Summary\n2. Clearly labeled sections with headers (##)\n3. Markdown table grids for tabular numbers and timeline dates\n4. Bullet points and key takeaways."
  },
  "end": {
    name: "Pipeline Termination",
    type: "System exitpoint",
    engine: "Graph exit boundary",
    tools: "None",
    state: "Concludes the LangGraph trace and delivers final report payload to the API client.",
    prompt: "Graph enters terminal state (END). Checkpointer commits changes. Responses rendered in client."
  }
};

function renderPipelineView() {
  // Reset nodes active selected states
  document.querySelectorAll(".graph-node-group").forEach(el => el.classList.remove("node-active-selected"));

  // Map our STATE.activeNode to highlight executing node
  let activeNodeId = "start";
  if (STATE.activeNode === "clarity_agent") activeNodeId = "clarity";
  else if (STATE.activeNode === "research_agent") activeNodeId = "research";
  else if (STATE.activeNode === "validator_agent") activeNodeId = "validator";
  else if (STATE.activeNode === "synthesis_agent") activeNodeId = "synthesis";
  else if (STATE.displayHistory.length > 0 && !STATE.activeNode) activeNodeId = "end";

  const activeGroup = document.getElementById(`node-${activeNodeId}`);
  if (activeGroup) {
    activeGroup.classList.add("node-active-selected");
  }

  // Pre-select active node in inspector
  selectPipelineNode(activeNodeId);
}

function selectPipelineNode(nodeKey) {
  const data = NODE_SPECIFICATIONS[nodeKey];
  if (!data) return;

  // Visual node select state update on click
  document.querySelectorAll(".graph-node-group").forEach(el => el.classList.remove("node-active-selected"));
  const nodeEl = document.getElementById(`node-${nodeKey}`);
  if (nodeEl) nodeEl.classList.add("node-active-selected");

  document.getElementById("node-inspector-empty").classList.add("hidden");
  const inspector = document.getElementById("node-inspector-content");
  inspector.classList.remove("hidden");

  document.getElementById("inspector-node-name").textContent = data.name;
  document.getElementById("inspector-node-type").textContent = data.type;
  document.getElementById("inspector-node-engine").textContent = data.engine;
  document.getElementById("inspector-node-tools").textContent = data.tools;
  document.getElementById("inspector-node-state").textContent = data.state;
  document.getElementById("inspector-node-prompt").textContent = data.prompt;
}

// ── 3. Knowledge Base Registry ──────────────────────────────────────
function renderKnowledgeView() {
  const findings = sessionStorage.getItem("aetheris_findings");
  if (!findings) {
    document.getElementById("knowledge-empty").classList.remove("hidden");
    document.getElementById("knowledge-content").classList.add("hidden");
    return;
  }

  document.getElementById("knowledge-empty").classList.add("hidden");
  document.getElementById("knowledge-content").classList.remove("hidden");

  const sources = extractSourcesFromFindings(findings);
  const tbody = document.getElementById("sources-table-body");

  if (sources.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 20px; color:var(--text-light)">No specific web source URLs could be extracted.</td></tr>`;
    return;
  }

  tbody.innerHTML = sources.map((s, idx) => {
    let domain = "External Article";
    try {
      domain = new URL(s.url).hostname.replace("www.", "");
    } catch (_) { }

    return `
      <tr class="source-row">
        <td style="font-weight:600; color:var(--text-light);">${idx + 1}</td>
        <td><span class="source-domain-badge">${escapeHtml(domain)}</span></td>
        <td><span class="source-snippet-text" title="${escapeHtml(s.content)}">${escapeHtml(s.content)}</span></td>
        <td>
          <a href="${escapeHtml(s.url)}" target="_blank" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:4px;">
            Open URL
            <svg class="icon" style="width:10px; height:10px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
          </a>
        </td>
      </tr>
    `;
  }).join("");
}

function extractSourcesFromFindings(findings) {
  if (!findings || typeof findings !== 'string') return [];

  const sources = [];
  const lines = findings.split(/\r?\n/);
  let currentQuery = "General Search";
  let currentUrl = "";
  let currentContent = [];

  function flushSource() {
    if (currentUrl) {
      sources.push({
        url: currentUrl,
        content: currentContent.join(" ").substring(0, 180) + "...",
        query: currentQuery
      });
      currentContent = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith("=== ")) {
      flushSource();
      currentUrl = "";
      const searchIdx = line.indexOf("Search:");
      if (searchIdx > 0) {
        const endIdx = line.indexOf("===", searchIdx + 7);
        currentQuery = endIdx > searchIdx + 7
          ? line.substring(searchIdx + 7, endIdx).trim()
          : "General Search";
      } else {
        currentQuery = line.replace(/===/g, "").trim();
      }
    } else if (line.match(/^\[\d+\]\s+https?:\/\//)) {
      flushSource();
      const urlMatch = line.match(/^\[\d+\]\s+(https?:\/\/\S+)/);
      currentUrl = urlMatch ? urlMatch[1] : "";
      const restOfLine = line.replace(/^\[\d+\]\s+https?:\/\/\S+\s*/, "").trim();
      if (restOfLine) {
        currentContent.push(restOfLine);
      }
    } else if (currentUrl && line) {
      currentContent.push(line);
    }
  }

  flushSource();

  return sources;
}

function filterKnowledgeTable() {
  const searchInput = document.getElementById("knowledge-search");
  if (!searchInput) return;
  const query = searchInput.value.toLowerCase().trim();
  const rows = document.querySelectorAll("#sources-table-body .source-row");

  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    if (!query || text.includes(query)) {
      row.classList.remove("hidden");
    } else {
      row.classList.add("hidden");
    }
  });
}

// ── 4. Storage Sessions Archive ──────────────────────────────────────
function saveToArchive(data, query) {
  if (!data || !data.thread_id) return;

  let archive = [];
  try {
    archive = JSON.parse(localStorage.getItem("aetheris_archive") || "[]");
    if (!Array.isArray(archive)) archive = [];
  } catch (e) {
    archive = [];
  }

  const session = {
    id: data.thread_id,
    query: query || "General Query",
    timestamp: new Date().toLocaleString(),
    final_response: data.final_response || "",
    confidence_score: data.confidence_score || 0,
    completion: data.completion || 0,
    attempts: data.attempts || 1,
    agents: Array.isArray(data.agents) ? data.agents : [],
    displayHistory: Array.isArray(STATE.displayHistory) ? STATE.displayHistory : [],
    research_findings: data.research_findings || sessionStorage.getItem("aetheris_findings") || ""
  };

  const idx = archive.findIndex(s => s && s.id === session.id);
  if (idx !== -1) {
    archive[idx] = session;
  } else {
    archive.unshift(session);
  }

  try {
    localStorage.setItem("aetheris_archive", JSON.stringify(archive));
  } catch (e) {
    console.warn("Failed to save to archive (storage may be full):", e);
  }
}

function renderArchiveView() {
  let archive = [];
  try {
    archive = JSON.parse(localStorage.getItem("aetheris_archive") || "[]");
    if (!Array.isArray(archive)) archive = [];
  } catch (e) {
    archive = [];
  }

  const empty = document.getElementById("archive-empty");
  const content = document.getElementById("archive-content");

  if (archive.length === 0) {
    empty.classList.remove("hidden");
    content.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  content.classList.remove("hidden");

  content.innerHTML = archive.map((session) => {
    if (!session || !session.id) return "";

    const score = session.confidence_score || 0;
    let badgeClass = "confidence-badge-md";
    let badgeText = "Medium Confidence";
    if (score >= 7) {
      badgeClass = "confidence-badge-hi";
      badgeText = "High Confidence";
    }

    const msgCount = Array.isArray(session.displayHistory) ? session.displayHistory.length : 0;

    return `
      <div class="archive-card" onclick="restoreSession('${escapeHtml(session.id)}')">
        <div>
          <div class="archive-header">
            <span class="archive-time">${escapeHtml(session.timestamp || "Unknown date")}</span>
            <span class="${badgeClass}" style="font-size:8px; padding:2px 6px;">${badgeText} (${score}/10)</span>
          </div>
          <h3 class="archive-query" title="${escapeHtml(session.query || "")}">${escapeHtml(session.query || "Untitled Session")}</h3>
        </div>
        <div class="archive-footer">
          <span style="font-size:11px; color:var(--text-light)">${msgCount} message${msgCount !== 1 ? 's' : ''}</span>
          <div class="archive-btn-row">
            <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); deleteSession('${escapeHtml(session.id)}')" style="color:#d9534f; border-color:#d9534f; background:transparent;">
              Delete
            </button>
          </div>
        </div>
      </div>
    `;
  }).filter(Boolean).join("");
}

function restoreSession(sessionId) {
  const archive = JSON.parse(localStorage.getItem("aetheris_archive") || "[]");
  const session = archive.find(s => s.id === sessionId);
  if (!session) return;

  STATE.threadId = session.id;
  STATE.isClarifying = false;
  STATE.clarificationQuestion = "";
  STATE.displayHistory = Array.isArray(session.displayHistory) ? session.displayHistory : [];
  STATE.sessionTitle = session.query && session.query.length > 50
    ? session.query.substring(0, 48) + "…"
    : (session.query || "Synthesis Workspace");
  STATE.activeNode = null;

  // Reset clarification state in sessionStorage
  sessionStorage.setItem("aetheris_thread_id", STATE.threadId);
  sessionStorage.setItem("aetheris_is_clarifying", "false");
  sessionStorage.setItem("aetheris_clarification_question", "");
  sessionStorage.setItem("aetheris_session_title", STATE.sessionTitle);
  sessionStorage.setItem("aetheris_history", JSON.stringify(STATE.displayHistory));

  // Clear any existing clarification flag from context
  DOM.chatInput.placeholder = "Instruct agents to pivot research focus or synthesize specific findings...";

  if (session.research_findings) {
    sessionStorage.setItem("aetheris_findings", session.research_findings);
  } else {
    sessionStorage.removeItem("aetheris_findings");
  }

  const mockMetricsData = {
    completion: session.completion || 100,
    confidence_score: session.confidence_score || 0,
    attempts: session.attempts || 1,
    agents: Array.isArray(session.agents) ? session.agents : [],
    validation_result: session.confidence_score >= 6 ? "sufficient" : "insufficient"
  };
  sessionStorage.setItem("aetheris_metrics", JSON.stringify(mockMetricsData));

  DOM.sessionTitle.textContent = STATE.sessionTitle;
  renderFeed();
  updateMetricsUI(mockMetricsData);

  switchView(VIEWS.RESEARCH);
}

function deleteSession(sessionId) {
  if (!sessionId) return;

  let archive = [];
  try {
    archive = JSON.parse(localStorage.getItem("aetheris_archive") || "[]");
    if (!Array.isArray(archive)) archive = [];
  } catch (e) {
    archive = [];
  }

  archive = archive.filter(s => s && s.id !== sessionId);

  try {
    localStorage.setItem("aetheris_archive", JSON.stringify(archive));
  } catch (e) {
    console.warn("Failed to update archive:", e);
  }

  if (STATE.threadId === sessionId) {
    clearSession();
  } else {
    renderArchiveView();
  }
}

// Global scope mapping for SVG and inline handlers
window.selectPipelineNode = selectPipelineNode;
window.restoreSession = restoreSession;
window.deleteSession = deleteSession;

// Run init on load
window.addEventListener("DOMContentLoaded", init);
