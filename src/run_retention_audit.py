"""Executes and verifies SQL cohort retention, feature adoption, and quarantine queries."""

import sqlite3
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

DB_PATH = "saas_telemetry.db"

def run_verifications():
    conn = sqlite3.connect(DB_PATH)

    print("\n" + "=" * 80)
    print("QUERY 1: WEEKLY COHORT USER RETENTION MATRIX (TOP 5 WEEKS)")
    print("=" * 80)
    q1 = """
    WITH cohort_sizes AS (
        SELECT 
            cohort_week,
            COUNT(DISTINCT user_id) AS total_cohort_users
        FROM dim_users
        GROUP BY cohort_week
    ),
    user_activity_deltas AS (
        SELECT 
            u.cohort_week,
            u.user_id,
            CAST(ROUND(JULIANDAY(f.event_date) - JULIANDAY(u.signup_date)) AS INTEGER) AS days_since_signup
        FROM dim_users u
        JOIN fact_product_events f ON u.user_id = f.user_id
        GROUP BY u.cohort_week, u.user_id, days_since_signup
    )
    SELECT 
        c.cohort_week,
        c.total_cohort_users,
        COUNT(DISTINCT CASE WHEN a.days_since_signup = 0 THEN a.user_id END) AS active_day_0,
        ROUND(COUNT(DISTINCT CASE WHEN a.days_since_signup BETWEEN 1 AND 7 THEN a.user_id END) * 100.0 / c.total_cohort_users, 1) AS pct_retained_week_1,
        ROUND(COUNT(DISTINCT CASE WHEN a.days_since_signup BETWEEN 8 AND 14 THEN a.user_id END) * 100.0 / c.total_cohort_users, 1) AS pct_retained_week_2,
        ROUND(COUNT(DISTINCT CASE WHEN a.days_since_signup BETWEEN 15 AND 30 THEN a.user_id END) * 100.0 / c.total_cohort_users, 1) AS pct_retained_month_1
    FROM cohort_sizes c
    LEFT JOIN user_activity_deltas a ON c.cohort_week = a.cohort_week
    GROUP BY c.cohort_week, c.total_cohort_users
    ORDER BY c.cohort_week ASC
    LIMIT 5;
    """
    df1 = pd.read_sql_query(q1, conn)
    print(df1.to_string(index=False))

    print("\n" + "=" * 80)
    print("QUERY 2: AI FEATURE ADOPTION BY PLAN TIER")
    print("=" * 80)
    q2 = """
    SELECT 
        u.plan_tier,
        COUNT(DISTINCT u.user_id) AS total_users,
        COUNT(CASE WHEN f.event_type = 'meeting_recorded' THEN 1 END) AS total_meetings_recorded,
        COUNT(CASE WHEN f.event_type = 'ai_summary_generated' THEN 1 END) AS total_ai_summaries,
        ROUND(
            COUNT(CASE WHEN f.event_type = 'ai_summary_generated' THEN 1 END) * 1.0 / 
            NULLIF(COUNT(CASE WHEN f.event_type = 'meeting_recorded' THEN 1 END), 0), 2
        ) AS ai_summary_attach_rate,
        SUM(f.ai_tokens_consumed) AS total_tokens_used,
        ROUND(AVG(f.ai_tokens_consumed), 0) AS avg_tokens_per_ai_event
    FROM dim_users u
    JOIN fact_product_events f ON u.user_id = f.user_id
    GROUP BY u.plan_tier
    ORDER BY total_meetings_recorded DESC;
    """
    df2 = pd.read_sql_query(q2, conn)
    print(df2.to_string(index=False))

    print("\n" + "=" * 80)
    print("QUERY 3: QUARANTINE INTEGRITY AUDIT")
    print("=" * 80)
    q3 = """
    SELECT 
        rejection_reason,
        COUNT(*) AS error_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM telemetry_quarantine), 2) AS pct_of_errors
    FROM telemetry_quarantine
    GROUP BY rejection_reason
    ORDER BY error_count DESC;
    """
    df3 = pd.read_sql_query(q3, conn)
    print(df3.to_string(index=False))

    conn.close()

if __name__ == "__main__":
    run_verifications()