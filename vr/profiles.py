"""Bölüm 3: Kullanıcı kriter profilleri.
Her kriter ZORUNLU (eleme), TERCİH (profil uyumu) veya KAPALI olur.
Veri eksikliği nedeniyle kontrol edilemeyen zorunlu kriter ürünü ELEMEZ, ama 'doğrulanmadı' işaretler
ve ürün güçlü aday / ŞİMDİ DEĞERLENDİR olamaz."""
import copy

ZORUNLU, TERCIH, KAPALI = "zorunlu", "tercih", "kapali"
MODES = (ZORUNLU, TERCIH, KAPALI)

TREND_STAGES = ["henuz_kesfedilmemis", "erken_yukselis", "hizli_buyume", "viral", "rekabet_yogunlasiyor",
                "doygun", "dususte", "yetersiz_veri"]
TREND_LABELS = {"henuz_kesfedilmemis": "Henüz keşfedilmemiş", "erken_yukselis": "Erken yükseliş",
                "hizli_buyume": "Hızlı büyüme", "viral": "Viral", "rekabet_yogunlasiyor": "Rekabet yoğunlaşıyor",
                "doygun": "Doygun", "dususte": "Düşüşte", "yetersiz_veri": "Yetersiz veri"}
COMPETITION = ["dusuk", "orta", "yuksek", "asiri"]
PORTFOLIOS = ["yil_boyu", "donemsel", "erken_trend"]

# kriter: (etiket, alan, tür)  tür: min | max | range | true | false | in | not_in | max_level
CRITERIA = {
    "hedef_pazar": ("Hedef pazar", "pazar", "in"),
    "kategori_dahil": ("Dahil kategoriler", "kategori", "in"),
    "kategori_haric": ("Hariç kategoriler", "kategori", "not_in"),
    "min_turkiye_talebi": ("Minimum Türkiye talep sinyali (0-100)", "turkiye_talebi", "min"),
    "min_satin_alma_niyeti": ("Minimum bot filtreli satın alma niyeti (%)", "satin_alma_niyeti", "min"),
    "trend_asamasi": ("İzin verilen trend aşamaları", "trend_asamasi", "in"),
    "max_rekabet": ("Maksimum rekabet doyumu", "rekabet", "max_level"),
    "fiyat_araligi": ("Hedef satış fiyatı aralığı (TL)", "satis_fiyati", "range"),
    "min_komisyon_orani": ("Minimum komisyon oranı (%)", "komisyon_orani_yuzde", "min"),
    "min_aylik_katki": ("Minimum tahmini aylık katkı (TL)", "aylik_katki", "min"),
    "net_kar_hedefi": ("Net kâr hedefi (satış fiyatının %'si)", "net_marj", "min"),
    "zamaninda_yetisir": ("Yalnızca zamanında yetişebilecek", "yetisir", "true"),
    "portfoy": ("Portföy türü", "portfoy", "in"),
    "ozel_gunler": ("Belirli özel günler", "eslesen_ozel_gunler", "in"),
    "yerli_uretim": ("Yerli üretim", "yerli", "true"),
    "el_yapimi": ("El yapımı", "el_yapimi", "true"),
    "kisisellestirilebilir": ("Kişiselleştirilebilir", "kisisellestirilebilir", "true"),
    "hediye_uygun": ("Hediye olarak uygun", "hediye_uygun", "true"),
    "max_desi": ("Maksimum desi", "desi", "max"),
    "kirilgan_haric": ("Kırılgan ürün hariç", "kirilgan", "false"),
    "batarya_haric": ("Elektrik/batarya içeren hariç", "batarya", "false"),
    "min_yerli_uretici": ("Minimum doğrulanmış yerli üretici sayısı", "dogrulanmis_uretici", "min"),
    "min_avatar_puani": ("Minimum AI avatar puanı", "avatar_puani", "min"),
    "gercek_goruntu": ("Gerçek ürün görüntüsüyle gösterilebilir", "gercek_goruntu", "true"),
    "min_veri_guveni": ("Minimum veri güveni", "veri_guveni", "min"),
}

DEFAULT_PROFILE = {
    "ad": "Varsayılan: Türkiye, yerli, avatar uyumlu",
    "aktif": True,
    "kriterler": {
        "hedef_pazar": {"mod": ZORUNLU, "deger": ["TR"]},
        "kategori_dahil": {"mod": KAPALI, "deger": []},
        "kategori_haric": {"mod": KAPALI, "deger": []},
        "min_turkiye_talebi": {"mod": TERCIH, "deger": 40},
        "min_satin_alma_niyeti": {"mod": TERCIH, "deger": 5},
        "trend_asamasi": {"mod": TERCIH, "deger": ["henuz_kesfedilmemis", "erken_yukselis", "hizli_buyume"]},
        "max_rekabet": {"mod": TERCIH, "deger": "orta"},
        "fiyat_araligi": {"mod": KAPALI, "deger": [150, 2500]},
        "min_komisyon_orani": {"mod": KAPALI, "deger": 15},
        "min_aylik_katki": {"mod": KAPALI, "deger": 3000},
        "net_kar_hedefi": {"mod": TERCIH, "deger": 50},
        "zamaninda_yetisir": {"mod": TERCIH, "deger": True},
        "portfoy": {"mod": KAPALI, "deger": PORTFOLIOS},
        "ozel_gunler": {"mod": KAPALI, "deger": []},
        "yerli_uretim": {"mod": TERCIH, "deger": True},
        "el_yapimi": {"mod": TERCIH, "deger": True},
        "kisisellestirilebilir": {"mod": KAPALI, "deger": True},
        "hediye_uygun": {"mod": KAPALI, "deger": True},
        "max_desi": {"mod": TERCIH, "deger": 5},
        "kirilgan_haric": {"mod": TERCIH, "deger": True},
        "batarya_haric": {"mod": KAPALI, "deger": True},
        "min_yerli_uretici": {"mod": TERCIH, "deger": 1},
        "min_avatar_puani": {"mod": ZORUNLU, "deger": 45},
        "gercek_goruntu": {"mod": TERCIH, "deger": True},
        "min_veri_guveni": {"mod": KAPALI, "deger": 50},
    },
}


def new_profile(name: str) -> dict:
    p = copy.deepcopy(DEFAULT_PROFILE)
    p["ad"] = name
    return p


def _check(kind: str, actual, target):
    """True / False / None(bilinmiyor)."""
    if actual is None or (isinstance(actual, (list, str)) and len(actual) == 0 and kind in ("in", "not_in")):
        return None
    if kind == "min":
        return actual >= target
    if kind == "max":
        return actual <= target
    if kind == "range":
        return target[0] <= actual <= target[1]
    if kind == "true":
        return bool(actual) is True
    if kind == "false":
        return bool(actual) is False
    if kind == "max_level":
        return COMPETITION.index(actual) <= COMPETITION.index(target)
    vals = actual if isinstance(actual, list) else [actual]
    if kind == "in":
        if not target:
            return True
        return any(v in target for v in vals)
    if kind == "not_in":
        return not any(v in target for v in vals)
    raise ValueError(kind)


def evaluate(profile: dict, facts: dict) -> dict:
    """facts: ürünün profil alanlarına karşılık gelen değerleri (bilinmeyen = None)."""
    elendi, nedenler, dogrulanmadi, uyum_ok, uyum_top, detay = False, [], [], 0, 0, {}
    for key, conf in profile["kriterler"].items():
        if key not in CRITERIA or conf.get("mod") == KAPALI:
            continue
        label, field, kind = CRITERIA[key]
        if kind in ("in", "not_in") and not conf.get("deger"):
            continue  # boş liste = kısıt yok
        res = _check(kind, facts.get(field), conf.get("deger"))
        detay[key] = {"etiket": label, "mod": conf["mod"], "sonuc": res, "deger": facts.get(field)}
        if conf["mod"] == ZORUNLU:
            if res is False:
                elendi = True
                nedenler.append(label)
            elif res is None:
                dogrulanmadi.append(label)
        else:
            uyum_top += 1
            uyum_ok += 1 if res is True else 0   # bilinmeyen tercih karşılanmış sayılmaz
    return {
        "elendi": elendi,
        "eleme_nedenleri": nedenler,
        "dogrulanmayan_zorunlu": dogrulanmadi,
        "zorunlu_dogrulandi": not elendi and not dogrulanmadi,
        "profil_uyumu": round(100 * uyum_ok / uyum_top, 1) if uyum_top else None,
        "detay": detay,
    }


def validate_profile(p: dict) -> list[str]:
    errs = []
    if not p.get("ad"):
        errs.append("Profil adı boş.")
    for k, c in p.get("kriterler", {}).items():
        if k not in CRITERIA:
            errs.append(f"Bilinmeyen kriter: {k}")
        elif c.get("mod") not in MODES:
            errs.append(f"{k}: geçersiz mod")
        elif CRITERIA[k][2] == "range" and (len(c["deger"]) != 2 or c["deger"][0] > c["deger"][1]):
            errs.append(f"{k}: aralık hatalı")
    return errs
