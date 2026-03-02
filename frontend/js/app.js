/**
 * Deadline Conflict Resolver – Frontend Application
 *
 * Manages task state locally, communicates with the Flask backend for
 * AI analysis, and renders results (conflicts, workload, risk, schedule).
 */

const API_BASE = window.location.origin;

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  tasks: [],       // Array of task objects
  editingId: null, // ID of task being edited (null = add mode)
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const form        = document.getElementById("task-form");
const titleEl     = document.getElementById("task-title");
const deadlineEl  = document.getElementById("task-deadline");
const hoursEl     = document.getElementById("task-hours");
const priorityEl  = document.getElementById("task-priority");
const descEl      = document.getElementById("task-description");
const addBtn      = document.getElementById("add-btn");
const cancelBtn   = document.getElementById("cancel-edit-btn");
const analyzeBtn  = document.getElementById("analyze-btn");
const taskList    = document.getElementById("task-list");
const taskCount   = document.getElementById("task-count");
const clearAllBtn = document.getElementById("clear-all-btn");
const resultsPanel = document.getElementById("results-panel");
const toast       = document.getElementById("toast");

// ── Utilities ──────────────────────────────────────────────────────────────
function uid() {
  return "task-" + Math.random().toString(36).slice(2, 10);
}

function showToast(msg, duration = 3000) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), duration);
}

function priorityColor(p) {
  return ["p1","p2","p3","p4","p5"][p - 1] || "p3";
}

function fmtDeadline(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function setMinDeadline() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  deadlineEl.min = now.toISOString().slice(0, 16);
}

// ── Render task list ───────────────────────────────────────────────────────
function renderTasks() {
  taskCount.textContent = state.tasks.length;
  analyzeBtn.disabled = state.tasks.length === 0;

  if (state.tasks.length === 0) {
    taskList.innerHTML = '<p class="empty-state">No tasks added yet. Use the form above to get started.</p>';
    return;
  }

  taskList.innerHTML = state.tasks.map(t => `
    <div class="task-card" data-id="${t.id}">
      <div class="priority-dot ${priorityColor(t.priority)}" title="Priority ${t.priority}"></div>
      <div class="task-card-info">
        <div class="task-card-title">${escHtml(t.title)}</div>
        <div class="task-card-meta">
          📅 ${fmtDeadline(t.deadline)} &nbsp;|&nbsp;
          ⏱ ${t.estimated_hours}h &nbsp;|&nbsp;
          ⭐ P${t.priority}
          ${t.description ? ` &nbsp;|&nbsp; ${escHtml(t.description.slice(0, 50))}${t.description.length > 50 ? "…" : ""}` : ""}
        </div>
      </div>
      <div class="task-card-actions">
        <button class="btn btn-sm btn-secondary" onclick="startEdit('${t.id}')" title="Edit">✏️</button>
        <button class="btn btn-sm btn-danger" onclick="deleteTask('${t.id}')" title="Delete">🗑</button>
      </div>
    </div>
  `).join("");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Form handling ──────────────────────────────────────────────────────────
form.addEventListener("submit", e => {
  e.preventDefault();
  const title = titleEl.value.trim();
  const deadline = deadlineEl.value;
  const hours = parseFloat(hoursEl.value);
  const priority = parseInt(priorityEl.value, 10);
  const description = descEl.value.trim();

  if (!title || !deadline || isNaN(hours) || hours <= 0) {
    showToast("⚠️ Please fill in all required fields.");
    return;
  }

  const deadlineISO = new Date(deadline).toISOString();

  if (state.editingId) {
    const idx = state.tasks.findIndex(t => t.id === state.editingId);
    if (idx !== -1) {
      state.tasks[idx] = { ...state.tasks[idx], title, deadline: deadlineISO, estimated_hours: hours, priority, description };
    }
    state.editingId = null;
    addBtn.textContent = "Add Task";
    cancelBtn.style.display = "none";
    showToast("✅ Task updated.");
  } else {
    state.tasks.push({ id: uid(), title, deadline: deadlineISO, estimated_hours: hours, priority, description });
    showToast("✅ Task added.");
  }

  form.reset();
  setMinDeadline();
  renderTasks();
});

cancelBtn.addEventListener("click", () => {
  state.editingId = null;
  addBtn.textContent = "Add Task";
  cancelBtn.style.display = "none";
  form.reset();
  setMinDeadline();
});

function startEdit(id) {
  const task = state.tasks.find(t => t.id === id);
  if (!task) return;
  state.editingId = id;
  titleEl.value = task.title;
  const local = new Date(task.deadline);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  deadlineEl.value = local.toISOString().slice(0, 16);
  hoursEl.value = task.estimated_hours;
  priorityEl.value = task.priority;
  descEl.value = task.description || "";
  addBtn.textContent = "Update Task";
  cancelBtn.style.display = "inline-flex";
  form.scrollIntoView({ behavior: "smooth" });
}

function deleteTask(id) {
  state.tasks = state.tasks.filter(t => t.id !== id);
  if (state.editingId === id) {
    state.editingId = null;
    addBtn.textContent = "Add Task";
    cancelBtn.style.display = "none";
    form.reset();
    setMinDeadline();
  }
  renderTasks();
  showToast("🗑 Task deleted.");
}

clearAllBtn.addEventListener("click", () => {
  if (state.tasks.length === 0) return;
  if (!confirm("Remove all tasks?")) return;
  state.tasks = [];
  state.editingId = null;
  addBtn.textContent = "Add Task";
  cancelBtn.style.display = "none";
  form.reset();
  setMinDeadline();
  renderTasks();
  resultsPanel.style.display = "none";
  showToast("🗑 All tasks cleared.");
});

// ── Tabs ───────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ── Analysis ───────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  if (state.tasks.length === 0) return;
  analyzeBtn.textContent = "⏳ Analyzing…";
  analyzeBtn.disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/api/analyze/full`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks: state.tasks }),
    });
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    const data = await resp.json();

    renderConflicts(data.conflicts);
    renderWorkload(data.workload);
    renderRisk(data.risk);
    renderSchedule(data.schedule);

    resultsPanel.style.display = "block";
    resultsPanel.scrollIntoView({ behavior: "smooth" });

    // Reset tabs
    document.querySelectorAll(".tab-btn").forEach((b, i) => b.classList.toggle("active", i === 0));
    document.querySelectorAll(".tab-content").forEach((c, i) => c.classList.toggle("active", i === 0));

    showToast("✅ Analysis complete!");
  } catch (err) {
    showToast(`❌ Analysis failed: ${err.message}`, 5000);
    console.error(err);
  } finally {
    analyzeBtn.textContent = "⚡ Analyze & Optimize";
    analyzeBtn.disabled = false;
  }
});

// ── Render: Conflicts ──────────────────────────────────────────────────────
function renderConflicts({ items, count }) {
  const summary = document.getElementById("conflicts-summary");
  const list    = document.getElementById("conflicts-list");

  const sevBadge = count === 0 ? "ok" : (items.some(c => c.severity === "high") ? "bad" : "warn");
  summary.innerHTML = `
    <div class="stat-block">
      <div class="stat-label">Conflicts Found</div>
      <div class="stat-value ${sevBadge}">${count}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Overdue Tasks</div>
      <div class="stat-value ${items.filter(c=>c.type==="overdue").length > 0 ? "bad":"ok"}">
        ${items.filter(c=>c.type==="overdue").length}
      </div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Capacity Issues</div>
      <div class="stat-value ${items.filter(c=>c.type==="capacity_overload"||c.type==="deadline_overload").length > 0 ? "warn":"ok"}">
        ${items.filter(c=>c.type==="capacity_overload"||c.type==="deadline_overload").length}
      </div>
    </div>
  `;

  if (count === 0) {
    list.innerHTML = '<div class="result-card severity-low"><div class="result-card-title">✅ No conflicts detected</div><div class="result-card-body">All tasks can be accommodated without scheduling conflicts.</div></div>';
    return;
  }

  list.innerHTML = items.map(c => `
    <div class="result-card severity-${c.severity || "medium"}">
      <div class="result-card-title">${conflictTypeLabel(c.type)}</div>
      <div class="result-card-body">${escHtml(c.message)}</div>
    </div>
  `).join("");
}

function conflictTypeLabel(type) {
  const map = { overdue: "🔴 Overdue Task", deadline_overload: "🟠 Deadline Overload", capacity_overload: "🟡 Capacity Overload" };
  return map[type] || type;
}

// ── Render: Workload ───────────────────────────────────────────────────────
function renderWorkload(data) {
  const summary   = document.getElementById("workload-summary");
  const breakdown = document.getElementById("workload-breakdown");

  const utilPct = (data.utilization_rate * 100).toFixed(1);
  const utilClass = data.is_feasible ? (data.utilization_rate > 0.8 ? "warn" : "ok") : "bad";

  summary.innerHTML = `
    <div class="stat-block">
      <div class="stat-label">Total Hours Required</div>
      <div class="stat-value">${data.total_estimated_hours}h</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Hours Available</div>
      <div class="stat-value">${data.total_available_hours}h</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Utilization</div>
      <div class="stat-value ${utilClass}">${utilPct}%</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Feasible?</div>
      <div class="stat-value ${data.is_feasible ? "ok" : "bad"}">${data.is_feasible ? "Yes" : "No"}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Overloaded Days</div>
      <div class="stat-value ${data.overloaded_periods.length > 0 ? "warn" : "ok"}">${data.overloaded_periods.length}</div>
    </div>
  `;

  breakdown.innerHTML = data.task_breakdown.map(tb => `
    <div class="result-card ${tb.is_feasible ? "severity-low" : "severity-high"}">
      <div class="result-card-title">${escHtml(tb.task_title)}</div>
      <div class="result-card-body">
        ${tb.estimated_hours}h required &nbsp;|&nbsp;
        ${tb.working_days_until_deadline} working day(s) left &nbsp;|&nbsp;
        ${(tb.utilization_rate * 100).toFixed(1)}% utilization
        ${!tb.is_feasible ? " &nbsp;<strong style='color:var(--color-danger)'>⚠ Infeasible</strong>" : ""}
      </div>
    </div>
  `).join("");
}

// ── Render: Risk ───────────────────────────────────────────────────────────
function renderRisk({ predictions }) {
  const summary = document.getElementById("risk-summary");
  const list    = document.getElementById("risk-list");

  const high   = predictions.filter(p => p.risk_level === "high").length;
  const medium = predictions.filter(p => p.risk_level === "medium").length;
  const low    = predictions.filter(p => p.risk_level === "low").length;
  const avgRisk = predictions.length
    ? (predictions.reduce((s, p) => s + p.risk_score, 0) / predictions.length * 100).toFixed(1)
    : 0;

  summary.innerHTML = `
    <div class="stat-block">
      <div class="stat-label">High Risk</div>
      <div class="stat-value ${high > 0 ? "bad" : "ok"}">${high}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Medium Risk</div>
      <div class="stat-value ${medium > 0 ? "warn" : "ok"}">${medium}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Low Risk</div>
      <div class="stat-value ok">${low}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Avg Risk Score</div>
      <div class="stat-value ${avgRisk >= 70 ? "bad" : avgRisk >= 40 ? "warn" : "ok"}">${avgRisk}%</div>
    </div>
  `;

  list.innerHTML = predictions
    .slice()
    .sort((a, b) => b.risk_score - a.risk_score)
    .map(p => `
      <div class="result-card risk-${p.risk_level}">
        <div class="result-card-title">${escHtml(p.task_title)} — <span style="text-transform:capitalize">${p.risk_level} risk</span></div>
        <div class="result-card-body">
          Risk score: ${(p.risk_score * 100).toFixed(1)}% &nbsp;|&nbsp;
          ${p.features.days_until_deadline.toFixed(1)}d remaining &nbsp;|&nbsp;
          ${p.features.hours_per_day_required.toFixed(1)}h/day required &nbsp;|&nbsp;
          Utilization: ${(p.features.utilization_rate * 100).toFixed(0)}%
        </div>
        <div class="risk-bar-wrap">
          <div class="risk-bar-bg">
            <div class="risk-bar-fill ${p.risk_level}" style="width:${(p.risk_score*100).toFixed(1)}%"></div>
          </div>
        </div>
      </div>
    `).join("");
}

// ── Render: Schedule ───────────────────────────────────────────────────────
function renderSchedule({ schedule, unscheduled, total_days_used, summary: sum }) {
  const summaryEl     = document.getElementById("schedule-summary");
  const gridEl        = document.getElementById("schedule-grid");
  const unschedEl     = document.getElementById("unscheduled-list");

  summaryEl.innerHTML = `
    <div class="stat-block">
      <div class="stat-label">Scheduled Tasks</div>
      <div class="stat-value ok">${sum.scheduled_count}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Unscheduled</div>
      <div class="stat-value ${sum.unscheduled_count > 0 ? "bad" : "ok"}">${sum.unscheduled_count}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Working Days Used</div>
      <div class="stat-value">${total_days_used}</div>
    </div>
    <div class="stat-block">
      <div class="stat-label">Schedule Slots</div>
      <div class="stat-value">${sum.total_slots}</div>
    </div>
  `;

  // Group slots by date
  const byDay = {};
  for (const slot of schedule) {
    (byDay[slot.date] = byDay[slot.date] || []).push(slot);
  }

  gridEl.innerHTML = Object.keys(byDay).sort().map(date => {
    const slots = byDay[date];
    const totalHours = slots.reduce((s, sl) => s + sl.hours_assigned, 0);
    return `
      <div class="schedule-day">
        <div class="schedule-day-header">📅 ${new Date(date + "T12:00:00Z").toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"})} — ${totalHours.toFixed(1)}h</div>
        <div class="schedule-day-slots">
          ${slots.map(sl => `
            <div class="schedule-slot">
              <span>${escHtml(sl.task_title)} <small style="color:var(--color-muted)">(P${sl.priority})</small></span>
              <span class="schedule-slot-hours">${sl.hours_assigned}h</span>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");

  if (unscheduled.length === 0) {
    unschedEl.innerHTML = '<div class="result-card severity-low"><div class="result-card-title">✅ All tasks scheduled successfully</div></div>';
  } else {
    unschedEl.innerHTML = `<h4 style="margin:.5rem 0;color:var(--color-danger)">⚠️ Unscheduled Tasks</h4>` +
      unscheduled.map(u => `
        <div class="result-card unscheduled">
          <div class="result-card-title">${escHtml(u.task_title)}</div>
          <div class="result-card-body">${escHtml(u.reason)} (${u.hours_unscheduled}h remaining)</div>
        </div>
      `).join("");
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
setMinDeadline();
renderTasks();
