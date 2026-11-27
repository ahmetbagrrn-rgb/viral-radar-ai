"""30 + 38. Risk kontrolü ve reklam mevzuatı.
Kaynak: Ticari Reklam ve Haksız Ticari Uygulamalar Yönetmeliği değişikliği, RG 1/7/2026 sayı 33297,
yürürlük 1/8/2026 (md. 18/8 YZ açıklaması, 27/12 dijital kopya yasağı, 25/A hedefli reklam, 23/A etkileyici).
Bu modül hukuki görüş değildir; kategoriye özgü belge gereklilikleri resmî kaynaktan doğrulanmalıdır."""

RISK_RULES = [
    # (kod, koşul anahtarı, şiddet, açıklama)
    ("TAKLIT_MARKA", "taklit_marka", "kritik", "Taklit/replika marka ürünü satılamaz."),
    ("TELIF_TASARIM", "telif_riski", "yüksek", "Telif veya tasarım hakkı riski: tasarım sahibini doğrula."),
    ("COCUK_BOGULMA", "kucuk_parca_cocuk", "kritik", "Küçük parça + çocuk hedefi: oyuncak güvenliği ve yaş uyarısı zorunlu, belgeleri doğrula."),
    ("BATARYA", "batarya", "yüksek", "Batarya/elektrik: uygunluk belgeleri ve kargo kısıtları doğrulanmalı."),
    ("GIDA_TEMAS", "gida_temasi", "yüksek", "Gıda ile temas eden malzeme: uygunluk beyanı gerekli olabilir."),
    ("SAGLIK_IDDIASI", "saglik_iddiasi", "kritik", "Sağlık/tedavi iddiası reklamda kullanılamaz; ürün kategorisini doğrula."),
    ("KOZMETIK", "kozmetik", "yüksek", "Kozmetik mevzuatı (ÜTS kaydı vb.) doğrulanmalı."),
    ("YASAKLI", "yasakli_urun", "kritik", "Yasaklı veya kısıtlı ürün."),
    ("NEGATIF_KATKI", "negatif_katki", "yüksek", "Negatif katkı kârı: satış zarar üretir."),
    ("SAHTE_AI_GOSTERIM", "ai_gosterim_dogrulanamaz", "yüksek", "Ürün performansı görsel olarak doğrulanamıyor: sahte AI demonstrasyonu yapılamaz."),
    ("ITHALAT", "ithal", "orta", "İthalat: gümrük, fatura ve ticari ithalat şartları araştırılmalı."),
    ("FATURA_YOK", "faturasiz_tedarik", "yüksek", "Tedarikçi fatura kesmiyor: yasal satış riski."),
]


def evaluate(flags: dict) -> list[dict]:
    out = []
    for code, key, sev, note in RISK_RULES:
        if flags.get(key):
            out.append({"code": code, "severity": sev, "note": note})
    if flags.get("kategori") in ("oyuncak", "elektronik") and not flags.get("belgeler_dogrulandi"):
        out.append({"code": "BELGE_DOGRULANMADI", "severity": "yüksek",
                    "note": "Kategori belgeleri doğrulanmadı. CE her ürün için zorunlu varsayılmaz; kategoriye göre resmî kaynaktan kontrol edilmeli."})
    return out


def has_critical(risks: list[dict]) -> bool:
    return any(r["severity"] == "kritik" for r in risks)


AI_DISCLOSURE = "Bu reklamda yapay zekâ kullanılmıştır; insandan ayırt edilemeyecek dijital karakterlere yer verilmiştir."
AD_LABEL = "#reklam"

FORBIDDEN_AD_PATTERNS = {
    r"\bson \d+ (adet|ürün)\b": "Doğrulanmamış stok kıtlığı ifadesi",
    r"\b(ben de kullanıyorum|ben kullandım|bizzat denedim|evimde kullanıyorum)\b": "Avatarın kişisel kullanım iddiası (sahte deneyim)",
    r"\b(doktor(lar)? öneriyor|uzman onaylı|öğretmen tavsiyesi)\b": "Sahte uzman/kimlik referansı",
    r"\b(garantili sonuç|kesin çözüm|%100 etkili|mucize)\b": "Kanıtlanamayan fayda vaadi",
    r"\b(sadece bugün|son saatler|stoklar tükeniyor)\b": "Gerçek dışı aciliyet (doğrulanmadıysa)",
    r"\b(müşterilerimiz bayıldı|binlerce mutlu müşteri)\b": "Doğrulanmamış müşteri referansı",
    r"\b(tedavi eder|iyileştirir|zayıflatır)\b": "Sağlık iddiası",
}


def lint_ad(text: str) -> list[str]:
    import re
    t = text.lower()
    return [why for rx, why in FORBIDDEN_AD_PATTERNS.items() if re.search(rx, t)]
