"""32-37. Puan motorları ve karar sınıfları.

Temel ilke: Eksik veri puanı YÜKSELTMEZ. Bilinmeyen kriter nokta puana 0 katar, yalnızca 'maksimum olası'
aralığa ağırlığı kadar eklenir. Ağırlıklar başka kriterlere aktarılmaz (puan şişirme yok).
Nitel kriterlerde kanıt (gerekçe) yoksa değer YOK sayılır.
Puanlar satış başarı olasılığı DEĞİLDİR."""
from datetime import date, timedelta

from . import config, season

QUALITATIVE = {
    "ai_avatar_uygunlugu", "rekabet_avantaji", "farklilastirma", "harcama_istegi_deger",
    "ilk_uc_saniye", "gercek_urun_gosterme", "problem_acikligi", "turkce_kultur_uyumu", "duygusal_hediye_degeri",
    "guven_olusturma", "senaryo_cesitliligi", "organik_paylasim", "gorsel_dogruluk", "hedef_musteri_ihtiyaci",
}


def _clamp(x):
    return max(0.0, min(1.0, float(x)))


def weighted(criteria: dict, weights: dict) -> dict:
    """criteria: {ad: {'deger': 0..1 | None, 'kanit': str}} -> nokta, min, max, eksikler."""
    assert sum(weights.values()) == 100, "Ağırlık toplamı 100 olmalı"
    point, maxv, missing, rejected, detail = 0.0, 0.0, [], [], {}
    for name, w in weights.items():
        c = criteria.get(name) or {}
        v, ev = c.get("deger"), (c.get("kanit") or "").strip()
        if v is not None and name in QUALITATIVE and not ev:
            rejected.append(name)   # kanıtsız nitel değer kabul edilmez
            v = None
        if v is None:
            missing.append(name)
            maxv += w
            detail[name] = {"puan": None, "agirlik": w, "kanit": ev or "veri yok"}
        else:
            p = w * _clamp(v)
            point += p
            maxv += p
            detail[name] = {"puan": round(p, 2), "agirlik": w, "kanit": ev}
    return {"puan": round(point, 1), "min": round(point, 1), "max": round(maxv, 1),
            "eksik": missing, "kanitsiz_reddedilen": rejected, "detay": detail}


# ---- Ölçülebilir kriterler için deterministik dönüşüm kuralları ----
def rule_purchase_intent(filtered_rate_pct: float | None, sample_n: int) -> dict:
    if filtered_rate_pct is None or sample_n == 0:
        return {"deger": None, "kanit": "yorum verisi yok"}
    v = _clamp(filtered_rate_pct / 15.0)           # %15+ bot filtreli satın alma niyeti = tam puan
    if sample_n < 30:
        v *= 0.5                                    # küçük örneklem cezası
    return {"deger": v, "kanit": f"bot filtreli niyet %{filtered_rate_pct}, n={sample_n}"}


def rule_profitability(margin_pct: float | None, verified: bool) -> dict:
    if margin_pct is None:
        return {"deger": None, "kanit": "kârlılık hesaplanamadı"}
    v = _clamp(margin_pct / 30.0)                   # reklam sonrası %30+ marj = tam puan
    if not verified:
        v *= 0.7
    return {"deger": v, "kanit": f"reklam sonrası marj %{margin_pct}{'' if verified else ' (varsayımlı maliyetler)'}"}


def rule_shipping(desi: float | None, fragile: bool | None) -> dict:
    if desi is None:
        return {"deger": None, "kanit": "desi bilinmiyor"}
    v = 1.0 if desi <= 2 else 0.7 if desi <= 5 else 0.4 if desi <= 10 else 0.1
    if fragile:
        v *= 0.6
    return {"deger": v, "kanit": f"desi={desi}, kırılgan={fragile}"}


def rule_supplier(n_verified: int, n_total: int) -> dict:
    if n_total == 0:
        return {"deger": None, "kanit": "tedarikçi yok"}
    return {"deger": _clamp(n_verified / 3), "kanit": f"{n_verified}/{n_total} doğrulanmış tedarikçi"}


def overall_score(criteria: dict) -> dict:
    return weighted(criteria, config.OVERALL_WEIGHTS)


def avatar_score(criteria: dict) -> dict:
    return weighted(criteria, config.AVATAR_WEIGHTS)


def confidence_score(criteria: dict) -> dict:
    return weighted(criteria, config.CONFIDENCE_WEIGHTS)


def timing_score(product: dict, today: date, horizon_days: int = 0) -> dict:
    """Belirli bir ufuk için dönemsel uygunluk. product: tags, timing_inputs, lead_tasks."""
    target = today + timedelta(days=horizon_days)
    tags = product.get("tags", [])
    fm = season.monthly_fit_map(tags)
    ti = product.get("timing_inputs", {})
    crit = {}
    m = fm[target.month - 1]
    crit["kategori_talebi"] = {"deger": None if m is None else m / 100,
                               "kanit": f"aylık hipotez haritası ({target.strftime('%m')}. ay) - doğrulanmamış"}
    # Özel gün / mevsim: hedef tarihten sonraki 45 gün içinde eşleşen etiketli olay var mı?
    # Ürünün kendi sezon haritası olayın ayında zayıfsa (ör. yazlık çanta + yılbaşı) olay eşleşmez
    match = [e for e in season.upcoming_events(target, 45) if set(e.tags) & set(tags)
             and (fm[e.day.month - 1] is None or fm[e.day.month - 1] >= 50)]
    if match:
        e = match[0]
        d = (e.day - target).days
        v = 1.0 if d <= e.lead_days else max(0.3, 1 - (d - e.lead_days) / 45)
        crit["ozel_gun_mevsim"] = {"deger": v, "kanit": f"{e.name} ({e.day}), {d} gün sonra"}
        r = season.readiness(e.day, today, product.get("lead_tasks"), verified=product.get("sureler_dogrulandi", False))
        crit["tedarik_teslimat_zamanlamasi"] = {
            "deger": 1.0 if r["yetisir"] else 0.4 if r["kismen_yetisebilir"] else 0.0,
            "kanit": f"gereken {r['gereken_gun_kotumser']} gün / kalan {r['gun_kaldi']} gün"}
    else:
        yr = season.is_year_round(tags)
        crit["ozel_gun_mevsim"] = {"deger": 0.5 if yr else 0.0, "kanit": "yakın eşleşen özel gün yok" + (" (yıl boyu ürün)" if yr else "")}
        crit["tedarik_teslimat_zamanlamasi"] = {"deger": 0.8 if yr else None,
                                                 "kanit": "yıl boyu satış; teslim penceresi kısıtı yok" if yr else "olay yok"}
    for k in ("alim_gucu_fiyat_uyumu", "viral_buyume", "donemsel_reklam_maliyeti", "rakip_kampanya_yogunlugu",
              "hedef_musteri_ihtiyaci", "sezon_sonrasi"):
        crit[k] = ti.get(k) or {"deger": None, "kanit": "veri yok"}
    res = weighted(crit, config.TIMING_WEIGHTS)
    res["hedef_tarih"] = target.isoformat()
    return res


def timing_profile(product: dict, today: date) -> dict:
    prof = {f"{h}_gun" if h else "bugun": timing_score(product, today, h)["puan"] for h in (0, 7, 15, 30, 60, 90)}
    fm = season.monthly_fit_map(product.get("tags", []))
    prof["yillik_harita"] = fm
    if fm[0] is not None:
        best = max(range(12), key=lambda i: fm[i])
        prof["en_uygun_ay"] = best + 1
    return prof


def priority(overall: float, timing_today: float) -> dict:
    v = overall * config.PRIORITY_OVERALL_W + timing_today * config.PRIORITY_TIMING_W
    label = next(l for t, l in config.PRIORITY_THRESHOLDS if v >= t)
    return {"puan": round(v, 1), "etiket": label}


def ready_gates(p: dict) -> dict:
    g = {
        "veri_guveni_80": p.get("confidence", 0) >= config.MIN_CONFIDENCE_FOR_READY,
        "kritik_maliyetler_dogrulandi": bool(p.get("kritik_maliyetler_dogrulandi")),
        "en_az_bir_dogrulanmis_uretici": bool(p.get("tedarikci_dogrulandi")),
        "risk_kontrolu_tamam": bool(p.get("risk_kontrolu")),
        "zorunlu_kriterler_dogrulandi": bool(p.get("zorunlu_dogrulandi")),
        "pozitif_katki": (p.get("katki") or 0) > 0,
        "sezona_yetisir": bool(p.get("sezona_yetisir")),
        "gercekci_avatar_reklami": p.get("avatar", 0) >= 60,
    }
    g["satisa_hazir"] = all(g.values())
    return g


def decide(p: dict) -> tuple[str, str]:
    """37. Karar sınıfı + gerekçe. p: overall, timing_today, timing_peak_future, confidence, avatar, katki,
    kritik_risk, trend, tedarikci_dogrulandi, yil_boyu, firsat_kacti, sezona_yetisir, hazirlik_baslamali"""
    if p.get("kritik_risk"):
        return "RİSK NEDENİYLE ELE", "Çözümlenmemiş kritik risk var."
    if p.get("profil_elendi"):
        return "PROFİLE UYMUYOR", "Zorunlu kriter karşılanmadı: " + ", ".join(p.get("profil_eleme_nedenleri", []))
    if p.get("confidence", 0) < 50:
        return "DAHA FAZLA VERİ GEREKLİ", f"Veri güveni {p.get('confidence', 0)} < 50."
    if p.get("katki") is not None and p["katki"] <= 0:
        return "FİYATI UYGUN DEĞİL", "Reklam sonrası katkı kârı sıfır veya negatif."
    if p.get("avatar", 100) < 45:
        return "AI AVATAR İLE PAZARLANMASI ZOR", f"Avatar puanı {p.get('avatar')}."
    if p.get("trend") == "dusuyor":
        return "TREND DÜŞÜYOR", "Tekrarlı ölçümlerde düşüş."
    gates = ready_gates(p)
    t_now, t_fut = p.get("timing_today", 0), p.get("timing_peak_future", 0)
    if p.get("firsat_kacti") and t_fut < 50 and not p.get("yil_boyu"):
        return "FIRSAT KAÇTI", "Bu sezona yetişemiyor; arşive alındı (silinmedi)."
    if t_now >= 65 and p.get("overall", 0) >= 70:
        if gates["satisa_hazir"]:
            return "ŞİMDİ DEĞERLENDİR", "Zamanlama ve genel puan yüksek, bütün hazırlık kapıları geçti."
        if not gates["en_az_bir_dogrulanmis_uretici"]:
            return "ÜRETİCİYİ DOĞRULA", "Zamanlama uygun ama doğrulanmış üretici adayı yok."
        return "DAHA FAZLA VERİ GEREKLİ", "Zamanlama uygun; eksik kapılar: " + ", ".join(k for k, v in gates.items() if not v and k != "satisa_hazir")
    if p.get("hazirlik_baslamali") and t_fut >= 65 and p.get("overall", 0) >= 60:
        return "HEMEN HAZIRLAN", "Gelecek fırsata yetişmek için hazırlık şimdi başlamalı."
    if p.get("yil_boyu") and p.get("overall", 0) >= 60:
        return "YIL BOYU UYGUN", "Belirgin sezon bağımlılığı yok."
    if not p.get("yil_boyu") and p.get("overall", 0) >= 60 and (t_fut >= 65 or (p.get("yillik_zirve") or 0) >= 65):
        return "SEZONU BEKLE", "Ürün güçlü ama şu an sezon dışı; gelecek sezon arşivinde."
    if not p.get("tedarikci_dogrulandi") and p.get("overall", 0) >= 70:
        return "ÜRETİCİYİ DOĞRULA", "Genel puan iyi, üretici adayı doğrulanmadı."
    return "DAHA FAZLA VERİ GEREKLİ", "Karar için yeterli sinyal yok."
