"""
Motivasyon Botu (Telegram)
Hatırlatma kurar ve her gün belirlediğin saatte bir motivasyon sözü gönderir.

Çalıştırma:
    1) Telegram'da @BotFather ile bot oluştur, token'ı al
    2) .env dosyasına TELEGRAM_BOT_TOKEN=... yaz (ya da ortam değişkeni olarak ver)
    3) python bot.py

Yalnızca Python standart kütüphanesini kullanır (uzun yoklama / long polling).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from core import TR, Durum, rastgele_soz, saat_coz, sure_coz, sure_yazi, zaman_yazi

KLASOR = Path(__file__).parent
DURUM_DOSYASI = KLASOR / "durum.json"

YARDIM = (
    "🌱 *Motivasyon Botu*\n\n"
    "/soz — rastgele bir motivasyon sözü\n"
    "/hatirlat 10dk Su iç — süre sonra hatırlatır (sn, dk, saat, g)\n"
    "/gunluk 09:00 — her gün o saatte bir söz gönderir\n"
    "/liste — bekleyen hatırlatmaların\n"
    "/iptal — tüm hatırlatmaları ve günlük sözü iptal eder"
)


def env_yukle() -> None:
    """Basit .env okuyucu (ek kütüphane gerektirmez)."""
    yol = KLASOR / ".env"
    if not yol.exists():
        return
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if satir and not satir.startswith("#") and "=" in satir:
            anahtar, deger = satir.split("=", 1)
            os.environ.setdefault(anahtar.strip(), deger.strip().strip('"'))


class Telegram:
    def __init__(self, token: str):
        self.url = f"https://api.telegram.org/bot{token}/"

    def istek(self, metod: str, **parametreler) -> dict:
        veri = urllib.parse.urlencode(parametreler).encode()
        with urllib.request.urlopen(self.url + metod, data=veri, timeout=40) as yanit:
            return json.loads(yanit.read().decode())

    def gonder(self, sohbet: int, metin: str) -> None:
        try:
            self.istek("sendMessage", chat_id=sohbet, text=metin, parse_mode="Markdown")
        except urllib.error.URLError as e:
            print(f"Mesaj gönderilemedi ({sohbet}): {e}")

    def guncellemeler(self, offset: int) -> list[dict]:
        return self.istek("getUpdates", offset=offset, timeout=5).get("result", [])


def komut_isle(tg: Telegram, durum: Durum, sohbet: int, metin: str) -> bool:
    """Komutu işler; durum değiştiyse True döner."""
    komut, _, arguman = metin.strip().partition(" ")
    komut = komut.split("@")[0].lower()  # gruplarda /soz@BotAdi

    if komut in ("/start", "/yardim", "/help"):
        tg.gonder(sohbet, YARDIM)
    elif komut == "/soz":
        tg.gonder(sohbet, f"💬 {rastgele_soz()}")
    elif komut == "/hatirlat":
        sure_metni, _, mesaj = arguman.strip().partition(" ")
        saniye = sure_coz(sure_metni)
        if not saniye or not mesaj.strip():
            tg.gonder(sohbet, "Şöyle yazabilirsin: `/hatirlat 10dk Su iç`\nBirimler: sn, dk, saat, g (en fazla 30 gün)")
            return False
        if not durum.hatirlatma_ekle(sohbet, saniye, mesaj.strip(), time.time()):
            tg.gonder(sohbet, "En fazla 20 bekleyen hatırlatman olabilir. /iptal ile temizleyebilirsin.")
            return False
        tg.gonder(sohbet, f"⏰ Tamam! {sure_yazi(saniye)} sonra hatırlatacağım: _{mesaj.strip()}_")
        return True
    elif komut == "/gunluk":
        saat = saat_coz(arguman)
        if not saat:
            tg.gonder(sohbet, "Şöyle yazabilirsin: `/gunluk 09:00`")
            return False
        durum.gunluk_ayarla(sohbet, *saat)
        tg.gonder(sohbet, f"☀️ Her gün saat {saat[0]:02d}:{saat[1]:02d} olduğunda bir motivasyon sözü göndereceğim.")
        return True
    elif komut == "/liste":
        liste = durum.sohbet_hatirlatmalari(sohbet)
        gunluk = durum.gunluk.get(str(sohbet))
        satirlar = [f"• {zaman_yazi(h.zaman)} — {h.mesaj}" for h in liste]
        if gunluk:
            satirlar.append(f"• Her gün {gunluk['saat']:02d}:{gunluk['dakika']:02d} — günlük söz")
        tg.gonder(sohbet, "📋 Bekleyenler:\n" + "\n".join(satirlar) if satirlar else "Bekleyen hatırlatman yok.")
    elif komut == "/iptal":
        silinen = durum.iptal(sohbet)
        tg.gonder(sohbet, f"🗑️ {silinen} öğe iptal edildi." if silinen else "İptal edilecek bir şey yok.")
        return silinen > 0
    elif komut.startswith("/"):
        tg.gonder(sohbet, "Bu komutu tanımıyorum. /yardim yazarak komutları görebilirsin.")
    return False


def calistir(token: str) -> None:
    tg = Telegram(token)
    durum = Durum.yukle(DURUM_DOSYASI)
    offset = 0
    print("Bot çalışıyor. Durdurmak için Ctrl+C.")
    while True:
        degisti = False
        try:
            for g in tg.guncellemeler(offset):
                offset = g["update_id"] + 1
                mesaj = g.get("message") or {}
                if "text" in mesaj:
                    degisti |= komut_isle(tg, durum, mesaj["chat"]["id"], mesaj["text"])
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"Bağlantı sorunu, tekrar deneniyor: {e}")
            time.sleep(5)

        for h in durum.zamani_gelenler(time.time()):
            tg.gonder(h.sohbet, f"⏰ Hatırlatma: {h.mesaj}")
            degisti = True
        for sohbet in durum.gunluk_soz_zamani(datetime.now(TR)):
            tg.gonder(sohbet, f"☀️ Günün sözü:\n\n{rastgele_soz()}")
            degisti = True
        if degisti:
            durum.kaydet(DURUM_DOSYASI)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    env_yukle()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN bulunamadı. .env.example dosyasını .env olarak kopyalayıp token'ı yazın.")
        return 1
    try:
        calistir(token)
    except KeyboardInterrupt:
        print("\nBot durduruldu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
