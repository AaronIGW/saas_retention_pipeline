import json
import random
import uuid
from datetime import datetime, timedelta

OUTPUT_USERS = "data/raw_users.json"
OUTPUT_EVENTS = "data/raw_events.json"

def generate_telemetry_dataset(num_users=500, base_date=datetime(2026, 8, 1, 9, 0, 0)):
    company_sizes = ["1-10", "11-50", "51-200", "201+"]
    plan_tiers = ["free", "free", "pro", "business"]
    platforms = ["zoom", "google_meet", "ms_teams"]
    event_types = [
        "meeting_recorded", 
        "ai_summary_generated", 
        "transcript_search", 
        "action_item_shared", 
        "plan_upgraded"
    ]

    users = []
    events = []

    print(f"Generating {num_users} users and simulated product events...")

    for i in range(num_users):
        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        # Spread signups over 10 consecutive weeks
        signup_offset_days = random.randint(0, 70)
        signup_dt = base_date + timedelta(days=signup_offset_days, hours=random.randint(0, 12))
        
        cohort_week = signup_dt.strftime("%Y-W%U")
        plan = random.choice(plan_tiers)
        company_size = random.choice(company_sizes)

        users.append({
            "user_id": user_id,
            "signup_timestamp": signup_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "cohort_week": cohort_week,
            "company_size": company_size,
            "plan_tier": plan
        })

        # Simulate user lifecycle & retention drop-off
        # Some users drop off after day 1, others engage actively for 30+ days
        is_churned_early = random.random() < 0.35
        total_activity_days = random.randint(1, 3) if is_churned_early else random.randint(1, 45)

        for d in range(total_activity_days):
            day_dt = signup_dt + timedelta(days=d)
            if day_dt > datetime(2026, 10, 15):
                break  # Do not exceed current date boundary

            # Number of events on active days
            daily_events_count = random.randint(1, 6)
            for _ in range(daily_events_count):
                event_type = random.choice(event_types)
                evt_dt = day_dt + timedelta(hours=random.randint(0, 10), minutes=random.randint(0, 59))
                
                duration = random.randint(15, 65) if event_type == "meeting_recorded" else None
                tokens = random.randint(400, 2800) if event_type in ["ai_summary_generated", "action_item_shared"] else None

                event_record = {
                    "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_timestamp": evt_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "meeting_duration_minutes": duration,
                    "ai_tokens_consumed": tokens,
                    "platform": random.choice(platforms)
                }

                # Inject realistic pipeline edge cases
                if len(events) % 180 == 0:
                    # Injected Anomaly: Corrupted negative duration
                    event_record["meeting_duration_minutes"] = -45
                elif len(events) % 250 == 0:
                    # Injected Anomaly: Orphaned event (unmapped user)
                    event_record["user_id"] = "usr_ghost_missing"

                events.append(event_record)

    # Save to data directory
    with open(OUTPUT_USERS, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    with open(OUTPUT_EVENTS, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    print(f" Saved {len(users)} users to {OUTPUT_USERS}")
    print(f" Saved {len(events)} telemetry events to {OUTPUT_EVENTS}")

if __name__ == "__main__":
    generate_telemetry_dataset()