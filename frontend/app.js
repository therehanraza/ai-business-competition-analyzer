const isLocalHost = ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
const API_BASE =
  localStorage.getItem("competitionAnalyzerApi") ||
  window.COMPETITION_ANALYZER_API ||
  (isLocalHost ? "http://127.0.0.1:5000" : "");
const API_CANDIDATES = [
  API_BASE,
  !isLocalHost ? "https://ai-business-competition-analyzer-api.onrender.com" : "",
].filter((value, index, items) => value !== null && value !== undefined && items.indexOf(value) === index);

const state = {
  dashboard: null,
  analysis: null,
  battlecard: null,
  charts: {},
  competitorFilter: "",
  activeView: "dashboard",
  apiBase: API_BASE,
  demoMode: false,
  enrichment: null,
  sidebarOpen: false,
  currencyRegion: "India",
};

const colors = ["#2dd4bf", "#f59e0b", "#fb7185", "#60a5fa", "#a3e635", "#c084fc"];

function byId(id) {
  return document.getElementById(id);
}

function renderIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

const currencyByRegion = {
  Global: { currency: "USD", locale: "en-US", rate: 1 },
  India: { currency: "INR", locale: "en-IN", rate: 83 },
  "United States": { currency: "USD", locale: "en-US", rate: 1 },
  "United Kingdom": { currency: "GBP", locale: "en-GB", rate: 0.79 },
  Europe: { currency: "EUR", locale: "de-DE", rate: 0.92 },
  "Asia Pacific": { currency: "SGD", locale: "en-SG", rate: 1.35 },
  "Middle East": { currency: "AED", locale: "en-AE", rate: 3.67 },
  "Latin America": { currency: "MXN", locale: "es-MX", rate: 18.2 },
};

function regionCurrency(region = state.currencyRegion) {
  return currencyByRegion[region] || currencyByRegion.Global;
}

function money(value, region = state.currencyRegion) {
  const config = regionCurrency(region);
  const converted = Number(value || 0) * config.rate;
  return new Intl.NumberFormat(config.locale, {
    style: "currency",
    currency: config.currency,
    maximumFractionDigits: 0,
  }).format(converted);
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

function clean_string(value, fallback = "") {
  const text = String(value ?? "").trim();
  return text || fallback;
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

const demoSeed = {
  competitors: [
    {
      _id: "c_marketpulse",
      name: "MarketPulse Pro",
      category: "Retail Analytics",
      website: "https://marketpulse.example",
      region: "North America",
      positioning: "Premium analytics suite for omnichannel retailers",
      current_price: 249,
      previous_price: 279,
      market_share: 24,
      product_score: 88,
      sentiment: 81,
      growth_rate: 12,
      traffic_trend: 18,
      hiring_activity: 14,
      funding_news: "Expanded Series B round to fund enterprise sales hiring.",
      product_launch: "Launched automated promotion attribution for retail teams.",
      market_mentions: 128,
    },
    {
      _id: "c_pricehawk",
      name: "PriceHawk",
      category: "Pricing Intelligence",
      website: "https://pricehawk.example",
      region: "Europe",
      positioning: "Automated price monitoring for mid-market brands",
      current_price: 129,
      previous_price: 119,
      market_share: 18,
      product_score: 79,
      sentiment: 74,
      growth_rate: 9,
      traffic_trend: 7,
      hiring_activity: 6,
      funding_news: "No recent funding event captured.",
      product_launch: "Released marketplace repricing alerts.",
      market_mentions: 84,
    },
    {
      _id: "c_signalgrid",
      name: "SignalGrid",
      category: "Demand Forecasting",
      website: "https://signalgrid.example",
      region: "Asia Pacific",
      positioning: "Regional demand forecasting for fast-moving products",
      current_price: 199,
      previous_price: 199,
      market_share: 15,
      product_score: 83,
      sentiment: 77,
      growth_rate: 15,
      traffic_trend: 22,
      hiring_activity: 18,
      funding_news: "Raised strategic growth capital for Asia Pacific expansion.",
      product_launch: "Introduced AI demand scenario planning.",
      market_mentions: 96,
    },
  ],
  price_history: [
    ["c_marketpulse", "2026-01", 299], ["c_marketpulse", "2026-02", 289], ["c_marketpulse", "2026-03", 279], ["c_marketpulse", "2026-04", 279], ["c_marketpulse", "2026-05", 259], ["c_marketpulse", "2026-06", 249],
    ["c_pricehawk", "2026-01", 99], ["c_pricehawk", "2026-02", 109], ["c_pricehawk", "2026-03", 119], ["c_pricehawk", "2026-04", 119], ["c_pricehawk", "2026-05", 129], ["c_pricehawk", "2026-06", 129],
    ["c_signalgrid", "2026-01", 229], ["c_signalgrid", "2026-02", 219], ["c_signalgrid", "2026-03", 209], ["c_signalgrid", "2026-04", 199], ["c_signalgrid", "2026-05", 199], ["c_signalgrid", "2026-06", 199],
  ].map(([competitor_id, date, price], index) => ({ _id: `p${index + 1}`, competitor_id, date, price })),
  market_signals: [
    { _id: "m1", area: "New York", demand: 91, trend: "Rising", category: "Retail Analytics" },
    { _id: "m2", area: "London", demand: 84, trend: "Stable", category: "Pricing Intelligence" },
    { _id: "m3", area: "Singapore", demand: 89, trend: "Rising", category: "Demand Forecasting" },
    { _id: "m4", area: "Toronto", demand: 76, trend: "Softening", category: "Retail Analytics" },
    { _id: "m5", area: "Berlin", demand: 82, trend: "Rising", category: "Pricing Intelligence" },
  ],
  alerts: [
    { _id: "a1", severity: "High", title: "MarketPulse Pro dropped pricing by 10.8%", message: "Premium competitor is moving down-market. Review enterprise discount guardrails.", created_at: new Date().toISOString(), status: "Open" },
    { _id: "a2", severity: "Medium", title: "Demand spike in Singapore", message: "Demand forecasting category is up across Asia Pacific. Launch regional campaign tests.", created_at: new Date().toISOString(), status: "Open" },
  ],
  activity_signals: [
    { _id: "s1", competitor_id: "c_marketpulse", type: "Product Launch", sentiment: "Positive", summary: "Automated promotion attribution launched for retail teams.", impact_score: 82, source: "Product page", created_at: new Date().toISOString() },
    { _id: "s2", competitor_id: "c_signalgrid", type: "Hiring", sentiment: "Positive", summary: "Multiple enterprise sales and data science roles opened in Singapore.", impact_score: 76, source: "Careers page", created_at: new Date().toISOString() },
    { _id: "s3", competitor_id: "c_pricehawk", type: "Pricing", sentiment: "Negative", summary: "Price increase may create buyer resistance in mid-market renewals.", impact_score: 61, source: "Pricing page", created_at: new Date().toISOString() },
  ],
  reports: [],
  battlecards: [],
};

function showSystemMessage(message, tone = "info") {
  const element = byId("systemMessage");
  element.textContent = message || "";
  element.dataset.tone = tone;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function getDemoDb() {
  try {
    return JSON.parse(localStorage.getItem("competitionAnalyzerDemoDb")) || clone(demoSeed);
  } catch (_error) {
    return clone(demoSeed);
  }
}

function saveDemoDb(db) {
  localStorage.setItem("competitionAnalyzerDemoDb", JSON.stringify(db));
}

function demoId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function average(items, selector) {
  const values = items.map(selector).map(Number).filter((value) => Number.isFinite(value));
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function competitorSignalScore(competitor) {
  return Math.round(
    Number(competitor.product_score || 0) * 0.34 +
    Number(competitor.sentiment || 0) * 0.18 +
    Number(competitor.growth_rate || 0) * 1.25 +
    Number(competitor.traffic_trend || 0) * 0.9 +
    Math.min(Number(competitor.market_mentions || 0) / 2, 35)
  );
}

function buildDemoDashboard() {
  const db = getDemoDb();
  const competitors = clone(db.competitors);
  const marketSignals = clone(db.market_signals).sort((a, b) => Number(b.demand) - Number(a.demand));
  const alerts = clone(db.alerts).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const priceHistory = clone(db.price_history).sort((a, b) => `${a.competitor_id}${a.date}`.localeCompare(`${b.competitor_id}${b.date}`));
  const positiveSignals = db.activity_signals.filter((item) => item.sentiment === "Positive").length;
  const negativeSignals = db.activity_signals.filter((item) => item.sentiment === "Negative").length;
  const priceDrops = competitors.map((item) => Number(item.previous_price || 0) - Number(item.current_price || 0));
  const labels = [...new Set(priceHistory.map((item) => item.date))].sort();
  const topWatch = competitors
    .map((competitor) => ({
      ...competitor,
      score: Math.min(100, competitorSignalScore(competitor)),
      prediction: {
        move: Number(competitor.growth_rate || 0) >= 12 ? "Expansion likely" : Number(competitor.current_price || 0) < Number(competitor.previous_price || 0) ? "Pricing attack" : "Steady pressure",
        rationale: `${competitor.name} combines ${competitor.growth_rate || 0}% growth, ${competitor.traffic_trend || 0}% traffic movement, and ${competitor.market_mentions || 0} market mentions.`,
      },
    }))
    .sort((a, b) => b.score - a.score);

  return {
    metrics: {
      tracked_competitors: competitors.length,
      average_price: Math.round(average(competitors, (item) => item.current_price)),
      demand_index: Math.round(average(marketSignals, (item) => item.demand)),
      open_alerts: alerts.filter((item) => item.status !== "Closed").length + topWatch.filter((item) => item.score >= 78).length,
      biggest_price_drop: Math.max(0, ...priceDrops).toFixed(1).replace(".0", ""),
      positive_developments: positiveSignals,
      negative_developments: negativeSignals,
      average_traffic_trend: average(competitors, (item) => item.traffic_trend),
      market_mentions: competitors.reduce((sum, item) => sum + Number(item.market_mentions || 0), 0),
    },
    intelligence: {
      summary: `${topWatch[0]?.name || "The market"} is the highest-priority competitor signal, while ${marketSignals[0]?.area || "your strongest market"} shows the strongest demand for the category.`,
      top_watch: topWatch,
      opportunities: [
        `Lead with faster deployment against premium competitors in ${marketSignals[0]?.area || "high-demand regions"}.`,
        "Use pricing clarity and ROI proof to counter competitors with recent price movement.",
        "Turn launch and hiring signals into targeted battlecards for sales conversations.",
      ],
      threats: [
        `${topWatch[0]?.name || "A top competitor"} may increase share through growth and product momentum.`,
        "Down-market pricing pressure could compress entry offers without clear packaging.",
        "Regional demand spikes can move quickly if campaigns are not localized.",
      ],
      auto_alerts: topWatch.filter((item) => item.score >= 78),
    },
    charts: {
      price_labels: labels,
      price_series: competitors.map((competitor) => ({
        name: competitor.name,
        data: labels.map((label) => priceHistory.find((item) => item.competitor_id === competitor._id && item.date === label)?.price ?? null),
      })),
      share_labels: competitors.map((item) => item.name),
      share_values: competitors.map((item) => item.market_share || 0),
      demand_labels: marketSignals.map((item) => item.area),
      demand_values: marketSignals.map((item) => item.demand),
      performance_labels: labels,
      performance_series: topWatch.slice(0, 3).map((competitor, index) => ({
        name: competitor.name,
        data: labels.map((_, monthIndex) => Math.min(100, Math.round(competitor.score - (labels.length - monthIndex - 1) * (3 + index)))),
      })),
    },
    competitors,
    market_signals: marketSignals,
    alerts: [
      ...alerts,
      ...topWatch.filter((item) => item.score >= 78).map((item) => ({
        _id: `auto_${item._id}`,
        severity: item.score >= 86 ? "High" : "Medium",
        title: `${item.name} requires active watch`,
        message: item.prediction.rationale,
        status: "Open",
        auto_generated: true,
      })),
    ],
  };
}

function buildDemoRecommendations() {
  const dashboard = buildDemoDashboard();
  const leader = dashboard.intelligence.top_watch[0];
  return {
    source: "Local intelligence engine",
    items: [
      { priority: "High", title: "Protect the highest-intent segment", recommendation: `Prioritize competitive messaging against ${leader?.name || "the fastest mover"} and focus sales on quantified implementation speed.` },
      { priority: "Medium", title: "Create a price-response package", recommendation: "Bundle onboarding, analytics templates, and annual terms so discount pressure does not become the only buyer comparison." },
      { priority: "Medium", title: "Launch regional proof points", recommendation: `Use ${dashboard.market_signals[0]?.area || "the strongest region"} demand signals to anchor a localized case-study campaign.` },
      { priority: "Low", title: "Refresh signal intake weekly", recommendation: "Log product launches, funding, hiring, and sentiment changes so alerts stay presentation-ready." },
    ],
    note: "Local intelligence mode is active while the deployed API is unavailable.",
  };
}

function buildDemoAnalysis(payload) {
  const dashboard = buildDemoDashboard();
  const competitors = dashboard.competitors;
  const profile = {
    business_name: clean_string(payload.business_name, sampleBusiness.business_name),
    category: clean_string(payload.category, sampleBusiness.category),
    region: clean_string(payload.region, sampleBusiness.region),
    price: Number(payload.price || sampleBusiness.price),
    product_score: Number(payload.product_score || sampleBusiness.product_score),
    target_customer: clean_string(payload.target_customer, sampleBusiness.target_customer),
    advantage: clean_string(payload.advantage, sampleBusiness.advantage),
  };
  const avgPrice = average(competitors, (item) => item.current_price);
  const threats = competitors
    .map((competitor) => {
      const score = Math.min(100, Math.round(competitorSignalScore(competitor) + Math.abs(Number(competitor.current_price || 0) - profile.price) / 10));
      return {
        ...competitor,
        threat_score: score,
        threat_level: score >= 82 ? "High" : score >= 64 ? "Medium" : "Low",
        reason: `${competitor.name} has ${competitor.growth_rate || 0}% growth, ${competitor.product_score || 0}/100 product score, and ${money(competitor.current_price, competitor.region || profile.region)} pricing.`,
      };
    })
    .sort((a, b) => b.threat_score - a.threat_score);
  const pressure = Math.round(average(threats.slice(0, 3), (item) => item.threat_score));
  const exactRegionMarket = dashboard.market_signals.find(
    (signal) => clean_string(signal.area).toLowerCase() === clean_string(profile.region).toLowerCase()
  );
  const categoryMarket = dashboard.market_signals.find(
    (signal) => clean_string(signal.category).toLowerCase() === clean_string(profile.category).toLowerCase()
  );
  const bestMarket = exactRegionMarket ||
    (clean_string(profile.region).toLowerCase() !== "global"
      ? { area: profile.region, demand: 78, trend: "Selected market", category: profile.category }
      : categoryMarket || { area: "Global", demand: 75, trend: "Global baseline", category: profile.category });
  const priceDelta = avgPrice ? Math.round(((profile.price - avgPrice) / avgPrice) * 100) : 0;
  return {
    source: "Local scoring model",
    method: "Generated with the local intelligence engine.",
    business_profile: profile,
    summary: `${profile.business_name} can compete in ${profile.category} by positioning ${profile.advantage} for ${profile.target_customer}, while preparing a direct response to ${threats[0]?.name}.`,
    competition_pressure_score: pressure,
    threat_level: pressure >= 82 ? "High" : pressure >= 64 ? "Medium" : "Low",
    opportunity_score: Math.min(100, Math.round(bestMarket.demand + Math.max(0, profile.product_score - 75) / 2 - Math.max(0, priceDelta) / 3)),
    market_opportunity: bestMarket,
    price_position: {
      label: priceDelta <= -10 ? "Value challenger" : priceDelta >= 10 ? "Premium" : "Market aligned",
      price_delta_percent: priceDelta,
    },
    top_threats: threats.slice(0, 3),
    swot: {
      strengths: [`Clear advantage in ${profile.advantage}.`, `${profile.product_score}/100 product score supports premium claims.`, `Focused ICP: ${profile.target_customer}.`],
      weaknesses: ["Needs stronger proof against established competitor awareness.", "Pricing must be explained with ROI evidence."],
      opportunities: [`Highest demand market: ${bestMarket.area}.`, "Competitor pricing movement creates room for clearer packaging.", "Battlecards can turn market signals into sales plays."],
      threats: threats.slice(0, 3).map((item) => `${item.name}: ${item.reason}`),
    },
    action_plan: [
      `Build a one-page comparison against ${threats[0]?.name || "the top competitor"}.`,
      `Target ${bestMarket.area} with a localized demand campaign.`,
      "Publish pricing proof, deployment timeline, and ROI calculator before customer reviews.",
      "Track weekly product-launch, hiring, traffic, and market-mention signals.",
    ],
  };
}

function buildDemoBattlecard(competitorId, objective) {
  const dashboard = buildDemoDashboard();
  const competitor = dashboard.competitors.find((item) => item._id === competitorId) || dashboard.competitors[0];
  const score = competitorSignalScore(competitor);
  return {
    _id: demoId("bc"),
    source: "Local intelligence engine",
    competitor_id: competitor._id,
    competitor_name: competitor.name,
    objective,
    risk_level: score >= 84 ? "High" : score >= 66 ? "Medium" : "Low",
    headline: `${competitor.name} is strongest around ${competitor.positioning.toLowerCase()}, so lead with faster proof, pricing clarity, and category-specific outcomes.`,
    positioning: competitor.positioning,
    quick_stats: [
      { label: "Price", value: money(competitor.current_price, competitor.region) },
      { label: "Share", value: `${competitor.market_share || 0}%` },
      { label: "Growth", value: `${competitor.growth_rate || 0}%` },
      { label: "Signal score", value: `${Math.min(100, score)}/100` },
    ],
    strengths: [competitor.positioning, `${competitor.product_score || 0}/100 product score`, competitor.product_launch],
    weaknesses: [`${money(competitor.current_price, competitor.region)} pricing creates comparison pressure.`, "Recent movement gives sales teams a chance to challenge switching cost.", competitor.funding_news],
    talk_track: [
      `When buyers mention ${competitor.name}, anchor on speed to value and implementation simplicity.`,
      "Ask whether they need a broad enterprise suite or a focused workflow that teams adopt quickly.",
      "Use ROI, onboarding time, and dashboard clarity as proof points.",
    ],
    recommended_moves: [
      "Prepare a comparison sheet for sales review.",
      "Create a regional landing page tied to the strongest demand signal.",
      "Monitor pricing and launch signals before renewal conversations.",
    ],
    note: "Local intelligence mode is active while the deployed API is unavailable.",
  };
}

function inferDiscoveryCategory(name, website = "") {
  const text = `${name} ${website}`.toLowerCase();
  if (text.includes("chatgpt") || text.includes("openai")) return ["AI Assistant Platform", 20];
  if (["price", "repric", "billing", "chargebee", "stripe"].some((word) => text.includes(word))) return ["Pricing Intelligence", 129];
  if (["retail", "shop", "commerce", "store", "market"].some((word) => text.includes(word))) return ["Retail Analytics", 179];
  if (["demand", "forecast", "supply", "inventory", "grid"].some((word) => text.includes(word))) return ["Demand Forecasting", 199];
  if (["crm", "sales", "hub", "lead"].some((word) => text.includes(word))) return ["Sales Intelligence", 149];
  if (["traffic", "similar", "seo", "web"].some((word) => text.includes(word))) return ["Market Intelligence", 119];
  return ["AI Business Intelligence", 159];
}

function inferDiscoveryRegion(website = "") {
  const url = website.toLowerCase();
  if (url.endsWith(".in") || url.includes(".in/")) return "India";
  if (url.endsWith(".uk") || url.includes(".uk/") || url.includes(".eu")) return "Europe";
  if (url.includes(".sg") || url.includes(".asia")) return "Asia Pacific";
  if (url.includes(".ca")) return "North America";
  return "Global";
}

function pricingPlansForCompany(name, category, currentPrice) {
  const text = name.toLowerCase();
  if (text.includes("chatgpt") || text.includes("openai")) {
    return [
      { name: "Free", price: 0, billing: "monthly", audience: "individuals", note: "Free individual plan with limited access." },
      { name: "Go", price: 8, billing: "monthly", audience: "individuals", note: "Lower-cost individual plan; localized pricing may differ by country." },
      { name: "Plus", price: 20, billing: "monthly", audience: "individuals", note: "Advanced intelligence, projects, tasks, custom GPTs, and expanded usage." },
      { name: "Pro", price: 200, billing: "monthly", audience: "power users", note: "Maximum usage, pro reasoning, deep research, agent mode, and higher limits." },
      { name: "Business", price: 30, billing: "per user/month", audience: "teams", note: "Team workspace; lower per-user annual billing may be available." },
      { name: "Enterprise", price: null, billing: "custom", audience: "large organizations", note: "Custom pricing, admin, security, and enterprise controls." },
    ];
  }
  return [
    { name: "Starter", price: Math.max(0, Math.round(currentPrice * 0.55)), billing: "monthly", audience: "small teams", note: `Entry ${category.toLowerCase()} package.` },
    { name: "Growth", price: currentPrice, billing: "monthly", audience: "mid-market teams", note: "Main plan used for price-position comparison." },
    { name: "Business", price: Math.round(currentPrice * 1.65), billing: "monthly", audience: "larger teams", note: "More usage, seats, and workflow controls." },
    { name: "Enterprise", price: null, billing: "custom", audience: "enterprise buyers", note: "Custom quote for security, scale, and support." },
  ];
}

function buildLocalEnrichment(payload) {
  const name = clean_string(payload.name || payload.business_name);
  const website = clean_string(payload.website);
  if (!name) {
    throw new Error("Competitor name is required.");
  }
  const [category, basePrice] = inferDiscoveryCategory(name, website);
  const seed = [...name.toLowerCase()].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const currentPrice = basePrice + (seed % 5) * 20;
  const region = clean_string(payload.region, inferDiscoveryRegion(website));
  const profile = {
    name,
    category,
    website: website || `https://${name.toLowerCase().replace(/[^a-z0-9]+/g, "")}.com`,
    region,
    positioning: `${name} appears positioned as a ${category.toLowerCase()} platform for teams that need faster competitive decisions.`,
    current_price: currentPrice,
    previous_price: Math.max(0, currentPrice + [20, -10, 0, 30, -20][seed % 5]),
    market_share: 8 + seed % 18,
    product_score: 72 + seed % 18,
    sentiment: 66 + seed % 22,
    growth_rate: 6 + seed % 15,
    traffic_trend: 4 + seed % 24,
    hiring_activity: 3 + seed % 18,
    market_mentions: 45 + seed % 140,
    funding_news: "No verified funding event is connected yet; keep this company on the funding watchlist.",
    product_launch: `AI enrichment suggests ${name} recently expanded ${category.toLowerCase()} workflows.`,
  };
  profile.pricing_plans = pricingPlansForCompany(name, category, currentPrice);
  if (name.toLowerCase().includes("chatgpt") || name.toLowerCase().includes("openai")) {
    Object.assign(profile, {
      category: "AI Assistant Platform",
      positioning: "ChatGPT is OpenAI's AI assistant platform for individuals, teams, developers, and enterprises.",
      current_price: 20,
      previous_price: 20,
      price_summary: "Plan range: Free, Go, Plus, Pro, Business, Enterprise.",
      data_quality: "Known public pricing profile",
      funding_news: "OpenAI is a major AI platform company; use funding/news signals only when connected to live sources.",
      product_launch: "ChatGPT plans differ by usage limits, model access, team workspace controls, and enterprise security.",
    });
  }
  return {
    source: "Local intelligence engine",
    confidence: "Estimated",
    profile,
    insights: [
      `${name} is most relevant to the ${category} category.`,
      `Market focus is set to ${region}; demand and recommendations will prioritize that country/region.`,
      `Initial signal model estimates ${profile.traffic_trend}% traffic movement and ${profile.market_mentions} market mentions.`,
      "The system will track pricing, launch, hiring, traffic, sentiment, and market-mention changes after this company is added.",
    ],
    activity_signal: {
      type: "Product Launch",
      sentiment: profile.product_score >= 78 ? "Positive" : "Neutral",
      summary: profile.product_launch,
      impact_score: Math.min(100, Math.round((profile.product_score + profile.traffic_trend + profile.growth_rate) / 1.9)),
      metric_value: profile.traffic_trend,
      source: website || "AI enrichment",
    },
    market_signal: {
      area: region,
      demand: Math.min(100, 68 + seed % 26),
      trend: profile.growth_rate >= 12 ? "Rising" : "Stable",
      category,
    },
    next_tracking_actions: [
      "Review auto-filled fields and start tracking.",
      "Generate a battlecard after the company appears in the watchlist.",
      "Refresh the dashboard to see pricing, market, and threat signals update.",
    ],
    note: "Local intelligence mode is active while the deployed API is unavailable.",
  };
}

function demoApi(path, options = {}) {
  const db = getDemoDb();
  const method = (options.method || "GET").toUpperCase();
  const payload = options.body ? JSON.parse(options.body) : {};
  const now = new Date().toISOString();

  if (path === "/api/health") {
    return { status: "ok", store: "Local intelligence", timestamp: now };
  }
  if (path === "/api/dashboard") {
    return buildDemoDashboard();
  }
  if (path === "/api/recommendations") {
    return buildDemoRecommendations();
  }
  if (path === "/api/reports" && method === "GET") {
    return clone(db.reports).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  }
  if (path === "/api/reports" && method === "POST") {
    const report = { _id: demoId("r"), title: payload.title || `Competitive Intelligence Brief - ${new Date().toLocaleDateString()}`, created_at: now, summary: buildDemoDashboard().metrics, source: "Local intelligence engine" };
    db.reports.unshift(report);
    saveDemoDb(db);
    return report;
  }
  if (path === "/api/analyze" && method === "POST") {
    return buildDemoAnalysis(payload);
  }
  if ((path === "/api/battlecard" || path === "/api/battlecards") && method === "POST") {
    const card = buildDemoBattlecard(payload.competitor_id, payload.objective || "Win new business against this competitor");
    if (payload.save !== false) {
      db.battlecards.unshift(card);
      saveDemoDb(db);
    }
    return card;
  }
  if (path === "/api/copilot" && method === "POST") {
    const dashboard = buildDemoDashboard();
    const leader = dashboard.intelligence.top_watch[0];
    return {
      source: "Local intelligence engine",
      answer: `${leader?.name || "The top competitor"} should get the first response because it leads the combined growth, traffic, product, and mention signals. Pair a direct battlecard with pricing proof and a regional campaign in ${dashboard.market_signals[0]?.area || "the strongest market"}.`,
      bullets: [dashboard.intelligence.summary, ...buildDemoRecommendations().items.slice(0, 3).map((item) => item.recommendation)],
      follow_up: "Ask about a specific competitor, pricing pressure, growth threat, or recommended response.",
      note: "Local intelligence mode is active while the deployed API is unavailable.",
    };
  }
  if (path === "/api/enrich-competitor" && method === "POST") {
    return buildLocalEnrichment(payload);
  }
  if (path === "/api/track-competitor" && method === "POST") {
    const enrichment = payload.enrichment || buildLocalEnrichment(payload);
    const competitor = { _id: demoId("c"), ...enrichment.profile };
    db.competitors.push(competitor);
    db.price_history.push({ _id: demoId("p"), competitor_id: competitor._id, date: currentMonth(), price: Number(competitor.current_price || 0), created_at: now });
    db.activity_signals.push({ _id: demoId("s"), competitor_id: competitor._id, ...enrichment.activity_signal, created_at: now });
    db.market_signals.push({ _id: demoId("m"), ...enrichment.market_signal, created_at: now });
    saveDemoDb(db);
    return { created: true, competitor, activity_signal: db.activity_signals[db.activity_signals.length - 1], market_signal: db.market_signals[db.market_signals.length - 1], enrichment };
  }
  if (path === "/api/competitors" && method === "POST") {
    const competitor = { _id: demoId("c"), previous_price: Number(payload.current_price || 0), updated_at: now, ...payload };
    db.competitors.push(competitor);
    db.price_history.push({ _id: demoId("p"), competitor_id: competitor._id, date: currentMonth(), price: Number(payload.current_price || 0), created_at: now });
    saveDemoDb(db);
    return competitor;
  }
  if (path === "/api/prices" && method === "POST") {
    const price = { _id: demoId("p"), ...payload, price: Number(payload.price || 0), created_at: now };
    db.price_history.push(price);
    const competitor = db.competitors.find((item) => item._id === payload.competitor_id);
    if (competitor) {
      competitor.previous_price = competitor.current_price;
      competitor.current_price = Number(payload.price || competitor.current_price || 0);
    }
    saveDemoDb(db);
    return price;
  }
  if (path === "/api/market-signals" && method === "POST") {
    db.market_signals.push({ _id: demoId("m"), ...payload, demand: Number(payload.demand || 0), created_at: now });
    saveDemoDb(db);
    return db.market_signals[db.market_signals.length - 1];
  }
  if (path === "/api/activity-signals" && method === "POST") {
    db.activity_signals.push({ _id: demoId("s"), ...payload, impact_score: Number(payload.impact_score || 0), created_at: now });
    const competitor = db.competitors.find((item) => item._id === payload.competitor_id);
    if (competitor && payload.metric_value) {
      if (payload.type === "Hiring") competitor.hiring_activity = Number(payload.metric_value);
      if (payload.type === "Traffic") competitor.traffic_trend = Number(payload.metric_value);
      if (payload.type === "Market Mention") competitor.market_mentions = Number(payload.metric_value);
    }
    saveDemoDb(db);
    return db.activity_signals[db.activity_signals.length - 1];
  }
  if (path === "/api/alerts" && method === "POST") {
    db.alerts.unshift({ _id: demoId("a"), status: "Open", created_at: now, ...payload });
    saveDemoDb(db);
    return db.alerts[0];
  }
  const alertMatch = path.match(/^\/api\/alerts\/(.+)\/status$/);
  if (alertMatch && method === "PATCH") {
    const alert = db.alerts.find((item) => item._id === alertMatch[1]);
    if (alert) {
      alert.status = payload.status || "Closed";
      alert.closed_at = now;
      saveDemoDb(db);
      return alert;
    }
  }
  throw new Error("Local intelligence endpoint not implemented.");
}

async function api(path, options = {}) {
  if (state.demoMode) {
    return demoApi(path, options);
  }
  const bases = API_CANDIDATES.length ? API_CANDIDATES : [""];
  let lastError = null;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (_error) {
        data = { error: text.trim() || "Non-JSON response from API." };
      }
      if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status})`);
      }
      state.apiBase = base;
      return data;
    } catch (error) {
      lastError = error;
    }
  }
  state.demoMode = true;
  console.warn("API unavailable, switching to local intelligence.", lastError);
  return demoApi(path, options);
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
  byId("pricePressureDetail").textContent = pressure ? `${money(Number(pressure.previous_price || 0) - Number(pressure.current_price || 0), pressure.region)} tracked price movement` : "Log price history";
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

function fillAnalysisFromProfile(profile) {
  const form = byId("analysisForm");
  const targetCustomer = profile.category === "AI Assistant Platform"
    ? "individuals, teams, developers, and enterprises"
    : `${profile.category || "business"} buyers`;
  const advantage = profile.category === "AI Assistant Platform"
    ? "broad model access, assistant workflows, team controls, and enterprise security"
    : clean_string(profile.positioning, "clear positioning and faster competitive decisions");
  const values = {
    business_name: profile.name,
    category: profile.category,
    region: profile.region,
    price: profile.current_price || 0,
    product_score: profile.product_score || 78,
    target_customer: targetCustomer,
    advantage,
    objective: "Find the best competitive position for market entry",
  };
  Object.entries(values).forEach(([key, value]) => {
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
    plugins: { legend: { position: "bottom", labels: { boxWidth: 10, color: "#9ca3af" } } },
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
        y: { ticks: { callback: (value) => `$${value}`, color: "#9ca3af" }, grid: { color: "rgba(148, 163, 184, 0.18)" } },
        x: { ticks: { color: "#9ca3af" }, grid: { display: false } },
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
        y: { beginAtZero: true, max: 100, ticks: { color: "#9ca3af" }, grid: { color: "rgba(148, 163, 184, 0.18)" } },
        x: { ticks: { color: "#9ca3af" }, grid: { display: false } },
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
        y: { beginAtZero: true, max: 100, ticks: { color: "#9ca3af" }, grid: { color: "rgba(148, 163, 184, 0.18)" } },
        x: { ticks: { color: "#9ca3af" }, grid: { display: false } },
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
      <td>${money(competitor.current_price, competitor.region)}</td>
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
      <a class="icon-link" href="${state.demoMode ? `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(report, null, 2))}` : `${state.apiBase}/api/reports/${escapeHtml(report._id)}/export`}" download="${escapeHtml(report._id)}.json" title="Export report" aria-label="Export report">
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
    byId("healthStatus").textContent = state.demoMode ? "Local Intelligence" : "Online";
    byId("storeName").textContent = state.demoMode ? "Resilient data layer active" : `${health.store} connected`;
  } catch (error) {
    byId("healthStatus").textContent = "Offline";
    byId("storeName").textContent = isLocalHost ? "Start Flask on port 5000" : "Intelligence layer unavailable";
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

async function quickAnalyzeBusiness() {
  setButtonLoading(byId("quickAnalyzeButton"), true, "Analyzing...");
  try {
    const enrichment = await api("/api/enrich-competitor", {
      method: "POST",
      body: JSON.stringify({
        name: byId("quickBusinessName").value,
        website: byId("quickBusinessWebsite").value,
        region: byId("quickBusinessRegion").value,
      }),
    });
    state.currencyRegion = enrichment.profile.region || state.currencyRegion;
    fillAnalysisFromProfile(enrichment.profile);
    await generateAnalysis();
    showSystemMessage(`${enrichment.profile.name} analyzed from AI-filled business profile.`, "success");
  } catch (error) {
    byId("analysisMessage").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("quickAnalyzeButton"), false);
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

function setSidebar(open) {
  state.sidebarOpen = open;
  document.body.classList.toggle("sidebar-open", open);
  byId("sidebarToggle").setAttribute("aria-expanded", String(open));
  byId("sidebarToggle").setAttribute("title", open ? "Close navigation" : "Open navigation");
  byId("sidebarToggle").setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
}

function fillCompetitorForm(profile) {
  const form = byId("competitorForm");
  Object.entries(profile || {}).forEach(([key, value]) => {
    if (form.elements[key]) {
      form.elements[key].value = value;
    }
  });
}

function renderEnrichment(enrichment) {
  state.enrichment = enrichment;
  const profile = enrichment.profile || {};
  state.currencyRegion = profile.region || state.currencyRegion;
  const hasPlans = Array.isArray(profile.pricing_plans) && profile.pricing_plans.length > 1;
  const priceTitle = hasPlans ? "Pricing model" : "Comparable price";
  const namedPlans = Object.fromEntries((profile.pricing_plans || []).map((plan) => [plan.name, plan]));
  const priceValue = hasPlans && namedPlans.Plus
    ? `Plans: Free, Go ${money(namedPlans.Go?.price || 8, profile.region)}, Plus ${money(namedPlans.Plus.price, profile.region)}, Pro ${money(namedPlans.Pro?.price || 200, profile.region)}, Business ${money(namedPlans.Business?.price || 30, profile.region)}/user`
    : profile.price_summary || money(profile.current_price, profile.region);
  const planCards = (profile.pricing_plans || []).map((plan) => `
    <article>
      <span>${escapeHtml(plan.billing || "monthly")}</span>
      <strong>${escapeHtml(plan.name || "Plan")}</strong>
      <small>${plan.price === null || plan.price === undefined ? "Custom / varies" : money(plan.price, profile.region)}</small>
      <p>${escapeHtml(plan.note || plan.audience || "")}</p>
    </article>
  `).join("");
  byId("discoverySource").textContent = enrichment.source || "AI enrichment";
  byId("trackEnrichedButton").disabled = false;
  byId("enrichmentPreview").innerHTML = `
    <div class="enrichment-card">
      <div>
        <span>${escapeHtml(profile.category || "Category")} - ${escapeHtml(profile.region || "Global")}</span>
        <strong>${escapeHtml(profile.name || "Company")}</strong>
        <p>${escapeHtml(profile.positioning || "")}</p>
      </div>
      <div class="enrichment-stats">
        <article class="wide-stat"><span>${priceTitle}</span><strong>${escapeHtml(priceValue)}</strong></article>
        <article><span>Score</span><strong>${escapeHtml(profile.product_score || 0)}/100</strong></article>
        <article><span>Growth</span><strong>${escapeHtml(profile.growth_rate || 0)}%</strong></article>
        <article><span>Mentions</span><strong>${number(profile.market_mentions || 0)}</strong></article>
      </div>
      <div class="plan-grid">
        <div class="plan-grid-heading">
          <strong>Pricing plans detected</strong>
          <span>${hasPlans ? "Plans are shown separately; charts use the comparable paid plan where needed." : "Comparable price is used in charts."}</span>
        </div>
        ${planCards || `<article><strong>No plans detected</strong><p>Add pricing manually after tracking.</p></article>`}
      </div>
      <ul>${listItems(enrichment.insights || [])}</ul>
    </div>
  `;
  fillCompetitorForm(profile);
  byId("discoveryMessage").textContent = `${profile.name} profile enriched. Review or start tracking.`;
}

async function enrichCompetitor(event = null) {
  if (event) {
    event.preventDefault();
  }
  setButtonLoading(byId("enrichButton"), true, "Enriching...");
  byId("trackEnrichedButton").disabled = true;
  try {
    const enrichment = await api("/api/enrich-competitor", {
      method: "POST",
      body: JSON.stringify(formPayload(byId("discoveryForm"))),
    });
    renderEnrichment(enrichment);
    showSystemMessage(`${enrichment.profile.name} enriched with AI competitor signals.`, "success");
  } catch (error) {
    byId("discoveryMessage").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("enrichButton"), false);
  }
}

async function trackEnrichedCompetitor() {
  if (!state.enrichment) {
    byId("discoveryMessage").textContent = "Run AI enrichment first.";
    return;
  }
  setButtonLoading(byId("trackEnrichedButton"), true, "Tracking...");
  try {
    const response = await api("/api/track-competitor", {
      method: "POST",
      body: JSON.stringify({ enrichment: state.enrichment }),
    });
    await refreshAll();
    const status = response.created ? "added to live tracking" : "already tracked";
    byId("discoveryMessage").textContent = `${response.competitor.name} ${status}.`;
    showSystemMessage(`${response.competitor.name} is now in the watchlist with signals attached.`, "success");
    setActiveView("market");
  } catch (error) {
    byId("discoveryMessage").textContent = error.message;
    showSystemMessage(error.message, "error");
  } finally {
    setButtonLoading(byId("trackEnrichedButton"), false);
  }
}

function viewFromHash() {
  const requested = window.location.hash.replace("#", "");
  const aliases = {
    intelligence: "dashboard",
    command: "analyzer",
    portfolio: "market",
    portfolioTable: "market",
  };
  return aliases[requested] || requested || "dashboard";
}

function setActiveView(viewName, updateHash = true) {
  const available = [...document.querySelectorAll("[data-view]")].map((section) => section.dataset.view);
  const nextView = available.includes(viewName) ? viewName : "dashboard";
  state.activeView = nextView;
  document.querySelectorAll("[data-view]").forEach((section) => {
    section.classList.toggle("view-hidden", section.dataset.view !== nextView);
  });
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    const isActive = link.dataset.viewLink === nextView;
    link.classList.toggle("active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
  if (updateHash && window.location.hash !== `#${nextView}`) {
    history.replaceState(null, "", `#${nextView}`);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function attachEvents() {
  byId("sidebarToggle").addEventListener("click", () => setSidebar(!state.sidebarOpen));
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      setActiveView(link.dataset.viewLink);
      if (window.innerWidth <= 1240) {
        setSidebar(false);
      }
    });
  });
  window.addEventListener("hashchange", () => setActiveView(viewFromHash(), false));
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
  byId("quickAnalyzeButton").addEventListener("click", quickAnalyzeBusiness);
  byId("quickBusinessRegion").addEventListener("change", (event) => {
    state.currencyRegion = event.target.value;
  });
  byId("copilotForm").addEventListener("submit", askCopilot);
  byId("discoveryForm").addEventListener("submit", enrichCompetitor);
  byId("discoveryForm").elements.region.addEventListener("change", (event) => {
    state.currencyRegion = event.target.value;
  });
  byId("trackEnrichedButton").addEventListener("click", trackEnrichedCompetitor);
  byId("sampleBusinessButton").addEventListener("click", () => {
    fillSampleBusiness();
    generateAnalysis();
  });
  byId("exportAnalysisButton").addEventListener("click", exportAnalysis);
  byId("scrollIntakeButton").addEventListener("click", () => {
    setActiveView("intake");
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
      setActiveView("battlecard");
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
  setSidebar(false);
  setActiveView(viewFromHash(), false);
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
