# Work & Business Atlas

A concrete directory of **business types, trades, and professions** that exist in the world —
the kinds of real operators you can research, find a problem for, and sell a solution to.

This is different from `niche-atlas` (which maps abstract topics/markets). This maps **who you
would actually walk up to**: a "flag & banner manufacturer", a "women's clothing boutique", a
"regional-cuisine restaurant", an "auto body shop", a "mobile dog groomer".

## Current coverage (v0.1.0 seed)
| Level | Count |
|---|---|
| Sectors | 23 |
| Groups | 64 |
| Business/profession types | 493 |
| Example specializations | 189 |

> Breadth-first seed. Next phase deepens each sector toward thousands of entries
> (mirrors are NAICS/ISIC industry codes, O*NET occupations, and Google/Yelp business categories).

## Data model
`businesses.json` has 4 levels: **sector → group → type → examples**.

```jsonc
{
  "meta": { "levels": ["sector", "group", "type", "examples"] },
  "sectors": [
    {
      "id": "manufacturing-production",
      "name": "Manufacturing & Production",
      "groups": [
        {
          "name": "Promotional, Signage & Print",
          "types": [
            { "name": "Flag & banner manufacturer", "examples": ["promotional flags", "feather/teardrop flags"] },
            { "name": "Umbrella, gazebo & tent manufacturer", "examples": ["market umbrellas", "pop-up gazebos"] }
          ]
        }
      ]
    }
  ]
}
```

- **`type`** = a concrete business or profession you can sell to.
- **`examples`** = common specializations within that type.
- **`id`** (sector) = URL-safe slug for routing on the future funnel website.

## The 23 sectors
Retail Shops & Markets · Food, Drink & Hospitality · Manufacturing & Production ·
Construction & Skilled Trades · Automotive & Vehicles · Personal Care, Beauty & Wellness ·
Professional & Business Services · Health & Medical · Education & Training ·
Repair & Maintenance Services · Agriculture, Farming & Fishing · Logistics, Transport & Storage ·
Wholesale & Distribution · Real Estate & Property · Creative, Media & Entertainment ·
Events & Occasions · Recreation, Leisure & Travel · Pets & Animal Services ·
Industrial & Trade Services · Financial & Money Services · Public, Civic & Community ·
Security & Protective Services · End-of-Life & Memorial Services.

## Intended workflow (why this exists)
1. Browse a sector → pick a concrete business **type** (e.g. "auto body shop").
2. Run the sibling **gap-finder** tool on it to mine real complaints/problems.
3. Pick the sharpest problem and build/sell a solution to that exact type of operator.

## How the funnel website will use this
- Drill down sector → group → type, or search across all types.
- Each type page: description, typical specializations, and a "Find the problems" button
  that runs `gap-finder` for that business type.
- Filters (planned fields): `b2b_b2c`, `online_offline`, `avg_deal_size`, `tech_adoption`,
  `pain_density`, `ai_opportunity`.

## Roadmap to thousands of entries
1. Confirm this sector/group structure (this seed).
2. Deepen every group with more concrete types + specializations.
3. Cross-reference NAICS/ISIC codes and Google Business categories to catch the long tail.
4. Enrich each type with the filter fields above + example real-world businesses.

## Editing
Validate after any change:
```bash
python -c "import json;json.load(open('work-atlas/businesses.json'));print('ok')"
```
Add a type: append `{ "name": "...", "examples": ["..."] }` to the right group's `types`.
Add a sector: append a new object to `sectors` following the model above.
