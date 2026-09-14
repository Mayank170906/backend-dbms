import { api } from "/static/js/api.js";

api.requireAuth();

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

async function loadNotifications() {
  const data = await api.get("/notifications/");
  const list = document.getElementById("notification-list");
  const empty = document.getElementById("notification-empty");
  empty.classList.toggle("hidden", data.results.length > 0);
  list.innerHTML = "";
  for (const notification of data.results) {
    const li = document.createElement("li");
    li.className = `p-3 flex items-start justify-between gap-3 ${notification.is_read ? "" : "bg-indigo-50"}`;
    li.innerHTML = `
      <div>
        <div>${escapeHtml(notification.message)}</div>
        <div class="text-xs text-gray-400 mt-1">${new Date(notification.created_at).toLocaleString()}</div>
      </div>
    `;
    if (!notification.is_read) {
      const btn = document.createElement("button");
      btn.className = "text-xs text-indigo-600 hover:underline whitespace-nowrap";
      btn.textContent = "Mark read";
      btn.addEventListener("click", async () => {
        await api.post(`/notifications/${notification.id}/read/`);
        await loadNotifications();
      });
      li.appendChild(btn);
    }
    list.appendChild(li);
  }
}

document.getElementById("mark-all-btn").addEventListener("click", async () => {
  await api.post("/notifications/read-all/");
  await loadNotifications();
});

loadNotifications();
