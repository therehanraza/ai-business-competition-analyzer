import json
import os
import re
import statistics
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError, ServerSelectionTimeoutError


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


def clean_string(value, fallback=""):
    return str(value if value is not None else fallback).strip()


def clamp_number(value, minimum=0, maximum=100, fallback=0):
    number = as_float(value, fallback)
    return max(minimum, min(maximum, number))


def validate_month(value):
    text = clean_string(value)
    if not re.fullmatch(r"\d{4}-\d{2}", text):
        return None
    month = int(text[-2:])
    return text if 1 <= month <= 12 else None


def validate_choice(value, allowed, fallback=None):
    text = clean_string(value, fallback or "")
    return text if text in allowed else fallback


def error_response(message, status=400):
    return jsonify({"error": message}), status


def public_api_metadata():
    return {
        "name": "AI Business Competition Analyzer API",
        "status": "ok",
        "store": store_name,
        "endpoints": {
            "health": "/api/health",
            "dashboard": "/api/dashboard",
            "analyze": "/api/analyze",
            "competitors": "/api/competitors",
            "prices": "/api/prices",
            "market_signals": "/api/market-signals",
            "activity_signals": "/api/activity-signals",
            "alerts": "/api/alerts",
            "reports": "/api/reports",
            "recommendations": "/api/recommendations",
            "battlecards": "/api/battlecards",
            "intelligence": "/api/intelligence",
            "copilot": "/api/copilot",
            "enrich_competitor": "/api/enrich-competitor",
            "track_competitor": "/api/track-competitor",
        },
    }


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
            "traffic_trend": 18,
            "hiring_activity": 14,
            "funding_news": "Expanded Series B round to fund enterprise sales hiring.",
            "product_launch": "Launched automated promotion attribution for retail teams.",
            "market_mentions": 128,
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
            "traffic_trend": 7,
            "hiring_activity": 6,
            "funding_news": "No recent funding event captured.",
            "product_launch": "Released marketplace repricing alerts.",
            "market_mentions": 84,
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
            "traffic_trend": 22,
            "hiring_activity": 18,
            "funding_news": "Raised strategic growth capital for Asia Pacific expansion.",
            "product_launch": "Introduced AI demand scenario planning.",
            "market_mentions": 96,
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
    "activity_signals": [
        {
            "_id": "s1",
            "competitor_id": "c_marketpulse",
            "type": "Product Launch",
            "sentiment": "Positive",
            "summary": "Automated promotion attribution launched for retail teams.",
            "impact_score": 82,
            "source": "Product page",
            "created_at": utc_now(),
        },
        {
            "_id": "s2",
            "competitor_id": "c_signalgrid",
            "type": "Hiring",
            "sentiment": "Positive",
            "summary": "Multiple enterprise sales and data science roles opened in Singapore.",
            "impact_score": 76,
            "source": "Careers page",
            "created_at": utc_now(),
        },
        {
            "_id": "s3",
            "competitor_id": "c_pricehawk",
            "type": "Pricing",
            "sentiment": "Negative",
            "summary": "Price increase may create buyer resistance in mid-market renewals.",
            "impact_score": 61,
            "source": "Pricing page",
            "created_at": utc_now(),
        },
    ],
    "reports": [],
    "battlecards": [],
}


class LocalStore:
    def __init__(self, path):
        self.path = path
        if not self.path.exists():
            self._write(deepcopy(STARTER_DATA))
        else:
            self._ensure_schema()

    def _read(self):
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, data):
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def _ensure_schema(self):
        data = self._read()
        changed = False
        for collection, starter_items in STARTER_DATA.items():
            if collection not in data:
                data[collection] = deepcopy(starter_items)
                changed = True
        starter_competitors = {item["_id"]: item for item in STARTER_DATA["competitors"]}
        for item in data.get("competitors", []):
            starter = starter_competitors.get(item.get("_id"), {})
            defaults = {
                "traffic_trend": starter.get("traffic_trend", 0),
                "hiring_activity": starter.get("hiring_activity", 0),
                "funding_news": starter.get("funding_news", "No funding update captured."),
                "product_launch": starter.get("product_launch", "No product launch captured."),
                "market_mentions": starter.get("market_mentions", 0),
            }
            for key, value in defaults.items():
                if key not in item:
                    item[key] = value
                    changed = True
        if changed:
            try:
                self._write(data)
            except PermissionError as exc:
                print(f"Local data schema migration skipped because the file is not writable: {exc}")

    def all(self, collection):
        return self._read().get(collection, [])

    def get(self, collection, document_id):
        return next(
            (item for item in self._read().get(collection, []) if str(item.get("_id")) == str(document_id)),
            None,
        )

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

    def delete_many(self, collection, field, value):
        data = self._read()
        before = len(data.get(collection, []))
        data[collection] = [item for item in data.get(collection, []) if str(item.get(field)) != str(value)]
        self._write(data)
        return before - len(data[collection])


class MongoStore:
    def __init__(self, uri, database):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        self.client.admin.command("ping")
        self.db = self.client[database]
        self.db.competitors.create_index([("name", ASCENDING)], unique=True)
        self.db.price_history.create_index([("competitor_id", ASCENDING), ("date", ASCENDING)])
        self.db.market_signals.create_index([("category", ASCENDING), ("area", ASCENDING)])
        self.db.alerts.create_index([("created_at", ASCENDING)])
        self.db.activity_signals.create_index([("competitor_id", ASCENDING), ("created_at", ASCENDING)])
        self.db.reports.create_index([("created_at", ASCENDING)])
        self.db.battlecards.create_index([("competitor_id", ASCENDING), ("created_at", ASCENDING)])
        self.seed_if_empty()

    def serialize(self, document):
        clean = {}
        for key, value in document.items():
            clean[key] = str(value) if key == "_id" else value
        return clean

    def all(self, collection):
        return [self.serialize(item) for item in self.db[collection].find({})]

    def get(self, collection, document_id):
        document = self.db[collection].find_one({"_id": document_id})
        return self.serialize(document) if document else None

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

    def delete_many(self, collection, field, value):
        return self.db[collection].delete_many({field: value}).deleted_count

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
    local_data_path = Path(os.getenv("LOCAL_DATA_PATH", BASE_DIR / "local_data.json"))
    return LocalStore(local_data_path), "Local JSON"


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


@app.errorhandler(DuplicateKeyError)
def duplicate_key(_):
    return jsonify({"error": "A record with that unique value already exists."}), 409


def sorted_price_history():
    return sorted(store.all("price_history"), key=lambda item: (item.get("competitor_id", ""), item.get("date", "")))


def get_document(collection, document_id):
    if hasattr(store, "get"):
        return store.get(collection, document_id)
    return next((item for item in store.all(collection) if str(item.get("_id")) == str(document_id)), None)


def delete_related_competitor_data(competitor_id):
    deleted = {
        "price_history": store.delete_many("price_history", "competitor_id", competitor_id),
        "battlecards": store.delete_many("battlecards", "competitor_id", competitor_id),
    }
    return deleted


def filtered_competitors():
    items = store.all("competitors")
    search = clean_string(request.args.get("q")).lower()
    category = clean_string(request.args.get("category")).lower()
    region = clean_string(request.args.get("region")).lower()
    if search:
        items = [
            item
            for item in items
            if search in clean_string(item.get("name")).lower()
            or search in clean_string(item.get("category")).lower()
            or search in clean_string(item.get("positioning")).lower()
        ]
    if category:
        items = [item for item in items if clean_string(item.get("category")).lower() == category]
    if region:
        items = [item for item in items if clean_string(item.get("region")).lower() == region]
    sort = request.args.get("sort", "name")
    reverse = request.args.get("order", "asc").lower() == "desc"
    allowed_sort = {"name", "category", "region", "current_price", "market_share", "product_score", "sentiment", "growth_rate"}
    if sort in allowed_sort:
        items = sorted(items, key=lambda item: item.get(sort, ""), reverse=reverse)
    return items


def get_competitor(competitor_id):
    return get_document("competitors", competitor_id)


def competitor_price_history(competitor_id):
    return [
        item
        for item in sorted_price_history()
        if str(item.get("competitor_id")) == str(competitor_id)
    ]


def sorted_reports():
    return sorted(store.all("reports"), key=lambda item: item.get("created_at", ""), reverse=True)


def sorted_alerts():
    return sorted(store.all("alerts"), key=lambda item: item.get("created_at", ""), reverse=True)


def sorted_battlecards():
    return sorted(store.all("battlecards"), key=lambda item: item.get("created_at", ""), reverse=True)


def competitor_payload(payload, existing=None):
    error = require_fields(payload, ["name", "category", "region", "current_price"]) if existing is None else None
    if error:
        return None, error

    document = deepcopy(existing) if existing else {}
    text_fields = ["name", "category", "website", "region", "positioning", "funding_news", "product_launch"]
    numeric_fields = {
        "current_price": (0, 10_000_000, document.get("current_price", 0)),
        "previous_price": (0, 10_000_000, document.get("previous_price", payload.get("current_price", 0))),
        "market_share": (0, 100, document.get("market_share", 0)),
        "product_score": (0, 100, document.get("product_score", 70)),
        "sentiment": (0, 100, document.get("sentiment", 70)),
        "growth_rate": (-100, 1000, document.get("growth_rate", 0)),
        "traffic_trend": (-100, 1000, document.get("traffic_trend", 0)),
        "hiring_activity": (0, 10_000, document.get("hiring_activity", 0)),
        "market_mentions": (0, 1_000_000, document.get("market_mentions", 0)),
    }

    for field in text_fields:
        if field in payload or existing is None:
            document[field] = clean_string(payload.get(field, document.get(field, "")))
    for field, (minimum, maximum, fallback) in numeric_fields.items():
        if field in payload or existing is None:
            document[field] = clamp_number(payload.get(field, fallback), minimum, maximum, fallback)
    if not document.get("name") or not document.get("category") or not document.get("region"):
        return None, "Name, category, and region are required."
    document["updated_at"] = utc_now()
    return document, None


def price_payload(payload, existing=None):
    error = require_fields(payload, ["competitor_id", "date", "price"]) if existing is None else None
    if error:
        return None, error
    document = deepcopy(existing) if existing else {}
    competitor_id = clean_string(payload.get("competitor_id", document.get("competitor_id")))
    if not get_competitor(competitor_id):
        return None, "Competitor not found."
    date = validate_month(payload.get("date", document.get("date")))
    if not date:
        return None, "Date must use YYYY-MM format."
    document.update(
        {
            "competitor_id": competitor_id,
            "date": date,
            "price": clamp_number(payload.get("price", document.get("price", 0)), 0, 10_000_000, 0),
            "updated_at": utc_now(),
        }
    )
    return document, None


def market_signal_payload(payload, existing=None):
    error = require_fields(payload, ["area", "demand", "trend", "category"]) if existing is None else None
    if error:
        return None, error
    document = deepcopy(existing) if existing else {}
    trend = validate_choice(payload.get("trend", document.get("trend")), {"Rising", "Stable", "Softening"}, "Stable")
    document.update(
        {
            "area": clean_string(payload.get("area", document.get("area"))),
            "demand": clamp_number(payload.get("demand", document.get("demand", 0)), 0, 100, 0),
            "trend": trend,
            "category": clean_string(payload.get("category", document.get("category"))),
            "updated_at": utc_now(),
        }
    )
    if not document["area"] or not document["category"]:
        return None, "Area and category are required."
    return document, None


def alert_payload(payload, existing=None):
    error = require_fields(payload, ["severity", "title", "message"]) if existing is None else None
    if error:
        return None, error
    document = deepcopy(existing) if existing else {"created_at": utc_now()}
    severity = validate_choice(payload.get("severity", document.get("severity")), {"High", "Medium", "Low"}, "Medium")
    status = validate_choice(payload.get("status", document.get("status")), {"Open", "In Review", "Closed"}, "Open")
    document.update(
        {
            "severity": severity,
            "title": clean_string(payload.get("title", document.get("title"))),
            "message": clean_string(payload.get("message", document.get("message"))),
            "status": status,
            "updated_at": utc_now(),
        }
    )
    if not document["title"] or not document["message"]:
        return None, "Title and message are required."
    if status == "Closed" and not document.get("closed_at"):
        document["closed_at"] = utc_now()
    if status != "Closed":
        document.pop("closed_at", None)
    return document, None


def activity_signal_payload(payload, existing=None):
    error = require_fields(payload, ["competitor_id", "type", "summary", "impact_score"]) if existing is None else None
    if error:
        return None, error
    document = deepcopy(existing) if existing else {"created_at": utc_now()}
    competitor_id = clean_string(payload.get("competitor_id", document.get("competitor_id")))
    if not get_competitor(competitor_id):
        return None, "Competitor not found."
    signal_type = validate_choice(
        payload.get("type", document.get("type")),
        {"Traffic", "Funding", "Hiring", "Product Launch", "Pricing", "Sentiment", "Market Mention"},
        "Market Mention",
    )
    signal_sentiment = validate_choice(
        payload.get("sentiment", document.get("sentiment")),
        {"Positive", "Neutral", "Negative"},
        "Neutral",
    )
    document.update(
        {
            "competitor_id": competitor_id,
            "type": signal_type,
            "sentiment": signal_sentiment,
            "summary": clean_string(payload.get("summary", document.get("summary"))),
            "impact_score": clamp_number(payload.get("impact_score", document.get("impact_score", 50)), 0, 100, 50),
            "metric_value": as_float(payload.get("metric_value", document.get("metric_value", 0))),
            "source": clean_string(payload.get("source", document.get("source")), "Manual entry"),
            "updated_at": utc_now(),
        }
    )
    if not document["summary"]:
        return None, "Summary is required."
    return document, None


def sync_competitor_from_activity(signal):
    competitor = get_competitor(signal["competitor_id"])
    if not competitor:
        return
    updates = {"updated_at": utc_now()}
    signal_type = signal.get("type")
    metric_value = as_float(signal.get("metric_value"))
    if signal_type == "Traffic" and metric_value:
        updates["traffic_trend"] = metric_value
    elif signal_type == "Hiring" and metric_value:
        updates["hiring_activity"] = metric_value
    elif signal_type == "Funding":
        updates["funding_news"] = signal.get("summary")
    elif signal_type == "Product Launch":
        updates["product_launch"] = signal.get("summary")
    elif signal_type == "Sentiment" and metric_value:
        updates["sentiment"] = clamp_number(metric_value, 0, 100, as_float(competitor.get("sentiment")))
    elif signal_type == "Market Mention" and metric_value:
        updates["market_mentions"] = metric_value
    store.update("competitors", signal["competitor_id"], {**competitor, **updates})


def sync_competitor_from_price(price_record):
    competitor = get_competitor(price_record["competitor_id"])
    if not competitor:
        return
    history = competitor_price_history(price_record["competitor_id"])
    if not history:
        return
    latest = sorted(history, key=lambda item: item.get("date", ""))[-1]
    prior_items = [item for item in history if item.get("_id") != latest.get("_id")]
    previous = sorted(prior_items, key=lambda item: item.get("date", ""))[-1]["price"] if prior_items else latest["price"]
    store.update(
        "competitors",
        price_record["competitor_id"],
        {
            "previous_price": as_float(previous),
            "current_price": as_float(latest["price"]),
            "updated_at": utc_now(),
        },
    )


def price_delta_percent(competitor):
    previous = as_float(competitor.get("previous_price"))
    current = as_float(competitor.get("current_price"))
    return round(((current - previous) / previous) * 100, 1) if previous else 0


def competitor_signal_score(competitor):
    pricing_change = abs(price_delta_percent(competitor))
    return round(
        clamp_number(
            as_float(competitor.get("growth_rate")) * 1.7
            + as_float(competitor.get("traffic_trend")) * 1.4
            + as_float(competitor.get("hiring_activity")) * 1.2
            + as_float(competitor.get("market_mentions")) * 0.18
            + as_float(competitor.get("sentiment")) * 0.18
            + pricing_change * 1.8,
            0,
            100,
            0,
        ),
        1,
    )


def predicted_next_move(competitor):
    price_delta = price_delta_percent(competitor)
    growth = as_float(competitor.get("growth_rate"))
    traffic = as_float(competitor.get("traffic_trend"))
    hiring = as_float(competitor.get("hiring_activity"))
    mentions = as_float(competitor.get("market_mentions"))
    launch = clean_string(competitor.get("product_launch"))
    funding = clean_string(competitor.get("funding_news"))

    if hiring >= 15 or "fund" in funding.lower() or "raised" in funding.lower():
        move = "Market expansion"
        rationale = "Funding or hiring momentum suggests the competitor is preparing to scale coverage."
    elif launch:
        move = "Product push"
        rationale = "A captured product launch suggests messaging and roadmap pressure will increase."
    elif price_delta <= -8:
        move = "Aggressive discounting"
        rationale = "Recent pricing movement points to a near-term acquisition or retention play."
    elif traffic >= 15 or growth >= 14 or mentions >= 100:
        move = "Awareness campaign"
        rationale = "Traffic, growth, and market mentions indicate demand-generation activity."
    else:
        move = "Steady positioning"
        rationale = "Signals are active but not strong enough to imply a major move yet."
    return {"move": move, "rationale": rationale}


def build_signal_digest(competitors, activity_signals, market_signals):
    active_alerts = []
    trend_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    performance_series = []

    for competitor in competitors:
        score = competitor_signal_score(competitor)
        price_change = price_delta_percent(competitor)
        prediction = predicted_next_move(competitor)
        direction = "positive" if score >= 58 and price_change >= -12 else "negative" if price_change <= -8 else "neutral"
        severity = "High" if score >= 74 or price_change <= -12 else "Medium" if score >= 50 or abs(price_change) >= 6 else "Low"
        title = f"{competitor.get('name')} shows {prediction['move'].lower()} signals"
        message = prediction["rationale"]
        if price_change <= -8:
            title = f"{competitor.get('name')} price dropped {abs(price_change)}%"
            message = "Pricing pressure is increasing. Review win-loss objections and discount guardrails."
        elif as_float(competitor.get("sentiment")) <= 58:
            title = f"{competitor.get('name')} sentiment weakened"
            message = "Customer sentiment has fallen below a healthy range. Prepare switching and comparison messaging."

        active_alerts.append(
            {
                "_id": f"auto_{competitor.get('_id')}",
                "severity": severity,
                "title": title,
                "message": message,
                "created_at": utc_now(),
                "status": "Open",
                "direction": direction,
                "auto_generated": True,
            }
        )

        base = max(8, score - (as_float(competitor.get("growth_rate")) * 1.5))
        performance_series.append(
            {
                "name": competitor.get("name"),
                "data": [
                    round(clamp_number(base + index * (as_float(competitor.get("growth_rate")) / 3), 0, 100, base), 1)
                    for index in range(len(trend_labels))
                ],
            }
        )

    sorted_competitors = sorted(competitors, key=competitor_signal_score, reverse=True)
    top_watch = [
        {
            "competitor_id": item.get("_id"),
            "name": item.get("name"),
            "website": item.get("website"),
            "score": competitor_signal_score(item),
            "growth_rate": as_float(item.get("growth_rate")),
            "traffic_trend": as_float(item.get("traffic_trend")),
            "hiring_activity": as_float(item.get("hiring_activity")),
            "market_mentions": as_float(item.get("market_mentions")),
            "sentiment": as_float(item.get("sentiment")),
            "funding_news": clean_string(item.get("funding_news"), "No funding update captured."),
            "product_launch": clean_string(item.get("product_launch"), "No launch captured."),
            "prediction": predicted_next_move(item),
        }
        for item in sorted_competitors[:6]
    ]

    strongest_market = max(market_signals, key=lambda item: as_float(item.get("demand")), default={})
    biggest_threat = top_watch[0] if top_watch else {}
    opportunities = [
        f"Target {strongest_market.get('area', 'the strongest region')} while demand is strongest.",
        "Use competitor pricing movement to create comparison pages and retention scripts.",
        "Turn weak competitor sentiment into switching campaigns with proof points and customer stories.",
    ]
    threats = [
        f"{biggest_threat.get('name', 'The highest-signal competitor')} may make the next major market move.",
        "Funding and hiring momentum can quickly shift sales coverage and brand awareness.",
        "Product launches can reset buyer expectations before your sales team updates its narrative.",
    ]
    summary = (
        f"{len(competitors)} competitors are being tracked across pricing, traffic, funding, hiring, launches, "
        f"sentiment, and market mentions. {biggest_threat.get('name', 'No competitor')} has the highest current signal score."
    )

    return {
        "summary": summary,
        "top_watch": top_watch,
        "activity_signals": sorted(activity_signals, key=lambda item: item.get("created_at", ""), reverse=True)[:8],
        "auto_alerts": sorted(active_alerts, key=lambda item: item.get("severity") != "High")[:6],
        "opportunities": opportunities,
        "threats": threats,
        "trend_labels": trend_labels,
        "performance_series": performance_series[:5],
    }


def build_dashboard():
    competitors = store.all("competitors")
    price_history = sorted_price_history()
    market_signals = store.all("market_signals")
    activity_signals = store.all("activity_signals")
    intelligence = build_signal_digest(competitors, activity_signals, market_signals)
    manual_alerts = sorted(store.all("alerts"), key=lambda item: item.get("created_at", ""), reverse=True)
    alerts = sorted(
        [*intelligence["auto_alerts"], *manual_alerts],
        key=lambda item: (item.get("severity") != "High", item.get("created_at", "")),
        reverse=False,
    )

    average_price = round(statistics.mean([as_float(c.get("current_price")) for c in competitors]), 2) if competitors else 0
    average_sentiment = round(statistics.mean([as_float(c.get("sentiment")) for c in competitors]), 1) if competitors else 0
    average_traffic = round(statistics.mean([as_float(c.get("traffic_trend")) for c in competitors]), 1) if competitors else 0
    total_mentions = round(sum(as_float(c.get("market_mentions")) for c in competitors), 1)
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
            "average_traffic_trend": average_traffic,
            "market_mentions": total_mentions,
            "positive_developments": len([alert for alert in intelligence["auto_alerts"] if alert.get("direction") == "positive"]),
            "negative_developments": len([alert for alert in intelligence["auto_alerts"] if alert.get("direction") == "negative"]),
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
            "performance_labels": intelligence["trend_labels"],
            "performance_series": intelligence["performance_series"],
        },
        "intelligence": intelligence,
        "competitors": competitors,
        "market_signals": market_signals,
        "alerts": alerts[:10],
    }


def classify_level(score):
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def build_business_profile(payload):
    price = payload.get("price", payload.get("current_price"))
    error = require_fields(
        {
            "business_name": payload.get("business_name"),
            "category": payload.get("category"),
            "region": payload.get("region"),
            "price": price,
        },
        ["business_name", "category", "region", "price"],
    )
    if error:
        return None, error

    profile = {
        "business_name": clean_string(payload.get("business_name")),
        "category": clean_string(payload.get("category")),
        "region": clean_string(payload.get("region")),
        "price": clamp_number(price, 0, 10_000_000, 0),
        "product_score": clamp_number(payload.get("product_score", 75), 0, 100, 75),
        "target_customer": clean_string(payload.get("target_customer"), "mid-market buyers"),
        "advantage": clean_string(payload.get("advantage"), "focused customer support and faster implementation"),
        "objective": clean_string(payload.get("objective"), "Find the best competitive position for market entry"),
    }
    return profile, None


def relevant_competitors_for_profile(profile):
    competitors = store.all("competitors")
    category = profile["category"].lower()
    region = profile["region"].lower()
    relevant = [
        competitor
        for competitor in competitors
        if clean_string(competitor.get("category")).lower() == category
        or clean_string(competitor.get("region")).lower() == region
    ]
    return relevant or competitors


def competitor_threat(profile, competitor):
    business_price = as_float(profile["price"])
    competitor_price = as_float(competitor.get("current_price"))
    price_gap_percent = round(((competitor_price - business_price) / business_price) * 100, 1) if business_price else 0
    if competitor_price < business_price * 0.85:
        price_pressure = 95
        price_reason = "it is materially cheaper"
    elif competitor_price < business_price:
        price_pressure = 72
        price_reason = "it is priced below your offer"
    elif competitor_price <= business_price * 1.15:
        price_pressure = 48
        price_reason = "pricing is close enough for direct comparison"
    else:
        price_pressure = 24
        price_reason = "it is positioned at a premium price"

    category_fit = 1 if clean_string(competitor.get("category")).lower() == profile["category"].lower() else 0.72
    region_fit = 1 if clean_string(competitor.get("region")).lower() == profile["region"].lower() else 0.82
    growth_signal = clamp_number(as_float(competitor.get("growth_rate")) * 5, 0, 100, 0)
    raw_score = (
        as_float(competitor.get("market_share")) * 0.28
        + as_float(competitor.get("product_score")) * 0.24
        + as_float(competitor.get("sentiment")) * 0.16
        + growth_signal * 0.20
        + price_pressure * 0.12
    )
    threat_score = round(clamp_number(raw_score * category_fit * region_fit, 0, 100, 0), 1)
    return {
        "competitor_id": competitor.get("_id"),
        "name": competitor.get("name"),
        "category": competitor.get("category"),
        "region": competitor.get("region"),
        "price": competitor_price,
        "price_gap_percent": price_gap_percent,
        "threat_score": threat_score,
        "threat_level": classify_level(threat_score),
        "reason": (
            f"{competitor.get('name')} has {competitor.get('market_share', 0)}% market share, "
            f"{competitor.get('product_score', 0)}/100 product score, and {price_reason}."
        ),
    }


def build_business_analysis(payload):
    profile, error = build_business_profile(payload)
    if error:
        return None, error

    competitors = relevant_competitors_for_profile(profile)
    market_signals = store.all("market_signals")
    category_signals = [
        signal
        for signal in market_signals
        if clean_string(signal.get("category")).lower() == profile["category"].lower()
    ] or market_signals
    strongest_signal = max(category_signals, key=lambda item: as_float(item.get("demand")), default={})

    threats = sorted(
        [competitor_threat(profile, competitor) for competitor in competitors],
        key=lambda item: item["threat_score"],
        reverse=True,
    )
    top_threats = threats[:5]
    pressure_score = round(statistics.mean([item["threat_score"] for item in top_threats]), 1) if top_threats else 0
    threat_level = classify_level(pressure_score)

    competitor_prices = [as_float(item.get("current_price")) for item in competitors if as_float(item.get("current_price"))]
    competitor_scores = [as_float(item.get("product_score")) for item in competitors if as_float(item.get("product_score"))]
    average_price = round(statistics.mean(competitor_prices), 2) if competitor_prices else 0
    average_score = round(statistics.mean(competitor_scores), 1) if competitor_scores else 0
    price_delta_percent = round(((profile["price"] - average_price) / average_price) * 100, 1) if average_price else 0

    if price_delta_percent <= -12:
        price_label = "Value challenger"
        price_detail = "Your offer is priced below the tracked competitor average."
    elif price_delta_percent >= 12:
        price_label = "Premium entrant"
        price_detail = "Your offer is above the tracked competitor average, so value proof matters."
    else:
        price_label = "Comparable price"
        price_detail = "Your offer is close to the tracked competitor average."

    demand = as_float(strongest_signal.get("demand"))
    opportunity_score = round(
        clamp_number((profile["product_score"] * 0.32) + (demand * 0.36) + ((100 - pressure_score) * 0.32), 0, 100, 0),
        1,
    )
    top_name = top_threats[0]["name"] if top_threats else "the current market leader"
    market_area = strongest_signal.get("area", profile["region"])

    strengths = [
        f"{profile['business_name']} can position around {profile['advantage']}.",
        f"Product readiness is scored at {profile['product_score']}/100.",
    ]
    if price_delta_percent <= 0:
        strengths.append(f"Pricing is {abs(price_delta_percent)}% below or near the competitor average.")
    else:
        strengths.append("Premium pricing can work if the sales story proves measurable value.")

    weaknesses = [
        "The business has no captured market share yet, so trust-building evidence is important.",
        f"Tracked competitors average {average_score}/100 product perception in this segment.",
    ]
    if price_delta_percent > 0:
        weaknesses.append("Higher pricing creates comparison risk unless ROI is clear.")
    else:
        weaknesses.append("Lower pricing may require careful positioning so it does not look like a weaker product.")

    opportunities = [
        f"{market_area} shows the strongest demand signal at {demand or 0}/100.",
        f"{profile['target_customer']} can be targeted with sharper positioning against broad competitor messaging.",
        "Pricing, demand, and alert data can be refreshed to keep recommendations current.",
    ]
    threats_list = [
        f"{top_name} is the highest-ranked threat in the current data.",
        "Competitors with strong growth and product scores can influence buyer perception early.",
        "Discounting competitors can pressure renewal and acquisition conversations.",
    ]
    action_plan = [
        f"Lead with {profile['advantage']} in every comparison against {top_name}.",
        f"Target {market_area} first because it has the strongest demand signal.",
        f"Use {price_label.lower()} messaging and explain price using outcomes, not only features.",
        "Create one comparison page for the top three threats and update it monthly.",
        "Track price changes, product scores, alerts, and market demand before every review meeting.",
    ]

    return {
        "source": "Competition scoring model",
        "method": "Weighted analysis using competitor price, product score, sentiment, market share, growth, regional fit, and demand signals.",
        "business_profile": profile,
        "summary": (
            f"{profile['business_name']} faces {threat_level.lower()} competitive pressure in "
            f"{profile['category']}. The best initial opportunity is {market_area}, while {top_name} "
            f"is the clearest competitor to watch."
        ),
        "competition_pressure_score": pressure_score,
        "opportunity_score": opportunity_score,
        "threat_level": threat_level,
        "price_position": {
            "label": price_label,
            "detail": price_detail,
            "average_competitor_price": average_price,
            "price_delta_percent": price_delta_percent,
        },
        "market_opportunity": {
            "area": market_area,
            "demand": demand,
            "trend": strongest_signal.get("trend", "Unknown"),
            "category": strongest_signal.get("category", profile["category"]),
        },
        "top_threats": top_threats,
        "swot": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats_list,
        },
        "action_plan": action_plan,
        "note": "Add GEMINI_API_KEY to backend/.env when you want Gemini to rewrite the analysis narrative; the scoring model works offline for demos.",
    }, None


def build_competitor_profile(competitor_id):
    competitor = get_competitor(competitor_id)
    if not competitor:
        return None

    history = competitor_price_history(competitor_id)
    latest_signal = next(
        (
            signal
            for signal in sorted(store.all("market_signals"), key=lambda item: as_float(item.get("demand")), reverse=True)
            if signal.get("category") == competitor.get("category")
        ),
        None,
    )
    open_alerts = [
        alert
        for alert in build_dashboard().get("alerts", [])
        if alert.get("status") == "Open"
    ]
    previous = as_float(competitor.get("previous_price"))
    current = as_float(competitor.get("current_price"))
    price_delta = round(current - previous, 2)
    price_delta_percent = round(((current - previous) / previous) * 100, 1) if previous else 0

    return {
        "competitor": competitor,
        "price_history": history,
        "market_signal": latest_signal,
        "alerts": open_alerts[:5],
        "metrics": {
            "current_price": current,
            "previous_price": previous,
            "price_delta": price_delta,
            "price_delta_percent": price_delta_percent,
            "market_share": as_float(competitor.get("market_share")),
            "product_score": as_float(competitor.get("product_score")),
            "sentiment": as_float(competitor.get("sentiment")),
            "growth_rate": as_float(competitor.get("growth_rate")),
            "traffic_trend": as_float(competitor.get("traffic_trend")),
            "hiring_activity": as_float(competitor.get("hiring_activity")),
            "market_mentions": as_float(competitor.get("market_mentions")),
            "signal_score": competitor_signal_score(competitor),
        },
        "prediction": predicted_next_move(competitor),
        "activity_signals": [
            item
            for item in sorted(store.all("activity_signals"), key=lambda item: item.get("created_at", ""), reverse=True)
            if item.get("competitor_id") == competitor_id
        ][:5],
    }


def generate_local_battlecard(profile, objective):
    competitor = profile["competitor"]
    metrics = profile["metrics"]
    signal = profile.get("market_signal") or {}
    price_direction = "discounting" if metrics["price_delta"] < 0 else "raising price" if metrics["price_delta"] > 0 else "holding price"
    share = metrics["market_share"]
    score = metrics["product_score"]
    sentiment = metrics["sentiment"]
    demand = as_float(signal.get("demand"))

    return {
        "source": "Rules engine",
        "competitor_id": competitor["_id"],
        "competitor_name": competitor["name"],
        "objective": objective,
        "headline": f"{competitor['name']} is {price_direction} while carrying a {score}/100 product perception score and a {metrics['signal_score']}/100 intelligence score.",
        "positioning": competitor.get("positioning") or "No positioning statement has been captured yet.",
        "quick_stats": [
            {"label": "Current price", "value": f"${metrics['current_price']:,.0f}"},
            {"label": "Price change", "value": f"{metrics['price_delta_percent']}%"},
            {"label": "Market share", "value": f"{share}%"},
            {"label": "Sentiment", "value": f"{sentiment}/100"},
            {"label": "Traffic trend", "value": f"{metrics['traffic_trend']}%"},
            {"label": "Hiring", "value": f"{metrics['hiring_activity']} roles"},
        ],
        "strengths": [
            f"Strong product perception at {score}/100.",
            f"Category traction is visible in {signal.get('area', 'tracked markets')} with demand around {demand or 'unknown'}.",
            f"Growth signal is {metrics['growth_rate']}%, so the account team should assume active pipeline momentum.",
            f"Next likely move: {profile['prediction']['move']}.",
        ],
        "weaknesses": [
            "Pricing movement creates room to question discount sustainability." if metrics["price_delta"] < 0 else "Stable pricing leaves room to win on faster time-to-value.",
            "Market share is meaningful but not dominant, so challenger positioning can still work.",
            "Captured data is mostly structured intelligence; add win-loss notes for a sharper narrative.",
        ],
        "talk_track": [
            f"Lead with business outcomes in {competitor.get('category', 'the category')}, then contrast speed, support, and implementation risk.",
            "Ask the buyer what changed internally that made them evaluate alternatives now.",
            "Anchor pricing to measurable value before responding to competitor discounts.",
        ],
        "recommended_moves": [
            "Create a one-page comparison for sales using price, implementation timeline, and support model.",
            "Add a pricing alert for the next 30 days and review any new movement weekly.",
            "Run a targeted campaign in the strongest demand area captured for this category.",
            "Monitor website, hiring, funding, launch, and sentiment signals before the next sales review.",
        ],
        "risk_level": "High" if metrics["price_delta_percent"] <= -8 or metrics["growth_rate"] >= 14 else "Medium",
    }


def generate_local_recommendations(dashboard):
    competitors = dashboard["competitors"]
    alerts = dashboard["alerts"]
    metrics = dashboard["metrics"]
    intelligence = dashboard.get("intelligence", {})
    top_watch = (intelligence.get("top_watch") or [{}])[0]
    fastest = max(competitors, key=lambda item: as_float(item.get("growth_rate")), default={})
    strongest = max(competitors, key=lambda item: as_float(item.get("product_score")), default={})
    pressure = max(competitors, key=lambda item: as_float(item.get("previous_price")) - as_float(item.get("current_price")), default={})

    recommendations = [
        {
            "title": "Protect high-intent accounts from pricing pressure",
            "priority": "High",
            "recommendation": f"{pressure.get('name', 'A competitor')} is creating pricing pressure. Create a retention offer and monitor win-loss notes weekly.",
        },
        {
            "title": "Respond to the highest signal competitor",
            "priority": "High",
            "recommendation": f"{top_watch.get('name', fastest.get('name', 'A competitor'))} has the highest combined signal score. Prepare a response to its likely next move: {(top_watch.get('prediction') or {}).get('move', 'market push')}.",
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
            "recommendation": f"{fastest.get('name', 'A fast-growing competitor')} has the highest growth signal. Add alert rules for traffic, pricing, funding, hiring, launches, and regional demand changes.",
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


def gemini_model_name():
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip() or "gemini-flash-latest"


def parse_gemini_json(response):
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def infer_company_domain(name, website=""):
    text = " ".join([clean_string(name), clean_string(website)]).lower()
    if "chatgpt" in text or "openai" in text:
        return "AI Assistant Platform", 20
    if any(word in text for word in ["price", "repric", "billing", "chargebee", "stripe"]):
        return "Pricing Intelligence", 129
    if any(word in text for word in ["retail", "shop", "commerce", "store", "market"]):
        return "Retail Analytics", 179
    if any(word in text for word in ["demand", "forecast", "supply", "inventory", "grid"]):
        return "Demand Forecasting", 199
    if any(word in text for word in ["crm", "sales", "hub", "lead"]):
        return "Sales Intelligence", 149
    if any(word in text for word in ["traffic", "similar", "seo", "web"]):
        return "Market Intelligence", 119
    return "AI Business Intelligence", 159


def infer_region(website=""):
    url = clean_string(website).lower()
    if url.endswith(".in") or ".in/" in url:
        return "India"
    if url.endswith(".uk") or ".uk/" in url or ".eu" in url:
        return "Europe"
    if ".sg" in url or ".asia" in url:
        return "Asia Pacific"
    if ".ca" in url:
        return "North America"
    return "Global"


def pricing_plans_for_company(name, category, current_price):
    text = name.lower()
    if "chatgpt" in text or "openai" in text:
        return [
            {"name": "Free", "price": 0, "billing": "monthly", "audience": "individuals", "note": "Free individual plan with limited access."},
            {"name": "Go", "price": 8, "billing": "monthly", "audience": "individuals", "note": "Lower-cost individual plan; localized pricing may differ by country."},
            {"name": "Plus", "price": 20, "billing": "monthly", "audience": "individuals", "note": "Advanced intelligence, projects, tasks, custom GPTs, and expanded usage."},
            {"name": "Pro", "price": 200, "billing": "monthly", "audience": "power users", "note": "Maximum usage, pro reasoning, deep research, agent mode, and higher limits."},
            {"name": "Business", "price": 30, "billing": "per user/month", "audience": "teams", "note": "Team workspace; lower per-user annual billing may be available."},
            {"name": "Enterprise", "price": None, "billing": "custom", "audience": "large organizations", "note": "Custom pricing, admin, security, and enterprise controls."},
        ]
    low_price = max(0, round(current_price * 0.55))
    return [
        {"name": "Starter", "price": low_price, "billing": "monthly", "audience": "small teams", "note": f"Entry {category.lower()} package."},
        {"name": "Growth", "price": current_price, "billing": "monthly", "audience": "mid-market teams", "note": "Main plan used for price-position comparison."},
        {"name": "Business", "price": round(current_price * 1.65), "billing": "monthly", "audience": "larger teams", "note": "More usage, seats, and workflow controls."},
        {"name": "Enterprise", "price": None, "billing": "custom", "audience": "enterprise buyers", "note": "Custom quote for security, scale, and support."},
    ]


def local_competitor_enrichment(payload):
    name = clean_string(payload.get("name") or payload.get("business_name"))
    website = clean_string(payload.get("website"))
    if not name:
        return None, "Competitor name is required."

    category, base_price = infer_company_domain(name, website)
    region = clean_string(payload.get("region"), infer_region(website))
    signal_seed = sum(ord(char) for char in name.lower())
    product_score = 72 + signal_seed % 18
    sentiment = 66 + signal_seed % 22
    growth_rate = 6 + signal_seed % 15
    traffic_trend = 4 + signal_seed % 24
    hiring_activity = 3 + signal_seed % 18
    market_mentions = 45 + signal_seed % 140
    current_price = base_price + (signal_seed % 5) * 20
    previous_price = max(0, current_price + ([20, -10, 0, 30, -20][signal_seed % 5]))
    launch_focus = {
        "Pricing Intelligence": "released automated pricing-change alerts and competitor price movement detection",
        "Retail Analytics": "expanded promotion analytics and merchandising performance dashboards",
        "Demand Forecasting": "introduced AI scenario planning for regional demand shifts",
        "Sales Intelligence": "launched account scoring and sales battlecard automation",
        "Market Intelligence": "added web traffic and share-of-attention monitoring",
    }.get(category, "expanded AI-assisted market and competitor intelligence workflows")
    profile = {
        "name": name,
        "category": category,
        "website": website or f"https://{re.sub(r'[^a-z0-9]+', '', name.lower())}.com",
        "region": region,
        "positioning": f"{name} appears positioned as a {category.lower()} platform for teams that need faster competitive decisions.",
        "current_price": current_price,
        "previous_price": previous_price,
        "market_share": 8 + signal_seed % 18,
        "product_score": product_score,
        "sentiment": sentiment,
        "growth_rate": growth_rate,
        "traffic_trend": traffic_trend,
        "hiring_activity": hiring_activity,
        "market_mentions": market_mentions,
        "funding_news": "No verified funding event is connected yet; keep this company on the funding watchlist.",
        "product_launch": f"AI enrichment suggests {name} recently {launch_focus}.",
    }
    profile["pricing_plans"] = pricing_plans_for_company(name, category, current_price)
    if "chatgpt" in name.lower() or "openai" in name.lower():
        profile.update(
            {
                "category": "AI Assistant Platform",
                "positioning": "ChatGPT is OpenAI's AI assistant platform for individuals, teams, developers, and enterprises.",
                "current_price": 20,
                "previous_price": 20,
                "price_summary": "Plan range: Free, Go $8/mo, Plus $20/mo, Pro $200/mo, Business per user, Enterprise custom.",
                "data_quality": "Known public pricing profile",
                "funding_news": "OpenAI is a major AI platform company; use funding/news signals only when connected to live sources.",
                "product_launch": "ChatGPT plans differ by usage limits, model access, team workspace controls, and enterprise security.",
            }
        )
    return {
        "source": "AI enrichment model",
        "confidence": "Estimated",
        "profile": profile,
        "insights": [
            f"{name} is most relevant to the {category} category.",
            f"Market focus is set to {region}; dashboard demand and recommendations will prioritize that country/region.",
            f"Initial signal model estimates {traffic_trend}% traffic movement and {market_mentions} market mentions.",
            "The system will track pricing, launch, hiring, traffic, sentiment, and market-mention changes after this company is added.",
        ],
        "activity_signal": {
            "type": "Product Launch",
            "sentiment": "Positive" if product_score >= 78 else "Neutral",
            "summary": profile["product_launch"],
            "impact_score": min(100, round((product_score + traffic_trend + growth_rate) / 1.9)),
            "metric_value": traffic_trend,
            "source": website or "AI enrichment",
        },
        "market_signal": {
            "area": region,
            "demand": min(100, 68 + signal_seed % 26),
            "trend": "Rising" if growth_rate >= 12 else "Stable",
            "category": category,
        },
        "next_tracking_actions": [
            "Review auto-filled fields and start tracking.",
            "Generate a battlecard after the company appears in the watchlist.",
            "Refresh the dashboard to see pricing, market, and threat signals update.",
        ],
    }, None


def ask_gemini_enrichment(payload):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = gemini_model_name()
    if not api_key:
        enrichment, error = local_competitor_enrichment(payload)
        if enrichment:
            enrichment["note"] = "AI enrichment is running from the built-in signal model. Add GEMINI_API_KEY for Gemini-generated enrichment."
        return enrichment, error

    prompt = {
        "role": "competitive intelligence researcher",
        "instruction": "Return strict JSON only. Enrich the requested competitor for a business intelligence app. Use public business knowledge when known; if exact values are unavailable, produce reasonable estimates and set confidence to Estimated. Do not leave required profile fields blank.",
        "schema": {
            "source": "Google Gemini",
            "confidence": "High|Medium|Estimated",
            "profile": {
                "name": "string",
                "category": "string",
                "website": "string",
                "region": "string",
                "positioning": "string",
                "current_price": "number",
                "previous_price": "number",
                "market_share": "number 0-100",
                "product_score": "number 0-100",
                "sentiment": "number 0-100",
                "growth_rate": "number",
                "traffic_trend": "number",
                "hiring_activity": "number",
                "market_mentions": "number",
                "funding_news": "string",
                "product_launch": "string",
                "pricing_plans": [
                    {
                        "name": "string",
                        "price": "number or null when custom/varies",
                        "billing": "string",
                        "audience": "string",
                        "note": "string",
                    }
                ],
            },
            "insights": ["string"],
            "activity_signal": {
                "type": "Traffic|Funding|Hiring|Product Launch|Pricing|Sentiment|Market Mention",
                "sentiment": "Positive|Neutral|Negative",
                "summary": "string",
                "impact_score": "number 0-100",
                "metric_value": "number",
                "source": "string",
            },
            "market_signal": {"area": "string", "demand": "number 0-100", "trend": "Rising|Stable|Softening", "category": "string"},
            "next_tracking_actions": ["string"],
        },
        "request": payload,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": json.dumps(prompt)}]}]},
        timeout=25,
    )
    response.raise_for_status()
    parsed = parse_gemini_json(response)
    parsed["source"] = "Google Gemini"
    parsed["note"] = f"Powered by {model}."
    return parsed, None


def normalize_enrichment(enrichment):
    raw_profile = enrichment.get("profile", {})
    profile, error = competitor_payload(raw_profile)
    if error:
        return None, error
    for optional_field in ["price_summary", "data_quality"]:
        if clean_string(raw_profile.get(optional_field)):
            profile[optional_field] = clean_string(raw_profile.get(optional_field))
    raw_plans = enrichment.get("profile", {}).get("pricing_plans", [])
    if isinstance(raw_plans, list):
        profile["pricing_plans"] = [
            {
                "name": clean_string(plan.get("name"), "Plan"),
                "price": None if plan.get("price") in (None, "") else clamp_number(plan.get("price"), 0, 10_000_000, 0),
                "billing": clean_string(plan.get("billing"), "monthly"),
                "audience": clean_string(plan.get("audience"), "customers"),
                "note": clean_string(plan.get("note"), ""),
            }
            for plan in raw_plans
            if isinstance(plan, dict)
        ]
    activity = enrichment.get("activity_signal") or {}
    market = enrichment.get("market_signal") or {}
    enrichment["profile"] = profile
    enrichment["activity_signal"] = {
        "type": validate_choice(activity.get("type"), {"Traffic", "Funding", "Hiring", "Product Launch", "Pricing", "Sentiment", "Market Mention"}, "Product Launch"),
        "sentiment": validate_choice(activity.get("sentiment"), {"Positive", "Neutral", "Negative"}, "Neutral"),
        "summary": clean_string(activity.get("summary"), profile.get("product_launch", "Initial competitor activity captured.")),
        "impact_score": clamp_number(activity.get("impact_score"), 0, 100, 70),
        "metric_value": as_float(activity.get("metric_value"), profile.get("traffic_trend", 0)),
        "source": clean_string(activity.get("source"), profile.get("website", "AI enrichment")),
    }
    enrichment["market_signal"] = {
        "area": clean_string(market.get("area"), profile.get("region", "Global")),
        "demand": clamp_number(market.get("demand"), 0, 100, 75),
        "trend": validate_choice(market.get("trend"), {"Rising", "Stable", "Softening"}, "Stable"),
        "category": clean_string(market.get("category"), profile.get("category")),
    }
    enrichment["confidence"] = clean_string(enrichment.get("confidence"), "Estimated")
    enrichment["insights"] = [clean_string(item) for item in enrichment.get("insights", []) if clean_string(item)]
    enrichment["next_tracking_actions"] = [
        clean_string(item) for item in enrichment.get("next_tracking_actions", []) if clean_string(item)
    ]
    return enrichment, None


def ask_gemini(dashboard):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = gemini_model_name()
    if not api_key:
        return {
            "source": "Rules engine",
            "items": generate_local_recommendations(dashboard),
            "note": f"Add GEMINI_API_KEY to backend/.env to enable Gemini-powered recommendations with {model}.",
        }

    prompt = {
        "role": "competitive intelligence strategist",
        "instruction": "Return strict JSON only. Create five concise executive recommendations from competitor pricing, growth, traffic, funding, hiring, launches, sentiment, market mentions, alerts, predictions, opportunities, and threats.",
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
    parsed = parse_gemini_json(response)
    return {"source": "Google Gemini", "items": parsed.get("items", []), "note": f"Powered by {model}."}


def ask_gemini_battlecard(profile, objective):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = gemini_model_name()
    if not api_key:
        card = generate_local_battlecard(profile, objective)
        card["note"] = f"Add GEMINI_API_KEY to backend/.env to enable Gemini-powered battlecards with {model}."
        return card

    prompt = {
        "role": "competitive intelligence strategist",
        "instruction": "Return strict JSON only. Create a concise competitive battlecard for the selected competitor using pricing, growth, traffic, funding, hiring, launch, sentiment, market mention, alert, and prediction signals.",
        "schema": {
            "competitor_id": "string",
            "competitor_name": "string",
            "objective": "string",
            "headline": "string",
            "positioning": "string",
            "quick_stats": [{"label": "string", "value": "string"}],
            "strengths": ["string"],
            "weaknesses": ["string"],
            "talk_track": ["string"],
            "recommended_moves": ["string"],
            "risk_level": "High|Medium|Low",
        },
        "objective": objective,
        "profile": profile,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": json.dumps(prompt)}]}]},
        timeout=25,
    )
    response.raise_for_status()
    parsed = parse_gemini_json(response)
    parsed["source"] = "Google Gemini"
    parsed["note"] = f"Powered by {model}."
    return parsed


def answer_copilot_locally(question, dashboard_data):
    intelligence = dashboard_data.get("intelligence", {})
    top_watch = intelligence.get("top_watch", [])
    alerts = dashboard_data.get("alerts", [])
    recommendations = generate_local_recommendations(dashboard_data)[:3]
    leader = top_watch[0] if top_watch else {}
    question_text = clean_string(question, "Summarize competitor activity")
    answer = (
        f"For '{question_text}', the strongest competitive signal is {leader.get('name', 'not available')} "
        f"with a {leader.get('score', 0)}/100 signal score. Its likely next move is "
        f"{(leader.get('prediction') or {}).get('move', 'steady positioning')}. "
        f"There are {len([alert for alert in alerts if alert.get('status') == 'Open'])} open alerts, "
        f"including pricing, growth, hiring, launch, traffic, sentiment, and market-mention signals."
    )
    return {
        "source": "Rules engine",
        "answer": answer,
        "bullets": [
            intelligence.get("summary", "No intelligence summary is available."),
            *(item["recommendation"] for item in recommendations),
        ],
        "follow_up": "Ask about a specific competitor, pricing pressure, growth threat, opportunity, or recommended response.",
        "note": f"Add GEMINI_API_KEY to backend/.env to enable Gemini copilot answers with {gemini_model_name()}.",
    }


def ask_gemini_copilot(question, dashboard_data):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = gemini_model_name()
    if not api_key:
        return answer_copilot_locally(question, dashboard_data)

    prompt = {
        "role": "AI competitor-intelligence copilot",
        "instruction": "Return strict JSON only. Answer the user's competitive-positioning question concisely with strategic recommendations grounded in the dashboard data.",
        "schema": {
            "answer": "string",
            "bullets": ["string"],
            "follow_up": "string",
        },
        "question": clean_string(question),
        "dashboard": dashboard_data,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": json.dumps(prompt)}]}]},
        timeout=25,
    )
    response.raise_for_status()
    parsed = parse_gemini_json(response)
    return {
        "source": "Google Gemini",
        "answer": parsed.get("answer", ""),
        "bullets": parsed.get("bullets", []),
        "follow_up": parsed.get("follow_up", ""),
        "note": f"Powered by {model}.",
    }


@app.get("/")
def root():
    return jsonify(public_api_metadata())


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "store": store_name, "timestamp": utc_now()})


@app.get("/api/dashboard")
def dashboard():
    return jsonify(build_dashboard())


@app.get("/api/intelligence")
def intelligence():
    return jsonify(build_dashboard()["intelligence"])


@app.post("/api/copilot")
def copilot():
    payload = request.get_json(force=True, silent=True) or {}
    question = clean_string(payload.get("question"))
    if not question:
        return error_response("Question is required.")
    dashboard_data = build_dashboard()
    try:
        return jsonify(ask_gemini_copilot(question, dashboard_data))
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
        fallback = answer_copilot_locally(question, dashboard_data)
        fallback["note"] = f"Gemini response was unavailable, so a rule-based copilot answer was used. Detail: {exc}"
        return jsonify(fallback)


@app.post("/api/enrich-competitor")
def enrich_competitor():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        enrichment, error = ask_gemini_enrichment(payload)
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
        enrichment, error = local_competitor_enrichment(payload)
        if enrichment:
            enrichment["note"] = f"Gemini enrichment was unavailable, so the built-in signal model was used. Detail: {exc}"
    if error:
        return error_response(error)
    normalized, error = normalize_enrichment(enrichment)
    if error:
        return error_response(error)
    return jsonify(normalized)


@app.post("/api/track-competitor")
def track_competitor():
    payload = request.get_json(force=True, silent=True) or {}
    enrichment = payload.get("enrichment")
    if not enrichment:
        try:
            enrichment, error = ask_gemini_enrichment(payload)
        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
            enrichment, error = local_competitor_enrichment(payload)
            if enrichment:
                enrichment["note"] = f"Gemini enrichment was unavailable, so the built-in signal model was used. Detail: {exc}"
        if error:
            return error_response(error)

    normalized, error = normalize_enrichment(enrichment)
    if error:
        return error_response(error)

    profile = normalized["profile"]
    existing = next(
        (item for item in store.all("competitors") if clean_string(item.get("name")).lower() == profile["name"].lower()),
        None,
    )
    if existing:
        return jsonify({"created": False, "competitor": existing, "enrichment": normalized})

    try:
        created = store.insert("competitors", profile)
    except DuplicateKeyError:
        return error_response("Competitor name already exists.", 409)

    store.insert(
        "price_history",
        {
            "competitor_id": created["_id"],
            "date": datetime.now().strftime("%Y-%m"),
            "price": as_float(created.get("current_price")),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
    )
    activity = store.insert(
        "activity_signals",
        {
            **normalized["activity_signal"],
            "competitor_id": created["_id"],
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
    )
    market = store.insert(
        "market_signals",
        {
            **normalized["market_signal"],
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
    )
    return jsonify({"created": True, "competitor": created, "activity_signal": activity, "market_signal": market, "enrichment": normalized}), 201


@app.post("/api/analyze")
def analyze_business():
    payload = request.get_json(force=True, silent=True) or {}
    analysis, error = build_business_analysis(payload)
    if error:
        return error_response(error)
    return jsonify(analysis)


@app.get("/api/competitors")
def competitors_list():
    return jsonify(filtered_competitors())


@app.get("/api/competitors/<competitor_id>")
def competitors_detail(competitor_id):
    competitor = get_competitor(competitor_id)
    if not competitor:
        return error_response("Competitor not found", 404)
    return jsonify(
        {
            **competitor,
            "price_history": competitor_price_history(competitor_id),
            "battlecards": [
                card for card in sorted_battlecards() if str(card.get("competitor_id")) == str(competitor_id)
            ],
        }
    )


@app.post("/api/competitors")
def competitors_create():
    payload = request.get_json(force=True, silent=True) or {}
    document, error = competitor_payload(payload)
    if error:
        return error_response(error)
    if any(clean_string(item.get("name")).lower() == document["name"].lower() for item in store.all("competitors")):
        return error_response("Competitor name already exists.", 409)
    current_price = as_float(document["current_price"])
    try:
        created = store.insert("competitors", document)
    except DuplicateKeyError:
        return error_response("Competitor name already exists.", 409)
    store.insert(
        "price_history",
        {
            "competitor_id": created["_id"],
            "date": datetime.now().strftime("%Y-%m"),
            "price": current_price,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
    )
    return jsonify(created), 201


@app.put("/api/competitors/<competitor_id>")
def competitors_update(competitor_id):
    existing = get_competitor(competitor_id)
    if not existing:
        return error_response("Competitor not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    document, error = competitor_payload(payload, existing)
    if error:
        return error_response(error)
    if any(
        clean_string(item.get("name")).lower() == document["name"].lower()
        and str(item.get("_id")) != str(competitor_id)
        for item in store.all("competitors")
    ):
        return error_response("Competitor name already exists.", 409)
    old_price = as_float(existing.get("current_price"))
    new_price = as_float(document.get("current_price"))
    if "current_price" in payload and new_price != old_price:
        document["previous_price"] = old_price
        store.insert(
            "price_history",
            {
                "competitor_id": competitor_id,
                "date": datetime.now().strftime("%Y-%m"),
                "price": new_price,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            },
        )
    try:
        updated = store.update("competitors", competitor_id, document)
    except DuplicateKeyError:
        return error_response("Competitor name already exists.", 409)
    return jsonify(updated)


@app.delete("/api/competitors/<competitor_id>")
def competitors_delete(competitor_id):
    deleted = store.delete("competitors", competitor_id)
    if not deleted:
        return error_response("Competitor not found", 404)
    related = delete_related_competitor_data(competitor_id)
    return jsonify({"deleted": True, "related_deleted": related})


@app.get("/api/prices")
@app.get("/api/price-history")
def prices_list():
    competitor_id = request.args.get("competitor_id")
    if competitor_id:
        if not get_competitor(competitor_id):
            return error_response("Competitor not found", 404)
        return jsonify(competitor_price_history(competitor_id))
    return jsonify(sorted_price_history())


@app.get("/api/prices/<price_id>")
def prices_detail(price_id):
    price = get_document("price_history", price_id)
    if not price:
        return error_response("Price record not found", 404)
    return jsonify(price)


@app.post("/api/prices")
def prices_create():
    payload = request.get_json(force=True, silent=True) or {}
    document, error = price_payload(payload)
    if error:
        return error_response(error)
    document["created_at"] = utc_now()
    created = store.insert("price_history", document)
    sync_competitor_from_price(created)
    return jsonify(created), 201


@app.put("/api/prices/<price_id>")
def prices_update(price_id):
    existing = get_document("price_history", price_id)
    if not existing:
        return error_response("Price record not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    document, error = price_payload(payload, existing)
    if error:
        return error_response(error)
    updated = store.update("price_history", price_id, document)
    if existing.get("competitor_id") != updated.get("competitor_id"):
        sync_competitor_from_price(existing)
    sync_competitor_from_price(updated)
    return jsonify(updated)


@app.delete("/api/prices/<price_id>")
def prices_delete(price_id):
    existing = get_document("price_history", price_id)
    if not existing:
        return error_response("Price record not found", 404)
    store.delete("price_history", price_id)
    sync_competitor_from_price(existing)
    return jsonify({"deleted": True})


@app.get("/api/market-signals")
def market_signals_list():
    signals = store.all("market_signals")
    category = clean_string(request.args.get("category")).lower()
    trend = clean_string(request.args.get("trend")).lower()
    if category:
        signals = [item for item in signals if clean_string(item.get("category")).lower() == category]
    if trend:
        signals = [item for item in signals if clean_string(item.get("trend")).lower() == trend]
    return jsonify(sorted(signals, key=lambda item: as_float(item.get("demand")), reverse=True))


@app.get("/api/market-signals/<signal_id>")
def market_signal_detail(signal_id):
    signal = get_document("market_signals", signal_id)
    if not signal:
        return error_response("Market signal not found", 404)
    return jsonify(signal)


@app.post("/api/market-signals")
def market_signal_create():
    payload = request.get_json(force=True, silent=True) or {}
    document, error = market_signal_payload(payload)
    if error:
        return error_response(error)
    document["created_at"] = utc_now()
    created = store.insert("market_signals", document)
    return jsonify(created), 201


@app.put("/api/market-signals/<signal_id>")
def market_signal_update(signal_id):
    existing = get_document("market_signals", signal_id)
    if not existing:
        return error_response("Market signal not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    document, error = market_signal_payload(payload, existing)
    if error:
        return error_response(error)
    return jsonify(store.update("market_signals", signal_id, document))


@app.delete("/api/market-signals/<signal_id>")
def market_signal_delete(signal_id):
    deleted = store.delete("market_signals", signal_id)
    if not deleted:
        return error_response("Market signal not found", 404)
    return jsonify({"deleted": True})


@app.get("/api/activity-signals")
def activity_signals_list():
    signals = store.all("activity_signals")
    competitor_id = clean_string(request.args.get("competitor_id"))
    signal_type = clean_string(request.args.get("type")).lower()
    if competitor_id:
        signals = [item for item in signals if str(item.get("competitor_id")) == competitor_id]
    if signal_type:
        signals = [item for item in signals if clean_string(item.get("type")).lower() == signal_type]
    return jsonify(sorted(signals, key=lambda item: item.get("created_at", ""), reverse=True))


@app.get("/api/activity-signals/<signal_id>")
def activity_signal_detail(signal_id):
    signal = get_document("activity_signals", signal_id)
    if not signal:
        return error_response("Activity signal not found", 404)
    return jsonify(signal)


@app.post("/api/activity-signals")
def activity_signal_create():
    payload = request.get_json(force=True, silent=True) or {}
    document, error = activity_signal_payload(payload)
    if error:
        return error_response(error)
    created = store.insert("activity_signals", document)
    sync_competitor_from_activity(created)
    return jsonify(created), 201


@app.put("/api/activity-signals/<signal_id>")
def activity_signal_update(signal_id):
    existing = get_document("activity_signals", signal_id)
    if not existing:
        return error_response("Activity signal not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    document, error = activity_signal_payload(payload, existing)
    if error:
        return error_response(error)
    updated = store.update("activity_signals", signal_id, document)
    sync_competitor_from_activity(updated)
    return jsonify(updated)


@app.delete("/api/activity-signals/<signal_id>")
def activity_signal_delete(signal_id):
    deleted = store.delete("activity_signals", signal_id)
    if not deleted:
        return error_response("Activity signal not found", 404)
    return jsonify({"deleted": True})


@app.get("/api/alerts")
def alerts_list():
    alerts = sorted_alerts()
    status = clean_string(request.args.get("status")).lower()
    severity = clean_string(request.args.get("severity")).lower()
    if status:
        alerts = [item for item in alerts if clean_string(item.get("status")).lower() == status]
    if severity:
        alerts = [item for item in alerts if clean_string(item.get("severity")).lower() == severity]
    return jsonify(alerts)


@app.get("/api/alerts/<alert_id>")
def alert_detail(alert_id):
    alert = get_document("alerts", alert_id)
    if not alert:
        return error_response("Alert not found", 404)
    return jsonify(alert)


@app.post("/api/alerts")
def alert_create():
    payload = request.get_json(force=True, silent=True) or {}
    document, error = alert_payload(payload)
    if error:
        return error_response(error)
    created = store.insert("alerts", document)
    return jsonify(created), 201


@app.put("/api/alerts/<alert_id>")
def alert_update(alert_id):
    existing = get_document("alerts", alert_id)
    if not existing:
        return error_response("Alert not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    document, error = alert_payload(payload, existing)
    if error:
        return error_response(error)
    return jsonify(store.update("alerts", alert_id, document))


@app.patch("/api/alerts/<alert_id>/status")
def alert_status_update(alert_id):
    existing = get_document("alerts", alert_id)
    if not existing:
        return error_response("Alert not found", 404)
    payload = request.get_json(force=True, silent=True) or {}
    payload = {**existing, "status": payload.get("status", "Closed")}
    document, error = alert_payload(payload, existing)
    if error:
        return error_response(error)
    return jsonify(store.update("alerts", alert_id, document))


@app.delete("/api/alerts/<alert_id>")
def alert_delete(alert_id):
    deleted = store.delete("alerts", alert_id)
    if not deleted:
        return error_response("Alert not found", 404)
    return jsonify({"deleted": True})


def build_report_document(payload=None):
    payload = payload or {}
    dashboard_data = build_dashboard()
    try:
        recommendations_payload = ask_gemini(dashboard_data)
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
        recommendations_payload = {
            "source": "Rules engine",
            "items": generate_local_recommendations(dashboard_data),
            "note": f"Gemini response was unavailable, so rule-based recommendations were used. Detail: {exc}",
        }
    report = {
        "title": clean_string(
            payload.get("title"),
            f"Competitive Intelligence Brief - {datetime.now().strftime('%B %d, %Y')}",
        ),
        "created_at": utc_now(),
        "summary": {
            "metrics": dashboard_data["metrics"],
            "top_competitors": dashboard_data["competitors"][:5],
            "market_signals": dashboard_data["market_signals"][:5],
            "alerts": dashboard_data["alerts"][:5],
            "recommendations": recommendations_payload.get("items", []),
        },
        "source": recommendations_payload.get("source", "Rules engine"),
    }
    return report


@app.get("/api/reports")
def reports_list():
    return jsonify(sorted_reports())


@app.get("/api/reports/<report_id>")
def report_detail(report_id):
    report = get_document("reports", report_id)
    if not report:
        return error_response("Report not found", 404)
    return jsonify(report)


@app.post("/api/reports")
def report_create():
    payload = request.get_json(force=True, silent=True) or {}
    created = store.insert("reports", build_report_document(payload))
    return jsonify(created), 201


@app.delete("/api/reports/<report_id>")
def report_delete(report_id):
    deleted = store.delete("reports", report_id)
    if not deleted:
        return error_response("Report not found", 404)
    return jsonify({"deleted": True})


@app.get("/api/reports/<report_id>/export")
def report_export(report_id):
    report = get_document("reports", report_id)
    if not report:
        return error_response("Report not found", 404)
    payload = json.dumps(report, indent=2)
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={report_id}.json"},
    )


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


@app.get("/api/battlecards")
def battlecards_list():
    competitor_id = request.args.get("competitor_id")
    cards = sorted_battlecards()
    if competitor_id:
        cards = [card for card in cards if str(card.get("competitor_id")) == str(competitor_id)]
    return jsonify(cards)


@app.get("/api/battlecards/<battlecard_id>")
def battlecard_detail(battlecard_id):
    card = get_document("battlecards", battlecard_id)
    if not card:
        return error_response("Battlecard not found", 404)
    return jsonify(card)


@app.post("/api/battlecard")
@app.post("/api/battlecards")
def battlecard_create():
    payload = request.get_json(force=True, silent=True) or {}
    error = require_fields(payload, ["competitor_id"])
    if error:
        return error_response(error)
    objective = clean_string(payload.get("objective"), "Win new business against this competitor")
    profile = build_competitor_profile(payload["competitor_id"])
    if not profile:
        return error_response("Competitor not found", 404)
    try:
        card = ask_gemini_battlecard(profile, objective)
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
        card = generate_local_battlecard(profile, objective)
        card["note"] = f"Gemini response was unavailable, so a rule-based battlecard was used. Detail: {exc}"
    card["created_at"] = utc_now()
    if payload.get("save", True) is not False:
        card = store.insert("battlecards", card)
    return jsonify(card), 201


@app.delete("/api/battlecards/<battlecard_id>")
def battlecard_delete(battlecard_id):
    deleted = store.delete("battlecards", battlecard_id)
    if not deleted:
        return error_response("Battlecard not found", 404)
    return jsonify({"deleted": True})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
