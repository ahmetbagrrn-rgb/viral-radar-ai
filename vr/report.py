"""Bölüm 17: Günlük ürün raporu (Türkçe, kısa, sonuç odaklı). Demo veri açıkça etiketlenir."""
from datetime import date

from .profiles import TREND_LABELS

PORTFOY = {"yil_boyu": "Yıl boyu", "donemsel": "Dönemsel", "erken_trend": "Erken trend"}


def _line(r: dict) -> str:
    demo = " [DEMO]" if r.get("demo") else ""
    kat = r.get("aylik_katki")
    katki = f"{kat['min']:,}-{kat['max']:,} TL/ay".replace(",", ".") if kat else "aylık katkı: veri yok"
    kisit = f" (kısıt: {', '.join(r['oncelik_kisiti'])})" if r.get("oncelik_kisiti") else ""
    return (f"- **{r['ad']}**{demo} — {r['karar']} · öncelik {r['oncelik']} ({r['oncelik_etiketi']}{kisit}) · "
            f"profil uyumu %{r['profil']['profil_uyumu']} · veri güveni {r['veri_guveni']['puan']} · {katki} · "
            f"{TREND_LABELS.get(r['trend_asamasi'], r['trend_asamasi'])} · {PORTFOY.get(r['portfoy'])}")


def daily(results: dict, today: date) -> str:
    from .pipeline import rank
    out = [f"# Günlük Ürün Raporu — {today.strftime('%d.%m.%Y')}", ""]
    any_demo = any(r.get("demo") for rs in results.values() for r in rs)
    if any_demo:
        out += ["> Uyarı: [DEMO] işaretli ürünler sentetik test verisidir, gerçek araştırma sonucu değildir.", ""]
    for prof, rs in results.items():
        ranked = rank(rs)
        out += [f"## Profil: {prof}", ""]
        real = [r for r in ranked if not r.get("demo")]
        if not real:
            out += ["Gerçek veriye dayalı aday ürün yok. Kaynaklar Aşama 2'de bağlanınca dolacak.", ""]
        out += ["### En güçlü 10", ""] + [_line(r) for r in ranked[:10]] + [""]
        for key, label in PORTFOY.items():
            group = [r for r in ranked if r["portfoy"] == key][:5]
            if group:
                out += [f"### Portföy: {label}", ""] + [_line(r) for r in group] + [""]
        upcoming = [r for r in ranked if r.get("ozel_gun") and r["karar"] in ("HEMEN HAZIRLAN", "ŞİMDİ DEĞERLENDİR")]
        if upcoming:
            out += ["### Hazırlık zamanı gelenler", ""]
            for r in upcoming[:10]:
                h = r["ozel_gun"]["hazirlik"]
                out.append(f"- {r['ad']}: {r['ozel_gun']['ad']} ({r['ozel_gun']['tarih']}) — son güvenli başlangıç {h['son_guvenli_baslangic']}")
            out.append("")
        arsiv = [r for r in rs if r["karar"] in ("SEZONU BEKLE", "FIRSAT KAÇTI")]
        if arsiv:
            out += ["### Gelecek sezon arşivi", ""] + [f"- {r['ad']} — {r['gerekce']}" for r in arsiv[:10]] + [""]
        elenen = [r for r in rs if r["profil"]["elendi"] or r["karar"] == "RİSK NEDENİYLE ELE"]
        if elenen:
            out += ["### Elenenler", ""]
            for r in elenen[:15]:
                neden = ", ".join(r["profil"]["eleme_nedenleri"]) or r["gerekce"]
                out.append(f"- {r['ad']} — {neden}")
            out.append("")
    out += ["---", "Puanlar satış başarı olasılığı değildir. Ağırlıklar başlangıç hipotezidir."]
    return "\n".join(out)
