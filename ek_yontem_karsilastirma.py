#!/usr/bin/env python3
"""PX4 ana deneylerine dokunmadan görev tahsis yöntemlerini karşılaştırır.

Bu betik uçuş gerçekleştirmez. Mevcut kontrollu_deneyler.py dosyasındaki
enerji ve güvenlik denklemini kullanarak tekrarlanabilir Monte Carlo deneyleri
üretir ve dört tahsis yöntemini aynı senaryolarda eşleştirilmiş olarak sınar.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev


MESAFE_AGIRLIGI = 2.0
ENERJI_AGIRLIGI = 1.0
BATARYA_AGIRLIGI = 20.0
METRE_BASI_ENERJI = 0.50
MIN_GUVENLI_BATARYA = 30.0
GOREV_ODULU = 100.0

YONTEMLER = (
    "distance_only",
    "battery_only",
    "standard_auction",
    "proposed_safe_auction",
)


@dataclass(frozen=True)
class Drone:
    drone_id: int
    x_m: float
    y_m: float
    batarya_yuzde: float


@dataclass(frozen=True)
class Gorev:
    x_m: float
    y_m: float
    odul: float = GOREV_ODULU


def aday_metrikleri(drone: Drone, gorev: Gorev) -> dict[str, float | bool | int]:
    mesafe = math.hypot(gorev.x_m - drone.x_m, gorev.y_m - drone.y_m)
    gidis_donus = 2.0 * mesafe
    enerji = gidis_donus * METRE_BASI_ENERJI
    kalan = drone.batarya_yuzde - enerji
    guvenli = (
        drone.batarya_yuzde >= MIN_GUVENLI_BATARYA
        and kalan >= MIN_GUVENLI_BATARYA
    )
    standard_puan = gorev.odul - MESAFE_AGIRLIGI * mesafe
    onerilen_puan = (
        gorev.odul
        - MESAFE_AGIRLIGI * mesafe
        - ENERJI_AGIRLIGI * enerji
        + BATARYA_AGIRLIGI * (drone.batarya_yuzde / 100.0)
    )
    return {
        "drone_id": drone.drone_id,
        "batarya_yuzde": drone.batarya_yuzde,
        "mesafe_m": mesafe,
        "gidis_donus_mesafe_m": gidis_donus,
        "tahmini_enerji_yuzde": enerji,
        "kalan_batarya_yuzde": kalan,
        "guvenli": guvenli,
        "standard_puan": standard_puan,
        "onerilen_puan": onerilen_puan,
    }


def sec(yontem: str, adaylar: list[dict]) -> dict | None:
    if yontem == "distance_only":
        return min(adaylar, key=lambda a: (a["mesafe_m"], a["drone_id"]))
    if yontem == "battery_only":
        return max(adaylar, key=lambda a: (a["batarya_yuzde"], -a["drone_id"]))
    if yontem == "standard_auction":
        return max(adaylar, key=lambda a: (a["standard_puan"], -a["drone_id"]))
    if yontem == "proposed_safe_auction":
        uygunlar = [a for a in adaylar if a["guvenli"]]
        if not uygunlar:
            return None
        return max(uygunlar, key=lambda a: (a["onerilen_puan"], -a["drone_id"]))
    raise ValueError(f"Bilinmeyen yöntem: {yontem}")


def senaryo_uret(
    rng: random.Random,
    drone_sayisi: int,
    alan_yaricapi_m: float,
) -> tuple[list[Drone], Gorev]:
    gorev = Gorev(
        x_m=rng.uniform(-alan_yaricapi_m, alan_yaricapi_m),
        y_m=rng.uniform(-alan_yaricapi_m, alan_yaricapi_m),
    )
    dronelar = [
        Drone(
            drone_id=i,
            x_m=rng.uniform(-alan_yaricapi_m, alan_yaricapi_m),
            y_m=rng.uniform(-alan_yaricapi_m, alan_yaricapi_m),
            batarya_yuzde=rng.uniform(20.0, 100.0),
        )
        for i in range(1, drone_sayisi + 1)
    ]
    return dronelar, gorev


def wilson_araligi(basari: int, toplam: int) -> tuple[float, float]:
    if toplam == 0:
        return math.nan, math.nan
    z = 1.959963984540054
    p = basari / toplam
    payda = 1.0 + z * z / toplam
    merkez = (p + z * z / (2.0 * toplam)) / payda
    yaricap = z * math.sqrt(
        p * (1.0 - p) / toplam + z * z / (4.0 * toplam * toplam)
    ) / payda
    return merkez - yaricap, merkez + yaricap


def ort_ss(degerler: list[float]) -> tuple[float, float]:
    if not degerler:
        return math.nan, math.nan
    return mean(degerler), stdev(degerler) if len(degerler) > 1 else 0.0


def yaz_csv(yol: Path, satirlar: list[dict], alanlar: list[str]) -> None:
    with yol.open("w", newline="", encoding="utf-8-sig") as dosya:
        writer = csv.DictWriter(dosya, fieldnames=alanlar)
        writer.writeheader()
        writer.writerows(satirlar)


def deneyi_calistir(
    kosu_sayisi: int,
    drone_sayisi: int,
    seed: int,
    alan_yaricapi_m: float,
    cikti: Path,
) -> None:
    rng = random.Random(seed)
    ham: list[dict] = []

    for kosu_no in range(1, kosu_sayisi + 1):
        dronelar, gorev = senaryo_uret(rng, drone_sayisi, alan_yaricapi_m)
        adaylar = [aday_metrikleri(d, gorev) for d in dronelar]
        guvenli_adaylar = [a for a in adaylar if a["guvenli"]]
        en_kisa_guvenli = (
            min(a["gidis_donus_mesafe_m"] for a in guvenli_adaylar)
            if guvenli_adaylar else math.nan
        )

        for yontem in YONTEMLER:
            kazanan = sec(yontem, adaylar)
            atama_var = kazanan is not None
            guvenli_atama = bool(kazanan and kazanan["guvenli"])
            ham.append({
                "run_id": kosu_no,
                "seed": seed,
                "method": yontem,
                "safe_candidate_exists": bool(guvenli_adaylar),
                "assigned": atama_var,
                "selected_drone_id": kazanan["drone_id"] if kazanan else "",
                "safe_assignment": guvenli_atama,
                "unsafe_assignment": bool(kazanan and not kazanan["guvenli"]),
                "mission_success": guvenli_atama,
                "mission_distance_m": round(kazanan["gidis_donus_mesafe_m"], 6) if kazanan else "",
                "estimated_energy_pct": round(kazanan["tahmini_enerji_yuzde"], 6) if kazanan else "",
                "remaining_battery_pct": round(kazanan["kalan_batarya_yuzde"], 6) if kazanan else "",
                "reserve_margin_pct": round(kazanan["kalan_batarya_yuzde"] - MIN_GUVENLI_BATARYA, 6) if kazanan else "",
                "distance_regret_vs_shortest_safe_m": (
                    round(kazanan["gidis_donus_mesafe_m"] - en_kisa_guvenli, 6)
                    if kazanan and guvenli_adaylar and kazanan["guvenli"] else ""
                ),
            })

    ozet: list[dict] = []
    for yontem in YONTEMLER:
        satirlar = [r for r in ham if r["method"] == yontem]
        atamalar = [r for r in satirlar if r["assigned"]]
        basarili = [r for r in satirlar if r["mission_success"]]
        guvenli_firsatlar = [r for r in satirlar if r["safe_candidate_exists"]]
        firsat_basarisi = [r for r in guvenli_firsatlar if r["mission_success"]]
        mesafeler = [float(r["mission_distance_m"]) for r in basarili]
        kalanlar = [float(r["remaining_battery_pct"]) for r in basarili]
        pismanliklar = [
            float(r["distance_regret_vs_shortest_safe_m"])
            for r in basarili if r["distance_regret_vs_shortest_safe_m"] != ""
        ]
        basari_alt, basari_ust = wilson_araligi(len(firsat_basarisi), len(guvenli_firsatlar))
        mesafe_ort, mesafe_ss = ort_ss(mesafeler)
        kalan_ort, kalan_ss = ort_ss(kalanlar)
        pismanlik_ort, pismanlik_ss = ort_ss(pismanliklar)
        ozet.append({
            "method": yontem,
            "runs": len(satirlar),
            "assignment_rate_pct": round(100 * len(atamalar) / len(satirlar), 3),
            "unsafe_assignment_count": sum(bool(r["unsafe_assignment"]) for r in satirlar),
            "unsafe_assignment_rate_pct": round(100 * sum(bool(r["unsafe_assignment"]) for r in satirlar) / len(satirlar), 3),
            "safe_opportunity_success_rate_pct": round(100 * len(firsat_basarisi) / len(guvenli_firsatlar), 3),
            "success_rate_95ci_low_pct": round(100 * basari_alt, 3),
            "success_rate_95ci_high_pct": round(100 * basari_ust, 3),
            "mean_successful_roundtrip_distance_m": round(mesafe_ort, 3),
            "sd_successful_roundtrip_distance_m": round(mesafe_ss, 3),
            "mean_remaining_battery_pct": round(kalan_ort, 3),
            "sd_remaining_battery_pct": round(kalan_ss, 3),
            "mean_distance_regret_vs_shortest_safe_m": round(pismanlik_ort, 3),
            "sd_distance_regret_vs_shortest_safe_m": round(pismanlik_ss, 3),
        })

    cikti.mkdir(parents=True, exist_ok=True)
    yaz_csv(cikti / "ek_karsilastirma_ham.csv", ham, list(ham[0]))
    yaz_csv(cikti / "ek_karsilastirma_ozet.csv", ozet, list(ozet[0]))

    print("\n=== EK YÖNTEM KARŞILAŞTIRMASI ===")
    print(
        f"Koşu: {kosu_sayisi} | Drone: {drone_sayisi} | "
        f"Alan: ±{alan_yaricapi_m:g} m | Seed: {seed}"
    )
    print(f"Güvenli aday bulunan senaryo: {sum(r['safe_candidate_exists'] for r in ham if r['method'] == YONTEMLER[0])}/{kosu_sayisi}")
    print("\nYöntem                 Güvensiz atama   Güvenli fırsatta başarı")
    for r in ozet:
        print(
            f"{r['method']:<23} {r['unsafe_assignment_count']:>7} "
            f"          %{r['safe_opportunity_success_rate_pct']:>7.3f}"
        )
    print(f"\nHam CSV : {(cikti / 'ek_karsilastirma_ham.csv').resolve()}")
    print(f"Özet CSV: {(cikti / 'ek_karsilastirma_ozet.csv').resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=1000, help="Monte Carlo koşusu")
    parser.add_argument("--drones", type=int, default=3, help="Senaryo başına drone")
    parser.add_argument("--seed", type=int, default=20260801, help="Tekrarlanabilirlik tohumu")
    parser.add_argument(
        "--arena",
        type=float,
        default=10.0,
        help="Drone ve görev koordinatlarının ±metre sınırı (varsayılan: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"ek_karsilastirma_{datetime.now():%Y%m%d_%H%M%S}"),
        help="Çıktı klasörü",
    )
    args = parser.parse_args()
    if args.runs < 1 or args.drones < 2 or args.arena <= 0:
        parser.error("--runs en az 1, --drones en az 2, --arena pozitif olmalıdır")
    deneyi_calistir(args.runs, args.drones, args.seed, args.arena, args.output)


if __name__ == "__main__":
    main()
