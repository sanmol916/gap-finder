# gmb-leads — find local businesses with no website

> **Run locally?** Read [SETUP_GUIDE.md](SETUP_GUIDE.md) — full beginner walkthrough
> (install Python, get a Google key, run it, open the sheet, troubleshooting).
>
> **Deploy as a website on Vercel?** Read [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) — deploys just
> this scraper as a web form, and fixes the "Places API not in the Restrict-key list" issue.

This folder works two ways:
- **CLI** (`find_leads.py`) — best for big bulk runs; outputs CSV + Excel.
- **Web app** (`api/index.py`) — a small browser form for quick, targeted lookups; deployable
  free on Vercel. Capped per run to fit serverless time limits.

Build a clean lead list of local businesses that **don't have a website** — ideal prospects
for selling website / digital services. Presets target **North East India** (all 8 states),
but you can point it anywhere.

## How it works (and why it's done this way)
It uses the **official Google Places API (New)** — not scraping.

> **Scraping Google Maps / Business Profiles violates Google's Terms of Service**, breaks
> constantly, and risks bans. The Places API legally returns each business's `websiteUri`,
> so we simply keep the ones where that field is empty. This is the sustainable, allowed path.

For each `city × category` it runs a Text Search, collects businesses, de-duplicates them,
and filters to those with **no website**. Output is a CSV and a real Excel `.xlsx`.

## What it can and cannot do
- It **can** target business-dense NE India cities + categories and find no-website businesses.
- It **cannot** tell you "where people search for website services" — no business API exposes
  search volume per area. Targeting by city + category is the practical equivalent.

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

## Usage
```bash
# verify the tool works WITHOUT a key (uses a built-in mock)
python find_leads.py --self-test

# all NE India presets (every city x every category) - large run
python find_leads.py

# a few cities + categories
python find_leads.py --cities Guwahati Shillong Imphal \
    --categories "beauty salon" "dental clinic" "real estate agent"

# one whole state
python find_leads.py --states Assam

# also keep businesses that already have a website (comparison)
python find_leads.py --include-with-website
```

Output goes to `gmb-leads/output/ne_india_no_website_leads.csv` (+ `.xlsx`).

## Output columns
`business_name, category, city, state, phone, address, maps_url, rating, reviews,
business_status, place_id`

## Sample sheet (no key needed)
`SAMPLE_leads_template.csv` / `SAMPLE_leads_template.xlsx` show the exact output format with
**fictional** NE India rows (names prefixed `[SAMPLE]`). Use them to preview the structure
and import into Google Sheets before you run the real thing.

## Presets
Edit `presets.json` to change cities (grouped by state) and categories. Categories are chosen
to favor business types that often **lack** a website (salons, clinics, boutiques, garages,
coaching centers, etc.).

## Cost & etiquette notes
- Each query that returns results bills against your Places API usage; pagination (up to 3
  pages = 60 results) multiplies that. Start with a few cities/categories to gauge cost.
- Respect the API quota and Google's Terms. Don't resell raw Google data; use it to contact
  businesses directly.

## Turning leads into clients (the point of this)
For each no-website business: a quick call/visit — "I saw you're on Google Maps but don't have
a website; here's a 1-page site I can set up for you." High-intent, low-competition outreach.


---

## Coverage
`presets.json` now spans **all of India** — 36 states & union territories and ~185 major cities.
The web app turns this into a **State dropdown** + a **City multi-select** (grouped by state), and
a **Category multi-select**. Edit `presets.json` to add more cities/categories any time.

## FAQ

**Is searching by keyword good?**
Yes — it's the recommended approach. The Places API (New) **Text Search** is keyword-based by
design (e.g. `"beauty salon in Jaipur, Rajasthan, India"`). Keywords are flexible and match how
people label businesses, so they surface more results than rigid category-only filters. Tips:
- Use the business *type* people would search (e.g. `dental clinic`, `boutique`, `car garage`).
- Run several related keywords (the multi-select lets you queue many at once) to widen coverage.
- Each keyword+city search returns up to **60 results** (Google's hard cap), so coverage comes
  from running **many keyword × city combinations**, not from one big query.

**How do I make the API key permanent (stop pasting it)?**
Set `GOOGLE_MAPS_API_KEY` as an environment variable on the server (Vercel → Project → Settings →
Environment Variables). The app detects it and the form's key box becomes optional. See
[DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) step 5. Keep the URL private if you do this.

**How do I scrape as much as possible?**
- **Web app:** capped per run (serverless time limit). Run batches: e.g. one state at a time, or
  a set of cities, repeatedly. Use "Top 60" depth for maximum results per search.
- **Local CLI (best for bulk):** no time limit. Examples:
  ```bash
  python find_leads.py --states Maharashtra Karnataka Tamil Nadu --max-pages 3
  python find_leads.py --all-india --max-pages 3        # everything (large - mind the cost)
  ```
  The CLI writes CSV **and** a real Excel `.xlsx`, and de-dupes across the whole run.

> Reminder: each search consumes Google quota. Big sweeps cost money — keep a budget + daily
> quota cap set (SETUP_GUIDE.md, Step 6), and start narrow.
