"""
DSE data - faili moja.
  python dse_all.py daily      -> bei za leo (DSE) + ripoti za TSL
  python dse_all.py backfill   -> data za zamani (Wayback + archive.org yote) + ripoti za TSL
Matokeo: data/dse_daily.csv  na  data/tsl_daily.csv
Install: pip install requests beautifulsoup4 pdfplumber
"""
import csv
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from io import BytesIO

import requests
from bs4 import BeautifulSoup

# =====================================================================
# HAPA NDIO PAMErekebishwa: Tumeongeza Cookie na Browser details kamili
# ili kuvuka kizuizi cha "Cookie Consent" cha tovuti ya DSE
# =====================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "cookieconsent_status=allow; cookies_accepted=true; _ga=GA1.2.123456789.123456789"
}

DSE_URL = "https://dse.co.tz/"
DSE_FILE = "data/dse_daily.csv"
TSL_FILE = "data/tsl_daily.csv"
WAYBACK_DONE = "data/wayback_done.txt"
CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_TARGETS = ["dse.co.tz/", "www.dse.co.tz/", "dse.co.tz/?action=index"]
FROM_YEAR, TO_YEAR = "2015", "2026"
DEADLINE = time.time() + 320 * 60       # simama kabla GitHub haijakata kazi (saa 6)

COLS = ["open", "prev_close", "close", "high", "low", "turnover", "deals", "bid", "offer", "volume", "mcap"]
DSE_FIELDS = ["date", "symbol"] + COLS
FIELD_MAP = {"symbol": "symbol", "open": "open", "prevclose": "prev_close", "close": "close",
             "high": "high", "low": "low", "turnover": "turnover", "deals": "deals",
             "outstandingbid": "bid", "outstandingoffer": "offer", "volume": "volume"}
TSL_FIELDS = ["date", "symbol", "open", "close", "gain_pct", "div_yield_pct", "ytd_pct", "turnover", "prev_turnover"]
TSL_LIST = "https://www.tanzaniasecurities.co.tz/reports/daily?catId=1&page={}"
SYM = r"([A-Z][A-Z0-9\-]{1,12})\*{0,2}"
PRICE_RE = re.compile(rf"^{SYM}\s+([\d,]+)\s+([\d,]+)\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%$")
TURN_RE = re.compile(rf"^{SYM}\s+([\d,]+)\s+([\d,]+)(?:\s+-?[\d.]+%)?$")


# ---------------- zana za pamoja ----------------
def num(s):
    s = re.sub(r"[^\d.\-]", "", (s or "").replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return None


def http_get(url, **kw):
    for i in range(5):
        try:
            # Hapa tunatumia HEADERS zilizoboreshwa
            r = requests.get(url, headers=HEADERS, timeout=90, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(10 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            time.sleep(5 * (i + 1))
    return None


def load_csv(path, key_fields):
    data = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                data[tuple(r[k] for k in key_fields)] = r
    return data


def save_csv(path, data, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(data):
            w.writerow({c: data[k].get(c, "") for c in fields})


# ---------------- DSE: ukurasa wa mbele ----------------
def parse_date(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    m = re.search(r"Market Summary\s*:?\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", text)
    if not m:
        return None
    try:
        return datetime.strptime(" ".join(m.groups()), "%B %d %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_table(html):
    out = []
    for tb in BeautifulSoup(html, "html.parser").find_all("table"):
        rows = tb.find_all("tr")
        if not rows:
            continue
        head = [re.sub(r"[^a-z]", "", c.get_text().lower()) for c in rows[0].find_all(["th", "td"])]
        if "symbol" not in head or "close" not in head:
            continue
        idx = {}
        for i, h in enumerate(head):
            if h in FIELD_MAP:
                idx[FIELD_MAP[h]] = i
            elif h.startswith("mcap"):
                idx["mcap"] = i
        for tr in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) <= idx["symbol"] or not cells[idx["symbol"]]:
                continue
            d = {"symbol": cells[idx["symbol"]].upper()}
            for k in COLS:
                d[k] = num(cells[idx[k]]) if k in idx and idx[k] < len(cells) else None
            out.append(d)
    return out


def merge_dse(data, date, rows):
    """Kama (tarehe, hisa) ipo, ibaki ile yenye turnover kubwa (siku kamili)."""
    added = 0
    for r in rows:
        key = (date, r["symbol"])
        old = data.get(key)
        new_t = r.get("turnover") or 0
        old_t = float(old.get("turnover") or 0) if old else -1
        if new_t >= old_t:
            data[key] = {"date": date, **{k: ("" if r.get(k) is None else r.get(k)) for k in ["symbol"] + COLS}}
            added += 1 if old is None else 0
    return added


def run_live():
    print("== DSE: bei za leo ==")
    r = http_get(DSE_URL)
    if not r:
        print("  ! ukurasa wa DSE haukufunguka")
        return
    date, rows = parse_date(r.text), parse_table(r.text)
    if not date or not rows:
        print(f"  ! imeshindwa kusoma (tarehe={date}, hisa={len(rows)})")
        return
    data = load_csv(DSE_FILE, ["date", "symbol"])
    added = merge_dse(data, date, rows)
    save_csv(DSE_FILE, data, DSE_FIELDS)
    print(f"  {date}: hisa {len(rows)}, mpya {added}, jumla ya safu {len(data)}")


# ---------------- Wayback Machine (historia) ----------------
def list_snapshots():
    days = {}
    for t in WAYBACK_TARGETS:
        r = http_get(CDX, params={"url": t, "from": FROM_YEAR, "to": TO_YEAR, "output": "json",
                                  "fl": "timestamp,original", "filter": "statuscode:200",
                                  "collapse": "timestamp:8"})
        if not r or not r.text.strip():
            print(f"  ! CDX haikujibu kwa {t}")
            continue
        rows = r.json()[1:]
        print(f"  {t}: picha {len(rows)}")
        for ts, orig in rows:
            days.setdefault(ts[:8], (ts, orig))
    return sorted(days.items())


def run_wayback():
    print("== Wayback Machine: historia ya DSE ==")
    os.makedirs("data", exist_ok=True)
    done = set(open(WAYBACK_DONE).read().split()) if os.path.exists(WAYBACK_DONE) else set()
    snaps = list_snapshots()
    todo = [(d, v) for d, v in snaps if d not in done]
    print(f"  siku zenye picha: {len(snaps)} | zilizobaki: {len(todo)}")
    data = load_csv(DSE_FILE, ["date", "symbol"])
    ok = fail = 0
    for i, (day, (ts, orig)) in enumerate(todo, 1):
        if time.time() > DEADLINE:
            print("  muda umeisha; endesha tena kuendelea")
            break
        r = http_get(f"https://web.archive.org/web/{ts}id_/{orig}")
        date, rows = (parse_date(r.text), parse_table(r.text)) if r else (None, [])
        if date and rows:
            merge_dse(data, date, rows)
            ok += 1
        else:
            fail += 1
        done.add(day)
        if i % 50 == 0:
            save_csv(DSE_FILE, data, DSE_FIELDS)
            open(WAYBACK_DONE, "w").write("\n".join(sorted(done)))
            print(f"  [{i}/{len(todo)}] sawa {ok} | haikusomeka {fail} | safu {len(data)}")
        time.sleep(1.0)
    save_csv(DSE_FILE, data, DSE_FIELDS)
    open(WAYBACK_DONE, "w").write("\n".join(sorted(done)))
    dates = sorted({d for d, _ in data})
    if dates:
        per_year = Counter(d[:4] for d in dates)
        print(f"  tarehe: {dates[0]} -> {dates[-1]} | siku {len(dates)} | safu {len(data)}")
        print("  siku kwa mwaka:", dict(sorted(per_year.items())))
    else:
        print("  hakuna data iliyosomeka (muundo wa zamani ni tofauti)")


# ---------------- TSL: ripoti za PDF ----------------
def tsl_title_date(title):
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", title)
    if not m:
        return None
    try:
        return datetime.strptime(" ".join(m.groups()), "%B %d %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def tsl_listing(html):
    out = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        if ".pdf" not in a["href"].lower():
            continue
        h = a.find_previous(["h1", "h2", "h3", "h4", "h5"])
        out.append((tsl_title_date(h.get_text(" ", strip=True)) if h else None, a["href"]))
    return out


def tsl_parse_text(text):
    rows = {}
    for line in text.splitlines():
        line = " ".join(line.split())
        m = PRICE_RE.match(line)
        if m:
            rows.setdefault(m.group(1), {}).update(
                open=num(m.group(2)), close=num(m.group(3)), gain_pct=num(m.group(4)),
                div_yield_pct=num(m.group(5)), ytd_pct=num(m.group(6)))
            continue
        m = TURN_RE.match(line)
        if m:
            rows.setdefault(m.group(1), {}).update(prev_turnover=num(m.group(2)), turnover=num(m.group(3)))
    return {s: d for s, d in rows.items() if "close" in d}


def run_tsl():
    print("== TSL: ripoti za PDF ==")
    import pdfplumber
    data = load_csv(TSL_FILE, ["date", "symbol"])
    have = {d for d, _ in data}
    reports, seen = [], set()
    for page in range(1, 41):
        r = http_get(TSL_LIST.format(page))
        if not r:
            break
        items = [x for x in tsl_listing(r.text) if x[1] not in seen]
        if not items:
            break
        for date, url in items:
            seen.add(url)
            reports.append((date, url))
        time.sleep(1.0)
    new = [(d, u) for d, u in reports if d not in have]
    print(f"  ripoti: {len(reports)} | mpya: {len(new)}")
    for i, (date, url) in enumerate(new, 1):
        try:
            resp = http_get(url)
            pdf = pdfplumber.open(BytesIO(resp.content))
            rows = tsl_parse_text("\n".join(p.extract_text() or "" for p in pdf.pages))
            if not date or not rows:
                print(f"  [{i}/{len(new)}] ! imeshindwa ({date})")
                continue
            for s, d in rows.items():
                data[(date, s)] = {"date": date, "symbol": s, **d}
        except Exception as e:
            print(f"  [{i}/{len(new)}] ! kosa: {e}")
        time.sleep(1.0)
    save_csv(TSL_FILE, data, TSL_FIELDS)
    dates = sorted({d for d, _ in data})
    if dates:
        print(f"  tarehe: {dates[0]} -> {dates[-1]} | siku {len(dates)}")


# ---------------- ARCHIVE.ORG: kila kitu cha zamani ----------------
ARCHIVE_TO_YEAR = "2024"
KEYWORDS = "market|report|price|daily|highlight|equit|trading|statistic"
FALLBACK_PREFIXES = ["dse.co.tz/dse/market-report"]
ARCHIVE_DONE = "data/archive_done.txt"
ARCHIVE_DIAG = "data/archive_diagnostics.txt"
MAX_ITEMS = 6000
MAX_PDF_BYTES = 2_000_000
SKIP_WORDS = ("annual", "brochure", "rule", "regulation", "prospectus", "financial", "form", "guideline",
              "circular", "tender", "vacanc", "career")
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}
SYMBOL_OK = re.compile(r"^[A-Z][A-Z0-9\-\.]{1,12}$")
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/,]+([A-Za-z]{3,9})\.?[\s\-/,]+(\d{4})"),
    re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"),
]


def month_num(name):
    name = name.lower()
    for full, n in MONTHS.items():
        if full == name or (len(name) >= 3 and full.startswith(name[:3]) and len(name) <= len(full)
                            and full.startswith(name)):
            return n
    return None


def find_date(text, snap_day=None):
    text = " ".join(text.split())
    cands = []
    for pat_i, pat in enumerate(DATE_PATTERNS):
        for m in pat.finditer(text):
            a, b, y = m.groups()
            day, mon = (a, b) if pat_i == 0 else (b, a)
            mn = month_num(mon)
            if not mn or not day.isdigit():
                continue
            try:
                dt = datetime(int(y), mn, int(day))
            except ValueError:
                continue
            if 2008 <= dt.year <= 2026:
                cands.append((m.start(), dt.strftime("%Y-%m-%d")))
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", text)
    if m:
        try:
            datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            cands.append((m.start(), "-".join(m.groups())))
        except ValueError:
            pass
    for _, dt in sorted(cands):
        if snap_day is None or dt.replace("-", "") <= snap_day:
            return dt
    return None


def map_header(head):
    idx = {}
    for i, h in enumerate(head):
        if h.startswith(("prev", "previous")) and "clos" in h:
            idx.setdefault("prev_close", i)
        elif any(h.startswith(k) for k in ("company", "symbol", "counter", "security", "ticker")):
            idx.setdefault("symbol", i)
        elif h in ("closingprice", "closeprice", "close", "closing", "todayprice", "currentprice", "price"):
            idx.setdefault("close", i)
        elif h in ("open", "openingprice", "openprice", "opening"):
            idx.setdefault("open", i)
        elif h in ("high", "highprice", "dayhigh"):
            idx.setdefault("high", i)
        elif h in ("low", "lowprice", "daylow"):
            idx.setdefault("low", i)
        elif "volume" in h or h in ("vol", "quantity"):
            idx.setdefault("volume", i)
        elif "turnover" in h:
            idx.setdefault("turnover", i)
        elif h in ("deals", "trades", "noofdeals"):
            idx.setdefault("deals", i)
        elif h.startswith(("mcap", "marketcap")):
            idx.setdefault("mcap", i)
    return idx


def records_from_rows(table):
    """table = orodha ya safu (orodha ya maandishi). Rudisha orodha ya dict."""
    for hi in range(min(3, len(table))):
        head = [re.sub(r"[^a-z]", "", (c or "").lower()) for c in table[hi]]
        idx = map_header(head)
        if "symbol" in idx and "close" in idx:
            out = []
            for row in table[hi + 1:]:
                row = [(c or "").replace("\n", " ").strip() for c in row]
                if len(row) <= max(idx.values()):
                    continue
                sym = row[idx["symbol"]].upper().strip()
                if not SYMBOL_OK.match(sym) or sym in ("TOTAL", "COMPANY"):
                    continue
                rec = {"symbol": sym}
                for k in COLS:
                    rec[k] = num(row[idx[k]]) if k in idx else None
                if rec["close"] is not None:
                    out.append(rec)
            return out
    return []


def html_records(html):
    soup = BeautifulSoup(html, "html.parser")
    recs = []
    for tb in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in tb.find_all("tr")]
        recs += records_from_rows(rows)
    return soup.get_text(" ", strip=True), recs


def pdf_records(content):
    import pdfplumber
    pdf = pdfplumber.open(BytesIO(content))
    pages = pdf.pages[:8]
    text = "\n".join((p.extract_text() or "") for p in pages[:2])
    recs = []
    for p in pages:
        for tb in p.extract_tables():
            recs += records_from_rows(tb)
    return text, recs


def cdx(params):
    r = http_get(CDX, params=params)
    if not r or not r.text.strip():
        return None
    try:
        return r.json()[1:]
    except ValueError:
        return None


def list_items():
    base = [("matchType", "prefix"), ("output", "json"), ("from", "2009"), ("to", ARCHIVE_TO_YEAR),
            ("filter", "statuscode:200")]
    items = []
    rows = cdx([("url", "dse.co.tz/"), *base, ("fl", "timestamp,original"), ("filter", "mimetype:text/html"),
                ("filter", f"original:.*({KEYWORDS}).*"), ("collapse", "timestamp:8")])
    if rows is None:
        print("  ! kichujio cha CDX kimeshindwa, natumia orodha ya msingi")
        rows = []
        for pref in FALLBACK_PREFIXES:
            rows += cdx([("url", pref), *base, ("fl", "timestamp,original"),
                         ("filter", "mimetype:text/html"), ("collapse", "timestamp:8")]) or []
    items += [("html", ts, o) for ts, o in rows]
    print(f"  kurasa za HTML: {len(rows)}")
    rows = cdx([("url", "dse.co.tz/"), *base, ("fl", "timestamp,original,length"),
                ("filter", "mimetype:application/pdf"), ("collapse", "urlkey")]) or []
    pdfs = []
    for ts, o, ln in rows:
        if any(w in o.lower() for w in SKIP_WORDS):
            continue
        if ln.isdigit() and int(ln) > MAX_PDF_BYTES:
            continue
        pdfs.append(("pdf", ts, o))
    print(f"  PDF: {len(pdfs)} (kati ya {len(rows)})")
    return items + pdfs


def run_archive():
    print("== Archive.org: kurasa na PDF zote za zamani ==")
    os.makedirs("data", exist_ok=True)
    done = set(open(ARCHIVE_DONE).read().split("\n")) if os.path.exists(ARCHIVE_DONE) else set()
    items = list_items()
    todo = [it for it in items if f"{it[1]} {it[2]}" not in done][:MAX_ITEMS]
    print(f"Jumla: {len(items)} | zinazofuata: {len(todo)}")
    if not todo:
        print("  hakuna cha kufanya (kila kitu kimeshapitiwa); angalia data/archive_diagnostics.txt")
        return
    data = load_csv(DSE_FILE, ["date", "symbol"])
    stats = {"html": Counter(), "pdf": Counter()}
    samples = {"html": [], "pdf": []}
    new_rows, new_dates = 0, set()

    def flush():
        save_csv(DSE_FILE, data, DSE_FIELDS)
        open(ARCHIVE_DONE, "w").write("\n".join(sorted(done)))

    for i, (kind, ts, orig) in enumerate(todo, 1):
        if time.time() > DEADLINE:
            print("Muda umeisha; endesha tena kuendelea.")
            break
        done.add(f"{ts} {orig}")
        r = http_get(f"https://web.archive.org/web/{ts}id_/{orig}")
        reason, text, recs = "haikupakuliwa", "", []
        if r is not None:
            try:
                if kind == "pdf":
                    if r.content.startswith(b"%PDF"):
                        text, recs = pdf_records(r.content)
                    else:
                        reason = "si PDF"
                else:
                    text, recs = html_records(r.text)
            except Exception as e:
                reason = f"kosa la kusoma: {str(e)[:60]}"
            date = find_date(text, ts[:8]) if recs else None
            if recs and date:
                for rec in recs:
                    key = (date, rec["symbol"])
                    row = data.get(key)
                    if row is None:
                        data[key] = {"date": date, **{k: ("" if rec.get(k) is None else rec[k])
                                                      for k in ["symbol"] + COLS}}
                        new_rows += 1
                        new_dates.add(date)
                    else:
                        for k in COLS:
                            if row.get(k, "") in ("", None) and rec.get(k) is not None:
                                row[k] = rec[k]
                stats[kind]["sawa"] += 1
                reason = None
            elif recs:
                reason = "jedwali lipo, tarehe haipo"
            elif reason == "haikupakuliwa":
                reason = "hakuna jedwali la bei"
        if reason:
            stats[kind]["imeshindwa"] += 1
            if len(samples[kind]) < 8:
                samples[kind].append(f"{reason} | {ts} {orig}\n    {' '.join(text.split())[:250]}")
        if i % 25 == 0:
            flush()
            print(f"  [{i}/{len(todo)}] html {dict(stats['html'])} | pdf {dict(stats['pdf'])} | safu mpya {new_rows}")
        time.sleep(1.0)
    flush()

    all_dates = sorted({k[0] for k in data})
    per_year = dict(sorted(Counter(x[:4] for x in all_dates).items()))
    lines = [f"Imeandikwa: {datetime.now():%Y-%m-%d %H:%M}",
             f"Tarehe zote kwenye dse_daily.csv: {all_dates[0] if all_dates else '-'} -> {all_dates[-1] if all_dates else '-'}"
             f" | siku {len(all_dates)} | safu {len(data)}",
             f"Siku kwa mwaka: {per_year}",
             f"Run hii: safu mpya {new_rows}, siku mpya {len(new_dates)}",
             f"HTML: {dict(stats['html'])} | PDF: {dict(stats['pdf'])}", "", "Mifano ya zilizoshindwa:"]
    for kind in ("html", "pdf"):
        lines += [f"[{kind}] {s}" for s in samples[kind]]
    open(ARCHIVE_DIAG, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:5]))


# ---------------- kuanzisha ----------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if mode == "backfill":
        run_wayback()
        run_tsl()
        run_archive()
    elif mode == "archive":
        run_archive()
    elif mode == "daily":
        run_live()
        run_tsl()
    else:
        print("Tumia: python dse_all.py daily   au   python dse_all.py backfill")


if __name__ == "__main__":
    main()
