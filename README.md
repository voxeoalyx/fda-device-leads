# FDA Device Leads

Turn three public FDA device databases (510(k) clearances, establishment registrations & listings, device recalls) into one weekly lead CSV of medical-device companies with fresh FDA activity.

- **Get the weekly CSV without running anything:** Ko-fi membership, $12/mo, cancel anytime → **[KOFI_LINK_PLACEHOLDER]**
- **Free sample:** [`sample/sample-fda-device-leads.csv`](sample/sample-fda-device-leads.csv)
- **Run it yourself (free, MIT):** `python3 scripts/generate_weekly.py --end 2026-10-26` (stdlib only, no key needed)
- `actor/` is the same pipeline packaged as an Apify actor (Python SDK).

## Columns
leadType, company, contactName, phone, address, state, country, device, productCode, establishmentType, recallReason, recallStatus, date, dateType, id, sourceUrl

## Limits
- FDA posts 510(k) decisions and listings 1–2 weeks late, so the script shifts that window back 10 days (`--lag`).
- openFDA caps paging at 25,000 per query. Contacts are as filed (often a consultant). No emails.

## Disclosures
- Data: **openFDA, public domain / CC0** (https://open.fda.gov/license/). Uses only the official API. No website scraping.
- **Not affiliated with or endorsed by the U.S. FDA.** openFDA data is unvalidated, so verify before use. Not regulatory or legal advice.
- **AI-assisted:** code, docs and data pipeline were built with AI assistance and are reviewed and published by a human.
