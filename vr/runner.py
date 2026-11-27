"""Tek yazıcı iş: gelen kutusunu işler, bütün ürünleri bütün aktif profillerle değerlendirir,
skor geçmişini ve tahmin kaydını yazar, günlük raporu üretir, bütünlük kontrolü ve yedek alır.
Aynı anda iki kopyası çalışamaz (dosya kilidi + GitHub Actions concurrency)."""
import fcntl
import glob
import json
import os
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import config, db, ingest, pipeline, profiles, report


def today_tr() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


@contextmanager
def single_writer(path: str):
    lock = path + ".lock"
    os.makedirs(os.path.dirname(os.path.abspath(lock)), exist_ok=True)
    f = open(lock, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise RuntimeError("Başka bir iş zaten çalışıyor; bu çalıştırma atlandı.")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def evaluate_all(con, today: date) -> dict:
    profs = [p for p in ingest.load_profiles(con) if p.get("aktif", True)]
    rows = con.execute("SELECT id, slug, data_json FROM products WHERE status != 'elendi'").fetchall()
    out = {p["ad"]: [] for p in profs}
    for r in rows:
        rec = json.loads(r["data_json"])
        rec.setdefault("slug", r["slug"])
        for p in profs:
            res = pipeline.evaluate(rec, p, today)
            out[p["ad"]].append(res)
            con.execute(
                """INSERT INTO evaluations(product_id, profile_name, decision, priority, profile_match, eliminated, result_json, computed_at)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(product_id, profile_name) DO UPDATE SET decision=excluded.decision, priority=excluded.priority,
                     profile_match=excluded.profile_match, eliminated=excluded.eliminated, result_json=excluded.result_json,
                     computed_at=excluded.computed_at""",
                (r["id"], p["ad"], res["karar"], res["oncelik"], res["profil"]["profil_uyumu"], int(res["profil"]["elendi"]),
                 json.dumps(res, ensure_ascii=False, default=str), db.now_iso()))
        # Skor geçmişi ve tahmin kaydı (profilden bağımsız; ilk profil sonucu)
        base = out[profs[0]["ad"]][-1]
        for kind, key in (("overall", "genel"), ("confidence", "veri_guveni"), ("avatar", "avatar")):
            db.save_score(con, r["id"], kind, base[key]["puan"], {}, base[key]["min"], base[key]["max"])
        db.save_score(con, r["id"], "timing", base["zamanlama"]["bugun"], {"profil": base["zamanlama"]})
        db.save_score(con, r["id"], "priority", base["oncelik"], {})
        con.execute("INSERT OR IGNORE INTO predictions(product_id, predicted_at, priority, decision, trend_stage) VALUES (?,?,?,?,?)",
                    (r["id"], today.isoformat(), base["oncelik"], base["karar"], base["trend_asamasi"]))
    return out


def run(db_path: str | None = None, today: date | None = None, report_dir: str | None = None) -> dict:
    db_path = db_path or config.DB_PATH
    today = today or today_tr()
    report_dir = report_dir or os.path.join(os.path.dirname(os.path.abspath(db_path)), "..", "reports")
    with single_writer(db_path):
        db.init_db(db_path)
        with db.connect(db_path) as con:
            db.seed_sources(con)
            if not con.execute("SELECT 1 FROM criteria_profiles LIMIT 1").fetchone():
                ingest.save_profile(con, profiles.DEFAULT_PROFILE)
            inbox = ingest.process_inbox(con)
            results = evaluate_all(con, today)
            md = report.daily(results, today)
            db.audit(con, "gunluk_is", json.dumps({"inbox": inbox, "urun": sum(len(v) for v in results.values())}))
        if not db.integrity_ok(db_path):
            raise RuntimeError("Veritabanı bütünlük kontrolü başarısız; commit edilmeyecek.")
        bk = db.backup(db_path)
        backups = sorted(glob.glob(os.path.join(os.path.dirname(bk), "*.db")))
        for old in backups[:-7]:  # son 7 yedek tutulur
            os.remove(old)
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "gunluk_rapor.md"), "w", encoding="utf-8") as f:
        f.write(md)
    return {"inbox": inbox, "profiller": list(results), "urun_sayisi": len(next(iter(results.values()), [])), "yedek": bk}
