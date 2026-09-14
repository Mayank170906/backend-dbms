import { api } from "/static/js/api.js";

if (api.isAuthenticated()) {
  window.location.href = "/";
}

const form = document.getElementById("register-form");
const errorEl = document.getElementById("form-error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.classList.add("hidden");
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  try {
    await api.register(payload);
    await api.login(payload.username, payload.password);
    window.location.href = "/";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});
