// Thin fetch wrapper: JWT storage/refresh, one shared error format, and
// nothing else. Every page below calls only `api.*` — none of them touch
// `fetch()`, `localStorage`, or a Django template variable for data, which
// is the point: the frontend consumes the REST API exactly like an
// external client would, not the ORM.

const API_BASE = "/api/v1";
const STORAGE_KEY = "backend_dbms_auth";

function getTokens() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setTokens(tokens) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}

function clearTokens() {
  localStorage.removeItem(STORAGE_KEY);
}

function isAuthenticated() {
  return getTokens() !== null;
}

function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = "/login/";
  }
}

async function refreshAccessToken() {
  const tokens = getTokens();
  if (!tokens || !tokens.refresh) return false;
  const res = await fetch(`${API_BASE}/auth/login/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json();
  setTokens({ access: data.access, refresh: tokens.refresh });
  return true;
}

// Low-level: returns the raw Response. Retries exactly once after a
// refresh on a 401; a second 401 means the refresh token itself is
// invalid/expired/blacklisted, so the session is over.
async function apiFetch(path, options = {}) {
  const tokens = getTokens();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (tokens) headers.Authorization = `Bearer ${tokens.access}`;

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && tokens) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      clearTokens();
      window.location.href = "/login/";
      throw new Error("Session expired");
    }
    const freshTokens = getTokens();
    headers.Authorization = `Bearer ${freshTokens.access}`;
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  }
  return res;
}

function formatApiError(data) {
  if (!data) return "Something went wrong.";
  const detail = data.error ? data.error.detail : data;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    return Object.entries(detail)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(", ") : messages}`)
      .join(" — ");
  }
  return "Something went wrong.";
}

// High-level: parses JSON and throws a plain Error with a readable message
// on a non-2xx response, so callers can just `try { await api.get(...) }`.
async function apiJson(path, options = {}) {
  const res = await apiFetch(path, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(formatApiError(data));
  }
  return data;
}

function get(path) {
  return apiJson(path);
}

function post(path, body) {
  return apiJson(path, { method: "POST", body: JSON.stringify(body ?? {}) });
}

function patch(path, body) {
  return apiJson(path, { method: "PATCH", body: JSON.stringify(body ?? {}) });
}

function del(path) {
  return apiJson(path, { method: "DELETE" });
}

async function login(username, password) {
  const data = await apiJson("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) });
  setTokens({ access: data.access, refresh: data.refresh });
}

async function register(payload) {
  return apiJson("/auth/register/", { method: "POST", body: JSON.stringify(payload) });
}

async function logout() {
  const tokens = getTokens();
  if (tokens) {
    try {
      await apiJson("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh: tokens.refresh }) });
    } catch {
      // Refresh token may already be expired/blacklisted — logging out
      // client-side still has to succeed either way.
    }
  }
  clearTokens();
  window.location.href = "/login/";
}

function wsUrl(path) {
  const tokens = getTokens();
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const token = tokens ? `?token=${encodeURIComponent(tokens.access)}` : "";
  return `${scheme}://${window.location.host}${path}${token}`;
}

export const api = {
  getTokens,
  isAuthenticated,
  requireAuth,
  get,
  post,
  patch,
  delete: del,
  login,
  register,
  logout,
  wsUrl,
  formatApiError,
};
