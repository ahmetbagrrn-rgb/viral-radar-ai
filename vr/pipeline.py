"""Ürün değerlendirme hattı: tek bir ürün kaydını kanıtlarıyla birlikte bütün motorlardan geçirir.
Girdi: ürün kaydı (dict) + kriter profili + bugün. Çıktı: puanlar, karar, profil sonucu, rapor alanları."""
from datetime import date, timedelta

from . import comments as cm
from . import compliance, finance, profiles, scoring, season

VERIFIED = {"Doğrulanmış"}


def _overall_criteria(rec: dict, intent: dict, fin: dict, avatar_total: float | None) -> dict:
    crit = dict(rec.get("kriterler_genel", {}))
    crit["satin_alma_niyeti"] = scoring.rule_purchase_intent(intent.get("rate"), intent.get("n", 0))
    if "hata" in fin:
        crit["karlilik"] = {"deger": None, "kanit": fin["hata"]}
    else:
        crit["karlilik"] = scoring.rule_profitability(fin["kar_marji_yuzde"], fin["kritik_maliyetler_dogrulandi"])
    fz = rec.get("fiziksel", {})
    crit["kargo_lojistik"] = scoring.rule_shipping(_v(fz.get("desi")), _v(fz.get("kirilgan")))
    sup = rec.get("ureticiler", [])
    crit["tedarikci_guvenilirligi"] = scoring.rule_supplier(sum(s.get("dogrulama") in VERIFIED for s in sup), len(sup))
    crit["ai_avatar_uygunlugu"] = ({"deger": avatar_total / 100, "kanit": f"AI avatar puanı {avatar_total}"}
                                    if avatar_total is not None else {"deger": None, "kanit": "avatar puanı yok"})
    y, e = rec.get("yerli"), rec.get("el_yapimi")
    if y is None and e is None:
        crit["yerli_el_yapimi"] = {"deger": None, "kanit": "üretim bilgisi yok"}
    else:
        crit["yerli_el_yapimi"] = {"deger": (0.6 if y else 0) + (0.4 if e else 0), "kanit": f"yerli={y}, el yapımı={e}"}
    if "turkiye_talebi" not in crit and rec.get("turkiye_talebi") is not None:
        crit["turkiye_talebi"] = {"deger": rec["turkiye_talebi"] / 100, "kanit": rec.get("turkiye_talebi_kanit", "talep sinyali")}
    return crit


def _v(x):
    """Doğrulama durumlu alanlardan değeri çıkar: {'deger':..,'durum':..} veya ham değer."""
    if isinstance(x, dict):
        return None if x.get("durum") == "Bilinmiyor" else x.get("deger")
    return x


def evaluate(rec: dict, profile: dict, today: date) -> dict:
    tags = rec.get("tags", [])
    # Yorumlar
    ca = cm.analyze(rec.get("yorumlar", []), rec.get("gorunen_yorum")) if rec.get("yorumlar") else None
    intent = {"rate": ca["satin_alma_niyeti_orani_bot_filtreli"], "n": ca["analiz_edilen"]} if ca else {}

    # Finans
    fin_inputs = finance.Inputs(**rec.get("finans", {})) if rec.get("finans") else None
    fin = finance.unit_economics(fin_inputs) if fin_inputs else {"hata": "Finans verisi yok"}
    scen = finance.scenarios(fin_inputs) if fin_inputs and "hata" not in fin else {}
    est = rec.get("aylik_satis_tahmini")  # [min, max] veya None
    aylik = None
    if est and "hata" not in fin:
        aylik = {"min": round(fin["reklam_sonrasi_katki"] * est[0]), "max": round(fin["reklam_sonrasi_katki"] * est[1])}

    # Puanlar
    av = scoring.avatar_score(rec.get("avatar_kriterleri", {}))
    av_known = None if len(av["eksik"]) == len(av["detay"]) else av["puan"]
    overall = scoring.overall_score(_overall_criteria(rec, intent, fin, av_known))
    conf = scoring.confidence_score(rec.get("guven_kriterleri", {}))
    tprof = scoring.timing_profile(rec, today)
    t_now = tprof["bugun"]
    t_fut = max(tprof[k] for k in ("7_gun", "15_gun", "30_gun", "60_gun", "90_gun"))
    prio = scoring.priority(overall["puan"], t_now)

    # Zamanlama ayrıntısı
    matches = [e for e in season.upcoming_events(today, 365) if set(e.tags) & set(tags)]
    yil_boyu = season.is_year_round(tags)
    nearest = next((e for e in matches if season.readiness(e.day, today, rec.get("lead_tasks"))["yetisir"]), None)
    first = matches[0] if matches else None
    ready_first = season.readiness(first.day, today, rec.get("lead_tasks"), verified=rec.get("sureler_dogrulandi", False)) if first else None
    yetisir = True if yil_boyu and not first else (ready_first["yetisir"] if ready_first else None)
    hazirlik = bool(nearest and (date.fromisoformat(season.readiness(nearest.day, today, rec.get("lead_tasks"))["son_guvenli_baslangic"]) - today).days <= 7)

    # Riskler
    flags = dict(rec.get("risk_flags", {}))
    if "hata" not in fin and fin["reklam_sonrasi_katki"] <= 0:
        flags["negatif_katki"] = True
    risks = compliance.evaluate(flags)

    trend = rec.get("trend_asamasi", "yetersiz_veri")
    portfoy = "erken_trend" if trend in ("henuz_kesfedilmemis", "erken_yukselis") else "yil_boyu" if yil_boyu else "donemsel"
    sup = rec.get("ureticiler", [])
    n_verified_local = sum(s.get("dogrulama") in VERIFIED and s.get("yerli") for s in sup)

    facts = {
        "pazar": rec.get("pazar", "TR"), "kategori": rec.get("kategori"),
        "turkiye_talebi": rec.get("turkiye_talebi"),
        "satin_alma_niyeti": intent.get("rate"),
        "trend_asamasi": trend, "rekabet": rec.get("rekabet"),
        "satis_fiyati": (rec.get("finans") or {}).get("satis_fiyati"),
        "komisyon_orani_yuzde": (rec["finans"]["komisyon_orani"] * 100) if (rec.get("finans") or {}).get("komisyon_orani") is not None else None,
        "aylik_katki": aylik["min"] if aylik else None,
        "net_marj": fin.get("kar_marji_yuzde"),
        "yetisir": yetisir, "portfoy": portfoy,
        "eslesen_ozel_gunler": [e.key for e in matches if (e.day - today).days <= 120],
        "yerli": rec.get("yerli"), "el_yapimi": rec.get("el_yapimi"),
        "kisisellestirilebilir": rec.get("kisisellestirilebilir"), "hediye_uygun": rec.get("hediye_uygun"),
        "desi": _v(rec.get("fiziksel", {}).get("desi")), "kirilgan": _v(rec.get("fiziksel", {}).get("kirilgan")),
        "batarya": _v(rec.get("fiziksel", {}).get("batarya")),
        "dogrulanmis_uretici": n_verified_local if sup else None,
        "avatar_puani": av_known,
        "gercek_goruntu": rec.get("gercek_goruntu"), "veri_guveni": conf["puan"],
    }
    prof = profiles.evaluate(profile, facts)

    dp = {
        "overall": overall["puan"], "timing_today": t_now, "timing_peak_future": t_fut,
        "confidence": conf["puan"], "avatar": av["puan"], "katki": fin.get("reklam_sonrasi_katki"),
        "kritik_risk": compliance.has_critical(risks), "trend": "dusuyor" if trend == "dususte" else None,
        "tedarikci_dogrulandi": any(s.get("dogrulama") in VERIFIED for s in sup),
        "yil_boyu": yil_boyu, "yillik_zirve": max([x for x in tprof["yillik_harita"] if x is not None], default=None), "firsat_kacti": bool(first and not ready_first["yetisir"] and not ready_first["kismen_yetisebilir"] and not nearest),
        "sezona_yetisir": bool(yetisir), "hazirlik_baslamali": hazirlik,
        "kritik_maliyetler_dogrulandi": fin.get("kritik_maliyetler_dogrulandi"),
        "risk_kontrolu": bool(rec.get("risk_kontrolu_yapildi")), "zorunlu_dogrulandi": prof["zorunlu_dogrulandi"],
        "profil_elendi": prof["elendi"], "profil_eleme_nedenleri": prof["eleme_nedenleri"],
    }
    karar, gerekce = scoring.decide(dp)

    # Güçlü aday kısıtı: doğrulanmamış zorunlu kriter veya < 2 bağımsız kaynak
    etiket = prio["etiket"]
    kisit = []
    if prof["dogrulanmayan_zorunlu"]:
        kisit.append("doğrulanmamış zorunlu kriter")
    if rec.get("bagimsiz_kaynak_sayisi", 0) < 2:
        kisit.append("2'den az bağımsız kaynak")
    if kisit and etiket in ("Öncelikli aday", "Güçlü aday"):
        etiket = "Ayrıntılı araştırma"

    return {
        "slug": rec["slug"], "ad": rec.get("name_tr"), "kategori": rec.get("kategori"), "demo": rec.get("is_demo", False),
        "karar": karar, "gerekce": gerekce,
        "oncelik": prio["puan"], "oncelik_etiketi": etiket, "oncelik_kisiti": kisit,
        "genel": overall, "zamanlama": tprof, "veri_guveni": conf, "avatar": av,
        "finans": fin, "senaryolar": scen, "aylik_katki": aylik,
        "fiyat_senaryolari": finance.price_scenarios(fin_inputs, rec.get("rakip_medyan")) if fin_inputs and "hata" not in fin else [],
        "yorum": {k: v for k, v in ca.items() if k != "satirlar"} if ca else None,
        "riskler": risks, "profil": prof, "portfoy": portfoy, "trend_asamasi": trend,
        "rekabet": rec.get("rekabet"),
        "ozel_gun": {"ad": first.name, "tarih": first.day.isoformat(), "hazirlik": ready_first} if first else None,
        "gates": scoring.ready_gates(dp),
    }


def rank(results: list[dict]) -> list[dict]:
    """Elenmeyenler: önce öncelik, eşitlikte profil uyumu."""
    ok = [r for r in results if not r["profil"]["elendi"] and r["karar"] != "RİSK NEDENİYLE ELE"]
    return sorted(ok, key=lambda r: (r["oncelik"], r["profil"]["profil_uyumu"] or 0), reverse=True)
