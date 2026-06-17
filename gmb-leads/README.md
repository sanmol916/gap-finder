# gmb-leads — find local businesses with no website

> **New here? Read [SETUP_GUIDE.md](SETUP_GUIDE.md) — a full beginner, step-by-step walkthrough
> (install Python, get a Google key, run it, open the sheet, troubleshooting).**

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
