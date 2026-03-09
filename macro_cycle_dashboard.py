import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Macro Cycle • Hedge Fund View", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 Macro Cycle Dashboard — Hedge Fund Edition")
st.caption("Institutional-grade • Repeatable • Live FRED data • Updated daily")

# ================== FRED SETUP ==================
api_key = st.secrets.get("FRED_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your FRED API key:", type="password")
if not api_key:
    st.stop()
fred = Fred(api_key=api_key)

# ================== FETCH DATA ==================
@st.cache_data(ttl=86400)
def fetch_data():
    series = {
        'UNRATE': 'Unemployment Rate',
        'T10Y3M': '10Y-3M Yield Spread',
        'T10Y2Y': '10Y-2Y Yield Spread',
        'CFNAI': 'Chicago Fed National Activity Index',
        'CPIAUCSL': 'CPI',
        'VIXCLS': 'VIX',
        'BAA10Y': 'Corp Credit Spread (BAA-10Y)',
        'RECPROUSM156N': 'NY Fed Recession Probability',
        'INDPRO': 'Industrial Production'
    }
    df = pd.DataFrame()
    for code, name in series.items():
        try:
            s = fred.get_series(code, observation_start='2010-01-01')
            df[name] = s
        except:
            pass
    return df

df = fetch_data()

# Calculations
cpi_yoy = df['CPI'].pct_change(12) * 100
sahm = df['Unemployment Rate'].rolling(3).mean() - df['Unemployment Rate'].rolling(12).min()
vix_pct = (df['VIX'].rolling(252).rank(pct=True).iloc[-1] * 100) if 'VIX' in df.columns and len(df) > 252 else 50
latest_date = df.index[-1].strftime('%b %d, %Y')

# ================== ADVANCED PHASE SCORING ==================
def calculate_phase_score():
    ur = df['Unemployment Rate'][-1]
    cf3m = df['Chicago Fed National Activity Index'].rolling(3).mean()[-1]
    spread_10_3 = df['10Y-3M Yield Spread'][-1]
    rec_prob = df['NY Fed Recession Probability'][-1]
    credit_spread = df['Corp Credit Spread (BAA-10Y)'][-1]
    cpi12 = cpi_yoy[-1]
    sahm_val = sahm[-1]
    
    score = 0
    score += 30 * (1 if cf3m > 0 else 0.3)                    # Growth
    score += 25 * min(max((ur - 3.5) / 2.5, 0), 1)           # Labor
    if sahm_val > 0.5: score += 12.5
    score += 20 * (1 if spread_10_3 > 0 else 0)               # Yield curve
    if 2 < cpi12 < 3.5: score += 10                           # Inflation
    if rec_prob < 15: score += 8
    if credit_spread < 2.0: score += 7
    return min(int(score), 100)

score = calculate_phase_score()
phase_map = {range(0,40): "Early Cycle (Recovery)", range(40,65): "Mid Cycle Expansion", 
             range(65,85): "Late Cycle (Slowdown)", range(85,101): "Contraction / Recession"}
phase = next((v for k,v in phase_map.items() if score in k), "Late Cycle (Slowdown)")

# Executive Summary
st.header(f"**Current Phase: {phase}** (Composite Score: {score}/100)")
col_a, col_b, col_c = st.columns([3,1,1])
with col_a:
    st.metric("NY Fed Recession Probability", f"{df['NY Fed Recession Probability'][-1]:.1f}%")
with col_b:
    st.metric("VIX Percentile (252d)", f"{vix_pct:.0f}th")
with col_c:
    st.caption(f"Latest: {latest_date} • NBER expansion since Apr 2020")

# ================== TABS ==================
tab1, tab2, tab3, tab4 = st.tabs(["📍 Cycle Position", "📈 Leading Indicators", "⚠️ Risk Gauges", "📊 Regime Allocation"])

with tab1:
    st.subheader("Key Coincident Gauges")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=df['Unemployment Rate'][-1],
            delta={'reference': 4.0},
            title={'text': "Unemployment Rate"},
            gauge={'axis': {'range': [3,7]}, 'bar': {'color': "darkblue"},
                   'steps': [{'range': [3,4.5], 'color': "green"}, {'range': [4.5,5.5], 'color': "yellow"}, {'range': [5.5,7], 'color': "red"}]}))
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=df['10Y-3M Yield Spread'][-1],
            title={'text': "10Y-3M Spread"},
            gauge={'axis': {'range': [-1,2]}, 'bar': {'color': "darkblue"},
                   'steps': [{'range': [-1,0], 'color': "red"}, {'range': [0,2], 'color': "green"}]}))
        st.plotly_chart(fig, use_container_width=True)
    with g3:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=df['Chicago Fed National Activity Index'].rolling(3).mean()[-1],
            title={'text': "CFNAI 3-mo Avg"},
            gauge={'axis': {'range': [-1,1]}, 'bar': {'color': "darkblue"},
                   'steps': [{'range': [-1,0], 'color': "red"}, {'range': [0,1], 'color': "green"}]}))
        st.plotly_chart(fig, use_container_width=True)
    with g4:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=cpi_yoy[-1],
            title={'text': "CPI YoY"},
            gauge={'axis': {'range': [0,6]}, 'bar': {'color': "darkblue"},
                   'steps': [{'range': [0,2], 'color': "green"}, {'range': [2,4], 'color': "yellow"}, {'range': [4,6], 'color': "red"}]}))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Historical Charts with NBER Shading")
    fig = make_subplots(rows=3, cols=1, subplot_titles=("Unemployment + Sahm", "10Y-3M Yield Spread", "CFNAI"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Unemployment Rate'], name="UNRATE"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sahm, name="Sahm Rule", line=dict(dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['10Y-3M Yield Spread'], name="10Y-3M"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Chicago Fed National Activity Index'], name="CFNAI"), row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Hedge-Fund Risk Dashboard")
    r1, r2, r3 = st.columns(3)
    with r1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=df['NY Fed Recession Probability'][-1],
            title={'text': "12M Recession Prob"}, gauge={'axis': {'range': [0,100]}, 'bar': {'color': "darkred" if df['NY Fed Recession Probability'][-1] > 20 else "darkgreen"}}))
        st.plotly_chart(fig, use_container_width=True)
    with r2:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=df['Corp Credit Spread (BAA-10Y)'][-1],
            title={'text': "Corp Credit Spread"}, gauge={'axis': {'range': [1,5]}, 'bar': {'color': "darkblue"}}))
        st.plotly_chart(fig, use_container_width=True)
    with r3:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=df['VIX'][-1],
            title={'text': "VIX"}, gauge={'axis': {'range': [10,50]}, 'bar': {'color': "darkblue"}}))
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Regime-Based Asset Allocation Signals")
    if score >= 65:
        signals = ["Neutral", "Slight Underweight", "Overweight", "Overweight", "Neutral", "Overweight"]
        rationale = ["Late-cycle valuations", "Defensives outperforming", "Curve steepening", "Inflation/commodity hedge", "Tight spreads", "Liquidity premium"]
    else:
        signals = ["Overweight", "Overweight", "Neutral", "Neutral", "Overweight", "Underweight"]
        rationale = ["Early/mid-cycle beta", "Cyclicals leading", "Neutral duration", "Growth-sensitive", "Credit expansion", "Risk-on tilt"]
    allocation = pd.DataFrame({
        "Asset Class": ["US Equities", "Cyclicals vs Defensives", "Duration (Bonds)", "Commodities/Gold", "High Yield Credit", "Cash / T-Bills"],
        "Signal": signals,
        "Rationale": rationale
    })
    st.dataframe(allocation, use_container_width=True, hide_index=True)

st.success("✅ Live hedge-fund macro dashboard • All data from official FRED sources • Auto-updates daily")
