"""Değiştirilebilir AI sağlayıcı katmanı (Aşama 2'de bağlanacak). Varsayılan: KAPALI.
- Ücretli çağrı kod düzeyinde engellenir (0 TL kuralı).
- Günlük çağrı sınırı vardır; dolunca kontrollü durur.
- Ücretsiz katmanlara yalnızca herkese açık ürün bilgisi ve anonim yorum gönderilir.
- Çıktı JSON şemasıyla doğrulanmadan kaydedilmez."""
import json

from . import config


class PaidCallBlocked(RuntimeError):
    pass


class QuotaExceeded(RuntimeError):
    pass


class ProviderDisabled(RuntimeError):
    pass


_calls_today = 0


def call(prompt: str, paid: bool = False, schema_keys: tuple = ()) -> dict:
    global _calls_today
    if paid or config.ALLOW_PAID_APIS:
        raise PaidCallBlocked("Ücretli API çağrısı engellendi (0 TL bütçe kuralı).")
    if config.AI_PROVIDER == "none":
        raise ProviderDisabled("AI sağlayıcı kapalı; kural tabanlı analiz kullanılıyor.")
    if _calls_today >= config.DAILY_AI_CALL_LIMIT:
        raise QuotaExceeded("Günlük AI çağrı sınırı doldu; sonraki dönemde devam edilecek.")
    _calls_today += 1
    raise ProviderDisabled(f"{config.AI_PROVIDER} bağlantısı Aşama 2'de eklenecek.")


def validate_json(text: str, keys: tuple) -> dict | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict) or any(k not in data for k in keys):
        return None
    return data
