# Test raporu — 28.11.2026 (Aşama 1)

Sonuç: **46 / 46 test geçti** (python -m pytest). Sentetik veri: 23 kayıt (1 tekrar), 362 yorum.
Sentetik test doğruluğu gerçek dünya başarısı DEĞİLDİR.

| Bölüm 22 kontrolü | Sonuç |
|---|---|
| Ağırlık toplamları 100, öncelik 0,60+0,40 | Geçti |
| Puanlar 0-100 ve min ≤ max | Geçti (iki tarih × 23 ürün) |
| Eksik veri puanı yükseltmiyor; kanıtsız nitel değer reddi | Geçti |
| Zorunlu kriter elemesi; doğrulanmamış zorunlu → güçlü aday olamaz | Geçti |
| Profil değişince yeniden sıralama | Geçti |
| Sezon dışı ürün "şimdi" önerilmiyor; sezonunda öneriliyor | Geçti (kasım / mayıs) |
| Yetişemeyen sezon engelleniyor | Geçti |
| Alay ve genel övgü satın alma niyeti sayılmıyor; rubrik örnekleri | Geçti |
| Tekrar yorum/ürün ayıklama; bot şüphesi; anonimleştirme | Geçti |
| Komisyon hesabı; bilinmeyen maliyet sıfır sayılmıyor; duyarlılık | Geçti |
| Negatif katkı → FİYATI UYGUN DEĞİL; düşük komisyonlu hacimli ürün elenmiyor | Geçti |
| Kritik riskli ürünler eleniyor; reklam metni denetimi | Geçti |
| SSRF, CSV formül enjeksiyonu, dosya türü/boyut | Geçti |
| Ücretli API çağrısı engelli; dış metin talimatları etkisiz | Geçti |
| Tek yazıcı kilidi; gelen kutusu (bozuk dosya diğerlerini durdurmuyor) | Geçti |
| Yedekleme/geri yükleme, bütünlük kontrolü | Geçti |
| Uçtan uca iş + günlük rapor, aynı gün tekrar tahmin kaydı yok | Geçti |
| Panel: 7 sayfa yüklenir, profil kaydet, bağlantı ekle (Streamlit AppTest) | Geçti (elle çalıştırıldı) |
| Bağımlılık denetimi (pip-audit) | Bilinen açık yok |

Test edilmeyenler: GitHub Actions'ın gerçek ortamda çalışması, Streamlit Cloud yayını, gerçek tablet görünümü,
yorum sınıflandırmanın gerçek doğruluğu (insan etiketli veri yok).
