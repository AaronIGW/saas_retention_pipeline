# SaaS Telemetry & Cohort Retention Engine

An analytical data pipeline and business intelligence engine modeling user lifecycle retention, meeting telemetry, and AI feature adoption for voice assistant platforms.

## Architecture & Data Flow

1. **Telemetry Ingestion (`src/event_generator.py`, `src/process_funnels.py`)**
   * Processes streaming product payloads covering meeting recordings, transcript searches, AI summary generations, and plan upgrades.
   * Enforces referential integrity between user profiles and telemetry events.
   * Identifies schema drift, negative meeting durations, and orphaned records, diverting them to an audit quarantine table.

2. **Relational Data Modeling (`sql/schema.sql`)**
   * **`dim_users`**: Normalizes user attributes, signup dates, company size classifications, and subscription tiers.
   * **`fact_product_events`**: Stores event-level interaction records, session durations, token consumption metrics, and host platform metadata.
   * **`telemetry_quarantine`**: Maintains an append-only audit trail of malformed records with explicit validation failure codes.

3. **Analytics Mart & SQL Auditing (`sql/cohort_retention.sql`)**
   * Executes weekly user cohort retention tracking across Day 0, Week 1, Week 2, and Month 1 milestones using Common Table Expressions (CTEs) and date math.
   * Calculates AI summary attach rates and token utilization intensity segmented by customer subscription tier.

4. **Product Intelligence Dashboard (`app.py`)**
   * Deploys an interactive Streamlit application visualizing cohort retention heatmaps, feature drop-off funnels, and video platform market share.

## Schema Specifications

* **`dim_users`**
  * `user_id` (TEXT, Primary Key)
  * `signup_timestamp` (TIMESTAMP)
  * `signup_date` (DATE)
  * `cohort_week` (TEXT)
  * `company_size` (TEXT)
  * `plan_tier` (TEXT)

* **`fact_product_events`**
  * `event_id` (TEXT, Primary Key)
  * `user_id` (TEXT, Foreign Key)
  * `event_type` (TEXT)
  * `event_timestamp` (TIMESTAMP)
  * `event_date` (DATE)
  * `meeting_duration_minutes` (INTEGER)
  * `ai_tokens_consumed` (INTEGER)
  * `platform` (TEXT)

* **`telemetry_quarantine`**
  * `raw_payload` (TEXT)
  * `rejection_reason` (TEXT)
  * `flagged_at` (TIMESTAMP)

## Execution Instructions

1. Generate synthetic telemetry records:
   ```bash
   python src/event_generator.py