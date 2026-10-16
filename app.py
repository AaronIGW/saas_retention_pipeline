"""
SaaS Product Telemetry & Cohort Retention Dashboard.
Provides product intelligence, user lifecycle tracking, and feature attach metrics.
"""

import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = "saas_telemetry.db"

st.set_page_config(
    page_title="Product Telemetry & Cohort Analytics",
    layout="wide"
)

st.title("SaaS Telemetry & Cohort Retention Engine")

@st.cache_data
def load_kpis():
    """Fetches high-level executive product metrics."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        COUNT(DISTINCT u.user_id) AS total_users,
        COUNT(CASE WHEN f.event_type = 'meeting_recorded' THEN 1 END) AS total_meetings,
        COUNT(CASE WHEN f.event_type = 'ai_summary_generated' THEN 1 END) AS total_ai_summaries,
        COALESCE(SUM(f.ai_tokens_consumed), 0) AS total_tokens
    FROM dim_users u
    LEFT JOIN fact_product_events f ON u.user_id = f.user_id;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0]

@st.cache_data
def load_cohort_data():
    """Loads weekly cohort retention matrix."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    WITH cohort_sizes AS (
        SELECT 
            cohort_week,
            COUNT(DISTINCT user_id) AS cohort_size
        FROM dim_users
        GROUP BY cohort_week
    ),
    user_activity AS (
        SELECT 
            u.cohort_week,
            u.user_id,
            CAST(ROUND(JULIANDAY(f.event_date) - JULIANDAY(u.signup_date)) AS INTEGER) AS delta_days
        FROM dim_users u
        JOIN fact_product_events f ON u.user_id = f.user_id
        GROUP BY u.cohort_week, u.user_id, delta_days
    )
    SELECT 
        c.cohort_week,
        c.cohort_size,
        COUNT(DISTINCT CASE WHEN a.delta_days = 0 THEN a.user_id END) * 100.0 / c.cohort_size AS day_0,
        COUNT(DISTINCT CASE WHEN a.delta_days BETWEEN 1 AND 7 THEN a.user_id END) * 100.0 / c.cohort_size AS week_1,
        COUNT(DISTINCT CASE WHEN a.delta_days BETWEEN 8 AND 14 THEN a.user_id END) * 100.0 / c.cohort_size AS week_2,
        COUNT(DISTINCT CASE WHEN a.delta_days BETWEEN 15 AND 30 THEN a.user_id END) * 100.0 / c.cohort_size AS month_1
    FROM cohort_sizes c
    LEFT JOIN user_activity a ON c.cohort_week = a.cohort_week
    GROUP BY c.cohort_week, c.cohort_size
    ORDER BY c.cohort_week ASC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data
def load_feature_funnel():
    """Calculates lifecycle conversion counts across core product actions."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        event_type,
        COUNT(event_id) AS event_count,
        COUNT(DISTINCT user_id) AS unique_users
    FROM fact_product_events
    GROUP BY event_type
    ORDER BY event_count DESC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data
def load_platform_tier_breakdown():
    """Aggregates meeting volume segmented by conference platform and plan tier."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        u.plan_tier,
        f.platform,
        COUNT(f.event_id) AS meeting_volume
    FROM fact_product_events f
    JOIN dim_users u ON f.user_id = u.user_id
    WHERE f.event_type = 'meeting_recorded'
    GROUP BY u.plan_tier, f.platform
    ORDER BY meeting_volume DESC;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Metric Banner
kpi = load_kpis()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Onboarded Users", f"{int(kpi['total_users']):,}")
c2.metric("Meetings Processed", f"{int(kpi['total_meetings']):,}")
c3.metric("AI Summaries Created", f"{int(kpi['total_ai_summaries']):,}")
attach_rate = (kpi['total_ai_summaries'] / kpi['total_meetings'] * 100) if kpi['total_meetings'] > 0 else 0
c4.metric("AI Attach Rate", f"{attach_rate:.1f}%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "Cohort Retention Analysis", 
    "Product Funnel & Feature Usage", 
    "Platform Integration Share"
])

with tab1:
    st.subheader("Weekly Cohort Retention Rates (%)")
    cohort_df = load_cohort_data()
    heatmap_matrix = cohort_df.set_index("cohort_week")[["day_0", "week_1", "week_2", "month_1"]].round(1)
    
    fig_cohort = px.imshow(
        heatmap_matrix,
        labels=dict(x="Retention Interval", y="Signup Cohort", color="Retained %"),
        x=["Day 0", "Week 1", "Week 2", "Month 1"],
        y=heatmap_matrix.index,
        color_continuous_scale="Blues",
        text_auto=".1f",
        aspect="auto"
    )
    fig_cohort.update_layout(height=480)
    st.plotly_chart(fig_cohort, use_container_width=True)

with tab2:
    st.subheader("Feature Adoption & Engagement Funnel")
    funnel_df = load_feature_funnel()
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_funnel = px.bar(
            funnel_df,
            x="event_count",
            y="event_type",
            orientation="h",
            labels={"event_count": "Total Invocations", "event_type": "Product Event"},
            color="event_count",
            color_continuous_scale="Viridis",
            text="event_count"
        )
        fig_funnel.update_traces(textposition="outside")
        fig_funnel.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_b:
        fig_users = px.bar(
            funnel_df,
            x="unique_users",
            y="event_type",
            orientation="h",
            labels={"unique_users": "Unique Participating Users", "event_type": "Product Event"},
            color="unique_users",
            color_continuous_scale="Cividis",
            text="unique_users"
        )
        fig_users.update_traces(textposition="outside")
        fig_users.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_users, use_container_width=True)

with tab3:
    st.subheader("Meeting Recording Volume by Platform & Plan Tier")
    platform_df = load_platform_tier_breakdown()
    fig_platform = px.bar(
        platform_df,
        x="plan_tier",
        y="meeting_volume",
        color="platform",
        barmode="group",
        labels={"plan_tier": "Subscription Tier", "meeting_volume": "Total Recorded Meetings"},
        height=420
    )
    st.plotly_chart(fig_platform, use_container_width=True)