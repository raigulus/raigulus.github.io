# Raigulus Lore Archive

Lore pages are generated from versioned JSON records. Edit records under
`entries/`, the shared registry in `sources.json`, coverage files under
`inventories/`, and policy copy in `editorial.json`; do not hand-edit generated
files under `/lore/`.

The builder recursively discovers JSON records below `entries/`, so entity
folders can be introduced without changing the build. Controlled values live
in `vocabularies.json` and must be extended deliberately rather than bypassed.

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
python3 -m unittest scripts/test_validate_lore.py
python3 scripts/build_lore.py
python3 scripts/check_lore_pages.py
```

CI uses `python3 scripts/validate_lore.py --strict-site-inventory`. Canonical
video pages and `videos.json` records must agree; legacy HTML aliases with a
meta refresh are deliberately excluded from canonical inventory counts.

## Publication and copyright gates

- `human-reviewed` and `published` require `human_reviewed: true` and a named
  `reviewed_by` human editor.
- Raw transcript/subtitle fields and common audio/video/subtitle extensions are
  blocked from public lore content paths.
- Full working transcripts belong outside this public repository unless a
  separate rights review explicitly approves publication.
- Coverage inventories use `null` for an unknown expected total. The validator
  forbids calling an inventory reconciled until the expected total is known and
  equals the captured total.

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
