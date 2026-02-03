import os
import requests
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

# ---------------------------
# PAGE CONFIG
# ---------------------------
st.set_page_config(
    page_title="SACB Lead & Inquiry Dashboard (Kobo)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #d35400;
        text-align: center;
        margin-bottom: 1.25rem;
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 800;
        color: #2c3e50;
        border-bottom: 2px solid #e67e22;
        padding-bottom: 0.4rem;
        margin: 0.8rem 0 0.6rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SETTINGS (fallback to secrets/env)
# ---------------------------
def get_setting(key: str, default: str = "") -> str:
    if key in st.secrets:
        return str(st.secrets[key])
    return os.getenv(key, default)

DEFAULT_BASE_URL = get_setting("KOBO_BASE_URL", "https://eu.kobotoolbox.org")
DEFAULT_TOKEN = get_setting("KOBO_TOKEN", "")
DEFAULT_ASSET_UID = get_setting("KOBO_ASSET_UID", "")
VERIFY_SSL = get_setting("KOBO_ENCRYPT_VERIFY_SSL", "true").lower() != "false"

# ---------------------------
# FIELD MAPPING
# ---------------------------
FIELD = {
    "submitted_at": "_submission_time",
    "assignee": "assignee_name",
    "client_type": "client_type",
    "inquiry_source": "inquiry_source",
    "inquiry_type": "inquiry_type",
    "country_residence": "location_country",
    "country_origin": "Country_of_Origin",
    "next_action": "next_action",
    "lead_status": "lead_status",
}

# ---------------------------
# KOBO API HELPERS
# ---------------------------
def kobo_headers(token: str):
    return {"Authorization": f"Token {token}"}

def kobo_get_data(base_url: str, token: str, asset_uid: str, verify_ssl: bool, limit: int = 30000) -> pd.DataFrame:
    base_url = base_url.rstrip("/")
    url = f"{base_url}/api/v2/assets/{asset_uid}/data/?format=json&limit=1000"
    all_rows = []

    while url:
        r = requests.get(url, headers=kobo_headers(token), verify=verify_ssl, timeout=60)

        if r.status_code == 401:
            raise RuntimeError("401 Unauthorized: invalid token or no permission.")
        if r.status_code == 404:
            raise RuntimeError("404 Not Found: wrong base URL or asset UID.")

        r.raise_for_status()
        payload = r.json()
        all_rows.extend(payload.get("results", []))
        url = payload.get("next")

        if len(all_rows) >= limit:
            break

    return pd.DataFrame(all_rows)

def explode_multiselect(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns or "_id" not in df.columns:
        return pd.DataFrame(columns=["_id", col])

    tmp = df[["_id", col]].copy()
    tmp[col] = tmp[col].fillna("").astype(str)

    def split_any(x: str):
        x = x.strip()
        if not x:
            return []
        if "," in x:
            return [i.strip() for i in x.split(",") if i.strip()]
        return [i.strip() for i in x.split() if i.strip()]

    tmp[col] = tmp[col].apply(split_any)
    tmp = tmp.explode(col)
    tmp = tmp[tmp[col].notna() & (tmp[col] != "")]
    return tmp

@st.cache_data(ttl=300)
def load_kobo_dataframe(base_url: str, token: str, asset_uid: str, verify_ssl: bool) -> pd.DataFrame:
    df = kobo_get_data(base_url, token, asset_uid, verify_ssl)
    if df.empty:
        return df

    submitted_col = FIELD["submitted_at"]
    if submitted_col in df.columns:
        df[submitted_col] = pd.to_datetime(df[submitted_col], errors="coerce")

    return df

# ---------------------------
# TABLE HELPERS
# ---------------------------
def freq_percent_table(series: pd.Series, label_name: str = "Category") -> pd.DataFrame:
    s = series.fillna("Unknown").astype(str)
    counts = s.value_counts(dropna=False)
    total = counts.sum()
    return pd.DataFrame({
        label_name: counts.index,
        "Frequency": counts.values,
        "Percent": (counts.values / total * 100).round(1)
    })

def show_table(df_table: pd.DataFrame):
    st.dataframe(df_table.style.format({"Percent": "{:.1f}%"}), use_container_width=True)

# ---------------------------
# SIDEBAR: INPUT ORDER (BASE URL -> TOKEN -> FORM ID) + DATES
# ---------------------------
KOBO_BASE_URL = st.sidebar.text_input("KOBO_BASE_URL", value=DEFAULT_BASE_URL)
KOBO_TOKEN = st.sidebar.text_input("KOBO_TOKEN", value=DEFAULT_TOKEN, type="password")
KOBO_ASSET_UID = st.sidebar.text_input("KOBO_ASSET_UID", value=DEFAULT_ASSET_UID)

refresh = st.sidebar.button("Refresh Data")
if refresh:
    st.cache_data.clear()

if not KOBO_BASE_URL.strip() or not KOBO_TOKEN.strip() or not KOBO_ASSET_UID.strip():
    st.markdown('<div class="main-header">📊 SACB Lead & Client Inquiry Dashboard (Kobo)</div>', unsafe_allow_html=True)
    st.info("Enter KOBO_BASE_URL, KOBO_TOKEN, and KOBO_ASSET_UID in the sidebar.")
    st.stop()

# ---------------------------
# LOAD DATA
# ---------------------------
st.markdown('<div class="main-header">📊 SACB Lead & Client Inquiry Dashboard (Kobo)</div>', unsafe_allow_html=True)

try:
    df = load_kobo_dataframe(KOBO_BASE_URL, KOBO_TOKEN, KOBO_ASSET_UID, VERIFY_SSL)
except Exception as e:
    st.error(str(e))
    st.stop()

if df.empty:
    st.warning("No submissions returned (check base URL, token, or asset UID).")
    st.stop()

submitted_col = FIELD["submitted_at"]
if submitted_col not in df.columns:
    st.error(f"'{submitted_col}' column not found. Update FIELD mapping.")
    st.stop()
st.sidebar.markdown("### Debug: Columns")
st.sidebar.write(sorted(df.columns.tolist()))
st.sidebar.markdown("### Debug: Columns containing 'action'")
st.sidebar.write([c for c in df.columns if "action" in c.lower() or "next" in c.lower() or "follow" in c.lower()])

# ---------------------------
# DATE FILTER (DEFAULT: SHOW ALL DATA ON FIRST LOAD)
# ---------------------------
valid_dates = df[submitted_col].dropna()
if valid_dates.empty:
    min_dt = date.today()
    max_dt = date.today()
else:
    min_dt = valid_dates.min().date()
    max_dt = valid_dates.max().date()

# Default to full available range so dashboard loads with ALL submissions
start_date = st.sidebar.date_input("Start Date", value=min_dt, min_value=min_dt, max_value=max_dt, key="start_date")
end_date = st.sidebar.date_input("End Date", value=max_dt, min_value=min_dt, max_value=max_dt, key="end_date")

if start_date > end_date:
    st.sidebar.error("Start Date cannot be after End Date.")
    st.stop()

filtered = df[
    (df[submitted_col] >= pd.to_datetime(start_date)) &
    (df[submitted_col] <= pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
].copy()

if filtered.empty:
    st.warning("No submissions found in the selected date range.")
    st.stop()

# ---------------------------
# KPI ROW
# ---------------------------
st.markdown('<div class="section-header">📈 Key Stats (Selected Date Range)</div>', unsafe_allow_html=True)

status_col = FIELD["lead_status"]
client_type_col = FIELD["client_type"]

total_leads = len(filtered)
new_clients = int((filtered[client_type_col] == "New Client").sum()) if client_type_col in filtered.columns else 0
existing_clients = int((filtered[client_type_col] == "Existing Client").sum()) if client_type_col in filtered.columns else 0
converted = int((filtered[status_col] == "Converted to Client").sum()) if status_col in filtered.columns else 0
conversion_rate = (converted / total_leads) if total_leads else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Submissions", f"{total_leads:,}")
c2.metric("New Clients", f"{new_clients:,}")
c3.metric("Existing Clients", f"{existing_clients:,}")
c4.metric("Converted to Client", f"{converted:,}")
c5.metric("Conversion Rate", f"{conversion_rate*100:.1f}%")

# ---------------------------
# TABS
# ---------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📌 Overview",
    "👤 Assignee Performance",
    "🎥 Inquiry Source",
    "🧾 Inquiry Type",
    "🌍 Countries",
    "📞 Follow-up"
])

# ---------------------------
# TAB 1: OVERVIEW
# ---------------------------
with tab1:
    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)

    if status_col in filtered.columns:
        status_order = [
            "New Lead", "Contacted", "Interested", "Estimate Sent",
            "Negotiation", "Converted to Client", "Not Interested", "No Response"
        ]
        s = filtered[status_col].fillna("Unknown").astype(str)
        status_counts = s.value_counts().reindex(status_order).fillna(0)

        with colA:
            fig_status = px.bar(x=status_counts.index, y=status_counts.values, title="Lead Status Distribution")
            fig_status.update_xaxes(tickangle=35)
            st.plotly_chart(fig_status, use_container_width=True)

            status_tbl = pd.DataFrame({
                "Lead Status": status_counts.index,
                "Frequency": status_counts.values.astype(int),
                "Percent": (status_counts.values / status_counts.values.sum() * 100).round(1)
            })
            show_table(status_tbl)

    with colB:
        trend = filtered.groupby(filtered[submitted_col].dt.date).size().reset_index(name="Frequency")
        trend.columns = ["Date", "Frequency"]
        fig_trend = px.line(trend, x="Date", y="Frequency", title="Submissions Trend (Daily)", markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

        trend["Percent"] = (trend["Frequency"] / trend["Frequency"].sum() * 100).round(1)
        show_table(trend)

    st.dataframe(filtered.head(200), use_container_width=True)

# ---------------------------
# TAB 2: ASSIGNEE PERFORMANCE
# ---------------------------
with tab2:
    st.markdown('<div class="section-header">Assignee Performance</div>', unsafe_allow_html=True)
    assignee_col = FIELD["assignee"]

    if assignee_col not in filtered.columns:
        st.warning(f"Column '{assignee_col}' not found. Update FIELD mapping.")
    else:
        tmp = filtered.copy()
        tmp["_converted"] = (tmp[status_col] == "Converted to Client") if status_col in tmp.columns else False

        m = tmp.groupby(assignee_col).agg(
            Frequency=(assignee_col, "size"),
            Converted=("_converted", "sum")
        ).reset_index()

        m["Conversion %"] = np.where(m["Frequency"] > 0, (m["Converted"] / m["Frequency"] * 100).round(1), 0)
        m["Percent"] = (m["Frequency"] / m["Frequency"].sum() * 100).round(1)
        m = m.sort_values("Frequency", ascending=False)

        colA, colB = st.columns(2)

        with colA:
            fig = px.bar(m, x=assignee_col, y="Frequency", title="Total Submissions by Assignee")
            fig.update_xaxes(tickangle=25)
            st.plotly_chart(fig, use_container_width=True)
            show_table(m[[assignee_col, "Frequency", "Percent"]])

        with colB:
            fig2 = px.bar(
                m, x=assignee_col, y="Conversion %",
                title="Conversion % by Assignee",
                text=m["Conversion %"].map(lambda x: f"{x:.1f}%")
            )
            fig2.update_xaxes(tickangle=25)
            st.plotly_chart(fig2, use_container_width=True)

            conv_tbl = m[[assignee_col, "Frequency", "Percent", "Converted", "Conversion %"]]
            st.dataframe(conv_tbl.style.format({"Percent": "{:.1f}%", "Conversion %": "{:.1f}%"}), use_container_width=True)

# ---------------------------
# TAB 3: INQUIRY SOURCE
# ---------------------------
with tab3:
    st.markdown('<div class="section-header">Inquiry Source</div>', unsafe_allow_html=True)
    source_col = FIELD["inquiry_source"]

    if source_col not in filtered.columns:
        st.warning(f"Column '{source_col}' not found. Update FIELD mapping.")
    else:
        tbl = freq_percent_table(filtered[source_col], label_name="Inquiry Source")
        colA, colB = st.columns(2)

        with colA:
            st.plotly_chart(
                px.pie(tbl, names="Inquiry Source", values="Frequency", title="Share of Leads by Source"),
                use_container_width=True
            )
            show_table(tbl)

        with colB:
            fig = px.bar(tbl, x="Inquiry Source", y="Frequency", title="Frequency by Source")
            fig.update_xaxes(tickangle=25)
            st.plotly_chart(fig, use_container_width=True)
            show_table(tbl)

# ---------------------------
# TAB 4: INQUIRY TYPE
# ---------------------------
with tab4:
    st.markdown('<div class="section-header">Inquiry Type</div>', unsafe_allow_html=True)
    inquiry_type_col = FIELD["inquiry_type"]

    if inquiry_type_col not in filtered.columns:
        st.warning(f"Column '{inquiry_type_col}' not found. Update FIELD mapping.")
    else:
        exploded = explode_multiselect(filtered, inquiry_type_col)

        if exploded.empty:
            st.info("No multi-select values found.")
        else:
            counts = exploded[inquiry_type_col].value_counts().reset_index()
            counts.columns = ["Inquiry Type", "Frequency"]
            counts["Percent"] = (counts["Frequency"] / counts["Frequency"].sum() * 100).round(1)

            fig = px.bar(counts, x="Inquiry Type", y="Frequency", title="Inquiry Type Frequency")
            fig.update_xaxes(tickangle=25)
            st.plotly_chart(fig, use_container_width=True)
            show_table(counts)

# ---------------------------
# TAB 5: COUNTRIES
# ---------------------------
with tab5:
    st.markdown('<div class="section-header">Countries</div>', unsafe_allow_html=True)
    res_col = FIELD["country_residence"]
    org_col = FIELD["country_origin"]

    colA, colB = st.columns(2)

    with colA:
        if res_col in filtered.columns:
            tbl = freq_percent_table(filtered[res_col], label_name="Country of Residence").head(20)
            fig = px.bar(tbl, x="Country of Residence", y="Frequency", title="Top Countries of Residence")
            fig.update_xaxes(tickangle=25)
            st.plotly_chart(fig, use_container_width=True)
            show_table(tbl)
        else:
            st.warning(f"Column '{res_col}' not found.")

    with colB:
        if org_col in filtered.columns:
            tbl2 = freq_percent_table(filtered[org_col], label_name="Country of Origin").head(20)
            fig2 = px.bar(tbl2, x="Country of Origin", y="Frequency", title="Top Countries of Origin")
            fig2.update_xaxes(tickangle=25)
            st.plotly_chart(fig2, use_container_width=True)
            show_table(tbl2)
        else:
            st.warning(f"Column '{org_col}' not found.")

# ---------------------------
# TAB 6: FOLLOW-UP
# ---------------------------
with tab6:
    st.markdown('<div class="section-header">Follow-up</div>', unsafe_allow_html=True)
    next_action_col = FIELD["next_action"]

    colA, colB = st.columns(2)

    with colA:
        if next_action_col in filtered.columns:
            tbl = freq_percent_table(filtered[next_action_col], label_name="Next Action")
            fig = px.bar(tbl, x="Next Action", y="Frequency", title="Next Action Distribution")
            fig.update_xaxes(tickangle=25)
            st.plotly_chart(fig, use_container_width=True)
            show_table(tbl)
        else:
            st.warning(f"Column '{next_action_col}' not found.")

    with colB:
        if status_col in filtered.columns:
            tbl2 = freq_percent_table(filtered[status_col], label_name="Lead Status")
            st.plotly_chart(
                px.pie(tbl2, names="Lead Status", values="Frequency", title="Lead Status Share"),
                use_container_width=True
            )
            show_table(tbl2)
        else:
            st.warning(f"Column '{status_col}' not found.")

# ---------------------------
# EXPORT
# ---------------------------
st.markdown("---")
st.markdown('<div class="section-header">📥 Export</div>', unsafe_allow_html=True)

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Data (CSV)",
    data=csv,
    file_name=f"sacb_leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)