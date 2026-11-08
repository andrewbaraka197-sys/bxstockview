import os, re, io, time, datetime as dt
from pathlib import Path
from urllib.parse import urljoin
import requests, pdfplumber, pandas as pd
from bs4 import BeautifulSoup

START = dt.date(2026, 10, 1)
END = dt.date.today()
LISTING_URL = os.environ.get(
    "LISTING_URL", "https://dse.co.tz/en/resources/research/investment-insights")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "15"))
OUT = Path("dse_daily.csv")
HDR = {"User-Agent": "Mozilla/5.0"}
COLS = ["date", "symbol", "open", "prev_close", "close", "high", "low",
        "turnover", "deals", "bid", "offer", "volume", "mcap"]
PDF_COLS = ["open", "close", "high", "low", "turnover", "deals",
            "volume", "mcap", "bid", "offer"]
ROW = re.compile(
    r"^\**\s*([A-Z][A-Z0-9&\-]*(?: [A-Z0-9&\-]+){0,3})\s+"
    r"((?:-?[\d,]+(?:\.\d+)?\s+){9}-?[\d,]+(?:\.\d+)?)\s*$")
DETAIL = re.compile(r"/resources/research/investment-insights/[A-Za-z0-9]+/?$")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def find_detail_links(html, base):
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(base, a["href"])
        if "/en/" in full and DETAIL.search(full.split("?")[0]):
            m = DATE_RE.search(a.get_text(" ", strip=True))
            if full not in out or m:
                out[full] = m.group(1) if m else None
    return out


def find_pdf_url(html, base):
    txt = html.replace("\\/", "/").replace("\\u002F", "/").replace("\\u0026", "&")
    pats = [r'https?://[^\s"\'<>\\]+?\.pdf(?:\?[^\s"\'<>\\]*)?',
            r'(?:https?://dse\.co\.tz)?/(?:storage|get/daily/report)/[^\s"\'<>\\]+']
    for p in pats:
        for m in re.finditer(p, txt, re.I):
            u = m.group(0)
            low = u.lower()
            if "data_services" in low or "/extras/" in low or "pricelist" in low:
                continue
            return urljoin(base, u)
    return None


def debug_page(html):
    txt = html.replace("\\/", "/")
    print("  html length:", len(html))
    shown = []
    for m in re.finditer(
            r'"([^"\s]{0,200}(?:pdf|document|attachment|file|storage|report)[^"\s]{0,200})"',
            txt, re.I):
        s = m.group(1)
        if s not in shown:
            shown.append(s)
        if len(shown) >= 25:
            break
    for s in shown:
        print("  candidate:", s[:200])


def parse_pdf(content):
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    rows = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m and m.group(1) != "TOTAL":
            nums = [float(x.replace(",", "")) for x in m.group(2).split()]
            rows.append({"symbol": m.group(1), **dict(zip(PDF_COLS, nums))})
    return rows, text


def main():
    if OUT.exists():
        existing = pd.read_csv(OUT)
    else:
        existing = pd.DataFrame(columns=COLS)
    have = set(existing["date"].astype(str))

    pages = {}
    for page in range(1, MAX_PAGES + 1):
        r = requests.get(LISTING_URL, params={"page": page}, headers=HDR, timeout=60)
        found = find_detail_links(r.text, r.url)
        new = {k: v for k, v in found.items() if k not in pages}
        print("listing page", page, "status", r.status_code,
              "reports:", len(found), "new:", len(new))
        if not new:
            break
        pages.update(new)
    print("report pages found:", len(pages))

    all_rows = []
    for url, ldate in pages.items():
        try:
            if ldate and (ldate in have or
                          not (START <= dt.date.fromisoformat(ldate) <= END)):
                continue
            r = requests.get(url, headers=HDR, timeout=60)
            m = re.search(r"Daily Market Report\s+(\d{4}-\d{2}-\d{2})", r.text)
            iso = m.group(1) if m else ldate
            if not iso:
                print("no date for", url)
                continue
            d = dt.date.fromisoformat(iso)
            if iso in have or not (START <= d <= END):
                continue
            pdf_url = find_pdf_url(r.text, r.url)
            if not pdf_url:
                print("NO PDF LINK on", url)
                debug_page(r.text)
                continue
            pr = requests.get(pdf_url, headers=HDR, timeout=90)
            if not pr.content.startswith(b"%PDF"):
                print("not a PDF:", pdf_url[:100], pr.headers.get("content-type"))
                continue
            rows, text = parse_pdf(pr.content)
            if not rows:
                print("no rows for", iso)
                print("\n".join(text.splitlines()[:30]))
                continue
            if len(rows) < 25:
                print("WARNING", iso, "only", len(rows), "rows")
            for row in rows:
                row["date"] = iso
            all_rows += rows
            print(iso, len(rows), "rows")
        except Exception as e:
            print("fail", url, e)
        time.sleep(1)

    if not all_rows:
        print("nothing new to add")
        return

    new = pd.DataFrame(all_rows)
    new["_new"] = True
    old = existing.copy()
    old["_new"] = False
    df = pd.concat([old, new], ignore_index=True)
    df["date"] = df["date"].astype(str)
    df["_new"] = df["_new"].astype(bool)
    df = df.drop_duplicates(["date", "symbol"], keep="first")
    for c in COLS[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values(["symbol", "date"])
    prev = df.groupby("symbol")["close"].shift(1)
    df.loc[df["_new"], "prev_close"] = prev[df["_new"]].fillna(0.0)
    df = df.sort_values(["date", "symbol"])[COLS]
    df.to_csv(OUT, index=False)
    print("total rows:", len(df), "| last date:", df["date"].max())


if __name__ == "__main__":
    main()
