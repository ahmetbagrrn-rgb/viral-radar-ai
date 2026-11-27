"""31. Gerçek kârlılık motoru. İki iş modeli:
- 'dropshipping' / 'stoklu': satış fiyatı üzerinden ürün maliyeti düşülür.
- 'komisyon': kullanıcı yalnızca aracılık komisyonu kazanır, ürünü satın almaz (kullanıcının güncel kararı).

Kurallar: KDV dahil/hariç karıştırılmaz (tüm girdiler KDV DAHİL TL kabul edilir, net'e çevrilir),
gider iki kez düşülmez, bilinmeyen maliyet sıfır kabul edilmez (temkinli varsayım + işaret).
Gelir vergisi/kurumlar vergisi hesaba katılmaz -> muhasebeci ile doğrulanmalı."""
from dataclasses import dataclass, field, asdict

# Bilinmeyen maliyetler için TEMKİNLİ varsayımlar (kesin değil, işaretlenir)
CONSERVATIVE_DEFAULTS = {
    "kargo": 120.0,            # TL/sipariş, KDV dahil - taşıyıcı fiyatı ile doğrula
    "paketleme": 25.0,
    "odeme_komisyon_orani": 0.035,
    "pazaryeri_komisyon_orani": 0.0,
    "iade_orani": 0.10,
    "iade_kargo": 120.0,
    "hasar_orani": 0.02,
    "reklam_maliyeti_siparis_basina": None,   # gerçek veri yoksa fiyatın %25'i varsayılır
    "avatar_uretim_siparis_basina": 0.0,      # ücretsiz prompt aşamasında 0, ücretli üretimde girilmeli
    "musteri_hizmetleri": 5.0,
    "diger_degisken": 0.0,
}


@dataclass
class Inputs:
    model: str = "dropshipping"                 # dropshipping | stoklu | komisyon
    satis_fiyati: float = 0.0                   # KDV dahil
    kdv_orani: float = 0.20
    kdv_mukellefi: bool = True                  # indirilebilir KDV
    tedarik_maliyeti: float | None = None       # KDV dahil, birim
    komisyon_orani: float | None = None         # komisyon modelinde satıcıdan alınan pay
    komisyon_sabit: float | None = None
    kargo: float | None = None
    paketleme: float | None = None
    odeme_komisyon_orani: float | None = None
    pazaryeri_komisyon_orani: float | None = None
    iade_orani: float | None = None
    iade_kargo: float | None = None
    hasar_orani: float | None = None
    reklam_maliyeti_siparis_basina: float | None = None
    avatar_uretim_siparis_basina: float | None = None
    musteri_hizmetleri: float | None = None
    diger_degisken: float | None = None
    sabit_gider_aylik: float = 0.0
    beklenen_aylik_siparis: int = 0
    minimum_siparis_adedi: int = 0
    test_reklam_butcesi: float = 0.0
    tedarikci_odeme_vadesi_gun: int = 0
    tahsilat_suresi_gun: int = 7


def _fill(inp: Inputs) -> tuple[dict, list[str]]:
    vals, assumed = {}, []
    for k, default in CONSERVATIVE_DEFAULTS.items():
        v = getattr(inp, k)
        if v is None:
            if k == "reklam_maliyeti_siparis_basina":
                v = round(inp.satis_fiyati * 0.25, 2)
            else:
                v = default
            assumed.append(k)
        vals[k] = v
    return vals, assumed


def _net(x: float, rate: float, deductible: bool) -> float:
    return x / (1 + rate) if deductible else x


def unit_economics(inp: Inputs, overrides: dict | None = None) -> dict:
    v, assumed = _fill(inp)
    if overrides:
        v.update(overrides)
    r, ded = inp.kdv_orani, inp.kdv_mukellefi
    P = inp.satis_fiyati
    reklam = v["reklam_maliyeti_siparis_basina"]

    if inp.model == "komisyon":
        if inp.komisyon_orani is None and inp.komisyon_sabit is None:
            return {"hata": "Komisyon modelinde komisyon oranı veya sabit tutarı girilmeli.", "varsayimlar": assumed}
        brut = (inp.komisyon_orani or 0) * P + (inp.komisyon_sabit or 0)
        gelir_net = brut / (1 + r)  # komisyon faturası KDV'li kabul edilir
        degisken = _net(v["musteri_hizmetleri"] + v["diger_degisken"] + v["avatar_uretim_siparis_basina"], r, ded)
        iade_kaybi = v["iade_orani"] * gelir_net  # iade olursa komisyon geri alınır varsayımı
        katki_once = gelir_net - degisken - iade_kaybi
        urun = 0.0
    else:
        if inp.tedarik_maliyeti is None:
            return {"hata": "Tedarik maliyeti bilinmiyor: kârlılık hesaplanamaz (sıfır kabul edilmez).", "varsayimlar": assumed}
        gelir_net = P / (1 + r)
        urun = _net(inp.tedarik_maliyeti * (1 + v.get("_tedarik_artis", 0)), r, ded)
        kargo = _net(v["kargo"], r, ded)
        paket = _net(v["paketleme"], r, ded)
        pazaryeri = _net(P * v["pazaryeri_komisyon_orani"] * (1 + r), r, ded)  # komisyon + KDV'si
        odeme = P * v["odeme_komisyon_orani"]
        musteri = _net(v["musteri_hizmetleri"] + v["diger_degisken"] + v["avatar_uretim_siparis_basina"], r, ded)
        # İade: satış iptal (gelir kaybı yok sayılmaz -> gidiş+dönüş kargo + hasar kaybı)
        iade_kaybi = v["iade_orani"] * (kargo + _net(v["iade_kargo"], r, ded) + paket)
        hasar = v["hasar_orani"] * urun
        degisken = kargo + paket + pazaryeri + odeme + musteri
        katki_once = gelir_net - urun - degisken - iade_kaybi - hasar
        brut = gelir_net - urun

    reklam_net = _net(reklam, r, ded)
    katki_sonra = katki_once - reklam_net
    marj = katki_sonra / P if P else 0
    sabit_birim = (inp.sabit_gider_aylik / inp.beklenen_aylik_siparis) if inp.beklenen_aylik_siparis else None
    return {
        "model": inp.model,
        "satis_fiyati_kdv_dahil": round(P, 2),
        "net_gelir": round(gelir_net, 2),
        "urun_maliyeti_net": round(urun, 2),
        "brut_kar": round(brut, 2),
        "reklam_oncesi_katki": round(katki_once, 2),
        "reklam_sonrasi_katki": round(katki_sonra, 2),
        "kar_marji_yuzde": round(100 * marj, 1),
        "maksimum_cac": round(katki_once * (1 + r) if ded else katki_once, 2),
        "basabas_roas": round(P / (katki_once * (1 + r) if ded else katki_once), 2) if katki_once > 0 else None,
        "sabit_gider_birim": round(sabit_birim, 2) if sabit_birim else None,
        "net_kar_sabit_sonrasi": round(katki_sonra - sabit_birim, 2) if sabit_birim else None,
        "varsayimlar": assumed,
        "reklam_varsayim": "reklam_maliyeti_siparis_basina" in assumed,
        "kritik_maliyetler_dogrulandi": not ({"kargo", "reklam_maliyeti_siparis_basina", "iade_orani"} & set(assumed))
                                        and (inp.model == "komisyon" or inp.tedarik_maliyeti is not None),
    }


def breakeven_price(inp: Inputs) -> float | None:
    """Reklam sonrası katkı = 0 yapan satış fiyatı (ikili arama). Reklam maliyeti sabit tutulur."""
    if inp.model == "komisyon":
        return None
    base = unit_economics(inp)
    if "hata" in base:
        return None
    reklam = (inp.reklam_maliyeti_siparis_basina if inp.reklam_maliyeti_siparis_basina is not None
              else inp.satis_fiyati * 0.25)
    lo, hi = 0.0, max(inp.satis_fiyati * 10, 1000)
    for _ in range(60):
        mid = (lo + hi) / 2
        t = Inputs(**{**asdict(inp), "satis_fiyati": mid, "reklam_maliyeti_siparis_basina": reklam})
        if unit_economics(t)["reklam_sonrasi_katki"] > 0:
            hi = mid
        else:
            lo = mid
    return round(hi, 2)


def sensitivity(inp: Inputs) -> dict:
    base = unit_economics(inp)
    if "hata" in base:
        return {"hata": base["hata"]}
    reklam = (inp.reklam_maliyeti_siparis_basina if inp.reklam_maliyeti_siparis_basina is not None
              else inp.satis_fiyati * 0.25)
    out = {"temel": base["reklam_sonrasi_katki"]}
    for p in (25, 50, 100):
        out[f"reklam_+%{p}"] = unit_economics(inp, {"reklam_maliyeti_siparis_basina": reklam * (1 + p / 100)})["reklam_sonrasi_katki"]
    if inp.model != "komisyon":
        for p in (10, 20, 30):
            out[f"tedarik_+%{p}"] = unit_economics(inp, {"_tedarik_artis": p / 100})["reklam_sonrasi_katki"]
    for p in (10, 20):
        t = Inputs(**{**asdict(inp), "satis_fiyati": inp.satis_fiyati * (1 - p / 100),
                      "reklam_maliyeti_siparis_basina": reklam})
        out[f"fiyat_-%{p}"] = unit_economics(t)["reklam_sonrasi_katki"]
    iade = inp.iade_orani if inp.iade_orani is not None else CONSERVATIVE_DEFAULTS["iade_orani"]
    out["iade_orani_x2"] = unit_economics(inp, {"iade_orani": min(iade * 2, 1)})["reklam_sonrasi_katki"]
    return out


def scenarios(inp: Inputs) -> dict:
    s = sensitivity(inp)
    if "hata" in s:
        return s
    vals = [v for v in s.values() if isinstance(v, (int, float))]
    nakit = inp.minimum_siparis_adedi * (inp.tedarik_maliyeti or 0) + inp.test_reklam_butcesi
    return {
        "iyimser": round(s["temel"] * 1.15, 2),
        "normal": s["temel"],
        "kotumser": round(min(vals), 2),
        "en_kotu_makul_kayip_test": round(-inp.test_reklam_butcesi - inp.minimum_siparis_adedi * (inp.tedarik_maliyeti or 0) * 0.5, 2),
        "nakit_ihtiyaci": round(nakit, 2),
        "odeme_vadesi_etkisi_gun": inp.tahsilat_suresi_gun - inp.tedarikci_odeme_vadesi_gun,
        "duyarlilik": s,
        "not": "Reklam maliyeti gerçek veri değilse tüm sonuçlar varsayımdır. Vergi hariçtir.",
    }


def price_scenarios(inp: Inputs, competitor_median: float | None) -> list[dict]:
    """23. En az üç fiyat senaryosu (ekonomik / orta / premium)."""
    base = competitor_median or inp.satis_fiyati
    out = []
    for name, k in (("ekonomik", 0.85), ("orta", 1.0), ("premium", 1.25)):
        p = round(base * k, -1) - 0.1 if base * k > 100 else round(base * k, 2)  # psikolojik eşik: ...9,90
        t = Inputs(**{**asdict(inp), "satis_fiyati": p})
        ue = unit_economics(t)
        out.append({"senaryo": name, "fiyat": p, "katki": ue.get("reklam_sonrasi_katki"), "marj": ue.get("kar_marji_yuzde")})
    return out
