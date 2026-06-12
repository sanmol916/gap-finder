#!/usr/bin/env python3
"""
gap-finder: mine Reddit + App Store reviews for unmet needs in any niche.

Usage examples
--------------
    # basic: search Reddit + App Store for a niche
    python main.py "youth sports scorekeeping"

    # focus on specific subreddits and pull more data
    python main.py "meal planning" --subreddits mealprep nutrition EatCheapAndHealthy \
        --reddit-limit 80 --review-pages 6

    # enable AI clustering (needs OPENAI_API_KEY in the environment)
    python main.py "dog training app" --llm

    # write the report somewhere specific
    python main.py "rent pg hostel" --out reports/pg.md

Optional environment variables
------------------------------
    REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET  -> use Reddit's official OAuth API
    OPENAI_API_KEY                           -> enable --llm clustering
    OPENAI_BASE_URL / GAPFINDER_MODEL        -> point at any OpenAI-compatible API
"""

from __future__ import annotations

import os
import sys
import argparse

import sources
import analyze
import report


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="gap-finder",
        description="Mine Reddit + App Store reviews for unmet needs in any niche.",
    )
    p.add_argument("query", help="the niche / topic to investigate")
    p.add_argument("--subreddits", nargs="*", default=None,
                   help="restrict Reddit search to these subreddits")
    p.add_argument("--reddit-limit", type=int, default=50,
                   help="max Reddit posts per search (default 50)")
    p.add_argument("--time", default="year",
                   choices=["hour", "day", "week", "month", "year", "all"],
                   help="Reddit time window (default year)")
    p.add_argument("--no-comments", action="store_true",
                   help="skip fetching Reddit comments (faster, less depth)")
    p.add_argument("--comment-posts", type=int, default=12,
                   help="how many top posts to pull comments from (default 12)")
    p.add_argument("--no-reddit", action="store_true", help="skip Reddit entirely")
    p.add_argument("--no-appstore", action="store_true", help="skip App Store entirely")
    p.add_argument("--appstore-apps", type=int, default=6,
                   help="how many related apps to pull reviews from (default 6)")
    p.add_argument("--review-pages", type=int, default=4,
                   help="review pages per app, ~50 reviews/page (default 4)")
    p.add_argument("--country", default="us", help="App Store country code (default us)")
    p.add_argument("--min-score", type=float, default=1.5,
                   help="minimum finding score to keep (default 1.5)")
    p.add_argument("--top", type=int, default=40,
                   help="how many top quotes to show in the report (default 40)")
    p.add_argument("--llm", action="store_true",
                   help="cluster findings into themes via OPENAI_API_KEY")
    p.add_argument("--out", default=None,
                   help="output markdown path (default: <slug>-gap-report.md)")
    return p.parse_args(argv)


def slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:50]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    niche = args.query
    print(f"\n=== gap-finder: \"{niche}\" ===\n")

    items: list[dict] = []

    if not args.no_reddit:
        print("[1/3] Reddit ...")
        try:
            reddit = sources.Reddit()
            items += reddit.search(
                niche, subreddits=args.subreddits, limit=args.reddit_limit,
                time_filter=args.time, with_comments=not args.no_comments,
                comment_posts=args.comment_posts,
            )
        except Exception as exc:  # never let one source kill the run
            print(f"  [reddit] skipped due to error: {exc}")

    if not args.no_appstore:
        print("[2/3] App Store ...")
        try:
            store = sources.AppStore()
            items += store.collect(
                niche, country=args.country,
                apps=args.appstore_apps, pages=args.review_pages,
            )
        except Exception as exc:
            print(f"  [appstore] skipped due to error: {exc}")

    stats = {
        "items": len(items),
        "reddit": sum(1 for i in items if i["source"] == "reddit"),
        "appstore": sum(1 for i in items if i["source"] == "appstore"),
    }
    print(f"\n  collected {stats['items']} items "
          f"(reddit {stats['reddit']}, appstore {stats['appstore']})")

    if not items:
        print("\nNo data collected. Reddit may be blocking this IP (set "
              "REDDIT_CLIENT_ID/SECRET for the OAuth API) or the query was too narrow.")
        return 1

    print("[3/3] Analysing ...")
    findings = analyze.find_pain(items, min_score=args.min_score)
    signal_freq = analyze.signal_frequency(findings)
    keyword_freq = analyze.keyword_frequency(findings)
    print(f"  found {len(findings)} pain findings")

    llm_summary = None
    if args.llm:
        print("  clustering with LLM ...")
        llm_summary = analyze.cluster_with_llm(findings, niche)
        if llm_summary is None:
            print("  [llm] no OPENAI_API_KEY (or call failed) - skipping clustering")

    md = report.build_report(niche, findings, signal_freq, keyword_freq,
                             stats, llm_summary, top=args.top)

    out = args.out or f"{slugify(niche)}-gap-report.md"
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)

    print(f"\nDone. Report written to: {out}")
    print(f"Top findings: {min(len(findings), 5)} shown below\n")
    for f in findings[:5]:
        print(f"  [{f['score']}] {f['quote'][:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
