#!/usr/bin/env python3
"""Seçilmiş Monte Carlo koşularını PX4-Gazebo uçuşunda doğrular.

Kullanım:
  python3 kritik_px4_dogrulama.py --list
  python3 kritik_px4_dogrulama.py --run 648

Her komutta yalnızca bir kritik koşu yürütülür. PX4-Gazebo her uçuş koşusu
öncesinde kullanıcı tarafından yeniden başlatılmalıdır. Güvenli adayı olmayan
38 numaralı koşu PX4'e bağlanmadan görev reddini doğrular.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import math
import random
import time
from pathlib import Path

import kontrollu_deneyler as kd


SEED = 20260801
DRONE_SAYISI = 3
ALAN_YARICAPI_M = 10.0
KRITIK_KOSULAR = {
    38: "Güvenli aday yok; önerilen yöntem görevi reddetmeli",
    130: "Sınır durumu; kazananın rezerv marjı yaklaşık %0,499",
    425: "Battery-only güvensiz, önerilen yöntem güvenli",
    648: "Distance-only/standard auction güvensiz, önerilen yöntem güvenli",
}


def senaryo_uret(rng: random.Random):
    gorev = kd.Gorev(
        gorev_id=0,
        x_m=rng.uniform(-ALAN_YARICAPI_M, ALAN_YARICAPI_M),
        y_m=rng.uniform(-ALAN_YARICAPI_M, ALAN_YARICAPI_M),
        odul=100.0,
    )
    dronelar = [
        kd.Drone(
            drone_id=i,
            x_m=rng.uniform(-ALAN_YARICAPI_M, ALAN_YARICAPI_M),
            y_m=rng.uniform(-ALAN_YARICAPI_M, ALAN_YARICAPI_M),
            batarya_yuzde=rng.uniform(20.0, 100.0),
        )
        for i in range(1, DRONE_SAYISI + 1)
    ]
    return dronelar, gorev


def kosuyu_uret(kosu_no: int):
    rng = random.Random(SEED)
    dronelar = gorev = None
    for _ in range(kosu_no):
        dronelar, gorev = senaryo_uret(rng)
    gorev.gorev_id = kosu_no
    return dronelar, gorev


def aday_metrikleri(drone, gorev):
    sonuc = kd.teklif_hesapla(drone, gorev)
    sonuc["standard_puan"] = gorev.odul - kd.MESAFE_AGIRLIGI * sonuc["mesafe_m"]
    return sonuc


def baseline_sec(adaylar):
    distance = min(adaylar, key=lambda a: (a["mesafe_m"], a["drone_id"]))
    battery = max(adaylar, key=lambda a: (a["batarya_yuzde"], -a["drone_id"]))
    standard = max(adaylar, key=lambda a: (a["standard_puan"], -a["drone_id"]))
    uygunlar = [a for a in adaylar if a["uygun"]]
    proposed = (
        max(uygunlar, key=lambda a: (a["teklif_puani"], -a["drone_id"]))
        if uygunlar else None
    )
    return {
        "distance_only": distance,
        "battery_only": battery,
        "standard_auction": standard,
        "proposed_safe_auction": proposed,
    }


def mantiksal_ozeti_yaz(kosu_no, gorev, adaylar, secimler):
    zaman = time.strftime("%Y%m%d_%H%M%S")
    yol = Path(f"kritik_kosu_{kosu_no}_mantiksal_{zaman}.csv")
    with yol.open("w", newline="", encoding="utf-8-sig") as dosya:
        alanlar = [
            "run_id", "seed", "task_x_m", "task_y_m", "method",
            "selected_drone_id", "assigned", "safe_assignment",
            "selected_distance_m", "selected_battery_pct",
            "estimated_energy_pct", "remaining_battery_pct",
            "reserve_margin_pct",
        ]
        writer = csv.DictWriter(dosya, fieldnames=alanlar)
        writer.writeheader()
        for yontem, secim in secimler.items():
            writer.writerow({
                "run_id": kosu_no,
                "seed": SEED,
                "task_x_m": round(gorev.x_m, 6),
                "task_y_m": round(gorev.y_m, 6),
                "method": yontem,
                "selected_drone_id": secim["drone_id"] if secim else "",
                "assigned": secim is not None,
                "safe_assignment": bool(secim and secim["uygun"]),
                "selected_distance_m": round(secim["mesafe_m"], 6) if secim else "",
                "selected_battery_pct": round(secim["batarya_yuzde"], 6) if secim else "",
                "estimated_energy_pct": round(secim["tahmini_enerji_yuzde"], 6) if secim else "",
                "remaining_battery_pct": round(secim["kalan_batarya_yuzde"], 6) if secim else "",
                "reserve_margin_pct": (
                    round(secim["kalan_batarya_yuzde"] - kd.MIN_GUVENLI_BATARYA, 6)
                    if secim else ""
                ),
            })
    return yol


def yazdir(kosu_no, gorev, adaylar, secimler):
    print("=" * 70)
    print(f"KRİTİK PX4 DOĞRULAMA — KOŞU {kosu_no}")
    print(KRITIK_KOSULAR[kosu_no])
    print(f"Görev: ({gorev.x_m:.3f}, {gorev.y_m:.3f})")
    print("-" * 70)
    for a in adaylar:
        print(
            f"Drone {a['drone_id']} | konum=({a['drone_x_m']:.3f}, "
            f"{a['drone_y_m']:.3f}) | batarya=%{a['batarya_yuzde']:.3f} | "
            f"mesafe={a['mesafe_m']:.3f} m | kalan=%{a['kalan_batarya_yuzde']:.3f} | "
            f"güvenli={a['uygun']}"
        )
    print("-" * 70)
    for yontem, secim in secimler.items():
        if secim is None:
            print(f"{yontem:24s}: ATAMA YOK")
        else:
            print(
                f"{yontem:24s}: Drone {secim['drone_id']} "
                f"({'GÜVENLİ' if secim['uygun'] else 'GÜVENSİZ'})"
            )


def argumanlar():
    parser = argparse.ArgumentParser()
    grup = parser.add_mutually_exclusive_group(required=True)
    grup.add_argument("--list", action="store_true", help="Kritik koşuları göster")
    grup.add_argument("--run", type=int, choices=sorted(KRITIK_KOSULAR), help="Tek koşu çalıştır")
    return parser.parse_args()


def main():
    args = argumanlar()
    if args.list:
        for kosu_no, aciklama in KRITIK_KOSULAR.items():
            print(f"{kosu_no}: {aciklama}")
        return

    kosu_no = args.run
    dronelar, gorev = kosuyu_uret(kosu_no)
    adaylar = [aday_metrikleri(d, gorev) for d in dronelar]
    secimler = baseline_sec(adaylar)
    yazdir(kosu_no, gorev, adaylar, secimler)
    ozet_yolu = mantiksal_ozeti_yaz(kosu_no, gorev, adaylar, secimler)
    print(f"Mantıksal özet CSV: {ozet_yolu.resolve()}")

    kd.DRONELAR = dronelar
    kd.GOREV = gorev

    if secimler["proposed_safe_auction"] is None:
        print("\n✅ BEKLENEN SONUÇ: Güvenli aday yok; görev reddedildi.")
        print("PX4 bağlantısı ve uçuş başlatılmadı.")
        return

    print("\nPX4-Gazebo uçuş doğrulaması başlatılıyor...")
    asyncio.run(kd.main())


if __name__ == "__main__":
    main()
