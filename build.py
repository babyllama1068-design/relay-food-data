"""
Builds Relay's food copy: UK products from Open Food Facts plus the UK government's CoFID, cleaned and cut down to
what Relay uses (name, brand, kcal, protein, carbs, fat per 100 g or ml, pack size). Everything else (vitamins,
minerals, ingredients, pictures, eco scores) is left out.

    python build.py --off en.openfoodfacts.org.products.csv.gz --out out

Writes out/relay-food-uk-<date>.sqlite.gz and out/latest.json. Exits with an error, and writes nothing, if the copy
fails its checks (checks.py), so a bad week never reaches phones.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import unicodedata

import duckdb
import openpyxl

FORMAT = 1  # Relay reads only copies whose format it knows; raise it when the tables change.
HERE = os.path.dirname(os.path.abspath(__file__))
COFID = os.path.join(HERE, "sources", "cofid-2021.xlsx")
CREDITS = ("Branded products: Open Food Facts (openfoodfacts.org), Open Database Licence (ODbL). "
           "Plain foods: McCance and Widdowson's Composition of Foods Integrated Dataset 2021 (UKHSA, OHID), "
           "Crown copyright, Open Government Licence v3.0.")

ALCOHOL = re.compile(r"\b(beer|lager|ale|stout|cider|wine|prosecco|champagne|gin|vodka|rum|whisky|whiskey|"
                     r"brandy|liqueur|spirit|porter|ipa|sake|alcoholic)\b")
MULTIPACK = re.compile(r"\b\d+\s*(?:pk|pack)\b|multipack|\bpack of \d")
NON_LATIN = re.compile(r"[Ͱ-῿⺀-￯]")
PACK = re.compile(r"(?:\d+\s*[x×]\s*)?(\d+(?:[.,]\d+)?)\s*(kg|g|ml|cl|l)(?![a-z])")


def num(v, lo=0.0, hi=100.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if lo <= x <= hi else None


def pack_size(quantity):
    """One pack's grams or ml, as Relay's FoodLookup.packSize reads it (a multipack's '8x25g' is one 25 g bag)."""
    m = PACK.search((quantity or "").lower())
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    grams = n * {"kg": 1000, "l": 1000, "cl": 10}.get(m.group(2), 1)
    return grams if 5 <= grams <= 2000 else None


SERVING_COUNT = re.compile(r"^\s*(\d+)\s*(biscuit|bar|slice|piece|cracker|cake|bun|sweet|finger|roll|pot|sachet)s?\b")


def one_unit(quantity, serving_size, serving_quantity):
    """One of what people say they had: the pack, unless the pack is a box or multipack of servings, then one
    serving ("a Mars bar" in a 160 g four-pack is 40 g; "a Greggs sausage roll" in an 854 g bag is 103 g, Relay 4.40
    on the phone). A serving of "2 biscuits (38 g)" is 19 g, as "three Weetabix" means three biscuits."""
    pack = pack_size(quantity)
    serving = num(serving_quantity, 5, 2000)
    if serving:
        m = SERVING_COUNT.match((serving_size or "").lower())
        if m and int(m.group(1)) > 1:
            serving /= int(m.group(1))
        # More than three servings is a box or multipack; a Twix's 50 g is two 25 g fingers and still one Twix.
        if pack is None or pack > 3 * serving:
            return round(serving, 1)
    return pack


def kcal_for(row, alcoholic):
    """Calories per 100 g, mending the common slips: kJ typed in the kcal box, or only kJ given."""
    kcal = num(row["kcal"], 0, 4000)
    kj = num(row["kj"], 0, 4000) or num(row["energy"], 0, 4000)
    if kcal is None and kj is not None:
        kcal = kj / 4.184
    elif kcal is not None and kj is not None and kj > 50 and 0.9 <= kcal / kj <= 1.1:
        kcal = kj / 4.184  # the same number in both boxes: it was kJ
    if kcal is None:
        return None
    p, c, f = (num(row[k]) for k in ("protein", "carbs", "fat"))
    if None not in (p, c, f):
        macros = 4 * p + 4 * c + 9 * f
        if not alcoholic and macros > 20 and kcal > 3 * macros and 0.8 <= (kcal / 4.184) / macros <= 1.2:
            kcal /= 4.184
        if macros > 8 and kcal < 0.5 * macros:
            return None  # figures that can't all be right (an apple juice at 0 kcal)
        # Calories that protein, carbs and fat can't explain: Red Bull at 463 per 100 ml (it's 46), a Tesco wholemeal
        # loaf at 580 (16 Nov 2026). Alcohol, and sweets' polyols and fibre, move it a little, never this far.
        if not alcoholic and macros > 20 and not 0.55 <= kcal / macros <= 1.6:
            return None
    return kcal if 0 <= kcal <= 900 else None  # 0 is real: diet drinks, water


def open_food_facts(path):
    """UK products with believable figures, one row per product, from Open Food Facts' CSV export."""
    con = duckdb.connect()
    rows = con.sql(f"""
        select code, product_name as name, brands as brand, quantity,
               "energy-kcal_100g" as kcal, "energy-kj_100g" as kj, energy_100g as energy,
               proteins_100g as protein, carbohydrates_100g as carbs, fat_100g as fat,
               coalesce(try_cast(unique_scans_n as integer), 0) as scans, categories_tags as cats,
               serving_size, serving_quantity
        from read_csv('{path}', delim='\t', quote='', header=true, all_varchar=true, ignore_errors=true,
                      max_line_size=10000000)
        where countries_tags like '%en:united-kingdom%' and coalesce(trim(product_name), '') <> ''
    """).fetchall()
    cols = ["code", "name", "brand", "quantity", "kcal", "kj", "energy", "protein", "carbs", "fat", "scans", "cats",
            "serving_size", "serving_quantity"]
    best = {}
    for r in rows:
        row = dict(zip(cols, r))
        name, brand = row["name"].strip(), (row["brand"] or "").strip()
        if NON_LATIN.search(name):
            continue  # tagged as sold in the UK, but named in Cyrillic, Greek, Arabic...: no English search finds it
        # "non-alcoholic-beverages" (Red Bull's category) says alcoholic too.
        text = re.sub(r"non-alcoholic|alcohol-free|low-alcohol|0\.0", " ", f"{name} {row['cats'] or ''}".lower())
        alcoholic = bool(ALCOHOL.search(text))
        kcal = kcal_for(row, alcoholic)
        if kcal is None:
            continue
        p, c, f = (None if x is None else round(x, 1) for x in (num(row[k]) for k in ("protein", "carbs", "fat")))
        if sum(x or 0 for x in (p, c, f)) > 105:
            continue
        multipack = bool(MULTIPACK.search(f"{name} {row['quantity'] or ''}".lower()))
        item = dict(source="off", code=row["code"], name=name, brand=brand, kcal=round(kcal, 1),
                    protein=p, carbs=c, fat=f, per="100g",
                    pack=one_unit(None if multipack else row["quantity"], row["serving_size"], row["serving_quantity"]),
                    multipack=int(multipack), scans=row["scans"])
        # The same product entered twice: keep the one people scan most.
        key = (name.lower(), brand.lower(), (row["quantity"] or "").lower().replace(" ", ""))
        if key not in best or item["scans"] > best[key]["scans"]:
            best[key] = item
    return list(best.values())


def cofid(path=COFID):
    """Plain foods measured in labs, per 100 g (per 100 ml for alcoholic drinks, CoFID's group Q)."""
    ws = openpyxl.load_workbook(path, read_only=True)["1.3 Proximates"]
    rows = list(ws.iter_rows(values_only=True))
    head = rows[0]
    col = {name: head.index(name) for name in
           ("Food Code", "Food Name", "Group", "Protein (g)", "Fat (g)", "Carbohydrate (g)", "Energy (kcal) (kcal)")}
    out = []
    for r in rows[3:]:
        name = r[col["Food Name"]]
        kcal = num(r[col["Energy (kcal) (kcal)"]], 0, 900)  # "N" (not measured) and "Tr" (trace) aren't numbers
        if not name or kcal is None:
            continue
        group = str(r[col["Group"]] or "")
        out.append(dict(source="cofid", code=r[col["Food Code"]], name=name.strip(), brand="", kcal=kcal,
                        protein=num(r[col["Protein (g)"]]), carbs=num(r[col["Carbohydrate (g)"]]),
                        fat=num(r[col["Fat (g)"]]), per="100ml" if group.startswith("Q") else "100g",
                        pack=None, multipack=0, scans=0))
    return out


def plain(s):
    """Without accents, for the search only: "Nestlé" and "Müller" are found by "nestle" and "muller" (Relay folds
    what it searches for the same way, FoodLookup.words)."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def write_sqlite(path, foods, meta):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript("""
        create table food(id integer primary key, source text not null, code text, name text not null,
            brand text not null, kcal real not null, protein real, carbs real, fat real, per text not null,
            pack real, multipack integer not null, scans integer not null);
        -- Android's own SQLite has FTS4 (not always FTS5); porter matches 'mushrooms' to 'mushroom'.
        create virtual table food_search using fts4(name, brand, tokenize=porter);
        create table meta(key text primary key, value text);
    """)
    for i, f in enumerate(foods, 1):
        db.execute("insert into food values(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (i, f["source"], f["code"], f["name"], f["brand"], f["kcal"], f["protein"], f["carbs"],
                    f["fat"], f["per"], f["pack"], f["multipack"], f["scans"]))
        db.execute("insert into food_search(docid, name, brand) values(?,?,?)",
                   (i, plain(f["name"]).replace("&", " and "), plain(f["brand"]).replace(",", " ")))
    db.executemany("insert into meta values(?,?)", [(k, str(v)) for k, v in meta.items()])
    db.commit()
    db.execute("insert into food_search(food_search) values('optimize')")
    db.commit()
    db.execute("vacuum")
    db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True, help="Open Food Facts' CSV export (.csv.gz)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--previous", help="last week's latest.json, for the size check")
    args = ap.parse_args()

    version = dt.date.today().isoformat()
    off, plain = open_food_facts(args.off), cofid()
    print(f"Open Food Facts: {len(off):,} UK products; CoFID: {len(plain):,} plain foods")

    os.makedirs(args.out, exist_ok=True)
    db_path = os.path.join(args.out, "relay-food-uk.sqlite")
    meta = dict(format=FORMAT, version=version, off_products=len(off), cofid_foods=len(plain), credits=CREDITS)
    write_sqlite(db_path, off + plain, meta)

    import checks
    problems = checks.run(db_path, json.load(open(args.previous)) if args.previous else None)
    if problems:
        print("Not published:\n- " + "\n- ".join(problems))
        sys.exit(1)

    gz_name = f"relay-food-uk-{version}.sqlite.gz"
    gz_path = os.path.join(args.out, gz_name)
    with open(db_path, "rb") as src, gzip.open(gz_path, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    sha = hashlib.sha256(open(gz_path, "rb").read()).hexdigest()
    latest = dict(format=FORMAT, version=version, file=gz_name, sha256=sha, size=os.path.getsize(gz_path),
                  unpacked_size=os.path.getsize(db_path), **{k: meta[k] for k in ("off_products", "cofid_foods")},
                  credits=CREDITS)
    json.dump(latest, open(os.path.join(args.out, "latest.json"), "w"), indent=2)
    print(f"Built {gz_name}: {latest['size'] / 1e6:.1f} MB to download, {latest['unpacked_size'] / 1e6:.1f} MB on the phone")


if __name__ == "__main__":
    main()
