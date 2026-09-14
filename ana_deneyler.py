import csv
import gc
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import kontrollu_deneyler as kd


TEKRAR_SAYISI = 10
KOSU_ZAMAN_ASIMI_S = 180
KOSULAR_ARASI_BEKLEME_S = 5


SENARYOLAR = {
    "farkli_batarya": {
        "baslik": "FARKLI BATARYA",
        "beklenen_kazanan": 3,
        "beklenen_reddedilenler": [],
        "dronelar": [
            (1, 0.0, 0.0, 50.0),
            (2, 0.0, 0.0, 70.0),
            (3, 0.0, 0.0, 90.0),
        ],
        "gorev": (1, 0.0, 3.0, 100.0),
    },
    "farkli_mesafe": {
        "baslik": "FARKLI MESAFE",
        "beklenen_kazanan": 2,
        "beklenen_reddedilenler": [],
        "dronelar": [
            (1, 0.0, 0.0, 70.0),
            (2, 0.0, 3.0, 70.0),
            (3, 4.0, 0.0, 70.0),
        ],
        "gorev": (2, 0.0, 5.0, 100.0),
    },
    "dusuk_batarya_reddi": {
        "baslik": "DÜŞÜK BATARYA REDDİ",
        "beklenen_kazanan": 2,
        "beklenen_reddedilenler": [1],
        "dronelar": [
            (1, 0.0, 4.5, 30.0),
            (2, 0.0, 2.0, 70.0),
            (3, 4.0, 0.0, 80.0),
        ],
        "gorev": (3, 0.0, 5.0, 100.0),
    },
    "esit_teklif_kucuk_id": {
        "baslik": "EŞİT TEKLİF - KÜÇÜK ID",
        "beklenen_kazanan": 1,
        "beklenen_reddedilenler": [],
        "dronelar": [
            (1, 0.0, 0.0, 70.0),
            (2, 0.0, 0.0, 70.0),
            (3, 4.0, 0.0, 40.0),
        ],
        "gorev": (4, 0.0, 3.0, 100.0),
    },
}


OZET_ALANLARI = [
    "scenario_name",
    "repeat_number",
    "expected_winner",
    "actual_winner",
    "expected_rejected_drones",
    "actual_rejected_drones",
    "auction_success",
    "takeoff_success",
    "target_success",
    "return_success",
    "landing_success",
    "overall_success",
    "target_arrival_error_m",
    "home_error_m",
    "mission_duration_s",
    "winning_bid_score",
    "mission_distance_m",
    "auction_csv",
    "flight_csv",
    "error_message",
]


def senaryoyu_ayarla(senaryo_adi):
    senaryo = SENARYOLAR[senaryo_adi]

    kd.DRONELAR = [
        kd.Drone(
            drone_id,
            x_m,
            y_m,
            batarya,
        )
        for drone_id, x_m, y_m, batarya
        in senaryo["dronelar"]
    ]

    gorev_id, x_m, y_m, odul = senaryo["gorev"]

    kd.GOREV = kd.Gorev(
        gorev_id=gorev_id,
        x_m=x_m,
        y_m=y_m,
        odul=odul,
    )

    return senaryo


def tek_kosu_cocuk(senaryo_adi):
    import asyncio

    senaryo = senaryoyu_ayarla(senaryo_adi)

    print("=" * 60)
    print(f"ANA DENEY: {senaryo['baslik']}")
    print(
        "Beklenen kazanan: "
        f"Drone {senaryo['beklenen_kazanan']}"
    )
    print("=" * 60)

    asyncio.run(kd.main())
    gc.collect()


def sayiyi_bul(desen, metin):
    eslesme = re.search(desen, metin)

    if eslesme is None:
        return ""

    return float(eslesme.group(1).replace(",", "."))


def tam_sayiyi_bul(desen, metin):
    eslesme = re.search(desen, metin)

    if eslesme is None:
        return ""

    return int(eslesme.group(1))


def reddedilenleri_bul(metin):
    bulunanlar = re.findall(
        r"Drone\s+(\d+).*?TEKLİF REDDEDİLDİ",
        metin,
    )

    return sorted({int(drone_id) for drone_id in bulunanlar})


def yeni_dosyayi_bul(onceki_dosyalar, desen):
    sonraki_dosyalar = set(Path(".").glob(desen))
    yeni_dosyalar = sonraki_dosyalar - onceki_dosyalar

    if not yeni_dosyalar:
        return ""

    en_yeni = max(
        yeni_dosyalar,
        key=lambda yol: yol.stat().st_mtime,
    )

    return str(en_yeni.resolve())


def alt_sureci_calistir(senaryo_adi):
    komut = [
        sys.executable,
        "-u",

        str(Path(__file__).resolve()),
        "--run",
        senaryo_adi,
    ]

    surec = subprocess.Popen(
        komut,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    satirlar = []
    baslangic = time.monotonic()

    try:
        while True:
            if surec.stdout is not None:
                satir = surec.stdout.readline()

                if satir:
                    print(satir, end="", flush=True)
                    satirlar.append(satir)

            if surec.poll() is not None:
                if surec.stdout is not None:
                    kalan = surec.stdout.read()

                    if kalan:
                        print(kalan, end="", flush=True)
                        satirlar.append(kalan)

                break

            if (
                time.monotonic() - baslangic
                > KOSU_ZAMAN_ASIMI_S
            ):
                surec.terminate()

                try:
                    surec.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    surec.kill()
                    surec.wait()

                satirlar.append(
                    "\n❌ ANA DENEY ZAMAN AŞIMI\n"
                )
                break

            time.sleep(0.05)

    except KeyboardInterrupt:
        surec.terminate()

        try:
            surec.wait(timeout=10)
        except subprocess.TimeoutExpired:
            surec.kill()
            surec.wait()

        raise

    return "".join(satirlar), surec.returncode


def sonucu_cozumle(
    senaryo_adi,
    tekrar_no,
    metin,
    donus_kodu,
    ihale_csv,
    ucus_csv,
):
    senaryo = SENARYOLAR[senaryo_adi]

    actual_winner = tam_sayiyi_bul(
        r"Kazanan:\s*Drone\s+(\d+)",
        metin,
    )

    actual_rejected = reddedilenleri_bul(metin)

    target_error = sayiyi_bul(
        r"Hedefe varış hatası:\s*([0-9.,]+)\s*m",
        metin,
    )

    home_error = sayiyi_bul(
        r"Son home hatası:\s*([0-9.,]+)\s*m",
        metin,
    )

    duration = sayiyi_bul(
        r"Toplam görev süresi:\s*([0-9.,]+)\s*s",
        metin,
    )

    winning_bid = sayiyi_bul(
        r"Kazanan teklif:\s*([0-9.,]+)",
        metin,
    )

    mission_distance = sayiyi_bul(
        r"Görev mesafesi:\s*([0-9.,]+)\s*m",
        metin,
    )

    auction_success = (
        actual_winner == senaryo["beklenen_kazanan"]
        and actual_rejected
        == senaryo["beklenen_reddedilenler"]
    )

    takeoff_success = (
        "✅ Kalkış tamamlandı:" in metin
    )
    target_success = (
        "✅ Hedefe ulaşıldı." in metin
    )
    return_success = (
        "RTL başlatılıyor..." in metin
    )
    landing_success = (
        "✅ İniş tamamlandı." in metin
    )

    overall_success = (
        donus_kodu == 0
        and auction_success
        and takeoff_success
        and target_success
        and return_success
        and landing_success
    )

    hata_eslesmesi = re.search(
        r"❌ Görev hatası:\s*(.+)",
        metin,
    )

    if hata_eslesmesi:
        error_message = hata_eslesmesi.group(1).strip()
    elif "ANA DENEY ZAMAN AŞIMI" in metin:
        error_message = "Ana deney zaman aşımı"
    elif donus_kodu not in (0, None):
        error_message = f"Alt süreç çıkış kodu: {donus_kodu}"
    elif not overall_success:
        error_message = "Başarı koşullarından biri sağlanmadı"
    else:
        error_message = ""

    return {
        "scenario_name": senaryo_adi,
        "repeat_number": tekrar_no,
        "expected_winner":
            senaryo["beklenen_kazanan"],
        "actual_winner": actual_winner,
        "expected_rejected_drones":
            ",".join(
                map(
                    str,
                    senaryo["beklenen_reddedilenler"],
                )
            ),
        "actual_rejected_drones":
            ",".join(map(str, actual_rejected)),
        "auction_success": auction_success,
        "takeoff_success": takeoff_success,
        "target_success": target_success,
        "return_success": return_success,
        "landing_success": landing_success,
        "overall_success": overall_success,
        "target_arrival_error_m": target_error,
        "home_error_m": home_error,
        "mission_duration_s": duration,
        "winning_bid_score": winning_bid,
        "mission_distance_m": mission_distance,
        "auction_csv": ihale_csv,
        "flight_csv": ucus_csv,
        "error_message": error_message,
    }


def ozet_satiri_ekle(ozet_yolu, sonuc):
    dosya_var = ozet_yolu.exists()

    with ozet_yolu.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as dosya:
        writer = csv.DictWriter(
            dosya,
            fieldnames=OZET_ALANLARI,
        )

        if not dosya_var:
            writer.writeheader()

        writer.writerow(sonuc)


def ana_deneyleri_calistir():
    zaman_etiketi = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    ozet_yolu = Path(
        f"ana_deney_ozeti_{zaman_etiketi}.csv"
    )

    kosu_plani = []

    for tekrar_no in range(1, TEKRAR_SAYISI + 1):
        for senaryo_adi in SENARYOLAR:
            kosu_plani.append(
                (senaryo_adi, tekrar_no)
            )

    toplam_kosu = len(kosu_plani)
    basarili_kosu = 0

    print("=" * 70)
    print("40 KONTROLLÜ PX4-GAZEBO DENEYİ")
    print(f"Toplam koşu: {toplam_kosu}")
    print(f"Özet CSV: {ozet_yolu.resolve()}")
    print("=" * 70)

    for sira_no, (senaryo_adi, tekrar_no) in enumerate(
        kosu_plani,
        start=1,
    ):
        senaryo = SENARYOLAR[senaryo_adi]

        print("\n" + "#" * 70)
        print(
            f"KOŞU {sira_no}/{toplam_kosu} | "
            f"{senaryo['baslik']} | "
            f"TEKRAR {tekrar_no}/{TEKRAR_SAYISI}"
        )
        print("#" * 70)

        onceki_ihale_dosyalari = set(
            Path(".").glob("ihale_sonucu_*.csv")
        )
        onceki_ucus_dosyalari = set(
            Path(".").glob("ihale_ucus_verisi_*.csv")
        )

        metin, donus_kodu = alt_sureci_calistir(
            senaryo_adi
        )

        ihale_csv = yeni_dosyayi_bul(
            onceki_ihale_dosyalari,
            "ihale_sonucu_*.csv",
        )
        ucus_csv = yeni_dosyayi_bul(
            onceki_ucus_dosyalari,
            "ihale_ucus_verisi_*.csv",
        )

        sonuc = sonucu_cozumle(
            senaryo_adi,
            tekrar_no,
            metin,
            donus_kodu,
            ihale_csv,
            ucus_csv,
        )

        ozet_satiri_ekle(ozet_yolu, sonuc)

        if sonuc["overall_success"]:
            basarili_kosu += 1
            print(
                f"\n✅ KOŞU BAŞARILI: "
                f"{sira_no}/{toplam_kosu}"
            )
        else:
            print(
                f"\n❌ KOŞU BAŞARISIZ: "
                f"{sira_no}/{toplam_kosu}"
            )
            print(
                "Hata: "
                f"{sonuc['error_message']}"
            )

        print(
            f"Anlık sonuç: {basarili_kosu}/"
            f"{sira_no} başarılı"
        )
        print(
            f"Özet kaydedildi: {ozet_yolu.resolve()}"
        )

        if sira_no < toplam_kosu:
            print(
                f"Sonraki koşu için "
                f"{KOSULAR_ARASI_BEKLEME_S} saniye "
                "bekleniyor..."
            )
            time.sleep(KOSULAR_ARASI_BEKLEME_S)

    basari_orani = (
        100.0 * basarili_kosu / toplam_kosu
    )

    print("\n" + "=" * 70)
    print("ANA DENEYLER TAMAMLANDI")
    print(
        f"Başarılı koşu: "
        f"{basarili_kosu}/{toplam_kosu}"
    )
    print(f"Başarı oranı: %{basari_orani:.2f}")
    print(f"Özet CSV: {ozet_yolu.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--run":
        senaryo_adi = sys.argv[2]

        if senaryo_adi not in SENARYOLAR:
            raise SystemExit(
                f"Bilinmeyen senaryo: {senaryo_adi}"
            )

        tek_kosu_cocuk(senaryo_adi)
    else:
        ana_deneyleri_calistir()

