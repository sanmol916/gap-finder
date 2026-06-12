"""
Turn raw text Items into ranked "pain findings".

The idea: people describe unmet needs with predictable language.
"I wish there was...", "is there an app that...", "I hate how...",
"there's no way to...", "would be so much easier if...".

We scan every Item for these signal phrases, pull out the sentence that
contains the signal (the actual pain quote), and score it by:
    signal strength  x  source weight (upvotes / negative star rating)

Optionally, if an OpenAI-compatible API key is present, we ask an LLM to
cluster the raw pain quotes into named themes + suggested product ideas.
"""

from __future__ import annotations

import os
import re
import json
from collections import Counter
from typing import List, Dict, Any

import requests

# signal phrase -> strength. Higher = stronger evidence of an unmet need.
SIGNALS: Dict[str, float] = {
    # explicit demand for a solution
    "i wish there was": 3.0,
    "i wish there were": 3.0,
    "wish there was": 3.0,
    "wish it could": 2.5,
    "is there an app": 3.0,
    "is there a tool": 3.0,
    "is there a website": 3.0,
    "is there any app": 3.0,
    "is there a way to": 2.5,
    "does anyone know of": 2.5,
    "looking for an app": 2.8,
    "looking for a tool": 2.8,
    "why is there no": 3.2,
    "why isn't there": 3.2,
    "why does no one": 2.8,
    "someone should build": 3.2,
    "someone should make": 3.2,
    "needs to exist": 3.0,
    "would be nice if": 2.2,
    "would be great if": 2.2,
    "it would be amazing if": 2.4,
    "please add": 2.0,
    "feature request": 2.0,
    "no way to": 2.5,
    "there's no way": 2.5,
    "can't find a": 2.2,
    "cant find a": 2.2,
    # frustration / friction
    "so frustrating": 2.0,
    "frustrating": 1.5,
    "so annoying": 1.8,
    "annoying": 1.2,
    "i hate that": 2.2,
    "i hate how": 2.2,
    "hate that it": 2.0,
    "such a pain": 2.2,
    "what a pain": 2.0,
    "huge pain": 2.2,
    "waste of time": 2.0,
    "takes forever": 2.0,
    "by hand": 1.8,
    "manually": 1.6,
    "one by one": 2.0,
    "tedious": 2.0,
    "clunky": 1.6,
    "overpriced": 1.8,
    "too expensive": 1.8,
    "rip off": 1.8,
    "doesn't work": 1.5,
    "doesnt work": 1.5,
    "keeps crashing": 1.8,
    "missing feature": 2.2,
    "the only problem": 1.8,
    "biggest problem": 2.0,
    "the worst part": 1.8,
    "struggle with": 1.8,
    "struggling to": 1.8,
}

# strip noise so quotes read cleanly
_URL_RE = re.compile(r"https?://\S+")
_WS_RE = re.compile(r"\s+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


def _clean(text: str) -> str:
    text = _URL_RE.sub("", text)
    text = text.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")
    return _WS_RE.sub(" ", text).strip()


def _sentences(text: str) -> List[str]:
    parts = _SENT_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def find_pain(items: List[Dict[str, Any]], min_score: float = 1.5) -> List[Dict[str, Any]]:
    """Scan items, extract the sentence around each signal, score it."""
    findings: List[Dict[str, Any]] = []
    seen_quotes: set[str] = set()

    for item in items:
        blob = _clean(f"{item.get('title', '')}. {item.get('text', '')}")
        if not blob:
            continue
        low = blob.lower()
        sentences = _sentences(blob)

        for phrase, strength in SIGNALS.items():
            if phrase not in low:
                continue
            # find the sentence(s) containing this phrase
            for sent in sentences:
                if phrase not in sent.lower():
                    continue
                quote = sent if len(sent) <= 320 else sent[:317] + "..."
                key = quote.lower()
                if key in seen_quotes or len(quote) < 12:
                    continue
                seen_quotes.add(key)
                score = strength * float(item.get("weight", 1.0))
                if score < min_score:
                    continue
                findings.append({
                    "quote": quote,
                    "signal": phrase,
                    "score": round(score, 2),
                    "source": item.get("source"),
                    "kind": item.get("kind"),
                    "url": item.get("url"),
                    "meta": item.get("meta", {}),
                })

    findings.sort(key=lambda f: f["score"], reverse=True)
    return findings


def signal_frequency(findings: List[Dict[str, Any]]) -> List[tuple]:
    counter = Counter(f["signal"] for f in findings)
    return counter.most_common()


def keyword_frequency(findings: List[Dict[str, Any]], top: int = 25) -> List[tuple]:
    """Crude noun-ish keyword frequency across pain quotes (stopword filtered)."""
    stop = set("""
        the a an and or but if then so of to in on for with at by from as is are was were be been
        being it its it's this that these those i you he she we they them my your our their me us
        not no yes do does did doing have has had having will would could should can cant cannt
        just like really very too also more most some any all what when where why how who which
        there here app apps tool tools use using used want need get got make made one only thing
        things way ways im ive dont doesnt wish about into out up down than then them about
    """.split())
    words = Counter()
    for f in findings:
        for w in re.findall(r"[a-zA-Z][a-zA-Z'-]{2,}", f["quote"].lower()):
            if w not in stop:
                words[w] += 1
    return words.most_common(top)


# --------------------------------------------------------------------------- #
# Optional LLM clustering
# --------------------------------------------------------------------------- #
def cluster_with_llm(findings: List[Dict[str, Any]], niche: str,
                     max_quotes: int = 60) -> str | None:
    """Cluster pain quotes into themes + product ideas using an OpenAI-compatible API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("GAPFINDER_MODEL", "gpt-4o-mini")

    quotes = [f["quote"] for f in findings[:max_quotes]]
    if not quotes:
        return None
    joined = "\n".join(f"- {q}" for q in quotes)
    prompt = (
        f"You are a product strategist. Below are real user complaints and "
        f"unmet-need quotes mined from Reddit and app reviews for the niche: "
        f"\"{niche}\".\n\nCluster them into 4-8 named pain themes. For each theme give:\n"
        f"1) Theme name\n2) The core unmet need in one sentence\n"
        f"3) How often it appears (low/medium/high)\n"
        f"4) A concrete product or AI-feature idea that would solve it\n"
        f"5) A 1-10 opportunity score (demand x how unsolved it seems).\n\n"
        f"Rank themes by opportunity score. Be concrete and specific.\n\n"
        f"QUOTES:\n{joined}"
    )
    try:
        resp = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            }),
            timeout=90,
        )
        if resp.status_code != 200:
            print(f"  [llm] error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        print(f"  [llm] failed: {exc}")
        return None
