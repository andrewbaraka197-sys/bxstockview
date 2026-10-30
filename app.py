import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# ================= MIPANGILIO =================
st.set_page_config(page_title="BXStockView", layout="wide", initial_sidebar_state="expanded")

UP, DOWN = "#26a69a", "#ef5350"
UP_A, DOWN_A = "rgba(38,166,154,0.5)", "rgba(239,83,80,0.5)"
BG, GRID, TXT = "#131722", "#1e222d", "#d1d4dc"
LINE_COLOR = "#2962ff"
SMA_COLORS = ["#2962ff", "#ff9800", "#e040fb"]

st.markdown(f'''
    <style>
    .stApp {{ background-color: {BG}; color: {TXT}; }}
    .css-1d391kg {{ background-color: #1e222d; }}
    .stSelectbox label, .stRadio label {{ color: {TXT} !important; }}
    .stButton>button {{ background-color: #2a2e39; color: {TXT}; border: 1px solid #363a45; }}
    .stButton>button:hover {{ background-color: #363a45; color: white; }}
    </style>
''', unsafe_allow_html=True)

@st.cache_data(ttl=60) 
def load_data():
    try:
        with open("data.json", "r") as f:
            data = json.load(f)
            
        all_rows = []
        for stock in data:
            sym = stock['symbol']
            for day in stock['chart_data']:
                all_rows.append({
                    'symbol': sym, 'date': pd.to_datetime(day['time']),
                    'open': day['open'], 'high': day['high'], 'low': day['low'],
                    'close': day['close'], 'volume': day.get('volume', 0),
                    'rsi_14': day.get('rsi_14', 50.0) 
                })
        df = pd.DataFrame(all_rows)
        df = df.sort_values(['symbol', 'date'])
        return df
    except Exception as e:
        return pd.DataFrame()

df_master = load_data()

if df_master.empty:
    st.error("Data haipo au ina hitilafu. Tafadhali hakikisha 'data.json' ipo GitHub na Pipeline imefanya kazi.")
    st.stop()

def resample(d, kind):
    if kind == "D": return d.copy().reset_index(drop=True)
    if kind == "W": key = d["date"].dt.to_period("W")
    elif kind == "M": key = d["date"].dt.to_period("M")
    elif kind == "3M": key = d["date"].dt.to_period("Q")
    elif kind == "6M": key = d["date"].dt.year.astype(str) + "-H" + np.where(d["date"].dt.quarter <= 2, "1", "2")
    else: key = d["date"].dt.year

    g = d.groupby(key)
    out = pd.DataFrame({
        "date": g["date"].max(), "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(), "volume": g["volume"].sum(),
        "rsi_14": g["rsi_14"].last()
    })
    return out.reset_index(drop=True).sort_values("date").reset_index(drop=True)

# ================= SIDEBAR: WATCHLIST =================
st.sidebar.title("📈 BXStockView")
st.sidebar.markdown("---")

symbols = df_master['symbol'].unique().tolist()
selected_sym = st.sidebar.radio("**Watchlist (Chagua Hisa):**", sorted(symbols))

# ================= MAIN PAGE: CONTROLS =================
st.title(f"📊 {selected_sym}")

# Nimeongeza chaguo la muda wa historia
col1, col2, col3 = st.columns(3)
with col1:
    timeframe = st.selectbox("**Timeframe:**", ["Daily", "Weekly", "Monthly", "3 Months", "6 Months", "1 Year"])
with col2:
    chart_type = st.selectbox("**Chart Type:**", ["Candlestick", "Line", "Area"])
with col3:
    history_range = st.selectbox("**History (Data za Nyuma):**", ["Zote (Tangu 2015)", "Mwaka 1 wa Mwisho", "Miezi 6 ya Mwisho"])

# ================= FILTER DATA =================
tf_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "3 Months": "3M", "6 Months": "6M", "1 Year": "1Y"}
d = df_master[df_master["symbol"] == selected_sym].sort_values("date")

# Filter kulingana na History Range
if history_range == "Mwaka 1 wa Mwisho":
    d = d.tail(252) # Siku 252 za biashara = mwaka 1
elif history_range == "Miezi 6 ya Mwisho":
    d = d.tail(126)

r = resample(d, tf_map[timeframe])
r["lab"] = r["date"].dt.strftime("%d %b %y")

# ================= TENGENEZA CHART =================
fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
    row_heights=[0.6, 0.15, 0.25] 
)

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(x=r["lab"], open=r["open"], high=r["high"], low=r["low"], close=r["close"],
                                 increasing_line_color=UP, decreasing_line_color=DOWN,
                                 increasing_fillcolor=UP, decreasing_fillcolor=DOWN, whiskerwidth=0), row=1, col=1)
elif chart_type == "Line":
    fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", line=dict(color=LINE_COLOR, width=2)), row=1, col=1)
elif chart_type == "Area":
    fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", fill="tozeroy",
                             line=dict(color=LINE_COLOR, width=2), fillcolor="rgba(41, 98, 255, 0.2)"), row=1, col=1)

fig.add_trace(go.Bar(x=r["lab"], y=r["volume"], marker_color=np.where(r["close"] >= r["open"], UP_A, DOWN_A), name="Volume"), row=2, col=1)

fig.add_trace(go.Scatter(x=r["lab"], y=r["rsi_14"], mode="lines", line=dict(color="#e040fb", width=2), name="RSI"), row=3, col=1)
fig.add_trace(go.Scatter(x=[r["lab"].iloc[0], r["lab"].iloc[-1]], y=[70, 70], mode="lines", line=dict(color="rgba(255, 255, 255, 0.3)", width=1, dash="dash"), showlegend=False), row=3, col=1)
fig.add_trace(go.Scatter(x=[r["lab"].iloc[0], r["lab"].iloc[-1]], y=[30, 30], mode="lines", line=dict(color="rgba(255, 255, 255, 0.3)", width=1, dash="dash"), showlegend=False), row=3, col=1)
fig.add_trace(go.Scatter(x=[r["lab"].iloc[0], r["lab"].iloc[-1]], y=[50, 50], mode="lines", line=dict(color="rgba(255, 255, 255, 0.1)", width=1), showlegend=False), row=3, col=1)

fig.update_xaxes(type="category", categoryorder="array", categoryarray=list(r["lab"]), rangeslider_visible=False, gridcolor=GRID, zerolinecolor=GRID)
fig.update_yaxes(side="right", tickformat=",.0f", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(side="right", tickformat=".2s", gridcolor=GRID, row=2, col=1)
fig.update_yaxes(side="right", range=[0, 100], tickvals=[30, 50, 70], gridcolor=GRID, row=3, col=1)

fig.update_layout(
    paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TXT), height=900,
    dragmode="pan", hovermode="x unified", showlegend=False,
    margin=dict(l=10, r=70, t=30, b=30)
)

st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})
