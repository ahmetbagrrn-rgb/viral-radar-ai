"""Derin yorum analizi (Aşama 1: deterministik, ücretsiz). Çok etiketli C01-C30 rubriği.
- Genel övgü satın alma isteği sayılmaz.
- Alay/ironi tespit edilirse C01 (satın alma isteği) düşürülür.
- Bot şüphesi kesin hüküm değildir: düşük / orta / yüksek / belirsiz.
AI ile sınıflandırma (Aşama 2) isteğe bağlıdır ve bu kuralların üstüne çalışır."""
import re
from collections import Counter

LABELS = {
    "C01": "Doğrudan satın alma isteği", "C02": "Fiyat sorusu", "C03": "Satın alma bağlantısı isteği",
    "C04": "Kargo ve teslimat sorusu", "C05": "Arkadaş etiketleme", "C06": "Hediye alma isteği",
    "C07": "Kullanım deneyimi iddiası", "C08": "Kalite şikâyeti", "C09": "Pahalı bulma",
    "C10": "Güvenlik endişesi", "C11": "Alay ve ironi", "C12": "Gereksiz ürün değerlendirmesi",
    "C13": "Alternatif ürün önerisi", "C14": "Ürün geliştirme talebi", "C15": "Spam veya bot şüphesi",
    "C16": "Dolandırıcılık şüphesi", "C17": "Türkiye'ye özgü satın alma ilgisi", "C18": "Üründen bağımsız videoya tepki",
    "C19": "Rakip marka önerisi", "C20": "Belirsiz veya ilgisiz", "C21": "Yerel satış noktası arayışı",
    "C22": "Renk, model ve boyut talebi", "C23": "Ürün gerçek ihtiyacı çözüyor", "C24": "Satın alma engeli",
    "C25": "Gerçek dışı ürün vaadi şüphesi", "C26": "Satın almış olma iddiası", "C27": "Tekrar satın alma isteği",
    "C28": "Yerli üretim veya kişiselleştirme talebi", "C29": "Telif ve marka endişesi", "C30": "Yanıltıcı reklam beklentisi",
}

# Türkçe büyük/küçük harf ve ekler için basit normalize
_TR_MAP = str.maketrans("İIŞĞÜÖÇ", "iışğüöç")


def norm(text: str) -> str:
    return text.translate(_TR_MAP).lower()


P = {
    "C01": r"\b(almak ist|alıcam|alacağım|alırım|alicam|sipariş vermek|sipariş ver|bende ist|ben de ist|istiyorum|lazım bana|bunu alıyorum|i want (this|one|it)|need (this|one)|want one|أريد)",
    "C02": r"\b(fiyat|kaç ?(tl|lira|para)|ne kadar|ücret|price|how much|بكم|السعر)",
    "C03": r"\b(link|nereden al|nerden al|nereden buluruz|nasıl sipariş|where (can|to) (i )?buy|link\?|bağlantı)",
    "C04": r"\b(kargo|teslimat|kaç günde gel|gönderim|shipping|deliver)",
    "C05": r"@\w+",
    "C06": r"\b(hediye|anneme|annem için|babama|sevgilime|eşime|kızıma|oğluma|çocuğuma|yeğenime|arkadaşıma al|gift|for my (mom|wife|son|daughter))",
    "C07": r"\b(kullanıyorum|kullandım|denedim|bizde var|evde var|i use|i tried|i have (this|one))",
    "C08": r"\b(kalitesiz|bozuldu|kırıldı|çöp|dayanmıyor|kopuyor|sökül|cheap quality|broke|garbage|quality is bad)",
    "C09": r"\b(pahalı|çok para|fiyatı yüksek|bu paraya|kazık|expensive|overpriced)",
    "C10": r"\b(tehlikeli|güvenli mi|zararlı|yutabilir|boğul|yanar|patlar|dangerous|unsafe|choking)",
    "C12": r"\b(gereksiz|ne gerek var|saçma|kim alır|para israfı|useless|pointless|who needs)",
    "C13": r"\b(bunun yerine|daha iyisi|alternatif|aynısı .* daha ucuz|instead)",
    "C14": r"\b(keşke|olsaydı|şöyle olsa|daha büyük|daha küçük olsa|should make|wish it)",
    "C16": r"\b(dolandırıcı|sahte site|para gönderdim gelmedi|scam|fraud)",
    "C17": r"\b(türkiye'?de|türkiyeye|tr'?de|yurt içi|türkiye'?ye gönderim|in turkey)",
    "C18": r"\b(sesi çok güzel|ne güzel kadın|ne tatlı adam|müzik ne|şarkı ne|video güzel|edit güzel)",
    "C19": r"\b(ikea|xiaomi|philips|karaca|madame coco|english home|lc waikiki|koton|temu'?da|aliexpress'?te|amazon'?da var)",
    "C21": r"\b(mağaza|mağazada|şubesi|hangi ilde|istanbul'?da nerede|ankara'?da nerede|izmir'?de nerede|yakınımda)",
    "C22": r"\b(rengi|renk seçen|başka renk|bedeni|beden|boyutu|ölçüsü|modeli var mı|size|colou?r)",
    "C23": r"\b(çok işe yarar|hayat kurtarır|tam ihtiyacım|işimi gördü|çok pratik|lifesaver|so useful)",
    "C24": r"\b(ama pahalı|kargo parası|kargo ücreti|stokta yok|güvenmiyorum|taksit yok|iade|yurt dışından|gümrük)",
    "C25": r"\b(gerçek değil|montaj|photoshop|yapay zeka|ai ile|fake|edited|böyle olmuyor)",
    "C26": r"\b(aldım|sipariş ettim|geldi|bought it|ordered)",
    "C27": r"\b(bir tane daha|tekrar alacağım|ikincisini|yine aldım|buy again)",
    "C28": r"\b(yerlisi|yerli üretim|el yapımı|isim yazdır|kişiye özel|ismimizi|kişiselleştir|handmade|personaliz)",
    "C29": r"\b(taklit|çakma|orijinal mi|replika|fake brand|copy of)",
    "C30": r"\b(reklamda göründüğü gibi değil|gerçekte böyle değil|reklam abartı|kandırmaca)",
}
_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in P.items()}

SARCASM = re.compile(
    r"(😂|🤣|😅|🙄|\byok artık\b|\btabii ki? (alırım|alacağım)\b|\bkesin alırım\b.*(😂|🤣|:\))|\baynen\b.*(😂|🤣)|"
    r"\bbir bu eksikti\b|\bçok lazım(dı)?\b.*(😂|🤣|🙄)|\bhemen koşuyorum\b|\bsure,? (i'll|i will) buy\b|"
    r"\bböbreğimi sat)", re.IGNORECASE)

LINK = re.compile(r"(https?://|www\.|\.com\b|t\.me/|bit\.ly)", re.IGNORECASE)
SPAM_PHRASES = re.compile(r"(profilime bak|dm at|takip et.*takip|kazanç|bitcoin|forex|follow me|check my (bio|profile)|"
                          r"promote it on|send (it|pic) to)", re.IGNORECASE)
PRAISE_ONLY = re.compile(r"^(çok güzel|harika|süper|muhteşem|bayıldım|wow|nice|amazing|love it|❤️|😍|👏|🔥|\s|!)+$", re.IGNORECASE)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
MENTION = re.compile(r"@[\w.]+")


def anonymize(text: str) -> str:
    """KVKK: gereksiz kişisel bilgi saklama. Etiketleme bilgisi (C05) korunur, kimlik saklanmaz."""
    text = EMAIL.sub("[e-posta]", text)
    text = PHONE.sub("[telefon]", text)
    return MENTION.sub("@kullanici", text)


def detect_lang(text: str) -> str:
    if re.search(r"[؀-ۿ]", text):
        return "ar"
    if re.search(r"[çğışöüÇĞİŞÖÜ]", text) or re.search(r"\b(ve|bir|bu|çok|ama|için|mı|mi|ne)\b", text, re.I):
        return "tr"
    if re.search(r"\b(the|this|and|want|buy|is|it)\b", text, re.I):
        return "en"
    return "bilinmiyor"


def classify(text: str) -> list[str]:
    t = norm(text)
    labels = [k for k, rx in _COMPILED.items() if rx.search(t) or rx.search(text)]
    if SARCASM.search(text):
        labels.append("C11")
        # Alay satın alma isteği sayılmaz
        labels = [l for l in labels if l not in ("C01", "C26", "C27")]
    if "C09" in labels and "C24" not in labels:
        labels.append("C24")  # pahalı bulma = satın alma engeli
    if LINK.search(text) or SPAM_PHRASES.search(text):
        labels.append("C15")
    if PRAISE_ONLY.match(text.strip()):
        labels = [l for l in labels if l not in ("C01",)]  # övgü != satın alma niyeti
    # Hediye niyeti + istek ifadesi -> satın alma niyeti de say (örn. "anneme almak istiyorum")
    if not labels:
        labels = ["C20"]
    return sorted(set(labels))


def bot_level_for(text: str, dup_count: int, template_count: int) -> str:
    """Tek yorum + küme bilgisinden şüphe seviyesi. Yabancı dil/emoji/kısalık tek başına kanıt DEĞİL."""
    score = 0
    if LINK.search(text):
        score += 2
    if SPAM_PHRASES.search(text):
        score += 2
    if dup_count >= 3:
        score += 2
    elif dup_count == 2:
        score += 1
    if template_count >= 4:
        score += 1
    if score >= 4:
        return "yüksek"
    if score >= 2:
        return "orta"
    if len(text.strip()) <= 3:
        return "belirsiz"
    return "düşük"


def _template(text: str) -> str:
    t = norm(MENTION.sub("@", text))
    t = re.sub(r"\d+", "#", t)
    return re.sub(r"[^\w#@ ]", "", t).strip()[:40]


BOT_WEIGHT = {"düşük": 1.0, "belirsiz": 0.7, "orta": 0.4, "yüksek": 0.1}


def analyze(comments: list[str], visible_total: int | None = None, sampling: str = "erişilebilen tümü") -> dict:
    accessed = len(comments)
    anon = [anonymize(c) for c in comments if c and c.strip()]
    counts = Counter(" ".join(norm(c).split()) for c in anon)
    tmpl = Counter(_template(c) for c in anon)
    unique_texts, seen = [], set()
    rows = []
    for c in anon:
        key = " ".join(norm(c).split())
        lvl = bot_level_for(c, counts[key], tmpl[_template(c)])
        labels = classify(c)
        rows.append({"text": c, "labels": labels, "bot": lvl, "lang": detect_lang(c), "dup": key in seen})
        if key not in seen:
            seen.add(key)
            unique_texts.append(c)

    uniq_rows = [r for r in rows if not r["dup"]]
    n = len(uniq_rows) or 1

    def rate(code, filtered=False):
        if filtered:
            w = sum(BOT_WEIGHT[r["bot"]] for r in uniq_rows if code in r["labels"])
            tot = sum(BOT_WEIGHT[r["bot"]] for r in uniq_rows) or 1
            return round(100 * w / tot, 1)
        return round(100 * sum(code in r["labels"] for r in uniq_rows) / n, 1)

    barriers = Counter()
    for r in uniq_rows:
        t = norm(r["text"])
        if "C09" in r["labels"]:
            barriers["Fiyat"] += 1
        if "kargo" in t:
            barriers["Kargo ücreti/süresi"] += 1
        if "C08" in r["labels"]:
            barriers["Kalite endişesi"] += 1
        if "C10" in r["labels"]:
            barriers["Güvenlik endişesi"] += 1
        if "C25" in r["labels"] or "C30" in r["labels"]:
            barriers["Güven / gerçeklik şüphesi"] += 1
        if "güvenm" in t or "stokta yok" in t:
            barriers["Güven / erişim"] += 1

    lang_dist = Counter(r["lang"] for r in uniq_rows)
    return {
        "gorunen_toplam": visible_total,
        "erisilen": accessed,
        "benzersiz": len(uniq_rows),
        "analiz_edilen": len(uniq_rows),
        "orneklem_yontemi": sampling,
        "satin_alma_niyeti_orani": rate("C01"),
        "satin_alma_niyeti_orani_bot_filtreli": rate("C01", filtered=True),
        "bot_suphesi_orani": round(100 * sum(r["bot"] in ("orta", "yüksek") for r in uniq_rows) / n, 1),
        "alay_orani": rate("C11"),
        "sikayet_orani": rate("C08"),
        "hediye_niyeti": rate("C06"),
        "turkiye_talebi": round(rate("C17") + rate("C21"), 1),
        "fiyat_hassasiyeti": round(rate("C09") + rate("C02") * 0.3, 1),
        "en_buyuk_engel": barriers.most_common(1)[0][0] if barriers else "Belirgin engel yok / veri yetersiz",
        "engeller": dict(barriers),
        "etiket_dagilimi": {k: sum(k in r["labels"] for r in uniq_rows) for k in LABELS},
        "dil_dagilimi": dict(lang_dist),
        "veri_kisitlari": _limits(len(uniq_rows), visible_total),
        "satirlar": rows,
    }


def _limits(n, visible):
    notes = []
    if n < 30:
        notes.append("Örneklem 30'dan küçük: sonuçlar yalnızca ön sinyaldir.")
    if visible and n < 0.1 * visible:
        notes.append("Görünen yorumların %10'undan azı analiz edildi; temsil gücü bilinmiyor.")
    notes.append("Yorumdaki satın alma niyeti gerçekleşmiş satış değildir.")
    return notes
