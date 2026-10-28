"""openFDA Device Leads Feed — Apify actor (AI-assisted build). Data: openFDA (public domain / CC0)."""
import asyncio, os, httpx
from urllib.parse import quote
from apify import Actor

BASE = "https://api.fda.gov/device"
FREE_TIER_LIMIT = 50  # free users (no paid plan) capped per run, stated in README/input schema

def d(s): return s.replace("-", "")

def q_or(field, vals): return "(" + "+OR+".join(f'{field}:"{v}"' for v in vals) + ")"

def build(src, inp):
    df, dt = d(inp["dateFrom"]), d(inp["dateTo"])
    codes, kws, state = inp.get("productCodes") or [], inp.get("keywords") or [], inp.get("state")
    if src == "510k":
        parts = [f"decision_date:[{df}+TO+{dt}]"]
        if codes: parts.append(q_or("product_code", codes))
        if kws: parts.append(q_or("device_name", kws))
        if state: parts.append(f'state:"{state}"')
        return "510k", "+AND+".join(parts), "decision_date:desc"
    if src == "registrationlisting":
        parts = [f"products.created_date:[{df}+TO+{dt}]"]
        if codes: parts.append(q_or("products.product_code", codes))
        if kws: parts.append(q_or("proprietary_name", kws))
        if state: parts.append(f'registration.state_code:"{state}"')
        return "registrationlisting", "+AND+".join(parts), None
    parts = [f"event_date_posted:[{df}+TO+{dt}]"]
    if codes: parts.append(q_or("product_code", codes))
    if kws: parts.append(q_or("product_description", kws))
    if state: parts.append(f'state:"{state}"')
    return "recall", "+AND+".join(parts), "event_date_posted:desc"

def row(src, r):
    if src == "510k":
        k = r.get("k_number")
        return {"leadType": "510k_clearance", "company": r.get("applicant"), "contactName": (r.get("contact") or "").strip() or None,
            "address": ", ".join(x for x in [r.get("address_1"), r.get("address_2"), r.get("city"), r.get("state"), r.get("zip_code"), r.get("country_code")] if x),
            "state": r.get("state"), "device": r.get("device_name"), "productCode": r.get("product_code"),
            "date": r.get("decision_date"), "dateType": "decision_date", "id": k,
            "sourceUrl": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k}",
            "apiUrl": f"{BASE}/510k.json?search=k_number:{k}"}
    if src == "registrationlisting":
        g = r.get("registration", {}); p = (r.get("products") or [{}])[0]; fei = g.get("fei_number")
        return {"leadType": "new_device_listing", "company": g.get("name"), "contactName": None,
            "address": ", ".join(x for x in [g.get("address_line_1"), g.get("address_line_2"), g.get("city"), g.get("state_code"), g.get("zip_code"), g.get("iso_country_code")] if x),
            "state": g.get("state_code") or None, "device": "; ".join(r.get("proprietary_name") or []), "productCode": p.get("product_code"),
            "establishmentType": "; ".join(r.get("establishment_type") or []),
            "date": p.get("created_date"), "dateType": "listing_created_date",
            "id": g.get("registration_number") or p.get("owner_operator_number"),
            "sourceUrl": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRL/rl.cfm?start_search=1&establishmentName=" + quote(g.get("name") or ""),
            "apiUrl": f"{BASE}/registrationlisting.json?search=registration.name:" + quote('"' + (g.get("name") or "") + '"')}
    i = r.get("cfres_id")
    return {"leadType": "recall", "company": r.get("recalling_firm"), "contactName": None, "phone": r.get("additional_info_contact"),
        "address": ", ".join(x for x in [r.get("address_1"), r.get("city"), r.get("state"), r.get("postal_code")] if x),
        "state": r.get("state"), "device": (r.get("product_description") or "")[:300], "productCode": r.get("product_code"),
        "recallReason": r.get("reason_for_recall"), "recallStatus": r.get("recall_status"),
        "date": r.get("event_date_posted"), "dateType": "recall_posted_date", "id": r.get("product_res_number"),
        "sourceUrl": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={i}",
        "apiUrl": f"{BASE}/recall.json?search=cfres_id:{i}"}

async def fetch(client, src, inp, cap):
    ep, search, sort = build(src, inp)
    out, skip = [], 0
    while len(out) < cap and skip < 25000:
        lim = min(100, cap - len(out))
        url = f"{BASE}/{ep}.json?search={search}&limit={lim}&skip={skip}" + (f"&sort={sort}" if sort else "")
        if inp.get("fdaApiKey"): url += f"&api_key={inp['fdaApiKey']}"
        r = await client.get(url)
        if r.status_code == 404: break  # openFDA returns 404 for no matches
        r.raise_for_status()
        res = r.json().get("results", [])
        out += [row(src, x) for x in res]
        if len(res) < lim: break
        skip += lim; await asyncio.sleep(0.3)
    return out

async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        inp.setdefault("dateFrom", "2026-09-01"); inp.setdefault("dateTo", "2026-10-27")
        sources = inp.get("sources") or ["510k", "registrationlisting", "recall"]
        cap = int(inp.get("maxResults", 100))
        free = os.environ.get("APIFY_IS_AT_HOME") == "1" and os.environ.get("APIFY_USER_IS_PAYING") == "0"
        if free and cap > FREE_TIER_LIMIT:
            Actor.log.info(f"Free tier: capping to {FREE_TIER_LIMIT} results per run."); cap = FREE_TIER_LIMIT
        total = 0
        async with httpx.AsyncClient(timeout=60) as c:
            for s in sources:
                rows = await fetch(c, s, inp, cap - total)
                for rw in rows:
                    await Actor.push_data(rw)
                    try: await Actor.charge("result")  # PPE event
                    except Exception: pass  # no-op locally
                total += len(rows); Actor.log.info(f"{s}: {len(rows)} leads")
                if total >= cap: break
        if free and total >= FREE_TIER_LIMIT:
            await Actor.set_status_message("Free tier limit reached (50 results/run). Upgrade Apify plan for more.")

if __name__ == "__main__": asyncio.run(main())
