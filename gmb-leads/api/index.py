#!/usr/bin/env python3
"""
Vercel-deployable web app for the gmb-leads scraper (ALL INDIA).

Vercel serves this file as a Python serverless function (it exposes a WSGI
`app`). The catch-all rewrite in vercel.json sends every path here, and Flask
routes internally. It reuses the CLI engine in ../find_leads.py.

KEY HANDLING
  - If GOOGLE_MAPS_API_KEY is set on the server (Vercel env var), it's used
    automatically and the form key box can stay empty ("permanent" key).
  - Otherwise paste a key into the form each run.

PLACE SELECTION
  - Pick a STATE (scans its major cities) and/or multi-select specific CITIES
    from the dropdown (grouped by state). Covers all India from presets.json.

SERVERLESS LIMITS
  Vercel functions have a max duration (~60s). The web version caps how many
  city x category searches run at once. For full-India / bulk scrapes, run the
  CLI locally (see SETUP_GUIDE.md) - it has no time limit.
"""

from __future__ import annotations

import os
import sys
import csv
import io
import base64

from flask import Flask, request, render_template_string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import find_leads as fl  # noqa: E402

app = Flask(__name__)

# Time budget caps (queries per run) so we stay under the serverless limit.
CAPS = {1: 40, 2: 16, 3: 10}
DEFAULT_CATEGORIES = ["beauty salon", "dental clinic", "real estate agent",
                      "gym / fitness center", "clothing boutique"]


def _query_cap(pages: int):
    """Per-run search cap. Returns None (no cap) when running locally/uncapped.

    Set GMB_UNCAPPED=1 (recommended for local runs) to remove the cap entirely,
    or GMB_MAX_QUERIES=<number> for a custom limit. On Vercel, leave these unset
    so the serverless time limit isn't exceeded.
    """
    if os.environ.get("GMB_UNCAPPED", "").lower() in ("1", "true", "yes"):
        return None
    override = os.environ.get("GMB_MAX_QUERIES", "")
    if override.isdigit():
        return int(override)
    return CAPS[pages]

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GMB Leads - businesses with no website (India)</title>
<style>
 :root{--bg:#0f1115;--card:#181b22;--line:#272b35;--text:#e6e8ec;--muted:#9aa3b2;--accent:#5b8cff;--accent2:#1f6feb;--warn:#ffb84d;--good:#3fb950}
 *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
 .wrap{max-width:1040px;margin:0 auto;padding:26px 16px 80px}
 h1{font-size:24px;margin:0 0 4px}h1 .dot{color:var(--accent)}
 .sub{color:var(--muted);margin:0 0 18px}
 form{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:20px}
 label{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:0 0 5px}
 input,select{width:100%;background:#0d0f14;border:1px solid var(--line);color:var(--text);border-radius:9px;padding:10px 12px;font-size:15px}
 select[multiple]{padding:4px}
 .field{margin-top:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
 @media(max-width:640px){.grid{grid-template-columns:1fr}}
 button{margin-top:16px;background:var(--accent2);color:#fff;border:0;border-radius:9px;padding:12px 22px;font-size:15px;font-weight:600;cursor:pointer}
 button:hover{background:var(--accent)}
 .note{font-size:12.5px;color:var(--muted);margin-top:8px}
 .keyok{background:#11281b;border:1px solid #1f5133;color:var(--good);border-radius:9px;padding:8px 12px;font-size:13px;margin-bottom:6px}
 .err{background:#2a1d12;border:1px solid #5a3c1a;color:var(--warn);border-radius:10px;padding:10px 14px;margin:14px 0}
 .ok{background:#11281b;border:1px solid #1f5133;color:var(--good);border-radius:10px;padding:10px 14px;margin:14px 0}
 table{width:100%;border-collapse:collapse;margin-top:14px;font-size:13.5px}
 th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
 th{color:var(--muted);font-weight:600}
 a{color:var(--accent);text-decoration:none}
 .dl{display:inline-block;margin:14px 0;background:#11281b;border:1px solid #1f5133;color:var(--good);padding:9px 16px;border-radius:9px;font-weight:600}
 .pill{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px;color:var(--muted);margin-right:8px}
 .pill b{color:var(--text)}
 footer{margin-top:34px;color:var(--muted);font-size:12.5px}
</style></head><body><div class="wrap">
<h1>GMB Leads<span class="dot">.</span></h1>
<p class="sub">Find local businesses across <b>India</b> that have <b>no website</b> - via the official Google Places API.</p>

<form method="get" action="/">
  {% if server_key %}
    <div class="keyok">&#10003; A permanent API key is configured on the server - you can leave the box below empty.</div>
  {% endif %}
  <label for="api_key">Google API key (Places API New){{ ' - optional, server key set' if server_key else '' }}</label>
  <input type="password" id="api_key" name="api_key" placeholder="{{ 'leave blank to use the server key' if server_key else 'paste your key' }}">

  <div class="grid field">
    <div>
      <label for="state">State / UT (scans its major cities)</label>
      <select id="state" name="state">
        <option value="">- choose a state (optional) -</option>
        {% for st in states.keys() %}<option value="{{ st }}" {{ 'selected' if state==st else '' }}>{{ st }}</option>{% endfor %}
      </select>
      <div class="note">Pick a state to scan its cities, and/or multi-select exact cities &rarr;</div>
    </div>
    <div>
      <label for="max_pages">Results depth per search</label>
      <select id="max_pages" name="max_pages">
        <option value="1" {{ 'selected' if pages==1 else '' }}>Top 20 (cheapest, most queries)</option>
        <option value="2" {{ 'selected' if pages==2 else '' }}>Top 40</option>
        <option value="3" {{ 'selected' if pages==3 else '' }}>Top 60 (deepest)</option>
      </select>
    </div>
  </div>

  <div class="field">
    <label for="cities">Cities (hold Ctrl / Cmd to pick several)</label>
    <select id="cities" name="cities" multiple size="12">
      {% for st, cs in states.items() %}
      <optgroup label="{{ st }}">
        {% for c in cs %}<option value="{{ c }}" {{ 'selected' if c in sel_cities else '' }}>{{ c }}</option>{% endfor %}
      </optgroup>
      {% endfor %}
    </select>
  </div>

  <div class="field">
    <label for="categories">Search keywords / business types (type ANYTHING, comma separated)</label>
    <input type="text" id="categories" name="categories" value="{{ cats_text|e }}"
           list="catlist" placeholder="e.g. beauty salon, web design agency, scrap dealer, gym">
    <datalist id="catlist">
      {% for cat in categories_all %}<option value="{{ cat }}">{% endfor %}
    </datalist>
    <div class="note">Pick from the suggestions as you type, or enter your own keywords - search whatever you want.</div>
  </div>

  <button type="submit" name="run" value="1">Find no-website leads</button>
  <div class="note">{% if cap %}Capped to {{ cap }} searches per web run to stay fast (serverless limit). For unlimited runs, run locally with GMB_UNCAPPED=1 - see SETUP_GUIDE.md.{% else %}No per-run cap (local mode) - large runs may take several minutes; that's normal.{% endif %}</div>
</form>

{% if error %}<div class="err">{{ error }}</div>{% endif %}
{% if trimmed %}<div class="err">Selection was large - trimmed to the first {{ cap }} city &times; category searches. Run again with another batch, or use the local CLI for everything at once.</div>{% endif %}

{% if ran %}
  <div class="ok">Scanned {{ total }} businesses across {{ nqueries }} searches - <b>{{ leads|length }}</b> have no website.</div>
  <span class="pill">Businesses <b>{{ total }}</b></span>
  <span class="pill">No-website leads <b>{{ leads|length }}</b></span>
  {% if csv_data %}<a class="dl" download="india_no_website_leads.csv" href="data:text/csv;base64,{{ csv_data }}">&darr; Download CSV</a>{% endif %}
  {% if leads %}
  <table>
    <tr><th>Business</th><th>Category</th><th>City</th><th>State</th><th>Phone</th><th>Address</th><th>Rating</th><th>Maps</th></tr>
    {% for r in leads %}
    <tr>
      <td>{{ r.business_name }}</td><td>{{ r.category }}</td><td>{{ r.city }}</td><td>{{ r.state }}</td>
      <td>{{ r.phone }}</td><td>{{ r.address }}</td>
      <td>{{ r.rating }}{% if r.reviews %} ({{ r.reviews }}){% endif %}</td>
      <td>{% if r.maps_url %}<a href="{{ r.maps_url }}" target="_blank" rel="noopener">open</a>{% endif %}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}<p class="note">No no-website businesses found for that search. Try other cities/categories.</p>{% endif %}
{% endif %}

<footer>Uses the official Google Places API (New) - not scraping. If you set a server-side key, keep this URL private (anyone with it could spend your quota).</footer>
</div></body></html>"""


def _presets():
    return fl.load_presets()


def _city_state_map(states: dict) -> dict:
    m = {}
    for state, cities in states.items():
        for c in cities:
            m[c.lower()] = state
    return m


def _csv_b64(rows: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fl.COLUMNS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fl.COLUMNS})
    return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")


@app.route("/", methods=["GET"])
def index():
    presets = _presets()
    states = presets["states"]
    categories_all = presets["categories"]
    server_key = bool(os.environ.get("GOOGLE_MAPS_API_KEY"))
    pages = int(request.args.get("max_pages", 1) or 1)
    pages = max(1, min(3, pages))
    cap = _query_cap(pages)

    ctx = {
        "states": states, "categories_all": categories_all, "server_key": server_key,
        "state": request.args.get("state", ""),
        "sel_cities": request.args.getlist("cities"),
        "cats_text": request.args.get("categories", ", ".join(DEFAULT_CATEGORIES)),
        "pages": pages, "cap": cap,
        "ran": False, "error": None, "trimmed": False,
        "leads": [], "total": 0, "nqueries": 0, "csv_data": "",
    }

    if request.args.get("run") != "1":
        return render_template_string(PAGE, **ctx)

    api_key = (request.args.get("api_key") or "").strip() or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        ctx["error"] = "No API key. Paste your Google Places API key, or set GOOGLE_MAPS_API_KEY on the server."
        return render_template_string(PAGE, **ctx)

    # Resolve which cities to search.
    cities = list(ctx["sel_cities"])
    if not cities and ctx["state"] and ctx["state"] in states:
        cities = list(states[ctx["state"]])
    if not cities:
        ctx["error"] = "Choose a state (to scan its cities) and/or pick cities from the dropdown."
        return render_template_string(PAGE, **ctx)

    cats = [c.strip() for c in ctx["cats_text"].replace("\n", ",").split(",") if c.strip()] or DEFAULT_CATEGORIES
    cs_map = _city_state_map(states)

    queries = []
    for city in cities:
        st = cs_map.get(city.lower(), ctx["state"] or "")
        for cat in cats:
            queries.append((city, st, cat))
    if cap is not None and len(queries) > cap:
        queries = queries[:cap]
        ctx["trimmed"] = True

    seen, all_rows = set(), []
    for city, st, cat in queries:
        loc = f"{city}, {st}, India" if st else f"{city}, India"
        q = f"{cat} in {loc}"
        try:
            places = fl.search_text(api_key, q, max_pages=pages)
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = f"Search failed: {exc}"
            break
        for row in fl.extract_rows(places, city, st, cat):
            pid = row["place_id"]
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            all_rows.append(row)

    leads = [r for r in all_rows if not r.get("_website")]
    ctx.update(ran=True, leads=leads, total=len(all_rows),
               nqueries=len(queries), csv_data=_csv_b64(leads) if leads else "")
    return render_template_string(PAGE, **ctx)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
