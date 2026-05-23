/**
 * LLM Gateway — Admin Dashboard JS
 * Polls /api/providers every 10 s and updates the UI.
 */

const POLL_INTERVAL = 10_000;

async function fetchStatus() {
  try {
    const res = await fetch("/api/providers");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch provider status:", err);
    return null;
  }
}

function render(data) {
  if (!data) {
    setGatewayStatus(false);
    return;
  }

  const { configured, all_providers, circuits, cors_origin } = data;
  const configuredSet = new Set(configured);

  // Gateway status
  setGatewayStatus(true);

  // Stat cards
  document.getElementById("stat-configured").textContent = configured.length;
  document.getElementById("stat-total").textContent = all_providers.length;
  document.getElementById("stat-cors").textContent = cors_origin || "*";

  // Count healthy circuits (only among configured)
  let healthy = 0;
  for (const name of configured) {
    if (circuits[name] && circuits[name].state === "CLOSED") healthy++;
  }
  document.getElementById("stat-healthy").textContent = `${healthy}/${configured.length}`;

  // Provider grid
  const grid = document.getElementById("provider-grid");
  grid.innerHTML = "";

  for (const name of all_providers) {
    const isConfigured = configuredSet.has(name);
    const circuit = circuits[name];

    const card = document.createElement("div");
    card.className = `provider-card${isConfigured ? " configured" : ""}`;

    const statusIcon = isConfigured ? "✅" : "❌";

    let circuitHTML = "";
    if (isConfigured && circuit) {
      const reopenNote =
        circuit.state === "OPEN" && circuit.reopens_in_secs > 0
          ? ` · reopens in ${circuit.reopens_in_secs}s`
          : "";
      circuitHTML = `
        <div class="circuit-info">
          <span class="circuit-dot ${circuit.state}"></span>
          ${circuit.state}${reopenNote}
        </div>`;
    } else if (!isConfigured) {
      circuitHTML = `<div class="circuit-info" style="color:var(--text-muted)">no key set</div>`;
    }

    card.innerHTML = `
      <div class="provider-name">
        <span class="provider-status-icon">${statusIcon}</span>
        ${name}
      </div>
      ${circuitHTML}`;

    grid.appendChild(card);
  }
}

function setGatewayStatus(healthy) {
  const dot = document.getElementById("gateway-status-dot");
  const badge = document.getElementById("gateway-status-badge");

  dot.className = `logo ${healthy ? "healthy" : "unhealthy"}`;
  badge.className = `badge ${healthy ? "healthy" : "unhealthy"}`;
  badge.textContent = healthy ? "operational" : "unreachable";
}

// Initial load + polling
(async function init() {
  render(await fetchStatus());
  setInterval(async () => render(await fetchStatus()), POLL_INTERVAL);
})();
