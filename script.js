// ═══════════════════════════════════════════════════════════════
// STATE MANAGEMENT & CONFIGURATION
// ═══════════════════════════════════════════════════════════════
const STATE = {
  threadId: null,
  isClarifying: false,
  clarificationQuestion: "",
  displayHistory: [],
  sessionTitle: "Synthesis Workspace"
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
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
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
  DOM.chatInput.addEventListener("input", function() {
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
}

// ═══════════════════════════════════════════════════════════════
// ACTION HANDLERS
// ═══════════════════════════════════════════════════════════════
async function handleSubmit() {
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
  renderFeed();
  saveSessionState();

  // Show loading
  DOM.loadingOverlay.classList.remove("hidden");

  try {
    const payload = {
      query: query,
      thread_id: STATE.threadId
    };

    if (STATE.isClarifying) {
      payload.clarification_answer = query;
    }

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      // Try to extract the detailed error message from the JSON body first.
      // Vercel/FastAPI always sends {"detail": "..."} on errors.
      let errorMsg = `HTTP ${response.status}`;
      try {
        const errBody = await response.json();
        errorMsg = errBody.detail || errBody.error || errBody.message || errorMsg;
      } catch (_) {
        errorMsg = response.statusText || errorMsg;
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();

    // Update state from API response
    STATE.isClarifying = data.is_clarifying;
    STATE.clarificationQuestion = data.clarification_question;
    sessionStorage.setItem("aetheris_is_clarifying", STATE.isClarifying);
    sessionStorage.setItem("aetheris_clarification_question", STATE.clarificationQuestion);

    if (STATE.isClarifying) {
      STATE.displayHistory.push({
        role: "clarification",
        content: STATE.clarificationQuestion
      });
    } else if (data.final_response) {
      // Extract pseudo-tags from query
      const tags = extractTags(payload.query);
      STATE.displayHistory.push({
        role: "assistant",
        title: "Literature Review Summary",
        content: data.final_response,
        confidence: data.confidence_score,
        tags: tags
      });
    } else {
      STATE.displayHistory.push({
        role: "assistant",
        title: "System Notice",
        content: "Research complete, but no final response was drafted. Please refine your query."
      });
    }

    // Update UI elements
    renderFeed();
    updateMetricsUI(data);
    saveSessionState();
    sessionStorage.setItem("aetheris_metrics", JSON.stringify(data));

  } catch (err) {
    console.error(err);
    STATE.displayHistory.push({
      role: "assistant",
      title: "System Error",
      content: `Failed to communicate with research graph: ${err.message}`
    });
    renderFeed();
  } finally {
    DOM.loadingOverlay.classList.add("hidden");
  }
}

function clearSession() {
  sessionStorage.removeItem("aetheris_thread_id");
  sessionStorage.removeItem("aetheris_history");
  sessionStorage.removeItem("aetheris_is_clarifying");
  sessionStorage.removeItem("aetheris_clarification_question");
  sessionStorage.removeItem("aetheris_session_title");
  sessionStorage.removeItem("aetheris_metrics");

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
  const existingElements = DOM.chatFeed.querySelectorAll(".chat-bubble-user, .report-card, .clarify-banner");
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

  // Scroll to bottom
  DOM.chatFeed.scrollTop = DOM.chatFeed.scrollHeight;
}

function updateMetricsUI(data) {
  // Overall completion
  DOM.completionText.textContent = `${data.completion}%`;
  DOM.completionBar.style.width = `${data.completion}%`;

  // Active agents header badge
  const activeCount = data.agents.filter(a => a.status === "complete").length;
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

  // Confidence bar
  if (data.confidence_score > 0) {
    DOM.confidenceSection.classList.remove("hidden");
    DOM.confidenceText.textContent = `${data.confidence_score}/10`;
    DOM.confidenceBar.style.width = `${data.confidence_score * 10}%`;
  } else {
    DOM.confidenceSection.classList.add("hidden");
  }

  // Deployed agents list
  DOM.agentsList.innerHTML = data.agents.map(a => {
    let statusClass = "status-idle";
    if (a.status === "complete") statusClass = "status-complete";
    if (a.status === "busy") statusClass = "status-busy";

    return `
      <div class="agent-item">
        <div class="agent-avatar ${statusClass}">${escapeHtml(a.icon)}</div>
        <div>
          <div class="agent-name">${escapeHtml(a.name)}</div>
          <div class="agent-status">${escapeHtml(a.sub)}</div>
        </div>
      </div>
    `;
  }).join("");

  // Validation pill
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
  const stopWords = new Set(["the","and","for","with","that","this","from","are","was","were","have","has","not","but","its","about","what"]);
  const words = query.split(/\s+/)
    .map(w => w.replace(/[.,!?;:":']/g, "").trim())
    .filter(w => w.length > 4 && !stopWords.has(w.toLowerCase()))
    .map(w => w.charAt(0).toUpperCase() + w.slice(1));
    
  return [...new Set(words)].slice(0, 4);
}

function formatReportMarkdown(text) {
  let html = escapeHtml(text);
  
  // Headers (## Title)
  html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  
  // Unordered list items (- Item)
  html = html.replace(/^\s*-\s+(.+)$/gm, '<li>$1</li>');
  
  // Wrap lists
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  
  return html;
}

// Run init on load
window.addEventListener("DOMContentLoaded", init);
