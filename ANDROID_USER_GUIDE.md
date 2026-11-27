# Tabletten kullanım rehberi

## Bir kerelik kurulum (yalnızca tarayıcı)
1. **GitHub:** github.com'da giriş yap → sağ üst "+" → "New repository" → ad: `viral-radar-ai`, **Private** → oluştur. Kodu Claude bu depoya gönderecek.
2. **Jeton (panelin girdi gönderebilmesi için):** GitHub → Settings → Developer settings → Fine-grained tokens → yalnızca `viral-radar-ai` deposu; izinler: Contents (Read and write), Actions (Read and write). Jetonu sohbete yazma.
3. **Streamlit:** share.streamlit.io → GitHub ile giriş → "Create app" → depo `viral-radar-ai`, dosya `app.py` → Advanced settings → Secrets alanına `.streamlit/secrets.toml.example` örneğine göre `GITHUB_REPO` ve `GITHUB_TOKEN` ekle → uygulamayı **özel** (yalnızca sen) yap.
4. Panel adresini tarayıcıda aç → menü "Paylaş/Ana ekrana ekle" ile uygulama gibi kullan.

## Günlük kullanım
- **Bugünün ürünleri:** kriterlerine uyan en güçlü 10 ürün.
- **Kriter profilleri:** fiyat aralığı, yerli/el yapımı, trend aşaması vb. ZORUNLU/TERCİH/KAPALI.
- **Bağlantı ekle:** Instagram/TikTok/Trendyol bağlantılarını toplu yapıştır.
- **Veri kaynakları ve sistem:** "Araştırma işini şimdi başlat" ile beklemeden çalıştır.
- Panel 12 saat kullanılmazsa uyur; açınca 1-2 dakikada uyanır.
- Demo veri görmek için: GitHub → Actions → "Araştırma işi" → Run workflow → demo: yukle (kaldırmak için: sil).
