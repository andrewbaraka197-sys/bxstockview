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

# Kamusi ya majina na Nembo za Makampuni (Clearbit)
COMPANY_DATA = {
    "CRDB": {"name": "CRDB Bank Plc", "domain": "crdbbank.co.tz"},
    "NMB": {"name": "NMB Bank Plc", "domain": "nmbbank.co.tz"},
    "TOL": {"name": "TOL Gases Ltd", "domain": "tol.co.tz"},
    "VODA": {"name": "Vodacom Tanzania", "domain": "vodacom.co.tz"},
    "TCC": {"name": "Tanzania Cigarette Co", "domain": "tcc.co.tz"},
    "TBL": {"name": "Tanzania Breweries", "domain": "tbl.co.tz"},
    "KCB": {"name": "KCB Bank (Kenya)", "domain": "kcbgroup.com"},
    "DCB": {"name": "DCB Commercial Bank", "domain": "dcbbank.co.tz"},
    "TPCC": {"name": "Tanzania Portland Cement", "domain": "twigacement.com"},
    "SWIS": {"name": "Swissport Tanzania", "domain": "swissport.com"},
    "NICO": {"name": "National Investment Co", "domain": "nico.co.tz"},
}

st.markdown(f'''
    <style>
    .stApp {{ background-color: {BG}; color: {TXT}; }}
    .css-1d391kg {{ background-color: #1e222d; }}
    .stRadio label {{ color: {TXT} !important; }}
    
    .stock-item {{
        display: flex; align-items: center; padding: 8px; border-radius: 5px; cursor: pointer; margin-bottom: 5px;
    }}
    .stock-item:hover {{ background-color: #2a2e39; }}
    .stock-logo {{ width: 30px; height: 30px; object-fit: contain; margin-right: 10px; border-radius: 4px; }}
    .stock-info {{ display: flex; flex-direction: column; }}
    .stock-symbol {{ font-weight: bold; font-size: 14px; color: white; }}
    .stock-name {{ font-size: 11px; color: #8b949e; }}
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
    st.error("Data haipo au ina hitilafu. Tafadhali hakikisha 'data.json' ipo GitHub.")
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

# ================= SIDEBAR: WATCHLIST NA NEMBO =================
st.sidebar.title("📈 BXStockView")
st.sidebar.markdown("---")

symbols = df_master['symbol'].unique().tolist()

sym_options = []
for s in sorted(symbols):
    if s in COMPANY_DATA:
        name = COMPANY_DATA[s]["name"]
        logo = f"https://logo.clearbit.com/{COMPANY_DATA[s]['domain']}"
    else:
        name = s 
        logo = "https://logo.clearbit.com/placeholder.com"
    sym_options.append({"symbol": s, "name": name, "logo": logo})

st.sidebar.markdown("<h4 style='color:#00f2fe; font-size:16px; margin-bottom:10px;'>WATCHLIST</h4>", unsafe_allow_html=True)

selected_idx = st.sidebar.selectbox(
    "Chagua Hisa:",
    range(len(sym_options)),
    format_func=lambda x: f"{sym_options[x]['symbol']} - {sym_options[x]['name']}"
)

selected_item = sym_options[selected_idx]
selected_sym = selected_item['symbol']
selected_name = selected_item['name']
selected_logo = selected_item['logo']

st.sidebar.markdown(f"""
<div style="display:flex; align-items:center; background-color:#151a21; padding:10px; border-radius:8px; margin-top:10px; border:1px solid #2a323d;">
    <img src="{selected_logo}" style="width:40px; height:40px; object-fit:contain; margin-right:15px; border-radius:5px;">
    <div>
        <div style="color:white; font-weight:bold; font-size:16px;">{selected_sym}</div>
        <div style="color:#8b949e; font-size:12px;">{selected_name}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= MAIN PAGE: CONTROLS =================
st.markdown(f"""
<div style="display:flex; align-items:center; margin-bottom: 20px;">
    <img src="{selected_logo}" style="width:50px; height:50px; object-fit:contain; margin-right:20px; border-radius:8px;">
    <div>
        <h2 style="margin:0; color:white;">{selected_sym}</h2>
        <span style="color:#8b949e; font-size:16px;">{selected_name}</span>
    </div>
</div>
""", unsafe_allow_html=True)

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

if history_range == "Mwaka 1 wa Mwisho":
    d = d.tail(252) 
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