const linkInput = document.getElementById("linkInput");
const convertBtn = document.getElementById("convertBtn");
const copyBtn = document.getElementById("copyBtn");
const addressOutput = document.getElementById("addressOutput");
const resultSection = document.getElementById("resultSection");
const suggestionsSection = document.getElementById("suggestionsSection");
const suggestionsList = document.getElementById("suggestionsList");
const mapSection = document.getElementById("mapSection");
const mapPreview = document.getElementById("mapPreview");
const errorText = document.getElementById("errorText");
const statusText = document.getElementById("statusText");

let latestAddress = "";

function updateMapPreview(address) {
  const mapQuery = encodeURIComponent(address.replace(/\n/g, ", "));
  mapPreview.src = `https://www.google.com/maps?q=${mapQuery}&output=embed`;
  mapSection.classList.remove("hidden");
}

function setActiveAddress(address, sourceElement = null) {
  latestAddress = address;
  addressOutput.textContent = address;
  updateMapPreview(address);

  const options = suggestionsList.querySelectorAll(".suggestion-item");
  options.forEach((item) => item.classList.remove("active"));
  if (sourceElement) {
    sourceElement.classList.add("active");
  }
}

function setLoading(isLoading) {
  convertBtn.disabled = isLoading;
  convertBtn.textContent = isLoading ? "Converting..." : "Convert";
  statusText.textContent = isLoading ? "Resolving and fetching address..." : "";
}

function showError(message) {
  errorText.textContent = message;
  resultSection.classList.add("hidden");
  mapSection.classList.add("hidden");
  suggestionsSection.classList.add("hidden");
  suggestionsList.innerHTML = "";
}

function clearError() {
  errorText.textContent = "";
}

function renderSuggestions(address, suggestions) {
  suggestionsList.innerHTML = "";

  if (!Array.isArray(suggestions) || suggestions.length === 0) {
    suggestionsSection.classList.add("hidden");
    return;
  }

  const filtered = suggestions.filter((item) => item && item !== address);
  if (filtered.length === 0) {
    suggestionsSection.classList.add("hidden");
    return;
  }

  for (const item of filtered.slice(0, 3)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion-item";
    button.textContent = item;
    button.addEventListener("click", () => {
      setActiveAddress(item, button);
      statusText.textContent = "Using selected suggestion.";
      setTimeout(() => {
        if (statusText.textContent === "Using selected suggestion.") {
          statusText.textContent = "";
        }
      }, 1200);
    });
    suggestionsList.appendChild(button);
  }

  suggestionsSection.classList.remove("hidden");
}

function renderSuccess(address, suggestions = []) {
  setActiveAddress(address);
  resultSection.classList.remove("hidden");
  renderSuggestions(address, suggestions);
}

async function convertLink() {
  const link = linkInput.value.trim();

  if (!link) {
    showError("Please enter a Google Maps link or coordinates.");
    return;
  }

  clearError();
  setLoading(true);
  suggestionsSection.classList.add("hidden");
  suggestionsList.innerHTML = "";

  try {
    const response = await fetch("/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link })
    });

    const payload = await response.json().catch(() => ({
      status: "error",
      message: "Unexpected response from server."
    }));

    if (!response.ok || payload.status !== "success") {
      throw new Error(payload.message || "Failed to convert the provided link.");
    }

    renderSuccess(payload.address, payload.suggestions || []);
  } catch (error) {
    showError(error.message || "Something went wrong.");
  } finally {
    setLoading(false);
  }
}

async function copyAddress() {
  if (!latestAddress) {
    return;
  }

  const originalText = copyBtn.textContent;
  try {
    await navigator.clipboard.writeText(latestAddress);
    copyBtn.textContent = "Copied";
  } catch (err) {
    copyBtn.textContent = "Copy failed";
  }

  setTimeout(() => {
    copyBtn.textContent = originalText;
  }, 1200);
}

convertBtn.addEventListener("click", convertLink);
copyBtn.addEventListener("click", copyAddress);

linkInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    convertLink();
  }
});
