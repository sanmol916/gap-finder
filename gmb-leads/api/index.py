#!/usr/bin/env python3
"""
Vercel-deployable web app for the gmb-leads scraper.

Vercel serves this file as a Python serverless function (it exposes a WSGI
`app`). The catch-all rewrite in vercel.json sends every path here, and Flask
routes internally.

It reuses the CLI engine in ../find_leads.py (search_text / extract_rows).

IMPORTANT - serverless time limits:
  Vercel functions have a max duration (~60s on Hobby). So the web version is
  capped to a SMALL number of queries per run. For big bulk scrapes, run the
  CLI locally (see SETUP_GUIDE.md).

Run locally for testing:
  pip install -r requirements.txt
  python api/index.py            # http://localhost:5000
"""

from __future__ import annotations

import os
import sys
import csv
import base64
import io

from flask import Flask, request, render_template_string

# Make the parent folder importable so we can reuse the CLI engine.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import find_leads as fl  # noqa: E402

app = Flask(__name__)

# Keep runs inside the serverless time budget.
MAX_QUERIES_1PAGE = 15
MAX_QUERIES_MULTIPAGE = 6
DEFAULT_CATEGORIES = ["beauty salon", "dental clinic", "real estate agent",
                      "gym / fitness center", "clothing boutique"]

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GMB Leads - businesses with no website (NE India)</title>
<style>
 :root{--bg:#0f1115;--card:#181b22;--line:#272b35;--text:#e6e8ec;--muted:#9aa3b2;--accent:#5b8cff;--accent2:#1f6feb;--warn:#ffb84d;--good:#3fb950}
 *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
 .wrap{max-width:1000px;margin:0 auto;padding:26px 16px 80px}
 h1{font-size:24px;margin:0 0 4px}h1 .dot{color:var(--accent)}
 .sub{color:var(--muted);margin:0 0 20px}
 form{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:20px}
 label{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:0 0 5px}
 input,select{width:100%;background:#0d0f14;border:1px solid var(--line);color:var(--text);border-radius:9px;padding:11px 12px;font-size:15px}
 .field{margin-top:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
 button{margin-top:16px;background:var(--accent2);color:#fff;border:0;border-radius:9px;padding:12px 22px;font-size:15px;font-weight:600;cursor:pointer}
 button:hover{background:var(--accent)}
 .note{font-size:12.5px;color:var(--muted);margin-top:8px}
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
<p class="sub">Find local businesses with <b>no website</b> (North East India) via the official Google Places API.</p>

<form method="get" action="/">
  <label for="api_key">Google API key (Places API New)</label>
  <input type="password" id="api_key" name="api_key" placeholder="paste your key (or set GOOGLE_MAPS_API_KEY on the server)" value="{{ api_key_shown }}">
  <div class="grid field">
    <div><label for="cities">Cities (comma separated)</label>
      <input type="text" id="cities" name="cities" value="{{ cities|e }}" placeholder="Guwahati, Shillong"></div>
    <div><label for="max_pages">Results depth</label>
      <select id="max_pages" name="max_pages">
        <option value="1" {{ 'selected' if pages==1 else '' }}>Top 20 (cheapest)</option>
        <option value="2" {{ 'selected' if pages==2 else '' }}>Top 40</option>
        <option value="3" {{ 'selected' if pages==3 else '' }}>Top 60</option>
      </select></div>
  </div>
  <div class="field"><label for="categories">Categories (comma separated)</label>
    <input type="text" id="categories" name="categories" value="{{ categories|e }}" placeholder="beauty salon, dental clinic, real estate agent"></div>
  <button type="submit" name="run" value="1">Find no-website leads</button>
  <div class="note">Serverless runs are capped to keep them fast. For big bulk scrapes, run the CLI locally (see SETUP_GUIDE.md).</div>
</form>

{% if error %}<div class="err">{{ error }}</div>{% endif %}
{% if trimmed %}<div class="err">Too many city x category combinations for one web run - trimmed to {{ max_q }} queries. Use the local CLI for bigger jobs.</div>{% endif %}

{% if ran %}
  <div class="ok">Scanned {{ total }} businesses across {{ nqueries }} searches - <b>{{ leads|length }}</b> have no website.</div>
  <span class="pill">Businesses <b>{{ total }}</b></span>
  <span class="pill">No-website leads <b>{{ leads|length }}</b></span>
  {% if csv_data %}<a class="dl" download="ne_india_no_website_leads.csv" href="data:text/csv;base64,{{ csv_data }}">&darr; Download CSV</a>{% endif %}
  {% if leads %}
  <table>
    <tr><th>Business</th><th>Category</th><th>City</th><th>Phone</th><th>Address</th><th>Rating</th><th>Maps</th></tr>
    {% for r in leads %}
    <tr>
      <td>{{ r.business_name }}</td><td>{{ r.category }}</td><td>{{ r.city }}</td>
      <td>{{ r.phone }}</td><td>{{ r.address }}</td>
      <td>{{ r.rating }}{% if r.reviews %} ({{ r.reviews }}){% endif %}</td>
      <td>{% if r.maps_url %}<a href="{{ r.maps_url }}" target="_blank" rel="noopener">open</a>{% endif %}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}<p class="note">No no-website businesses found for that search. Try other cities/categories.</p>{% endif %}
{% endif %}

<footer>Uses the official Google Places API (New) - not scraping. Keep this URL private if you set a server-side key, or require visitors to paste their own.</footer>
</div></body></html>"""


def _city_state_map() -> dict:
    presets = fl.load_presets()
    m = {}
    for state, cities in presets["states"].items():
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
    ctx = {
        "api_key_shown": "", "cities": request.args.get("cities", "Guwahati"),
        "categories": request.args.get("categories", ", ".join(DEFAULT_CATEGORIES)),
        "pages": int(request.args.get("max_pages", 1) or 1),
        "ran": False, "error": None, "trimmed": False, "leads": [], "total": 0,
        "nqueries": 0, "csv_data": "", "max_q": MAX_QUERIES_1PAGE,
    }
    if request.args.get("run") != "1":
        return render_template_string(PAGE, **ctx)

    api_key = (request.args.get("api_key") or "").strip() or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        ctx["error"] = "No API key. Paste your Google Places API key, or set GOOGLE_MAPS_API_KEY on the server."
        return render_template_string(PAGE, **ctx)

    pages = max(1, min(3, ctx["pages"]))
    max_q = MAX_QUERIES_1PAGE if pages == 1 else MAX_QUERIES_MULTIPAGE
    ctx["max_q"] = max_q

    cities = [c.strip() for c in ctx["cities"].replace("\n", ",").split(",") if c.strip()]
    cats = [c.strip() for c in ctx["categories"].replace("\n", ",").split(",") if c.strip()]
    if not cities:
        cities = ["Guwahati"]
    if not cats:
        cats = DEFAULT_CATEGORIES

    cs_map = _city_state_map()
    queries = []
    for city in cities:
        state = cs_map.get(city.lower(), "")
        for cat in cats:
            queries.append((city, state, cat))
    if len(queries) > max_q:
        queries = queries[:max_q]
        ctx["trimmed"] = True

    seen, all_rows = set(), []
    for city, state, cat in queries:
        loc = f"{city}, {state}, India" if state else f"{city}, India"
        q = f"{cat} in {loc}"
        try:
            places = fl.search_text(api_key, q, max_pages=pages)
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = f"Search failed: {exc}"
            break
        for row in fl.extract_rows(places, city, state, cat):
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
