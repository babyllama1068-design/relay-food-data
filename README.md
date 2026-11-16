# Relay's food copy

Builds a cleaned list of UK foods for Relay's offline food logging, every Saturday at 05:00 UTC (or with **Actions → Weekly food copy → Run workflow**), and publishes it to Hugging Face at [Killerfuzzball/relay-food-uk](https://huggingface.co/datasets/Killerfuzzball/relay-food-uk).

This repo is public only so its GitHub Actions minutes are free. It holds no secrets (the Hugging Face key is an Actions secret) and no documentation beyond this note: how it works, how to run it and what the checks are live with Relay's own docs.

## Licences

Code: MIT. Data: Open Food Facts under the [ODbL](https://opendatacommons.org/licenses/odbl/1-0/); CoFID 2021, Crown copyright, under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
