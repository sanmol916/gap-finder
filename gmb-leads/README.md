# gmb-leads — find local businesses worldwide (with & without a website)

Build clean lead lists of local businesses **anywhere in the world** and split them into:

- **No website** — your best prospects for selling a website / digital services.
- **With a website** — for comparison, or to pitch other services.

Every run produces **two CSV files** (and Excel `.xlsx` from the CLI): one for each bucket.

> **Run locally (no cap, unlimited scraping)?** Read [RUN_LOCALLY.md](RUN_LOCALLY.md).
> **Deploy as a website on Vercel?** Read [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md).
> **First time / Google key setup?** Read [SETUP_GUIDE.md](SETUP_GUIDE.md).

This folder works two ways:
- **CLI** (`find_leads.py`) — best for big bulk runs; outputs CSV + Excel.
- **Web app** (`api/index.py`) — a clean browser form (WhatsApp-style UI); deployable free on Vercel.

## How it works (and why it's done this way)
It uses the **official Google Places API (New)** — not scraping.

> **Scraping Google Maps / Business Profiles violates Google's Terms of Service**, breaks
> constantly, and risks bans. The Places API legally returns each business's `websiteUri`,
> so we simply split businesses by whether that field is empty. This is the sustainable, allowed path.

For each `location × keyword` it runs a Text Search, collects businesses, de-duplicates them,
and splits them into **no website** vs **with website**.

## Worldwide
There are no built-in city presets anymore — you **type any places you want**, e.g.
`Paris, France`, `New York, USA`, `Dubai, UAE`, `Lagos, Nigeria`. Add as many as you like
(one per line in the web app, or space-separated on the CLI). The old India presets still work
on the CLI via `--cities` / `--states` / `--all-india`, but the default mode is free-form worldwide.

An optional **country bias** (ISO 3166-1 code, e.g. `GB`, `US`, `AE`) nudges results toward one
country — handy when your location text is just a city name.

## Setup
1. Create a project: https://console.cloud.google.com/
2. Enable **Places API (New)** and turn on **billing** (Google gives a recurring free credit;
   check current Places pricing before large runs).
3. Create an API key and restrict it to the Places API.
4. Install + set the key:
   ```bash
   pip install -r requirements.txt
   export GOOGLE_MAPS_API_KEY="your_key"
   ```

## Usage (CLI)
```bash
# verify the tool works WITHOUT a key (uses a built-in mock)
python find_leads.py --self-test

# WORLDWIDE: type any places (multiple, no limit) + your keywords
python find_leads.py \
    --locations "Paris, France" "New York, USA" "Dubai, UAE" \
    --categories "beauty salon" "dental clinic" "real estate agency"

# bias results toward one country (optional ISO code)
python find_leads.py --locations "London" --region GB --categories "cafe"

# India presets still work
python find_leads.py --states Assam
python find_leads.py --cities Guwahati Shillong --categories "gym"
python find_leads.py --all-india
```

Output goes to `gmb-leads/output/`:
```
worldwide_leads_no_website.csv    (+ .xlsx)
worldwide_leads_with_website.csv  (+ .xlsx)
```

## Web app
Run it locally or deploy on Vercel (see the guides). The form lets you:
- paste any number of **locations** (one per line),
- optionally pick a **country bias**,
- type **keywords** (with one-click suggestion chips),
- choose **results depth** (Top 20 / 40 / 60),
- and download **two CSVs** — *no website* and *with website* — from tabbed result tables.

By default the web app has **no per-run cap**. On serverless (Vercel ~60s limit) keep runs small,
or set `GMB_MAX_QUERIES=<n>` to cap searches per run. For huge sweeps, run locally.

## Output columns
`business_name, category, location, city, state, phone, address, website, maps_url, rating,
reviews, business_status, place_id`

## Cost & etiquette notes
- Each `location × keyword` that returns results bills against your Places API usage; pagination
  (up to 3 pages = 60 results) multiplies that. Start with a few locations/keywords to gauge cost.
- Set a **budget alert** and a **daily quota cap** in Google Cloud (SETUP_GUIDE.md, Step 6).
- Respect the API quota and Google's Terms. Don't resell raw Google data; use it to contact
  businesses directly.

## Turning leads into clients (the point of this)
For each no-website business: a quick call/visit — "I saw you're on Google Maps but don't have
a website; here's a 1-page site I can set up for you." High-intent, low-competition outreach.

## FAQ

**Is searching by keyword good?**
Yes — it's the recommended approach. The Places API (New) **Text Search** is keyword-based by
design (e.g. `"beauty salon in Paris, France"`). Run several related keywords (comma/space
separated) to widen coverage. Each keyword+location search returns up to **60 results** (Google's
hard cap), so coverage comes from running **many keyword × location combinations**.

**How do I make the API key permanent (stop pasting it)?**
Set `GOOGLE_MAPS_API_KEY` as an environment variable on the server (Vercel → Project → Settings →
Environment Variables). The app detects it and the form's key box becomes optional. Keep the URL
private if you do this.

**How do I scrape as much as possible?**
The web app is uncapped by default; on Vercel set `GMB_MAX_QUERIES` to avoid the ~60s timeout, or
use the local CLI / local web form for unlimited runs ([RUN_LOCALLY.md](RUN_LOCALLY.md)).
