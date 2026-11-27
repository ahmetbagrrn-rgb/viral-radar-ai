# Puanlama sistemi (sürüm v5.1-hipotez)

Ağırlıklar başlangıç hipotezidir; puanlar satış olasılığı değildir. Toplamlar testle doğrulanır (her biri 100).

- **Genel fırsat (zamanlama hariç):** Türkiye talebi 12, satın alma niyeti 12, kârlılık 15, AI avatar 15, harcama isteği/değer 10, rekabet avantajı 7, yerli/el yapımı 6, üretici güvenilirliği 5, kargo 4, iade/kalite riski 4, farklılaştırma 4, düşük sermaye 3, tekrar/tamamlayıcı satış 3.
- **Dönemsel uygunluk:** kategori talebi 20, alım gücü/fiyat 15, özel gün/mevsim 15, tedarik/teslim zamanlaması 15, trend büyümesi 10, reklam maliyeti 10, rakip kampanya 5, müşteri ihtiyacı 5, sezon sonrası 5.
- **Veri güveni:** kaynak kalitesi 25, kapsam 25, güncellik 20, bağımsız doğrulama 15, örneklem 15.
- **AI avatar:** ilk 3 saniye 15, gerçek ürünü gösterme 15, problem açıklığı 15, Türkçe/kültür 10, duygusal/hediye 10, güven 10, senaryo çeşitliliği 10, organik paylaşım 5, düşük maliyet 5, görsel doğruluk 5.
- **Öncelik** = genel × 0,60 + bugünkü dönemsel × 0,40. Eşikler: 90 öncelikli, 80 güçlü, 70 ayrıntılı araştırma, 60 izleme.

## Ölçülebilir kurallar
- Satın alma niyeti: bot filtreli oran / %15 (n<30 ise ×0,5).
- Kârlılık: reklam sonrası marj / %30 (maliyetler varsayımlıysa ×0,7).
- Kargo: desi ≤2 → 1,0; ≤5 → 0,7; ≤10 → 0,4; üstü 0,1; kırılgan ×0,6.
- Üretici: doğrulanmış üretici sayısı / 3.

## Kısıtlar
- Eksik kriter: nokta puana 0, maksimum aralığa ağırlığı kadar.
- Nitel kriter kanıtsızsa reddedilir.
- Doğrulanmamış zorunlu kriter veya 2'den az bağımsız kaynak → en fazla "Ayrıntılı araştırma".
- "ŞİMDİ DEĞERLENDİR" kapıları: veri güveni ≥80, maliyetler doğrulanmış, ≥1 doğrulanmış üretici, risk kontrolü, pozitif katkı, sezona yetişme, avatar ≥60, zorunlu kriterler doğrulanmış.
