const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const statusEl = document.getElementById("status");

let ws = null;
let threadId = null;
// Tracks the collapsible tool-updates panel for the current user question
let currentToolPanel = null;
let pendingAnswer = false;

// Backend URL — auto-detects environment:
// - Frontend deployed (e.g. Vercel) -> primary hosted backend
// - Served locally (localhost / 127.0.0.1) -> local backend on port 8000
const PRIMARY_BACKEND = "https://research-agent-ez0j.onrender.com";
const LOCAL_BACKEND = "http://localhost:8000";
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_HOST = isLocal ? LOCAL_BACKEND : PRIMARY_BACKEND;

/* ---------- Minimal Markdown renderer (no dependencies) ---------- */
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderMarkdown(md) {
  let text = escapeHtml(md);

  // Fenced code blocks first
  const codeBlocks = [];
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push(`<pre><code>${code}</code></pre>`);
    return `\u0000CODE${codeBlocks.length - 1}\u0000`;
  });

  // Inline code
  const inlineCodes = [];
  text = text.replace(/`([^`\n]+)`/g, (_, code) => {
    inlineCodes.push(`<code>${code}</code>`);
    return `\u0000IC${inlineCodes.length - 1}\u0000`;
  });

  // Plain uploaded-file citations are emitted as:
  // [filename.docx, chunk 6; filename.pdf, chunk 6].
  // Link each cited file to the current user's files endpoint.
  text = text.replace(/\[([^\]]+)\]/g, (full, citationGroup) => {
    const citations = citationGroup.split(/;\s*/);
    const links = citations.map(citation => {
      const match = citation.trim().match(
        /(?:^|[/\\])([^/\\,;]+\.(?:pdf|txt|md|docx|csv|xlsx|json))(?:,\s*chunk\s+\d+)?$/i
      );
      if (!match) return null;
      const filename = match[1];
      const user = new URLSearchParams(window.location.search).get("session") || "";
      const href = `${API_HOST}/files/${encodeURIComponent(user)}/${encodeURIComponent(filename)}`;
      return `<a href="${href}" target="_blank" rel="noopener noreferrer">${escapeHtml(citation.trim())}</a>`;
    });
    return links.every(Boolean) ? links.join("; ") : full;
  });

  // Uploaded-file citations use the form [label](filename.ext, chunk N).
  // Turn them into links to the current user's file endpoint.
  text = text.replace(/\[([^\]]+)\]\((?!https?:\/\/)([^)\n]+)\)/gi,
    (_, label, citation) => {
      const match = citation.trim().match(
        /(?:^|[/\\])([^/\\]+\.(?:pdf|txt|md|docx|csv|xlsx|json))(?:,\s*chunk\s+\d+)?$/i
      );
      if (!match) return _;
      const filename = match[1];
      const user = new URLSearchParams(window.location.search).get("session") || "";
      const href = `${API_HOST}/files/${encodeURIComponent(user)}/${encodeURIComponent(filename)}`;
      return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });

  // Links: [text](url)
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
    const isCiteNum = /^\[\d+\]$|^\d+$/.test(label.trim());
    const cls = isCiteNum ? ' class="cite-num"' : "";
    const title = isCiteNum ? ` title="${url}"` : "";
    return `<a href="${url}" target="_blank" rel="noopener noreferrer"${cls}${title}>${label}</a>`;
  });
  // Bare URLs
  text = text.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g,
    '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');

  // Bold / italic / strikethrough
  text = text.replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<em>$2</em>");
  text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");

  // Headings
  text = text.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  text = text.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Blockquote
  text = text.replace(/^&gt; ?(.+)$/gm, "<blockquote>$1</blockquote>");

  // Horizontal rule
  text = text.replace(/^---+$/gm, "<hr>");

  // Unordered lists (group consecutive lines)
  text = text.replace(/(?:^[-*] .+(?:\n|$))+/gm, (block) => {
    const items = block.trim().split("\n").map(l => `<li>${l.replace(/^[-*] /, "")}</li>`).join("");
    return `<ul>${items}</ul>\n`;
  });
  // Ordered lists
  text = text.replace(/(?:^\d+\. .+(?:\n|$))+/gm, (block) => {
    const items = block.trim().split("\n").map(l => `<li>${l.replace(/^\d+\. /, "")}</li>`).join("");
    return `<ol>${items}</ol>\n`;
  });

  // Paragraphs: remaining non-empty lines not already block-level
  text = text.split(/\n{2,}/).map(chunk => {
    const t = chunk.trim();
    if (!t) return "";
    if (/^<(h\d|ul|ol|pre|blockquote|hr|table|div)/.test(t)) return t;
    return `<p>${t.replace(/\n/g, "<br>")}</p>`;
  }).join("\n");

  // Restore code placeholders
  text = text.replace(/\u0000CODE(\d+)\u0000/g, (_, i) => codeBlocks[i]);
  text = text.replace(/\u0000IC(\d+)\u0000/g, (_, i) => inlineCodes[i]);

  return text;
}

function renderAgentMessage(text) {
  const div = document.createElement("div");
  div.className = "msg agent md";
  div.innerHTML = renderMarkdown(text);

  // Collect all links into a "Sources" section at the bottom
  const links = [...div.querySelectorAll("a[href^='http']")];
  const unique = new Map();
  links.forEach(a => {
    const href = a.href;
    if (!unique.has(href)) unique.set(href, a.textContent.trim() || href);
  });
  if (unique.size > 0) {
    const src = document.createElement("div");
    src.className = "sources";
    src.innerHTML =
      '<div class="sources-title">Sources</div>' +
      '<ol>' + [...unique.entries()].map(([href, label]) =>
        `<li><a href="${href}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a></li>`
      ).join("") + '</ol>';
    div.appendChild(src);
  }

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function addMsg(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function getToolPanel() {
  if (!currentToolPanel || !currentToolPanel.isConnected) {
    currentToolPanel = document.createElement("details");
    currentToolPanel.className = "tool-updates";
    currentToolPanel.innerHTML =
      '<summary><span class="updates-count">0</span> agent steps</summary>' +
      '<div class="updates-body"></div>';
    chat.appendChild(currentToolPanel);
  }
  return currentToolPanel;
}

function addToolUpdate(msg) {
  const panel = getToolPanel();
  const body = panel.querySelector(".updates-body");
  const count = panel.querySelector(".updates-count");

  const entry = document.createElement("div");
  entry.className = "update-entry";
  entry.innerHTML =
    `<div class="update-meta">${escapeHtml(msg.timestamp)} · ${escapeHtml(msg.function)}</div>` +
    escapeHtml(msg.content);
  body.appendChild(entry);
  body.scrollTop = body.scrollHeight;

  count.textContent = body.children.length;
  // Auto-open briefly so the user sees activity, they can collapse it
  panel.open = true;
  chat.scrollTop = chat.scrollHeight;
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  input.disabled = busy;
}

async function connect(threadId) {
  const res = await fetch(`${API_HOST}/generate_thread_id`);
  // Use the username (session id) if provided, otherwise fall back to a random id
  threadId = threadId || ((await res.json()).thread_id);

  const proto = API_HOST.startsWith("https") ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${API_HOST.replace(/^https?:\/\//, "")}/ws/${threadId}`);

  ws.onopen = () => { statusEl.textContent = "connected"; };
  ws.onclose = () => { statusEl.textContent = "disconnected"; };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "response") {
      renderAgentMessage(msg.content);
      setBusy(false);
    } else if (msg.type === "agent_question") {
      const div = addMsg("", "agent question");
      const header = document.createElement("span");
      header.className = "question-header";
      header.textContent = "Question";
      div.appendChild(header);
      div.appendChild(document.createTextNode(msg.content));
      setBusy(false); // let the user answer
      pendingAnswer = true;
    } else if (msg.type === "tool_update") {
      addToolUpdate(msg);
    } else if (msg.type === "status") {
      statusEl.textContent = msg.content;
    }
  };
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  document.body.classList.add("chat-started");
  addMsg(text, "user");
  input.value = "";
  currentToolPanel = null; // new question → fresh collapsible panel
  if (pendingAnswer) {
    // This message is the answer to the agent's question
    ws.send(JSON.stringify({ type: "answer", content: text }));
    pendingAnswer = false;
  } else {
    ws.send(JSON.stringify({ type: "message", content: text }));
  }
  setBusy(true);
  statusEl.textContent = "thinking...";
});

// Example prompt chips — fill and submit
document.querySelectorAll(".example").forEach(btn => {
  btn.addEventListener("click", () => {
    input.value = btn.textContent;
    form.dispatchEvent(new Event("submit", { cancelable: true }));
  });
});

/* ---------- Entry point: session id comes from the setup page ---------- */
const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session");

if (!sessionId) {
  // No session yet → send the user back to setup
  window.location.href = "index.html";
} else {
  connect(sessionId);
  addMsg(`Hello ${sessionId}! We have a few exoplanet related files and preset prompts to test.`, "system");
}

/* ---------- Files panel & in-chat upload ---------- */
const filesBtn = document.getElementById("filesBtn");
const uploadBtn = document.getElementById("uploadBtn");
const chatFileInput = document.getElementById("chatFileInput");
const filesPanel = document.getElementById("filesPanel");
const closeFilesBtn = document.getElementById("closeFilesBtn");
const filesList = document.getElementById("filesList");

function getSessionUser() {
  return new URLSearchParams(window.location.search).get("session") || "";
}

function formatSize(bytes) {
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB";
  return bytes + " B";
}

async function loadFiles() {
  const user = getSessionUser();
  filesList.innerHTML = '<li class="empty">Loading…</li>';
  try {
    const res = await fetch(`${API_HOST}/files/${encodeURIComponent(user)}`);
    if (!res.ok) throw new Error(`server returned ${res.status}`);
    const data = await res.json();
    if (!data.files.length) {
      filesList.innerHTML = '<li class="empty">No files uploaded yet.</li>';
      return;
    }
    filesList.innerHTML = data.files.map(f =>
      `<li><a href="${API_HOST}/files/${encodeURIComponent(user)}/${encodeURIComponent(f.name)}" target="_blank" rel="noopener noreferrer">📄 ${escapeHtml(f.name)}</a><span class="size">${formatSize(f.size)}</span></li>`
    ).join("");
  } catch {
    filesList.innerHTML = '<li class="empty">Failed to load files.</li>';
  }
}

filesBtn.addEventListener("click", () => {
  filesPanel.classList.remove("hidden");
  loadFiles();
});
closeFilesBtn.addEventListener("click", () => filesPanel.classList.add("hidden"));
filesPanel.addEventListener("click", e => {
  if (e.target === filesPanel) filesPanel.classList.add("hidden");
});

uploadBtn.addEventListener("click", () => chatFileInput.click());
chatFileInput.addEventListener("change", async () => {
  const user = getSessionUser();
  if (!user || !chatFileInput.files.length) return;
  statusEl.textContent = "Uploading & indexing files...";
  const fd = new FormData();
  fd.append("username", user);
  [...chatFileInput.files].forEach(f => fd.append("files", f));
  chatFileInput.value = "";
  try {
    const res = await fetch(`${API_HOST}/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`server returned ${res.status}`);
    const data = await res.json();
    const ok = data.results.filter(r => r.status === "indexed").length;
    statusEl.textContent = `${ok}/${data.results.length} file(s) indexed`;
    setTimeout(() => { if (statusEl.textContent.includes("indexed")) statusEl.textContent = ""; }, 4000);
  } catch {
    statusEl.textContent = "Upload failed";
  }
});
