# Google Sheets JSON API

The API reads a publicly accessible Google Sheet through its CSV export endpoint,
uses the first row as object keys, converts numbers and booleans to JSON types,
and ignores completely empty rows.

## Configuration

The sheet must be shared publicly or published to the web. Set either a full
spreadsheet URL or its ID.

```sh
export GOOGLE_SHEET_URL="https://docs.google.com/spreadsheets/d/<id>/edit?gid=0"
export GOOGLE_SHEET_GID_EVENTS="0"
export GOOGLE_SHEET_GID_INTERVENANTS="<gid-de-l-onglet-intervenants>"
```

## Run locally

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# Edit .env with your public spreadsheet URL before starting.
python app.py
```

Then request `http://localhost:8000/api/events` or
`http://localhost:8000/api/intervenants`. FastAPI documentation is available
at `http://localhost:8000/docs`. Add `?refresh=true` to bypass
the five-minute in-memory cache. `GET /health` is available for container
health checks.

`/api/data` remains available as an alias for the configured `events` sheet.

## Make commands

```sh
make build
make run       # Start the API; keep this terminal running.
make query     # Query the API from another terminal.
```