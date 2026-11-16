"""
Checks a built copy before it's published. Any problem stops the week's copy, so phones keep last week's.
"""
import sqlite3

# Foods whose figures are well known, with a generous range: if the cleaning broke, these move.
# (words to search, source, lowest and highest kcal per 100 g or ml)
# Searches use FTS4's column filters, so "mars" doesn't also find every Mars-made sweet.
KNOWN = [
    ("name:mars name:bar brand:mars", "off", 400, 480),
    ("name:baked name:beans brand:heinz", "off", 60, 95),
    ("name:coca name:cola", "off", 35, 48),
    ("name:weetabix", "off", 330, 390),
    ("name:red name:bull brand:red", "off", 0, 50),   # its most-scanned entry once said 463
    ("name:wholemeal name:bread", "off", 180, 280),
    ("name:ready name:salted brand:walkers", "off", 480, 560),
    ("name:lager", "cofid", 5, 60),
    ("name:potato name:chips", "cofid", 150, 400),
    ("name:beef name:mince name:raw", "cofid", 120, 300),
]

MIN_OFF = 40_000   # the UK has far more; fewer means the export or the filter broke
MIN_COFID = 2_500


def median_kcal(db, words, source):
    rows = db.execute("""select f.kcal from food_search s join food f on f.id = s.docid
                         where food_search match ? and f.source = ? order by f.scans desc limit 9""",
                      (words, source)).fetchall()
    xs = sorted(r[0] for r in rows)
    return xs[len(xs) // 2] if xs else None


def run(path, previous=None):
    db = sqlite3.connect(path)
    problems = []
    off = db.execute("select count(*) from food where source = 'off'").fetchone()[0]
    plain = db.execute("select count(*) from food where source = 'cofid'").fetchone()[0]
    if off < MIN_OFF:
        problems.append(f"only {off:,} Open Food Facts products (expected at least {MIN_OFF:,})")
    if plain < MIN_COFID:
        problems.append(f"only {plain:,} CoFID foods (expected at least {MIN_COFID:,})")
    if previous and off < 0.9 * previous.get("off_products", 0):
        problems.append(f"{off:,} Open Food Facts products, down more than 10% on last week's {previous['off_products']:,}")
    for words, source, lo, hi in KNOWN:
        k = median_kcal(db, words, source)
        if k is None or not lo <= k <= hi:
            problems.append(f"'{words}' ({source}) came out {k} kcal, expected {lo} to {hi}")
    bad = db.execute("select count(*) from food where kcal < 0 or kcal > 900 or name = ''").fetchone()[0]
    if bad:
        problems.append(f"{bad} rows with impossible figures or no name")
    db.close()
    return problems
