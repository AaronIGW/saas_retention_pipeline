import json
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "saas_telemetry.db"
SCHEMA_PATH = "sql/schema.sql"
USERS_PATH = "data/raw_users.json"
EVENTS_PATH = "data/raw_events.json"

def init_database(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    """Initializes SQLite database using DDL schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
    print(" Database schema initialized.")

def ingest_users(users_path=USERS_PATH, db_path=DB_PATH):
    """Loads and validates user dimension records."""
    with open(users_path, "r", encoding="utf-8") as f:
        users = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    valid_users = []
    for u in users:
        signup_dt = datetime.strptime(u["signup_timestamp"], "%Y-%m-%d %H:%M:%S")
        valid_users.append((
            u["user_id"],
            u["signup_timestamp"],
            signup_dt.strftime("%Y-%m-%d"),
            u["cohort_week"],
            u["company_size"],
            u["plan_tier"]
        ))

    cursor.executemany(
        """
        INSERT OR IGNORE INTO dim_users (
            user_id, signup_timestamp, signup_date,
            cohort_week, company_size, plan_tier
        ) VALUES (?, ?, ?, ?, ?, ?);
        """,
        valid_users
    )
    conn.commit()
    conn.close()
    print(f" Loaded {len(valid_users)} users into dim_users.")

def ingest_telemetry_events(events_path=EVENTS_PATH, db_path=DB_PATH):
    """Ingests, validates, and stages streaming product telemetry events."""
    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Pre-fetch valid user IDs for referential integrity check
    cursor.execute("SELECT user_id FROM dim_users;")
    valid_user_ids = {row[0] for row in cursor.fetchall()}

    valid_events = []
    quarantined = []
    VALID_EVENT_TYPES = {
        "meeting_recorded", "ai_summary_generated", 
        "transcript_search", "action_item_shared", "plan_upgraded"
    }

    for evt in events:
        evt_id = evt.get("event_id")
        user_id = evt.get("user_id")
        event_type = evt.get("event_type")
        ts_str = evt.get("event_timestamp")
        duration = evt.get("meeting_duration_minutes")
        tokens = evt.get("ai_tokens_consumed", 0)
        platform = evt.get("platform", "unknown")
        raw_dump = json.dumps(evt)

        # Rule 1: Missing event ID or timestamp
        if not evt_id or not ts_str:
            quarantined.append((raw_dump, "Missing event_id or timestamp"))
            continue

        # Rule 2: Foreign Key Referential Integrity (Orphaned user)
        if user_id not in valid_user_ids:
            quarantined.append((raw_dump, f"Orphaned event: user_id '{user_id}' does not exist in dim_users"))
            continue

        # Rule 3: Valid Event Type
        if event_type not in VALID_EVENT_TYPES:
            quarantined.append((raw_dump, f"Invalid event_type: '{event_type}'"))
            continue

        # Rule 4: Non-negative meeting duration
        if duration is not None and duration < 0:
            quarantined.append((raw_dump, f"Corrupted duration: {duration} min"))
            continue

        evt_date = ts_str[:10]

        valid_events.append((
            evt_id,
            user_id,
            event_type,
            ts_str,
            evt_date,
            duration,
            tokens,
            platform
        ))

    # Bulk Insert valid telemetry events
    if valid_events:
        cursor.executemany(
            """
            INSERT OR IGNORE INTO fact_product_events (
                event_id, user_id, event_type,
                event_timestamp, event_date,
                meeting_duration_minutes, ai_tokens_consumed, platform
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            valid_events
        )

    # Bulk Insert quarantined records
    if quarantined:
        cursor.executemany(
            "INSERT INTO telemetry_quarantine (raw_payload, rejection_reason) VALUES (?, ?);",
            quarantined
        )

    conn.commit()
    conn.close()

    print("\n--- Telemetry Ingestion Execution Summary ---")
    print(f"Total Raw Events Processed : {len(events)}")
    print(f"Valid Events Staged        : {len(valid_events)}")
    print(f"Quarantined Anomalies      : {len(quarantined)}")

if __name__ == "__main__":
    init_database()
    ingest_users()
    ingest_telemetry_events()