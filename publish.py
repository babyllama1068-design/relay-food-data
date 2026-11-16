"""
Publishes a built copy to Hugging Face: the new file and latest.json in one commit, so a phone never sees a
latest.json naming a file that isn't there yet. Keeps the last four weeks' files, so a bad copy can be rolled back
by pointing latest.json at an older one.

    HF_TOKEN=... python publish.py --out out
"""
import argparse
import json
import os

from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

REPO = "Killerfuzzball/relay-food-uk"
KEEP = 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    latest = json.load(open(os.path.join(args.out, "latest.json")))

    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(REPO, repo_type="dataset", exist_ok=True, private=False)
    old = sorted(f for f in api.list_repo_files(REPO, repo_type="dataset")
                 if f.startswith("relay-food-uk-") and f != latest["file"])
    here = os.path.dirname(os.path.abspath(__file__))
    ops = [CommitOperationAdd(latest["file"], os.path.join(args.out, latest["file"])),
           CommitOperationAdd("latest.json", os.path.join(args.out, "latest.json")),
           CommitOperationAdd("README.md", os.path.join(here, "dataset-card.md"))]
    ops += [CommitOperationDelete(f) for f in old[:max(0, len(old) - (KEEP - 1))]]
    api.create_commit(REPO, ops, repo_type="dataset",
                      commit_message=f"Food copy {latest['version']}: {latest['off_products']:,} products, "
                                     f"{latest['cofid_foods']:,} plain foods")
    print(f"Published {latest['file']} to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
