# Viral Radar AI — Ürün Bulucu (V5.1, Aşama 1)

Kullanıcının belirlediği kriterlere uyan ürünleri bulan, kanıtla değerlendiren ve sıralayan araştırma sistemi.
Satış, sipariş, reklam yayını, içerik üretimi veya üretici iletişimi **yapmaz**.

## Ne yapar (Aşama 1)
- Kriter profilleri: her kriter ZORUNLU / TERCİH / KAPALI.
- Dört puan motoru (genel fırsat, dönemsel uygunluk, veri güveni, AI avatar) + öncelik + karar sınıfları.
- Dinamik Türkiye alışveriş takvimi, zamanında yetişme (kritik yol) hesabı.
- Yorum analizi (C01–C30), alay ve bot şüphesi ayrımı, kişisel veri anonimleştirme.
- Komisyon / dropshipping / stoklu kârlılık hesabı, duyarlılık ve fiyat senaryoları.
- Risk ve reklam mevzuatı denetimi.
- Bağlantı kuyruğu, CSV/JSON ürün aktarımı, günlük rapor.
- Türkçe, tablet uyumlu Streamlit paneli.

## Mimari
Python motoru (`vr/`) · Streamlit paneli (`app.py`) · GitHub Actions tek yazıcı iş (`.github/workflows/research.yml`)
· SQLite (`data/viral_radar.db`) · Panel girdileri `data/inbox/` dosyalarına gider, iş bunları işler.
Ayrıntı: `DECISIONS.md`, `SCORING_SYSTEM.md`.

## Kurulum
Tablet üzerinden adım adım: `ANDROID_USER_GUIDE.md`.

## Geliştirme
```
pip install -r requirements-dev.txt
python -m pytest -q
python scripts/load_demo.py      # isteğe bağlı sentetik demo veri
python scripts/run_job.py
streamlit run app.py
```
