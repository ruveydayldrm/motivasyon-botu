"""
Botun ağdan bağımsız mantığı: komut ayrıştırma, hatırlatmalar, günlük söz zamanlaması.
Telegram'a hiç bağlanmadan test edilebilir.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sozler import SOZLER

# Türkiye 2016'dan beri yaz saati uygulamıyor: sabit UTC+3
TR = timezone(timedelta(hours=3), "Europe/Istanbul")

BIRIMLER = {
    "sn": 1, "saniye": 1,
    "dk": 60, "dakika": 60, "m": 60,
    "sa": 3600, "saat": 3600, "s": 3600, "h": 3600,
    "g": 86400, "gün": 86400, "gun": 86400, "d": 86400,
}
SURE_DESENI = re.compile(r"^(\d+)\s*([a-zçğıöşü]+)$")
SAAT_DESENI = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")
MAKS_SURE = 30 * 86400  # en fazla 30 gün sonrası
MAKS_HATIRLATMA = 20  # kişi başı


def sure_coz(metin: str) -> int | None:
    """'10dk', '2 saat', '30sn', '1g' → saniye. Geçersizse None."""
    m = SURE_DESENI.match(metin.strip().lower())
    if not m:
        return None
    sayi, birim = int(m.group(1)), m.group(2)
    if birim not in BIRIMLER or sayi <= 0:
        return None
    saniye = sayi * BIRIMLER[birim]
    return saniye if saniye <= MAKS_SURE else None


def saat_coz(metin: str) -> tuple[int, int] | None:
    """'09:00', '9.30' → (saat, dakika). Geçersizse None."""
    m = SAAT_DESENI.match(metin.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def sure_yazi(saniye: int) -> str:
    """Saniyeyi okunur Türkçe metne çevirir: 5400 → '1 saat 30 dakika'."""
    parcalar = []
    for ad, deger in (("gün", 86400), ("saat", 3600), ("dakika", 60), ("saniye", 1)):
        if saniye >= deger:
            parcalar.append(f"{saniye // deger} {ad}")
            saniye %= deger
    return " ".join(parcalar[:2]) or "0 saniye"


def rastgele_soz(rng: random.Random | None = None) -> str:
    return (rng or random).choice(SOZLER)


@dataclass
class Hatirlatma:
    sohbet: int
    zaman: float  # UNIX zaman damgası
    mesaj: str


@dataclass
class Durum:
    """Kalıcı bot durumu: bekleyen hatırlatmalar ve günlük söz abonelikleri."""

    hatirlatmalar: list[Hatirlatma] = field(default_factory=list)
    # sohbet kimliği (str) → {"saat": 9, "dakika": 0, "son_gun": "2026-10-16"}
    gunluk: dict[str, dict] = field(default_factory=dict)

    # ---- kalıcılık ----
    @classmethod
    def yukle(cls, yol: Path) -> "Durum":
        if not yol.exists():
            return cls()
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
            return cls(hatirlatmalar=[Hatirlatma(**h) for h in veri.get("hatirlatmalar", [])], gunluk=veri.get("gunluk", {}))
        except (ValueError, TypeError):
            return cls()

    def kaydet(self, yol: Path) -> None:
        veri = {"hatirlatmalar": [asdict(h) for h in self.hatirlatmalar], "gunluk": self.gunluk}
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- hatırlatmalar ----
    def hatirlatma_ekle(self, sohbet: int, saniye: int, mesaj: str, simdi: float) -> bool:
        if sum(1 for h in self.hatirlatmalar if h.sohbet == sohbet) >= MAKS_HATIRLATMA:
            return False
        self.hatirlatmalar.append(Hatirlatma(sohbet, simdi + saniye, mesaj[:500]))
        return True

    def zamani_gelenler(self, simdi: float) -> list[Hatirlatma]:
        """Zamanı gelen hatırlatmaları listeden çıkarıp döndürür."""
        gelen = [h for h in self.hatirlatmalar if h.zaman <= simdi]
        self.hatirlatmalar = [h for h in self.hatirlatmalar if h.zaman > simdi]
        return gelen

    def sohbet_hatirlatmalari(self, sohbet: int) -> list[Hatirlatma]:
        return sorted((h for h in self.hatirlatmalar if h.sohbet == sohbet), key=lambda h: h.zaman)

    # ---- günlük söz ----
    def gunluk_ayarla(self, sohbet: int, saat: int, dakika: int) -> None:
        self.gunluk[str(sohbet)] = {"saat": saat, "dakika": dakika, "son_gun": None}

    def iptal(self, sohbet: int) -> int:
        """Sohbetin tüm hatırlatmalarını ve günlük aboneliğini siler; silinen öğe sayısını döndürür."""
        once = len(self.hatirlatmalar)
        self.hatirlatmalar = [h for h in self.hatirlatmalar if h.sohbet != sohbet]
        silinen = once - len(self.hatirlatmalar)
        if self.gunluk.pop(str(sohbet), None) is not None:
            silinen += 1
        return silinen

    def gunluk_soz_zamani(self, simdi: datetime) -> list[int]:
        """Bugünkü saati gelmiş ve bugün henüz söz gönderilmemiş sohbetleri döndürür (ve işaretler)."""
        yerel = simdi.astimezone(TR)
        bugun = yerel.date().isoformat()
        gonderilecek = []
        for sohbet, ayar in self.gunluk.items():
            vakit = yerel.replace(hour=ayar["saat"], minute=ayar["dakika"], second=0, microsecond=0)
            if yerel >= vakit and ayar.get("son_gun") != bugun:
                ayar["son_gun"] = bugun
                gonderilecek.append(int(sohbet))
        return gonderilecek


def zaman_yazi(zaman: float) -> str:
    return datetime.fromtimestamp(zaman, TR).strftime("%d.%m %H:%M")
