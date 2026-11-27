# Güvenlik
- Özel (private) depo; anahtarlar yalnızca GitHub Secrets / Streamlit Secrets'ta, sohbette paylaşılmaz.
- GitHub jetonu: fine-grained, yalnızca bu depo, Contents RW + Actions RW.
- SSRF koruması (yalnızca http/https, yerel/özel IP reddi), parametreli SQL, CSV formül enjeksiyonu kaçışı.
- Yükleme: yalnızca .csv/.json, en fazla 5 MB.
- Yorumlarda e-posta/telefon/kullanıcı adı anonimleştirilir.
- Dış metinler veri olarak işlenir; içindeki talimatlar sisteme etki etmez (testli).
- Ücretli API çağrısı kod düzeyinde engelli; AI sağlayıcı varsayılan kapalı.
- Bağımlılık denetimi: pip-audit (28.11.2026: bilinen açık yok).
- Panel: Streamlit özel uygulama; isteğe bağlı PBKDF2 parola özeti.
