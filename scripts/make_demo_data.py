"""Sentetik DEMO veri üretir (yalnızca yazılım testi içindir; gerçek araştırma sonucu DEĞİLDİR).
Kullanım: python scripts/make_demo_data.py [çıktı.json]"""
import json
import random
import sys

FAST = {  # komisyon modeli: üretici gönderir, numune/ stok yok -> kısa hazırlık (hipotez)
    "uretici_bulma": (2, 4, []), "numune": (2, 4, ["uretici_bulma"]), "kalite_kontrol": (1, 1, ["numune"]),
    "urun_gorselleri": (1, 2, ["numune"]), "avatar_reklam": (1, 3, ["urun_gorselleri"]),
    "satis_sayfasi": (1, 1, ["urun_gorselleri"]), "reklam_testi": (2, 4, ["avatar_reklam", "satis_sayfasi", "kalite_kontrol"]),
    "tedarik": (1, 2, ["kalite_kontrol"]), "teslimat": (1, 3, ["tedarik", "reklam_testi"]),
}

BUY = ["Bunu almak istiyorum, fiyatı ne kadar?", "Ben de istiyorum link var mı?", "Anneme hediye almak istiyorum",
       "Türkiye'de nereden bulabilirim?", "Kaç TL acaba, kargo var mı?", "Çocuğuma almak istiyorum çok güzel",
       "Bunun yerlisi yok mu?", "İsim yazdırılabiliyor mu? Kişiye özel olsa alırım", "bende istiyorum nasıl sipariş veririm",
       "Rengi başka var mı? Bedeni nedir?", "Sevgilime almak istiyorum", "I want this! how much?", "بكم هذا؟ أريد واحد"]
NEG = ["Çok güzel ama pahalı", "Kargo parası üründen pahalı", "Kalitesiz duruyor bir haftada bozulur",
       "Bu ürün gerçekten işe yarıyor mu? Reklamda göründüğü gibi değil bence", "Gereksiz bir ürün kim alır bunu",
       "Çocuklar için güvenli mi? küçük parçası var", "Bunun aynısı aliexpress'te var daha ucuz"]
SARC = ["Kesin alırım 😂😂", "Tabii ki alırım hemen koşuyorum 🙄", "Bir bu eksikti 😂", "Böbreğimi satıp alayım bari"]
PRAISE = ["Çok güzel", "Harika 😍", "Muhteşem 🔥", "❤️❤️", "wow amazing"]
OTHER = ["Müzik ne?", "Video güzel olmuş", "Ne tatlı kadın", "@ayse bak", "@mehmet.k bunu gördün mü"]
BOT = ["Profilime bak kazanç fırsatı www.kazan.com", "Follow me check my bio", "DM at takip et takip edeyim"]


def comments(rng, buy_bias):
    out = []
    for _ in range(rng.randint(14, 18)):
        r = rng.random()
        pool = BUY if r < buy_bias else NEG if r < buy_bias + 0.2 else SARC if r < buy_bias + 0.3 else PRAISE if r < buy_bias + 0.45 else OTHER
        out.append(rng.choice(pool))
    out += [rng.choice(BOT)] * rng.randint(0, 3)  # tekrarlı spam kümesi
    return out


def crit(v, k="demo kanıt"):
    return {"deger": v, "kanit": k}


def product(rng, name, kategori, tags, price, kom, *, yerli=True, el=True, desi=1.5, kirilgan=False, batarya=False,
            trend="erken_yukselis", rekabet="orta", talep=60, avatar=0.75, conf=0.85, risk=None, buy=0.4,
            sup_verified=2, sales=(20, 60), fast=True, missing=False, strong=False):
    rec = {"name_tr": name, "kategori": kategori, "tags": tags, "is_demo": True, "pazar": "TR"}
    if missing:
        return rec
    rec.update({
        "yerli": yerli, "el_yapimi": el, "kisisellestirilebilir": "kisisellestirilmis" in tags, "hediye_uygun": "hediye" in tags,
        "gercek_goruntu": True,
        "fiziksel": {"desi": {"deger": desi, "durum": "Satıcı beyanı"}, "kirilgan": {"deger": kirilgan, "durum": "Satıcı beyanı"},
                     "batarya": {"deger": batarya, "durum": "Doğrulanmış"}},
        "trend_asamasi": trend, "rekabet": rekabet, "turkiye_talebi": talep, "bagimsiz_kaynak_sayisi": 3,
        "finans": {"model": "komisyon", "satis_fiyati": price, "komisyon_orani": kom, "reklam_maliyeti_siparis_basina": 0.0,
                   "kargo": 0.0, "iade_orani": 0.08},
        "aylik_satis_tahmini": list(sales), "rakip_medyan": price * rng.uniform(0.9, 1.15),
        "ureticiler": [{"ad": f"Demo Atölye {i+1}", "dogrulama": "Doğrulanmış" if i < sup_verified else "Satıcı beyanı", "yerli": yerli}
                       for i in range(3)],
        "kriterler_genel": {
            "turkiye_talebi": crit(talep / 100), "harcama_istegi_deger": crit(0.7), "rekabet_avantaji": crit({"dusuk": .9, "orta": .6, "yuksek": .3, "asiri": .1}[rekabet]),
            "dusuk_iade_kalite_riski": crit(0.7), "farklilastirma": crit(0.7 if el else 0.4), "dusuk_sermaye": crit(1.0),
            "tekrar_tamamlayici_satis": crit(0.5)},
        "avatar_kriterleri": {k: crit(avatar) for k in ("ilk_uc_saniye", "gercek_urun_gosterme", "problem_acikligi", "turkce_kultur_uyumu",
                              "duygusal_hediye_degeri", "guven_olusturma", "senaryo_cesitliligi", "organik_paylasim", "dusuk_uretim_maliyeti", "gorsel_dogruluk")},
        "guven_kriterleri": {k: crit(conf) for k in ("kaynak_kalitesi", "veri_kapsami", "guncellik", "bagimsiz_dogrulama", "orneklem_guvenilirligi")},
        "timing_inputs": {k: crit(0.7) for k in ("alim_gucu_fiyat_uyumu", "viral_buyume", "donemsel_reklam_maliyeti",
                                                 "rakip_kampanya_yogunlugu", "hedef_musteri_ihtiyaci", "sezon_sonrasi")},
        "risk_flags": risk or {}, "risk_kontrolu_yapildi": True,
        "yorumlar": comments(rng, buy), "gorunen_yorum": 800,
    })
    if strong:
        rec["kriterler_genel"].update({k: crit(0.9) for k in ("harcama_istegi_deger", "dusuk_iade_kalite_riski", "farklilastirma", "tekrar_tamamlayici_satis")})
        rec["kriterler_genel"]["turkiye_talebi"] = crit(0.85)
    if fast:
        rec["lead_tasks"] = FAST
    return rec


def build(seed=42):
    rng = random.Random(seed)
    P = lambda *a, **k: product(rng, *a, **k)
    return [
        P("El örgüsü hasır plaj çantası", "kadin_aksesuar", ["yaz_aksesuar", "kadin_aksesuar", "el_yapimi"], 650, 0.25),
        P("Kişiye özel isimli seramik kupa", "hediye", ["hediye", "kisisellestirilmis"], 350, 0.2, kirilgan=True, desi=2),
        P("Montessori ahşap meşgul tahtası", "cocuk", ["cocuk_egitici", "hediye"], 900, 0.18, el=False, buy=0.5),
        P("Montessori boncuk labirent (küçük parçalı)", "cocuk", ["cocuk_egitici"], 400, 0.2, risk={"kucuk_parca_cocuk": True}),
        P("Havalandırmalı kedi taşıma çantası", "evcil_hayvan", ["evcil_hayvan", "seyahat"], 1200, 0.15, el=False, desi=6),
        P("Ucuz telefon tutucu", "pratik", ["tasarruf"], 60, 0.05, yerli=False, el=False, sales=(5, 10)),
        P("LED ışıklı makyaj aynası", "kadin_aksesuar", ["kadin_aksesuar", "hediye"], 700, 0.15, yerli=False, el=False, batarya=True),
        P("Zayıflatıcı bitkisel kemer", "saglik", ["tasarruf"], 500, 0.3, yerli=False, el=False, risk={"saglik_iddiasi": True}),
        P("Marka logolu replika çanta", "kadin_aksesuar", ["kadin_aksesuar"], 900, 0.3, yerli=False, el=False, risk={"taklit_marka": True}),
        P("Hassas su arıtma filtresi", "ev", ["ev_duzen"], 1500, 0.12, el=False, avatar=0.2, risk={"ai_gosterim_dogrulanamaz": True}),
        P("Adı bilinen ama verisi olmayan ürün", "diger", [], 0, 0, missing=True),
        P("El yapımı keçe yılbaşı süsü seti", "hediye", ["yilbasi", "hediye", "el_yapimi"], 450, 0.25, trend="hizli_buyume", buy=0.55, talep=85, strong=True),
        P("Kişiye özel harf kolye", "kadin_aksesuar", ["sevgililer", "hediye", "kisisellestirilmis", "kadin_aksesuar"], 800, 0.2, trend="hizli_buyume"),
        P("Anneler Günü el örgüsü çanta", "kadin_aksesuar", ["el_yapimi", "kadin_aksesuar"], 950, 0.25, trend="henuz_kesfedilmemis"),
        P("Çekmece içi düzenleyici set", "ev", ["ev_duzen"], 300, 0.18, el=False, rekabet="yuksek"),
        P("Yıkanabilir silikon saklama kapağı", "ev", ["tasarruf", "ev_duzen"], 200, 0.15, el=False, trend="erken_yukselis"),
        P("Mıknatıslı baharat rafı", "ev", ["ev_duzen"], 550, 0.17, el=False, trend="henuz_kesfedilmemis", rekabet="dusuk", conf=0.6),
        P("Viral kar küresi lamba", "hediye", ["yilbasi", "hediye"], 400, 0.12, yerli=False, el=False, trend="doygun", rekabet="asiri"),
        P("Fidget spinner", "oyuncak", ["cocuk_egitici"], 120, 0.1, yerli=False, el=False, trend="dususte", rekabet="asiri"),
        P("El örgüsü kış beresi ve atkı seti", "kadin_aksesuar", ["kis_aksesuar", "el_yapimi", "hediye"], 700, 0.25, trend="hizli_buyume", buy=0.55, talep=85, strong=True, rekabet="dusuk"),
        P("Karne hediyesi eğitici kutu oyunu", "cocuk", ["cocuk_egitici", "hediye"], 600, 0.15, el=False),
        P("Düşük komisyonlu hacimli çorap seti", "giyim", ["tasarruf"], 250, 0.08, el=False, sales=(300, 600), rekabet="yuksek"),
        P("Kişiye özel isimli seramik kupa", "hediye", ["hediye", "kisisellestirilmis"], 360, 0.2, kirilgan=True, desi=2),  # tekrar kaydı
    ]


if __name__ == "__main__":
    data = build()
    path = sys.argv[1] if len(sys.argv) > 1 else "data/demo_products.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(data)} demo kayıt, {sum(len(d.get('yorumlar', [])) for d in data)} yorum -> {path}")
