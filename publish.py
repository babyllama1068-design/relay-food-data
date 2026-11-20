"""
Publishes a built copy to Hugging Face: the new file, latest.json and its signature (latest.json.sig, made by the
workflow's Sign step) in one commit, so a phone never sees a latest.json naming a file that isn't there yet, or one
without its signature. Keeps the last four weeks' files, so a bad copy can be rolled
back by pointing latest.json at an older one and signing it again (Relay's docs/operations.md).

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
    # Relay refuses an unsigned latest.json, so publishing one would only stop phones updating.
    if not os.path.exists(os.path.join(args.out, "latest.json.sig")):
        raise SystemExit("out/latest.json.sig is missing: sign latest.json first (the workflow's Sign step)")

    api = HfApi(token=os.environ["HF_TOKEN"])
    # A key limited to this dataset can write to it but not create repos, so only create it the first time.
    if not api.repo_exists(REPO, repo_type="dataset"):
        api.create_repo(REPO, repo_type="dataset", private=False)
    old = sorted(f for f in api.list_repo_files(REPO, repo_type="dataset")
                 if f.startswith("relay-food-uk-") and f != latest["file"])
    here = os.path.dirname(os.path.abspath(__file__))
    ops = [CommitOperationAdd(latest["file"], os.path.join(args.out, latest["file"])),
           CommitOperationAdd("latest.json", os.path.join(args.out, "latest.json")),
           CommitOperationAdd("latest.json.sig", os.path.join(args.out, "latest.json.sig")),
           CommitOperationAdd("README.md", os.path.join(here, "dataset-card.md"))]
    ops += [CommitOperationDelete(f) for f in old[:max(0, len(old) - (KEEP - 1))]]
    api.create_commit(REPO, ops, repo_type="dataset",
                      commit_message=f"Food copy {latest['version']}: {latest['off_products']:,} products, "
                                     f"{latest['cofid_foods']:,} plain foods")
    print(f"Published {latest['file']} to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
