import csv
import io
import json
import os
import re
import time
from threading import Lock
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


load_dotenv()
app = FastAPI(title="Google Sheets JSON API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DEFAULT_CACHE_TTL = 300
cache = {}
cache_lock = Lock()


def sheet_csv_url(gid=None):
    """Build a Google Sheets CSV export URL from a configured URL or ID."""
    configured_url = os.getenv("GOOGLE_SHEET_URL")
    if configured_url:
        parsed = urlparse(configured_url)
        spreadsheet_id = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", parsed.path)
        if spreadsheet_id:
            query = parse_qs(parsed.query)
            selected_gid = gid or query.get("gid", [os.getenv("GOOGLE_SHEET_GID_EVENTS", "0")])[0]
            return (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id.group(1)}"
                f"/export?format=csv&gid={selected_gid}"
            )
        return configured_url

    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("Configure GOOGLE_SHEET_URL or GOOGLE_SHEET_ID")
    selected_gid = gid or os.getenv("GOOGLE_SHEET_GID_EVENTS", "0")
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={selected_gid}"


def parse_value(value):
    value = value.strip()
    if not value:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def process_rows(rows):
    if not rows:
        return []

    headers = [header.strip() or f"column_{index + 1}" for index, header in enumerate(rows[0])]
    processed = []
    for row in rows[1:]:
        values = row + [""] * (len(headers) - len(row))
        item = {header: parse_value(values[index]) for index, header in enumerate(headers)}
        if any(value is not None for value in item.values()):
            processed.append(item)
    return processed


def fetch_data(gid=None, force_refresh=False):
    cache_key = gid or os.getenv("GOOGLE_SHEET_GID_EVENTS", "0")
    now = time.time()
    with cache_lock:
        cached = cache.get(cache_key)
        if not force_refresh and cached and cached["expires_at"] > now:
            return cached["payload"], True

    request_data = Request(sheet_csv_url(gid), headers={"User-Agent": "gsheet-fetch/1.0"})
    with urlopen(request_data, timeout=15) as response:
        csv_text = response.read().decode("utf-8-sig")

    payload = process_rows(list(csv.reader(io.StringIO(csv_text))))
    ttl = int(os.getenv("CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL))
    with cache_lock:
        cache[cache_key] = {"payload": payload, "expires_at": time.time() + ttl}
    return payload, False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/data")
def data(refresh: bool = Query(False, description="Bypass the in-memory cache")):
    try:
        rows, _ = fetch_data(force_refresh=not refresh)
        return rows
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


def named_sheet(sheet_name, environment_variable, refresh):
    gid = os.getenv(environment_variable)
    if not gid or not gid.isdigit():
        raise HTTPException(
            status_code=500,
            detail=f"Configure {environment_variable} with the numeric gid of the {sheet_name} sheet",
        )
    try:
        rows, _ = fetch_data(gid, force_refresh=not refresh)
        return rows
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/events")
def events(refresh: bool = Query(False, description="Bypass the in-memory cache")):
    return named_sheet("events", "GOOGLE_SHEET_GID_EVENTS", refresh)


@app.get("/api/intervenants")
def intervenants(refresh: bool = Query(False, description="Bypass the in-memory cache")):
    return named_sheet("intervenants", "GOOGLE_SHEET_GID_INTERVENANTS", refresh)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))