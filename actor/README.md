# openFDA Device Leads Feed — new FDA device clearances, listings & recalls as sales leads

Get a fresh list of medical-device companies that **just did something at the FDA**: cleared a 510(k), listed a new device, or posted a recall. Each one is a company that may need your help now (contract manufacturing, sterilization, distribution, regulatory, quality, legal, or recall logistics).

## What you get (one row per lead)
| Field | Meaning |
|---|---|
| leadType | `510k_clearance`, `new_device_listing`, or `recall` |
| company, contactName, phone, address, state | as filed with FDA (510(k) contacts may be the submitter's consultant) |
| device, productCode, establishmentType | what the event is about |
| date, dateType | decision date / listing created date / recall posted date |
| recallReason, recallStatus | recalls only |
| sourceUrl, apiUrl | link to the FDA record and the openFDA query |

## Input
Date range, sources, FDA product codes and/or device keywords, US state, max results. Example:
```json
{"dateFrom":"2026-09-01","dateTo":"2026-10-27","sources":["510k","recall"],"state":"CA","productCodes":["QJP"],"maxResults":200}
```
Schedule it weekly with a 7-day window to get a recurring lead feed.

## Pricing
- **$5 per 1,000 lead rows** (pay per result). No platform-usage charges on top.
- **Free tier:** Apify free-plan users get up to **50 rows per run**. The run stops cleanly with a "Free tier limit reached" message, not an error.

## Data source & disclosures
- Data comes from the U.S. FDA's **openFDA API** (510(k), device registration & listing, device recall endpoints). openFDA data is public domain / CC0 (https://open.fda.gov/license/). The actor calls the official API and does no website scraping.
- **Not affiliated with or endorsed by the FDA.** openFDA warns its data is unvalidated. Verify before relying on it. Not regulatory or legal advice.
- FDA publishes 510(k) decisions and listings with a lag of about a week. Recent days may be incomplete.
- openFDA caps paging at 25,000 records per query. Narrow the dates or product codes for bigger pulls.
- **AI-assisted build:** this actor and its README were built with AI assistance and reviewed by the publisher.
