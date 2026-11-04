import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import timedelta
from supabase import create_client, Client

# ================= MIPANGILIO YA UI =================
# HAPA NDIO TUNAWEKA LOGO KWENYE TAB YA BROWSER
st.set_page_config(
    page_title="BXStockView", 
    page_icon="bxlogo.svg", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

UP, DOWN = "#00e676", "#ff5252"
UP_A, DOWN_A = "rgba(0, 230, 118, 0.5)", "rgba(255, 82, 82, 0.5)"
BG = "#0e1117"
CARD_BG = "#1e222d"
TXT = "#fafafa"
ACCENT = "#00f2fe"

st.markdown(f'''
    <style>
    .stApp {{ background-color: {BG}; color: {TXT}; }}
    .css-1d391kg {{ background-color: {CARD_BG}; }}
    .main-header {{
        background: linear-gradient(90deg, #1e222d 0%, #2962ff 100%);
        padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .main-header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: 900; }}
    .main-header p {{ color: #a0aec0; margin: 0; font-size: 14px; }}
    .macro-card {{
        background-color: {CARD_BG}; border: 1px solid #2a323d; border-left: 5px solid {ACCENT};
        border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .macro-title {{ font-size: 12px; color: #8b949e; margin-bottom: 5px; font-weight: bold; text-transform: uppercase; }}
    .macro-value {{ font-size: 22px; color: white; font-weight: bold; font-family: 'Roboto Mono', monospace; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px; white-space: pre-wrap; background-color: {CARD_BG};
        border-radius: 5px 5px 0px 0px; padding-top: 10px; padding-bottom: 10px; color: {TXT};
    }}
    .stTabs [aria-selected="true"] {{ background-color: {ACCENT}; color: black; font-weight: bold; }}
    </style>
''', unsafe_allow_html=True)

# ================= SUPABASE CONNECTION =================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Kosa la kuunganisha na Supabase: {e}.")
        return None

supabase = init_supabase()

# ================= LOAD DATA =================
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
    "CBR (Benki Kuu)": {"val": "6.25%", "desc": "Riba ya Benki Kuu"},
    "Inflation (Mfumuko)": {"val": "4.30%", "desc": "Mfumuko wa Bei"},
    "GDP Growth (Uchumi)": {"val": "6.50%", "desc": "Ukuaji wa Uchumi"},
    "TZS / USD": {"val": "2,628", "desc": "Kiwango cha Fedha"},
    "Riba ya Bond": {"val": "8.75%", "desc": "Riba ya Dhama za Serikali"},
    "Interbank Rate": {"val": "N/A", "desc": "Riba ya Mikopo ya Benki"}
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
with st.sidebar:
    # HAPA NDIO TUNAWEKA LOGO KWENYE SIDEBAR
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Badilisha "bxlogo.svg" kama jina la faili lako ni tofauti
        st.image("bxlogo.svg", use_container_width=True) 
    
    st.markdown("<p style='text-align: center; font-size: 12px; color: #8b949e; margin-top: 5px;'>DSE Analytics Platform</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    user_email = st.text_input("📧 Ingia kwa Email Yako:", placeholder="mfano@gmail.com")
    if user_email:
        st.success(f"Umeingia kama: {user_email}")
    else:
        st.warning("Tafadhali ingia kwa email ili kuhifadhi Portfolio yako.")
    
    st.markdown("---")
    page = st.radio("**Menyu:**", ["📊 Uchambuzi wa Hisa", "💼 Portfolio Yangu", "🔎 Kichujio (Screener)", "🌍 Habari za Soko"])

# ================= KURASA =================
if page == "📊 Uchambuzi wa Hisa":
    st.markdown('''<div class="main-header"><h1>📊 Uchambuzi wa Hisa (Chart Analysis)</h1><p>Angalia mwenendo wa bei, viashiria (RSI), na pata ushauri wa AI.</p></div>''', unsafe_allow_html=True)

    symbols = df_master['symbol'].unique().tolist()
    sym_options = [{"symbol": s, "name": COMPANY_DATA.get(s, {}).get("name", s)} for s in sorted(symbols)]
    selected_idx = st.selectbox("Chagua Hisa Unayotaka Kuichambua:", range(len(sym_options)), format_func=lambda x: f"{sym_options[x]['symbol']} - {sym_options[x]['name']}")
    
    selected_sym = sym_options[selected_idx]['symbol']
    selected_name = sym_options[selected_idx]['name']
    domain = COMPANY_DATA.get(selected_sym, {}).get("domain", "")
    
    logo_html = get_logo_html(selected_sym, domain, size=60)
    st.markdown(f'''<div style="background-color: {CARD_BG}; padding: 20px; border-radius: 10px; display: flex; align-items: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">{logo_html}<div><h2 style="margin: 0; color: white;">{selected_sym}</h2><span style="color: #8b949e; font-size: 16px;">{selected_name}</span></div></div>''', unsafe_allow_html=True)

    stock_data = df_master[df_master['symbol'] == selected_sym].sort_values('date')
    ai_score, reasons, warnings = analyze_stock(stock_data)
    score_color = UP if ai_score >= 70 else "#ffb700" if ai_score >= 40 else DOWN
    
    reasons_html = "".join([f'<div style="margin-bottom: 4px;">• {r}</div>' for r in reasons])
    warnings_html = "".join([f'<div style="margin-bottom: 4px; color:#ff9800;">• {w}</div>' for w in warnings])
    st.markdown(f'''<div style="background-color: {CARD_BG}; padding: 15px; border-radius: 8px; border-left: 5px solid {score_color}; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);"><h4 style="margin: 0; color: white;">BX AI Score: <span style="color: {score_color};">{ai_score}/100</span></h4><div style="color: #e1e6ed; font-size: 14px; margin-top: 10px;">{reasons_html}{warnings_html}</div></div>''', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📈 Chart ya Bei", "💰 Kikokotoo & Utabiri"])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1: timeframe = st.selectbox("**Timeframe:**", ["Daily", "Weekly", "Monthly"])
        with col2: chart_type = st.selectbox("**Aina ya Chart:**", ["Candlestick", "Line", "Area"])
        with col3: history_range = st.selectbox("**Historia:**", ["Zote", "Mwaka 1", "Miezi 6"])

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
        elif chart_type == "Line": fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", line=dict(color=ACCENT, width=2)), row=1, col=1)
        else: fig.add_trace(go.Scatter(x=r["lab"], y=r["close"], mode="lines", fill="tozeroy", line=dict(color=ACCENT, width=2)), row=1, col=1)

        fig.add_trace(go.Bar(x=r["lab"], y=r["volume"], marker_color=np.where(r["close"] >= r["open"], UP_A, DOWN_A), name="Volume"), row=2, col=1)
        fig.add_trace(go.Scatter(x=r["lab"], y=r["rsi_14"], mode="lines", line=dict(color="#e040fb", width=2), name="RSI"), row=3, col=1)
        
        fig.update_xaxes(type="category", rangeslider_visible=False, gridcolor="#2a323d")
        fig.update_yaxes(side="right", gridcolor="#2a323d")
        fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TXT), height=600, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})

    with tab2:
        st.markdown("### 💰 Kikokotoo cha Faida & Utabiri (Data Science)")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1: investment = st.number_input("Weka Kiasi Unachotaka Kuwekeza (TZS):", min_value=10000, value=1000000, step=100000)
        with col_c2: period = st.selectbox("Muda wa Uwekezaji (Nyuma):", ["Miaka 2", "Mwaka 1", "Miezi 6", "Miezi 3"])

        current_date = stock_data['date'].max()
        current_price = stock_data['close'].iloc[-1]

        if period == "Miaka 2": past_date = current_date - timedelta(days=730)
        elif period == "Mwaka 1": past_date = current_date - timedelta(days=365)
        elif period == "Miezi 6": past_date = current_date - timedelta(days=180)
        else: past_date = current_date - timedelta(days=90)

        past_data = stock_data[stock_data['date'] <= past_date]
        if past_data.empty: past_price = stock_data['close'].iloc[0]; actual_past_date = stock_data['date'].iloc[0]
        else: past_price = past_data['close'].iloc[-1]; actual_past_date = past_data['date'].iloc[-1]

        cost_rate = 0.035; shares_bought = investment / past_price; cost_buying = investment * cost_rate; total_investment = investment + cost_buying
        value_now = shares_bought * current_price; cost_selling = value_now * cost_rate; net_value = value_now - cost_selling
        div_yield_est = 0.05; div_earned = investment * div_yield_est * (1 - 0.05); total_profit = (net_value + div_earned) - total_investment; profit_pct = (total_profit / total_investment) * 100

        st.info(f"Ukinunua hisa hii kwa bei ya **TZS {past_price:,.2f}** tarehe **{actual_past_date.strftime('%d %b %Y')}**:")
        st.write(f"- Umewekeza: **TZS {total_investment:,.2f}** (ikiwa na gharama za 3.5%)")
        st.write(f"- Thamani ya hisa sasa (tarehe {current_date.strftime('%d %b %Y')}): **TZS {net_value:,.2f}**")
        if total_profit > 0: st.success(f"Faida Kamili ya Nyuma: **TZS {total_profit:,.2f} (+{profit_pct:.2f}%)**")
        else: st.error(f"Hasara Kamili ya Nyuma: **TZS {total_profit:,.2f} ({profit_pct:.2f}%)**")

        st.markdown("---")
        st.markdown("#### 🔮 Utabiri wa Miaka 1 hadi 10 (Monte Carlo Simulation)")
        st.warning("""
        **Tahadhari:** Utabiri huu unatumia uwezekano (Probabilities) na mwenendo wa nyuma. 
        Ni **makadirio ya kihesabu (Data Science)** na **sio ushauri wa kifedha**. 
        """)
        
        forecast_years = st.slider("Chagua Muda wa Uwekezaji (Miaka):", min_value=1, max_value=10, value=5)
        
        three_years_ago = current_date - timedelta(days=1095)
        recent_data = stock_data[stock_data['date'] >= three_years_ago].copy()
        
        if len(recent_data) > 30:
            recent_data['Daily_Return'] = recent_data['close'].pct_change()
            recent_data = recent_data.dropna()
            mean_return = recent_data['Daily_Return'].mean()
            std_dev = recent_data['Daily_Return'].std()
            
            simulations = 1000
            days_to_forecast = forecast_years * 252
            final_values = []
            
            max_daily_return = 0.003
            min_daily_return = -0.003
            
            for _ in range(simulations):
                price_path = [current_price]
                for _ in range(days_to_forecast):
                    daily_ret = np.random.normal(mean_return, std_dev)
                    daily_ret = max(min(daily_ret, max_daily_return), min_daily_return)
                    price_path.append(price_path[-1] * (1 + daily_ret))
                
                final_price = price_path[-1]
                div_earned_total = investment * ((1.05 ** forecast_years) - 1) * (1 - 0.05)
                final_value = (shares_bought * final_price * (1 - cost_rate)) + div_earned_total - total_investment
                final_values.append(final_value)
                
            final_values = np.array(final_values)
            expected_profit = np.mean(final_values)
            worst_case = np.percentile(final_values, 10)
            best_case = np.percentile(final_values, 90)
            
            st.write(f"Kulingana na simulation za soko ({simulations} scenarios kwa miaka {forecast_years}):")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1: st.metric(label="Wastani wa Faida", value=f"TZS {expected_profit:,.2f}")
            with col_r2: st.metric(label="Hali Mbaya (10%)", value=f"TZS {worst_case:,.2f}")
            with col_r3: st.metric(label="Hali Nzuri (10%)", value=f"TZS {best_case:,.2f}")

elif page == "💼 Portfolio Yangu":
    st.markdown('''<div class="main-header"><h1>💼 Portfolio Yangu (My Portfolio)</h1><p>Fuatilia hisa ulizonunua na uone faida/hasara yako.</p></div>''', unsafe_allow_html=True)

    if not user_email:
        st.warning("Tafadhali weka Email yako kwenye Sidebar (kushoto) ili kuona Portfolio yako.")
    else:
        with st.expander("➕ Ongeza Hisa Mpya Kwenye Portfolio"):
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1: new_sym = st.selectbox("Chagua Hisa:", sorted(df_master['symbol'].unique().tolist()))
            with col_p2: new_shares = st.number_input("Idadi ya Hisa:", min_value=1, value=100)
            with col_p3: new_price = st.number_input("Bei ya Kununua (TZS):", min_value=1.0, value=1000.0)
            
            if st.button("Hifadhi kwenye Portfolio"):
                try:
                    supabase.table('user_portfolios').insert({
                        "user_email": user_email,
                        "symbol": new_sym,
                        "shares_owned": new_shares,
                        "buy_price": new_price
                    }).execute()
                    st.success(f"Hisa ya {new_sym} imeongezwa kwenye portfolio yako!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kosa: {e}")

        try:
            res = supabase.table('user_portfolios').select("*").eq("user_email", user_email).execute()
            portfolio_data = res.data
            
            if not portfolio_data:
                st.info("Bado hujaongeza hisa yoyote kwenye portfolio yako.")
            else:
                df_port = pd.DataFrame(portfolio_data)
                latest_prices = df_master.sort_values('date').groupby('symbol').tail(1)[['symbol', 'close']]
                df_port = df_port.merge(latest_prices, on='symbol', how='left')
                
                df_port['Cost'] = df_port['shares_owned'] * df_port['buy_price']
                df_port['Current_Value'] = df_port['shares_owned'] * df_port['close']
                df_port['Profit'] = df_port['Current_Value'] - df_port['Cost']
                df_port['Profit_%'] = (df_port['Profit'] / df_port['Cost']) * 100
                
                total_cost = df_port['Cost'].sum()
                total_value = df_port['Current_Value'].sum()
                total_profit = df_port['Profit'].sum()
                total_pct = (total_profit / total_cost) * 100 if total_cost > 0 else 0

                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1: st.metric("Jumla ya Gharama", f"TZS {total_cost:,.2f}")
                with col_m2: st.metric("Thamani ya Sasa", f"TZS {total_value:,.2f}")
                with col_m3: 
                    if total_profit > 0: st.metric("Faida/Hasara", f"TZS {total_profit:,.2f}", f"+{total_pct:.2f}%")
                    else: st.metric("Faida/Hasara", f"TZS {total_profit:,.2f}", f"{total_pct:.2f}%", delta_color="inverse")

                display_port = df_port[['symbol', 'shares_owned', 'buy_price', 'close', 'Current_Value', 'Profit_%']]
                display_port.columns = ['Hisa', 'Idadi', 'Bei ya Kununua', 'Bei ya Sasa', 'Thamani ya Sasa', 'Faida (%)']
                
                st.dataframe(display_port.style.format({
                    'Bei ya Kununua': '{:,.2f}', 'Bei ya Sasa': '{:,.2f}',
                    'Thamani ya Sasa': '{:,.2f}', 'Faida (%)': '{:+.2f}%'
                }).background_gradient(subset=['Faida (%)'], cmap='RdYlGn'), use_container_width=True)

                st.markdown("### 🗑️ Futa Hisa kwenye Portfolio")
                delete_id = st.selectbox("Chagua ID ya Hisa ya Kufuta:", df_port['id'].tolist())
                if st.button("Futa Hisa hii"):
                    supabase.table('user_portfolios').delete().eq('id', delete_id).execute()
                    st.success("Hisa imefutwa!")
                    st.rerun()

        except Exception as e:
            st.error(f"Kosa la kusoma Portfolio: {e}")

elif page == "🔎 Kichujio (Screener)":
    st.markdown('''<div class="main-header"><h1>🔎 Kichujio cha Hisa (Screener)</h1><p>Chuja hisa zote za DSE kulingana na AI Score, RSI, na Fedha.</p></div>''', unsafe_allow_html=True)

    latest_data = []
    for sym in df_master['symbol'].unique():
        sdf = df_master[df_master['symbol'] == sym].sort_values('date')
        if len(sdf) > 0:
            score, _, _ = analyze_stock(sdf)
            sdf_with_vol = sdf[sdf['volume'] > 0]
            last_trade_date = sdf_with_vol['date'].max() if not sdf_with_vol.empty else sdf['date'].max()
            last = sdf.iloc[-1]
            latest_data.append({'symbol': sym, 'close': last['close'], 'change': last['change'], 'pct': last['pct'], 'rsi_14': last['rsi_14'], 'volume': last['volume'], 'date': last_trade_date, 'ai_score': score})
    
    latest_df = pd.DataFrame(latest_data)
    last_market_date = df_master['date'].max()
    latest_df['days_since_trade'] = (last_market_date - latest_df['date']).dt.days

    col1, col2, col3 = st.columns(3)
    with col1: 
        min_score = st.slider("**Kiwango cha Chini cha AI Score:**", 0, 100, 50)
        rsi_filter = st.selectbox("**RSI Signal:**", ["Zote", "Oversold (<30)", "Overbought (>70)"])
    with col2: min_turnover = st.number_input("**Kiasi cha Chini cha Fedha (TZS):**", min_value=0, value=5000000, step=1000000)
    with col3: liquidity_filter = st.selectbox("**Uwezo wa Kufanya Biashara:**", ["Zote", "Zinazofanya biashara (Siku 5 zilizopita)"])

    filtered = latest_df.copy()
    filtered = filtered[filtered['ai_score'] >= min_score]
    if rsi_filter == "Oversold (<30)": filtered = filtered[filtered['rsi_14'] < 30]
    elif rsi_filter == "Overbought (>70)": filtered = filtered[filtered['rsi_14'] > 70]
    filtered['turnover'] = filtered['volume'] * filtered['close']
    filtered = filtered[filtered['turnover'] >= min_turnover]
    if liquidity_filter == "Zinazofanya biashara (Siku 5 zilizopita)": filtered = filtered[filtered['days_since_trade'] <= 5]

    display_df = filtered.reindex(columns=['symbol', 'ai_score', 'close', 'change', 'pct', 'rsi_14', 'turnover', 'days_since_trade']).fillna(0)
    display_df.columns = ['Hisa', 'AI Score', 'Bei', 'Mabadiliko (TZS)', 'Mabadiliko (%)', 'RSI', 'Fedha (TZS)', 'Siku Tangu Biashara']
    display_df = display_df.sort_values('AI Score', ascending=False)

    st.dataframe(display_df.style.format({'AI Score': '{:.0f}', 'Bei': '{:,.2f}', 'Mabadiliko (TZS)': '{:,.2f}', 'Mabadiliko (%)': '{:+.2f}%', 'RSI': '{:.1f}', 'Fedha (TZS)': '{:,.0f}'}).background_gradient(subset=['AI Score', 'Mabadiliko (%)'], cmap='RdYlGn'), use_container_width=True, height=600)

elif page == "🌍 Habari za Soko":
    st.markdown('''<div class="main-header"><h1>🌍 Habari za Soko (Market Pulse)</h1><p>Takwimu halisi za Uchumi (BOT) na Ripoti za Makampuni.</p></div>''', unsafe_allow_html=True)

    st.markdown("<h4 style='color:white; margin-bottom: 15px;'>Viashiria vya Uchumi (BOT)</h4>", unsafe_allow_html=True)
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m4, col_m5, col_m6 = st.columns(3)
    
    keys = list(MACRO_INFO.keys())
    vals = list(MACRO_INFO.values())

    with col_m1: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[0]}</div><div class="macro-value">{vals[0]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[0]["desc"]}</div></div>', unsafe_allow_html=True)
    with col_m2: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[1]}</div><div class="macro-value">{vals[1]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[1]["desc"]}</div></div>', unsafe_allow_html=True)
    with col_m3: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[2]}</div><div class="macro-value">{vals[2]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[2]["desc"]}</div></div>', unsafe_allow_html=True)
    with col_m4: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[3]}</div><div class="macro-value">{vals[3]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[3]["desc"]}</div></div>', unsafe_allow_html=True)
    with col_m5: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[4]}</div><div class="macro-value">{vals[4]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[4]["desc"]}</div></div>', unsafe_allow_html=True)
    with col_m6: st.markdown(f'<div class="macro-card"><div class="macro-title">{keys[5]}</div><div class="macro-value">{vals[5]["val"]}</div><div style="font-size:10px; color:#8b949e;">{vals[5]["desc"]}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:white; margin-bottom: 10px;'>Ripoti za Makampuni</h4>", unsafe_allow_html=True)
    st.info("Hapa utaweka viungo (Links) vya ripoti za mwaka (Annual Reports) au taarifa za makampuni.")
    
    reports = {
        "CRDB Annual Report 2023": "https://www.crdbbank.co.tz/investor-relations",
        "NMB Annual Report 2023": "https://www.nmbbank.co.tz/investor-relations",
        "Vodacom Annual Report 2023": "https://www.vodacom.co.tz/about-us/investor-relations"
    }
    for name, link in reports.items():
        st.markdown(f"🔗 [{name}]({link})")
