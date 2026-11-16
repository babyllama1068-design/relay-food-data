# Relay's food copy

Builds the cleaned UK food list that Relay's offline food logging searches on the phone, and publishes it to Hugging Face at [Killerfuzzball/relay-food-uk](https://huggingface.co/datasets/Killerfuzzball/relay-food-uk).

- **When:** every Saturday at 05:00 UTC by itself, or any time with **Actions → Weekly food copy → Run workflow**.
- **What:** UK products from Open Food Facts' export and the UK government's CoFID 2021 (`sources/cofid-2021.xlsx`), cut down to name, brand, kcal, protein, carbs, fat and pack size, with kJ-as-kcal slips mended, impossible figures dropped and duplicates merged (`build.py`).
- **Safety:** `checks.py` must pass before anything is published (enough products, no big drop on last week, well-known foods within range). If it fails, the run fails, GitHub emails the owner, and phones keep last week's copy.
- **Phones:** Relay reads `latest.json` weekly on Wi-Fi, downloads the named file, checks its SHA-256, then swaps it in. The last four weeks' files are kept, so a bad copy can be rolled back by pointing `latest.json` at an older one.
- `last-build.json` is committed each week, which records what was published and keeps GitHub from switching the schedule off (it does after 60 days with no commits).

This repo is public so its Actions minutes are free. It holds nothing private: the Hugging Face key is the `HF_TOKEN` Actions secret.

## Run it on a PC

```bash
pip install -r requirements.txt
curl -L -o off.csv.gz https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz
python build.py --off off.csv.gz --out out
HF_TOKEN=... python publish.py --out out
```

## Licences

Code: MIT. Data: Open Food Facts under the [ODbL](https://opendatacommons.org/licenses/odbl/1-0/); CoFID, Crown copyright, under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
