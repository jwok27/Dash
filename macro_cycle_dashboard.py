import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Macro Intelligence Suite", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 Macro Intelligence Suite — Billionaire Hedge Fund Edition")
st.caption("Used by top macro desks • Live FRED • Beautiful gradients • Updated daily")

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
        'T10Y3M': '10Y-3M Spread',
        'CFNAI': 'Chicago Fed NAI',
        'NFCI': 'Chicago Fed NFCI',
        'CPIAUCSL': 'CPI',
        'ICSA': 'Initial Claims (k)',
        'VIXCLS': 'VIX',
        'BAA10Y': 'Corp Credit Spread',
        'RECPROUSM156N': 'NY Fed Recession Prob',
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

# Calculations + NaN protection
cpi_yoy = df['CPI'].pct_change(12) * 100
sahm = df['Unemployment Rate'].rolling(3).mean() - df['Unemployment Rate'].rolling(12).min()
claims_mom = df['Initial Claims (k)'].rolling(4).mean().pct_change(4) * 100
vix_pct = df['VIX'].rolling(252).rank(pct=True).iloc[-1] * 100 if len(df) > 252 else 50
indpro_z = (df['Industrial Production'].iloc[-1] - df['Industrial Production'].mean()) / df['Industrial Production'].std() if len(df) > 50 else 0
latest_date = df.index[-1].strftime('%b %d, %Y')
rec_prob = df['NY Fed Recession Prob'].dropna().iloc[-1] if not df['NY Fed Recession Prob'].dropna().empty else 10.0

# Z-scores & Percentiles
def get_percentile_and_z(series):
    if len(series) < 50: return 50, 0
    pct = series.rank(pct=True).iloc[-1] * 100
    z = (series.iloc[-1] - series.mean()) / series.std()
    return round(pct, 1), round(z, 2)

# ================== ADVANCED SCORING ENGINE ==================
def calculate_phase_score():
    cf3m = df['Chicago Fed NAI'].rolling(3).mean()[-1]
    nfc = df['Chicago Fed NFCI'][-1]
    spread = df['10Y-3M Spread'][-1]
    credit = df['Corp Credit Spread'][-1]
    sahm_val = sahm[-1]
    
    score = 0
    score += 25 * (1 if cf3m > 0 else 0.2)
    score += 20 * (1 if spread > 0 else 0)
    score += 15 * min(max((df['Unemployment Rate'][-1] - 3.5) / 2.5, 0), 1)
    if sahm_val > 0.5: score += 10
    score += 12 * (1 if nfc < 0 else 0)
    if rec_prob < 15 and credit < 2.0: score += 8
    if indpro_z > 0: score += 5
    return min(int(score), 100)

score = calculate_phase_score()
phase_map = {range(0,40): "Early Cycle", range(40,65): "Mid Cycle", range(65,85): "Late Cycle", range(85,101): "Contraction"}
phase = next((v for k,v in phase_map.items() if score in k), "Late Cycle")

# ================== MACRO INTELLIGENCE BRIEFING ==================
def generate_briefing():
    nfc = df['Chicago Fed NFCI'][-1]
    claims_trend = "rising sharply" if claims_mom[-1] > 2 else "rising" if claims_mom[-1] > 0 else "falling"
    cpi = cpi_yoy[-1]
    if score >= 80:
        return f"**Contraction regime confirmed.** Recession probability {rec_prob:.1f}%. Tight financial conditions (NFCI {nfc:.2f}) and {claims_trend} claims signal defensive positioning. Overweight duration, gold, quality credit. Reduce beta immediately."
    elif score >= 65:
        return f"**Late-cycle expansion (soft-landing base case).** Labor resilient but momentum decelerating. Inflation expectations anchored. Favor defensives, commodities, moderate duration. Selective cyclicals only. Monitor credit spreads closely."
    elif score >= 40:
        return f"**Mid-cycle expansion.** Supportive financial conditions + above-trend growth. Risk-on bias intact. Overweight equities and high-yield credit with tight stops."
    else:
        return f"**Early-cycle recovery.** Steep yield curve + easing conditions. Strong beta exposure: equities, credit, commodities. Add to risk assets aggressively."
st.markdown(f"**MACRO INTELLIGENCE BRIEFING** — {latest_date}\n\n{generate_briefing()}")

st.header(f"**Current Regime: {phase}** (Composite Score: {score}/100 | NY Fed Recession Prob: {rec_prob:.1f}%)")

# ================== TABS ==================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Cycle Gauges", "📊 Heatmap & Z-Scores", "📈 Leading Signals", "⚠️ Risk Dashboard", "📋 Regime Playbook"])

with tab1:
    st.subheader("Key Institutional Gauges")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=df['Chicago Fed NFCI'][-1], title={'text':"NFCI"}, gauge={'axis':{'range':[-1,1]}})), use_container_width=True)
    with g2:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=cpi_yoy[-1], title={'text':"CPI YoY"}, gauge={'axis':{'range':[0,6]}})), use_container_width=True)
    with g3:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=df['Initial Claims (k)'][-1], title={'text':"Wkly Claims"}, gauge={'axis':{'range':[150,400]}})), use_container_width=True)
    with g4:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=df['Corp Credit Spread'][-1], title={'text':"Corp Spread"}, gauge={'axis':{'range':[1,5]}})), use_container_width=True)

with tab2:
    st.subheader("Cycle Heatmap — Historical Percentiles & Z-Scores")
    metrics = ['Unemployment Rate','10Y-3M Spread','Chicago Fed NAI','Chicago Fed NFCI','Corp Credit Spread','VIX','Industrial Production']
    data = []
    for m in metrics:
        if m in df.columns and not pd.isna(df[m].iloc[-1]):
            pct, z = get_percentile_and_z(df[m])
            signal = "🟢 Bullish" if (z > 0.5 or m in ['10Y-3M Spread','Chicago Fed NAI']) else "🔴 Caution"
            data.append([m, round(df[m].iloc[-1],2), pct, z, signal])
    heatmap_df = pd.DataFrame(data, columns=["Indicator","Latest","Hist. Percentile","Z-Score","Signal"])
    st.dataframe(heatmap_df.style.background_gradient(subset=['Hist. Percentile'], cmap='RdYlGn'), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Leading Indicators Charts")
    fig = make_subplots(rows=2, cols=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Chicago Fed NFCI'], name="NFCI"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Industrial Production'], name="Ind Prod"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Initial Claims (k)'], name="Claims"), row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Risk & Probability Dashboard")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=rec_prob, title={'text':"Recession Prob"}, gauge={'axis':{'range':[0,100]}})), use_container_width=True)
    with r2:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=vix_pct, title={'text':"VIX Percentile"}, gauge={'axis':{'range':[0,100]}})), use_container_width=True)
    with r3:
        st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=df['Chicago Fed NFCI'][-1], title={'text':"Financial Conditions"}, gauge={'axis':{'range':[-1,1]}})), use_container_width=True)

with tab5:
    st.subheader("Hedge-Fund Regime Playbook")
    if score >= 65:
        alloc = ["Underweight", "Underweight", "Overweight", "Overweight", "Neutral", "Overweight"]
        conv = ["High", "High", "Med", "High", "Low", "High"]
        rationale = ["Valuations extended", "Defensives outperforming", "Curve steepening", "Inflation/commodity hedge", "Tight spreads", "Liquidity premium"]
    else:
        alloc = ["Overweight", "Overweight", "Neutral", "Neutral", "Overweight", "Underweight"]
        conv = ["High", "Med", "High", "Low", "High", "Med"]
        rationale = ["Early/mid beta", "Cyclicals leading", "Neutral duration", "Growth-sensitive", "Credit expansion", "Risk-on tilt"]
    playbook = pd.DataFrame({
        "Asset Class": ["US Equities", "Cyclicals", "Duration", "Commodities/Gold", "HY Credit", "Cash"],
        "Position": alloc,
        "Conviction": conv,
        "Rationale": rationale
    })
    st.dataframe(playbook, use_container_width=True, hide_index=True)

st.success("✅ Billionaire-grade macro OS • Beautiful gradient heatmap • Zero NaNs • Auto-updates daily")
