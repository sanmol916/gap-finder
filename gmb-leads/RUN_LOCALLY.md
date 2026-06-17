# Run gmb-leads on your own computer (NO cap, unlimited scraping)

The Vercel website is great for quick searches, but it has a time limit, so big runs get capped.
Running on your **own computer removes that limit** — you can scan whole states or all of India.

You have two local options:
- **Option A — the CLI (recommended for big runs).** Simplest, truly unlimited, saves a CSV **and** an Excel file.
- **Option B — the same web form, locally.** The familiar dropdown UI, with the cap switched off.

> This guide assumes you've **never used Python or a terminal**. Follow it top to bottom.
> First time ~20 min. After that, getting leads takes ~2 min.

---

## STEP 1 — Install Python

### Windows
1. Go to https://www.python.org/downloads/
2. Click the yellow **Download Python 3.x** button → open the file.
3. **IMPORTANT:** on the first screen, tick **"Add Python to PATH"** (bottom) **before** clicking **Install Now**.
4. Finish, then Close.

### Mac
1. https://www.python.org/downloads/ → download → install (keep clicking Continue/Install).

### Check it worked
- **Windows:** Start → type `cmd` → open **Command Prompt** → type `python --version`
- **Mac:** open **Terminal** → type `python3 --version`

You should see `Python 3.x`. (Windows "not recognized" = you missed the "Add to PATH" tick — re-run the installer.)

---

## STEP 2 — Download the tool
1. Open https://github.com/sanmol916/gap-finder
2. Green **"< > Code"** button → **Download ZIP**.
3. In your Downloads, **right-click → Extract All** (Windows) or double-click (Mac).
4. You now have a `gap-finder` folder. Inside it is the **`gmb-leads`** folder — that's what we use.

---

## STEP 3 — Open a terminal INSIDE the gmb-leads folder

### Windows
1. Open the `gap-finder` folder → open the `gmb-leads` folder.
2. Click the **address bar** at the top (where the folder path shows).
3. Type `cmd` and press **Enter**. A black window opens, already in the right place.

### Mac
1. Open **Terminal**.
2. Type `cd ` (with a space), then **drag the `gmb-leads` folder** into the Terminal window → press **Enter**.

Type `dir` (Windows) or `ls` (Mac) — you should see `find_leads.py` and `api`.

---

## STEP 4 — Install the dependencies (one time)

- **Windows:** `pip install -r requirements.txt`
- **Mac:** `pip3 install -r requirements.txt`

---

## STEP 5 — Have your Google API key ready
You already created it. You also need (see SETUP_GUIDE.md if not done):
- **Places API (New)** enabled, and **Billing** turned on (or you'll get a `403`).

Keep the key handy — you'll paste it into the commands below where it says `PASTE_YOUR_KEY`.

---

# OPTION A — The CLI (unlimited, best for big runs)

The CLI has **no cap at all**. It saves results to `gmb-leads/output/` as **CSV and Excel**.

> Below, use `python` on Windows and `python3` on Mac.

**A few cities + your own keywords:**
```
python find_leads.py --api-key "PASTE_YOUR_KEY" --cities Mumbai Pune --categories "beauty salon" "web design agency"
```

**A whole state (all its major cities):**
```
python find_leads.py --api-key "PASTE_YOUR_KEY" --states "Uttar Pradesh" --max-pages 3
```

**Several states:**
```
python find_leads.py --api-key "PASTE_YOUR_KEY" --states Maharashtra Karnataka "Tamil Nadu" --max-pages 3
```

**EVERYTHING — all of India (large; mind the cost):**
```
python find_leads.py --api-key "PASTE_YOUR_KEY" --all-india --max-pages 3
```

What the options mean:
- `--cities` exact cities (space separated; quote names with spaces).
- `--states` scans every preset city in those states.
- `--all-india` scans every city in `presets.json`.
- `--categories` your keywords (space separated, quote multi-word ones). Omit to use the presets.
- `--max-pages 3` pulls up to 60 results per search (the max). Use `1` for cheaper/faster.

**Your results:** open the `output` folder inside `gmb-leads`:
```
gmb-leads/output/india_no_website_leads.xlsx   (also .csv)
```
Double-click the `.xlsx`, or import the `.csv` into Google Sheets.

---

# OPTION B — The web form, locally (no cap)

Same dropdown UI you used on Vercel, but with the limit removed. The magic switch is the
environment variable **`GMB_UNCAPPED=1`**.

### Windows — Command Prompt (cmd)
Run these three lines in the terminal from STEP 3:
```
set GOOGLE_MAPS_API_KEY=PASTE_YOUR_KEY
set GMB_UNCAPPED=1
python api/index.py
```

### Windows — PowerShell
```
$env:GOOGLE_MAPS_API_KEY="PASTE_YOUR_KEY"
$env:GMB_UNCAPPED="1"
python api/index.py
```

### Mac / Linux
```
export GOOGLE_MAPS_API_KEY="PASTE_YOUR_KEY"
export GMB_UNCAPPED=1
python3 api/index.py
```

Then:
1. You'll see a line like `Running on http://127.0.0.1:5000`.
2. Open a browser and go to **http://localhost:5000**
3. The key box can stay empty (it's read from the env var). The form will say
   **"No per-run cap (local mode)"**.
4. Pick a State and/or cities, type your keywords, choose depth, click **Find no-website leads**,
   then **Download CSV**.
5. To stop the local server later, go back to the terminal and press **Ctrl + C**.

> Big runs may make the browser "spin" for a few minutes — that's normal locally (no timeout).
> Keep the terminal window open while you use the site.

---

## Keeping the cost sane
- Each search uses Google quota; big sweeps cost money. Set a **budget alert** + **daily quota cap**
  in Google Cloud (SETUP_GUIDE.md, Step 6) so you can't overspend.
- Start with one state and a few keywords. Scale up once you're happy.
- `--max-pages 1` (or "Top 20") is the cheapest; `3` (or "Top 60") gets the most per search.

## Troubleshooting
| Problem | Fix |
|---|---|
| `python is not recognized` (Windows) | Re-run the Python installer and tick **Add Python to PATH** (or try `py`). |
| `pip is not recognized` | Same as above; on Mac use `pip3`. |
| `403 / PERMISSION_DENIED` | Enable **Places API (New)** + **Billing**; check the key. |
| Browser can't open localhost | Make sure the terminal still shows the server running; use `http://localhost:5000`. |
| Run feels stuck | Big uncapped runs take minutes — watch the terminal; it prints each search. |
| `No module named flask` | Re-run `pip install -r requirements.txt` in the `gmb-leads` folder. |
