const isLocalHost = ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
const API_BASE =
  localStorage.getItem("competitionAnalyzerApi") ||
  window.COMPETITION_ANALYZER_API ||
  (isLocalHost ? "http://127.0.0.1:5000" : "");

const state = {
  dashboard: null,
  analysis: null,
  battlecard: null,
  charts: {},
  competitorFilter: "",
};

const colors = ["#2563eb", "#0f766e", "#d97706", "#e11d48", "#0891b2", "#475569"];

function byId(id) {
  return document.getElementById(id);
}

function renderIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function money(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
}

function number(value) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value || 0);
}

function percent(value) {
  return `${Number(value || 0).toFixed(1).replace(".0", "")}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const sampleBusiness = {
  business_name: "Nova Retail AI",
  category: "Retail Analytics",
  region: "North America",
  price: "179",
  product_score: "82",
  target_customer: "mid-market retailers",
  advantage: "faster deployment and simple dashboards",
  objective: "Find the best competitive position for market entry",
};

function showSystemMessage(message, tone = "info") {
  const element = byId("systemMessage");
  element.textContent = message || "";
  element.dataset.tone = tone;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) {
    return;
  }
  if (isLoading) {
    button.dataset.label = button.textContent.trim();
    button.disabled = true;
    button.querySelector("span").textContent = loadingText;
  } else {
    button.disabled = false;
    if (button.dataset.label && button.querySelector("span")) {
      button.querySelector("span").textContent = button.dataset.label;
    }
  }
}

function renderMetrics(metrics) {
  byId("trackedCompetitors").textContent = metrics.tracked_competitors;
  byId("averagePrice").textContent = money(metrics.average_price);
  byId("demandIndex").textContent = metrics.demand_index;
  byId("openAlerts").textContent = metrics.open_alerts;
  byId("biggestDrop").textContent = `Largest price drop ${metrics.biggest_price_drop}%`;
}

function renderInsights(dashboard) {
  const competitors = dashboard.competitors || [];
  const signals = dashboard.market_signals || [];
  const topGrowth = [...competitors].sort((a, b) => Number(b.growth_rate || 0) - Number(a.growth_rate || 0))[0];
  const pressure = [...competitors].sort((a, b) => {
    const aDrop = Number(a.previous_price || 0) - Number(a.current_price || 0);
    const bDrop = Number(b.previous_price || 0) - Number(b.current_price || 0);
    return bDrop - aDrop;
  })[0];
  const strongest = [...signals].sort((a, b) => Number(b.demand || 0) - Number(a.demand || 0))[0];

  byId("topGrowth").textContent = topGrowth?.name || "No competitor";
  byId("topGrowthDetail").textContent = topGrowth ? `${topGrowth.growth_rate || 0}% growth in ${topGrowth.region}` : "Add competitors to calculate";
  byId("pricePressure").textContent = pressure?.name || "No pricing data";
  byId("pricePressureDetail").textContent = pressure ? `${money(Number(pressure.previous_price || 0) - Number(pressure.current_price || 0))} tracked price movement` : "Log price history";
  byId("strongestMarket").textContent = strongest?.area || "No market signal";
  byId("strongestMarketDetail").textContent = strongest ? `${strongest.demand}/100 demand for ${strongest.category}` : "Add market signals";
}

function renderIntelligence(dashboard) {
  const intelligence = dashboard.intelligence || {};
  const metrics = dashboard.metrics || {};
  byId("intelligenceSummary").textContent = intelligence.summary || "Add competitors and activity signals to build the intelligence summary.";
  byId("positiveDevelopments").textContent = metrics.positive_developments || 0;
  byId("negativeDevelopments").textContent = metrics.negative_developments || 0;
  byId("avgTrafficTrend").textContent = percent(metrics.average_traffic_trend);
  byId("marketMentions").textContent = number(metrics.market_mentions);

  byId("topWatchList").innerHTML = (intelligence.top_watch || []).slice(0, 4).map((item) => `
    <article class="watch-card">
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml((item.prediction || {}).move || "Monitoring")}</span>
      </div>
      <span class="score-pill">${escapeHtml(item.score)}/100</span>
      <p>${escapeHtml((item.prediction || {}).rationale || "")}</p>
      <small>${escapeHtml(item.product_launch || item.funding_news || "No captured activity yet.")}</small>
    </article>
  `).join("") || `<div class="empty-state">No competitor signals yet.</div>`;

  byId("opportunityList").innerHTML = listItems(intelligence.opportunities || []);
  byId("threatList").innerHTML = listItems(intelligence.threats || []);
}

function renderAnalysis(analysis) {
  state.analysis = analysis;
  byId("analysisSource").textContent = analysis.source || "Scoring model";
  byId("analysisTitle").textContent = `${analysis.business_profile.business_name} analysis`;
  byId("analysisSummary").textContent = analysis.summary;
  byId("competitionPressure").textContent = analysis.competition_pressure_score;
  byId("competitionLevel").textContent = `${analysis.threat_level} pressure`;
  byId("opportunityScore").textContent = analysis.opportunity_score;
  byId("opportunityMarket").textContent = `${analysis.market_opportunity.area} - ${analysis.market_opportunity.demand}/100 demand`;
  byId("pricePosition").textContent = analysis.price_position.label;
  byId("pricePositionDetail").textContent = `${analysis.price_position.price_delta_percent}% vs competitor average`;
  byId("analysisNote").textContent = analysis.method;

  byId("topThreatList").innerHTML = analysis.top_threats.map((threat) => `
    <article class="threat-item">
      <div>
        <strong>${escapeHtml(threat.name)}</strong>
        <span>${escapeHtml(threat.category)} - ${escapeHtml(threat.region)}</span>
        <p>${escapeHtml(threat.reason)}</p>
      </div>
      <span class="risk-pill ${escapeHtml(threat.threat_level)}">${escapeHtml(threat.threat_score)}</span>
    </article>
  `).join("");

  byId("actionPlanList").innerHTML = analysis.action_plan.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  byId("swotStrengths").innerHTML = listItems(analysis.swot.strengths);
  byId("swotWeaknesses").innerHTML = listItems(analysis.swot.weaknesses);
  byId("swotOpportunities").innerHTML = listItems(analysis.swot.opportunities);
  byId("swotThreats").innerHTML = listItems(analysis.swot.threats);
}

function fillSampleBusiness() {
  const form = byId("analysisForm");
  Object.entries(sampleBusiness).forEach(([key, value]) => {
    if (form.elements[key]) {
      form.elements[key].value = value;
    }
  });
}

function resetChart(key, elementId, config) {
  if (state.charts[key]) {
    state.charts[key].destroy();
  }
  state.charts[key] = new Chart(byId(elementId), config);
}

function renderCharts(charts) {
  const sharedOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: { legend: { position: "bottom", labels: { boxWidth: 10, color: "#475467" } } },
  };

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
        pointRadius: 3,
      })),
    },
    options: {
      ...sharedOptions,
      scales: {
        y: { ticks: { callback: (value) => `$${value}` }, grid: { color: "#e4e7ec" } },
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
      ...sharedOptions,
      cutout: "64%",
    },
  });

  resetChart("demand", "demandChart", {
    type: "bar",
    data: {
      labels: charts.demand_labels,
      datasets: [{ label: "Demand", data: charts.demand_values, backgroundColor: "#0f766e", borderRadius: 6 }],
    },
    options: {
      ...sharedOptions,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: "#e4e7ec" } },
        x: { grid: { display: false } },
      },
    },
  });

  resetChart("performance", "performanceChart", {
    type: "line",
    data: {
      labels: charts.performance_labels || [],
      datasets: (charts.performance_series || []).map((series, index) => ({
        label: series.name,
        data: series.data,
        borderColor: colors[index % colors.length],
        backgroundColor: `${colors[index % colors.length]}18`,
        borderWidth: 3,
        tension: 0.34,
        pointRadius: 2,
        fill: true,
      })),
    },
    options: {
      ...sharedOptions,
      scales: {
        y: { beginAtZero: true, max: 100, grid: { color: "#e4e7ec" } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderCompetitorOptions(competitors) {
  const options = competitors
    .map((competitor) => `<option value="${escapeHtml(competitor._id)}">${escapeHtml(competitor.name)}</option>`)
    .join("");
  byId("battlecardCompetitor").innerHTML = options;
  byId("priceCompetitor").innerHTML = options;
  byId("activityCompetitor").innerHTML = options;
}

function filteredCompetitors(competitors) {
  const needle = state.competitorFilter.trim().toLowerCase();
  if (!needle) {
    return competitors;
  }
  return competitors.filter((competitor) =>
    [competitor.name, competitor.category, competitor.region, competitor.positioning]
      .join(" ")
      .toLowerCase()
      .includes(needle)
  );
}

function renderCompetitors(competitors) {
  const rows = filteredCompetitors(competitors).map((competitor) => `
    <tr>
      <td>
        <div class="company-cell">
          <strong>${escapeHtml(competitor.name)}</strong>
          <small>${escapeHtml(competitor.category)}</small>
        </div>
      </td>
      <td>${escapeHtml(competitor.region)}</td>
      <td>${money(competitor.current_price)}</td>
      <td><span class="score-pill">${escapeHtml(competitor.product_score)}/100</span></td>
      <td>${Number(competitor.growth_rate || 0)}%</td>
      <td>${Number(competitor.traffic_trend || 0)}%</td>
      <td><button class="text-button" data-battlecard="${escapeHtml(competitor._id)}" type="button">Battlecard</button></td>
    </tr>
  `).join("");
  byId("competitorRows").innerHTML = rows || `<tr><td colspan="7" class="empty-state">No competitors match this search.</td></tr>`;
}

function renderSignals(signals) {
  byId("signalList").innerHTML = signals.map((signal) => `
    <div class="signal-item">
      <div>
        <strong>${escapeHtml(signal.area)}</strong>
        <span>${escapeHtml(signal.category)} - ${escapeHtml(signal.trend)}</span>
      </div>
      <span class="score-pill">${escapeHtml(signal.demand)}</span>
    </div>
  `).join("");
}

function renderAlerts(alerts) {
  const activeAlerts = alerts.filter((alert) => alert.status !== "Closed");
  byId("alertList").innerHTML = activeAlerts.map((alert) => `
    <article class="alert-item">
      <div>
        <span class="alert-severity ${escapeHtml(alert.severity)}">${escapeHtml(alert.severity)}</span>
        <strong>${escapeHtml(alert.title)}</strong>
        <p>${escapeHtml(alert.message)}</p>
      </div>
      ${alert.auto_generated ? `<span class="source-pill">AI alert</span>` : `
        <button class="icon-button" data-close-alert="${escapeHtml(alert._id)}" type="button" title="Close alert" aria-label="Close alert">
          <i data-lucide="check"></i>
        </button>
      `}
    </article>
  `).join("") || `<div class="empty-state">No active alerts. Add one when competitor movement needs review.</div>`;
  renderIcons();
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

function renderReports(reports) {
  byId("reportList").innerHTML = reports.slice(0, 5).map((report) => `
    <article class="report-item">
      <div>
        <strong>${escapeHtml(report.title)}</strong>
        <span>${new Date(report.created_at).toLocaleString()}</span>
      </div>
      <a class="icon-link" href="${API_BASE}/api/reports/${escapeHtml(report._id)}/export" title="Export report" aria-label="Export report">
        <i data-lucide="download"></i>
      </a>
    </article>
  `).join("") || `<div class="empty-state">No briefs yet. Create one from the top action bar.</div>`;
  renderIcons();
}

function listItems(items) {
  return (items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderBattlecard(card) {
  state.battlecard = card;
  byId("battlecardSource").textContent = card.source || "Rules engine";
  byId("battlecardRisk").textContent = "Risk level";
  byId("riskPill").textContent = card.risk_level || "Medium";
  byId("riskPill").className = `risk-pill ${escapeHtml(card.risk_level || "Medium")}`;
  byId("battlecardName").textContent = card.competitor_name || "Battlecard";
  byId("battlecardHeadline").textContent = card.headline || card.positioning || "";
  byId("battlecardStats").innerHTML = (card.quick_stats || []).map((stat) => `
    <div class="stat-tile">
      <span>${escapeHtml(stat.label)}</span>
      <strong>${escapeHtml(stat.value)}</strong>
    </div>
  `).join("");
  byId("strengthList").innerHTML = listItems(card.strengths);
  byId("weaknessList").innerHTML = listItems(card.weaknesses);
  byId("talkTrackList").innerHTML = listItems(card.talk_track);
  byId("moveList").innerHTML = listItems(card.recommended_moves);
  byId("battlecardNote").textContent = card.note || "";
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    byId("healthStatus").textContent = "Online";
    byId("storeName").textContent = `${health.store} connected`;
  } catch (error) {
    byId("healthStatus").textContent = "Offline";
    byId("storeName").textContent = isLocalHost ? "Start Flask on port 5000" : "Check deployed API route";
    throw error;
  }
}

async function loadDashboard() {
  const dashboard = await api("/api/dashboard");
  state.dashboard = dashboard;
  renderMetrics(dashboard.metrics);
  renderIntelligence(dashboard);
  renderInsights(dashboard);
  renderCharts(dashboard.charts);
  renderCompetitorOptions(dashboard.competitors);
  renderCompetitors(dashboard.competitors);
  renderSignals(dashboard.market_signals);
  renderAlerts(dashboard.alerts);
}

async function loadRecommendations() {
  renderRecommendations(await api("/api/recommendations"));
}

async function loadReports() {
  renderReports(await api("/api/reports"));
}

async function generateAnalysis(event = null) {
  if (event) {
    event.preventDefault();
  }
  setButtonLoading(byId("analysisButton"), true, "Analyzing...");
  try {
    const analysis = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify(formPayload(byId("analysisForm"))),
    });
    renderAnalysis(analysis);
    byId("analysisMessage").textContent = "Competition analysis generated.";
    showSystemMessage("Business competition analysis generated.", "success");
  } catch (error) {
    byId("analysisMessage").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("analysisButton"), false);
  }
}

async function generateBattlecard(competitorId, save = true, objective = null) {
  const selectedId = competitorId || byId("battlecardCompetitor").value;
  if (!selectedId) {
    showSystemMessage("Add or select a competitor before generating a battlecard.", "warning");
    return;
  }
  setButtonLoading(byId("battlecardButton"), true, "Generating...");
  try {
    const payload = {
      competitor_id: selectedId,
      objective: objective || byId("battlecardObjective").value,
      save,
    };
    const card = await api("/api/battlecard", { method: "POST", body: JSON.stringify(payload) });
    renderBattlecard(card);
    byId("battlecardMessage").textContent = "Battlecard ready.";
    showSystemMessage(`${card.competitor_name} battlecard generated.`, "success");
  } catch (error) {
    byId("battlecardMessage").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("battlecardButton"), false);
  }
}

async function askCopilot(event = null) {
  if (event) {
    event.preventDefault();
  }
  setButtonLoading(byId("copilotButton"), true, "Thinking...");
  try {
    const payload = { question: byId("copilotQuestion").value };
    const response = await api("/api/copilot", { method: "POST", body: JSON.stringify(payload) });
    byId("copilotSource").textContent = response.source || "Rules engine";
    byId("copilotAnswer").textContent = response.answer || "No answer returned.";
    byId("copilotBullets").innerHTML = listItems(response.bullets || []);
    byId("copilotNote").textContent = response.note || response.follow_up || "";
    showSystemMessage("Copilot answered your competitive-positioning question.", "success");
  } catch (error) {
    byId("copilotAnswer").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("copilotButton"), false);
  }
}

async function refreshAll() {
  showSystemMessage("Refreshing workspace...", "info");
  try {
    await loadHealth();
    await loadDashboard();
    await loadRecommendations();
    await loadReports();
    if (!state.battlecard && state.dashboard?.competitors?.length) {
      await generateBattlecard(state.dashboard.competitors[0]._id, false);
    }
    await askCopilot();
    showSystemMessage("Workspace is up to date.", "success");
  } catch (error) {
    showSystemMessage(error.message, "error");
  }
}

async function submitJsonForm(event, path, messageId, successMessage, afterSave = refreshAll) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api(path, { method: "POST", body: JSON.stringify(formPayload(form)) });
    form.reset();
    if (form.elements.date) {
      form.elements.date.value = currentMonth();
    }
    byId(messageId).textContent = successMessage;
    showSystemMessage(successMessage, "success");
    await afterSave();
  } catch (error) {
    byId(messageId).textContent = error.message;
    showSystemMessage(error.message, "error");
  }
}

function exportBattlecard() {
  if (!state.battlecard) {
    byId("battlecardMessage").textContent = "Generate a battlecard first.";
    return;
  }
  const card = state.battlecard;
  const lines = [
    `${card.competitor_name} Battlecard`,
    `Objective: ${card.objective}`,
    `Risk: ${card.risk_level}`,
    "",
    card.headline,
    "",
    "Strengths",
    ...(card.strengths || []).map((item) => `- ${item}`),
    "",
    "Weaknesses",
    ...(card.weaknesses || []).map((item) => `- ${item}`),
    "",
    "Talk Track",
    ...(card.talk_track || []).map((item) => `- ${item}`),
    "",
    "Recommended Moves",
    ...(card.recommended_moves || []).map((item) => `- ${item}`),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${card.competitor_name || "battlecard"}-battlecard.txt`.replaceAll(" ", "-").toLowerCase();
  link.click();
  URL.revokeObjectURL(link.href);
}

function exportAnalysis() {
  if (!state.analysis) {
    byId("analysisMessage").textContent = "Generate an analysis first.";
    return;
  }
  const analysis = state.analysis;
  const swot = analysis.swot;
  const lines = [
    `${analysis.business_profile.business_name} Competition Analysis`,
    `Category: ${analysis.business_profile.category}`,
    `Region: ${analysis.business_profile.region}`,
    `Competition Pressure: ${analysis.competition_pressure_score} (${analysis.threat_level})`,
    `Opportunity Score: ${analysis.opportunity_score}`,
    `Price Position: ${analysis.price_position.label}`,
    "",
    "Summary",
    analysis.summary,
    "",
    "Top Threats",
    ...(analysis.top_threats || []).map((threat) => `- ${threat.name}: ${threat.threat_score}/100. ${threat.reason}`),
    "",
    "Strengths",
    ...swot.strengths.map((item) => `- ${item}`),
    "",
    "Weaknesses",
    ...swot.weaknesses.map((item) => `- ${item}`),
    "",
    "Opportunities",
    ...swot.opportunities.map((item) => `- ${item}`),
    "",
    "Threats",
    ...swot.threats.map((item) => `- ${item}`),
    "",
    "Action Plan",
    ...analysis.action_plan.map((item, index) => `${index + 1}. ${item}`),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${analysis.business_profile.business_name}-competition-analysis.txt`.replaceAll(" ", "-").toLowerCase();
  link.click();
  URL.revokeObjectURL(link.href);
}

function syncBattlecardSelectors(source) {
  byId("battlecardCompetitor").value = source.value;
}

function attachEvents() {
  byId("refreshButton").addEventListener("click", refreshAll);
  byId("reportButton").addEventListener("click", async () => {
    setButtonLoading(byId("reportButton"), true, "Creating...");
    try {
      await api("/api/reports", { method: "POST", body: JSON.stringify({}) });
      await loadReports();
      showSystemMessage("Executive brief created and ready to export.", "success");
    } catch (error) {
      showSystemMessage(error.message, "error");
    } finally {
      setButtonLoading(byId("reportButton"), false);
    }
  });
  byId("analysisForm").addEventListener("submit", generateAnalysis);
  byId("copilotForm").addEventListener("submit", askCopilot);
  byId("sampleBusinessButton").addEventListener("click", () => {
    fillSampleBusiness();
    generateAnalysis();
  });
  byId("exportAnalysisButton").addEventListener("click", exportAnalysis);
  byId("scrollIntakeButton").addEventListener("click", () => {
    window.location.hash = "intake";
  });
  byId("battlecardForm").addEventListener("submit", (event) => {
    event.preventDefault();
    syncBattlecardSelectors(byId("battlecardCompetitor"));
    generateBattlecard();
  });
  byId("battlecardCompetitor").addEventListener("change", (event) => syncBattlecardSelectors(event.target));
  byId("exportBattlecardButton").addEventListener("click", exportBattlecard);
  byId("competitorSearch").addEventListener("input", (event) => {
    state.competitorFilter = event.target.value;
    renderCompetitors(state.dashboard?.competitors || []);
  });
  byId("competitorRows").addEventListener("click", (event) => {
    const button = event.target.closest("[data-battlecard]");
    if (button) {
      byId("battlecardCompetitor").value = button.dataset.battlecard;
      generateBattlecard(button.dataset.battlecard);
      window.location.hash = "battlecard";
    }
  });
  byId("alertList").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-close-alert]");
    if (!button) {
      return;
    }
    await api(`/api/alerts/${button.dataset.closeAlert}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: "Closed" }),
    });
    await refreshAll();
  });
  byId("competitorForm").addEventListener("submit", (event) =>
    submitJsonForm(event, "/api/competitors", "formMessage", "Competitor added.")
  );
  byId("priceForm").addEventListener("submit", (event) =>
    submitJsonForm(event, "/api/prices", "priceMessage", "Price saved.")
  );
  byId("signalForm").addEventListener("submit", (event) =>
    submitJsonForm(event, "/api/market-signals", "signalMessage", "Signal saved.")
  );
  byId("activitySignalForm").addEventListener("submit", (event) =>
    submitJsonForm(event, "/api/activity-signals", "activitySignalMessage", "Competitor growth signal saved.")
  );
  byId("alertForm").addEventListener("submit", (event) =>
    submitJsonForm(event, "/api/alerts", "alertMessage", "Alert added.")
  );
}

async function boot() {
  byId("priceForm").elements.date.value = currentMonth();
  fillSampleBusiness();
  attachEvents();
  renderIcons();
  await refreshAll();
  await generateAnalysis();
}

boot().catch((error) => {
  console.error(error);
  byId("healthStatus").textContent = "Offline";
  byId("storeName").textContent = error.message;
  showSystemMessage(error.message, "error");
});
