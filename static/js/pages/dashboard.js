import { api } from "/static/js/api.js";

api.requireAuth();

const orgList = document.getElementById("org-list");
const orgEmpty = document.getElementById("org-empty");
const newOrgBtn = document.getElementById("new-org-btn");
const newOrgForm = document.getElementById("new-org-form");
const cancelNewOrg = document.getElementById("cancel-new-org");
const newOrgError = document.getElementById("new-org-error");

function renderOrganizations(orgs) {
  orgList.innerHTML = "";
  orgEmpty.classList.toggle("hidden", orgs.length > 0);
  for (const org of orgs) {
    const card = document.createElement("a");
    card.href = `/organizations/${org.id}/`;
    card.className = "block bg-white rounded shadow p-4 hover:shadow-md transition-shadow";
    card.innerHTML = `
      <h2 class="font-semibold text-lg">${escapeHtml(org.name)}</h2>
      <p class="text-sm text-gray-500 mt-1">${escapeHtml(org.description || "No description")}</p>
    `;
    orgList.appendChild(card);
  }
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

async function loadOrganizations() {
  const data = await api.get("/organizations/");
  renderOrganizations(data.results);
}

newOrgBtn.addEventListener("click", () => {
  newOrgForm.classList.toggle("hidden");
});
cancelNewOrg.addEventListener("click", () => {
  newOrgForm.classList.add("hidden");
  newOrgForm.reset();
});

newOrgForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  newOrgError.classList.add("hidden");
  const formData = new FormData(newOrgForm);
  try {
    await api.post("/organizations/", {
      name: formData.get("name"),
      description: formData.get("description"),
    });
    newOrgForm.reset();
    newOrgForm.classList.add("hidden");
    await loadOrganizations();
  } catch (err) {
    newOrgError.textContent = err.message;
    newOrgError.classList.remove("hidden");
  }
});

loadOrganizations();
