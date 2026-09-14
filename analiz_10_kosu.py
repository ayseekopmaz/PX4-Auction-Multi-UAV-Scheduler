import csv
import statistics
from pathlib import Path

DOSYALAR = sorted(Path(".").glob("ucus_verisi_20260731_*.csv"))[-10:]

sonuclar = []

for dosya in DOSYALAR:
    with dosya.open(encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))

    sure = float(satirlar[-1]["sure_s"])
    max_irtifa = max(
        float(s["bagil_irtifa_m"]) for s in satirlar
    )
    min_hedef_hatasi = min(
        float(s["hedef_mesafesi_m"]) for s in satirlar
    )
    son_home_hatasi = float(
        satirlar[-1]["home_mesafesi_m"]
    )
    son_irtifa = float(
        satirlar[-1]["bagil_irtifa_m"]
    )

    basarili = (
        min_hedef_hatasi <= 0.7
        and son_home_hatasi <= 0.7
        and son_irtifa <= 0.15
        and max_irtifa <= 4.0
    )

    sonuclar.append(
        {
            "dosya": dosya.name,
            "sure_s": sure,
            "max_irtifa_m": max_irtifa,
            "min_hedef_hatasi_m": min_hedef_hatasi,
            "son_home_hatasi_m": son_home_hatasi,
            "son_irtifa_m": son_irtifa,
            "basarili": basarili,
        }
    )

with open(
    "kontrollu_10_kosu_ozeti.csv",
    "w",
    newline="",
    encoding="utf-8",
) as f:
    alanlar = list(sonuclar[0].keys())
    writer = csv.DictWriter(f, fieldnames=alanlar)
    writer.writeheader()
    writer.writerows(sonuclar)

sureler = [s["sure_s"] for s in sonuclar]
irtifalar = [s["max_irtifa_m"] for s in sonuclar]
hedef_hatalari = [s["min_hedef_hatasi_m"] for s in sonuclar]
home_hatalari = [s["son_home_hatasi_m"] for s in sonuclar]
basari_sayisi = sum(s["basarili"] for s in sonuclar)

print("=== 10 KONTROLLÜ KOŞU ANALİZİ ===")

for i, sonuc in enumerate(sonuclar, start=1):
    durum = "BAŞARILI" if sonuc["basarili"] else "BAŞARISIZ"

    print(
        f"{i:2}. {sonuc['dosya']} | "
        f"Süre: {sonuc['sure_s']:.2f} s | "
        f"Hedef: {sonuc['min_hedef_hatasi_m']:.3f} m | "
        f"Home: {sonuc['son_home_hatasi_m']:.3f} m | "
        f"Max irtifa: {sonuc['max_irtifa_m']:.3f} m | "
        f"{durum}"
    )

print("\n=== İSTATİSTİKSEL ÖZET ===")
print(f"Başarı oranı       : %{basari_sayisi / len(sonuclar) * 100:.1f}")
print(
    f"Görev süresi       : {statistics.mean(sureler):.3f} ± "
    f"{statistics.stdev(sureler):.3f} s"
)
print(
    f"Hedef hatası       : {statistics.mean(hedef_hatalari):.3f} ± "
    f"{statistics.stdev(hedef_hatalari):.3f} m"
)
print(
    f"Home hatası        : {statistics.mean(home_hatalari):.3f} ± "
    f"{statistics.stdev(home_hatalari):.3f} m"
)
print(
    f"Maksimum irtifa    : {statistics.mean(irtifalar):.3f} ± "
    f"{statistics.stdev(irtifalar):.3f} m"
)
print("Özet kaydedildi    : kontrollu_10_kosu_ozeti.csv")
