import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import timedelta
from sklearn.ensemble import RandomForestRegressor

# ================= MIPANGILIO =================
st.set_page_config(page_title="BXStockView", layout="wide", initial_sidebar_state="expanded")

UP, DOWN = "#26a69a", "#ef5350"
UP_A, DOWN_A = "rgba(38,166,154,0.5)", "rgba(239,83,80,0.5)"
BG, GRID, TXT = "#131722", "#1e222d", "#d1d4dc"
LINE_COLOR = "#2962ff"
FORECAST_COLOR = "#ffb700" # Rangi ya Utabiri

COMPANY_DATA = {
    "CRDB": {"name": "CRDB Bank Plc", "domain": "crdbbank.co.tz"},
    "NMB": {"name": "NMB Bank Plc", "domain": "nmbbank.co.tz"},
    "VODA": {"name": "Vodacom Tanzania", "domain": "vodacom.co.tz"},
    "TBL": {"name": "Tanzania Breweries", "domain": "tbl.co.tz"},
    "KCB": {"name": "KCB Bank (Kenya)", "domain": "kcbgroup.com"},
    "TPCC": {"name": "Tanzania Portland Cement (Twiga)", "domain": "twigacement.com"},
    "TOL": {"name": "TOL Gases Ltd", "domain": "tol.co.tz"},
    "TCC": {"name": "Tanzania Cigarette Co", "domain": "tcc.co.tz"},
    "DCB": {"name": "DCB Commercial Bank", "domain": "dcbbank.co.tz"},
    "SWIS": {"name": "Swissport Tanzania", "domain": "swissport.com"},
    "NICO": {"name": "National Investment Co", "domain": "nico.co.tz"},
    "TPLC": {"name": "Tanga Cement Plc", "domain": "tangacement.co.tz"},
}

SYMBOL_ALIASES = {"TCCL": "TPCC", "TWIGA": "TPCC", "TCPLC": "TPLC", "SWISS": "SWIS"}
VALID_DSE_SYMBOLS = ["DSE", "CRDB", "DCB", "EABL", "JHL", "KA", "KCB", "MBP", "NICO", "NMB", "NMG", "PAL", "SWIS", "TBL", "TPLC", "TOL", "TTP", "SWALA", "USL", "MKCB", "MCB", "YETU", "MUCOBA", "VODA", "AFRIPRISE", "JATU", "TCC", "TPCC", "VERTEX-ETF", "ITRUST-ETF", "IEACLC-ETF", "ZAN-ETF", "ZAN TANZANIA ETF"]

def get_logo_html(sym, domain, size=50):
    if domain:
        logo_url = f"https://img.logo.dev/{domain}?token=pk_2Z7XecBchSB7U8OxYamQIBoDH4F_7huod8eqNPzz6W5hgu1Uz"
        return f'<img src="{logo_url}" style="width:{size}px; height:{size}px; object-fit:contain; margin-right:15px; border-radius:8px;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';"> <div style="display:none; width:{size}px; height:{size}px; background-color:#2962ff; color:white; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'
    else:
        return f'<div style="width:{size}px; height:{size}px; background-color:#2962ff; color:white; display:flex; align-items:center; justify-content:center; font-size:{int(size/2)}px; font-weight:bold; border-radius:8px; margin-right:15px;">{sym[:3]}</div>'

st.markdown(f'''
    <style>
    .stApp {{ background-color: {BG}; color: {TXT}; }}
    .css-1d391kg {{ background-color: #1e222d; }}
    .stRadio label {{ color: {TXT} !important; }}
    .macro-card {{ background-color: #151a21; border: 1px solid #2a323d; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); height: 100%; }}
    .macro-title {{ font-size: 13px; color: #8b949e; margin-bottom: 5px; font-weight: bold; text-transform: uppercase; }}
    .macro-value {{ font-size: 24px; color: #00f2fe; font-weight: bold; font-family: 'Roboto Mono', monospace; margin-bottom: 5px; }}
    .macro-desc {{ font-size: 11px; color: #a0aec0; }}
    </style>
''', unsafe_allow_html=True)

def load_data():
    try:
        with open("data.json", "r") as f: data = json.load(f)
        all_rows = []
        for stock in data:
            raw_sym = stock['symbol'].strip().upper()
            sym = SYMBOL_ALIASES.get(raw_sym, raw_sym)
            if sym not in VALID_DSE_SYMBOLS: continue
            chart_data = stock.get('chart_data', [])
            for day in chart_data:
                all_rows.append({
                    'symbol': sym, 'date': pd.to_datetime(day['time']), 'open': day.get('open', 0),
                    'high': day.get('high', 0), 'low': day.get('low', 0), 'close': day.get('close', 0),
                    'volume': day.get('volume', 0), 'rsi_14': day.get('rsi_14', 50.0),
                    'change': stock.get('change', 0.0), 'pct': stock.get('pct', 0.0)
                })
        df = pd.DataFrame(all_rows)
        if df.empty: return df
        return df.sort_values(['symbol', 'date'])
    except: return pd.DataFrame()

MACRO_INFO = {
    "CBR (Benki Kuu)": {"val": "6.25%", "desc": "Riba ya Benki Kuu (Q4 2026)"},
    "Inflation (Mfumuko)": {"val": "4.30%", "desc": "Mfumuko wa bei (Sept 2026)"},
    "GDP Growth (Uchumi)": {"val": "6.50%", "desc": "Ukuaji wa Uchumi (Q2 2026)"},
    "TZS / USD": {"val": "2,628.24", "desc": "Kiwango cha Fedha (Nov 2026)"},
    "Riba ya Bond": {"val": "8.75%", "desc": "Riba ya Dhama za Serikali"},
    "7-Day Interbank": {"val": "N/A", "desc": "Riba ya Mikopo ya Benki"}
}

df_master = load_data()

if df_master.empty:
    st.error("Data haipo. Tafadhali hakikisha 'data.json' ipo GitHub.")
    st.stop()

def analyze_stock(sdf):
    if len(sdf) < 5: return 0, ["Hakuna data ya kutosha."], []
    last = sdf.iloc[-1]
    rsi, close, vol_today = last['rsi_14'], last['close'], last['volume']
    vol_avg = sdf['volume'].tail(20).mean()
    score = 50; reasons, warnings = [], []

    if rsi < 30: score += 20; reasons.append("✅ RSI iko chini ya 30 (Oversold).")
    elif rsi > 70: score -= 20; warnings.append("⚠️ RSI iko juu ya 70 (Overbought).")
    else: reasons.append("✅ RSI iko katika eneo la kati (Neutral).")

    if vol_today > (vol_avg * 1.5): score += 15; reasons.append("✅ Volume imeongezeka sana leo.")
    elif vol_today == 0: score -= 30; warnings.append("🚨 Hakuna biashara leo (Volume = 0).")

    if len(sdf) > 50:
        sma50 = sdf['close'].tail(50).mean()
        if close > sma50: score += 15; reasons.append("✅ Bei iko juu ya wastani wa siku 50.")
        else: score -= 15; warnings.append("⚠️ Bei iko chini ya wastani wa siku 50.")

    return max(0, min(100, score)), reasons, warnings

# ================= SIDEBAR =================
st.sidebar.title("📈 BXStockView")
st.sidebar.markdown("---")
page = st.sidebar.radio("**Menyu:**", ["📊 Chart Analysis", "🔎 Market Screener", "📰 Market Pulse"])

if page == "📊 Chart Analysis":
    symbols = df_master['symbol'].unique().tolist()
    sym_options = [{"symbol": s, "name": COMPANY_DATA.get(s, {}).get("name", s)} for s in sorted(symbols)]
    selected_idx = st.sidebar.selectbox("Chagua Hisa:", range(len(sym_options)), format_func=lambda x: f"{sym_options[x]['symbol']} - {sym_options[x]['name']}")
    
    selected_sym = sym_options[selected_idx]['symbol']
    selected_name = sym_options[selected_idx]['name']
    domain = COMPANY_DATA.get(selected_sym, {}).get("domain", "")
    logo_html_main = get_logo_html(selected_sym, domain, size=50)

    st.markdown(f'<div style="display:flex; align-items:center; margin-bottom: 10px;">{logo_html_main}<div><h2 style="margin:0; color:white;">{selected_sym}</h2><span style="color:#8b949e; font-size:16px;">{selected_name}</span></div></div>', unsafe_allow_html=True)

    stock_data = df_master[df_master['symbol'] == selected_sym].sort_values('date')
    ai_score, reasons, warnings = analyze_stock(stock_data)
    score_color = "#00e676" if ai_score >= 70 else "#ffb700" if ai_score >= 40 else "#ff5252"
    
    reasons_html = "".join([f'<div style="margin-bottom: 4px;">• {r}</div>' for r in reasons])
    warnings_html = "".join([f'<div style="margin-bottom: 4px; color:#ff9800;">• {w}</div>' for w in warnings])
    ai_panel_html = f'<div style="background-color:#151a21; padding:15px; border-radius:8px; border-left: 5px solid {score_color}; margin-bottom: 20px;"><h4 style="margin:0; color:white;">BX AI Score: <span style="color:{score_color};">{ai_score}/100</span></h4><div style="color:#e1e6ed; font-size:14px; margin-top:10px;">{reasons_html}{warnings_html}</div></div>'
    st.markdown(ai_panel_html, unsafe_allow_html=True)

    # =====================================================================
    # KIKOKOTOO CHA FAIDA & UTABIRI (Data Science)
    # =====================================================================
    st.markdown("---")
    st.markdown("### 💰 Kikokotoo cha Faida & Utabiri (Predictive Analytics)")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        investment = st.number_input("Weka Kiasi Unachotaka Kuwekeza (TZS):", min_value=10000, value=1000000, step=100000)
    with col_c2:
        period = st.selectbox("Muda wa Uwekezaji (Nyuma):", ["Miaka 2", "Mwaka 1", "Miezi 6", "Miezi 3"])

    current_date = stock_data['date'].max()
    current_price = stock_data['close'].iloc[-1]

    if period == "Miaka 2": past_date = current_date - timedelta(days=730)
    elif period == "Mwaka 1": past_date = current_date - timedelta(days=365)
    elif period == "Miezi 6": past_date = current_date - timedelta(days=180)
    else: past_date = current_date - timedelta(days=90)

    past_data = stock_data[stock_data['date'] <= past_date]
    
    if past_data.empty:
        st.warning(f"Hakuna data ya kutosha kwa kipindi cha {period}. Tunatumia bei ya kwanza iliyopo.")
        past_price = stock_data['close'].iloc[0]
        actual_past_date = stock_data['date'].iloc[0]
    else:
        past_price = past_data['close'].iloc[-1]
        actual_past_date = past_data['date'].iloc[-1]

    cost_rate = 0.035
    shares_bought = investment / past_price
    cost_buying = investment * cost_rate
    total_investment = investment + cost_buying
    value_now = shares_bought * current_price
    cost_selling = value_now * cost_rate
    net_value = value_now - cost_selling
    div_yield_est = 0.05
    div_earned = investment * div_yield_est * (1 - 0.05)
    total_profit = (net_value + div_earned) - total_investment
    profit_pct = (total_profit / total_investment) * 100

    st.info(f"Ukinunua hisa hii kwa bei ya **TZS {past_price:,.2f}** tarehe **{actual_past_date.strftime('%d %b %Y')}**:")
    st.write(f"- Umewekeza: **TZS {total_investment:,.2f}** (ikiwa na gharama za 3.5%)")
    st.write(f"- Thamani ya hisa sasa (tarehe {current_date.strftime('%d %b %Y')}): **TZS {net_value:,.2f}**")
    st.write(f"- Gawio ulilopata (baada ya kodi 5%): **TZS {div_earned:,.2f}**")
    
    if total_profit > 0: st.success(f"Faida Kamili ya Nyuma: **TZS {total_profit:,.2f} (+{profit_pct:.2f}%)**")
    else: st.error(f"Hasara Kamili ya Nyuma: **TZS {total_profit:,.2f} ({profit_pct:.2f}%)**")

    # =========================================================
    # UTABIRI (FORECAST) KWA KUTUMIA RANDOM FOREST - MUDA MPANA
    # =========================================================
    st.markdown("#### 🔮 Utabiri wa Data Science (Random Forest Model)")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        forecast_horizon = st.selectbox("Chagua Muda wa Utabiri (Forecast):", ["Miezi 3", "Miezi 6", "Mwaka 1"])
    with col_f2:
        st.info("Model inatabiri mwenendo wa bei kwa kutumia data ya miaka ya nyuma.")

    # 1. Feature Engineering
    ml_data = stock_data.copy()
    # Tunatengeneza target ya baadaye (Miezi 3 = siku 90, n.k.)
    if forecast_horizon == "Miezi 3": days_ahead = 90
    elif forecast_horizon == "Miezi 6": days_ahead = 180
    else: days_ahead = 365

    ml_data['Day'] = ml_data['date'].dt.dayofweek
    ml_data['Month'] = ml_data['date'].dt.month
    ml_data['SMA_5'] = ml_data['close'].rolling(window=5).mean()
    ml_data['SMA_20'] = ml_data['close'].rolling(window=20).mean()
    ml_data['Return_1d'] = ml_data['close'].pct_change(1)
    ml_data['Return_5d'] = ml_data['close'].pct_change(5)
    
    # Target: Mabadiliko ya asilimia (%) baada ya siku hizo
    ml_data['Future_Close'] = ml_data['close'].shift(-days_ahead)
    ml_data['Target_Pct'] = (ml_data['Future_Close'] - ml_data['close']) / ml_data['close'] * 100
    
    ml_data = ml_data.dropna()
    
    if len(ml_data) > 30: # Tunahitaji data ya kutosha kufunza
        features = ['close', 'volume', 'rsi_14', 'SMA_5', 'SMA_20', 'Return_1d', 'Return_5d', 'Day', 'Month']
        X = ml_data[features]
        y = ml_data['Target_Pct']
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # 3. Kufanya Utabiri wa Muda Ujao
        last_row = stock_data.iloc[-1:].copy()
        last_row['Day'] = last_row['date'].dt.dayofweek
        last_row['Month'] = last_row['date'].dt.month
        last_row['SMA_5'] = stock_data['close'].tail(5).mean()
        last_row['SMA_20'] = stock_data['close'].tail(20).mean()
        last_row['Return_1d'] = stock_data['close'].pct_change(1).iloc[-1]
        last_row['Return_5d'] = stock_data['close'].pct_change(5).iloc[-1]
        
        X_future = last_row[features]
        predicted_pct_change = model.predict(X_future)[0]
        
        # Bei ya Baadaye = Bei ya Sasa + (Bei ya Sasa * Mabadiliko ya Asilimia)
        predicted_price = current_price * (1 + (predicted_pct_change / 100))
        
        predicted_value_now = shares_bought * predicted_price
        predicted_cost_selling = predicted_value_now * cost_rate
        predicted_net_value = predicted_value_now - predicted_cost_selling
        predicted_profit = (predicted_net_value + div_earned) - total_investment
        predicted_pct_profit = (predicted_profit / total_investment) * 100

        # Onyesho la matokeo ya Utabiri
        st.write(f"Utabiri wa **{forecast_horizon}** ujao kwa kutumia **Random Forest**:")
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric(label=f"Bei Inayotarajiwa ({forecast_horizon})", value=f"TZS {predicted_price:,.2f}", delta=f"{predicted_pct_change:+.2f}%")
        with col_r2:
            st.metric(label=f"Thamani ya Uwekezaji", value=f"TZS {predicted_net_value:,.2f}")
        with col_r3:
            if predicted_profit > 0:
                st.metric(label="Faida Inayotarajiwa", value=f"TZS {predicted_profit:,.2f}", delta=f"+{predicted_pct_profit:.2f}%")
            else:
                st.metric(label="Hasara Inayotarajiwa", value=f"TZS {predicted_profit:,.2f}", delta=f"{predicted_pct_profit:.2f}%")
        
        st.caption(f"Utabiri huu unatumia mwenendo wa siku {len(ml_data)} za nyuma. Soko la hisa linaweza kubadilika ghafla.")
    else:
        st.info("Hakuna data ya kutosha (zaidi ya siku 30) ili kufanya utabiri (Forecast).")
    # =====================================================================

    col1, col2, col3 = st.columns(3)
    with col1: timeframe = st.selectbox("**Timeframe:**", ["Daily", "Weekly", "Monthly"])
    with col2: chart_type = st.selectbox("**Chart Type:**", ["Candlestick", "Line", "Area"])
    with col3: history_range = st.selectbox("**History:**", ["Zote", "Mwaka 1", "Miezi 6"])

    d = stock_data.copy()
    if history_range == "Mwaka 1": d = d.tail(252)
    elif history_range == "Miezi 6": d = d.tail(126)

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
    if chart_type == "Candlestick": fig.add_trace(go.Candlestick(x=r["lab"], open=r["open"], high=r["high"], low=r["low"], close=r["close"], increasing_line_color=UP, decreasing_line_color=DOWN), row=1, col=1)
    elif chart_type == "Line": fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", line=dict(color=LINE_COLOR, width=2)), row=1, col=1)
    else: fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", fill="tozeroy", line=dict(color=LINE_COLOR, width=2)), row=1, col=1)

    # =========================================================
    # HAPA: Kuweka Mstari wa Utabiri Kwenye Chart
    # =========================================================
    # Kama utabiri ulifanyika, tunachora mstari wa dotted wa bei ya baadaye
    if len(ml_data) > 30:
        # Tunachora mstari kutoka bei ya leo hadi bei inayotarajiwa
        fig.add_trace(go.Scatter(
            x=[r["lab"].iloc[-1], f"Forecast ({forecast_horizon})"], 
            y=[current_price, predicted_price], 
            mode="lines+markers", 
            line=dict(color=FORECAST_COLOR, width=2, dash='dot'),
            marker=dict(size=8, color=FORECAST_COLOR),
            name="Utabiri"
        ), row=1, col=1)
    # =========================================================

    fig.add_trace(go.Bar(x=r["lab"], y=r["volume"], marker_color=np.where(r["close"] >= r["open"], UP_A, DOWN_A), name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=r["lab"], y=r["rsi_14"], mode="lines", line=dict(color="#e040fb", width=2), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", row=3, col=1)

    fig.update_xaxes(type="category", rangeslider_visible=False, gridcolor=GRID)
    fig.update_yaxes(side="right", gridcolor=GRID)
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TXT), height=800, margin=dict(l=10, r=70, t=30, b=30))
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})

elif page == "🔎 Market Screener":
    # ... (Screener code)
    st.markdown("<h2 style='color:white;'>Market Screener</h2>", unsafe_allow_html=True)
    # ... (iliyobaki inabaki kama ilivyo)

elif page == "📰 Market Pulse":
    # ... (Market pulse code)
    st.markdown("<h2 style='color:white;'>Market Pulse & Reports</h2>", unsafe_allow_html=True)
    # ... (iliyobaki inabaki kama ilivyo)
