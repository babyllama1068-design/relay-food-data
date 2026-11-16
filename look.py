# A look over a built copy: counts, figures that don't add up, a random sample and common searches.
# python look.py out/relay-food-uk.sqlite
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(sys.argv[1]); q = lambda s, *a: db.execute(s, a).fetchall()
print("== counts", q("select source, count(*), sum(pack is not null), sum(protein is not null), sum(carbs is null or fat is null) from food group by source"))
print("== kcal spread (off)", q("select sum(kcal=0), sum(kcal<10), sum(kcal between 10 and 100), sum(kcal between 100 and 400), sum(kcal>400), sum(kcal>800) from food where source='off'"))
# macros vs kcal mismatch
print("== kcal far from macros (>35% off, macros>40)", q("select count(*) from food where source='off' and protein is not null and carbs is not null and fat is not null and (4*protein+4*carbs+9*fat)>40 and abs(kcal-(4*protein+4*carbs+9*fat))>0.35*(4*protein+4*carbs+9*fat)"))
print("   e.g.", q("select name, brand, kcal, protein, carbs, fat from food where source='off' and protein is not null and carbs is not null and fat is not null and (4*protein+4*carbs+9*fat)>40 and abs(kcal-(4*protein+4*carbs+9*fat))>0.35*(4*protein+4*carbs+9*fat) order by scans desc limit 12"))
print("== no brand", q("select count(*) from food where source='off' and brand=''"))
print("== scans 0", q("select count(*) from food where source='off' and scans=0"))
print("== non-latin names", q("select count(*) from food where source='off' and name glob '*[^ -~£éèêëàâäôöûüçñíóúÉ’‘–—®™°½¼¾]*'"))
print("   e.g.", q("select name, brand from food where source='off' and name glob '*[^ -~£éèêëàâäôöûüçñíóúÉ’‘–—®™°½¼¾]*' order by scans desc limit 8"))
print("== random 25"); [print("  ", r) for r in q("select name, brand, kcal, protein, pack, scans from food where source='off' order by random() limit 25")]
def s(words, src='off', n=8):
    print("==", words, src); [print("  ", r) for r in q("select f.name, f.brand, f.kcal, f.protein, f.pack, f.scans from food_search s join food f on f.id=s.docid where food_search match ? and f.source=? order by f.scans desc limit ?", words, src, n)]
for w in ["name:sausage name:roll brand:greggs", "name:flat name:white", "name:tikka name:masala", "name:carling", "name:twix", "name:red name:bull", "name:semi name:skimmed name:milk", "name:hovis", "name:pint name:milk"]: s(w)
for w in ["name:flat name:white", "name:tikka", "name:sausage name:roll", "name:rice name:boiled", "name:egg name:boiled", "name:banana"]: s(w, 'cofid', 6)
