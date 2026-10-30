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

# Hapa tumetumia link za uhakika kwa nembo maarufu, na clearbit kwa nyingine
COMPANY_DATA = {
    "CRDB": {"name": "CRDB Bank Plc", "logo": "https://upload.wikimedia.org/wikipedia/en/thumb/8/8a/CRDB_Bank_logo.svg/200px-CRDB_Bank_logo.svg.png"},
    "NMB": {"name": "NMB Bank Plc", "logo": "https://upload.wikimedia.org/wikipedia/en/thumb/4/44/NMB_Bank_logo.svg/200px-NMB_Bank_logo.svg.png"},
    "VODA": {"name": "Vodacom Tanzania", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Vodacom_Logo.svg/200px-Vodacom_Logo.svg.png"},
    "TBL": {"name": "Tanzania Breweries", "logo": "https://upload.wikimedia.org/wikipedia/en/thumb/1/1c/Tanzania_Breweries_Limited_logo.png/200px-Tanzania_Breweries_Limited_logo.png"},
    "KCB": {"name": "KCB Bank (Kenya)", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/KCB_Bank_Logo.svg/200px-KCB_Bank_Logo.svg.png"},
    "TPCC": {"name": "Tanzania Portland Cement", "logo": "https://twigacement.com/wp-content/uploads/2019/06/Twiga-Cement-Logo.png"},
    "TOL": {"name": "TOL Gases Ltd", "logo": "https://logo.clearbit.com/tol.co.tz"},
    "TCC": {"name": "Tanzania Cigarette Co", "logo": "https://logo.clearbit.com/tcc.co.tz"},
    "DCB": {"name": "DCB Commercial Bank", "logo": "https://logo.clearbit.com/dcbbank.co.tz"},
    "SWIS": {"name": "Swissport Tanzania", "logo": "https://logo.clearbit.com/swissport.com"},
    "NICO": {"name": "National Investment Co", "logo": "https://logo.clearbit.com/nico.co.tz"},
}

def get_logo_html(sym, logo_url, size=50):
    """Kama nembo haipo, tengeneza 'Avatar' yenye herufi"""
    if logo_url:
        return f'<img src="{logo_url}" style="width:{size}px; height:{size}px; object-fit:contain; margin-right:15px; border-radius:8px;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';"> <div style="display:none; width:{size}px; height:{size}px; background-color:#2962ff; color:white; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'
    else:
        return f'<div style="width:{size}px; height:{size}px; background-color:#2962ff; color:white; display:flex; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'

st.markdown(f'''
    <style>
    .stApp {{ background-color: {BG}; color: {TXT}; }}
    .css-1d391kg {{ background-color: #1e222d; }}
    .stRadio label {{ color: {TXT} !important; }}
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

# ================= SIDEBAR: WATCHLIST =================
st.sidebar.title("📈 BXStockView")
st.sidebar.markdown("---")

symbols = df_master['symbol'].unique().tolist()

sym_options = []
for s in sorted(symbols):
    if s in COMPANY_DATA:
        name = COMPANY_DATA[s]["name"]
        logo = COMPANY_DATA[s].get("logo", f"https://logo.clearbit.com/{name.replace(' ', '').lower()}.com")
    else:
        name = s 
        logo = None # Itatengeneza Avatar
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

logo_html_sidebar = get_logo_html(selected_sym, selected_logo, size=40)

st.sidebar.markdown(f"""
<div style="display:flex; align-items:center; background-color:#151a21; padding:10px; border-radius:8px; margin-top:10px; border:1px solid #2a323d;">
    {logo_html_sidebar}
    <div>
        <div style="color:white; font-weight:bold; font-size:16px;">{selected_sym}</div>
        <div style="color:#8b949e; font-size:12px;">{selected_name}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ================= MAIN PAGE =================
logo_html_main = get_logo_html(selected_sym, selected_logo, size=50)

st.markdown(f"""
<div style="display:flex; align-items:center; margin-bottom: 20px;">
    {logo_html_main}
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
