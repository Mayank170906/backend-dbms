import { api } from "/static/js/api.js";

if (api.isAuthenticated()) {
  window.location.href = "/";
}

const form = document.getElementById("login-form");
const errorEl = document.getElementById("form-error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.classList.add("hidden");
  const formData = new FormData(form);
  try {
    await api.login(formData.get("username"), formData.get("password"));
    window.location.href = "/";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  }
});
