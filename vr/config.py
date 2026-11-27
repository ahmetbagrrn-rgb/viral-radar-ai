"""Ayarlanabilir sabitler. Ağırlıklar başlangıç hipotezidir; gerçek satış verisiyle kalibre edilir.
Kullanıcı onayı olmadan kalıcı olarak değiştirilmez (bkz. DECISIONS.md)."""
import os

SCORING_VERSION = "v5.1-hipotez"
TIMEZONE = "Europe/Istanbul"
DB_PATH = os.environ.get("VR_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "viral_radar.db"))

# 32. Genel ticari fırsat puanı (toplam 100) - zamanlama BİLEREK yok
OVERALL_WEIGHTS = {
    "turkiye_talebi": 12,
    "satin_alma_niyeti": 12,
    "karlilik": 15,
    "ai_avatar_uygunlugu": 15,
    "harcama_istegi_deger": 10,
    "rekabet_avantaji": 7,
    "yerli_el_yapimi": 6,
    "tedarikci_guvenilirligi": 5,
    "kargo_lojistik": 4,
    "dusuk_iade_kalite_riski": 4,
    "farklilastirma": 4,
    "dusuk_sermaye": 3,
    "tekrar_tamamlayici_satis": 3,
}

# 33. Dönemsel satış uygunluğu (toplam 100)
TIMING_WEIGHTS = {
    "kategori_talebi": 20,
    "alim_gucu_fiyat_uyumu": 15,
    "ozel_gun_mevsim": 15,
    "tedarik_teslimat_zamanlamasi": 15,
    "viral_buyume": 10,
    "donemsel_reklam_maliyeti": 10,
    "rakip_kampanya_yogunlugu": 5,
    "hedef_musteri_ihtiyaci": 5,
    "sezon_sonrasi": 5,
}

# 34. Veri güveni (toplam 100)
CONFIDENCE_WEIGHTS = {
    "kaynak_kalitesi": 25,
    "veri_kapsami": 25,
    "guncellik": 20,
    "bagimsiz_dogrulama": 15,
    "orneklem_guvenilirligi": 15,
}

# 35. AI avatar pazarlama puanı (toplam 100)
AVATAR_WEIGHTS = {
    "ilk_uc_saniye": 15,
    "gercek_urun_gosterme": 15,
    "problem_acikligi": 15,
    "turkce_kultur_uyumu": 10,
    "duygusal_hediye_degeri": 10,
    "guven_olusturma": 10,
    "senaryo_cesitliligi": 10,
    "organik_paylasim": 5,
    "dusuk_uretim_maliyeti": 5,
    "gorsel_dogruluk": 5,
}

# 36. Nihai öncelik
PRIORITY_OVERALL_W = 0.60
PRIORITY_TIMING_W = 0.40
PRIORITY_THRESHOLDS = [(90, "Öncelikli aday"), (80, "Güçlü aday"), (70, "Ayrıntılı araştırma"),
                       (60, "İzleme"), (0, "Düşük öncelik")]
MIN_CONFIDENCE_FOR_READY = 80

# 45. AI sağlayıcı: varsayılan KAPALI. Ücretli çağrılar kod düzeyinde engellenir.
AI_PROVIDER = os.environ.get("VR_AI_PROVIDER", "none")  # none | gemini_free
AI_MODEL_LIGHT = os.environ.get("VR_AI_MODEL_LIGHT", "gemini-flash-lite-latest")
AI_MODEL_DEEP = os.environ.get("VR_AI_MODEL_DEEP", "gemini-flash-latest")
ALLOW_PAID_APIS = False  # Değiştirilemez sabit: 0 TL bütçe kuralı
DAILY_AI_CALL_LIMIT = int(os.environ.get("VR_DAILY_AI_CALL_LIMIT", "200"))

# Güvenlik sınırları
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_UPLOAD_EXT = {".csv", ".json"}
