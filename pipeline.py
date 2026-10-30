import pandas as pd
import numpy as np
import json
import requests
from io import StringIO

print("Inaanza mchakato wa kusoma data...")

# Hapa tunavuta data moja kwa moja kutoka kwenye Repo yako ya Pipeline (Dse.pipeline)
# Hii inahakikisha tunapata data zote zilizopo huko
RAW_CSV_URL = "https://raw.githubusercontent.com/andrewbaraka197-sys/Dse.pipeline/main/dse_daily.csv"

try:
    response = requests.get(RAW_CSV_URL)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text), parse_dates=["date"])
    print("Data imepatikana kutoka GitHub!")
except Exception as e:
    print(f"Kosa la kupakua data: {e}")
    # Kama imeshindikana, tumia ile iliyopo kwenye repo hii kama backup
    try:
        df = pd.read_csv("dse_daily.csv", parse_dates=["date"])
    except:
        exit()

# Usafishaji mdogo
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
df = df.dropna(subset=["date", "close"])
df = df.sort_values(["symbol", "date"])

# Hesabu RSI
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['rsi_14'] = df.groupby('symbol')['close'].transform(calculate_rsi)

output_data = []
for sym in df['symbol'].unique():
    # HAKUNA .tail() HAPA - Tunachukua data zote tangu mwanzo
    sdf = df[df['symbol'] == sym].sort_values('date')
    
    chart_data = []
    for _, row in sdf.iterrows():
        chart_data.append({
            "time": row['date'].strftime('%Y-%m-%d'),
            "open": float(row['open']) if pd.notnull(row['open']) else 0.0,
            "high": float(row['high']) if pd.notnull(row['high']) else 0.0,
            "low": float(row['low']) if pd.notnull(row['low']) else 0.0,
            "close": float(row['close']),
            "volume": float(row['volume']) if pd.notnull(row['volume']) else 0.0,
            "rsi_14": float(row['rsi_14']) if pd.notnull(row['rsi_14']) else 50.0
        })
        
    last_row = sdf.iloc[-1]
    prev_row = sdf.iloc[-2] if len(sdf) > 1 else last_row
    change = last_row['close'] - prev_row['close']
    pct = (change / prev_row['close']) * 100 if prev_row['close'] != 0 else 0

    output_data.append({
        "symbol": sym,
        "close": float(last_row['close']),
        "change": float(change),
        "pct": round(float(pct), 2),
        "chart_data": chart_data
    })

with open("data.json", "w") as f:
    json.dump(output_data, f)

print("Mchakato umekamilika! data.json imetengenezwa na data zote za nyuma.")
