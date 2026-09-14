import { api } from "/static/js/api.js";

api.requireAuth();

const projectId = window.location.pathname.match(/\/projects\/(\d+)\//)[1];

let project = null;
let workflow = null; // full workflow object (states, transitions) or null
let tasksById = new Map();
let currentTaskId = null;
let activitySocket = null;

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

async function fetchAllPages(initialPath) {
  let path = initialPath;
  const results = [];
  while (path) {
    const data = await api.get(path);
    results.push(...data.results);
    if (!data.next) break;
    const url = new URL(data.next);
    path = url.pathname.replace(/^\/api\/v1/, "") + url.search;
  }
  return results;
}

// ---------- Tabs ----------

function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("border-indigo-600", "font-medium", "text-gray-800"));
      buttons.forEach((b) => b.classList.add("border-transparent", "text-gray-500"));
      btn.classList.add("border-indigo-600", "font-medium");
      btn.classList.remove("border-transparent", "text-gray-500");
      document.querySelectorAll("[id^='tab-']").forEach((el) => el.classList.add("hidden"));
      document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("hidden");
      if (btn.dataset.tab === "activity") loadActivity();
      if (btn.dataset.tab === "workflow") loadWorkflowTab();
      if (btn.dataset.tab === "statistics") loadStatistics();
    });
  });
}

// ---------- Project header + members ----------

async function loadProject() {
  project = await api.get(`/projects/${projectId}/`);
  document.getElementById("project-name").textContent = project.name;
  document.getElementById("project-description").textContent = project.description || "";
  document.getElementById("org-link").href = `/organizations/${project.organization}/`;
}

async function loadMembers() {
  const data = await api.get(`/projects/${projectId}/members/`);
  const list = document.getElementById("member-list");
  list.innerHTML = "";
  for (const membership of data.results) {
    const li = document.createElement("li");
    li.className = "py-2 flex items-center justify-between";
    li.innerHTML = `<span>${escapeHtml(membership.user.username)}</span>
      <span class="text-xs uppercase text-gray-500">${escapeHtml(membership.role)}</span>`;
    list.appendChild(li);
  }
}

document.getElementById("members-btn").addEventListener("click", () => {
  document.getElementById("members-panel").classList.toggle("hidden");
});

document.getElementById("invite-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("invite-error");
  errorEl.classList.add("hidden");
  const username = document.getElementById("invite-username").value.trim();
  const role = document.getElementById("invite-role").value;
  try {
    const matches = await api.get(`/users/?search=${encodeURIComponent(username)}`);
    const user = matches.results.find((u) => u.username === username);
    if (!user) throw new Error(`No user found with username "${username}".`);
    await api.post(`/projects/${projectId}/members/`, { user_id: user.id, role });
    document.getElementById("invite-form").reset();
    await loadMembers();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

// ---------- Board (Kanban) ----------

async function loadWorkflow() {
  if (!project.workflow) {
    workflow = null;
    return;
  }
  workflow = await api.get(`/workflows/${project.workflow}/`);
}

function stateName(stateId) {
  if (!workflow || stateId === null) return "Unassigned";
  const state = workflow.states.find((s) => s.id === stateId);
  return state ? state.name : "Unknown";
}

function renderBoard() {
  const board = document.getElementById("kanban-board");
  const notice = document.getElementById("no-workflow-notice");
  board.innerHTML = "";
  notice.classList.toggle("hidden", !!workflow);

  const columns = [];
  if (workflow) {
    columns.push(...[...workflow.states].sort((a, b) => a.order - b.order).map((s) => ({ id: s.id, name: s.name })));
  }
  columns.unshift({ id: null, name: "Unassigned" });

  for (const column of columns) {
    const columnEl = document.createElement("div");
    columnEl.className = "kanban-column";
    columnEl.dataset.stateId = column.id === null ? "" : column.id;
    const tasksInColumn = [...tasksById.values()].filter((t) => t.workflow_state === column.id);
    columnEl.innerHTML = `
      <h3 class="font-medium text-sm mb-2 flex items-center justify-between">
        ${escapeHtml(column.name)}
        <span class="text-xs text-gray-400">${tasksInColumn.length}</span>
      </h3>
      <div class="space-y-2 cards"></div>
    `;
    const cardsEl = columnEl.querySelector(".cards");
    for (const task of tasksInColumn) {
      cardsEl.appendChild(renderCard(task));
    }
    if (column.id !== null || workflow) {
      // Unassigned only accepts drops when it's meaningless (no target
      // state), so it's the one column that isn't a drop target.
    }
    wireColumnDrop(columnEl, column.id);
    board.appendChild(columnEl);
  }
}

function renderCard(task) {
  const card = document.createElement("div");
  card.className = "kanban-card bg-white rounded shadow-sm p-3 text-sm";
  card.draggable = true;
  card.dataset.taskId = task.id;
  const priorityColor = { LOW: "bg-gray-200", MEDIUM: "bg-blue-200", HIGH: "bg-orange-200", CRITICAL: "bg-red-200" };
  card.innerHTML = `
    <div class="font-medium">${escapeHtml(task.title)}</div>
    <div class="flex items-center justify-between mt-2">
      <span class="text-xs px-1.5 py-0.5 rounded ${priorityColor[task.priority] || "bg-gray-200"}">${escapeHtml(task.priority)}</span>
      <span class="text-xs text-gray-500">${task.assignees_detail.map((u) => escapeHtml(u.username)).join(", ")}</span>
    </div>
  `;
  card.addEventListener("dragstart", () => {
    card.classList.add("dragging");
    card.dataset.dragging = "true";
  });
  card.addEventListener("dragend", () => card.classList.remove("dragging"));
  card.addEventListener("click", () => openTaskPanel(task.id));
  return card;
}

function wireColumnDrop(columnEl, stateId) {
  if (stateId === null) return; // no transition target for "unassigned"
  columnEl.addEventListener("dragover", (event) => {
    event.preventDefault();
    columnEl.classList.add("drag-over");
  });
  columnEl.addEventListener("dragleave", () => columnEl.classList.remove("drag-over"));
  columnEl.addEventListener("drop", async (event) => {
    event.preventDefault();
    columnEl.classList.remove("drag-over");
    const dragging = document.querySelector(".kanban-card.dragging");
    if (!dragging) return;
    const taskId = dragging.dataset.taskId;
    try {
      const updated = await api.post(`/tasks/${taskId}/transition/`, { to_state_id: stateId });
      tasksById.set(updated.id, updated);
      renderBoard();
    } catch (err) {
      // The backend is the sole authority on legal transitions (Phase 4) —
      // an illegal drop is expected to be rejected, not prevented client
      // side, so this just reports it and leaves the board as-is.
      alert(`Couldn't move task: ${err.message}`);
    }
  });
}

async function loadTasks() {
  const list = await fetchAllPages(`/tasks/?project=${projectId}`);
  tasksById = new Map(list.map((t) => [t.id, t]));
  renderBoard();
}

document.getElementById("new-task-btn").addEventListener("click", () => {
  document.getElementById("new-task-form").classList.toggle("hidden");
});
document.getElementById("cancel-new-task").addEventListener("click", (event) => {
  event.target.closest("form").classList.add("hidden");
});

document.getElementById("new-task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("new-task-error");
  errorEl.classList.add("hidden");
  const formData = new FormData(event.target);
  const payload = {
    project: Number(projectId),
    title: formData.get("title"),
    description: formData.get("description"),
    priority: formData.get("priority"),
  };
  if (formData.get("due_date")) payload.due_date = formData.get("due_date");
  if (formData.get("estimated_hours")) payload.estimated_hours = formData.get("estimated_hours");
  try {
    const task = await api.post("/tasks/", payload);
    tasksById.set(task.id, task);
    renderBoard();
    event.target.reset();
    event.target.classList.add("hidden");
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

// ---------- Task detail panel ----------

async function openTaskPanel(taskId) {
  currentTaskId = taskId;
  const task = await api.get(`/tasks/${taskId}/`);
  tasksById.set(task.id, task);

  document.getElementById("task-title").textContent = task.title;
  document.getElementById("task-description").textContent = task.description || "(no description)";
  document.getElementById("task-priority").textContent = task.priority;
  document.getElementById("task-due-date").textContent = task.due_date || "—";
  document.getElementById("task-estimated-hours").textContent = task.estimated_hours ?? "—";
  document.getElementById("task-status").textContent = stateName(task.workflow_state);

  renderTransitionButtons(task);
  renderAssignees(task);
  await renderLabelPicker(task);
  await loadComments(task.id);

  document.getElementById("task-panel").classList.remove("hidden");
  document.getElementById("task-panel-backdrop").classList.remove("hidden");
}

function closeTaskPanel() {
  currentTaskId = null;
  document.getElementById("task-panel").classList.add("hidden");
  document.getElementById("task-panel-backdrop").classList.add("hidden");
}
document.getElementById("task-panel-close").addEventListener("click", closeTaskPanel);
document.getElementById("task-panel-backdrop").addEventListener("click", closeTaskPanel);

function renderTransitionButtons(task) {
  const container = document.getElementById("task-transitions");
  container.innerHTML = "";
  if (!workflow) return;
  let targets;
  if (task.workflow_state === null) {
    targets = workflow.states.filter((s) => s.is_initial).map((s) => ({ id: s.id, name: s.name }));
  } else {
    targets = workflow.transitions
      .filter((t) => t.from_state === task.workflow_state)
      .map((t) => ({ id: t.to_state, name: stateName(t.to_state) }));
  }
  for (const target of targets) {
    const btn = document.createElement("button");
    btn.className = "text-xs border border-gray-300 rounded px-2 py-1 hover:bg-gray-50";
    btn.textContent = `Move to ${target.name}`;
    btn.addEventListener("click", async () => {
      const errorEl = document.getElementById("task-transition-error");
      errorEl.classList.add("hidden");
      try {
        const updated = await api.post(`/tasks/${task.id}/transition/`, { to_state_id: target.id });
        tasksById.set(updated.id, updated);
        renderBoard();
        await openTaskPanel(task.id);
      } catch (err) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
      }
    });
    container.appendChild(btn);
  }
}

function renderAssignees(task) {
  const list = document.getElementById("task-assignees");
  list.innerHTML = task.assignees_detail.length
    ? task.assignees_detail.map((u) => `<li>${escapeHtml(u.username)}</li>`).join("")
    : '<li class="text-gray-400">No assignees yet</li>';
}

document.getElementById("assign-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("assign-error");
  errorEl.classList.add("hidden");
  const username = document.getElementById("assign-username").value.trim();
  try {
    const matches = await api.get(`/users/?search=${encodeURIComponent(username)}`);
    const user = matches.results.find((u) => u.username === username);
    if (!user) throw new Error(`No user found with username "${username}".`);
    const updated = await api.post(`/tasks/${currentTaskId}/assign/`, { user_id: user.id });
    tasksById.set(updated.id, updated);
    renderBoard();
    renderAssignees(updated);
    document.getElementById("assign-form").reset();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/;

async function renderLabelPicker(task) {
  const list = document.getElementById("task-labels");
  // The backend validates label.color as a strict 6-digit hex code
  // (apps/tasks/models.py's hex_color_validator), but this value still
  // gets interpolated into an HTML style attribute below — re-validating
  // here means a relaxed backend constraint, a stale cached label, or any
  // other unexpected source can never turn this into a style/attribute
  // injection.
  const colorFor = (label) => {
    const color = HEX_COLOR_RE.test(label.color) ? label.color : "#6B7280";
    return `background:${color}22;border:1px solid ${color}`;
  };
  const allLabels = await fetchAllPages(`/labels/?project=${projectId}`);
  const currentIds = new Set(task.labels);
  const currentLabels = allLabels.filter((l) => currentIds.has(l.id));
  list.innerHTML = currentLabels
    .map((l) => `<li class="text-xs rounded px-2 py-0.5" style="${colorFor(l)}">${escapeHtml(l.name)}</li>`)
    .join("") || '<li class="text-gray-400 text-sm">No labels</li>';

  const select = document.getElementById("label-select");
  const available = allLabels.filter((l) => !currentIds.has(l.id));
  select.innerHTML = available.map((l) => `<option value="${l.id}">${escapeHtml(l.name)}</option>`).join("");
  document.getElementById("label-form").classList.toggle("hidden", available.length === 0);
}

document.getElementById("label-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const labelId = Number(document.getElementById("label-select").value);
  const task = tasksById.get(currentTaskId);
  const updated = await api.patch(`/tasks/${currentTaskId}/`, { labels: [...task.labels, labelId] });
  tasksById.set(updated.id, updated);
  await renderLabelPicker(updated);
});

async function loadComments(taskId) {
  const comments = await api.get(`/tasks/${taskId}/comments/`);
  const list = document.getElementById("task-comments");
  list.innerHTML = comments.length
    ? comments
        .map(
          (c) => `
      <li class="border border-gray-100 rounded p-2">
        <div class="text-xs text-gray-500">${escapeHtml(c.author_detail ? c.author_detail.username : "unknown")} — ${new Date(c.created_at).toLocaleString()}</div>
        <div>${escapeHtml(c.body)}</div>
      </li>`
        )
        .join("")
    : '<li class="text-gray-400">No comments yet</li>';
}

document.getElementById("comment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = document.getElementById("comment-body").value.trim();
  if (!body) return;
  await api.post(`/tasks/${currentTaskId}/comments/`, { body });
  document.getElementById("comment-body").value = "";
  await loadComments(currentTaskId);
});

// ---------- Activity tab ----------

async function loadActivity() {
  const entries = await fetchAllPages(`/projects/${projectId}/activity/`);
  renderActivityEntries(entries);
  connectActivitySocket();
}

function renderActivityEntries(entries) {
  const list = document.getElementById("activity-list");
  const empty = document.getElementById("activity-empty");
  empty.classList.toggle("hidden", entries.length > 0);
  list.innerHTML = entries
    .map(
      (entry) => `
    <li class="p-3">
      <span class="font-medium">${escapeHtml(entry.actor || "system")}</span>
      <span class="text-gray-600"> ${escapeHtml(entry.action)}</span>
      <span class="text-xs text-gray-400 block">${new Date(entry.created_at).toLocaleString()}</span>
    </li>`
    )
    .join("");
}

function connectActivitySocket() {
  if (activitySocket) return;
  activitySocket = new WebSocket(api.wsUrl(`/ws/projects/${projectId}/`));
  activitySocket.onmessage = (event) => {
    const entry = JSON.parse(event.data);
    const list = document.getElementById("activity-list");
    document.getElementById("activity-empty").classList.add("hidden");
    const li = document.createElement("li");
    li.className = "p-3 bg-indigo-50";
    li.innerHTML = `
      <span class="font-medium">${escapeHtml(entry.actor || "system")}</span>
      <span class="text-gray-600"> ${escapeHtml(entry.action)}</span>
      <span class="text-xs text-gray-400 block">${new Date(entry.created_at).toLocaleString()}</span>`;
    list.prepend(li);
    // A live event usually means a task/board change too — cheapest
    // correct way to reflect it without guessing which task moved.
    loadTasks();
  };
}

// ---------- Workflow tab ----------

async function loadWorkflowTab() {
  document.getElementById("workflow-missing").classList.toggle("hidden", !!project.workflow);
  document.getElementById("workflow-configured").classList.toggle("hidden", !project.workflow);
  if (project.workflow) {
    await loadWorkflow();
    renderWorkflowConfig();
  } else {
    const existing = await fetchAllPages(`/workflows/?organization=${project.organization}`);
    const select = document.getElementById("existing-workflow-select");
    select.innerHTML = existing.map((w) => `<option value="${w.id}">${escapeHtml(w.name)}</option>`).join("");
  }
}

document.getElementById("create-workflow-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("workflow-create-error");
  errorEl.classList.add("hidden");
  const name = new FormData(event.target).get("name");
  try {
    const created = await api.post("/workflows/", { organization: project.organization, name });
    project = await api.patch(`/projects/${projectId}/`, { workflow: created.id });
    await loadWorkflowTab();
    await loadTasks();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

document.getElementById("attach-existing-workflow").addEventListener("click", async () => {
  const workflowId = Number(document.getElementById("existing-workflow-select").value);
  if (!workflowId) return;
  project = await api.patch(`/projects/${projectId}/`, { workflow: workflowId });
  await loadWorkflowTab();
  await loadTasks();
});

function renderWorkflowConfig() {
  document.getElementById("workflow-name").textContent = workflow.name;

  const stateBody = document.getElementById("state-table-body");
  const sortedStates = [...workflow.states].sort((a, b) => a.order - b.order);
  stateBody.innerHTML = sortedStates
    .map(
      (s) => `<tr>
        <td class="py-1">${escapeHtml(s.name)}</td>
        <td>${s.order}</td>
        <td>${s.is_initial ? "✓" : ""}</td>
        <td>${s.is_terminal ? "✓" : ""}</td>
      </tr>`
    )
    .join("");

  const transitionBody = document.getElementById("transition-table-body");
  transitionBody.innerHTML = workflow.transitions
    .map(
      (t) => `<tr>
        <td class="py-1">${escapeHtml(stateName(t.from_state))}</td>
        <td>${escapeHtml(stateName(t.to_state))}</td>
        <td>${t.allowed_roles.length ? escapeHtml(t.allowed_roles.join(", ")) : "any member"}</td>
      </tr>`
    )
    .join("");

  document.querySelectorAll(".state-select").forEach((select) => {
    select.innerHTML = sortedStates.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("");
  });
}

document.getElementById("add-state-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  await api.post(`/workflows/${workflow.id}/states/`, {
    name: formData.get("name"),
    order: Number(formData.get("order")),
    is_initial: formData.get("is_initial") === "on",
    is_terminal: formData.get("is_terminal") === "on",
  });
  event.target.reset();
  await loadWorkflow();
  renderWorkflowConfig();
});

document.getElementById("add-transition-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const roles = formData.getAll("role");
  await api.post(`/workflows/${workflow.id}/transitions/`, {
    from_state: Number(formData.get("from_state")),
    to_state: Number(formData.get("to_state")),
    allowed_roles: roles,
  });
  event.target.reset();
  await loadWorkflow();
  renderWorkflowConfig();
});

// ---------- Statistics tab ----------

const charts = {};

function upsertChart(canvasId, config) {
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart(document.getElementById(canvasId), config);
}

async function loadStatistics() {
  const stats = await api.get(`/projects/${projectId}/statistics/`);

  const tiles = [
    ["Total tasks", stats.total_tasks],
    ["Completed", stats.completed_tasks],
    ["Pending", stats.pending_tasks],
    ["Overdue", stats.overdue_tasks],
  ];
  document.getElementById("stat-tiles").innerHTML = tiles
    .map(
      ([label, value]) => `
    <div class="bg-white rounded shadow p-4 text-center">
      <div class="text-2xl font-semibold">${value}</div>
      <div class="text-xs text-gray-500 mt-1">${label}</div>
    </div>`
    )
    .join("");

  upsertChart("chart-priority", {
    type: "bar",
    data: {
      labels: Object.keys(stats.tasks_by_priority),
      datasets: [{ label: "Tasks by priority", data: Object.values(stats.tasks_by_priority), backgroundColor: "#6366f1" }],
    },
    options: { responsive: true, plugins: { title: { display: true, text: "Tasks by priority" } } },
  });

  upsertChart("chart-status", {
    type: "bar",
    data: {
      labels: Object.keys(stats.tasks_by_status),
      datasets: [{ label: "Tasks by status", data: Object.values(stats.tasks_by_status), backgroundColor: "#0ea5e9" }],
    },
    options: { responsive: true, plugins: { title: { display: true, text: "Tasks by workflow state" } } },
  });

  upsertChart("chart-completed-per-day", {
    type: "line",
    data: {
      labels: Object.keys(stats.tasks_completed_per_day),
      datasets: [{ label: "Completed", data: Object.values(stats.tasks_completed_per_day), borderColor: "#22c55e" }],
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text:
            stats.average_completion_hours !== null
              ? `Tasks completed per day (avg ${stats.average_completion_hours}h to complete)`
              : "Tasks completed per day",
        },
      },
    },
  });

  upsertChart("chart-workload", {
    type: "bar",
    data: {
      labels: Object.keys(stats.workload_by_member),
      datasets: [{ label: "Assigned tasks", data: Object.values(stats.workload_by_member), backgroundColor: "#f59e0b" }],
    },
    options: { responsive: true, indexAxis: "y", plugins: { title: { display: true, text: "Workload by member" } } },
  });
}

// ---------- Boot ----------

async function init() {
  initTabs();
  await loadProject();
  await loadMembers();
  await loadWorkflow();
  await loadTasks();
}

init();
