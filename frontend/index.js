/* ---------- Backend URL — auto-detects environment ---------- */
const PRIMARY_BACKEND = "https://research-agent-ez0j.onrender.com";
const LOCAL_BACKEND = "http://localhost:8000";
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_HOST = isLocal ? LOCAL_BACKEND : PRIMARY_BACKEND;

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ---------- Onboarding / setup flow ---------- */
const usernameInput = document.getElementById("username");
const fileInput = document.getElementById("fileInput");
const fileDrop = document.getElementById("fileDrop");
const fileList = document.getElementById("fileList");
const startBtn = document.getElementById("startBtn");
const progressWrap = document.getElementById("progressWrap");
const progressLabel = document.getElementById("progressLabel");
const progressBar = document.getElementById("progressBar");

let selectedFiles = [];

function refreshFileList() {
  fileList.innerHTML = selectedFiles.map(f => `<div>📄 ${escapeHtml(f.name)}</div>`).join("");
  startBtn.disabled = !usernameInput.value.trim() || selectedFiles.length === 0;
}

usernameInput.addEventListener("input", refreshFileList);

fileDrop.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  selectedFiles = [...selectedFiles, ...fileInput.files];
  fileInput.value = "";
  refreshFileList();
});
["dragover", "dragenter"].forEach(ev =>
  fileDrop.addEventListener(ev, e => { e.preventDefault(); fileDrop.classList.add("dragover"); }));
["dragleave", "drop"].forEach(ev =>
  fileDrop.addEventListener(ev, e => { e.preventDefault(); fileDrop.classList.remove("dragover"); }));
fileDrop.addEventListener("drop", e => {
  selectedFiles = [...selectedFiles, ...e.dataTransfer.files];
  refreshFileList();
});

startBtn.addEventListener("click", async () => {
  const username = usernameInput.value.trim();
  if (!username || selectedFiles.length === 0) return;

  startBtn.disabled = true;
  usernameInput.disabled = true;
  progressWrap.classList.add("active");

  const fd = new FormData();
  fd.append("username", username);
  selectedFiles.forEach(f => fd.append("files", f));

  try {
    const res = await fetch(`${API_HOST}/setup`, { method: "POST", body: fd });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const p = JSON.parse(line);
        if (p.stage === "index" && p.total > 0) {
          progressBar.style.width = `${Math.round((p.current / p.total) * 100)}%`;
        }
        progressLabel.textContent = p.message || "";
      }
    }

    // Done → go to the chat page with the username as session id
    progressBar.style.width = "100%";
    setTimeout(() => {
      window.location.href = `chat.html?session=${encodeURIComponent(username)}`;
    }, 400);
  } catch (err) {
    progressLabel.textContent = "Upload failed: " + err.message;
    startBtn.disabled = false;
    usernameInput.disabled = false;
  }
});
