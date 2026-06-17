# gmb-leads — Beginner Setup Guide (step by step)

This guide assumes you've **never used Python, the terminal, or Google Cloud before**.
Follow it top to bottom. By the end you'll have a spreadsheet of North East India businesses
that have **no website** (your sales leads).

> Time needed: ~25–30 minutes the first time. After that, getting fresh leads takes ~2 minutes.

---

## What you'll end up with
A file like `ne_india_no_website_leads.xlsx` with columns:
business name, category, city, state, phone, address, Google Maps link, rating, reviews, status.
Every row is a business with **no website** — someone you can call/visit to sell a website to.

---

## STEP 0 — Will this cost money?
- You must add a card to Google (required), but there's a **monthly free allowance**.
- **Small runs are effectively free.** A big "scan everything" run can cost a few dollars.
- In STEP 6 you'll set a **spending cap** so you can never be surprised.

---

## STEP 1 — Install Python (the engine the tool runs on)

### Windows
1. Go to https://www.python.org/downloads/
2. Click the big yellow **"Download Python 3.x"** button.
3. Open the downloaded file.
4. **VERY IMPORTANT:** on the first screen, tick the box **"Add Python to PATH"** (bottom of the window) BEFORE clicking Install.
5. Click **Install Now** → wait → Close.

### Mac
1. Go to https://www.python.org/downloads/ → download → install (just keep clicking Continue/Install).

### Check it worked
- **Windows:** press the Start button, type `cmd`, open **Command Prompt**. Type:
  ```
  python --version
  ```
- **Mac:** open **Terminal** (Cmd+Space, type "Terminal"). Type:
  ```
  python3 --version
  ```
You should see something like `Python 3.12.x`. If you get "not found" on Windows, you missed
the "Add Python to PATH" tick — re-run the installer and tick it.

---

## STEP 2 — Download the tool

**Easiest way (no git needed):**
1. Open https://github.com/sanmol916/gap-finder
2. Click the green **"< > Code"** button → **Download ZIP**.
3. Find the ZIP in your Downloads, **right-click → Extract All** (Windows) or double-click (Mac).
4. You now have a folder `gap-finder` (or `gap-finder-main`). Inside it is a folder `gmb-leads`.

---

## STEP 3 — Open the terminal *inside the gmb-leads folder*

This is the step beginners find tricky. Pick your OS:

### Windows
1. Open the `gap-finder` (or `gap-finder-main`) folder, then open the `gmb-leads` folder.
2. Click in the address bar at the top of the window (where the folder path is shown).
3. Type `cmd` and press **Enter**. A black Command Prompt window opens, already in the right folder.

### Mac
1. Open **Terminal**.
2. Type `cd ` (with a space), then **drag the `gmb-leads` folder** into the Terminal window, then press **Enter**.

> Tip: to confirm you're in the right place, type `dir` (Windows) or `ls` (Mac). You should see
> `find_leads.py`, `presets.json`, `requirements.txt`.

---

## STEP 4 — Install the tool's dependencies

In that same terminal window, type:

- **Windows:**
  ```
  pip install -r requirements.txt
  ```
- **Mac:**
  ```
  pip3 install -r requirements.txt
  ```
Wait for it to finish (it downloads a couple of small libraries).

---

## STEP 5 — Test it works WITHOUT spending anything

Type:
- **Windows:** `python find_leads.py --self-test`
- **Mac:** `python3 find_leads.py --self-test`

You should see **`SELF-TEST PASSED`**. This proves Python + the tool are installed correctly.
It made **zero** Google calls, so it's completely free.

---

## STEP 6 — Get your Google API key (the part that talks to Google)

1. Go to https://console.cloud.google.com and sign in with a Google account.
2. **Create a project:** top-left, click the project dropdown → **New Project** → name it
   `gmb-leads` → **Create**. Wait a few seconds, then make sure that project is selected
   in the top bar.
3. **Turn on billing:** left menu (☰) → **Billing** → **Link a billing account** (or create one)
   → add your card. *(Google won't charge unless you exceed the free allowance.)*
4. **Enable the API:** left menu → **APIs & Services → Library**. In the search box type
   **Places API (New)**. Click the result that says **Places API (New)** → click **Enable**.
   - ⚠️ Make sure it says **(New)**. Don't pick the old "Places API".
5. **Create the key:** left menu → **APIs & Services → Credentials** → top button
   **+ Create Credentials → API key**. The **"Create API key"** screen opens — set it like this:
   - **Name:** anything (e.g. `gmb-leads`).
   - **"Authenticate API calls through a service account"** → **leave this UNCHECKED.**
     (That checkbox is only for Vertex AI / Gemini — not for Places. Ignore the blue info box.)
   - **"Select API restrictions" (dropdown says "No APIs selected"):** this list shows **only
     APIs already enabled in your project.** So:
       - If you did STEP 6.4 (enabled **Places API (New)**), open the dropdown and tick it. If it
         isn't there yet, wait 1–5 min and reopen this screen.
       - If you haven't enabled it yet, **just leave it on "No APIs selected" and click Create now.**
         The key will be *unrestricted* but fully working — you can add the restriction later.
   - **"Application restrictions"** → choose **None.**
     ⚠️ Do **not** pick "Websites" or "IP addresses" — this tool calls Google from a server / your
     computer, not from a browser, so those would **block** it. **None** is the correct choice here.
   - Click **Create** → a box shows your key → click **Copy** and paste it somewhere safe.

   > Creating a key does **not** enable any API by itself. You must enable **Places API (New)**
   > in the API Library (STEP 6.4). If you skipped it, do it now or the key returns `403`.
6. **Lock the key down later (optional safety):** once **Places API (New)** is enabled, open the
   key from the Credentials list → **API restrictions → Restrict key** → tick **Places API (New)**
   → **Save**. Now the key can only be used for this one thing.

### Set a spending cap so you can't be surprised
1. **Budget alert:** left menu → **Billing → Budgets & alerts → Create budget** → set amount
   to e.g. **$5** → enable email alerts → Finish.
2. **Hard daily limit:** left menu → **APIs & Services → Places API (New) → Quotas**. Find the
   "Requests per day" quota and set it low, e.g. **500**. When reached, the tool just stops —
   it does not keep charging.

---

## STEP 7 — Run a small real search

Now use your key. The **simplest** way for a beginner is to paste the key right into the command
with `--api-key`. Replace `PASTE_YOUR_KEY_HERE` with the key you copied:

- **Windows:**
  ```
  python find_leads.py --api-key "PASTE_YOUR_KEY_HERE" --cities Guwahati Shillong --categories "beauty salon" "dental clinic"
  ```
- **Mac:**
  ```
  python3 find_leads.py --api-key "PASTE_YOUR_KEY_HERE" --cities Guwahati Shillong --categories "beauty salon" "dental clinic"
  ```

You'll see it print each search, then a summary like
`Collected 80 unique businesses; 47 have NO website.`

---

## STEP 8 — Open your leads sheet

In the `gmb-leads` folder you'll now find a new folder **`output`** containing:
```
ne_india_no_website_leads.xlsx
ne_india_no_website_leads.csv
```
- Double-click the **.xlsx** to open it in Excel, OR
- Import the **.csv** into Google Sheets: in Google Sheets → **File → Import → Upload** → pick the file.

That's your call list.

---

## STEP 9 — Scale up when you're ready

```
# one whole state
python find_leads.py --api-key "PASTE_YOUR_KEY_HERE" --states Assam

# the full North East India preset (bigger run - costs more, see below)
python find_leads.py --api-key "PASTE_YOUR_KEY_HERE"

# cheaper mode: only top 20 results per search (about 3x fewer API calls)
python find_leads.py --api-key "PASTE_YOUR_KEY_HERE" --cities Guwahati --max-pages 1
```

To change which cities/categories are searched, open **`presets.json`** in any text editor
(Notepad works) and add or remove lines.

---

## STEP 10 — Costs in plain words
- **Tiny/targeted run** (a few cities + categories) = usually **free** (inside the monthly allowance).
- **Full 22-city run** = roughly **$50–65** at most before the free allowance, often less.
- The price per request and free amount change over time — check
  https://mapsplatform.google.com/pricing/ before a big run.
- Use `--max-pages 1`, fewer cities, and the quota cap to keep it near zero.

---

## Troubleshooting (common beginner errors)

| You see... | What it means / fix |
|---|---|
| `python is not recognized` (Windows) | Python isn't on PATH. Re-run the Python installer and tick **"Add Python to PATH"**. Or try `py` instead of `python`. |
| `pip is not recognized` | Same fix as above. On Mac use `pip3`. |
| `ERROR: no API key` | You didn't pass `--api-key "..."` (or the key has a typo). |
| `[http 403]` or `PERMISSION_DENIED` | The **Places API (New)** isn't enabled, billing isn't on, or the key restriction is blocking it. Recheck STEP 6. |
| `[http 429]` | You hit a rate limit; the tool waits and retries automatically. If it persists, run fewer queries. |
| No `output` folder appears | The run errored before finishing — read the message printed in the terminal. |
| Can't find the folder in terminal | Re-do STEP 3 carefully; type `dir`/`ls` to confirm you see `find_leads.py`. |

---

## Safety reminders
- **Never share your API key** or post it online. If it leaks, delete it in Credentials and make a new one.
- Keep the **quota cap** on so spending is physically limited.
- Use the leads to **contact businesses directly** — don't resell raw Google data.
