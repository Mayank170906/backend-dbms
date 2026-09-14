import { api } from "/static/js/api.js";

api.requireAuth();

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderList(listId, emptyId, items, renderItem) {
  const list = document.getElementById(listId);
  const empty = document.getElementById(emptyId);
  empty.classList.toggle("hidden", items.length > 0);
  list.innerHTML = items.map(renderItem).join("");
}

async function runSearch() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q") || "";
  document.getElementById("search-query").textContent = q;
  if (!q) return;

  const results = await api.get(`/search/?q=${encodeURIComponent(q)}`);

  renderList(
    "search-projects",
    "search-projects-empty",
    results.projects,
    (p) => `<li class="p-3"><a class="text-indigo-600 hover:underline" href="/projects/${p.id}/">${escapeHtml(p.name)}</a>
      <div class="text-xs text-gray-500">${escapeHtml(p.description || "")}</div></li>`
  );

  renderList(
    "search-tasks",
    "search-tasks-empty",
    results.tasks,
    (t) => `<li class="p-3"><a class="text-indigo-600 hover:underline" href="/projects/${t.project}/">${escapeHtml(t.title)}</a>
      <div class="text-xs text-gray-500">${escapeHtml(t.description || "")}</div></li>`
  );

  renderList(
    "search-comments",
    "search-comments-empty",
    results.comments,
    (c) => `<li class="p-3">${escapeHtml(c.body)}
      <div class="text-xs text-gray-500">by ${escapeHtml(c.author_detail ? c.author_detail.username : "unknown")}</div></li>`
  );
}

runSearch();
