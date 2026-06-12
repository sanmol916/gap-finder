"""
Data sources for the gap-finder.

Two public sources are supported out of the box:

1. Reddit  - searches posts (and optionally top comments). Uses the official
             OAuth API when REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET are set,
             otherwise falls back to the public .json endpoints.
2. App Store - finds related apps via the iTunes Search API and pulls their
               most-recent customer reviews via the public RSS-JSON feed.

Every fetcher returns a list of normalised `Item` dicts so the rest of the
pipeline does not care where the text came from.

An Item looks like:
    {
        "source":  "reddit" | "appstore",
        "kind":    "post" | "comment" | "review",
        "title":   str,
        "text":    str,
        "url":     str,
        "weight":  float,   # popularity / negativity multiplier
        "meta":    dict,    # source-specific extras (stars, upvotes, sub, ...)
    }
"""

from __future__ import annotations

import os
import time
import base64
from typing import List, Dict, Any
from urllib.parse import quote_plus

import requests

USER_AGENT = os.environ.get(
    "GAPFINDER_UA",
    "gap-finder/1.0 (market-research script; contact: you@example.com)",
)

DEFAULT_TIMEOUT = 20


def _get(url: str, headers: Dict[str, str] | None = None,
         params: Dict[str, Any] | None = None, retries: int = 3) -> requests.Response | None:
    """GET with a descriptive User-Agent, simple retry and backoff."""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=h, params=params, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"  [rate-limited] waiting {wait}s ...")
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                print(f"  [http {resp.status_code}] {url}")
                return None
            return resp
        except requests.RequestException as exc:
            print(f"  [network error] {exc} (attempt {attempt + 1}/{retries})")
            time.sleep(1 + attempt)
    return None


# --------------------------------------------------------------------------- #
# Reddit
# --------------------------------------------------------------------------- #
class Reddit:
    """Reddit search. Prefers OAuth (app-only) when credentials exist."""

    def __init__(self) -> None:
        self.client_id = os.environ.get("REDDIT_CLIENT_ID")
        self.client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        self.token: str | None = None
        if self.client_id and self.client_secret:
            self.token = self._authenticate()

    def _authenticate(self) -> str | None:
        creds = f"{self.client_id}:{self.client_secret}".encode()
        auth = base64.b64encode(creds).decode()
        try:
            resp = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                headers={"Authorization": f"Basic {auth}", "User-Agent": USER_AGENT},
                data={"grant_type": "client_credentials"},
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 200:
                print("  [reddit] using OAuth API")
                return resp.json().get("access_token")
            print(f"  [reddit] OAuth failed ({resp.status_code}); using public JSON")
        except requests.RequestException as exc:
            print(f"  [reddit] OAuth error: {exc}; using public JSON")
        return None

    @property
    def _base(self) -> str:
        return "https://oauth.reddit.com" if self.token else "https://www.reddit.com"

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"bearer {self.token}"} if self.token else {}

    def search(self, query: str, subreddits: List[str] | None = None,
               limit: int = 50, time_filter: str = "year",
               with_comments: bool = True, comment_posts: int = 12) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        searches = []
        if subreddits:
            for sub in subreddits:
                searches.append((sub, f"{self._base}/r/{sub}/search.json"))
        else:
            searches.append((None, f"{self._base}/search.json"))

        posts: List[Dict[str, Any]] = []
        for sub, url in searches:
            params = {
                "q": query, "limit": min(limit, 100), "sort": "relevance",
                "t": time_filter, "raw_json": 1,
            }
            if sub:
                params["restrict_sr"] = "true"
            resp = _get(url, headers=self._headers, params=params)
            if not resp:
                continue
            try:
                children = resp.json().get("data", {}).get("children", [])
            except ValueError:
                continue
            for c in children:
                d = c.get("data", {})
                posts.append(d)
                items.append({
                    "source": "reddit", "kind": "post",
                    "title": d.get("title", ""),
                    "text": d.get("selftext", "") or "",
                    "url": "https://www.reddit.com" + d.get("permalink", ""),
                    "weight": 1.0 + min(d.get("score", 0), 500) / 250.0,
                    "meta": {"subreddit": d.get("subreddit"), "upvotes": d.get("score"),
                             "comments": d.get("num_comments")},
                })
            time.sleep(0.7)

        if with_comments:
            # richest complaints live in comments of the most-discussed posts
            posts.sort(key=lambda p: p.get("num_comments", 0), reverse=True)
            for d in posts[:comment_posts]:
                permalink = d.get("permalink")
                if not permalink:
                    continue
                url = f"{self._base}{permalink}.json"
                resp = _get(url, headers=self._headers, params={"limit": 100, "raw_json": 1})
                if not resp:
                    continue
                try:
                    listings = resp.json()
                except ValueError:
                    continue
                if len(listings) < 2:
                    continue
                for c in listings[1].get("data", {}).get("children", []):
                    cd = c.get("data", {})
                    body = cd.get("body")
                    if not body:
                        continue
                    items.append({
                        "source": "reddit", "kind": "comment",
                        "title": d.get("title", ""),
                        "text": body,
                        "url": "https://www.reddit.com" + permalink,
                        "weight": 1.0 + min(cd.get("score", 0), 300) / 150.0,
                        "meta": {"subreddit": d.get("subreddit"), "upvotes": cd.get("score")},
                    })
                time.sleep(0.7)
        return items


# --------------------------------------------------------------------------- #
# App Store
# --------------------------------------------------------------------------- #
class AppStore:
    """Find related apps and pull their recent customer reviews (public RSS-JSON)."""

    def search_apps(self, query: str, country: str = "us", limit: int = 6) -> List[Dict[str, Any]]:
        url = "https://itunes.apple.com/search"
        params = {"term": query, "country": country, "entity": "software", "limit": limit}
        resp = _get(url, params=params)
        if not resp:
            return []
        try:
            results = resp.json().get("results", [])
        except ValueError:
            return []
        return [{"id": r.get("trackId"), "name": r.get("trackName"),
                 "url": r.get("trackViewUrl")} for r in results if r.get("trackId")]

    def reviews(self, app_id: int, app_name: str, country: str = "us",
                pages: int = 4) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for page in range(1, pages + 1):
            url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
                   f"page={page}/id={app_id}/sortby=mostrecent/json")
            resp = _get(url)
            if not resp:
                break
            try:
                entries = resp.json().get("feed", {}).get("entry", [])
            except ValueError:
                break
            if isinstance(entries, dict):
                entries = [entries]
            # first entry is app metadata when present; reviews carry im:rating
            for e in entries:
                if "im:rating" not in e:
                    continue
                try:
                    stars = int(e["im:rating"]["label"])
                except (KeyError, ValueError, TypeError):
                    stars = 3
                content = e.get("content", {}).get("label", "")
                title = e.get("title", {}).get("label", "")
                # weight negative reviews much higher - they describe missing things
                weight = {1: 3.0, 2: 2.2, 3: 1.4, 4: 0.7, 5: 0.4}.get(stars, 1.0)
                items.append({
                    "source": "appstore", "kind": "review",
                    "title": title, "text": content,
                    "url": e.get("link", {}).get("attributes", {}).get("href", ""),
                    "weight": weight,
                    "meta": {"stars": stars, "app": app_name},
                })
            time.sleep(0.4)
        return items

    def collect(self, query: str, country: str = "us", apps: int = 6,
                pages: int = 4) -> List[Dict[str, Any]]:
        found = self.search_apps(query, country=country, limit=apps)
        print(f"  [appstore] found {len(found)} related apps")
        items: List[Dict[str, Any]] = []
        for app in found:
            revs = self.reviews(app["id"], app["name"], country=country, pages=pages)
            print(f"  [appstore] {app['name']}: {len(revs)} reviews")
            items.extend(revs)
        return items
