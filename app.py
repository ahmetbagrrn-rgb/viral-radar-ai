"""VIRAL RADAR AI — Türkçe yönetim paneli (Android tablet uyumlu). Aşama 1 menüleri.
Panel veritabanına YAZMAZ (tek yazıcı modeli). Girdiler gelen kutusuna gider; iş bunları işler."""
import json
import os

import pandas as pd
import streamlit as st

from vr import auth, config, db, finance, ingest, profiles, remote
from vr.profiles import CRITERIA, COMPETITION, PORTFOLIOS, TREND_LABELS

st.set_page_config(page_title="Viral Radar AI", page_icon="📡", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding-top:1rem;max-width:860px}
.stButton button{min-height:3rem;width:100%;font-size:1.05rem}
div[data-testid="stMetricValue"]{font-size:1.4rem}
</style>""", unsafe_allow_html=True)


def secret(key, default=None):
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


# ---- Erişim kontrolü ----
PW_HASH = secret("PANEL_PASSWORD_HASH")
if PW_HASH:
    if not st.session_state.get("ok"):
        st.title("📡 Viral Radar AI")
        pw = st.text_input("Parola", type="password")
        if st.button("Giriş"):
            if auth.check_password(pw, PW_HASH):
                st.session_state.ok = True
                st.rerun()
            else:
                st.error("Parola hatalı.")
        st.stop()
else:
    with st.expander("🔐 Panel parolası tanımlı değil — kurmak için dokunun"):
        st.write("Bir parola yazın, oluşan satırı Streamlit > Settings > Secrets alanına ekleyin. "
                 "Parolanın kendisi hiçbir yere kaydedilmez.")
        np_ = st.text_input("Yeni parola (en az 10 karakter)", type="password", key="yeni_parola")
        if np_ and len(np_) >= 10:
            st.code(f'PANEL_PASSWORD_HASH = "{auth.hash_password(np_)}"', language="toml")
        elif np_:
            st.warning("Parola en az 10 karakter olmalı.")

REPO, TOKEN = secret("GITHUB_REPO"), secret("GITHUB_TOKEN")
REMOTE = bool(REPO and TOKEN and PW_HASH)  # parola yoksa jeton kullanılmaz (herkese açık panel koruması)


def send(kind: str, payload: dict) -> None:
    if REMOTE:
        ok = remote.push_inbox(REPO, TOKEN, kind, payload)
        st.success("Gelen kutusuna eklendi; bir sonraki çalıştırmada işlenecek.") if ok else st.error("Depoya yazılamadı (jeton/yetki).")
    else:
        ingest.write_inbox(kind, payload)
        st.success("Yerel gelen kutusuna eklendi. 'Şimdi işle' ile işleyebilirsiniz.")


@st.cache_data(ttl=300)
def load(profile_name: str | None = None):
    if not os.path.exists(config.DB_PATH):
        return [], [], []
    with db.connect() as con:
        profs = [json.loads(r["data_json"]) for r in con.execute("SELECT data_json FROM criteria_profiles ORDER BY name")]
        q = "SELECT e.result_json FROM evaluations e" + (" WHERE e.profile_name=?" if profile_name else "")
        ev = [json.loads(r["result_json"]) for r in con.execute(q, (profile_name,) if profile_name else ())]
        src = [dict(r) for r in con.execute("SELECT * FROM source_status ORDER BY layer, source")]
    return profs, ev, src


MENU = ["🏆 Bugünün ürünleri", "🔎 Ürün detayı", "🎛️ Kriter profilleri", "➕ Bağlantı ve dosya ekle",
        "🗑️ Elenen ürünler", "🧮 Kârlılık hesaplayıcı", "🩺 Veri kaynakları ve sistem"]
page = st.sidebar.radio("Menü", MENU)
st.sidebar.caption("Aşama 1 · Diğer menüler sonraki aşamalarda açılacak.")

profs, _, sources = load()
pnames = [p["ad"] for p in profs] or [profiles.DEFAULT_PROFILE["ad"]]
prof = st.selectbox("Profil", pnames) if page in MENU[:2] + [MENU[4]] else pnames[0]
_, ev, _ = load(prof)
if any(e.get("demo") for e in ev):
    st.info("Listede [DEMO] işaretli sentetik test ürünleri var; gerçek araştırma sonucu değildir.")


def tl(x):
    return "—" if x is None else f"{x:,.0f} TL".replace(",", ".")


# ---- 1. Bugünün ürünleri ----
if page == MENU[0]:
    st.header("Kriterlerinize uyan ürünler")
    if not ev:
        st.warning("Henüz değerlendirilmiş ürün yok. Ürün ekleyin veya işi çalıştırın.")
    ok = sorted([e for e in ev if not e["profil"]["elendi"] and e["karar"] != "RİSK NEDENİYLE ELE"],
                key=lambda e: (e["oncelik"], e["profil"]["profil_uyumu"] or 0), reverse=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Uygun ürün", len(ok))
    c2.metric("Şimdi değerlendir", sum(e["karar"] == "ŞİMDİ DEĞERLENDİR" for e in ok))
    c3.metric("Elenen", len(ev) - len(ok))
    pf = st.segmented_control("Portföy", ["Hepsi", "Yıl boyu", "Dönemsel", "Erken trend"], default="Hepsi")
    pmap = {"Yıl boyu": "yil_boyu", "Dönemsel": "donemsel", "Erken trend": "erken_trend"}
    show = [e for e in ok if pf in (None, "Hepsi") or e["portfoy"] == pmap[pf]][:10]
    for i, e in enumerate(show, 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {e['ad']}**{' `DEMO`' if e.get('demo') else ''}")
            st.markdown(f"**{e['karar']}** · {e['gerekce']}")
            a, b, c = st.columns(3)
            a.metric("Öncelik", e["oncelik"], help=e["oncelik_etiketi"])
            b.metric("Profil uyumu", f"%{e['profil']['profil_uyumu']}")
            c.metric("Veri güveni", e["veri_guveni"]["puan"])
            k = e.get("aylik_katki")
            st.caption(f"Trend: {TREND_LABELS.get(e['trend_asamasi'])} · Rekabet: {e.get('rekabet') or '—'} · "
                       f"Aylık katkı: {tl(k['min']) + ' – ' + tl(k['max']) if k else 'veri yok'}"
                       + (f" · Kısıt: {', '.join(e['oncelik_kisiti'])}" if e["oncelik_kisiti"] else ""))
    if ok:
        df = pd.DataFrame([{"Ürün": e["ad"], "Karar": e["karar"], "Öncelik": e["oncelik"], "Uyum": e["profil"]["profil_uyumu"],
                            "Genel": e["genel"]["puan"], "Zamanlama": e["zamanlama"]["bugun"], "Güven": e["veri_guveni"]["puan"],
                            "Portföy": e["portfoy"], "Demo": e.get("demo")} for e in ok])
        st.download_button("CSV indir", ingest.export_csv(df.to_dict("records")), "urunler.csv", "text/csv")

# ---- 2. Ürün detayı ----
elif page == MENU[1]:
    if not ev:
        st.warning("Ürün yok.")
        st.stop()
    sel = st.selectbox("Ürün", sorted({x["ad"] for x in ev}), key="urun_sec")
    e = next(x for x in ev if x["ad"] == sel)
    st.header(e["ad"] + (" `DEMO`" if e.get("demo") else ""))
    st.subheader(e["karar"])
    st.write(e["gerekce"])
    a, b, c, d = st.columns(4)
    a.metric("Genel fırsat", e["genel"]["puan"], help=f"aralık {e['genel']['min']}–{e['genel']['max']}")
    b.metric("Dönemsel (bugün)", e["zamanlama"]["bugun"])
    c.metric("Veri güveni", e["veri_guveni"]["puan"])
    d.metric("AI avatar", e["avatar"]["puan"])
    st.metric("Güncel öncelik", e["oncelik"], help=e["oncelik_etiketi"])
    with st.expander("Profil kriterleri", expanded=True):
        rows = [{"Kriter": v["etiket"], "Mod": v["mod"], "Sonuç": {True: "✅", False: "❌", None: "❔ doğrulanmadı"}[v["sonuc"]],
                 "Değer": v["deger"]} for v in e["profil"]["detay"].values()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Zamanlama"):
        z = e["zamanlama"]
        st.write({k: z[k] for k in ("bugun", "7_gun", "15_gun", "30_gun", "60_gun", "90_gun")})
        if z.get("yillik_harita") and z["yillik_harita"][0] is not None:
            st.bar_chart(pd.DataFrame({"Uygunluk": z["yillik_harita"]},
                                      index=["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]))
        if e.get("ozel_gun"):
            h = e["ozel_gun"]["hazirlik"]
            st.write(f"En yakın özel gün: **{e['ozel_gun']['ad']}** ({e['ozel_gun']['tarih']}) · yetişir: {h['yetisir']} · "
                     f"son güvenli başlangıç: {h['son_guvenli_baslangic']} · {h['not']}")
    with st.expander("Kârlılık (komisyon modeli)"):
        f = e["finans"]
        if "hata" in f:
            st.warning(f["hata"])
        else:
            st.write({"Net komisyon": tl(f["net_gelir"]), "Satış başına katkı": tl(f["reklam_sonrasi_katki"]),
                      "Marj": f"%{f['kar_marji_yuzde']}", "Varsayımlar": ", ".join(f["varsayimlar"]) or "yok"})
            if e.get("aylik_katki"):
                st.write(f"Aylık tahmini katkı: {tl(e['aylik_katki']['min'])} – {tl(e['aylik_katki']['max'])} (tahmindir)")
    with st.expander("Yorum istihbaratı"):
        y = e.get("yorum")
        st.write(y if y else "Yorum verisi yok.")
    with st.expander("Riskler"):
        st.write(e["riskler"] or "Kayıtlı risk yok (risk kontrolü yapılmadıysa bu bir güvence değildir).")
    with st.expander("Satışa hazırlık kapıları"):
        st.write(e["gates"])

# ---- 3. Kriter profilleri ----
elif page == MENU[2]:
    st.header("Kriter profilleri")
    st.caption("ZORUNLU: karşılamayan ürün elenir · TERCİH: sıralamayı etkiler · KAPALI: değerlendirilmez")
    base = st.selectbox("Düzenlenecek profil", pnames + ["➕ Yeni profil"])
    cur = next((p for p in profs if p["ad"] == base), profiles.new_profile("Yeni profil"))
    p = json.loads(json.dumps(cur))
    p["ad"] = st.text_input("Profil adı", p["ad"])
    p["aktif"] = st.toggle("Aktif", p.get("aktif", True))
    labels = {"zorunlu": "ZORUNLU", "tercih": "TERCİH", "kapali": "KAPALI"}
    for key, (label, _, kind) in CRITERIA.items():
        c = p["kriterler"].setdefault(key, {"mod": "kapali", "deger": profiles.DEFAULT_PROFILE["kriterler"][key]["deger"]})
        with st.container(border=True):
            c["mod"] = st.radio(label, list(labels), format_func=labels.get, index=list(labels).index(c["mod"]),
                                horizontal=True, key=f"m_{key}")
            if c["mod"] != "kapali":
                if kind in ("min", "max"):
                    c["deger"] = st.number_input("Değer", value=float(c["deger"] or 0), key=f"v_{key}")
                elif kind == "range":
                    lo, hi = st.columns(2)
                    c["deger"] = [lo.number_input("En az", value=float(c["deger"][0]), key=f"l_{key}"),
                                  hi.number_input("En çok", value=float(c["deger"][1]), key=f"h_{key}")]
                elif kind == "max_level":
                    c["deger"] = st.select_slider("Seviye", COMPETITION, value=c["deger"], key=f"v_{key}")
                elif key == "trend_asamasi":
                    c["deger"] = st.multiselect("Aşamalar", list(TREND_LABELS), c["deger"], format_func=TREND_LABELS.get, key=f"v_{key}")
                elif key == "portfoy":
                    c["deger"] = st.multiselect("Portföy", PORTFOLIOS, c["deger"], key=f"v_{key}")
                elif kind in ("in", "not_in"):
                    txt = st.text_input("Değerler (virgülle)", ", ".join(map(str, c["deger"])), key=f"v_{key}")
                    c["deger"] = [x.strip() for x in txt.split(",") if x.strip()]
    errs = profiles.validate_profile(p)
    for er in errs:
        st.error(er)
    if st.button("Profili kaydet", disabled=bool(errs)):
        send("profil", p)

# ---- 4. Bağlantı ve dosya ekle ----
elif page == MENU[3]:
    st.header("Araştırma kuyruğuna ekle")
    st.caption("Instagram, TikTok, YouTube, Trendyol vb. bağlantıları toplu yapıştırabilirsiniz. Bağlantı vermek yorumlara erişim izni anlamına gelmez.")
    txt = st.text_area("Bağlantılar", height=140)
    note = st.text_input("Not (isteğe bağlı)")
    if st.button("Kuyruğa ekle") and txt.strip():
        bad = [u for u in txt.split() if u.startswith("http") and not ingest.validate_url(u)[0]]
        if bad:
            st.warning(f"Reddedilecek bağlantılar: {bad}")
        send("url", {"metin": txt[:20000], "not": note})
    st.divider()
    st.subheader("Ürün dosyası (CSV / JSON)")
    st.caption("CSV sütunları: " + ", ".join(ingest.CSV_FIELDS))
    up = st.file_uploader("Dosya seçin", type=["csv", "json"])
    if up is not None:
        okf, why = ingest.check_upload(up.name, up.size)
        if not okf:
            st.error(why)
        else:
            raw = up.getvalue().decode("utf-8", errors="replace")
            try:
                recs = ingest.parse_products_csv(raw) if up.name.lower().endswith(".csv") else ingest.parse_products_json(raw)
                st.write(f"{len(recs)} ürün okundu.")
                if recs and st.button("Ürünleri gönder"):
                    send("urunler", {"urunler": recs})
            except Exception as ex:
                st.error(f"Dosya okunamadı: {ex}")

# ---- 8. Elenen ürünler ----
elif page == MENU[4]:
    st.header("Elenen ürünler")
    gone = [e for e in ev if e["profil"]["elendi"] or e["karar"] == "RİSK NEDENİYLE ELE"]
    if not gone:
        st.write("Elenen ürün yok.")
    for e in gone:
        reason = ", ".join(e["profil"]["eleme_nedenleri"]) or e["gerekce"]
        risks = ", ".join(r["code"] for r in e["riskler"])
        st.markdown(f"- **{e['ad']}** — {e['karar']}: {reason}" + (f" · Riskler: {risks}" if risks else ""))

# ---- 10. Kârlılık hesaplayıcı ----
elif page == MENU[5]:
    st.header("Kârlılık hesaplayıcı")
    st.caption("Tutarlar KDV dahil TL. Bilinmeyen maliyet sıfır kabul edilmez; boş bırakılan alanlarda temkinli varsayım kullanılır ve işaretlenir. Vergi hariç.")
    model = st.radio("İş modeli", ["komisyon", "dropshipping", "stoklu"], horizontal=True)
    price = st.number_input("Satış fiyatı", 0.0, value=750.0, step=10.0)
    kw = {"model": model, "satis_fiyati": price}
    if model == "komisyon":
        kw["komisyon_orani"] = st.slider("Komisyon oranı (%)", 0, 60, 20) / 100
    else:
        kw["tedarik_maliyeti"] = st.number_input("Tedarik maliyeti", 0.0, value=300.0, step=10.0)
        kw["kargo"] = st.number_input("Kargo (boş=varsayım 120)", 0.0, value=120.0)
        kw["pazaryeri_komisyon_orani"] = st.slider("Pazaryeri komisyonu (%)", 0, 30, 0) / 100
    kw["reklam_maliyeti_siparis_basina"] = st.number_input("Sipariş başına reklam (organik ise 0)", 0.0, value=0.0)
    kw["iade_orani"] = st.slider("İade oranı (%)", 0, 40, 8) / 100
    adet = st.slider("Aylık tahmini satış adedi (aralık)", 0, 1000, (20, 60))
    inp = finance.Inputs(**kw)
    ue = finance.unit_economics(inp)
    if "hata" in ue:
        st.error(ue["hata"])
    else:
        a, b, c = st.columns(3)
        a.metric("Satış başına katkı", tl(ue["reklam_sonrasi_katki"]))
        b.metric("Marj", f"%{ue['kar_marji_yuzde']}")
        c.metric("Aylık katkı", f"{tl(ue['reklam_sonrasi_katki'] * adet[0])} – {tl(ue['reklam_sonrasi_katki'] * adet[1])}")
        if ue["varsayimlar"]:
            st.caption("Varsayım kullanılan kalemler: " + ", ".join(ue["varsayimlar"]))
        st.write("Duyarlılık (satış başına katkı, TL):")
        st.dataframe(pd.DataFrame([finance.sensitivity(inp)]).T.rename(columns={0: "TL"}), width="stretch")
        st.write("Fiyat senaryoları:")
        st.dataframe(pd.DataFrame(finance.price_scenarios(inp, None)), hide_index=True, width="stretch")

# ---- 11. Veri kaynakları ve sistem ----
elif page == MENU[6]:
    st.header("Veri kaynakları ve sistem durumu")
    durum = {"calisiyor": "🟢 Çalışıyor", "kisitli": "🟡 Kısıtlı", "erisilemiyor": "🔴 Erişilemiyor", "baglanmadi": "⚪ Bağlanmadı"}
    if sources:
        st.dataframe(pd.DataFrame([{"Kaynak": s["source"], "Katman": s["layer"], "Durum": durum.get(s["status"], s["status"]),
                                    "Son başarılı": s["last_ok"] or "—", "Not": s["note"]} for s in sources]),
                     hide_index=True, width="stretch")
    else:
        st.write("Kaynak kaydı yok; iş henüz çalışmadı.")
    st.write(f"AI sağlayıcı: **{config.AI_PROVIDER}** · Ücretli API: **engelli** · Puanlama sürümü: {config.SCORING_VERSION}")
    st.write(f"Bağlantı modu: **{'Depo (GitHub)' if REMOTE else 'Yerel'}**")
    if REMOTE and st.button("Araştırma işini şimdi başlat"):
        st.success("İş başlatıldı.") if remote.dispatch_job(REPO, TOKEN) else st.error("Başlatılamadı (yetki).")
    if not REMOTE and st.button("Şimdi işle (yerel)"):
        from vr import runner
        try:
            st.write(runner.run())
            st.cache_data.clear()
        except RuntimeError as ex:
            st.error(str(ex))
