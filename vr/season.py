"""Türkiye dinamik alışveriş takvimi + ürün-sezon eşleştirme + zamanında yetişme (kritik yol).

ÖNEMLİ: Aylık kategori ağırlıkları BAŞLANGIÇ HİPOTEZİDİR, doğrulanmış satış verisi değildir.
Hareketli dini bayram tarihleri Diyanet takviminden doğrulanmalıdır (confidence alanına bakın)."""
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class Event:
    key: str
    name: str
    day: date
    lead_days: int            # alışveriş penceresinin olaydan kaç gün önce başladığı (hipotez)
    tags: tuple
    confidence: str           # kesin | hesaplandı | tahmini-dogrula
    note: str = ""


def _nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d + timedelta(weeks=n - 1)


def _black_friday(year):
    # ABD Şükran Günü (Kasım 4. perşembe) sonrası cuma
    return _nth_weekday(year, 11, 3, 4) + timedelta(days=1)


# Hareketli bayramlar: 1. gün. 2026 değerleri resmî tatil listesiyle uyumlu; 2027 TAHMİNİDİR.
MOVING_HOLIDAYS = {
    2026: {"ramazan_bayrami": (date(2026, 3, 20), "kesin"), "kurban_bayrami": (date(2026, 5, 27), "kesin")},
    2027: {"ramazan_bayrami": (date(2027, 3, 9), "tahmini-dogrula"), "kurban_bayrami": (date(2027, 5, 16), "tahmini-dogrula")},
    2028: {"ramazan_bayrami": (date(2028, 2, 26), "tahmini-dogrula"), "kurban_bayrami": (date(2028, 5, 5), "tahmini-dogrula")},
}


def events_for_year(year: int) -> list[Event]:
    ev = [
        Event("yilbasi", "Yılbaşı", date(year, 12, 31), 30, ("yilbasi", "hediye", "kisisellestirilmis", "cocuk_egitici", "kadin_aksesuar", "kis_aksesuar"), "kesin"),
        Event("sevgililer", "Sevgililer Günü", date(year, 2, 14), 21, ("sevgililer", "hediye", "kisisellestirilmis", "kadin_aksesuar"), "kesin"),
        Event("8mart", "8 Mart Dünya Kadınlar Günü", date(year, 3, 8), 10, ("hediye", "kadin_aksesuar"), "kesin"),
        Event("23nisan", "23 Nisan", date(year, 4, 23), 14, ("cocuk_egitici",), "kesin"),
        Event("anneler", "Anneler Günü", _nth_weekday(year, 5, 6, 2), 21, ("hediye", "kadin_aksesuar", "kisisellestirilmis", "el_yapimi"), "hesaplandı",
              "Mayıs 2. pazar"),
        Event("babalar", "Babalar Günü", _nth_weekday(year, 6, 6, 3), 14, ("hediye", "kisisellestirilmis"), "hesaplandı", "Haziran 3. pazar"),
        Event("karne_haziran", "Yaz karnesi", _nth_weekday(year, 6, 4, 3), 10, ("cocuk_egitici", "hediye"), "tahmini-dogrula",
              "MEB çalışma takviminden doğrula"),
        Event("karne_ocak", "Yarıyıl karnesi", _nth_weekday(year, 1, 4, 3), 10, ("cocuk_egitici", "hediye"), "tahmini-dogrula",
              "MEB çalışma takviminden doğrula"),
        Event("okul_acilis", "Okula dönüş", _nth_weekday(year, 9, 0, 2), 30, ("okul", "cocuk_egitici"), "tahmini-dogrula",
              "MEB çalışma takviminden doğrula"),
        Event("11_11", "11.11 kampanyaları", date(year, 11, 11), 7, ("genel_kampanya", "ev_duzen", "kadin_aksesuar"), "kesin"),
        Event("black_friday", "Black Friday / Efsane Cuma", _black_friday(year), 10, ("genel_kampanya", "ev_duzen", "kadin_aksesuar", "hediye"),
              "hesaplandı", "Pazaryerleri kendi tarihlerini değiştirebilir"),
    ]
    for key, (d, conf) in MOVING_HOLIDAYS.get(year, {}).items():
        name = "Ramazan Bayramı" if key == "ramazan_bayrami" else "Kurban Bayramı"
        ev.append(Event(key, name, d, 14, ("hediye", "giyim", "ev_duzen"), conf,
                        "Bayram günlerinde çevrimiçi işlem yoğunluğu düşebilir; satış öncesi haftadadır"))
    return sorted(ev, key=lambda e: e.day)


def upcoming_events(today: date, horizon_days: int = 365) -> list[Event]:
    out = []
    for y in (today.year, today.year + 1):
        out += [e for e in events_for_year(y) if today <= e.day <= today + timedelta(days=horizon_days)]
    return sorted(out, key=lambda e: e.day)


# Aylık kategori talep hipotezi (0-1). Kaynak: kullanıcı başlangıç hipotez listesi (Bölüm 8). DOĞRULANMADI.
MONTHLY_HYPOTHESIS = {
    "yaz_aksesuar":       [0.1, 0.1, 0.3, 0.5, 0.8, 1.0, 1.0, 0.9, 0.4, 0.1, 0.1, 0.1],
    "kis_aksesuar":       [0.9, 0.7, 0.3, 0.1, 0.0, 0.0, 0.0, 0.1, 0.3, 0.8, 1.0, 1.0],
    "kadin_aksesuar":     [0.5, 0.8, 0.8, 0.6, 1.0, 0.6, 0.6, 0.5, 0.6, 0.6, 0.9, 0.9],
    "hediye":             [0.5, 0.9, 0.6, 0.5, 1.0, 0.8, 0.4, 0.4, 0.4, 0.5, 0.8, 1.0],
    "kisisellestirilmis": [0.5, 1.0, 0.6, 0.5, 1.0, 0.8, 0.4, 0.4, 0.4, 0.5, 0.8, 1.0],
    "cocuk_egitici":      [0.7, 0.4, 0.5, 1.0, 0.5, 0.9, 0.5, 0.6, 0.8, 0.5, 0.7, 1.0],
    "okul":               [0.4, 0.3, 0.2, 0.2, 0.2, 0.2, 0.4, 1.0, 1.0, 0.3, 0.2, 0.2],
    "evcil_hayvan":       [0.6, 0.6, 0.6, 0.7, 0.8, 0.9, 1.0, 0.9, 0.7, 0.6, 0.7, 0.7],
    "seyahat":            [0.2, 0.2, 0.3, 0.5, 0.7, 1.0, 1.0, 0.9, 0.4, 0.3, 0.2, 0.3],
    "ev_duzen":           [0.9, 0.6, 0.9, 0.8, 0.8, 0.6, 0.6, 0.7, 0.9, 0.8, 0.9, 0.7],
    "ceyiz":              [0.4, 0.4, 0.6, 0.7, 0.9, 1.0, 1.0, 0.9, 0.8, 0.6, 0.4, 0.4],
    "el_yapimi":          [0.5, 0.7, 0.7, 0.7, 1.0, 0.8, 0.7, 0.6, 0.6, 0.6, 0.8, 0.9],
    "tasarruf":           [1.0, 0.8, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.9, 0.8],
    "genel_kampanya":     [0.5, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 0.7],
    "yilbasi":            [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.3, 0.9, 1.0],
    "sevgililer":         [0.6, 1.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2],
}
# Mevsime bağlı etiketler: varsa ay uygunluğunu BUNLAR belirler; genel etiketler (hediye, kadın aksesuarı) sezonu genişletemez.
SEASONAL_TAGS = {"yaz_aksesuar", "kis_aksesuar", "okul", "seyahat", "yilbasi", "sevgililer"}
YEAR_ROUND_TAGS = {"ev_duzen", "tasarruf", "evcil_hayvan"}


def monthly_fit_map(tags: list[str]) -> list[float]:
    """Her ay için 0-100 uygunluk. Bilinmeyen etiket -> None yerine nötr 0.5 değil, hiç katkı yok."""
    known = [t for t in tags if t in MONTHLY_HYPOTHESIS]
    seasonal = [t for t in known if t in SEASONAL_TAGS]
    if seasonal:
        known = seasonal
    if not known:
        return [None] * 12
    return [round(100 * max(MONTHLY_HYPOTHESIS[t][m] for t in known), 1) for m in range(12)]


def is_year_round(tags: list[str]) -> bool:
    if set(tags) & SEASONAL_TAGS:
        return False
    fm = monthly_fit_map(tags)
    if fm[0] is None:
        return bool(set(tags) & YEAR_ROUND_TAGS)
    return min(fm) >= 50


# ---- 21. Zamanında yetişme: kritik yol ----
DEFAULT_TASKS = {
    # gorev: (min_gun, max_gun, bağımlılıklar)
    "uretici_bulma": (2, 7, []),
    "numune": (3, 10, ["uretici_bulma"]),
    "kalite_kontrol": (1, 3, ["numune"]),
    "urun_gorselleri": (1, 4, ["numune"]),
    "avatar_reklam": (2, 5, ["urun_gorselleri"]),
    "satis_sayfasi": (1, 2, ["urun_gorselleri"]),
    "reklam_testi": (3, 7, ["avatar_reklam", "satis_sayfasi", "kalite_kontrol"]),
    "tedarik": (2, 14, ["kalite_kontrol"]),
    "teslimat": (1, 5, ["tedarik", "reklam_testi"]),
}


def critical_path(tasks: dict | None = None, use_max: bool = True) -> tuple[int, list[str]]:
    tasks = tasks or DEFAULT_TASKS
    finish, prev = {}, {}

    def ef(t):
        if t in finish:
            return finish[t]
        mn, mx, deps = tasks[t]
        start = 0
        for d in deps:
            if ef(d) > start:
                start, prev[t] = ef(d), d
        finish[t] = start + (mx if use_max else mn)
        return finish[t]

    end = max(tasks, key=ef)
    path = [end]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    return finish[end], list(reversed(path))


def readiness(event_day: date, today: date, tasks: dict | None = None, safety_ratio: float = 0.2,
              cargo_peak_extra: int = 2, verified: bool = False) -> dict:
    """Ürün olay tarihinden önce müşteriye teslim edilebilir mi?
    Doğrulanmamış süreler için en kötü (max) süre + güvenlik payı kullanılır; garanti verilmez."""
    total_max, path = critical_path(tasks, use_max=True)
    total_min, _ = critical_path(tasks, use_max=False)
    safety = int(round(total_max * safety_ratio)) + cargo_peak_extra
    days_left = (event_day - today).days
    need = total_max + safety
    can = days_left >= need
    return {
        "gun_kaldi": days_left,
        "gereken_gun_kotumser": need,
        "gereken_gun_iyimser": total_min,
        "kritik_yol": path,
        "yetisir": can,
        "kismen_yetisebilir": (not can) and days_left >= total_min,
        "son_guvenli_baslangic": (event_day - timedelta(days=need)).isoformat(),
        "garanti": False if not verified else can,
        "not": "Süreler doğrulanmadığı için garanti verilmez." if not verified else "",
    }
