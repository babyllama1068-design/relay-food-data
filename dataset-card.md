---
license: odbl
language: en
pretty_name: Relay's UK food copy
tags: [food, nutrition, open-food-facts, cofid, uk]
---

# Relay's UK food copy

A small, cleaned food list for [Relay](https://github.com/babyllama1068-design/relay-food-data)'s offline food logging, rebuilt every Saturday:

- **Branded products** sold in the UK, from [Open Food Facts](https://world.openfoodfacts.org).
- **Plain foods** (mince, chips, a pint of lager) from McCance and Widdowson's *Composition of Foods Integrated Dataset 2021* (CoFID).

Each food keeps only its name, brand, calories, protein, carbohydrate and fat per 100 g (per 100 ml for alcoholic drinks from CoFID), and one pack's size. Entries with impossible figures are left out, kJ typed as kcal is put right, and duplicates are merged.

`latest.json` names the current file and its SHA-256. The file is a gzipped SQLite database: table `food`, full-text search in `food_search` (FTS4, porter), and `meta`.

## Licences and credit

- Open Food Facts data: [Open Database Licence](https://opendatacommons.org/licenses/odbl/1-0/). This copy is shared under the same licence.
- CoFID: Crown copyright, [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Contains public sector information licensed under the Open Government Licence v3.0.

Figures are as the sources give them; check a pack's label when it matters.
