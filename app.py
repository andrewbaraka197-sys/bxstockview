import base64
import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from plotly.subplots import make_subplots

# ================= MIPANGILIO =================
st.set_page_config(page_title="BXStockView", layout="wide", initial_sidebar_state="expanded")

UP, DOWN = "#26a69a", "#ef5350"
UP_A, DOWN_A = "rgba(38,166,154,0.5)", "rgba(239,83,80,0.5)"
BG, GRID, TXT = "#131722", "#1e222d", "#d1d4dc"
LINE_COLOR = "#2962ff"
LOGO_TOKEN = "pk_2Z7XecBchSB7U8OxYamQIBoDH4F_7huod8eqNPzz6W5hgu1Uz"

# Kamusi ya Majina na Nembo za Makampuni (domain = tovuti ya kampuni; nembo inachukuliwa kutoka logo.dev)
# Hisa isiyo na domain hapa inapata nembo ya herufi 3 za alama yake. Ongeza domain ili kupata nembo halisi.
COMPANY_DATA = {
    "CRDB": {"name": "CRDB Bank Plc", "domain": "crdbbank.co.tz"},
    "NMB": {"name": "NMB Bank Plc", "domain": "nmbbank.co.tz"},
    "VODA": {"name": "Vodacom Tanzania", "domain": "vodacom.co.tz"},
    "TBL": {"name": "Tanzania Breweries", "domain": "tbl.co.tz"},
    "KCB": {"name": "KCB Bank (Kenya)", "domain": "kcbgroup.com"},
    "TPCC": {"name": "Tanzania Portland Cement", "domain": "twigacement.com"},
    "TOL": {"name": "TOL Gases Ltd", "domain": "tol.co.tz"},
    "TCC": {"name": "Tanzania Cigarette Co", "domain": "tcc.co.tz"},
    "DCB": {"name": "DCB Commercial Bank", "domain": "dcbbank.co.tz"},
    "SWIS": {"name": "Swissport Tanzania", "domain": "swissport.com"},
    "NICO": {"name": "National Investment Co", "domain": "nico.co.tz"},
    "EABL": {"name": "East African Breweries", "domain": "eabl.com"},
    "NMG": {"name": "Nation Media Group", "domain": "nationmedia.com"},
    "KA": {"name": "Kenya Airways", "domain": "kenya-airways.com"},
    "DSE": {"name": "Dar es Salaam Stock Exchange", "domain": "dse.co.tz"},
}


def get_logo_html(sym, domain, size=50):
    if domain:
        logo_url = f"https://img.logo.dev/{domain}?token={LOGO_TOKEN}"
        return f'<img src="{logo_url}" style="width:{size}px; height:{size}px; object-fit:contain; margin-right:15px; border-radius:8px;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';"> <div style="display:none; width:{size}px; height:{size}px; background-color:#2962ff; color:white; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'
    else:
        return f'<div style="width:{size}px; height:{size}px; background-color:#2962ff; color:white; display:flex; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'


@st.cache_data
def badge_uri(sym):
    """Nembo ya herufi 3 (PNG) kwa hisa isiyo na domain; inafaa kwa safu ya picha ya jedwali."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 63, 63), radius=12, fill="#2962ff")
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    txt = sym[:3]
    box = d.textbbox((0, 0), txt, font=font)
    d.text(((64 - (box[2] - box[0])) / 2 - box[0], (64 - (box[3] - box[1])) / 2 - box[1]), txt, fill="white", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_for_table(sym):
    domain = COMPANY_DATA.get(sym, {}).get("domain", "")
    if domain:
        return f"https://img.logo.dev/{domain}?token={LOGO_TOKEN}&size=64&format=png"
    return badge_uri(sym)


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
            
            stock_close = stock.get('close', 0.0)
            stock_change = stock.get('change', 0.0)
            stock_pct = stock.get('pct', 0.0)
            
            chart_data = stock.get('chart_data', [])
            
            if len(chart_data) > 0:
                last_day = chart_data[-1]
                prev_day = chart_data[-2] if len(chart_data) > 1 else last_day
                
                if stock_change == 0.0:
                    stock_change = last_day['close'] - prev_day['close']
                if stock_pct == 0.0 and prev_day['close'] != 0:
                    stock_pct = (stock_change / prev_day['close']) * 100

            for day in chart_data:
                all_rows.append({
                    'symbol': sym, 'date': pd.to_datetime(day['time']),
                    'open': day.get('open', 0), 'high': day.get('high', 0), 'low': day.get('low', 0),
                    'close': day.get('close', 0), 'volume': day.get('volume', 0),
                    'rsi_14': day.get('rsi_14', 50.0),
                    'change': stock_change, 
                    'pct': stock_pct
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

# ================= SIDEBAR =================
st.sidebar.title("📈 BXStockView")
st.sidebar.markdown("---")

page = st.sidebar.radio("**Menyu:**", ["📊 Chart Analysis", "🔎 Market Screener"])

if page == "📊 Chart Analysis":
    # ================= CHART ANALYSIS PAGE =================
    symbols = sorted(df_master['symbol'].unique().tolist())

    # ---------- WATCHLIST YENYE NEMBO ----------
    last_rows = df_master.sort_values('date').groupby('symbol').tail(1).set_index('symbol')
    wl_df = pd.DataFrame({
        "Nembo": [logo_for_table(s) for s in symbols],
        "Hisa": symbols,
        "Bei": [float(last_rows.loc[s, 'close']) for s in symbols],
        "%": [float(last_rows.loc[s, 'pct']) for s in symbols],
    })

    if "sel_sym" not in st.session_state:
        st.session_state["sel_sym"] = "CRDB" if "CRDB" in symbols else symbols[0]

    st.sidebar.markdown("**Watchlist** (bonyeza hisa kuichagua)")
    event = st.sidebar.dataframe(
        wl_df, hide_index=True, use_container_width=True, height=420,
        column_config={
            "Nembo": st.column_config.ImageColumn("", width="small"),
            "Hisa": st.column_config.TextColumn("Hisa", width="small"),
            "Bei": st.column_config.NumberColumn("Bei", format="%.0f"),
            "%": st.column_config.NumberColumn("%", format="%+.2f%%"),
        },
        on_select="rerun", selection_mode="single-row", key="watchlist_table",
    )
    picked = event.selection.rows if event is not None and hasattr(event, "selection") else []
    if picked:
        st.session_state["sel_sym"] = wl_df.iloc[picked[0]]["Hisa"]

    selected_sym = st.session_state["sel_sym"]
    selected_name = COMPANY_DATA.get(selected_sym, {}).get("name", selected_sym)
    domain = COMPANY_DATA.get(selected_sym, {}).get("domain", "")

    logo_html_main = get_logo_html(selected_sym, domain, size=50)

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
    with col1: timeframe = st.selectbox("**Timeframe:**", ["Daily", "Weekly", "Monthly"])
    with col2: chart_type = st.selectbox("**Chart Type:**", ["Candlestick", "Line", "Area"])
    with col3: history_range = st.selectbox("**History:**", ["Zote", "Mwaka 1", "Miezi 6"])

    d = df_master[df_master["symbol"] == selected_sym].sort_values("date")
    # Mwaka 1 / Miezi 6 kwa TAREHE (si kwa idadi ya safu; safu 252 si mwaka mmoja ikiwa data ina mapengo)
    if history_range == "Mwaka 1": d = d[d["date"] >= d["date"].max() - pd.Timedelta(days=365)]
    elif history_range == "Miezi 6": d = d[d["date"] >= d["date"].max() - pd.Timedelta(days=182)]

    # Resample logic
    def resample(d, kind):
        if kind == "Daily": return d.copy().reset_index(drop=True)
        if kind == "Weekly": key = d["date"].dt.to_period("W")
        else: key = d["date"].dt.to_period("M")
        g = d.groupby(key)
        out = pd.DataFrame({"date": g["date"].max(), "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(), "volume": g["volume"].sum(), "rsi_14": g["rsi_14"].last()})
        return out.reset_index(drop=True).sort_values("date").reset_index(drop=True)

    r = resample(d, timeframe)
    r["lab"] = r["date"].dt.strftime("%d %b %y")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.15, 0.25])
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(x=r["lab"], open=r["open"], high=r["high"], low=r["low"], close=r["close"], increasing_line_color=UP, decreasing_line_color=DOWN), row=1, col=1)
    elif chart_type == "Line":
        fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", line=dict(color=LINE_COLOR, width=2)), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", fill="tozeroy", line=dict(color=LINE_COLOR, width=2)), row=1, col=1)

    fig.add_trace(go.Bar(x=r["lab"], y=r["volume"], marker_color=np.where(r["close"] >= r["open"], UP_A, DOWN_A), name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=r["lab"], y=r["rsi_14"], mode="lines", line=dict(color="#e040fb", width=2), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", row=3, col=1)

    fig.update_xaxes(type="category", rangeslider_visible=False, gridcolor=GRID)
    fig.update_yaxes(side="right", gridcolor=GRID)
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TXT), height=800, margin=dict(l=10, r=70, t=30, b=30))
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})

    # ---------- UCHUNGUZI WA DATA (futa sehemu hii baadaye) ----------
    with st.expander("🔍 Uchunguzi wa data (kila hisa ina siku ngapi na kuanzia lini)"):
        cov = df_master.groupby("symbol")["date"].agg(["count", "min", "max"]).reset_index()
        cov.columns = ["Hisa", "Siku", "Kuanzia", "Hadi"]
        cov["Kuanzia"] = cov["Kuanzia"].dt.strftime("%Y-%m-%d")
        cov["Hadi"] = cov["Hadi"].dt.strftime("%Y-%m-%d")
        st.dataframe(cov, hide_index=True, use_container_width=True)

    st.markdown('<div style="color:#8b949e; font-size:12px;">Logos provided by <a href="https://logo.dev" style="color:#8b949e;">Logo.dev</a></div>', unsafe_allow_html=True)

elif page == "🔎 Market Screener":
    # ================= SCREENER PAGE =================
    st.markdown("<h2 style='color:white;'>Market Screener</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e;'>Chuja hisa kulingana na vigezo vya kiufundi (Technical Analysis).</p>", unsafe_allow_html=True)

    latest_data = df_master.sort_values('date').groupby('symbol').tail(1)
    latest_data = latest_data[latest_data['volume'] > 0]

    last_market_date = df_master['date'].max()
    latest_data['days_since_trade'] = (last_market_date - latest_data['date']).dt.days

    col1, col2, col3 = st.columns(3)
    with col1:
        rsi_filter = st.selectbox("**RSI Signal:**", ["Zote", "Oversold (<30)", "Overbought (>70)"])
    with col2:
        min_turnover = st.number_input("**Kiasi cha Chini cha Fedha (TZS):**", min_value=0, value=5000000, step=1000000)
    with col3:
        liquidity_filter = st.selectbox("**Uwezo wa Kufanya Biashara:**", ["Zote", "Zinazofanya biashara (Siku 5 zilizopita)"])

    filtered = latest_data.copy()
    
    if rsi_filter == "Oversold (<30)":
        filtered = filtered[filtered['rsi_14'] < 30]
    elif rsi_filter == "Overbought (>70)":
        filtered = filtered[filtered['rsi_14'] > 70]

    filtered['turnover'] = filtered['volume'] * filtered['close']
    filtered = filtered[filtered['turnover'] >= min_turnover]

    if liquidity_filter == "Zinazofanya biashara (Siku 5 zilizopita)":
        filtered = filtered[filtered['days_since_trade'] <= 5]

    display_df = filtered.reindex(columns=['symbol', 'close', 'change', 'pct', 'rsi_14', 'turnover', 'days_since_trade']).fillna(0)
    display_df.columns = ['Hisa', 'Bei ya Mwisho', 'Mabadiliko (TZS)', 'Mabadiliko (%)', 'RSI (14)', 'Fedha (TZS)', 'Siku Tangu Biashara']
    
    display_df = display_df.sort_values('Fedha (TZS)', ascending=False)

    st.dataframe(display_df.style.format({
        'Bei ya Mwisho': '{:,.2f}',
        'Mabadiliko (TZS)': '{:,.2f}',
        'Mabadiliko (%)': '{:+.2f}%',
        'RSI (14)': '{:.1f}',
        'Fedha (TZS)': '{:,.0f}'
    }).background_gradient(subset=['Mabadiliko (%)'], cmap='RdYlGn'), use_container_width=True, height=600)
