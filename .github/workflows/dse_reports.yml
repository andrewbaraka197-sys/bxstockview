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
COLS = ["open", "close", "high", "low", "turnover", "deals", "volume",
        "market_cap_bn", "bids", "offers"]
ROW = re.compile(
    r"^\**\s*([A-Z][A-Z0-9&\-]{1,14})\s+((?:-?[\d,]+(?:\.\d+)?\s+){9}-?[\d,]+(?:\.\d+)?)\s*$")
DETAIL = re.compile(r"/resources/research/investment-insights/[A-Za-z0-9]+/?$")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}


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
    seen_s = []
    for m in re.finditer(r'"([^"\s]{0,200}(?:pdf|document|attachment|file|storage|report)[^"\s]{0,200})"', txt, re.I):
        s = m.group(1)
        if s not in seen_s:
            seen_s.append(s)
        if len(seen_s) >= 25:
            break
    for s in seen_s:
        print("  candidate:", s[:200])


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
            rows.append({"section": section, "ticker": m.group(1),
                         **dict(zip(COLS, nums))})
    return parse_date(text), rows, text


def main():
    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    pages, new_seen, all_rows = {}, set(), []

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

    for url, ldate in pages.items():
        if url in seen:
            continue
        try:
            r = requests.get(url, headers=HDR, timeout=60)
            m = re.search(r"Daily Market Report\s+(\d{4}-\d{2}-\d{2})", r.text)
            iso = m.group(1) if m else ldate
            d = dt.date.fromisoformat(iso) if iso else None
            if d and not (START <= d <= END):
                print(d, "outside range, skipped")
                new_seen.add(url)
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
            pdf_date, rows, text = parse_pdf(pr.content)
            d = d or pdf_date
            if d is None or not rows:
                print("no rows/date for", url)
                print("\n".join(text.splitlines()[:30]))
                continue
            for row in rows:
                row["date"] = d.isoformat()
            new_seen.add(url)
            if START <= d <= END:
                all_rows += rows
                print(d, len(rows), "rows")
        except Exception as e:
            print("fail", url, e)
        time.sleep(1)

    OUT.parent.mkdir(exist_ok=True)
    new = pd.DataFrame(all_rows)
    if OUT.exists():
        new = pd.concat([pd.read_csv(OUT), new], ignore_index=True)
    if not new.empty:
        new = (new.dropna(subset=["date", "ticker"])
                  .drop_duplicates(["date", "section", "ticker"], keep="last")
                  .sort_values(["date", "section", "ticker"]))
        new = new[["date", "section", "ticker"] + COLS]
        new.to_csv(OUT, index=False)
        print("total rows:", len(new))
    SEEN.write_text("\n".join(sorted(seen | new_seen)))


if __name__ == "__main__":
    main()
