import os, re, io, time, datetime as dt
from pathlib import Path
from urllib.parse import urljoin
import requests, pdfplumber, pandas as pd
from bs4 import BeautifulSoup

START = dt.date(2026, 10, 1)
END = dt.date.today()
LISTING_URL = os.environ["LISTING_URL"]
MAX_PAGES = int(os.environ.get("MAX_PAGES", "15"))
OUT = Path("data/dse_daily.csv")
SEEN = Path("data/seen_links.txt")
HDR = {"User-Agent": "Mozilla/5.0"}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}
COLS = ["open", "close", "high", "low", "turnover", "deals", "volume",
        "market_cap_bn", "bids", "offers"]
ROW = re.compile(
    r"^\**\s*([A-Z][A-Z0-9&\-]{1,14})\s+((?:-?[\d,]+(?:\.\d+)?\s+){9}-?[\d,]+(?:\.\d+)?)\s*$")


def find_links(html, base):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "/get/daily/report/" in h or "/storage/market_reports/" in h:
            out.append(urljoin(base, h))
    return out


def parse_date(text):
    m = re.search(r"DATE:\s*(\d{1,2})-([A-Za-z]+)-(\d{4})", text)
    if not m:
        return None
    mo = MONTHS.get(m.group(2).lower())
    if not mo:
        return None
    return dt.date(int(m.group(3)), mo, int(m.group(1)))


def parse_pdf(content):
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    d = parse_date(text)
    if not d:
        return None, []
    rows, section = [], "EQUITY"
    for line in text.splitlines():
        u = line.upper()
        if "ETF DAILY PRICES" in u:
            section = "ETF"
        elif "EQUITY DAILY PRICES" in u:
            section = "EQUITY"
        m = ROW.match(line.strip())
        if m and m.group(1) != "TOTAL":
            nums = [float(x.replace(",", "")) for x in m.group(2).split()]
            rows.append({"date": d.isoformat(), "section": section,
                         "ticker": m.group(1), **dict(zip(COLS, nums))})
    return d, rows


def main():
    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    links, new_seen, all_rows = [], set(), []

    for page in range(1, MAX_PAGES + 1):
        r = requests.get(LISTING_URL, params={"page": page}, headers=HDR, timeout=60)
        print("listing page", page, "status", r.status_code, "length", len(r.text))
        found = [l for l in find_links(r.text, r.url) if l not in links]
        if not found:
            break
        links += found
    print("links found:", len(links))

    for url in links:
        if url in seen:
            continue
        try:
            r = requests.get(url, headers=HDR, timeout=90)
            d, rows = parse_pdf(r.content)
        except Exception as e:
            print("fail", url[:70], e)
            continue
        if d is None:
            print("no date found, skipped", url[:70])
            continue
        new_seen.add(url)
        if START <= d <= END:
            all_rows += rows
            print(d, len(rows), "rows")
        time.sleep(1)

    OUT.parent.mkdir(exist_ok=True)
    new = pd.DataFrame(all_rows)
    if OUT.exists():
        new = pd.concat([pd.read_csv(OUT), new], ignore_index=True)
    if not new.empty:
        new = (new.dropna(subset=["date", "ticker"])
                  .drop_duplicates(["date", "section", "ticker"], keep="last")
                  .sort_values(["date", "section", "ticker"]))
        new.to_csv(OUT, index=False)
        print("total rows:", len(new))
    SEEN.write_text("\n".join(sorted(seen | new_seen)))


if __name__ == "__main__":
    main()
