"""Sentetik DEMO ürünlerini veritabanına yükler (yalnızca deneme içindir, ürünler [DEMO] etiketlidir).
Kaldırmak için: python scripts/load_demo.py --sil"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from vr import db, ingest  # noqa: E402
import make_demo_data  # noqa: E402

db.init_db()
with db.connect() as con:
    if "--sil" in sys.argv:
        ids = [r["id"] for r in con.execute("SELECT id FROM products WHERE is_demo=1")]
        for t in ("evaluations", "scores", "predictions", "comments"):
            con.executemany(f"DELETE FROM {t} WHERE product_id=?", [(i,) for i in ids])
        con.execute("DELETE FROM products WHERE is_demo=1")
        print(f"{len(ids)} demo ürün silindi")
    else:
        n = ingest.save_products(con, ingest.parse_products_json(json.dumps(make_demo_data.build())))
        print(f"{n} demo kayıt yüklendi")
