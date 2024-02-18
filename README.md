# Motivasyon Botu 🌱

Hatırlatma kuran ve her gün belirlediğin saatte bir motivasyon sözü gönderen basit bir **Telegram botu**.
Yalnızca Python standart kütüphanesini kullanır; `pip install` gerekmez.

## Komutlar

| Komut | Ne yapar |
| --- | --- |
| `/soz` | Rastgele bir motivasyon sözü |
| `/hatirlat 10dk Su iç` | 10 dakika sonra "Su iç" diye hatırlatır (birimler: `sn`, `dk`, `saat`, `g`) |
| `/gunluk 09:00` | Her gün 09:00'da bir söz gönderir |
| `/liste` | Bekleyen hatırlatmaları gösterir |
| `/iptal` | Tüm hatırlatmaları ve günlük sözü iptal eder |
| `/yardim` | Komut listesi |

## Kurulum

1. Telegram'da [@BotFather](https://t.me/BotFather) ile konuşup `/newbot` yazın, botunuza bir ad verin ve **token**'ı kopyalayın.
2. `.env.example` dosyasını `.env` olarak kopyalayın ve token'ı yazın:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   ```
3. Botu başlatın:
   ```bash
   python bot.py
   ```
4. Telegram'da botunuzu bulup `/start` yazın.

Hatırlatmalar ve günlük abonelikler `durum.json` dosyasında saklanır; bot yeniden başlatılınca kaldığı yerden devam eder.
Saatler Türkiye saatine (UTC+3) göredir.

## Proje yapısı

```
bot.py       Telegram bağlantısı ve komutlar (long polling)
core.py      Ağdan bağımsız mantık: süre/saat ayrıştırma, hatırlatmalar, günlük söz zamanlaması
sozler.py    Motivasyon sözleri
test_core.py Testler
```

## Testler

```bash
python -m unittest -v
```

> `.env` dosyası `.gitignore` içindedir; token'ınızı asla depoya göndermeyin.
