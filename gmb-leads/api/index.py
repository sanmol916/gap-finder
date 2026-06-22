#!/usr/bin/env python3
"""
Worldwide web app for the gmb-leads scraper.

Type ANY places in the world (multiple, no limit) + keywords, and get back two
lists: businesses WITHOUT a website and businesses WITH a website - each with its
own CSV download. Reuses the CLI engine in ../find_leads.py.

KEY HANDLING
  - If GOOGLE_MAPS_API_KEY is set on the server (Vercel env var), it's used
    automatically and the form key box can stay empty ("permanent" key).
  - Otherwise paste a key into the form each run.

PLACE SELECTION
  - Free-text box: one location per line OR comma-separated, e.g.
    "Paris, France", "New York, USA", "Dubai, UAE". Works anywhere on Earth.
  - Optional country selector biases results toward one country (regionCode).

LIMITS
  - No per-run cap by default. Set GMB_MAX_QUERIES=<n> to cap, e.g. on Vercel
    (serverless functions have a ~60s limit). For huge sweeps, run locally.
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

DEFAULT_CATEGORIES = ["beauty salon", "dental clinic", "real estate agency",
                      "gym / fitness center", "cafe", "boutique"]

# Optional country bias (ISO 3166-1 alpha-2). "" = worldwide / auto from text.
COUNTRIES = [
    ("", "Worldwide (auto-detect from text)"),
    ("US", "United States"), ("GB", "United Kingdom"), ("CA", "Canada"),
    ("AU", "Australia"), ("IN", "India"), ("AE", "United Arab Emirates"),
    ("SA", "Saudi Arabia"), ("SG", "Singapore"), ("MY", "Malaysia"),
    ("ID", "Indonesia"), ("PH", "Philippines"), ("TH", "Thailand"),
    ("VN", "Vietnam"), ("JP", "Japan"), ("KR", "South Korea"),
    ("CN", "China"), ("HK", "Hong Kong"), ("BD", "Bangladesh"),
    ("PK", "Pakistan"), ("LK", "Sri Lanka"), ("NP", "Nepal"),
    ("DE", "Germany"), ("FR", "France"), ("ES", "Spain"), ("IT", "Italy"),
    ("PT", "Portugal"), ("NL", "Netherlands"), ("BE", "Belgium"),
    ("CH", "Switzerland"), ("AT", "Austria"), ("IE", "Ireland"),
    ("SE", "Sweden"), ("NO", "Norway"), ("DK", "Denmark"), ("FI", "Finland"),
    ("PL", "Poland"), ("CZ", "Czechia"), ("RO", "Romania"), ("GR", "Greece"),
    ("TR", "Turkey"), ("RU", "Russia"), ("UA", "Ukraine"),
    ("ZA", "South Africa"), ("NG", "Nigeria"), ("KE", "Kenya"),
    ("EG", "Egypt"), ("MA", "Morocco"), ("GH", "Ghana"), ("TZ", "Tanzania"),
    ("BR", "Brazil"), ("MX", "Mexico"), ("AR", "Argentina"), ("CL", "Chile"),
    ("CO", "Colombia"), ("PE", "Peru"), ("NZ", "New Zealand"),
    ("IL", "Israel"), ("QA", "Qatar"), ("KW", "Kuwait"), ("OM", "Oman"),
    ("BH", "Bahrain"),
]


def _query_cap():
    """Per-run search cap. None means no cap (default).

    Set GMB_MAX_QUERIES=<number> to cap (recommended on serverless/Vercel).
    """
    override = os.environ.get("GMB_MAX_QUERIES", "")
    if override.isdigit() and int(override) > 0:
        return int(override)
    return None


def _parse_locations(text: str) -> list[str]:
    """Accept one location per line and/or comma-separated; return clean list."""
    if not text:
        return []
    # Split on newlines first; treat each line as ONE location (so "City,
    # Country" stays intact). A line may hold several places separated by ";".
    locs: list[str] = []
    for line in text.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        for piece in line.split(";"):
            piece = piece.strip().strip(",").strip()
            if piece:
                locs.append(piece)
    # de-dupe, preserve order
    seen, out = set(), []
    for l in locs:
        k = l.lower()
        if k not in seen:
            seen.add(k)
            out.append(l)
    return out


def _csv_b64(rows: list) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fl.COLUMNS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fl.COLUMNS})
    return base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeadFinder - businesses with &amp; without a website, worldwide</title>
<style>
 :root{
   --green:#25D366; --green-d:#1da851; --teal:#128C7E; --teal-d:#075E54;
   --ink:#0b141a; --muted:#667781; --line:#e3e8ea; --bg:#eae6df; --card:#ffffff;
   --chat:#dcf8c6; --warn:#b35900; --warnbg:#fff4e5; --good:#0a7a3d;
 }
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--ink);
   font:16px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
   background-image:linear-gradient(135deg,#075E54 0,#075E54 220px,var(--bg) 220px);}
 .wrap{max-width:1080px;margin:0 auto;padding:0 16px 90px}
 header{padding:26px 0 18px;color:#fff}
 .brand{display:flex;align-items:center;gap:12px}
 .logo{width:46px;height:46px;border-radius:14px;background:var(--green);
   display:grid;place-items:center;box-shadow:0 6px 18px rgba(0,0,0,.25);flex:none}
 .logo svg{width:26px;height:26px}
 h1{font-size:26px;font-weight:800;margin:0;letter-spacing:-.5px}
 .tag{color:#cdeee2;margin:6px 0 0;font-size:14.5px;max-width:640px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:18px;
   padding:22px;box-shadow:0 10px 30px rgba(7,94,84,.12)}
 form .row{margin-top:16px}
 label{display:block;font-size:12px;font-weight:700;color:var(--teal-d);
   text-transform:uppercase;letter-spacing:.05em;margin:0 0 7px}
 input,select,textarea{width:100%;background:#f7faf9;border:1.5px solid var(--line);
   color:var(--ink);border-radius:12px;padding:12px 14px;font-size:15.5px;font-family:inherit;
   transition:border-color .15s,box-shadow .15s}
 textarea{resize:vertical;min-height:96px;line-height:1.5}
 input:focus,select:focus,textarea:focus{outline:0;border-color:var(--green);
   box-shadow:0 0 0 3px rgba(37,211,102,.18)}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
 @media(max-width:660px){.grid{grid-template-columns:1fr}
   body{background-image:linear-gradient(135deg,#075E54 0,#075E54 180px,var(--bg) 180px)}}
 .hint{font-size:12.5px;color:var(--muted);margin-top:7px}
 .chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
 .chip{background:var(--chat);border:1px solid #bfe6a8;color:#1f5e1f;border-radius:999px;
   padding:5px 12px;font-size:12.5px;cursor:pointer;user-select:none;font-weight:600}
 .chip:hover{background:#cdeeb0}
 .btn{margin-top:20px;width:100%;background:var(--green);color:#06281a;border:0;border-radius:13px;
   padding:15px 22px;font-size:16.5px;font-weight:800;cursor:pointer;letter-spacing:.2px;
   box-shadow:0 8px 20px rgba(37,211,102,.35);transition:transform .05s,background .15s}
 .btn:hover{background:var(--green-d);color:#fff}
 .btn:active{transform:translateY(1px)}
 .keyok{background:#e7f8ee;border:1px solid #b7e6c9;color:var(--good);border-radius:12px;
   padding:10px 14px;font-size:13.5px;margin-bottom:14px;font-weight:600}
 .alert{border-radius:13px;padding:13px 16px;margin:18px 0;font-size:14.5px}
 .err{background:var(--warnbg);border:1px solid #f0c992;color:var(--warn)}
 .ok{background:#e7f8ee;border:1px solid #b7e6c9;color:var(--good);font-weight:600}
 .stats{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0 6px}
 .stat{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);
   border-radius:14px;padding:14px 16px;box-shadow:0 6px 16px rgba(7,94,84,.08)}
 .stat .n{font-size:28px;font-weight:800;line-height:1}
 .stat .l{font-size:12.5px;color:var(--muted);margin-top:6px;text-transform:uppercase;
   letter-spacing:.04em;font-weight:700}
 .stat.no .n{color:var(--teal)} .stat.yes .n{color:var(--teal-d)} .stat.tot .n{color:var(--green-d)}
 .tabs{display:flex;gap:8px;margin:22px 0 0;border-bottom:2px solid var(--line)}
 .tab{appearance:none;background:none;border:0;border-bottom:3px solid transparent;
   padding:11px 16px;font-size:14.5px;font-weight:700;color:var(--muted);cursor:pointer;margin-bottom:-2px}
 .tab.active{color:var(--teal-d);border-bottom-color:var(--green)}
 .panel{display:none}.panel.active{display:block}
 .dlbar{margin:16px 0 4px}
 .dl{display:inline-flex;align-items:center;gap:8px;background:var(--teal);color:#fff;
   padding:11px 18px;border-radius:12px;font-weight:700;text-decoration:none;font-size:14.5px;
   box-shadow:0 6px 16px rgba(18,140,126,.3)}
 .dl:hover{background:var(--teal-d)}
 .dl.alt{background:var(--green);color:#06281a}.dl.alt:hover{background:var(--green-d);color:#fff}
 .tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px;margin-top:14px;background:var(--card)}
 table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:760px}
 th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top}
 th{background:#f3f7f6;color:var(--teal-d);font-weight:700;position:sticky;top:0}
 tr:last-child td{border-bottom:0}
 tr:hover td{background:#fafdfc}
 a.maps{color:var(--teal);font-weight:600;text-decoration:none}
 a.site{color:var(--green-d);font-weight:600;text-decoration:none;word-break:break-all}
 .empty{padding:26px;text-align:center;color:var(--muted)}
 footer{margin-top:34px;color:var(--muted);font-size:12.5px;text-align:center}
 footer a{color:var(--teal)}
</style></head><body><div class="wrap">

<header>
  <div class="brand">
    <span class="logo"><svg viewBox="0 0 24 24" fill="none"><path d="M12 2C8.1 2 5 5.1 5 9c0 5 7 13 7 13s7-8 7-13c0-3.9-3.1-7-7-7Z" fill="#06281a"/><circle cx="12" cy="9" r="2.6" fill="#25D366"/></svg></span>
    <div>
      <h1>LeadFinder</h1>
      <p class="tag">Find local businesses <b>anywhere in the world</b> - split into those <b>with</b> and <b>without</b> a website. Powered by the official Google Places API (New).</p>
    </div>
  </div>
</header>

<div class="card">
<form method="post" action="/">
  {% if server_key %}
    <div class="keyok">&#10003; A permanent API key is configured on the server - leave the key box empty.</div>
  {% endif %}

  <div class="row">
    <label for="api_key">Google API key (Places API New){{ ' - optional, server key set' if server_key else '' }}</label>
    <input type="password" id="api_key" name="api_key" autocomplete="off"
           placeholder="{{ 'leave blank to use the server key' if server_key else 'paste your key' }}">
  </div>

  <div class="row">
    <label for="locations">Locations - anywhere in the world (one per line; no limit)</label>
    <textarea id="locations" name="locations" placeholder="Paris, France&#10;New York, USA&#10;Dubai, UAE&#10;Tokyo, Japan&#10;Lagos, Nigeria">{{ locations_text|e }}</textarea>
    <div class="hint">Type as many places as you like - cities, neighbourhoods, regions. Each line is searched against every keyword below.</div>
  </div>

  <div class="grid row">
    <div>
      <label for="country">Country bias (optional)</label>
      <select id="country" name="country">
        {% for code,name in countries %}<option value="{{ code }}" {{ 'selected' if country==code else '' }}>{{ name }}</option>{% endfor %}
      </select>
      <div class="hint">Leave on "Worldwide" if your lines already include the country.</div>
    </div>
    <div>
      <label for="max_pages">Results depth per search</label>
      <select id="max_pages" name="max_pages">
        <option value="1" {{ 'selected' if pages==1 else '' }}>Top 20 (cheapest, fastest)</option>
        <option value="2" {{ 'selected' if pages==2 else '' }}>Top 40</option>
        <option value="3" {{ 'selected' if pages==3 else '' }}>Top 60 (deepest)</option>
      </select>
      <div class="hint">Google caps each search at ~60 results.</div>
    </div>
  </div>

  <div class="row">
    <label for="categories">Keywords / business types (comma separated)</label>
    <input type="text" id="categories" name="categories" value="{{ cats_text|e }}"
           placeholder="beauty salon, dental clinic, web design agency, cafe, gym">
    <div class="chips">
      {% for c in chip_cats %}<span class="chip" data-cat="{{ c|e }}">{{ c }}</span>{% endfor %}
    </div>
    <div class="hint">Click a suggestion to add it, or type your own. Search whatever you want.</div>
  </div>

  <button class="btn" type="submit" name="run" value="1">Find leads &rarr;</button>
  <div class="hint">{% if cap %}Capped to {{ cap }} searches per run (GMB_MAX_QUERIES). {% else %}No per-run limit. {% endif %}Each location &times; keyword is one search and uses Google quota. On serverless (Vercel ~60s) keep runs small or set GMB_MAX_QUERIES; for huge sweeps run locally.</div>
</form>
</div>

{% if error %}<div class="alert err">{{ error }}</div>{% endif %}
{% if trimmed %}<div class="alert err">Selection was large - trimmed to the first {{ cap }} searches. Run again with another batch, or remove the GMB_MAX_QUERIES cap / run locally.</div>{% endif %}

{% if ran %}
  <div class="alert ok">Scanned {{ total }} businesses across {{ nqueries }} searches - {{ no_website|length }} have no website, {{ with_website|length }} have a website.</div>
  <div class="stats">
    <div class="stat tot"><div class="n">{{ total }}</div><div class="l">Businesses found</div></div>
    <div class="stat no"><div class="n">{{ no_website|length }}</div><div class="l">No website (prospects)</div></div>
    <div class="stat yes"><div class="n">{{ with_website|length }}</div><div class="l">With a website</div></div>
  </div>

  <div class="tabs">
    <button class="tab active" type="button" data-panel="no">No website ({{ no_website|length }})</button>
    <button class="tab" type="button" data-panel="yes">With website ({{ with_website|length }})</button>
  </div>

  <div class="panel active" id="panel-no">
    <div class="dlbar">
      {% if csv_no %}<a class="dl alt" download="leads_NO_website.csv" href="data:text/csv;base64,{{ csv_no }}">&darr; Download CSV (no website)</a>{% endif %}
    </div>
    {% if no_website %}
    <div class="tablewrap"><table>
      <tr><th>Business</th><th>Keyword</th><th>Location</th><th>Phone</th><th>Address</th><th>Rating</th><th>Maps</th></tr>
      {% for r in no_website %}
      <tr><td>{{ r.business_name }}</td><td>{{ r.category }}</td><td>{{ r.location }}</td>
        <td>{{ r.phone }}</td><td>{{ r.address }}</td>
        <td>{{ r.rating }}{% if r.reviews %} ({{ r.reviews }}){% endif %}</td>
        <td>{% if r.maps_url %}<a class="maps" href="{{ r.maps_url }}" target="_blank" rel="noopener">open</a>{% endif %}</td></tr>
      {% endfor %}
    </table></div>
    {% else %}<div class="empty">No no-website businesses found for that search. Try other places/keywords.</div>{% endif %}
  </div>

  <div class="panel" id="panel-yes">
    <div class="dlbar">
      {% if csv_yes %}<a class="dl" download="leads_WITH_website.csv" href="data:text/csv;base64,{{ csv_yes }}">&darr; Download CSV (with website)</a>{% endif %}
    </div>
    {% if with_website %}
    <div class="tablewrap"><table>
      <tr><th>Business</th><th>Keyword</th><th>Location</th><th>Phone</th><th>Website</th><th>Rating</th><th>Maps</th></tr>
      {% for r in with_website %}
      <tr><td>{{ r.business_name }}</td><td>{{ r.category }}</td><td>{{ r.location }}</td>
        <td>{{ r.phone }}</td>
        <td>{% if r.website %}<a class="site" href="{{ r.website }}" target="_blank" rel="noopener">{{ r.website }}</a>{% endif %}</td>
        <td>{{ r.rating }}{% if r.reviews %} ({{ r.reviews }}){% endif %}</td>
        <td>{% if r.maps_url %}<a class="maps" href="{{ r.maps_url }}" target="_blank" rel="noopener">open</a>{% endif %}</td></tr>
      {% endfor %}
    </table></div>
    {% else %}<div class="empty">No businesses with a website found for that search.</div>{% endif %}
  </div>
{% endif %}

<footer>Uses the official Google Places API (New) - not scraping. If you set a server-side key, keep this URL private (anyone with it could spend your quota).</footer>
</div>

<script>
 // keyword suggestion chips
 document.querySelectorAll('.chip').forEach(function(ch){
   ch.addEventListener('click',function(){
     var inp=document.getElementById('categories');
     var cur=inp.value.split(',').map(function(s){return s.trim()}).filter(Boolean);
     var v=ch.getAttribute('data-cat');
     if(cur.indexOf(v)===-1){cur.push(v);inp.value=cur.join(', ');}
   });
 });
 // result tabs
 document.querySelectorAll('.tab').forEach(function(t){
   t.addEventListener('click',function(){
     document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
     document.querySelectorAll('.panel').forEach(function(x){x.classList.remove('active')});
     t.classList.add('active');
     document.getElementById('panel-'+t.getAttribute('data-panel')).classList.add('active');
   });
 });
</script>
</body></html>"""


def _chip_categories():
    """A handful of suggestion chips (from presets if available)."""
    try:
        cats = fl.load_presets().get("categories", [])
    except Exception:  # noqa: BLE001
        cats = []
    base = ["beauty salon", "dental clinic", "web design agency", "cafe",
            "restaurant", "gym / fitness center", "real estate agency",
            "car repair", "boutique", "law firm", "plumber", "electrician"]
    seen, out = set(), []
    for c in base + cats:
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out[:14]


@app.route("/", methods=["GET", "POST"])
def index():
    server_key = bool(os.environ.get("GOOGLE_MAPS_API_KEY"))
    src = request.form if request.method == "POST" else request.args
    pages = int(src.get("max_pages", 1) or 1)
    pages = max(1, min(3, pages))
    cap = _query_cap()

    ctx = {
        "countries": COUNTRIES, "chip_cats": _chip_categories(), "server_key": server_key,
        "country": src.get("country", ""),
        "locations_text": src.get("locations", ""),
        "cats_text": src.get("categories", ", ".join(DEFAULT_CATEGORIES)),
        "pages": pages, "cap": cap,
        "ran": False, "error": None, "trimmed": False,
        "no_website": [], "with_website": [], "total": 0, "nqueries": 0,
        "csv_no": "", "csv_yes": "",
    }

    if src.get("run") != "1":
        return render_template_string(PAGE, **ctx)

    api_key = (src.get("api_key") or "").strip() or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        ctx["error"] = "No API key. Paste your Google Places API key, or set GOOGLE_MAPS_API_KEY on the server."
        return render_template_string(PAGE, **ctx)

    locations = _parse_locations(ctx["locations_text"])
    if not locations:
        ctx["error"] = "Add at least one location (one per line), e.g. 'Paris, France'."
        return render_template_string(PAGE, **ctx)

    cats = [c.strip() for c in ctx["cats_text"].replace("\n", ",").split(",") if c.strip()] or DEFAULT_CATEGORIES
    region = ctx["country"] or None

    queries = [(loc, cat) for loc in locations for cat in cats]
    if cap is not None and len(queries) > cap:
        queries = queries[:cap]
        ctx["trimmed"] = True

    seen, all_rows = set(), []
    for loc, cat in queries:
        q = f"{cat} in {loc}"
        try:
            places = fl.search_text(api_key, q, region_code=region, max_pages=pages)
        except Exception as exc:  # noqa: BLE001
            ctx["error"] = f"Search failed: {exc}"
            break
        for row in fl.extract_rows(places, location=loc, category=cat):
            pid = row["place_id"]
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            all_rows.append(row)

    no_website, with_website = fl.split_leads(all_rows)
    ctx.update(ran=True, no_website=no_website, with_website=with_website,
               total=len(all_rows), nqueries=len(queries),
               csv_no=_csv_b64(no_website) if no_website else "",
               csv_yes=_csv_b64(with_website) if with_website else "")
    return render_template_string(PAGE, **ctx)


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
