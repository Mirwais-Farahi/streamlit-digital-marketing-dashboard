import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="SACB Group Services Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin: 1rem 0;
    }
    .insight-box {
        background: #f8f9fa;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    np.random.seed(42)

    # Weekly reporting period
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='W')

    # Client origin markets
    client_markets = ['UAE', 'GCC', 'South Asia', 'Africa', 'Europe', 'North America']

    # SACB service categories and services
    service_catalog = {
        'Business Setup': [
            'Mainland Company Formation',
            'Free Zone Company Formation',
            'Offshore Company Formation',
            'Trade License Issuance & Renewal',
            'Visa & Immigration Services'
        ],
        'Legal Advisory': [
            'Corporate Legal Advisory',
            'Contract Drafting & Review',
            'Compliance & Regulatory Advisory',
            'Labour Law Advisory',
            'Commercial Dispute Advisory'
        ],
        'Tax Advisory': [
            'UAE Corporate Tax Registration',
            'VAT Registration & Filing',
            'Tax Planning & Structuring',
            'ESR & UBO Compliance'
        ],
        'PSW Services': [
            'PRO & Government Liaison Services',
            'Document Attestation & Notarization',
            'Bank Account Opening Support',
            'Power of Attorney Services',
            'Ongoing Compliance Retainer'
        ]
    }

    # Lead sources
    lead_sources = ['Website', 'Google Search', 'WhatsApp', 'Referral', 'Email', 'Social Media']

    data = []

    for date in dates:
        for _ in range(np.random.randint(1, 4)):
            service_category = np.random.choice(list(service_catalog.keys()))
            service_name = np.random.choice(service_catalog[service_category])

            service_reach = np.random.randint(300, 6000)
            client_inquiries = np.random.randint(10, 250)
            signed_clients = np.random.randint(1, max(2, int(client_inquiries * 0.4)))

            acquisition_cost = np.random.uniform(1000, 20000)
            revenue = np.random.uniform(5000, 250000)

            row = {
                'Reporting_Week': date,
                'Reporting_Year': date.year,
                'Reporting_Month': date.strftime('%B'),
                'Reporting_Quarter': f"Q{(date.month - 1) // 3 + 1}",

                'Client_Origin_Market': np.random.choice(client_markets),
                'Service_Category': service_category,
                'Service_Name': service_name,
                'Lead_Source': np.random.choice(lead_sources),

                'Service_Reach': service_reach,
                'Client_Inquiries': client_inquiries,
                'Signed_Clients': signed_clients,

                'Client_Acquisition_Cost': acquisition_cost,
                'Service_Revenue_AED': revenue
            }
            data.append(row)

    df = pd.DataFrame(data)
    df['Reporting_Week'] = pd.to_datetime(df['Reporting_Week'])

    # Derived metrics
    df['Inquiry_Rate'] = df['Client_Inquiries'] / df['Service_Reach']
    df['Client_Conversion_Rate'] = df['Signed_Clients'] / df['Client_Inquiries']
    df['Cost_per_Inquiry'] = df['Client_Acquisition_Cost'] / df['Client_Inquiries']
    df['Cost_per_Signed_Client'] = df['Client_Acquisition_Cost'] / df['Signed_Clients']
    df['Revenue_per_Inquiry'] = df['Service_Revenue_AED'] / df['Client_Inquiries']
    df['Service_ROI'] = df['Service_Revenue_AED'] / df['Client_Acquisition_Cost']

    return df


# Load SACB dataset
df = load_data()

# Sidebar filters
st.sidebar.markdown("## 🎛️ Filters")

# Date filter (SACB)
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df['Reporting_Week'].min().date(), df['Reporting_Week'].max().date()),
    min_value=df['Reporting_Week'].min().date(),
    max_value=df['Reporting_Week'].max().date()
)

# Client market filter
markets = st.sidebar.multiselect(
    "Select Client Origin Markets",
    options=sorted(df['Client_Origin_Market'].unique()),
    default=sorted(df['Client_Origin_Market'].unique())
)

# Service Category filter
service_categories = st.sidebar.multiselect(
    "Select Service Categories",
    options=sorted(df['Service_Category'].unique()),
    default=sorted(df['Service_Category'].unique())
)

# --- Dependent Service Name filter (Category -> Services) ---
# If no category selected, show none (or you can show all)
if service_categories:
    available_services = (
        df.loc[df['Service_Category'].isin(service_categories), 'Service_Name']
        .dropna()
        .unique()
    )
    available_services = sorted(available_services)
else:
    available_services = []

# Keep previously selected services if still valid
# (prevents errors when user changes categories)
default_services = available_services  # default = all available under selected categories

service_names = st.sidebar.multiselect(
    "Select Services",
    options=available_services,
    default=default_services
)

# Lead Source filter
lead_sources = st.sidebar.multiselect(
    "Select Lead Sources",
    options=sorted(df['Lead_Source'].unique()),
    default=sorted(df['Lead_Source'].unique())
)

# Apply filters
filtered_df = df[
    (df['Reporting_Week'] >= pd.to_datetime(date_range[0])) &
    (df['Reporting_Week'] <= pd.to_datetime(date_range[1])) &
    (df['Client_Origin_Market'].isin(markets)) &
    (df['Service_Category'].isin(service_categories)) &
    (df['Service_Name'].isin(service_names)) &
    (df['Lead_Source'].isin(lead_sources))
].copy()

# Header
st.markdown('<div class="main-header">📊 SACB Group Services Analytics Dashboard</div>', unsafe_allow_html=True)

# KPI Section
st.markdown('<div class="section-header">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_cost = filtered_df['Client_Acquisition_Cost'].sum()
    st.metric("Total Acquisition Cost", f"AED {total_cost:,.0f}")

with col2:
    total_revenue = filtered_df['Service_Revenue_AED'].sum()
    st.metric("Total Revenue", f"AED {total_revenue:,.0f}")

with col3:
    overall_roi = (total_revenue / total_cost) if total_cost > 0 else 0
    st.metric("Overall ROI", f"{overall_roi:.2f}x")

with col4:
    avg_inquiry_rate = filtered_df['Inquiry_Rate'].mean()
    st.metric("Average Inquiry Rate", f"{avg_inquiry_rate*100:.2f}%")

with col5:
    total_signed = filtered_df['Signed_Clients'].sum()
    st.metric("Signed Clients", f"{total_signed:,.0f}")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "🌍 Client Market Analysis",
    "🧩 Service Performance",
    "📢 Lead Source Analysis",
    "📅 Time Series",
    "🎯 Advanced Analytics"
])

# -------------------- TAB 1: Overview --------------------
with tab1:
    st.markdown('<div class="section-header">Dashboard Overview</div>', unsafe_allow_html=True)

    colA, colB = st.columns(2)

    with colA:
        fig_scatter = px.scatter(
            filtered_df,
            x='Client_Acquisition_Cost',
            y='Service_Revenue_AED',
            color='Lead_Source',
            size='Signed_Clients',
            hover_data=['Client_Origin_Market', 'Service_Category', 'Service_Name', 'Service_ROI'],
            title="Revenue vs Acquisition Cost by Lead Source"
        )
        fig_scatter.update_layout(height=420)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with colB:
        fig_hist = px.histogram(
            filtered_df,
            x='Service_ROI',
            nbins=20,
            title="ROI Distribution (Service_ROI)"
        )
        fig_hist.update_layout(height=420)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown('<div class="section-header">🏆 Top Performing Service Slices</div>', unsafe_allow_html=True)

    top_slices = filtered_df.nlargest(10, 'Service_ROI')[[
        'Reporting_Week',
        'Client_Origin_Market',
        'Service_Category',
        'Service_Name',
        'Lead_Source',
        'Client_Acquisition_Cost',
        'Service_Revenue_AED',
        'Service_ROI',
        'Signed_Clients'
    ]]

    st.dataframe(top_slices.style.format({
        'Client_Acquisition_Cost': 'AED {:,.0f}',
        'Service_Revenue_AED': 'AED {:,.0f}',
        'Service_ROI': '{:.2f}x',
        'Signed_Clients': '{:,.0f}'
    }), use_container_width=True)

# -------------------- TAB 2: Client Market Analysis --------------------
with tab2:
    st.markdown('<div class="section-header">🌍 Client Market Performance Analysis</div>', unsafe_allow_html=True)

    market_metrics = filtered_df.groupby('Client_Origin_Market').agg({
        'Client_Acquisition_Cost': 'sum',
        'Service_Revenue_AED': 'sum',
        'Signed_Clients': 'sum',
        'Service_ROI': 'mean',
        'Inquiry_Rate': 'mean',
        'Cost_per_Inquiry': 'mean'
    }).round(4)

    colA, colB = st.columns(2)

    with colA:
        fig_pie = px.pie(
            values=market_metrics['Service_Revenue_AED'],
            names=market_metrics.index,
            title="Revenue Distribution by Client Origin Market"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with colB:
        fig_bar = px.bar(
            x=market_metrics.index,
            y=market_metrics['Service_ROI'],
            title="Average ROI by Client Origin Market",
            color=market_metrics['Service_ROI']
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### Client Market Performance Summary")
    st.dataframe(market_metrics.style.format({
        'Client_Acquisition_Cost': 'AED {:,.0f}',
        'Service_Revenue_AED': 'AED {:,.0f}',
        'Signed_Clients': '{:,.0f}',
        'Service_ROI': '{:.2f}x',
        'Inquiry_Rate': '{:.2%}',
        'Cost_per_Inquiry': 'AED {:.2f}'
    }), use_container_width=True)

# -------------------- TAB 3: Service Performance --------------------
with tab3:
    st.markdown('<div class="section-header">🧩 Service Performance Analysis</div>', unsafe_allow_html=True)

    service_metrics = filtered_df.groupby('Service_Name').agg({
        'Client_Acquisition_Cost': 'sum',
        'Service_Revenue_AED': 'sum',
        'Signed_Clients': 'sum',
        'Service_ROI': 'mean',
        'Inquiry_Rate': 'mean',
        'Client_Conversion_Rate': 'mean'
    }).round(4)

    colA, colB = st.columns(2)

    with colA:
        fig_bar = px.bar(
            x=service_metrics.index,
            y=service_metrics['Service_Revenue_AED'],
            title="Total Revenue by Service",
            color=service_metrics['Service_Revenue_AED']
        )
        fig_bar.update_xaxes(tickangle=45)
        st.plotly_chart(fig_bar, use_container_width=True)

    with colB:
        fig_scatter = px.scatter(
            x=service_metrics['Service_ROI'],
            y=service_metrics['Signed_Clients'],
            text=service_metrics.index,
            title="ROI vs Signed Clients by Service",
            size=service_metrics['Service_Revenue_AED']
        )
        fig_scatter.update_traces(textposition="top center")
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("### Service vs Lead Source (ROI Heatmap)")
    heatmap_data = filtered_df.pivot_table(
        values='Service_ROI',
        index='Service_Name',
        columns='Lead_Source',
        aggfunc='mean'
    ).round(3)

    fig_heatmap = px.imshow(
        heatmap_data,
        title="Average ROI: Service vs Lead Source",
        aspect="auto"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# -------------------- TAB 4: Lead Source Analysis --------------------
with tab4:
    st.markdown('<div class="section-header">📢 Lead Source Analysis</div>', unsafe_allow_html=True)

    channel_metrics = filtered_df.groupby('Lead_Source').agg({
        'Client_Acquisition_Cost': 'sum',
        'Service_Revenue_AED': 'sum',
        'Client_Inquiries': 'sum',
        'Signed_Clients': 'sum',
        'Service_ROI': 'mean',
        'Inquiry_Rate': 'mean',
        'Cost_per_Inquiry': 'mean'
    }).round(4)

    colA, colB = st.columns(2)

    with colA:
        fig_radar = go.Figure()

        normalized = channel_metrics[['Service_ROI', 'Inquiry_Rate', 'Signed_Clients']].copy()
        for col in normalized.columns:
            denom = (normalized[col].max() - normalized[col].min())
            normalized[col] = (normalized[col] - normalized[col].min()) / denom if denom != 0 else 0

        for channel in normalized.index:
            fig_radar.add_trace(go.Scatterpolar(
                r=[normalized.loc[channel, 'Service_ROI'],
                   normalized.loc[channel, 'Inquiry_Rate'],
                   normalized.loc[channel, 'Signed_Clients']],
                theta=['ROI', 'Inquiry Rate', 'Signed Clients'],
                fill='toself',
                name=channel
            ))

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True,
            title="Lead Source Performance Comparison (Normalized)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with colB:
        fig_bubble = px.scatter(
            x=channel_metrics['Client_Acquisition_Cost'],
            y=channel_metrics['Service_Revenue_AED'],
            size=channel_metrics['Signed_Clients'],
            color=channel_metrics['Service_ROI'],
            hover_name=channel_metrics.index,
            title="Acquisition Cost vs Revenue by Lead Source",
            labels={'x': 'Total Acquisition Cost', 'y': 'Total Revenue'}
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    st.markdown("### Lead Source Performance Metrics")
    st.dataframe(channel_metrics.style.format({
        'Client_Acquisition_Cost': 'AED {:,.0f}',
        'Service_Revenue_AED': 'AED {:,.0f}',
        'Client_Inquiries': '{:,.0f}',
        'Signed_Clients': '{:,.0f}',
        'Service_ROI': '{:.2f}x',
        'Inquiry_Rate': '{:.2%}',
        'Cost_per_Inquiry': 'AED {:.2f}'
    }), use_container_width=True)

# -------------------- TAB 5: Time Series --------------------
with tab5:
    st.markdown('<div class="section-header">📅 Time Series Analysis</div>', unsafe_allow_html=True)

    time_series = filtered_df.groupby('Reporting_Week').agg({
        'Client_Acquisition_Cost': 'sum',
        'Service_Revenue_AED': 'sum',
        'Client_Inquiries': 'sum',
        'Signed_Clients': 'sum',
        'Service_ROI': 'mean'
    }).reset_index()

    fig_ts = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Revenue Over Time', 'ROI Over Time', 'Inquiries Over Time', 'Signed Clients Over Time')
    )

    fig_ts.add_trace(go.Scatter(x=time_series['Reporting_Week'], y=time_series['Service_Revenue_AED'], name='Revenue'), row=1, col=1)
    fig_ts.add_trace(go.Scatter(x=time_series['Reporting_Week'], y=time_series['Service_ROI'], name='ROI'), row=1, col=2)
    fig_ts.add_trace(go.Scatter(x=time_series['Reporting_Week'], y=time_series['Client_Inquiries'], name='Inquiries'), row=2, col=1)
    fig_ts.add_trace(go.Scatter(x=time_series['Reporting_Week'], y=time_series['Signed_Clients'], name='Signed Clients'), row=2, col=2)

    fig_ts.update_layout(height=650, title_text="Weekly Performance Metrics Over Time")
    st.plotly_chart(fig_ts, use_container_width=True)

    st.markdown("### Monthly Trends")

    monthly_data = filtered_df.groupby('Reporting_Month').agg({
        'Client_Acquisition_Cost': 'sum',
        'Service_Revenue_AED': 'sum',
        'Service_ROI': 'mean',
        'Signed_Clients': 'sum'
    }).round(4)

    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    monthly_data = monthly_data.reindex([m for m in month_order if m in monthly_data.index])

    colA, colB = st.columns(2)

    with colA:
        fig_monthly_rev = px.bar(
            x=monthly_data.index,
            y=monthly_data['Service_Revenue_AED'],
            title="Monthly Revenue Trend"
        )
        fig_monthly_rev.update_xaxes(tickangle=45)
        st.plotly_chart(fig_monthly_rev, use_container_width=True)

    with colB:
        fig_monthly_roi = px.line(
            x=monthly_data.index,
            y=monthly_data['Service_ROI'],
            title="Monthly ROI Trend",
            markers=True
        )
        fig_monthly_roi.update_xaxes(tickangle=45)
        st.plotly_chart(fig_monthly_roi, use_container_width=True)

# -------------------- TAB 6: Advanced Analytics --------------------
with tab6:
    st.markdown('<div class="section-header">🎯 Advanced Analytics</div>', unsafe_allow_html=True)

    st.markdown("### ROI Performance Segmentation")

    filtered_df['ROI_Segment'] = pd.cut(
        filtered_df['Service_ROI'],
        bins=[-float('inf'), 2, 5, 10, float('inf')],
        labels=['Low (≤2)', 'Medium (2-5)', 'High (5-10)', 'Very High (>10)']
    )

    colA, colB = st.columns(2)

    with colA:
        roi_segments = filtered_df['ROI_Segment'].value_counts()
        fig_pie_roi = px.pie(
            values=roi_segments.values,
            names=roi_segments.index,
            title="Service Slices Distribution by ROI Segments"
        )
        st.plotly_chart(fig_pie_roi, use_container_width=True)

    with colB:
        segment_perf = filtered_df.groupby('ROI_Segment').agg({
            'Client_Acquisition_Cost': 'sum',
            'Service_Revenue_AED': 'sum',
            'Signed_Clients': 'sum'
        })

        fig_segment = px.bar(
            x=segment_perf.index,
            y=segment_perf['Service_Revenue_AED'],
            title="Revenue by ROI Segments",
            color=segment_perf['Service_Revenue_AED']
        )
        st.plotly_chart(fig_segment, use_container_width=True)

    st.markdown("### Correlation Analysis")

    correlation_cols = [
        'Client_Acquisition_Cost',
        'Service_Reach',
        'Client_Inquiries',
        'Signed_Clients',
        'Service_Revenue_AED',
        'Inquiry_Rate',
        'Cost_per_Inquiry',
        'Service_ROI'
    ]
    corr = filtered_df[correlation_cols].corr()

    fig_corr = px.imshow(
        corr,
        title="Correlation Matrix of Key SACB Metrics",
        aspect="auto"
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("### Outlier Detection")

    outlier_metric = st.selectbox(
        "Select metric for outlier analysis:",
        ['Client_Acquisition_Cost', 'Service_Revenue_AED', 'Service_ROI', 'Inquiry_Rate', 'Cost_per_Inquiry']
    )

    Q1 = filtered_df[outlier_metric].quantile(0.25)
    Q3 = filtered_df[outlier_metric].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    outliers = filtered_df[(filtered_df[outlier_metric] < lower_bound) | (filtered_df[outlier_metric] > upper_bound)]

    colA, colB = st.columns(2)

    with colA:
        fig_box = px.box(
            filtered_df,
            y=outlier_metric,
            title=f"{outlier_metric} Distribution with Outliers"
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with colB:
        st.write(f"**Outlier Analysis for {outlier_metric}:**")
        st.write(f"- Total outliers detected: {len(outliers)}")
        st.write(f"- Percentage of outliers: {(len(outliers)/len(filtered_df))*100:.1f}%")
        if len(outliers) > 0:
            st.write(f"- Outlier range: {outliers[outlier_metric].min():.4f} to {outliers[outlier_metric].max():.4f}")
            st.write(f"- Normal range: {lower_bound:.4f} to {upper_bound:.4f}")

# Footer
st.markdown("---")
st.markdown("### 📊 Dashboard Features")
st.markdown("""
- **Interactive Filters**: Filter by date range, client market, service category, service name, and lead source
- **Real-time Updates**: Charts update automatically based on your filter selections
- **Export Data**: Download filtered dataset for reporting
- **SACB Context**: Metrics aligned with service inquiries and signed clients
""")

# Data export
st.markdown("### 📥 Data Export")
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download Filtered Data (CSV)",
    data=csv,
    file_name=f"sacb_services_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# Dataset info
with st.expander("📋 Dataset Information"):
    colA, colB = st.columns(2)
    with colA:
        st.write(f"**Total Records:** {len(filtered_df):,}")
        st.write(f"**Date Range:** {filtered_df['Reporting_Week'].min().strftime('%Y-%m-%d')} to {filtered_df['Reporting_Week'].max().strftime('%Y-%m-%d')}")
        st.write(f"**Client Markets:** {', '.join(sorted(filtered_df['Client_Origin_Market'].unique()))}")
    with colB:
        st.write(f"**Service Categories:** {', '.join(sorted(filtered_df['Service_Category'].unique()))}")
        st.write(f"**Lead Sources:** {', '.join(sorted(filtered_df['Lead_Source'].unique()))}")
        st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")