"""
Cognituv Connect MCP Server
============================
A combined FastAPI + FastMCP server that:
  1. Receives myDevices webhook events (uplink, alert, ping) via HTTP POST
  2. Stores them in a local SQLite database
  3. Exposes MCP tools so AI agents can query sensor data, devices, alerts, and trends

Usage:
  uvicorn server:app --host 0.0.0.0 --port 8000

Webhook URL to configure in myDevices:
  https://<your-domain>/webhook

MCP endpoint (Streamable HTTP):
  https://<your-domain>/mcp/
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_FILE = os.environ.get("COGNITUV_DB_FILE", "cognituv_connect.db")
WEBHOOK_SECRET = os.environ.get("COGNITUV_WEBHOOK_SECRET", "")  # optional shared secret

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type  TEXT NOT NULL,
        received_at TEXT DEFAULT (datetime('now')),
        raw_json    TEXT NOT NULL
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        device_id       TEXT PRIMARY KEY,
        thing_name      TEXT,
        sensor_use      TEXT,
        device_type_id  TEXT,
        device_type_name TEXT,
        manufacturer    TEXT,
        model           TEXT,
        codec           TEXT,
        company_id      INTEGER,
        company_name    TEXT,
        location_id     INTEGER,
        location_name   TEXT,
        location_city   TEXT,
        location_state  TEXT,
        first_seen      TEXT,
        last_seen       TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   TEXT NOT NULL,
        sensor_id   TEXT,
        name        TEXT,
        type        TEXT,
        value       REAL,
        unit        TEXT,
        channel     INTEGER,
        ts          INTEGER,
        received_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (device_id) REFERENCES devices(device_id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   TEXT NOT NULL,
        sensor_id   TEXT,
        rule_id     TEXT,
        title       TEXT,
        triggered   INTEGER,
        value       TEXT,
        ts          INTEGER,
        received_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (device_id) REFERENCES devices(device_id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS gateway_pings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   TEXT NOT NULL,
        thing_name  TEXT,
        ts          INTEGER,
        received_at TEXT DEFAULT (datetime('now'))
    )""")

    # Indexes for common queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_readings_device ON sensor_readings(device_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_readings_ts ON sensor_readings(ts)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts)")

    conn.commit()
    conn.close()


def upsert_device(c, payload):
    """Insert or update device metadata from any webhook event."""
    event_data = payload.get("event_data", {})
    device_info = payload.get("device", {})
    device_type = payload.get("device_type", {})
    company = payload.get("company", {})
    location = payload.get("location", {})

    device_id = event_data.get("device_id") or event_data.get("thingId") or str(device_info.get("id", ""))
    if not device_id:
        return device_id

    c.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,))
    if c.fetchone():
        c.execute("UPDATE devices SET last_seen = datetime('now') WHERE device_id = ?", (device_id,))
    else:
        c.execute("""
        INSERT INTO devices (device_id, thing_name, sensor_use, device_type_id, device_type_name,
                             manufacturer, model, codec, company_id, company_name,
                             location_id, location_name, location_city, location_state,
                             first_seen, last_seen)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
        """, (
            device_id,
            device_info.get("thing_name"),
            device_info.get("sensor_use", ""),
            device_type.get("id"),
            device_type.get("name"),
            device_type.get("manufacturer"),
            device_type.get("model"),
            device_type.get("codec"),
            company.get("id"),
            company.get("name"),
            location.get("id"),
            location.get("name"),
            location.get("city"),
            location.get("state"),
        ))
    return device_id


# ---------------------------------------------------------------------------
# FastAPI application (webhook receiver)
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Cognituv Connect MCP Server",
    description="Receives myDevices webhooks and exposes MCP tools for AI agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "cognituv-connect-mcp"}


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receives webhook events from myDevices (Cognituv Connect platform).
    Supports event types: uplink, alert, ping.
    """
    # Optional: validate shared secret header
    if WEBHOOK_SECRET:
        auth = request.headers.get("x-api") or request.headers.get("authorization")
        if auth != WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = payload.get("event_type", "unknown")
    conn = get_db()
    c = conn.cursor()

    # Log raw event
    c.execute("INSERT INTO events (event_type, raw_json) VALUES (?, ?)",
              (event_type, json.dumps(payload)))

    try:
        if event_type == "uplink":
            device_id = upsert_device(c, payload)
            for reading in payload.get("event_data", {}).get("payload", []):
                c.execute("""
                INSERT INTO sensor_readings (device_id, sensor_id, name, type, value, unit, channel, ts)
                VALUES (?,?,?,?,?,?,?,?)
                """, (
                    device_id,
                    reading.get("sensor_id"),
                    reading.get("name"),
                    reading.get("type"),
                    reading.get("value"),
                    reading.get("unit"),
                    reading.get("channel"),
                    reading.get("timestamp"),
                ))

        elif event_type == "alert":
            device_id = upsert_device(c, payload)
            ed = payload.get("event_data", {})
            c.execute("""
            INSERT INTO alerts (device_id, sensor_id, rule_id, title, triggered, value, ts)
            VALUES (?,?,?,?,?,?,?)
            """, (
                device_id,
                ed.get("sensorId"),
                ed.get("ruleId"),
                ed.get("title"),
                1 if ed.get("triggered") else 0,
                str(ed.get("value", "")),
                ed.get("timestamp"),
            ))

        elif event_type == "ping":
            ed = payload.get("event_data", {})
            device = payload.get("device", {})
            c.execute("""
            INSERT INTO gateway_pings (device_id, thing_name, ts)
            VALUES (?,?,?)
            """, (
                ed.get("device_id", str(device.get("id", ""))),
                device.get("thing_name"),
                ed.get("timestamp"),
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")
    finally:
        conn.close()

    return {"status": "ok", "event_type": event_type}


# ---------------------------------------------------------------------------
# MCP Server (tools for AI agents)
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="cognituv-connect",
    instructions="""You are the Cognituv Connect AI assistant. You have access to real-time
    IoT sensor data from facilities monitored by Cognituv Connect. You can list devices,
    query sensor readings, check alerts, and analyze facility conditions. Always present
    data clearly with units and timestamps. Follow the Identify - Apply - Verify methodology.""",
)


@mcp.tool()
def list_devices(company_name: Optional[str] = None, location_name: Optional[str] = None) -> str:
    """List all devices registered in Cognituv Connect. Optionally filter by company or location name."""
    conn = get_db()
    query = "SELECT device_id, thing_name, sensor_use, device_type_name, manufacturer, model, company_name, location_name, location_city, location_state, last_seen FROM devices WHERE 1=1"
    params = []
    if company_name:
        query += " AND company_name LIKE ?"
        params.append(f"%{company_name}%")
    if location_name:
        query += " AND location_name LIKE ?"
        params.append(f"%{location_name}%")
    query += " ORDER BY last_seen DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return "No devices found matching the criteria."

    results = []
    for r in rows:
        results.append(
            f"- **{r['thing_name']}** (ID: {r['device_id']})\n"
            f"  Type: {r['device_type_name']} | {r['manufacturer']} {r['model']}\n"
            f"  Use: {r['sensor_use'] or 'N/A'}\n"
            f"  Location: {r['location_name']}, {r['location_city']}, {r['location_state']}\n"
            f"  Company: {r['company_name']} | Last seen: {r['last_seen']}"
        )
    return f"Found {len(rows)} device(s):\n\n" + "\n\n".join(results)


@mcp.tool()
def get_device_details(device_id: str) -> str:
    """Get full details for a specific device by its ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not row:
        conn.close()
        return f"Device {device_id} not found."

    # Also get reading count and alert count
    reading_count = conn.execute("SELECT COUNT(*) as cnt FROM sensor_readings WHERE device_id = ?", (device_id,)).fetchone()["cnt"]
    alert_count = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE device_id = ?", (device_id,)).fetchone()["cnt"]
    conn.close()

    lines = [f"**Device: {row['thing_name']}**", ""]
    for key in row.keys():
        lines.append(f"- {key}: {row[key]}")
    lines.append(f"- total_readings: {reading_count}")
    lines.append(f"- total_alerts: {alert_count}")
    return "\n".join(lines)


@mcp.tool()
def get_latest_readings(device_id: str) -> str:
    """Get the most recent sensor reading for each sensor channel on a device."""
    conn = get_db()
    rows = conn.execute("""
        SELECT sr.name, sr.type, sr.value, sr.unit, sr.channel, sr.ts
        FROM sensor_readings sr
        INNER JOIN (
            SELECT device_id, channel, MAX(ts) as max_ts
            FROM sensor_readings
            WHERE device_id = ?
            GROUP BY device_id, channel
        ) latest ON sr.device_id = latest.device_id
                 AND sr.channel = latest.channel
                 AND sr.ts = latest.max_ts
        WHERE sr.device_id = ?
        ORDER BY sr.channel
    """, (device_id, device_id)).fetchall()
    conn.close()

    if not rows:
        return f"No readings found for device {device_id}."

    lines = [f"Latest readings for device {device_id}:", ""]
    for r in rows:
        ts_str = datetime.fromtimestamp(r["ts"] / 1000, tz=timezone.utc).isoformat() if r["ts"] else "N/A"
        lines.append(f"- **{r['name']}**: {r['value']} {r['unit']} (channel {r['channel']}, at {ts_str})")
    return "\n".join(lines)


@mcp.tool()
def get_reading_history(device_id: str, sensor_type: Optional[str] = None, limit: int = 50) -> str:
    """Get historical sensor readings for a device. Optionally filter by sensor type (e.g., 'temp', 'rel_hum', 'co2', 'batt'). Returns up to `limit` most recent readings."""
    conn = get_db()
    query = "SELECT name, type, value, unit, channel, ts FROM sensor_readings WHERE device_id = ?"
    params: list = [device_id]
    if sensor_type:
        query += " AND type = ?"
        params.append(sensor_type)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return f"No readings found for device {device_id}" + (f" with type '{sensor_type}'" if sensor_type else "") + "."

    lines = [f"Reading history for device {device_id}" + (f" (type: {sensor_type})" if sensor_type else "") + f" — {len(rows)} records:", ""]
    for r in rows:
        ts_str = datetime.fromtimestamp(r["ts"] / 1000, tz=timezone.utc).isoformat() if r["ts"] else "N/A"
        lines.append(f"- {r['name']}: {r['value']} {r['unit']} @ {ts_str}")
    return "\n".join(lines)


@mcp.tool()
def get_alerts(device_id: Optional[str] = None, triggered_only: bool = True, limit: int = 25) -> str:
    """Get recent alerts. Optionally filter by device_id. Set triggered_only=False to include resolved alerts."""
    conn = get_db()
    query = "SELECT a.device_id, d.thing_name, a.title, a.triggered, a.value, a.ts, a.received_at FROM alerts a LEFT JOIN devices d ON a.device_id = d.device_id WHERE 1=1"
    params: list = []
    if device_id:
        query += " AND a.device_id = ?"
        params.append(device_id)
    if triggered_only:
        query += " AND a.triggered = 1"
    query += " ORDER BY a.ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return "No alerts found matching the criteria."

    lines = [f"Found {len(rows)} alert(s):", ""]
    for r in rows:
        ts_str = datetime.fromtimestamp(int(r["ts"]) / 1000, tz=timezone.utc).isoformat() if r["ts"] else "N/A"
        status = "TRIGGERED" if r["triggered"] else "RESOLVED"
        lines.append(f"- [{status}] **{r['title']}**\n  Device: {r['thing_name']} ({r['device_id']})\n  Value: {r['value']} | Time: {ts_str}")
    return "\n".join(lines)


@mcp.tool()
def get_facility_summary(company_name: Optional[str] = None) -> str:
    """Get a high-level summary of all monitored facilities: device counts, latest readings, active alerts."""
    conn = get_db()

    # Device counts by company/location
    query = """
        SELECT company_name, location_name, location_city, location_state,
               COUNT(*) as device_count, MAX(last_seen) as latest_activity
        FROM devices
    """
    params: list = []
    if company_name:
        query += " WHERE company_name LIKE ?"
        params.append(f"%{company_name}%")
    query += " GROUP BY company_name, location_name ORDER BY company_name, location_name"
    locations = conn.execute(query, params).fetchall()

    # Active alerts count
    alert_count = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE triggered = 1").fetchone()["cnt"]

    # Total readings
    reading_count = conn.execute("SELECT COUNT(*) as cnt FROM sensor_readings").fetchone()["cnt"]

    # Total devices
    device_count = conn.execute("SELECT COUNT(*) as cnt FROM devices").fetchone()["cnt"]

    conn.close()

    lines = ["**Cognituv Connect Facility Summary**", ""]
    lines.append(f"- Total devices: {device_count}")
    lines.append(f"- Total sensor readings: {reading_count}")
    lines.append(f"- Active alerts: {alert_count}")
    lines.append("")

    if locations:
        lines.append("**Locations:**")
        for loc in locations:
            lines.append(
                f"- {loc['company_name']} / {loc['location_name']} "
                f"({loc['location_city']}, {loc['location_state']}) — "
                f"{loc['device_count']} devices, last activity: {loc['latest_activity']}"
            )
    else:
        lines.append("No locations registered yet.")

    return "\n".join(lines)


@mcp.tool()
def query_sensor_data(sql_where: str, limit: int = 100) -> str:
    """
    Run a custom query against sensor_readings. Provide a SQL WHERE clause
    (e.g., "type = 'temp' AND value > 30"). Returns matching rows up to `limit`.
    Available columns: device_id, sensor_id, name, type, value, unit, channel, ts.
    """
    conn = get_db()
    try:
        query = f"SELECT sr.device_id, d.thing_name, sr.name, sr.type, sr.value, sr.unit, sr.ts FROM sensor_readings sr LEFT JOIN devices d ON sr.device_id = d.device_id WHERE {sql_where} ORDER BY sr.ts DESC LIMIT ?"
        rows = conn.execute(query, (limit,)).fetchall()
    except sqlite3.OperationalError as e:
        conn.close()
        return f"Query error: {e}. Please check your WHERE clause syntax."
    conn.close()

    if not rows:
        return "No results found for the given query."

    lines = [f"Query results ({len(rows)} rows):", ""]
    for r in rows:
        ts_str = datetime.fromtimestamp(r["ts"] / 1000, tz=timezone.utc).isoformat() if r["ts"] else "N/A"
        lines.append(f"- {r['thing_name']}: {r['name']} = {r['value']} {r['unit']} @ {ts_str}")
    return "\n".join(lines)


@mcp.tool()
def get_event_log(event_type: Optional[str] = None, limit: int = 20) -> str:
    """Get the raw event log. Optionally filter by event_type (uplink, alert, ping)."""
    conn = get_db()
    query = "SELECT id, event_type, received_at FROM events"
    params: list = []
    if event_type:
        query += " WHERE event_type = ?"
        params.append(event_type)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return "No events found."

    lines = [f"Event log ({len(rows)} entries):", ""]
    for r in rows:
        lines.append(f"- [{r['event_type']}] ID: {r['id']} at {r['received_at']}")
    return "\n".join(lines)


@mcp.tool()
def get_gateway_status(limit: int = 20) -> str:
    """Get the latest gateway ping/keepalive events to check gateway health."""
    conn = get_db()
    rows = conn.execute("""
        SELECT device_id, thing_name, ts, received_at
        FROM gateway_pings
        ORDER BY ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    if not rows:
        return "No gateway pings recorded yet."

    lines = ["**Gateway Status (recent pings):**", ""]
    for r in rows:
        ts_str = datetime.fromtimestamp(r["ts"] / 1000, tz=timezone.utc).isoformat() if r["ts"] else "N/A"
        lines.append(f"- **{r['thing_name']}** (ID: {r['device_id']}) — pinged at {ts_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mount MCP on FastAPI
# ---------------------------------------------------------------------------
# Mount the MCP Streamable HTTP transport as a sub-application
mcp_app = mcp.streamable_http_app()
app.mount("/mcp", mcp_app)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
