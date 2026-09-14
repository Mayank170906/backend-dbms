import { api } from "/static/js/api.js";

let notifSocket = null;

async function refreshBadge() {
  const badge = document.getElementById("notif-badge");
  if (!badge) return;
  try {
    const data = await api.get("/notifications/");
    const unread = data.results.filter((n) => !n.is_read).length;
    if (unread > 0) {
      badge.textContent = unread > 9 ? "9+" : String(unread);
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  } catch {
    // Nav renders regardless of whether the notification count loads.
  }
}

function connectNotificationSocket() {
  notifSocket = new WebSocket(api.wsUrl("/ws/notifications/"));
  notifSocket.onmessage = () => refreshBadge();
  // No reconnect loop: a dropped socket just means the badge stops
  // live-updating until the next page load, which still calls
  // refreshBadge() once on its own — an acceptable degrade for a nav
  // widget, not worth a backoff/retry implementation here.
}

export async function initNav() {
  const authSection = document.getElementById("nav-auth");
  const notifLink = document.getElementById("notif-link");
  const searchForm = document.getElementById("nav-search-form");

  if (!api.isAuthenticated()) {
    if (notifLink) notifLink.classList.add("hidden");
    if (searchForm) searchForm.classList.add("hidden");
    if (authSection) authSection.innerHTML = '<a href="/login/" class="hover:underline">Log in</a>';
    return;
  }

  if (authSection) {
    authSection.innerHTML = '<button id="logout-btn" class="hover:underline">Log out</button>';
    document.getElementById("logout-btn").addEventListener("click", () => api.logout());
  }

  if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const q = document.getElementById("nav-search-input").value.trim();
      window.location.href = `/search/?q=${encodeURIComponent(q)}`;
    });
  }

  await refreshBadge();
  connectNotificationSocket();
}
