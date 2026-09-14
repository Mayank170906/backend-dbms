import { api } from "/static/js/api.js";

api.requireAuth();

const orgId = window.location.pathname.match(/\/organizations\/(\d+)\//)[1];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

async function loadOrganization() {
  const org = await api.get(`/organizations/${orgId}/`);
  document.getElementById("org-name").textContent = org.name;
  document.getElementById("org-description").textContent = org.description || "";
}

async function loadProjects() {
  const data = await api.get(`/projects/?organization=${orgId}`);
  const list = document.getElementById("project-list");
  const empty = document.getElementById("project-empty");
  list.innerHTML = "";
  empty.classList.toggle("hidden", data.results.length > 0);
  for (const project of data.results) {
    const card = document.createElement("a");
    card.href = `/projects/${project.id}/`;
    card.className = "block border border-gray-200 rounded p-3 hover:border-indigo-300";
    card.innerHTML = `
      <div class="font-medium">${escapeHtml(project.name)}</div>
      <div class="text-xs text-gray-500 mt-1">${escapeHtml(project.status)}</div>
    `;
    list.appendChild(card);
  }
}

async function loadTeams() {
  const data = await api.get(`/teams/?organization=${orgId}`);
  const list = document.getElementById("team-list");
  const empty = document.getElementById("team-empty");
  list.innerHTML = "";
  empty.classList.toggle("hidden", data.results.length > 0);
  for (const team of data.results) {
    const li = document.createElement("li");
    li.className = "py-2";
    li.innerHTML = `<span class="font-medium">${escapeHtml(team.name)}</span>
      <span class="text-gray-500"> — ${escapeHtml(team.description || "no description")}</span>`;
    list.appendChild(li);
  }
}

async function loadMembers() {
  const data = await api.get(`/organizations/${orgId}/members/`);
  const list = document.getElementById("member-list");
  list.innerHTML = "";
  for (const membership of data.results) {
    const li = document.createElement("li");
    li.className = "py-2 flex items-center justify-between";
    li.innerHTML = `
      <span>${escapeHtml(membership.user.username)}</span>
      <span class="text-xs uppercase text-gray-500">${escapeHtml(membership.role)}</span>
    `;
    list.appendChild(li);
  }
}

function wireToggle(btnId, formId, cancelId) {
  const form = document.getElementById(formId);
  document.getElementById(btnId).addEventListener("click", () => form.classList.toggle("hidden"));
  document.getElementById(cancelId).addEventListener("click", () => {
    form.classList.add("hidden");
    form.reset();
  });
}

wireToggle("new-project-btn", "new-project-form", "cancel-new-project");
wireToggle("new-team-btn", "new-team-form", "cancel-new-team");

document.getElementById("new-project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("new-project-error");
  errorEl.classList.add("hidden");
  const formData = new FormData(event.target);
  try {
    await api.post("/projects/", {
      organization: Number(orgId),
      name: formData.get("name"),
      description: formData.get("description"),
    });
    event.target.reset();
    event.target.classList.add("hidden");
    await loadProjects();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

document.getElementById("new-team-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("new-team-error");
  errorEl.classList.add("hidden");
  const formData = new FormData(event.target);
  try {
    await api.post("/teams/", {
      organization: Number(orgId),
      name: formData.get("name"),
      description: formData.get("description"),
    });
    event.target.reset();
    event.target.classList.add("hidden");
    await loadTeams();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
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
    if (!user) {
      throw new Error(`No user found with username "${username}".`);
    }
    await api.post(`/organizations/${orgId}/members/`, { user_id: user.id, role });
    document.getElementById("invite-form").reset();
    await loadMembers();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});

loadOrganization();
loadProjects();
loadTeams();
loadMembers();
