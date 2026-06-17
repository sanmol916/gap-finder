# Deploy the GMB Leads scraper on Vercel (beginner guide)

This deploys **only** the `gmb-leads` tool as a small website with a form. You type cities +
categories, it returns businesses with **no website**, and gives you a CSV download.

> Note on size: Vercel runs this as a short-lived "serverless function" with a time limit
> (~60s). So the web version is capped to a **small number of searches per run** (great for
> quick, targeted lookups). For big bulk scrapes of many cities at once, run the CLI locally
> (see SETUP_GUIDE.md) or deploy on Render instead (a always-on server with no short timeout).

---

## A) Fixing the Google key issue ("Places API not in the Restrict-key list")

This is normal. **The API-restriction dropdown only lists APIs you've already ENABLED in the
project.** If Places isn't there, it's because it isn't enabled yet (or hasn't propagated).

Do this in order:

1. Pick your project (top bar) at https://console.cloud.google.com
2. Left menu (☰) → **APIs & Services → Library**.
3. Search **Places API (New)** → open it → click **Enable**. (Enable this *exact* one — the
   one labelled **(New)**. The old "Places API" is different.)
4. Wait **1–5 minutes** (newly enabled APIs take a moment to show up).
5. Go to **APIs & Services → Credentials** → open your API key → under **API restrictions**
   choose **Restrict key**. Now **Places API (New)** should appear in the list → tick it → **Save**.

If it *still* doesn't appear:
- Just choose **"Don't restrict key"** for now and click Save — the key will work fine, you can
  add the restriction later once it shows up.
- Do **not** use the "HTTP referrers" application restriction for this — that only works for
  browser/JavaScript calls. This tool calls Google from a server, so use **API restriction**
  (or none).

> Also make sure **Billing** is enabled (☰ → Billing). Without billing the key returns
> `403 / PERMISSION_DENIED` even when everything else is correct.

---

## B) Deploy on Vercel (step by step)

### 1. Make sure the code is on GitHub
It already is: https://github.com/sanmol916/gap-finder (the scraper lives in `/gmb-leads`).

### 2. Create a Vercel account
1. Go to https://vercel.com → **Sign Up** → **Continue with GitHub** → authorize.

### 3. Import the project
1. Vercel dashboard → **Add New… → Project**.
2. Find **gap-finder** in the repo list → **Import**.

### 4. Deploy ONLY the scraper (important)
On the configuration screen:
1. Find **Root Directory** → click **Edit** → choose the **`gmb-leads`** folder → Continue.
   - This makes Vercel deploy *only* the scraper, ignoring the rest of the repo.
2. **Framework Preset:** leave as **Other** (Vercel auto-detects Python from `api/` + `requirements.txt`).
3. Leave Build/Output settings empty (the included `vercel.json` handles routing).

### 5. (Optional) Set your API key on the server
On the same screen (or later under **Settings → Environment Variables**) you can add:
- **Name:** `GOOGLE_MAPS_API_KEY`  **Value:** your key

> ⚠️ Only do this if you'll keep the URL **private**. A public Vercel URL with a server-side key
> means anyone who finds it can spend your Google quota. The safer default is to **leave it
> blank** and paste your key into the form each time you use it.

### 6. Deploy
Click **Deploy**, wait ~1 minute. You'll get a URL like `https://gmb-leads-xxxx.vercel.app`.

### 7. Use it
1. Open the URL.
2. Paste your Google API key (if you didn't set it as an env var).
3. Enter cities (e.g. `Guwahati, Shillong`) and categories (e.g. `beauty salon, dental clinic`).
4. Choose "Top 20 (cheapest)" for the first run → **Find no-website leads**.
5. Review the table → click **Download CSV** → import into Google Sheets if you like.

### 8. Updates are automatic
Any time this repo's `main` branch changes, Vercel redeploys automatically.

---

## Costs (same as the CLI)
- Small web runs (a few cities/categories, "Top 20") are usually **free** (inside Google's
  monthly allowance).
- Set a **budget alert** and a **daily quota cap** in Google Cloud so you can't overspend
  (see SETUP_GUIDE.md, Step 6).
- Vercel's Hobby plan is free for this.

## Troubleshooting
| Problem | Fix |
|---|---|
| `403 / PERMISSION_DENIED` in results | Enable **Places API (New)** + enable **Billing**; check key restriction. |
| Page times out on a big search | Too many cities/categories for serverless. Use fewer, or run the CLI locally. |
| "No API key" message | Paste the key in the form, or set `GOOGLE_MAPS_API_KEY` in Vercel env vars. |
| Build failed on Vercel | Confirm **Root Directory = gmb-leads** so Vercel finds `api/index.py` + `requirements.txt`. |

## Run it locally too (optional)
```bash
cd gmb-leads
pip install -r requirements.txt
python api/index.py        # open http://localhost:5000
```
