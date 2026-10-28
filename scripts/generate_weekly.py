#!/usr/bin/env python3
"""Weekly FDA Device Leads CSV generator (public-domain openFDA data; AI-assisted build).
Usage: python3 generate_weekly.py [--end YYYY-MM-DD] [--days 7]
Writes out/fda-device-leads-<start>_<end>.csv (full) and out/sample-fda-device-leads.csv (first 15 rows, free).
No API key needed; set OPENFDA_API_KEY env to raise rate limits."""
import csv, json, os, sys, time, argparse, datetime as dt, urllib.request, urllib.error
from urllib.parse import quote
B = "https://api.fda.gov/device"
COLS = ["leadType","company","contactName","phone","address","state","country","device","productCode","establishmentType","recallReason","recallStatus","date","dateType","id","sourceUrl"]
def get(url):
    k = os.environ.get("OPENFDA_API_KEY")
    if k: url += f"&api_key={k}"
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return {"results": []}
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)
def pages(ep, search, sort=None, cap=5000):
    skip = 0
    while skip < min(cap, 25000):
        res = get(f"{B}/{ep}.json?search={search}&limit=100&skip={skip}" + (f"&sort={sort}" if sort else "")).get("results", [])
        yield from res
        if len(res) < 100: return
        skip += 100; time.sleep(0.3)
j = lambda *x: ", ".join(i for i in x if i)
def k510(a, b):
    for r in pages("510k", f"decision_date:[{a}+TO+{b}]", "decision_date:desc"):
        k = r.get("k_number")
        yield dict(leadType="510k_clearance", company=r.get("applicant"), contactName=(r.get("contact") or "").strip(),
            address=j(r.get("address_1"), r.get("address_2"), r.get("city"), r.get("state"), r.get("zip_code")), state=r.get("state"),
            country=r.get("country_code"), device=r.get("device_name"), productCode=r.get("product_code"),
            date=r.get("decision_date"), dateType="decision_date", id=k,
            sourceUrl=f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k}")
def listings(a, b):
    for r in pages("registrationlisting", f"products.created_date:[{a}+TO+{b}]"):
        g = r.get("registration", {}); p = (r.get("products") or [{}])[0]
        yield dict(leadType="new_device_listing", company=g.get("name"),
            address=j(g.get("address_line_1"), g.get("address_line_2"), g.get("city"), g.get("state_code"), g.get("zip_code")),
            state=g.get("state_code"), country=g.get("iso_country_code"), device="; ".join(r.get("proprietary_name") or []),
            productCode=p.get("product_code"), establishmentType="; ".join(r.get("establishment_type") or []),
            date=p.get("created_date"), dateType="listing_created_date", id=g.get("registration_number") or p.get("owner_operator_number"),
            sourceUrl="https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRL/rl.cfm?start_search=1&establishmentName=" + quote(g.get("name") or ""))
def recalls(a, b):
    for r in pages("recall", f"event_date_posted:[{a}+TO+{b}]", "event_date_posted:desc"):
        yield dict(leadType="recall", company=r.get("recalling_firm"), phone=(r.get("additional_info_contact") or "").replace("\n", " "),
            address=j(r.get("address_1"), r.get("city"), r.get("state"), r.get("postal_code")), state=r.get("state"),
            device=(r.get("product_description") or "").replace("\n", " ")[:300], productCode=r.get("product_code"),
            recallReason=(r.get("reason_for_recall") or "").replace("\n", " ")[:500], recallStatus=r.get("recall_status"),
            date=r.get("event_date_posted"), dateType="recall_posted_date", id=r.get("product_res_number"),
            sourceUrl=f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={r.get('cfres_id')}")
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--end"); ap.add_argument("--days", type=int, default=7); ap.add_argument("--lag", type=int, default=10, help="days to shift 510k/listing window back (FDA posts these ~1-2 weeks late)"); ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    a = ap.parse_args()
    end = dt.date.fromisoformat(a.end) if a.end else dt.date.today(); start = end - dt.timedelta(days=a.days - 1)
    s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    ls_, le_ = (start - dt.timedelta(days=a.lag)).strftime("%Y%m%d"), (end - dt.timedelta(days=a.lag)).strftime("%Y%m%d")
    rows = []
    for f, x, y in ((k510, ls_, le_), (listings, ls_, le_), (recalls, s, e)):
        n = len(rows); rows += list(f(x, y)); print(f"{f.__name__}: {len(rows)-n}", file=sys.stderr)
    seen, uniq = set(), []
    for r in rows:
        key = (r["leadType"], r.get("id"), r.get("device"))
        if key not in seen: seen.add(key); uniq.append(r)
    os.makedirs(a.out, exist_ok=True)
    full = os.path.join(a.out, f"fda-device-leads-{start}_{end}.csv")
    note = [f"# FDA Device Leads: recalls posted {start} to {end}; 510(k)/listings {start - dt.timedelta(days=a.lag)} to {end - dt.timedelta(days=a.lag)} (FDA publication lag). Source: openFDA (public domain/CC0). Not affiliated with or endorsed by FDA. AI-assisted. Data unvalidated: verify before use."]
    for path, data in ((full, uniq), (os.path.join(a.out, "sample-fda-device-leads.csv"), [r for t in ("510k_clearance","new_device_listing","recall") for r in [x for x in uniq if x["leadType"]==t][:5]])):
        with open(path, "w", newline="") as fh:
            fh.write(note[0] + "\n"); w = csv.DictWriter(fh, COLS, extrasaction="ignore"); w.writeheader(); w.writerows(data)
    print(f"{len(uniq)} rows -> {full}", file=sys.stderr)
if __name__ == "__main__": main()
