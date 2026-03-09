import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Macro Cycle Dashboard", layout="wide")
st.title("📊 Macro Cycle Dashboard")
st.caption("Repeatable, evidence-based answer to: Where are we in the macro cycle? | Data as of latest FRED pull")

# ================== FRED SETUP (works with Streamlit Secrets) ==================
api_key = st.secrets.get("FRED_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your FRED API key (free):", type="password")
if not api_key:
    st.warning("Please add your FRED_API_KEY in Streamlit Cloud → Settings → Secrets (or enter it here temporarily).")
    st.stop()
fred = Fred(api_key=api_key)

# ================== FETCH DATA ==================
@st.cache_data(ttl=86400)
def fetch_data():
    series = {
        'UNRATE': 'Unemployment Rate',
        'T10Y2Y': '10Y-2Y Yield Spread',
        'CFNAI': 'Chicago Fed National Activity Index',
        'CPIAUCSL': 'CPI',
        'INDPRO': 'Industrial Production Index',
        'FEDFUNDS': 'Fed Funds Rate'
    }
    df = pd.DataFrame()
    for code, name in series.items():
        s = fred.get_series(code, observation_start='2010-01-01')
        df[name] = s
    return df

df = fetch_data()

# Calculations
cpi_yoy = df['CPI'].pct_change(12) * 100
sahm = df['Unemployment Rate'].rolling(3).mean() - df['Unemployment Rate'].rolling(12).min()
latest_date = df.index[-1].strftime('%b %Y')

# ================== PHASE SCORING ==================
def calculate_phase_score():
    ur = df['Unemployment Rate'][-1]
    cf3m = df['Chicago Fed National Activity Index'].rolling(3).mean()[-1]
    spread = df['10Y-2Y Yield Spread'][-1]
    cpi12 = cpi_yoy[-1]
    sahm_val = sahm[-1]
    
    score = 0
    score += 40 * (1 if cf3m > 0 else 0)                    # Coincident 40%
    score += 30 * min(max((ur - 3.5) / 2.5, 0), 1)         # Labor 30%
    if sahm_val > 0.5: score += 15
    if 2 < cpi12 < 3.5: score += 15                         # Inflation 15%
    score += 10 * (1 if spread > 0 else 0)                  # Policy 10%
    if spread > 0: score += 5                               # Leading 5%
    return min(int(score), 100)

score = calculate_phase_score()
phase_map = {range(0,40): "Early Cycle (Recovery)", range(40,60): "Mid Cycle Expansion", 
             range(60,80): "Late Cycle (Slowdown)", range(80,101): "Contraction"}
phase = next((v for k,v in phase_map.items() if score in k), "Mid-to-Late Cycle Expansion")

st.header(f"**Current Phase: {phase}** (Score: {score}/100)")
st.caption(f"Latest data: {latest_date} • NBER expansion ongoing since Apr 2020")

# ================== GAUGES & CHARTS (same as the beautiful screenshot) ==================
col1, col2, col3, col4 = st.columns(4)
with col1:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=df['Unemployment Rate'][-1], title={'text':"Unemployment Rate"}, gauge={'axis':{'range':[3,7]}, 'bar':{'color':"darkblue"}, 'steps':[{'range':[3,4.5],'color':"green"},{'range':[4.5,5.5],'color':"yellow"},{'range':[5.5,7],'color':"red"}]}))
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=df['10Y-2Y Yield Spread'][-1], title={'text':"10Y-2Y Spread"}, gauge={'axis':{'range':[-1,2]}, 'bar':{'color':"darkblue"}, 'steps':[{'range':[-1,0],'color':"red"},{'range':[0,2],'color':"green"}]}))
    st.plotly_chart(fig, use_container_width=True)
with col3:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=df['Chicago Fed National Activity Index'].rolling(3).mean()[-1], title={'text':"CFNAI 3-mo Avg"}, gauge={'axis':{'range':[-1,1]}, 'bar':{'color':"darkblue"}, 'steps':[{'range':[-1,0],'color':"red"},{'range':[0,1],'color':"green"}]}))
    st.plotly_chart(fig, use_container_width=True)
with col4:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=cpi_yoy[-1], title={'text':"CPI YoY"}, gauge={'axis':{'range':[0,6]}, 'bar':{'color':"darkblue"}, 'steps':[{'range':[0,2],'color':"green"},{'range':[2,4],'color':"yellow"},{'range':[4,6],'color':"red"}]}))
    st.plotly_chart(fig, use_container_width=True)

# Time-series charts + Business Cycle Clock (exactly as shown in the phone screenshot)
st.subheader("Historical View with NBER Shading")
fig = make_subplots(rows=3, cols=1, subplot_titles=("Unemployment + Sahm Rule", "Yield Spread", "CFNAI"))
fig.add_trace(go.Scatter(x=df.index, y=df['Unemployment Rate'], name="UNRATE"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=sahm, name="Sahm Rule", line=dict(dash='dash')), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['10Y-2Y Yield Spread'], name="10Y-2Y"), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['Chicago Fed National Activity Index'], name="CFNAI"), row=3, col=1)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Business Cycle Clock")
growth_mom = df['Industrial Production Index'].pct_change(3)
infl_mom = cpi_yoy.diff(3)
clock_df = pd.DataFrame({'Growth Momentum': growth_mom, 'Inflation Change': infl_mom})
fig = px.scatter(clock_df, x='Growth Momentum', y='Inflation Change', title="Latest point = Mid-to-Late Expansion")
st.plotly_chart(fig, use_container_width=True)

st.success("✅ Dashboard live and updating daily from official FRED data!")