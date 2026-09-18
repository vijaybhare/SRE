// PRR Readiness frontend: submits a job, polls until it's done, renders the result.

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

async function pollJob(jobId, { onUpdate }) {
  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) throw new Error(`Status check failed (${res.status})`);
    const job = await res.json();
    onUpdate(job);
    if (job.status === "done" || job.status === "error") return job;
    await new Promise((r) => setTimeout(r, 1500));
  }
}

function setStatus(el, text, isError) {
  el.hidden = false;
  el.textContent = text;
  el.classList.toggle("error", !!isError);
}

const VERDICT_LABEL = {
  pass: "Pass",
  partial: "Partial",
  fail: "Fail",
  not_applicable: "N/A",
  not_evaluated: "Not evaluated",
};

function gateClass(decision) {
  if (decision === "READY") return "ready";
  if (decision === "CONDITIONAL") return "conditional";
  return "not-ready";
}

function renderAssessResult(container, data) {
  const report = data.json;
  container.hidden = false;
  container.innerHTML = "";

  const banner = document.createElement("div");
  banner.className = `gate-banner ${gateClass(report.gate_decision)}`;
  banner.innerHTML = `${report.gate_decision} <span class="pct">— ${report.overall_readiness_percentage}% readiness (${data.change_source})</span>`;
  container.appendChild(banner);

  if (report.blocking_items.length) {
    container.appendChild(renderFindingGroup("Blocking (mandatory, failed)", report.blocking_items, "fail"));
  }
  if (report.at_risk_items.length) {
    container.appendChild(renderFindingGroup("At risk (mandatory, partial)", report.at_risk_items, "partial"));
  }

  const catTitle = document.createElement("h3");
  catTitle.className = "section-title";
  catTitle.textContent = "By category";
  container.appendChild(catTitle);

  const table = document.createElement("table");
  table.innerHTML = `<thead><tr><th>Category</th><th>Score</th></tr></thead>`;
  const tbody = document.createElement("tbody");
  report.by_category.forEach((c) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${c.category}</td><td>${c.percentage}%</td>`;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);

  const findTitle = document.createElement("h3");
  findTitle.className = "section-title";
  findTitle.textContent = "All findings";
  container.appendChild(findTitle);

  const items = [...report.items].sort((a, b) =>
    a.category === b.category ? a.id.localeCompare(b.id) : a.category.localeCompare(b.category)
  );
  items.forEach((item) => container.appendChild(renderFinding(item)));

  const dl = document.createElement("a");
  dl.className = "download-link";
  dl.textContent = "Download full report (Markdown)";
  dl.href = URL.createObjectURL(new Blob([data.markdown], { type: "text/markdown" }));
  dl.download = "prr-report.md";
  container.appendChild(dl);
}

function renderFindingGroup(title, items, verdict) {
  const wrap = document.createElement("div");
  const h = document.createElement("h3");
  h.className = "section-title";
  h.textContent = title;
  wrap.appendChild(h);
  items.forEach((item) => wrap.appendChild(renderFinding({ ...item, verdict })));
  return wrap;
}

function renderFinding(item) {
  const div = document.createElement("div");
  div.className = `finding ${item.verdict}`;
  div.innerHTML = `
    <div class="finding-id">${item.id} — ${item.category}${item.weight ? ` (weight ${item.weight})` : ""}</div>
    <div class="finding-req">${escapeHtml(item.requirement)}</div>
    <div class="finding-meta">${VERDICT_LABEL[item.verdict] || item.verdict}${item.rationale ? " — " + escapeHtml(item.rationale) : ""}</div>
  `;
  return div;
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

document.getElementById("assess-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector("button[type=submit]");
  const statusEl = document.getElementById("assess-status");
  const resultEl = document.getElementById("assess-result");
  resultEl.hidden = true;
  submitBtn.disabled = true;

  try {
    setStatus(statusEl, "Uploading and starting assessment…");
    const fd = new FormData(form);
    const res = await fetch("/api/assess", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Failed to start assessment (${res.status})`);
    const { job_id } = await res.json();

    const job = await pollJob(job_id, {
      onUpdate: (j) => setStatus(statusEl, j.status === "running" ? "Grading change against PRR criteria…" : "Queued…"),
    });

    if (job.status === "error") {
      setStatus(statusEl, `Error: ${job.error}`, true);
      return;
    }
    statusEl.hidden = true;
    renderAssessResult(resultEl, job.result);
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});

document.getElementById("rubric-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector("button[type=submit]");
  const statusEl = document.getElementById("rubric-status");
  const resultEl = document.getElementById("rubric-result");
  resultEl.hidden = true;
  submitBtn.disabled = true;

  try {
    setStatus(statusEl, "Uploading and generating criteria…");
    const fd = new FormData(form);
    const res = await fetch("/api/normalize-criteria", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Failed to start (${res.status})`);
    const { job_id } = await res.json();

    const job = await pollJob(job_id, {
      onUpdate: (j) => setStatus(statusEl, j.status === "running" ? "Normalizing standards into criteria…" : "Queued…"),
    });

    if (job.status === "error") {
      setStatus(statusEl, `Error: ${job.error}`, true);
      return;
    }
    statusEl.hidden = true;
    resultEl.hidden = false;
    const rubric = job.result.rubric;
    const dl = document.createElement("a");
    dl.className = "download-link";
    dl.textContent = `Download rubric.json (${rubric.length} criteria)`;
    dl.href = URL.createObjectURL(new Blob([JSON.stringify(rubric, null, 2)], { type: "application/json" }));
    dl.download = "rubric.json";
    resultEl.innerHTML = "";
    resultEl.appendChild(dl);
    const pre = document.createElement("pre");
    pre.className = "rubric-preview";
    pre.textContent = JSON.stringify(rubric, null, 2);
    resultEl.appendChild(pre);
  } catch (err) {
    setStatus(statusEl, `Error: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});
