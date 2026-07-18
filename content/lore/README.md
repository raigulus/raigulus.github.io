# Raigulus Lore Archive

Lore pages are generated from JSON records. Edit the records in `entries/` and
the shared source registry in `sources.json`; do not hand-edit generated files
under `/lore/`.

## Editorial workflow

1. Inventory the game item, official publication, or real-world source.
2. Register every source once in `sources.json`.
3. Add factual statements to an entry's `claims` list.
4. Attach one or more registered `source_ids` to every claim.
5. Build prose sections by referencing `claim_ids`; unsupported paragraphs fail
   validation.
6. Use `draft` or `source-reviewed` until a human editor has checked the page.
7. Set `human_reviewed` to `true` before using `human-reviewed` or `published`.
8. Run the commands below and review the generated HTML before publishing.

```sh
python3 scripts/validate_lore.py
python3 scripts/build_lore.py
python3 scripts/check_lore_pages.py
```

Use `python3 scripts/validate_lore.py --strict-site-inventory` after the existing
video page/data drift has been repaired. In normal mode that legacy drift is a
warning, while all lore validation errors remain blocking.

## Evidence labels

- `confirmed-influence`: an official or primary source explicitly confirms the
  influence.
- `explicit-reference`: the source directly references the other subject.
- `documented-parallel`: both sides are sourced, but no direct influence is
  claimed.
- `thematic-similarity`: editorial comparison only.
- `community-theory`: useful lead that remains unverified.
- `disputed`: credible sources conflict or contradict the claim.

Community wikis, forum posts, Reddit and unsourced videos can locate research
leads, but cannot be the sole source for a published factual claim.
