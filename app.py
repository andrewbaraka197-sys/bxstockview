import streamlit as st
import json

st.set_page_config(page_title="BXStockView", layout="wide", initial_sidebar_state="collapsed")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 1rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# =====================================================================
# HAPA NDIO PAMErekebishwa: Tunatumia cache_data(ttl=1) 
# =====================================================================
@st.cache_data(ttl=1)
def load_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        return []

dse_data = load_data()

# Kama data haipo, onyesha kosa
if len(dse_data) == 0:
    st.error("⚠️ KOSA: Faili la 'data.json' halipo au ni tupu (empty) kwenye GitHub yako. Tafadhali hakikisha jina ni 'data.json' na lina data ndani yake.")
    st.stop() # Simamisha App isiendelee kama data haipo

json_data_str = json.dumps(dse_data)

html_code = f"""
<!DOCTYPE html>
<html lang="sw">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>

    <style>
        :root {{
            --bg-dark: #0b0e14; --card-bg: #151a21; --border-color: #2a323d;
            --text-main: #e1e6ed; --text-muted: #8b949e;
            --up-color: #00e676; --down-color: #ff5252; --accent-cyan: #00f2fe;
        }}
        body {{ background-color: var(--bg-dark); color: var(--text-main); font-family: 'Inter', sans-serif; }}
        .mono {{ font-family: 'Roboto Mono', monospace; }}
        .card {{ background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; }}
        
        .stock-row {{ cursor: pointer; transition: background-color 0.2s; border-bottom: 1px solid var(--border-color); }}
        .stock-row:hover {{ background-color: #1a212b; }}
        .text-green {{ color: var(--up-color) !important; }}
        .text-red {{ color: var(--down-color) !important; }}
        
        #chart_div {{ width: 100%; height: 350px; position: relative; }}
        #volume_div {{ width: 100%; height: 80px; position: relative; margin-top: -5px; }}
        
        .tf-btn {{ font-size: 12px; font-weight: 600; padding: 4px 8px; border-radius: 4px; cursor: pointer; color: var(--text-muted); border: 1px solid transparent; }}
        .tf-btn.active {{ color: var(--accent-cyan); border-color: var(--accent-cyan); background-color: rgba(0, 242, 254, 0.1); }}
        
        .search-input {{ background-color: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-main); border-radius: 8px; padding: 10px 15px; width: 100%; }}
        .search-input:focus {{ outline: none; border-color: var(--accent-cyan); }}
    </style>
</head>
<body class="p-2 p-md-3">

    <!-- HEADER -->
    <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
        <a class="navbar-brand p-0 m-0" href="#">
            <svg width="180" height="40" viewBox="0 0 400 90" fill="none">
                <g transform="translate(5, 12)">
                    <text x="0" y="62" fill="#00e676" font-family="'Inter', sans-serif" font-size="68" font-weight="900">B</text>
                    <text x="45" y="62" fill="#ff5252" font-family="'Inter', sans-serif" font-size="68" font-weight="900">X</text>
                    <path d="M 115 52 L 160 42 L 210 32 L 270 18 L 330 -2" stroke="rgba(0, 242, 254, 0.25)" stroke-width="2.5" stroke-dasharray="4 4" />
                    <g transform="translate(118, 22)"><rect x="2" y="5" width="14" height="20" rx="3" fill="#0b0e14" stroke="#ff5252"/><text x="5" y="19" fill="#ff5252" font-size="12">S</text></g>
                    <g transform="translate(138, 16)"><rect x="2" y="0" width="14" height="26" rx="3" fill="#00e676"/><text x="5" y="18" fill="#0b0e14" font-size="12">T</text></g>
                    <g transform="translate(158, 20)"><rect x="2" y="4" width="14" height="18" rx="3" fill="#0b0e14" stroke="#ffb700"/><text x="5" y="18" fill="#ffb700" font-size="12">O</text></g>
                    <g transform="translate(178, 14)"><rect x="2" y="2" width="14" height="22" rx="3" fill="#ff5252"/><text x="5" y="18" fill="#0b0e14" font-size="12">C</text></g>
                    <g transform="translate(198, 8)"><rect x="2" y="-4" width="14" height="32" rx="3" fill="#0b0e14" stroke="#00e676"/><text x="5" y="17" fill="#00e676" font-size="12">K</text></g>
                    <g transform="translate(225, 4)"><rect x="2" y="-2" width="14" height="28" rx="3" fill="#00f2fe"/><text x="5" y="17" fill="#0b0e14" font-size="12">V</text></g>
                    <g transform="translate(245, 0)"><rect x="2" y="-4" width="14" height="28" rx="3" fill="#0b0e14" stroke="#ff9100"/><text x="6" y="16" fill="#ff9100" font-size="12">I</text></g>
                    <g transform="translate(265, -4)"><rect x="2" y="-4" width="14" height="26" rx="3" fill="#ff5252"/><text x="5" y="15" fill="#0b0e14" font-size="12">E</text></g>
                    <g transform="translate(285, -12)"><rect x="2" y="-12" width="14" height="42" rx="3" fill="#00e676"/><text x="3" y="15" fill="#0b0e14" font-size="12">W</text></g>
                </g>
            </svg>
        </a>
        <span class="badge bg-outline-info border border-info text-info mono">LIVE DSE</span>
    </div>

    <div id="watchlistSection">
        <div class="mb-3">
            <input type="text" id="searchInput" class="search-input" placeholder="🔍 Tafuta hisa..." onkeyup="filterTable()">
        </div>
        <div class="card p-0 overflow-hidden">
            <div class="p-3 border-bottom border-secondary">
                <h5 class="fw-bold mb-0 text-info mono">DSE Watchlist</h5>
            </div>
            <div class="table-responsive" style="max-height: 450px; overflow-y: auto;">
                <table class="table table-dark table-hover mb-0" id="stockTable">
                    <thead class="mono" style="font-size: 11px; border-bottom: 2px solid var(--border-color);">
                        <tr><th class="ps-3">KAMPUNI</th><th>BEI (TZS)</th><th>MABADILIKO</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <div id="chartSection" class="d-none">
        <div class="d-flex justify-content-between mb-3">
            <button class="btn btn-outline-light btn-sm fw-bold px-3" onclick="showWatchlist()">&larr; Rudi</button>
        </div>
        <div class="d-flex justify-content-between align-items-end flex-wrap gap-2 mb-2">
            <div>
                <h4 id="selectedStockTitle" class="fw-bold mb-0 text-white">--</h4>
                <small class="text-success" id="selectedStockPrice">--</small>
            </div>
            <div class="btn-group">
                <button class="tf-btn active" onclick="changeTimeframe('1D')">1D</button>
                <button class="tf-btn" onclick="changeTimeframe('1W')">1W</button>
            </div>
        </div>
        <div class="card p-2 pb-0">
            <div id="chart_div"></div>
            <div id="volume_div"></div>
        </div>
    </div>

    <script>
        const dseData = {json_data_str}; 
        let chart, candlestickSeries, volumeSeries;
        let currentSymbol = '';

        function renderTable(data) {{
            const tbody = document.querySelector('#stockTable tbody');
            tbody.innerHTML = '';
            data.forEach(stock => {{
                const isUp = stock.change >= 0;
                const colorClass = isUp ? 'text-green' : 'text-red';
                const sign = isUp ? '+' : '';
                const tr = document.createElement('tr');
                tr.className = 'stock-row';
                tr.onclick = () => openChart(stock);
                tr.innerHTML = `
                    <td class="ps-3"><strong class="text-white mono">${{stock.symbol}}</strong></td>
                    <td class="fw-bold mono">${{stock.close.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</td>
                    <td class="${{colorClass}} mono fw-bold">${{sign}}${{stock.change.toFixed(2)}} (${{sign}}${{stock.pct}}%)</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const filtered = dseData.filter(s => s.symbol.toLowerCase().includes(query));
            renderTable(filtered);
        }}

        function openChart(stock) {{
            currentSymbol = stock.symbol;
            document.getElementById('watchlistSection').classList.add('d-none');
            document.getElementById('chartSection').classList.remove('d-none');
            document.getElementById('selectedStockTitle').innerText = stock.symbol;
            
            const priceEl = document.getElementById('selectedStockPrice');
            priceEl.innerText = `TZS ${{stock.close.toLocaleString()}}`;
            priceEl.className = stock.change >= 0 ? 'text-success fw-bold mono' : 'text-danger fw-bold mono';

            createChart(stock.chart_data);
        }}

        function showWatchlist() {{
            document.getElementById('chartSection').classList.add('d-none');
            document.getElementById('watchlistSection').classList.remove('d-none');
        }}

        function changeTimeframe(tf) {{
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            createChart(dseData.find(s => s.symbol === currentSymbol).chart_data);
        }}

        function createChart(data) {{
            const chartContainer = document.getElementById('chart_div');
            const volContainer = document.getElementById('volume_div');
            chartContainer.innerHTML = ''; volContainer.innerHTML = '';

            chart = LightweightCharts.createChart(chartContainer, {{
                width: chartContainer.clientWidth, height: 350,
                layout: {{ backgroundColor: '#151a21', textColor: '#8b949e' }},
                grid: {{ vertLines: {{ color: '#2a323d' }}, horzLines: {{ color: '#2a323d' }} }},
                rightPriceScale: {{ borderColor: '#2a323d' }},
                timeScale: {{ borderColor: '#2a323d', timeVisible: true, secondsVisible: false }},
            }});

            candlestickSeries = chart.addCandlestickSeries({{
                upColor: '#00e676', downColor: '#ff5252', borderVisible: false,
                wickUpColor: '#00e676', wickDownColor: '#ff5252',
            }});

            const volChart = LightweightCharts.createChart(volContainer, {{
                width: volContainer.clientWidth, height: 80,
                layout: {{ backgroundColor: '#151a21', textColor: '#8b949e' }},
                grid: {{ vertLines: {{ visible: false }}, horzLines: {{ visible: false }} }},
                timeScale: {{ visible: false }},
                rightPriceScale: {{ borderColor: '#2a323d' }},
            }});

            volumeSeries = volChart.addHistogramSeries({{ color: '#26a69a', priceFormat: {{ type: 'volume' }} }});

            candlestickSeries.setData(data);
            volumeSeries.setData(data.map(d => ({{ time: d.time, value: d.volume || 50000, color: d.close > d.open ? 'rgba(0, 230, 118, 0.5)' : 'rgba(255, 82, 82, 0.5)' }})));

            chart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => volChart.timeScale().setVisibleLogicalRange(timeRange));
            chart.timeScale().fitContent();
        }}

        window.onload = () => renderTable(dseData);
    </script>
</body>
</html>
"""

st.components.v1.html(html_code, height=850, scrolling=True)
