const API_BASE = localStorage.getItem("competitionAnalyzerApi") || "http://127.0.0.1:5000";

const state = {
  dashboard: null,
  charts: {},
};

const colors = ["#2563eb", "#0f766e", "#d97706", "#e11d48", "#7c3aed", "#0891b2"];

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
}

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function renderMetrics(metrics) {
  byId("trackedCompetitors").textContent = metrics.tracked_competitors;
  byId("averagePrice").textContent = money(metrics.average_price);
  byId("demandIndex").textContent = metrics.demand_index;
  byId("openAlerts").textContent = metrics.open_alerts;
  byId("biggestDrop").textContent = `Largest price drop ${metrics.biggest_price_drop}%`;
}

function resetChart(key, elementId, config) {
  if (state.charts[key]) {
    state.charts[key].destroy();
  }
  state.charts[key] = new Chart(byId(elementId), config);
}

function renderCharts(charts) {
  resetChart("prices", "priceChart", {
    type: "line",
    data: {
      labels: charts.price_labels,
      datasets: charts.price_series.map((series, index) => ({
        label: series.name,
        data: series.data,
        borderColor: colors[index % colors.length],
        backgroundColor: `${colors[index % colors.length]}22`,
        borderWidth: 3,
        tension: 0.35,
        pointRadius: 4,
      })),
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "bottom" } },
      scales: {
        y: { ticks: { callback: (value) => `$${value}` }, grid: { color: "#e7edf5" } },
        x: { grid: { display: false } },
      },
    },
  });

  resetChart("share", "shareChart", {
    type: "doughnut",
    data: {
      labels: charts.share_labels,
      datasets: [{ data: charts.share_values, backgroundColor: colors, borderWidth: 0 }],
    },
    options: {
      cutout: "62%",
      plugins: { legend: { position: "bottom" } },
    },
  });

  resetChart("demand", "demandChart", {
    type: "bar",
    data: {
      labels: charts.demand_labels,
      datasets: [{ label: "Demand", data: charts.demand_values, backgroundColor: "#0f766e", borderRadius: 8 }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: "#e7edf5" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderCompetitors(competitors) {
  byId("competitorRows").innerHTML = competitors.map((competitor) => `
    <tr>
      <td>
        <div class="company-cell">
          <strong>${escapeHtml(competitor.name)}</strong>
          <small>${escapeHtml(competitor.category)}</small>
        </div>
      </td>
      <td>${escapeHtml(competitor.region)}</td>
      <td>${money(competitor.current_price)}</td>
      <td><span class="score-pill">${competitor.product_score}/100</span></td>
      <td>${Number(competitor.growth_rate || 0)}%</td>
    </tr>
  `).join("");
}

function renderSignals(signals) {
  byId("signalList").innerHTML = signals.map((signal) => `
    <div class="signal-item">
      <div>
        <strong>${escapeHtml(signal.area)}</strong>
        <span>${escapeHtml(signal.category)} · ${escapeHtml(signal.trend)}</span>
      </div>
      <span class="score-pill">${signal.demand}</span>
    </div>
  `).join("");
}

function renderAlerts(alerts) {
  byId("alertList").innerHTML = alerts.map((alert) => `
    <article class="alert-item">
      <span class="alert-severity">${escapeHtml(alert.severity)}</span>
      <strong>${escapeHtml(alert.title)}</strong>
      <p>${escapeHtml(alert.message)}</p>
    </article>
  `).join("");
}

function renderRecommendations(payload) {
  byId("recommendationSource").textContent = payload.source;
  byId("aiNote").textContent = payload.note || "";
  byId("recommendationGrid").innerHTML = payload.items.map((item) => `
    <article class="recommendation-card">
      <span class="priority-pill ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <p>${escapeHtml(item.recommendation)}</p>
    </article>
  `).join("");
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    byId("healthStatus").textContent = "Online";
    byId("storeName").textContent = `${health.store} connected`;
  } catch (error) {
    byId("healthStatus").textContent = "Offline";
    byId("storeName").textContent = "Start Flask backend on port 5000";
  }
}

async function loadDashboard() {
  const dashboard = await api("/api/dashboard");
  state.dashboard = dashboard;
  renderMetrics(dashboard.metrics);
  renderCharts(dashboard.charts);
  renderCompetitors(dashboard.competitors);
  renderSignals(dashboard.market_signals);
  renderAlerts(dashboard.alerts);
}

async function loadRecommendations() {
  byId("aiButton").disabled = true;
  byId("aiButton").textContent = "Generating...";
  try {
    renderRecommendations(await api("/api/recommendations"));
  } finally {
    byId("aiButton").disabled = false;
    byId("aiButton").textContent = "Generate AI Strategy";
  }
}

async function submitCompetitor(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    await api("/api/competitors", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    byId("formMessage").textContent = "Competitor added and dashboard refreshed.";
    await loadDashboard();
  } catch (error) {
    byId("formMessage").textContent = error.message;
  }
}

async function boot() {
  byId("refreshButton").addEventListener("click", async () => {
    await loadHealth();
    await loadDashboard();
  });
  byId("aiButton").addEventListener("click", loadRecommendations);
  byId("competitorForm").addEventListener("submit", submitCompetitor);

  await loadHealth();
  await loadDashboard();
  await loadRecommendations();
}

boot().catch((error) => {
  console.error(error);
  byId("healthStatus").textContent = "Offline";
  byId("storeName").textContent = error.message;
});
