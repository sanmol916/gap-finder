# Niche Atlas

A comprehensive, **data-driven** taxonomy of niches in the world — from giant domains
(Aerospace, Mining, Healthcare) down to tiny micro-niches (e.g. *Entertainment → Film &
Video → Trailers → fan-made/concept trailers*). Online and offline, physical and digital,
consumer and industrial.

This is the **source of truth** for a planned funnel-style discovery website: the site will
just render this data, so growing to 10,000+ niches is "add more data", not "rebuild the app".

## Current coverage (v0.1.0 seed)
| Level | Count |
|---|---|
| Domains | 61 |
| Categories | 111 |
| Subcategories | 202 |
| Niches | 569 |
| Micro-niches | 459 |

> This is a **breadth-first seed**: every major domain of human/economic activity is present,
> with representative depth. The next phase deepens each branch toward the 10,000+ goal.

## Data model
`niches.json` has 5 levels: **domain → category → subcategory → niche → micro**.

```jsonc
{
  "meta": { "name": "Niche Atlas", "version": "...", "levels": ["domain","category","subcategory","niche","micro"] },
  "domains": [
    {
      "id": "entertainment-film-music",
      "name": "Entertainment, Film & Music",
      "categories": [
        {
          "name": "Film & Video",
          "subcategories": [
            {
              "name": "Production & Distribution",
              "niches": [
                { "name": "Trailers/promo editing", "micro": ["fan-made/concept trailers", "copyright-safe cuts"] }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

- **`id`** (domain level) is a URL-safe slug for routing on the website (`/d/entertainment-film-music`).
- **`micro`** is an array of the smallest-grain niches; it may be empty where not yet expanded.

## The 61 domains
Primary & physical: Agriculture · Fishing & Aquaculture · Mining & Metals · Energy & Power ·
Water/Utilities/Waste · Environment & Climate.
Industrial & build: Manufacturing · Materials & Chemicals · Construction · Architecture &
Engineering · Robotics & Automation.
Transport & logistics: Automotive · Aviation & Aerospace · Space & Satellites · Maritime ·
Rail & Transit · Logistics & Supply Chain.
Tech & digital: Software & IT · AI & Data · Hardware & Semiconductors · Telecom · Cybersecurity ·
Internet & Digital Media · Blockchain/Web3 · Gaming & Esports.
Health & bio: Healthcare · Mental Health & Wellness · Pharma & Biotech · Fitness & Recreation ·
Beauty & Personal Care.
Finance & business: Finance & Investing · Insurance · Real Estate · Professional Services ·
Marketing & PR · HR & Workforce.
Consumer & lifestyle: Retail & E-commerce · Food & Beverage · Restaurants · Fashion & Textiles ·
Travel & Hospitality · Events & Weddings · Home & Garden · Pets · Personal & Local Services.
Society, knowledge & culture: Education · Media & Publishing · Entertainment · Arts & Crafts ·
Photography · Government & Civic · Legal · Defense & Security · Nonprofit · Religion & Spirituality ·
Relationships & Family · Parenting · Elder Care · Death & Funeral · Science & Research ·
Hobbies & Collectibles.

## Roadmap to 10,000+ niches
1. **Confirm the structure** (this seed) — domains + the 5-level model.
2. **Deepen each domain** — fill every subcategory with more niches, and every niche with micro-niches.
3. **Semi-automated expansion** — use AI + the sibling `gap-finder` tool (Reddit/App Store mining)
   to discover real sub-niches and attach evidence of demand to each one.
4. **Enrich each node** (optional future fields): `tags` (online/offline/B2B/B2C), `demand_signal`,
   `competition`, `monetization`, `ai_opportunity`, `examples`.
5. **Build the funnel website** that renders this JSON: search + drill-down + "explore problems"
   per niche (wired to gap-finder).

## How the funnel website will use this
- Landing → pick a **domain** → **category** → **subcategory** → **niche** → **micro**.
- Each niche page: description, online/offline tags, and a "Find the gaps" button that runs
  `gap-finder` on that niche to surface real complaints/opportunities.
- Global search across all levels; filters by tag (e.g. "show only offline + low-competition").

## Editing
- Keep `niches.json` valid (it is parsed by the website). Validate with:
  ```bash
  python -c "import json;json.load(open('niche-atlas/niches.json'));print('ok')"
  ```
- Add a niche: append `{ "name": "...", "micro": ["..."] }` to the right subcategory's `niches`.
- Add a whole domain: append a new object to `domains` following the model above.
