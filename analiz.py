import csv
import statistics
from pathlib import Path

CSV_DOSYASI = Path("ucus_verisi_20260731_122052.csv")

with CSV_DOSYASI.open(encoding="utf-8") as dosya:
    veriler = list(csv.DictReader(dosya))

sureler = [float(satir["sure_s"]) for satir in veriler]
irtifalar = [float(satir["bagil_irtifa_m"]) for satir in veriler]
home_hatalari = [float(satir["home_mesafesi_m"]) for satir in veriler]
hedef_hatalari = [float(satir["hedef_mesafesi_m"]) for satir in veriler]

toplam_sure = sureler[-1] - sureler[0]
ortalama_aralik = statistics.mean(
    b - a for a, b in zip(sureler, sureler[1:])
)
ornekleme_hizi = 1 / ortalama_aralik

print("=== UÇUŞ ANALİZİ ===")
print(f"Kayıt sayısı       : {len(veriler)}")
print(f"Toplam süre        : {toplam_sure:.3f} s")
print(f"Örnekleme hızı     : {ornekleme_hizi:.2f} Hz")
print(f"Maksimum irtifa    : {max(irtifalar):.3f} m")
print(f"Minimum hedef hata : {min(hedef_hatalari):.3f} m")
print(f"Son home hatası    : {home_hatalari[-1]:.3f} m")
print(f"Son bağıl irtifa   : {irtifalar[-1]:.3f} m")

