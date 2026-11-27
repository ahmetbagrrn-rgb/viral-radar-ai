"""Veri aktarımı: bağlantı kuyruğu, CSV/JSON ürün aktarımı, 'gelen kutusu' dosyaları, güvenli dışa aktarma.
Güvenlik: yalnızca http/https; yerel/özel ağ adresleri reddedilir (SSRF); dosya türü ve boyut sınırı;
CSV formül enjeksiyonu engellenir; dış metinler veri olarak işlenir, komut olarak değil."""
import csv
import io
import ipaddress
import json
import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

from . import config, db

PLATFORMS = {
    "instagram.com": "Instagram", "facebook.com": "Facebook", "fb.watch": "Facebook", "tiktok.com": "TikTok",
    "youtube.com": "YouTube", "youtu.be": "YouTube", "pinterest.com": "Pinterest", "pin.it": "Pinterest",
    "trendyol.com": "Trendyol", "hepsiburada.com": "Hepsiburada", "amazon.com.tr": "Amazon Türkiye",
    "amazon.com": "Amazon", "n11.com": "N11", "temu.com": "Temu", "etsy.com": "Etsy",
}
SLUG_RX = re.compile(r"[^a-z0-9]+")
_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slugify(text: str) -> str:
    return SLUG_RX.sub("-", text.translate(_TR).lower()).strip("-")[:80] or "urun"


def validate_url(url: str) -> tuple[bool, str]:
    url = (url or "").strip()
    try:
        u = urlparse(url)
    except ValueError:
        return False, "Geçersiz bağlantı"
    if u.scheme not in ("http", "https"):
        return False, "Yalnızca http/https bağlantıları kabul edilir"
    host = (u.hostname or "").lower()
    if not host or host in ("localhost",) or host.endswith(".local") or host.endswith(".internal"):
        return False, "Yerel adresler kabul edilmez"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, "Özel ağ adresleri kabul edilmez"
    except ValueError:
        pass
    if len(url) > 2000:
        return False, "Bağlantı çok uzun"
    return True, ""


def platform_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.").removeprefix("m.")
    for dom, name in PLATFORMS.items():
        if host == dom or host.endswith("." + dom):
            return name
    return "Diğer"


def queue_urls(con, text: str, note: str = "") -> dict:
    """Toplu yapıştırılan metinden bağlantıları ayıklar, kuyruğa ekler. Tekrarlar eklenmez."""
    found = re.findall(r"https?://[^\s<>\"']+", text or "")
    added, dup, bad = 0, 0, []
    for url in found:
        url = url.rstrip(").,;")
        ok, why = validate_url(url)
        if not ok:
            bad.append((url, why))
            continue
        cur = con.execute("INSERT OR IGNORE INTO research_queue(url, platform, note, created_at) VALUES (?,?,?,?)",
                          (url, platform_of(url), note[:300], db.now_iso()))
        added += cur.rowcount
        dup += 1 - cur.rowcount
    return {"eklenen": added, "tekrar": dup, "reddedilen": bad, "bulunan": len(found)}


def check_upload(name: str, size: int) -> tuple[bool, str]:
    ext = os.path.splitext(name.lower())[1]
    if ext not in config.ALLOWED_UPLOAD_EXT:
        return False, f"Yalnızca {', '.join(sorted(config.ALLOWED_UPLOAD_EXT))} dosyaları kabul edilir"
    if size > config.MAX_UPLOAD_BYTES:
        return False, "Dosya 5 MB sınırını aşıyor"
    return True, ""


CSV_FIELDS = ["name_tr", "name_en", "kategori", "tags", "satis_fiyati", "komisyon_orani", "kaynak_url",
              "yerli", "el_yapimi", "desi", "trend_asamasi", "rekabet", "not"]


def _bool(x):
    s = str(x).strip().lower()
    if s in ("1", "evet", "true", "var", "e"):
        return True
    if s in ("0", "hayir", "hayır", "false", "yok", "h"):
        return False
    return None


def _num(x):
    try:
        return float(str(x).replace(",", ".")) if str(x).strip() != "" else None
    except ValueError:
        return None


def parse_products_csv(text: str) -> list[dict]:
    """Basit CSV -> ürün kaydı taslağı. Bilinmeyen alanlar None kalır (uydurulmaz)."""
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        name = (row.get("name_tr") or "").strip()
        if not name:
            continue
        price = _num(row.get("satis_fiyati"))
        kom = _num(row.get("komisyon_orani"))
        rec = {
            "slug": slugify(name), "name_tr": name[:200], "name_en": (row.get("name_en") or "")[:200],
            "kategori": (row.get("kategori") or "").strip() or None,
            "tags": [t.strip() for t in (row.get("tags") or "").split("|") if t.strip()],
            "yerli": _bool(row.get("yerli")), "el_yapimi": _bool(row.get("el_yapimi")),
            "fiziksel": {"desi": {"deger": _num(row.get("desi")), "durum": "Satıcı beyanı" if _num(row.get("desi")) else "Bilinmiyor"}},
            "trend_asamasi": (row.get("trend_asamasi") or "yetersiz_veri").strip(),
            "rekabet": (row.get("rekabet") or "").strip() or None,
            "kaynaklar": [row["kaynak_url"]] if row.get("kaynak_url") and validate_url(row["kaynak_url"])[0] else [],
            "not": (row.get("not") or "")[:500],
        }
        if price:
            rec["finans"] = {"model": "komisyon", "satis_fiyati": price, "komisyon_orani": kom / 100 if kom and kom > 1 else kom}
        rec["bagimsiz_kaynak_sayisi"] = len(rec["kaynaklar"])
        out.append(rec)
    return out


def parse_products_json(text: str) -> list[dict]:
    data = json.loads(text)
    items = data if isinstance(data, list) else data.get("urunler", [])
    out = []
    for it in items:
        if not isinstance(it, dict) or not it.get("name_tr"):
            continue
        it = dict(it)
        it["slug"] = slugify(it.get("slug") or it["name_tr"])
        it["is_demo"] = bool(it.get("is_demo", False))
        out.append(it)
    return out


def save_products(con, recs: list[dict]) -> int:
    for r in recs:
        db.upsert_product(con, r["slug"], r["name_tr"], r.get("kategori") or "", r, r.get("name_en", ""), r.get("is_demo", False))
    return len(recs)


# ---- Gelen kutusu (tek yazıcı modeli) ----
def inbox_dir() -> str:
    return os.environ.get("VR_INBOX", os.path.join(os.path.dirname(config.DB_PATH), "inbox"))


def write_inbox(kind: str, payload: dict) -> str:
    """Panel/Telegram girdileri doğrudan veritabanına değil, benzersiz isimli dosyaya yazılır."""
    os.makedirs(inbox_dir(), exist_ok=True)
    name = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}_{kind}_{uuid.uuid4().hex[:8]}.json"
    path = os.path.join(inbox_dir(), name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tur": kind, "veri": payload}, f, ensure_ascii=False)
    return path


def process_inbox(con) -> dict:
    d = inbox_dir()
    if not os.path.isdir(d):
        return {"islenen": 0}
    done_dir = os.path.join(d, "islenen")
    os.makedirs(done_dir, exist_ok=True)
    stats = {"islenen": 0, "hata": 0}
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if not name.endswith(".json") or not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                item = json.load(f)
            kind, data = item.get("tur"), item.get("veri", {})
            if kind == "url":
                queue_urls(con, data.get("metin", ""), data.get("not", ""))
            elif kind == "urunler":
                save_products(con, parse_products_json(json.dumps(data.get("urunler", []))))
            elif kind == "profil":
                save_profile(con, data)
            elif kind == "etiket":
                con.execute("INSERT INTO gold_labels(comment_text, labels_json, created_at) VALUES (?,?,?)",
                            (data["metin"][:1000], json.dumps(data["etiketler"]), db.now_iso()))
            else:
                raise ValueError(f"bilinmeyen tür {kind}")
            os.replace(p, os.path.join(done_dir, name))
            stats["islenen"] += 1
        except Exception as e:  # hatalı dosya diğerlerini durdurmaz
            stats["hata"] += 1
            db.audit(con, "inbox_hata", f"{name}: {e}")
            os.replace(p, os.path.join(done_dir, name + ".hata"))
    return stats


def save_profile(con, profile: dict) -> None:
    from .profiles import validate_profile
    errs = validate_profile(profile)
    if errs:
        raise ValueError("; ".join(errs))
    con.execute("""INSERT INTO criteria_profiles(name, data_json, active, updated_at) VALUES (?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET data_json=excluded.data_json, active=excluded.active, updated_at=excluded.updated_at""",
                (profile["ad"], json.dumps(profile, ensure_ascii=False), int(profile.get("aktif", True)), db.now_iso()))


def load_profiles(con) -> list[dict]:
    from .profiles import DEFAULT_PROFILE
    rows = con.execute("SELECT data_json FROM criteria_profiles ORDER BY name").fetchall()
    return [json.loads(r["data_json"]) for r in rows] or [DEFAULT_PROFILE]


# ---- Güvenli dışa aktarma ----
def safe_cell(v):
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def export_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow({k: safe_cell(v) for k, v in r.items()})
    return buf.getvalue()
