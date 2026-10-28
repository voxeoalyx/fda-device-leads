#!/usr/bin/env python3
"""Build a free public weekly summary page (Markdown) from the weekly CSV.
Public page = counts + top product codes/states + 10 sample rows. The full file stays paid (Ko-fi).
Usage: python3 weekly_summary.py <full.csv> <outdir>"""
import csv, sys, os, collections
src, outdir = sys.argv[1], sys.argv[2]
lines = open(src).read().splitlines(); header = lines[0].lstrip("# ")
rows = list(csv.DictReader(l for l in lines if not l.startswith("#")))
end = os.path.basename(src).rsplit("_", 1)[-1].replace(".csv", "")
c = collections.Counter(r["leadType"] for r in rows)
pc = collections.Counter(r["productCode"] for r in rows if r["productCode"]).most_common(10)
st = collections.Counter(r["state"] for r in rows if r["state"]).most_common(10)
foreign = sum(1 for r in rows if not r["state"])
lab = {"510k_clearance": "510(k) clearances", "new_device_listing": "New device listings", "recall": "Device recalls"}
o = [f"# FDA device activity, week ending {end}", "", f"_{header}_", "",
     "| Event type | Companies/rows |", "|---|---|"] + [f"| {lab[k]} | {c.get(k,0)} |" for k in lab] + [f"| **Total** | **{len(rows)}** |", "",
     f"Non-US firms (no state): {foreign}", "", "## Top FDA product codes", ""] + [f"- `{k}`: {v}" for k, v in pc] + ["", "## Top US states", ""] + [f"- {k}: {v}" for k, v in st] + [
     "", "## Recent 510(k) clearances (first 10)", "", "| Company | Device | Product code | Decision date |", "|---|---|---|---|"] + [
     f"| {r['company']} | {r['device'][:70]} | {r['productCode']} | [{r['date']}]({r['sourceUrl']}) |" for r in [x for x in rows if x['leadType']=='510k_clearance'][:10]] + [
     "", "---", "Full file (all rows with address, filed contact/phone, recalls with reasons, FDA links): **https://ko-fi.com/fdadeviceleads** ($12/mo, cancel anytime). Or run the free MIT script in this repo yourself.",
     "", "Source: openFDA, public domain (CC0). Not affiliated with or endorsed by the U.S. FDA. AI-assisted pipeline. Data unvalidated: verify before use."]
os.makedirs(outdir, exist_ok=True); p = os.path.join(outdir, f"{end}.md"); open(p, "w").write("\n".join(o) + "\n"); print(p)
