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

### On the "Create API key" pop-up specifically
If you're on the **Create API key** screen and the dropdown says **"No APIs selected"**, that's
normal (the list only shows APIs you've enabled). Just set it like this and you're good:
- **Authenticate API calls through a service account** → **leave UNCHECKED** (that's only for
  Vertex/Gemini, not Places).
- **Select API restrictions** → pick **Places API (New)** if it's listed; if not, leave it and
  restrict later.
- **Application restrictions** → **None** (server-side calls — "Websites"/"IP addresses" would
  block it).
- Click **Create**, copy the key. Then make sure **Places API (New)** is enabled in the API
  Library, or the key returns `403`.

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

### 5. Make your API key PERMANENT (recommended)
So you never paste the key again, store it on the server:
1. During import (or later: **Project → Settings → Environment Variables**) add:
   - **Key/Name:** `GOOGLE_MAPS_API_KEY`
   - **Value:** your Google key
   - Apply to **Production** (and Preview if you want).
2. Save and (if added later) **redeploy**.
3. Now the app shows "&#10003; A permanent API key is configured on the server" and the form's
   key box can stay empty forever.

> ⚠️ **Keep the URL private** when you do this. A public URL + a server-side key means anyone who
> finds it can spend your Google quota. Either keep the link to yourself, or turn on Vercel
> **Deployment Protection** (Project → Settings → Deployment Protection → *Vercel Authentication*),
> which requires a Vercel login to open the site. If you'd rather not store the key, just skip
> this step and paste the key into the form each time.

### 6. Deploy
Click **Deploy**, wait ~1 minute. You'll get a URL like `https://gmb-leads-xxxx.vercel.app`.

### 7. Use it
1. Open the URL.
2. Paste your Google API key (skip this if you set it as a permanent env var in step 5).
3. **Pick a State** from the dropdown (it scans that state's major cities) **and/or multi-select
   specific Cities** from the grouped dropdown (Ctrl/Cmd-click for several). Then **type your search
   keywords / business types** in the keyword box — anything you want, comma separated (preset
   suggestions appear as you type).
4. Choose "Top 20 (cheapest)" for the first run → **Find no-website leads**.
5. Review the table → click **Download CSV** → import into Google Sheets if you like.

> Covers **all of India** (36 states/UTs, ~185 major cities). The web app caps how many searches
> run at once (serverless time limit). For a full-India sweep in one go, use the local CLI:
> `python find_leads.py --all-india` (see SETUP_GUIDE.md).

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
