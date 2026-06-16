import json
import os
import statistics
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def as_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def as_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def require_fields(payload, fields):
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    return None


STARTER_DATA = {
    "competitors": [
        {
            "_id": "c_marketpulse",
            "name": "MarketPulse Pro",
            "category": "Retail Analytics",
            "website": "https://marketpulse.example",
            "region": "North America",
            "positioning": "Premium analytics suite for omnichannel retailers",
            "current_price": 249,
            "previous_price": 279,
            "market_share": 24,
            "product_score": 88,
            "sentiment": 81,
            "growth_rate": 12,
            "updated_at": utc_now(),
        },
        {
            "_id": "c_pricehawk",
            "name": "PriceHawk",
            "category": "Pricing Intelligence",
            "website": "https://pricehawk.example",
            "region": "Europe",
            "positioning": "Automated price monitoring for mid-market brands",
            "current_price": 129,
            "previous_price": 119,
            "market_share": 18,
            "product_score": 79,
            "sentiment": 74,
            "growth_rate": 9,
            "updated_at": utc_now(),
        },
        {
            "_id": "c_signalgrid",
            "name": "SignalGrid",
            "category": "Demand Forecasting",
            "website": "https://signalgrid.example",
            "region": "Asia Pacific",
            "positioning": "Regional demand forecasting for fast-moving products",
            "current_price": 199,
            "previous_price": 199,
            "market_share": 15,
            "product_score": 83,
            "sentiment": 77,
            "growth_rate": 15,
            "updated_at": utc_now(),
        },
    ],
    "price_history": [
        {"_id": "p1", "competitor_id": "c_marketpulse", "date": "2026-01", "price": 299},
        {"_id": "p2", "competitor_id": "c_marketpulse", "date": "2026-02", "price": 289},
        {"_id": "p3", "competitor_id": "c_marketpulse", "date": "2026-03", "price": 279},
        {"_id": "p4", "competitor_id": "c_marketpulse", "date": "2026-04", "price": 279},
        {"_id": "p5", "competitor_id": "c_marketpulse", "date": "2026-05", "price": 259},
        {"_id": "p6", "competitor_id": "c_marketpulse", "date": "2026-06", "price": 249},
        {"_id": "p7", "competitor_id": "c_pricehawk", "date": "2026-01", "price": 99},
        {"_id": "p8", "competitor_id": "c_pricehawk", "date": "2026-02", "price": 109},
        {"_id": "p9", "competitor_id": "c_pricehawk", "date": "2026-03", "price": 119},
        {"_id": "p10", "competitor_id": "c_pricehawk", "date": "2026-04", "price": 119},
        {"_id": "p11", "competitor_id": "c_pricehawk", "date": "2026-05", "price": 129},
        {"_id": "p12", "competitor_id": "c_pricehawk", "date": "2026-06", "price": 129},
        {"_id": "p13", "competitor_id": "c_signalgrid", "date": "2026-01", "price": 229},
        {"_id": "p14", "competitor_id": "c_signalgrid", "date": "2026-02", "price": 219},
        {"_id": "p15", "competitor_id": "c_signalgrid", "date": "2026-03", "price": 209},
        {"_id": "p16", "competitor_id": "c_signalgrid", "date": "2026-04", "price": 199},
        {"_id": "p17", "competitor_id": "c_signalgrid", "date": "2026-05", "price": 199},
        {"_id": "p18", "competitor_id": "c_signalgrid", "date": "2026-06", "price": 199},
    ],
    "market_signals": [
        {"_id": "m1", "area": "New York", "demand": 91, "trend": "Rising", "category": "Retail Analytics"},
        {"_id": "m2", "area": "London", "demand": 84, "trend": "Stable", "category": "Pricing Intelligence"},
        {"_id": "m3", "area": "Singapore", "demand": 89, "trend": "Rising", "category": "Demand Forecasting"},
        {"_id": "m4", "area": "Toronto", "demand": 76, "trend": "Softening", "category": "Retail Analytics"},
        {"_id": "m5", "area": "Berlin", "demand": 82, "trend": "Rising", "category": "Pricing Intelligence"},
    ],
    "alerts": [
        {
            "_id": "a1",
            "severity": "High",
            "title": "MarketPulse Pro dropped pricing by 10.8%",
            "message": "Premium competitor is moving down-market. Review enterprise discount guardrails.",
            "created_at": utc_now(),
            "status": "Open",
        },
        {
            "_id": "a2",
            "severity": "Medium",
            "title": "Demand spike in Singapore",
            "message": "Demand forecasting category is up across Asia Pacific. Launch regional campaign tests.",
            "created_at": utc_now(),
            "status": "Open",
        },
    ],
    "reports": [],
}


class LocalStore:
    def __init__(self, path):
        self.path = path
        if not self.path.exists():
            self._write(deepcopy(STARTER_DATA))

    def _read(self):
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, data):
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def all(self, collection):
        return self._read().get(collection, [])

    def insert(self, collection, document):
        data = self._read()
        document = deepcopy(document)
        document["_id"] = document.get("_id") or uuid.uuid4().hex
        data.setdefault(collection, []).append(document)
        self._write(data)
        return document

    def update(self, collection, document_id, updates):
        data = self._read()
        for item in data.get(collection, []):
            if str(item.get("_id")) == str(document_id):
                item.update(updates)
                self._write(data)
                return item
        return None

    def delete(self, collection, document_id):
        data = self._read()
        before = len(data.get(collection, []))
        data[collection] = [item for item in data.get(collection, []) if str(item.get("_id")) != str(document_id)]
        self._write(data)
        return len(data[collection]) != before


class MongoStore:
    def __init__(self, uri, database):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        self.client.admin.command("ping")
        self.db = self.client[database]
        self.db.competitors.create_index([("name", ASCENDING)], unique=True)
        self.db.price_history.create_index([("competitor_id", ASCENDING), ("date", ASCENDING)])
        self.db.alerts.create_index([("created_at", ASCENDING)])
        self.seed_if_empty()

    def serialize(self, document):
        clean = {}
        for key, value in document.items():
            clean[key] = str(value) if key == "_id" else value
        return clean

    def all(self, collection):
        return [self.serialize(item) for item in self.db[collection].find({})]

    def insert(self, collection, document):
        document = deepcopy(document)
        document["_id"] = document.get("_id") or uuid.uuid4().hex
        self.db[collection].insert_one(document)
        return self.serialize(document)

    def update(self, collection, document_id, updates):
        result = self.db[collection].find_one_and_update(
            {"_id": document_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self.serialize(result) if result else None

    def delete(self, collection, document_id):
        return self.db[collection].delete_one({"_id": document_id}).deleted_count == 1

    def seed_if_empty(self):
        if self.db.competitors.count_documents({}) == 0:
            for collection, items in STARTER_DATA.items():
                if items:
                    self.db[collection].insert_many(deepcopy(items))


def create_store():
    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    database = os.getenv("MONGODB_DATABASE", "ai_business_competition_analyzer")
    if mongo_uri:
        try:
            return MongoStore(mongo_uri, database), "MongoDB Atlas"
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            print(f"MongoDB connection failed, using local store: {exc}")
    return LocalStore(BASE_DIR / "local_data.json"), "Local JSON"


store, store_name = create_store()
app = Flask(__name__)
allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()]
CORS(app, resources={r"/api/*": {"origins": allowed_origins or "*"}})


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error", "detail": str(error)}), 500


def sorted_price_history():
    return sorted(store.all("price_history"), key=lambda item: (item.get("competitor_id", ""), item.get("date", "")))


def build_dashboard():
    competitors = store.all("competitors")
    price_history = sorted_price_history()
    market_signals = store.all("market_signals")
    alerts = sorted(store.all("alerts"), key=lambda item: item.get("created_at", ""), reverse=True)

    average_price = round(statistics.mean([as_float(c.get("current_price")) for c in competitors]), 2) if competitors else 0
    average_sentiment = round(statistics.mean([as_float(c.get("sentiment")) for c in competitors]), 1) if competitors else 0
    demand_index = round(statistics.mean([as_float(m.get("demand")) for m in market_signals]), 1) if market_signals else 0
    biggest_price_drop = 0
    for competitor in competitors:
        previous = as_float(competitor.get("previous_price"))
        current = as_float(competitor.get("current_price"))
        if previous:
            biggest_price_drop = max(biggest_price_drop, round(((previous - current) / previous) * 100, 1))

    labels = sorted({entry.get("date") for entry in price_history if entry.get("date")})
    price_series = []
    for competitor in competitors:
        series = []
        for label in labels:
            match = next(
                (
                    entry
                    for entry in price_history
                    if entry.get("competitor_id") == competitor.get("_id") and entry.get("date") == label
                ),
                None,
            )
            series.append(as_float(match.get("price")) if match else None)
        price_series.append({"name": competitor.get("name"), "data": series})

    return {
        "store": store_name,
        "metrics": {
            "tracked_competitors": len(competitors),
            "average_price": average_price,
            "average_sentiment": average_sentiment,
            "demand_index": demand_index,
            "biggest_price_drop": biggest_price_drop,
            "open_alerts": len([alert for alert in alerts if alert.get("status") == "Open"]),
        },
        "charts": {
            "price_labels": labels,
            "price_series": price_series,
            "share_labels": [c.get("name") for c in competitors],
            "share_values": [as_float(c.get("market_share")) for c in competitors],
            "demand_labels": [m.get("area") for m in market_signals],
            "demand_values": [as_float(m.get("demand")) for m in market_signals],
        },
        "competitors": competitors,
        "market_signals": market_signals,
        "alerts": alerts[:10],
    }


def generate_local_recommendations(dashboard):
    competitors = dashboard["competitors"]
    alerts = dashboard["alerts"]
    metrics = dashboard["metrics"]
    fastest = max(competitors, key=lambda item: as_float(item.get("growth_rate")), default={})
    strongest = max(competitors, key=lambda item: as_float(item.get("product_score")), default={})
    pressure = max(competitors, key=lambda item: as_float(item.get("previous_price")) - as_float(item.get("current_price")), default={})

    recommendations = [
        {
            "title": "Protect high-intent accounts",
            "priority": "High",
            "recommendation": f"{pressure.get('name', 'A competitor')} is creating pricing pressure. Create a retention offer and monitor win-loss notes weekly.",
        },
        {
            "title": "Invest where demand is strongest",
            "priority": "High",
            "recommendation": f"Demand index is {metrics['demand_index']}. Shift campaign budget toward the top two areas and test localized pricing pages.",
        },
        {
            "title": "Neutralize product narrative gaps",
            "priority": "Medium",
            "recommendation": f"{strongest.get('name', 'The strongest product')} leads product perception. Publish comparison content around accuracy, integrations, and time-to-value.",
        },
        {
            "title": "Track growth challenger",
            "priority": "Medium",
            "recommendation": f"{fastest.get('name', 'A fast-growing competitor')} has the highest growth signal. Add alert rules for pricing, launches, and regional demand changes.",
        },
    ]
    if alerts:
        recommendations.insert(
            0,
            {
                "title": "Resolve active competitive alerts",
                "priority": "High",
                "recommendation": f"{len(alerts)} active alert(s) need owner review. Assign each alert to pricing, product, or growth within 24 hours.",
            },
        )
    return recommendations


def ask_gemini(dashboard):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not api_key:
        return {
            "source": "Rules engine",
            "items": generate_local_recommendations(dashboard),
            "note": "Add GEMINI_API_KEY to backend/.env to enable Gemini-powered recommendations.",
        }

    prompt = {
        "role": "competitive intelligence strategist",
        "instruction": "Return strict JSON only. Create five concise SaaS executive recommendations from the dashboard data.",
        "schema": {"items": [{"title": "string", "priority": "High|Medium|Low", "recommendation": "string"}]},
        "dashboard": dashboard,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": json.dumps(prompt)}]}]},
        timeout=25,
    )
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(text)
    return {"source": "Google Gemini", "items": parsed.get("items", []), "note": "Powered by gemini-2.5-flash."}


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "store": store_name, "timestamp": utc_now()})


@app.get("/api/dashboard")
def dashboard():
    return jsonify(build_dashboard())


@app.get("/api/competitors")
def competitors_list():
    return jsonify(store.all("competitors"))


@app.post("/api/competitors")
def competitors_create():
    payload = request.get_json(force=True, silent=True) or {}
    error = require_fields(payload, ["name", "category", "region", "current_price"])
    if error:
        return jsonify({"error": error}), 400
    current_price = as_float(payload.get("current_price"))
    document = {
        "name": payload["name"].strip(),
        "category": payload["category"].strip(),
        "website": payload.get("website", "").strip(),
        "region": payload["region"].strip(),
        "positioning": payload.get("positioning", "").strip(),
        "current_price": current_price,
        "previous_price": as_float(payload.get("previous_price"), current_price),
        "market_share": as_float(payload.get("market_share"), 0),
        "product_score": as_float(payload.get("product_score"), 70),
        "sentiment": as_float(payload.get("sentiment"), 70),
        "growth_rate": as_float(payload.get("growth_rate"), 0),
        "updated_at": utc_now(),
    }
    created = store.insert("competitors", document)
    store.insert(
        "price_history",
        {
            "competitor_id": created["_id"],
            "date": datetime.now().strftime("%Y-%m"),
            "price": current_price,
        },
    )
    return jsonify(created), 201


@app.put("/api/competitors/<competitor_id>")
def competitors_update(competitor_id):
    payload = request.get_json(force=True, silent=True) or {}
    allowed = {
        "name",
        "category",
        "website",
        "region",
        "positioning",
        "current_price",
        "previous_price",
        "market_share",
        "product_score",
        "sentiment",
        "growth_rate",
    }
    updates = {key: payload[key] for key in allowed if key in payload}
    for numeric in ["current_price", "previous_price", "market_share", "product_score", "sentiment", "growth_rate"]:
        if numeric in updates:
            updates[numeric] = as_float(updates[numeric])
    updates["updated_at"] = utc_now()
    updated = store.update("competitors", competitor_id, updates)
    if not updated:
        return jsonify({"error": "Competitor not found"}), 404
    return jsonify(updated)


@app.delete("/api/competitors/<competitor_id>")
def competitors_delete(competitor_id):
    deleted = store.delete("competitors", competitor_id)
    if not deleted:
        return jsonify({"error": "Competitor not found"}), 404
    return jsonify({"deleted": True})


@app.post("/api/prices")
def prices_create():
    payload = request.get_json(force=True, silent=True) or {}
    error = require_fields(payload, ["competitor_id", "date", "price"])
    if error:
        return jsonify({"error": error}), 400
    price = as_float(payload.get("price"))
    created = store.insert(
        "price_history",
        {
            "competitor_id": payload["competitor_id"],
            "date": payload["date"],
            "price": price,
        },
    )
    competitor = next((item for item in store.all("competitors") if item.get("_id") == payload["competitor_id"]), None)
    if competitor:
        store.update(
            "competitors",
            payload["competitor_id"],
            {"previous_price": competitor.get("current_price", price), "current_price": price, "updated_at": utc_now()},
        )
    return jsonify(created), 201


@app.post("/api/market-signals")
def market_signal_create():
    payload = request.get_json(force=True, silent=True) or {}
    error = require_fields(payload, ["area", "demand", "trend", "category"])
    if error:
        return jsonify({"error": error}), 400
    created = store.insert(
        "market_signals",
        {
            "area": payload["area"].strip(),
            "demand": as_int(payload.get("demand")),
            "trend": payload["trend"].strip(),
            "category": payload["category"].strip(),
        },
    )
    return jsonify(created), 201


@app.post("/api/alerts")
def alert_create():
    payload = request.get_json(force=True, silent=True) or {}
    error = require_fields(payload, ["severity", "title", "message"])
    if error:
        return jsonify({"error": error}), 400
    created = store.insert(
        "alerts",
        {
            "severity": payload["severity"].strip(),
            "title": payload["title"].strip(),
            "message": payload["message"].strip(),
            "created_at": utc_now(),
            "status": payload.get("status", "Open"),
        },
    )
    return jsonify(created), 201


@app.post("/api/reports")
def report_create():
    dashboard_data = build_dashboard()
    report = {
        "title": f"Competitive Intelligence Brief - {datetime.now().strftime('%B %d, %Y')}",
        "created_at": utc_now(),
        "summary": {
            "metrics": dashboard_data["metrics"],
            "top_competitors": dashboard_data["competitors"][:5],
            "alerts": dashboard_data["alerts"][:5],
        },
    }
    created = store.insert("reports", report)
    return jsonify(created), 201


@app.get("/api/recommendations")
def recommendations():
    dashboard_data = build_dashboard()
    try:
        return jsonify(ask_gemini(dashboard_data))
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
        return jsonify(
            {
                "source": "Rules engine",
                "items": generate_local_recommendations(dashboard_data),
                "note": f"Gemini response was unavailable, so rule-based recommendations were used. Detail: {exc}",
            }
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
