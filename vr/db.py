"""SQLite kalıcı katman. İlk prototipte benzer tablolar birleştirildi (bkz. DATABASE_SCHEMA.md).
Tüm sorgular parametreli (SQL injection koruması). Tekrar kayıt UNIQUE anahtarlarla engellenir."""
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name_tr TEXT NOT NULL,
    name_en TEXT,
    category TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    data_json TEXT NOT NULL DEFAULT '{}',      -- teknik özellikler + doğrulama durumları
    status TEXT NOT NULL DEFAULT 'aktif',       -- aktif | elendi | arsiv | favori
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    source TEXT NOT NULL,
    url TEXT,
    video_key TEXT UNIQUE NOT NULL,              -- kaynak + video id / url hash
    published_at TEXT,
    data_json TEXT NOT NULL DEFAULT '{}',
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS video_metrics (       -- 24/48/72s, 7g yeniden ölçümler
    id INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id),
    measured_at TEXT NOT NULL,
    views INTEGER, likes INTEGER, comments INTEGER, shares INTEGER, saves INTEGER, followers INTEGER,
    UNIQUE(video_id, measured_at)
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    product_id INTEGER REFERENCES products(id),
    content_hash TEXT NOT NULL,
    text TEXT NOT NULL,                           -- kişisel bilgiler anonimleştirilmiş
    lang TEXT,
    labels_json TEXT NOT NULL DEFAULT '[]',
    bot_level TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(product_id, video_id, content_hash)
);
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    name TEXT NOT NULL,
    url TEXT,
    data_json TEXT NOT NULL DEFAULT '{}',
    verification TEXT NOT NULL DEFAULT 'Bilinmiyor',
    created_at TEXT NOT NULL,
    UNIQUE(product_id, name)
);
CREATE TABLE IF NOT EXISTS evidence_sources (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    topic TEXT NOT NULL,
    claim TEXT NOT NULL,
    source_url TEXT,
    period TEXT,
    method TEXT,
    confidence TEXT NOT NULL,                     -- yüksek | orta | düşük
    researched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS economic_indicators (
    id INTEGER PRIMARY KEY,
    indicator TEXT NOT NULL,
    period TEXT NOT NULL,
    value REAL,
    unit TEXT,
    source_url TEXT,
    confidence TEXT,
    researched_at TEXT NOT NULL,
    UNIQUE(indicator, period)
);
CREATE TABLE IF NOT EXISTS scores (              -- product/timing/confidence/avatar skor geçmişi
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    kind TEXT NOT NULL,                           -- overall | timing | confidence | avatar | priority
    value REAL NOT NULL,
    min_value REAL, max_value REAL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    scoring_version TEXT NOT NULL,
    computed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_flags (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    code TEXT NOT NULL,
    severity TEXT NOT NULL,                       -- kritik | yüksek | orta | düşük
    note TEXT,
    resolved INTEGER NOT NULL DEFAULT 0,
    UNIQUE(product_id, code)
);
CREATE TABLE IF NOT EXISTS research_queue (       -- Instagram/URL araştırma kuyruğu
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    platform TEXT,
    note TEXT,
    status TEXT NOT NULL DEFAULT 'bekliyor',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sales_test_results (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    alert_key TEXT UNIQUE NOT NULL,               -- aynı uyarı tekrar edilmez
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    day TEXT NOT NULL,
    calls INTEGER NOT NULL DEFAULT 0,
    UNIQUE(provider, day)
);
CREATE TABLE IF NOT EXISTS criteria_profiles (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    data_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluations (          -- son değerlendirme (ürün x profil)
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    profile_name TEXT NOT NULL,
    decision TEXT NOT NULL,
    priority REAL NOT NULL,
    profile_match REAL,
    eliminated INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    UNIQUE(product_id, profile_name)
);
CREATE TABLE IF NOT EXISTS predictions (          -- tahmin doğruluğu takibi
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    predicted_at TEXT NOT NULL,
    priority REAL, decision TEXT, trend_stage TEXT,
    outcome_30 TEXT, outcome_60 TEXT, outcome_90 TEXT,
    UNIQUE(product_id, predicted_at)
);
CREATE TABLE IF NOT EXISTS gold_labels (          -- insan etiketli yorumlar
    id INTEGER PRIMARY KEY,
    comment_text TEXT NOT NULL,
    labels_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    layer INTEGER NOT NULL,
    status TEXT NOT NULL,                         -- calisiyor | kisitli | erisilemiyor | baglanmadi
    last_ok TEXT, last_error TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    detail TEXT,
    at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_hash(text: str) -> str:
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:24]


@contextmanager
def connect(path: str | None = None):
    path = path or config.DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(path: str | None = None) -> None:
    with connect(path) as con:
        con.executescript(SCHEMA)


def audit(con, action: str, detail: str = "") -> None:
    con.execute("INSERT INTO audit_logs(action, detail, at) VALUES (?,?,?)", (action, detail[:500], now_iso()))


def upsert_product(con, slug: str, name_tr: str, category: str, data: dict, name_en: str = "", is_demo: bool = False) -> int:
    ts = now_iso()
    con.execute(
        """INSERT INTO products(slug, name_tr, name_en, category, is_demo, data_json, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(slug) DO UPDATE SET name_tr=excluded.name_tr, name_en=excluded.name_en,
             category=excluded.category, data_json=excluded.data_json, updated_at=excluded.updated_at""",
        (slug, name_tr, name_en, category, int(is_demo), json.dumps(data, ensure_ascii=False), ts, ts),
    )
    return con.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()["id"]


def add_comment(con, product_id: int, text: str, labels: list, bot_level: str, lang: str = "tr",
                video_id: int | None = None, is_demo: bool = False) -> bool:
    """Yeni kayıt eklenirse True, tekrar ise False. (video_id NULL olsa da tekrar engellenir.)"""
    h = content_hash(text)
    if con.execute("SELECT 1 FROM comments WHERE product_id=? AND content_hash=? AND video_id IS ?",
                   (product_id, h, video_id)).fetchone():
        return False
    cur = con.execute(
        """INSERT OR IGNORE INTO comments(video_id, product_id, content_hash, text, lang, labels_json, bot_level, is_demo, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (video_id, product_id, content_hash(text), text, lang, json.dumps(labels), bot_level, int(is_demo), now_iso()),
    )
    return cur.rowcount == 1


def save_score(con, product_id: int, kind: str, value: float, detail: dict, vmin=None, vmax=None) -> None:
    con.execute(
        """INSERT INTO scores(product_id, kind, value, min_value, max_value, detail_json, scoring_version, computed_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (product_id, kind, round(value, 2), vmin, vmax, json.dumps(detail, ensure_ascii=False),
         config.SCORING_VERSION, now_iso()),
    )


def add_alert(con, key: str, category: str, message: str) -> bool:
    cur = con.execute("INSERT OR IGNORE INTO alerts(alert_key, category, message, created_at) VALUES (?,?,?,?)",
                      (key, category, message, now_iso()))
    return cur.rowcount == 1


def backup(path: str | None = None, dest_dir: str | None = None) -> str:
    """SQLite online backup API ile tutarlı yedek alır."""
    path = path or config.DB_PATH
    dest_dir = dest_dir or os.path.join(os.path.dirname(os.path.abspath(path)), "backups")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"viral_radar_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db")
    src = sqlite3.connect(path)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    return dest


def restore(backup_file: str, path: str | None = None) -> None:
    path = path or config.DB_PATH
    # Geri yüklemeden önce mevcut durumun da yedeğini al (geri dönüş yolu)
    if os.path.exists(path):
        backup(path)
    shutil.copyfile(backup_file, path)


def integrity_ok(path: str | None = None) -> bool:
    con = sqlite3.connect(path or config.DB_PATH)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


SOURCES = [
    ("Google Trends", 1), ("Meta Ad Library", 1), ("Trendyol", 1), ("Hepsiburada", 1), ("Amazon Türkiye", 1),
    ("N11", 1), ("Temu Türkiye", 1), ("RSS ve açık veri", 1), ("TÜİK / TCMB EVDS", 1), ("Yerli üretici siteleri", 1),
    ("Instagram (paylaşım/ekran görüntüsü)", 2), ("Facebook (paylaşım)", 2), ("TikTok (paylaşım)", 2),
    ("YouTube Shorts (paylaşım)", 2), ("Pinterest (paylaşım)", 2), ("CSV/JSON dosya aktarımı", 2),
    ("TikTok Creative Center", 1), ("Bağlı ücretli araçlar (Apify, vidIQ vb.)", 3),
]


def seed_sources(con) -> None:
    for name, layer in SOURCES:
        status = "calisiyor" if name == "CSV/JSON dosya aktarımı" else "baglanmadi"
        con.execute("INSERT OR IGNORE INTO source_status(source, layer, status, note) VALUES (?,?,?,?)",
                    (name, layer, status, "Aşama 2'de bağlanacak" if status == "baglanmadi" else "Aşama 1'de hazır"))
