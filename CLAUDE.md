# CLAUDE.md — Oturum devamlılığı

Proje: Viral Radar AI V5.1 Ürün Bulucu. Ana talimat: `docs/PROMPT_V5.1_URUN_BULUCU.txt` (Bölüm 23 aşamalar).
Kullanıcı: Türkçe iletişim, Android tablet, 0 TL bütçe, diğer projelerine dokunulmaz.

## Durum
- Aşama 1 tamamlandı (bkz. PROJECT_STATUS.md, TEST_REPORT.md).
- Sıradaki: Aşama 2 — Katman 1 kaynak adaptörleri, erken trend radarı, rekabet/pazar eşleştirme, üretici adayları, ilk gerçek pilot.

## Kurallar (kısa)
- Kapsam yalnızca ürün bulma/araştırma. Satış, mesaj, yayın, ücretli API yok.
- Veritabanına yalnızca `scripts/run_job.py` (tek yazıcı) yazar; panel `data/inbox/`a yazar.
- Eksik veri puanı yükseltmez; ağırlıklar kullanıcı onayı olmadan değişmez; demo veri [DEMO] etiketlidir.
- Depodaki sistem dosyalarına "⛔CLAUDE_SILME_" öneki eklenmez (yalnızca Drive/teslim dosyaları).
- Her aşama sonunda: testler, TEST_REPORT, PROJECT_STATUS, TODO, DECISIONS, CHANGELOG güncellenir.
