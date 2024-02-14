import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from core import TR, Durum, rastgele_soz, saat_coz, sure_coz, sure_yazi
from sozler import SOZLER


class AyristirmaTesti(unittest.TestCase):
    def test_sure(self):
        self.assertEqual(sure_coz("10dk"), 600)
        self.assertEqual(sure_coz("30sn"), 30)
        self.assertEqual(sure_coz("2 saat"), 7200)
        self.assertEqual(sure_coz("1g"), 86400)
        self.assertEqual(sure_coz("3GÜN"), 3 * 86400)

    def test_gecersiz_sure(self):
        for metin in ["", "dk", "10", "10yıl", "-5dk", "0dk", "31g", "on dakika"]:
            self.assertIsNone(sure_coz(metin), metin)

    def test_saat(self):
        self.assertEqual(saat_coz("09:00"), (9, 0))
        self.assertEqual(saat_coz("9.30"), (9, 30))
        self.assertEqual(saat_coz("23:59"), (23, 59))
        for metin in ["24:00", "9", "12:60", "sabah"]:
            self.assertIsNone(saat_coz(metin), metin)

    def test_sure_yazi(self):
        self.assertEqual(sure_yazi(600), "10 dakika")
        self.assertEqual(sure_yazi(5400), "1 saat 30 dakika")
        self.assertEqual(sure_yazi(90061), "1 gün 1 saat")

    def test_soz(self):
        self.assertIn(rastgele_soz(random.Random(1)), SOZLER)
        self.assertGreaterEqual(len(SOZLER), 20)


class DurumTesti(unittest.TestCase):
    def test_hatirlatma_zamani_gelince_bir_kez_doner(self):
        d = Durum()
        d.hatirlatma_ekle(1, 60, "Su iç", simdi=1000)
        self.assertEqual(d.zamani_gelenler(1030), [])
        gelen = d.zamani_gelenler(1060)
        self.assertEqual([h.mesaj for h in gelen], ["Su iç"])
        self.assertEqual(d.zamani_gelenler(2000), [])

    def test_hatirlatma_siniri(self):
        d = Durum()
        for _ in range(20):
            self.assertTrue(d.hatirlatma_ekle(1, 60, "x", 0))
        self.assertFalse(d.hatirlatma_ekle(1, 60, "x", 0))
        self.assertTrue(d.hatirlatma_ekle(2, 60, "başka kişi", 0))

    def test_gunluk_soz_gunde_bir_kez(self):
        d = Durum()
        d.gunluk_ayarla(5, 9, 0)
        self.assertEqual(d.gunluk_soz_zamani(datetime(2026, 10, 16, 8, 59, tzinfo=TR)), [])
        self.assertEqual(d.gunluk_soz_zamani(datetime(2026, 10, 16, 9, 0, tzinfo=TR)), [5])
        self.assertEqual(d.gunluk_soz_zamani(datetime(2026, 10, 16, 15, 0, tzinfo=TR)), [])
        self.assertEqual(d.gunluk_soz_zamani(datetime(2026, 10, 17, 9, 1, tzinfo=TR)), [5])

    def test_iptal(self):
        d = Durum()
        d.hatirlatma_ekle(1, 60, "a", 0)
        d.hatirlatma_ekle(1, 60, "b", 0)
        d.hatirlatma_ekle(2, 60, "c", 0)
        d.gunluk_ayarla(1, 9, 0)
        self.assertEqual(d.iptal(1), 3)
        self.assertEqual(len(d.hatirlatmalar), 1)
        self.assertEqual(d.iptal(1), 0)

    def test_kaydet_ve_yukle(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "durum.json"
            d = Durum()
            d.hatirlatma_ekle(1, 60, "Kitap oku 📚", 0)
            d.gunluk_ayarla(1, 8, 30)
            d.kaydet(yol)
            y = Durum.yukle(yol)
            self.assertEqual(y.hatirlatmalar[0].mesaj, "Kitap oku 📚")
            self.assertEqual(y.gunluk["1"]["dakika"], 30)

    def test_bozuk_dosya_bos_durum_verir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "durum.json"
            yol.write_text("bozuk{", encoding="utf-8")
            self.assertEqual(Durum.yukle(yol).hatirlatmalar, [])


if __name__ == "__main__":
    unittest.main()
