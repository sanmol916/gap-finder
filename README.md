# gap-finder

Mine **Reddit** and **App Store reviews** for unmet needs (market gaps) in any niche.
It scans real user complaints for "demand signals" — *"I wish there was..."*, *"is there an app
that..."*, *"why is there no..."*, *"such a pain"*, *"no way to..."* — pulls out the exact pain
quote, scores it by signal strength × popularity, and writes a ranked Markdown report.

Optionally clusters everything into named pain themes + product ideas with an LLM.

## Why
You don't guess market gaps — you mine them. People describe missing products in
predictable language. This tool finds that language at scale so you can spot patterns,
then validate the strongest ones with real users before building.

## Install
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage (CLI)
```bash
# basic
.venv/bin/python main.py "youth sports scorekeeping"

# focus subreddits + pull more data
.venv/bin/python main.py "meal planning" \
    --subreddits mealprep nutrition EatCheapAndHealthy \
    --reddit-limit 80 --review-pages 6

# enable AI theme clustering (needs OPENAI_API_KEY)
.venv/bin/python main.py "dog training app" --llm

# App Store only, custom output path
.venv/bin/python main.py "rent pg hostel" --no-reddit --out reports/pg.md
```

Output: a Markdown file (default `<slug>-gap-report.md`) with:
- summary stats
- AI-clustered pain themes + product ideas (if `--llm`)
- top pain quotes ranked by `signal × popularity`, each linked to its source
- signal-phrase frequency table + recurring keywords

## Enabling Reddit (recommended)
Reddit blocks datacenter/cloud IPs on its public `.json` endpoints (you'll see `http 403`).
On your own machine it often works, but the reliable path is the free official API:

1. Go to <https://www.reddit.com/prefs/apps> → "create another app" → type **script**.
2. Copy the **client id** (under the app name) and the **secret**.
3. Export them before running:
   ```bash
   export REDDIT_CLIENT_ID="your_id"
   export REDDIT_CLIENT_SECRET="your_secret"
   ```
The tool auto-detects these and switches to the OAuth API. App Store works with no keys.

## Enabling LLM clustering (optional)
```bash
export OPENAI_API_KEY="sk-..."
# optional: point at any OpenAI-compatible endpoint / model
export OPENAI_BASE_URL="https://api.openai.com/v1"
export GAPFINDER_MODEL="gpt-4o-mini"
.venv/bin/python main.py "your niche" --llm
```

## Key options
| Flag | Meaning |
|---|---|
| `--subreddits a b c` | restrict Reddit to specific subreddits |
| `--reddit-limit N` | max posts per Reddit search (default 50) |
| `--time week\|month\|year\|all` | Reddit time window |
| `--no-comments` | skip Reddit comments (faster) |
| `--no-reddit` / `--no-appstore` | disable a source |
| `--appstore-apps N` | how many related apps to pull reviews from |
| `--review-pages N` | review pages per app (~50 reviews each) |
| `--min-score F` | drop weak findings below this score |
| `--top N` | how many quotes to show in the report |
| `--llm` | cluster findings into themes (needs key) |
| `--out PATH` | output markdown path |

## How scoring works
- Each complaint phrase has a **strength** (e.g. `"why is there no"` = 3.2, `"annoying"` = 1.2).
- Each source item has a **weight**: Reddit by upvotes; App Store by star rating
  (1★ reviews weigh ~3×, 5★ ~0.4× — negative reviews describe what's missing).
- `finding score = phrase strength × item weight`. Higher = stronger evidence of a real gap.

## Extending
Add new sources by returning the same normalised item dict from `sources.py`:
```python
{"source": "...", "kind": "...", "title": "...", "text": "...",
 "url": "...", "weight": 1.0, "meta": {}}
```
Good next sources: Google Play reviews, Yelp/Google business reviews, G2/Capterra (B2B),
Hacker News, Product Hunt comments, Trustpilot.

## Important
- Respect each platform's Terms of Service and rate limits.
- Treat findings as **leads, not proof**. Validate a promising theme by talking to
  10+ real users (or a landing page with a waitlist) before you build anything.

---

## Web app (run it in a browser)

The repo also ships a small Flask UI so you (or clients) can run searches without the terminal.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py          # open http://localhost:5000
```

Endpoints:
- `/` &mdash; search form + ranked results
- `/report.md?q=your+niche` &mdash; download the Markdown report
- `/healthz` &mdash; health check (used by the host)

Production server (what the host runs):
```bash
gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
```

## Deploy free on Render (recommended)

Render reads the included `render.yaml` blueprint automatically.

1. Push this repo to GitHub (done if you're reading this there).
2. Create a free account at <https://render.com> and connect your GitHub.
3. Click **New +** &rarr; **Blueprint** &rarr; select this repo &rarr; **Apply**.
   Render detects `render.yaml`, builds with `pip install -r requirements.txt`,
   and starts with gunicorn on the free plan.
4. (Optional but recommended) In the service's **Environment** tab add:
   - `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` &rarr; enables Reddit (see above)
   - `OPENAI_API_KEY` &rarr; enables the "AI cluster" checkbox
5. Open the live URL Render gives you (e.g. `https://gap-finder.onrender.com`).

> Free tier note: the service sleeps after ~15 min idle, so the first request
> after a nap takes ~30-60s to wake up. Keep `Apps to scan` / `Review pages` modest
> so a search finishes within the request window.

### Without a blueprint (manual)
New + &rarr; **Web Service** &rarr; pick the repo &rarr; set:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT`
- **Instance Type:** Free

## Deploy free elsewhere (same files work)

- **Railway** &mdash; New Project &rarr; Deploy from GitHub. It auto-detects Python and uses the `Procfile`. Add env vars in **Variables**. (Free trial credit.)
- **Fly.io** &mdash; `fly launch` (uses the `Procfile`); generous free allowance.
- **PythonAnywhere** &mdash; free tier; upload the repo and point a web app at `app:app`.
- **Hugging Face Spaces** &mdash; free; create a "Gradio/Docker/Flask" space and add these files.

All of them read the same `Procfile` / start command, so no code changes are needed.
