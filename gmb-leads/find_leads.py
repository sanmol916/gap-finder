#!/usr/bin/env python3
"""
find_leads: build a list of local businesses that have NO website, using the
official Google Places API (New). Intended use: lead-gen for selling website /
digital services (e.g. across North East India).

WHY THIS APPROACH
-----------------
Scraping Google Maps directly violates Google's Terms of Service and breaks
constantly. The Places API (New) legally returns each business's website field
(`websiteUri`), so we can keep only the businesses that don't have one.

SETUP
-----
1. Create a Google Cloud project: https://console.cloud.google.com/
2. Enable **Places API (New)** and enable **billing** (Google gives a recurring
   free credit; check current pricing before large runs).
3. Create an API key (restrict it to the Places API).
4. Export it:   export GOOGLE_MAPS_API_KEY="your_key"

USAGE
-----
    pip install -r requirements.txt

    # everything in the NE India presets (all cities x all categories)
    python find_leads.py

    # just a few cities / categories
    python find_leads.py --cities Guwahati Shillong Imphal \
        --categories "beauty salon" "dental clinic" "real estate agent"

    # one whole state
    python find_leads.py --states Assam

    # also keep businesses that DO have a website (for comparison)
    python find_leads.py --include-with-website

    # verify the pipeline with no API key (uses a built-in mock response)
    python find_leads.py --self-test

OUTPUT
------
    gmb-leads/output/ne_india_no_website_leads.csv   (and .xlsx if openpyxl installed)
Columns: business_name, category, city, state, phone, address, maps_url,
         rating, reviews, business_status, place_id
"""

from __future__ import annotations

import os
import csv
import sys
import json
import time
import argparse
from datetime import datetime

import requests

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Only request the fields we need (keeps cost down and response small).
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.rating",
    "places.userRatingCount",
    "places.googleMapsUri",
    "places.businessStatus",
    "places.primaryTypeDisplayName",
    "nextPageToken",
])

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS_PATH = os.path.join(HERE, "presets.json")
OUT_DIR = os.path.join(HERE, "output")

COLUMNS = ["business_name", "category", "city", "state", "phone", "address",
           "maps_url", "rating", "reviews", "business_status", "place_id"]


def load_presets() -> dict:
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def search_text(api_key: str, query: str, region_code: str = "IN",
                max_pages: int = 3, timeout: int = 30) -> list[dict]:
    """Call Places API (New) Text Search, following pagination up to max_pages."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    places: list[dict] = []
    page_token = None
    for page in range(max_pages):
        body = {"textQuery": query, "pageSize": 20, "regionCode": region_code}
        if page_token:
            body["pageToken"] = page_token
            time.sleep(2)  # token needs a moment to become valid
        for attempt in range(4):
            try:
                resp = requests.post(PLACES_SEARCH_URL, headers=headers,
                                     data=json.dumps(body), timeout=timeout)
            except requests.RequestException as exc:
                print(f"    [network] {exc} (retry {attempt + 1})")
                time.sleep(1 + attempt)
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2 ** attempt
                print(f"    [http {resp.status_code}] backing off {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"    [http {resp.status_code}] {resp.text[:200]}")
                return places
            data = resp.json()
            places.extend(data.get("places", []))
            page_token = data.get("nextPageToken")
            break
        else:
            break
        if not page_token:
            break
    return places


def extract_rows(places: list[dict], city: str, state: str, category: str) -> list[dict]:
    """Pure function: turn a Places API response list into normalized rows."""
    rows = []
    for p in places:
        website = p.get("websiteUri", "")
        rows.append({
            "business_name": (p.get("displayName") or {}).get("text", ""),
            "category": category,
            "city": city,
            "state": state,
            "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber", ""),
            "address": p.get("formattedAddress", ""),
            "maps_url": p.get("googleMapsUri", ""),
            "rating": p.get("rating", ""),
            "reviews": p.get("userRatingCount", ""),
            "business_status": p.get("businessStatus", ""),
            "place_id": p.get("id", ""),
            "_website": website,
        })
    return rows


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def write_xlsx(path: str, rows: list[dict]) -> bool:
    """Write a real .xlsx spreadsheet if openpyxl is available; else skip."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads (no website)"
    ws.append([c.replace("_", " ").title() for c in COLUMNS])
    header_fill = PatternFill("solid", fgColor="1F6FEB")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
    for r in rows:
        ws.append([r.get(k, "") for k in COLUMNS])
    # reasonable column widths
    widths = {"business_name": 32, "category": 20, "city": 14, "state": 18,
              "phone": 16, "address": 50, "maps_url": 38, "rating": 8,
              "reviews": 9, "business_status": 16, "place_id": 30}
    for i, c in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(c, 18)
    ws.freeze_panes = "A2"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    return True


def resolve_targets(presets: dict, args) -> list[tuple[str, str]]:
    """Return (city, state) pairs based on CLI filters."""
    states = presets["states"]
    pairs: list[tuple[str, str]] = []
    if args.cities:
        want = {c.lower() for c in args.cities}
        for state, cities in states.items():
            for city in cities:
                if city.lower() in want:
                    pairs.append((city, state))
    elif args.states:
        want = {s.lower() for s in args.states}
        for state, cities in states.items():
            if state.lower() in want:
                pairs.extend((city, state) for city in cities)
    elif args.all_india:
        for state, cities in states.items():
            pairs.extend((city, state) for city in cities)
    # else: no selection -> empty; main() warns (prevents accidental full-India runs)
    return pairs


def run_self_test() -> int:
    """Exercise extract/filter/write with a mock response (no API key needed)."""
    mock = {
        "places": [
            {"id": "p1", "displayName": {"text": "Hill View Salon"},
             "formattedAddress": "GS Road, Guwahati", "nationalPhoneNumber": "098640 00000",
             "rating": 4.3, "userRatingCount": 52, "googleMapsUri": "https://maps.google.com/?cid=1",
             "businessStatus": "OPERATIONAL", "websiteUri": ""},
            {"id": "p2", "displayName": {"text": "Brahmaputra Dental Care"},
             "formattedAddress": "Zoo Road, Guwahati", "nationalPhoneNumber": "036122 00000",
             "rating": 4.7, "userRatingCount": 120, "googleMapsUri": "https://maps.google.com/?cid=2",
             "businessStatus": "OPERATIONAL", "websiteUri": "https://example-dental.in"},
        ]
    }
    rows = extract_rows(mock["places"], "Guwahati", "Assam", "beauty salon")
    leads = [r for r in rows if not r["_website"]]
    assert len(rows) == 2 and len(leads) == 1, "filter logic broken"
    assert leads[0]["business_name"] == "Hill View Salon"
    out_csv = os.path.join(OUT_DIR, "self_test_leads.csv")
    write_csv(out_csv, leads)
    xlsx_ok = write_xlsx(os.path.join(OUT_DIR, "self_test_leads.xlsx"), leads)
    print("SELF-TEST PASSED")
    print(f"  parsed {len(rows)} places -> {len(leads)} no-website lead(s)")
    print(f"  wrote {out_csv}")
    print(f"  xlsx written: {xlsx_ok}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Find local businesses with no website via Places API (New).")
    ap.add_argument("--cities", nargs="*", help="limit to these cities")
    ap.add_argument("--states", nargs="*", help="limit to these states")
    ap.add_argument("--categories", nargs="*", help="override preset categories")
    ap.add_argument("--max-pages", type=int, default=3, help="pages per query (20 results each, max 3)")
    ap.add_argument("--all-india", action="store_true",
                    help="scan EVERY city in presets.json (large run - watch the cost)")
    ap.add_argument("--include-with-website", action="store_true", help="also output businesses that have a website")
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "india_no_website_leads"),
                    help="output path prefix (no extension)")
    ap.add_argument("--api-key", default=os.environ.get("GOOGLE_MAPS_API_KEY"))
    ap.add_argument("--self-test", action="store_true", help="run offline pipeline test (no key needed)")
    args = ap.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.api_key:
        print("ERROR: no API key. Set GOOGLE_MAPS_API_KEY or pass --api-key.\n"
              "       (Run with --self-test to verify the tool works without a key.)")
        return 2

    presets = load_presets()
    region = presets.get("region_code", "IN")
    categories = args.categories or presets["categories"]
    targets = resolve_targets(presets, args)
    if not targets:
        print("Nothing to search. Specify one of:\n"
              "  --cities Guwahati Shillong        (specific cities)\n"
              "  --states Assam Kerala             (all major cities in those states)\n"
              "  --all-india                       (EVERY city in presets - large run!)\n"
              "Check spelling against presets.json.")
        return 2

    print(f"Targets: {len(targets)} cities x {len(categories)} categories "
          f"= {len(targets) * len(categories)} queries")
    print("(this can take a while and consumes API quota)\n")

    seen: set[str] = set()
    all_rows: list[dict] = []
    for city, state in targets:
        for category in categories:
            query = f"{category} in {city}, {state}, India"
            print(f"  - {query}")
            places = search_text(args.api_key, query, region_code=region, max_pages=args.max_pages)
            for row in extract_rows(places, city, state, category):
                pid = row["place_id"]
                if pid and pid in seen:
                    continue
                if pid:
                    seen.add(pid)
                all_rows.append(row)

    leads = [r for r in all_rows if not r["_website"]]
    print(f"\nCollected {len(all_rows)} unique businesses; "
          f"{len(leads)} have NO website.")

    rows_to_write = all_rows if args.include_with_website else leads
    csv_path = args.out + ".csv"
    write_csv(csv_path, rows_to_write)
    print(f"Wrote {csv_path}")
    if write_xlsx(args.out + ".xlsx", rows_to_write):
        print(f"Wrote {args.out}.xlsx")
    else:
        print("(install openpyxl for an .xlsx spreadsheet: pip install openpyxl)")

    print(f"\nDone {datetime.utcnow():%Y-%m-%d %H:%M UTC}. "
          f"{len(leads)} leads ready for outreach.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
