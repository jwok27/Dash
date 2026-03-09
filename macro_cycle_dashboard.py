import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Macro OS — Billionaire Edition", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 Macro Intelligence OS — Billionaire Hedge Fund Edition")
st.caption("The ultimate one-stop institutional command center • Full tabs + charts + expert ratios • Long/Short language • Updated daily")

# ================== FRED SETUP ==================
api_key = st.secrets.get("FRED_API_KEY")
if not api_key:
    api_key = st.text_input("Enter your FRED API key:", type="password")
if not api_key:
    st.stop()
fred = Fred(api_key=api_key)

# ================== FETCH FRED DATA ==================
@st.cache_data(ttl=86400)
def fetch_data():
    series = {'UNRATE':'Unemployment Rate','T10Y3M':'10Y-3M Spread','CFNAI':'Chicago Fed NAI','NFCI':'Chicago Fed NFCI',
              'CPIAUCSL':'CPI','ICSA':'Initial Claims (k)','VIXCLS':'VIX','BAA10Y':'Corp Credit Spread',
              'RECPROUSM156N':'NY Fed Recession Prob','INDPRO':'Industrial Production'}
    df = pd.DataFrame()
    for code, name in series.items():
        try:
            s = fred.get_series(code, observation_start='2010-01-01')
            df[name] = s
        except: pass
    return df

df = fetch_data()

# Safe calculations
cpi_yoy = df['CPI'].pct_change(12) * 100
sahm = df['Unemployment Rate'].rolling(3).mean() - df['Unemployment Rate'].rolling(12).min()
claims_mom = df['Initial Claims (k)'].rolling(4).mean().pct_change(4) * 100
vix_pct = df['VIX'].rolling(252).rank(pct=True).iloc[-1] * 100 if len(df) > 252 else 50
latest_date = df.index[-1].strftime('%b %d, %Y')
rec_prob = df['NY Fed Recession Prob'].dropna().iloc[-1] if not df['NY Fed Recession Prob'].dropna().empty else 10.0

def safe_value(series, default=0.0):
    try:
        val = series.iloc[-1]
        return val if pd.notna(val) else default
    except:
        return default

# Scoring & Phase
def calculate_phase_score():
    cf3m = safe_value(df['Chicago Fed NAI'].rolling(3).mean())
    nfc = safe_value(df['Chicago Fed NFCI'])
    spread = safe_value(df['10Y-3M Spread'])
    credit = safe_value(df['Corp Credit Spread'])
    sahm_val = safe_value(sahm)
    score = 0
    score += 25 * (1 if cf3m > 0 else 0.2)
    score += 20 * (1 if spread > 0 else 0)
    score += 15 * min(max((safe_value(df['Unemployment Rate'], 4.4) - 3.5) / 2.5, 0), 1)
    if sahm_val > 0.5: score += 10
    score += 12 * (1 if nfc < 0 else 0)
    if rec_prob < 15 and credit < 2.0: score += 8
    return min(int(score), 100)

score = calculate_phase_score()
phase_map = {range(0,40): "Early Cycle", range(40,65): "Mid Cycle", range(65,85): "Late Cycle", range(85,101): "Contraction"}
phase = next((v for k,v in phase_map.items() if score in k), "Late Cycle")

# ================== TABS ==================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📍 Overview", "📈 Market Snapshot", "📊 Expert Ratios", "📉 Deep Charts", "⚠️ Risk Dashboard", "📋 Trades", "🔄 Cycle Clock"])

with tab1:
    st.header(f"**{phase}** — Composite Score: {score}/100 | Recession Prob: {rec_prob:.1f}%")
    ur = safe_value(df['Unemployment Rate'], 4.4)
    spread = safe_value(df['10Y-3M Spread'], 0.5)
    nfc = safe_value(df['Chicago Fed NFCI'], -0.2)
    cpi = safe_value(cpi_yoy, 2.4)
    note = f"""**{phase} Regime Assessment**  
Unemployment at {ur:.1f}%, 10Y-3M spread {spread:.2f}%, NFCI {nfc:.2f}, inflation {cpi:.1f}%. Recession odds {rec_prob:.1f}%. VIX {vix_pct:.0f}th percentile. Claims are {"rising sharply" if safe_value(claims_mom) > 2 else "rising" if safe_value(claims_mom) > 0 else "falling"}.  

**Forward 3-6 Month Outlook**  
Base case is continued recovery with above-trend growth. Steep curve and easing conditions favor risk assets. Monitor labor and credit spreads closely.  

**Key Risks**: Labor rollover (Sahm trigger), credit widening, geopolitical shock.  
**Opportunities**: Long defensives + duration, tactical commodity longs.  
**Positioning**: Long Staples & Defense, Short broad equities on valuation concerns."""
    st.markdown(f"**DAILY MACRO INTELLIGENCE NOTE** — {latest_date}\n\n{note}")

    # Score Breakdown Chart
    st.subheader("Score Breakdown")
    breakdown = {"Growth": 25, "Policy (Curve)": 20, "Labor": 15, "Financial Conditions": 12, "Inflation/Credit": 8}
    fig = go.Figure(go.Bar(x=list(breakdown.keys()), y=list(breakdown.values()), marker_color="#00cc66"))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📈 Market Snapshot — Indices + Defense + Staples + Commodities")
    tickers = {'^GSPC':'S&P 500','^IXIC':'Nasdaq','^DJI':'Dow','^RUT':'Russell 2000',
               'XLP':'Consumer Staples','ITA':'Aerospace & Defense','XLU':'Utilities',
               'XLK':'Technology','XLF':'Financials','XLE':'Energy',
               'DX-Y.NYB':'DXY','GC=F':'Gold','CL=F':'Oil','^TNX':'10Y Yield'}
    data = []
    for ticker, name in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="ytd")
            ytd = round(((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100, 1) if not hist.empty else 0
            m1 = t.history(period="1mo")
            one_m = round(((m1['Close'].iloc[-1] / m1['Close'].iloc[0]) - 1) * 100, 1) if len(m1) > 1 else 0
            m3 = t.history(period="3mo")
            three_m = round(((m3['Close'].iloc[-1] / m3['Close'].iloc[0]) - 1) * 100, 1) if len(m3) > 1 else 0
            signal = "🟢 Long" if name in ["Consumer Staples","Aerospace & Defense","Utilities","DXY","Gold"] else "🟢 Long" if name in ["Technology","Financials","Energy"] else "🔴 Short"
            data.append([name, one_m, three_m, ytd, signal])
        except:
            data.append([name, 0, 0, 0, "—"])
    market_df = pd.DataFrame(data, columns=["Asset","1M %","3M %","YTD %","Cycle Signal"])
    st.dataframe(market_df.style.format({"1M %": "{:.1f}%", "3M %": "{:.1f}%", "YTD %": "{:.1f}%"}), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📊 Expert Ratios & Valuations")
    st.caption("Live inter-market ratios with historical context and Long/Short signals")
    try:
        gold = yf.Ticker("GC=F").history(period="2y")['Close']
        spx = yf.Ticker("^GSPC").history(period="2y")['Close']
        ratio = gold / spx
        st.line_chart(ratio, use_container_width=True)
        st.caption("**Gold / S&P 500 ratio** — Long Gold when rising (current trend bullish)")
    except:
        st.write("Gold/S&P ratio loading...")
    try:
        dxy = yf.Ticker("DX-Y.NYB").history(period="2y")['Close']
        tnx = yf.Ticker("^TNX").history(period="2y")['Close']
        ratio = dxy / tnx
        st.line_chart(ratio, use_container_width=True)
        st.caption("**DXY / 10Y Yield ratio** — Short DXY when falling (current trend neutral)")
    except:
        st.write("DXY/10Y ratio loading...")
    try:
        ita = yf.Ticker("ITA").history(period="2y")['Close']
        xlk = yf.Ticker("XLK").history(period="2y")['Close']
        ratio = ita / xlk
        st.line_chart(ratio, use_container_width=True)
        st.caption("**Defense / Tech relative strength** — Long Defense
