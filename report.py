"""Render analysis results into a readable Markdown report."""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any


def _meta_label(f: Dict[str, Any]) -> str:
    meta = f.get("meta", {})
    if f["source"] == "reddit":
        sub = meta.get("subreddit")
        up = meta.get("upvotes")
        bits = []
        if sub:
            bits.append(f"r/{sub}")
        if up is not None:
            bits.append(f"{up}\u2191")
        return " \u00b7 ".join(bits)
    if f["source"] == "appstore":
        stars = meta.get("stars")
        app = meta.get("app")
        bits = []
        if app:
            bits.append(app)
        if stars is not None:
            bits.append("\u2605" * int(stars))
        return " \u00b7 ".join(bits)
    return ""


def build_report(niche: str, findings: List[Dict[str, Any]],
                 signal_freq: List[tuple], keyword_freq: List[tuple],
                 stats: Dict[str, Any], llm_summary: str | None,
                 top: int = 40) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines: List[str] = []
    lines.append(f"# Gap-Finder Report: \"{niche}\"")
    lines.append(f"\n*Generated {now}*\n")

    # --- summary stats ---
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Items scanned:** {stats.get('items', 0)} "
                 f"(reddit: {stats.get('reddit', 0)}, appstore: {stats.get('appstore', 0)})")
    lines.append(f"- **Pain findings:** {len(findings)}")
    lines.append(f"- **Top signal:** {signal_freq[0][0]!r} "
                 f"({signal_freq[0][1]}x)" if signal_freq else "- **Top signal:** none")
    lines.append("")

    # --- LLM clusters first (the punchline) ---
    if llm_summary:
        lines.append("## Pain themes & product ideas (AI-clustered)")
        lines.append("")
        lines.append(llm_summary.strip())
        lines.append("")

    # --- top findings ---
    lines.append("## Top pain quotes (ranked by signal x popularity)")
    lines.append("")
    if not findings:
        lines.append("_No strong complaint signals found. Try broader keywords, "
                     "more subreddits, or a lower --min-score._")
    for i, f in enumerate(findings[:top], 1):
        label = _meta_label(f)
        loc = f" \u2014 {label}" if label else ""
        lines.append(f"{i}. **[{f['score']}]** \u201c{f['quote']}\u201d  ")
        link = f"[{f['source']}/{f['kind']}]({f['url']})" if f.get("url") else f"{f['source']}/{f['kind']}"
        lines.append(f"   <sub>signal: `{f['signal']}` \u00b7 {link}{loc}</sub>")
    lines.append("")

    # --- signal frequency ---
    lines.append("## Signal phrase frequency")
    lines.append("")
    lines.append("| Signal phrase | Count |")
    lines.append("|---|---|")
    for phrase, count in signal_freq[:20]:
        lines.append(f"| `{phrase}` | {count} |")
    lines.append("")

    # --- keyword frequency ---
    lines.append("## Recurring keywords in pain quotes")
    lines.append("")
    lines.append(", ".join(f"`{w}` ({c})" for w, c in keyword_freq) if keyword_freq else "_none_")
    lines.append("")

    lines.append("---")
    lines.append("\n*Method: complaint-signal mining. Validate any promising theme by "
                 "talking to 10+ real users before building.*")
    return "\n".join(lines)
