#!/usr/bin/env python3
"""
Web wrapper for gap-finder so it can run as a hosted web service
(Render, Railway, Fly.io, etc.).

It reuses the same engine as the CLI (sources.py / analyze.py) and renders
the ranked pain findings as an HTML page. A "Download .md" endpoint returns
the same Markdown report the CLI produces.

Run locally:
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python app.py            # http://localhost:5000

Run in production (what Render/Railway use):
    gunicorn app:app --timeout 120 --workers 1
"""

from __future__ import annotations

import os
from flask import Flask, request, render_template, Response

import sources
import analyze
import report

app = Flask(__name__)

# Keep hosted requests fast enough to finish within free-tier limits.
# Users can push these higher when running the CLI locally.
MAX_REVIEW_PAGES = 6
MAX_APPS = 8
MAX_REDDIT_LIMIT = 80


def run_search(query: str, *, use_reddit: bool, use_appstore: bool,
               subreddits: list[str] | None, country: str,
               review_pages: int, appstore_apps: int, reddit_limit: int,
               time_filter: str, min_score: float, use_llm: bool) -> dict:
    """Run the full pipeline and return everything the template needs."""
    items: list[dict] = []
    errors: list[str] = []

    if use_reddit:
        try:
            reddit = sources.Reddit()
            items += reddit.search(
                query, subreddits=subreddits or None,
                limit=min(reddit_limit, MAX_REDDIT_LIMIT),
                time_filter=time_filter, with_comments=True, comment_posts=10,
            )
        except Exception as exc:  # noqa: BLE001 - surface, don't crash
            errors.append(f"Reddit: {exc}")

    if use_appstore:
        try:
            store = sources.AppStore()
            items += store.collect(
                query, country=country,
                apps=min(appstore_apps, MAX_APPS),
                pages=min(review_pages, MAX_REVIEW_PAGES),
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"App Store: {exc}")

    stats = {
        "items": len(items),
        "reddit": sum(1 for i in items if i["source"] == "reddit"),
        "appstore": sum(1 for i in items if i["source"] == "appstore"),
    }

    findings = analyze.find_pain(items, min_score=min_score)
    signal_freq = analyze.signal_frequency(findings)
    keyword_freq = analyze.keyword_frequency(findings)

    llm_summary = None
    if use_llm:
        llm_summary = analyze.cluster_with_llm(findings, query)
        if llm_summary is None and not os.environ.get("OPENAI_API_KEY"):
            errors.append("LLM clustering needs OPENAI_API_KEY set in the environment.")

    if use_reddit and stats["reddit"] == 0 and not errors:
        errors.append(
            "Reddit returned no items (cloud IPs are often blocked). "
            "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to use the official API."
        )

    return {
        "query": query, "stats": stats, "findings": findings,
        "signal_freq": signal_freq, "keyword_freq": keyword_freq,
        "llm_summary": llm_summary, "errors": errors,
    }


def _params_from_request() -> dict:
    """Parse query/form params shared by the HTML view and the .md download."""
    g = request.values
    subs = g.get("subreddits", "").replace(",", " ").split()
    return {
        "query": (g.get("q") or "").strip(),
        "use_reddit": g.get("reddit", "on") == "on",
        "use_appstore": g.get("appstore", "on") == "on",
        "subreddits": subs,
        "country": (g.get("country") or "us").strip() or "us",
        "review_pages": _int(g.get("review_pages"), 3),
        "appstore_apps": _int(g.get("appstore_apps"), 6),
        "reddit_limit": _int(g.get("reddit_limit"), 50),
        "time_filter": g.get("time", "year"),
        "min_score": _float(g.get("min_score"), 1.5),
        "use_llm": g.get("llm", "") == "on",
    }


def _int(v, default):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _float(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET"])
def index():
    params = _params_from_request()
    result = None
    if params["query"]:
        result = run_search(**params)
    return render_template("index.html", params=params, result=result,
                           top=int(request.values.get("top", 40)))


@app.route("/report.md", methods=["GET"])
def download_md():
    params = _params_from_request()
    if not params["query"]:
        return Response("Add ?q=your+niche to download a report.", mimetype="text/plain")
    result = run_search(**params)
    md = report.build_report(
        result["query"], result["findings"], result["signal_freq"],
        result["keyword_freq"], result["stats"], result["llm_summary"], top=80,
    )
    slug = "".join(c if c.isalnum() else "-" for c in params["query"].lower()).strip("-")[:50]
    return Response(
        md, mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{slug}-gap-report.md"'},
    )


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("FLASK_DEBUG")))
