import asyncio
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path

from mavsdk import System


KALKIS_IRTIFASI_M = 3.0
HEDEF_TOLERANSI_M = 0.7
GOREV_ZAMAN_ASIMI_S = 90

MESAFE_AGIRLIGI = 2.0
ENERJI_AGIRLIGI = 1.0
BATARYA_AGIRLIGI = 20.0
METRE_BASI_ENERJI = 0.50
MIN_GUVENLI_BATARYA = 30.0


@dataclass
class Drone:
    drone_id: int
    x_m: float
    y_m: float
    batarya_yuzde: float


@dataclass
class Gorev:
    gorev_id: int
    x_m: float
    y_m: float
    odul: float


DRONELAR = [
    Drone(1, 0.0, 0.0, 70.0),
    Drone(2, 4.0, 0.0, 90.0),
    Drone(3, 2.0, 4.0, 45.0),
]

GOREV = Gorev(
    gorev_id=1,
    x_m=0.0,
    y_m=5.0,
    odul=100.0,
)


def teklif_hesapla(drone, gorev):
    dx = gorev.x_m - drone.x_m
    dy = gorev.y_m - drone.y_m
    mesafe = math.hypot(dx, dy)

    gidis_donus_mesafesi = 2.0 * mesafe
    tahmini_enerji = gidis_donus_mesafesi * METRE_BASI_ENERJI
    kalan_batarya = drone.batarya_yuzde - tahmini_enerji

    uygun = (
        drone.batarya_yuzde >= MIN_GUVENLI_BATARYA
        and kalan_batarya >= MIN_GUVENLI_BATARYA
    )

    if uygun:
        teklif = (
            gorev.odul
            - MESAFE_AGIRLIGI * mesafe
            - ENERJI_AGIRLIGI * tahmini_enerji
            + BATARYA_AGIRLIGI
            * (drone.batarya_yuzde / 100.0)
        )
    else:
        teklif = None

    return {
        "drone_id": drone.drone_id,
        "drone_x_m": drone.x_m,
        "drone_y_m": drone.y_m,
        "batarya_yuzde": drone.batarya_yuzde,
        "mesafe_m": mesafe,
        "tahmini_enerji_yuzde": tahmini_enerji,
        "kalan_batarya_yuzde": kalan_batarya,
        "teklif_puani": teklif,
        "uygun": uygun,
        "goreli_dogu_m": dx,
        "goreli_kuzey_m": dy,
    }


def ihaleyi_calistir():
    teklifler = []

    print("=== DİNAMİK GÖREV İHALESİ ===")
    print(
        f"Görev {GOREV.gorev_id} | "
        f"Konum: ({GOREV.x_m:.1f}, {GOREV.y_m:.1f}) | "
        f"Ödül: {GOREV.odul:.1f}"
    )

    for drone in DRONELAR:
        sonuc = teklif_hesapla(drone, GOREV)
        teklifler.append(sonuc)

        if sonuc["uygun"]:
            print(
                f"Drone {drone.drone_id} | "
                f"Mesafe: {sonuc['mesafe_m']:.2f} m | "
                f"Batarya: %{drone.batarya_yuzde:.1f} | "
                f"Tahmini enerji: "
                f"%{sonuc['tahmini_enerji_yuzde']:.2f} | "
                f"Teklif: {sonuc['teklif_puani']:.2f}"
            )
        else:
            print(
                f"Drone {drone.drone_id} | "
                f"Batarya: %{drone.batarya_yuzde:.1f} | "
                "TEKLİF REDDEDİLDİ"
            )

    uygun_teklifler = [
        teklif for teklif in teklifler if teklif["uygun"]
    ]

    if not uygun_teklifler:
        raise RuntimeError(
            "Görevi güvenli tamamlayabilecek drone bulunamadı."
        )

    kazanan = max(
        uygun_teklifler,
        key=lambda teklif: (
            teklif["teklif_puani"],
            -teklif["drone_id"],
        ),
    )

    print("\n=== İHALE SONUCU ===")
    print(f"Kazanan: Drone {kazanan['drone_id']}")
    print(f"Kazanan teklif: {kazanan['teklif_puani']:.2f}")
    print(f"Görev mesafesi: {kazanan['mesafe_m']:.3f} m")
    print(
        "Göreli hareket: "
        f"{kazanan['goreli_kuzey_m']:.2f} m kuzey, "
        f"{kazanan['goreli_dogu_m']:.2f} m doğu"
    )
    print(
        "Tahmini görev sonu batarya: "
        f"%{kazanan['kalan_batarya_yuzde']:.2f}"
    )

    return teklifler, kazanan


def ihale_csv_kaydet(teklifler, kazanan, zaman_etiketi):
    csv_yolu = Path(
        f"ihale_sonucu_{zaman_etiketi}.csv"
    )

    alanlar = [
        "gorev_id",
        "gorev_x_m",
        "gorev_y_m",
        "gorev_odulu",
        "drone_id",
        "drone_x_m",
        "drone_y_m",
        "batarya_yuzde",
        "mesafe_m",
        "tahmini_enerji_yuzde",
        "kalan_batarya_yuzde",
        "teklif_puani",
        "uygun",
        "kazanan",
    ]

    with csv_yolu.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as dosya:
        writer = csv.DictWriter(
            dosya,
            fieldnames=alanlar,
        )
        writer.writeheader()

        for teklif in teklifler:
            writer.writerow(
                {
                    "gorev_id": GOREV.gorev_id,
                    "gorev_x_m": GOREV.x_m,
                    "gorev_y_m": GOREV.y_m,
                    "gorev_odulu": GOREV.odul,
                    "drone_id": teklif["drone_id"],
                    "drone_x_m": teklif["drone_x_m"],
                    "drone_y_m": teklif["drone_y_m"],
                    "batarya_yuzde":
                        teklif["batarya_yuzde"],
                    "mesafe_m":
                        round(teklif["mesafe_m"], 4),
                    "tahmini_enerji_yuzde":
                        round(
                            teklif[
                                "tahmini_enerji_yuzde"
                            ],
                            4,
                        ),
                    "kalan_batarya_yuzde":
                        round(
                            teklif[
                                "kalan_batarya_yuzde"
                            ],
                            4,
                        ),
                    "teklif_puani":
                        (
                            round(
                                teklif["teklif_puani"],
                                4,
                            )
                            if teklif["teklif_puani"]
                            is not None
                            else ""
                        ),
                    "uygun": teklif["uygun"],
                    "kazanan":
                        teklif["drone_id"]
                        == kazanan["drone_id"],
                }
            )

    return csv_yolu


def yatay_mesafe_m(lat1, lon1, lat2, lon2):
    r = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(d_lambda / 2.0) ** 2
    )

    return 2.0 * r * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )


def goreli_hedefi_gps_cevir(
    baslangic_lat,
    baslangic_lon,
    kuzey_m,
    dogu_m,
):
    hedef_lat = baslangic_lat + kuzey_m / 111111.0

    metre_basina_boylam = (
        111111.0
        * math.cos(math.radians(baslangic_lat))
    )

    hedef_lon = baslangic_lon + dogu_m / metre_basina_boylam

    return hedef_lat, hedef_lon


async def ilk_konum(drone):
    async for position in drone.telemetry.position():
        return position


async def konum_kaydi(
    drone,
    writer,
    dosya,
    baslangic_zamani,
    home_lat,
    home_lon,
    hedef_lat,
    hedef_lon,
    kazanan,
    son_konum,
):
    async for position in drone.telemetry.position():
        home_mesafesi = yatay_mesafe_m(
            position.latitude_deg,
            position.longitude_deg,
            home_lat,
            home_lon,
        )

        hedef_mesafesi = yatay_mesafe_m(
            position.latitude_deg,
            position.longitude_deg,
            hedef_lat,
            hedef_lon,
        )

        son_konum["position"] = position
        son_konum["home_mesafesi"] = home_mesafesi
        son_konum["hedef_mesafesi"] = hedef_mesafesi

        writer.writerow(
            [
                round(
                    time.monotonic() - baslangic_zamani,
                    3,
                ),
                kazanan["drone_id"],
                round(kazanan["teklif_puani"], 3),
                position.latitude_deg,
                position.longitude_deg,
                round(position.absolute_altitude_m, 3),
                round(position.relative_altitude_m, 3),
                round(home_mesafesi, 3),
                round(hedef_mesafesi, 3),
            ]
        )

        dosya.flush()


async def yerde_mi_bekle(drone):
    havalanma_goruldu = False

    async for is_in_air in drone.telemetry.in_air():
        if is_in_air:
            havalanma_goruldu = True

        if havalanma_goruldu and not is_in_air:
            return


async def main():
    teklifler, kazanan = ihaleyi_calistir()

    zaman_etiketi = time.strftime("%Y%m%d_%H%M%S")
    ihale_csv = ihale_csv_kaydet(
        teklifler,
        kazanan,
        zaman_etiketi,
    )

    drone = System()
    await drone.connect(
        system_address="udpin://0.0.0.0:14540"
    )

    print("\nPX4 bağlantısı bekleniyor...")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ PX4 bağlantısı kuruldu.")
            break

    print("GPS ve home konumu bekleniyor...")

    async for health in drone.telemetry.health():
        if (
            health.is_global_position_ok
            and health.is_home_position_ok
        ):
            print("✅ Konum sistemi hazır.")
            break

    home = await ilk_konum(drone)

    home_lat = home.latitude_deg
    home_lon = home.longitude_deg
    home_absolute_altitude = home.absolute_altitude_m

    hedef_lat, hedef_lon = goreli_hedefi_gps_cevir(
        home_lat,
        home_lon,
        kazanan["goreli_kuzey_m"],
        kazanan["goreli_dogu_m"],
    )

    hedef_absolute_altitude = (
        home_absolute_altitude + KALKIS_IRTIFASI_M
    )

    print(f"Home:  {home_lat:.7f}, {home_lon:.7f}")
    print(f"Hedef: {hedef_lat:.7f}, {hedef_lon:.7f}")
    print(
        f"PX4, Drone {kazanan['drone_id']} aracını "
        "temsil edecek."
    )

    ucus_csv = Path(
        f"ihale_ucus_verisi_{zaman_etiketi}.csv"
    )

    son_konum = {}
    drone_havada = False

    with ucus_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as dosya:
        writer = csv.writer(dosya)

        writer.writerow(
            [
                "sure_s",
                "kazanan_drone_id",
                "kazanan_teklif_puani",
                "enlem_deg",
                "boylam_deg",
                "mutlak_irtifa_m",
                "bagil_irtifa_m",
                "home_mesafesi_m",
                "hedef_mesafesi_m",
            ]
        )

        baslangic_zamani = time.monotonic()

        kayit_gorevi = asyncio.create_task(
            konum_kaydi(
                drone,
                writer,
                dosya,
                baslangic_zamani,
                home_lat,
                home_lon,
                hedef_lat,
                hedef_lon,
                kazanan,
                son_konum,
            )
        )

        try:
            await drone.action.set_takeoff_altitude(
                KALKIS_IRTIFASI_M
            )
            await drone.action.set_return_to_launch_altitude(
                KALKIS_IRTIFASI_M
            )

            print("Drone arm ediliyor...")
            await drone.action.arm()

            print("Kalkış başlatılıyor...")
            await drone.action.takeoff()
            drone_havada = True

            kalkis_baslangici = time.monotonic()

            while True:
                position = son_konum.get("position")

                if (
                    position is not None
                    and position.relative_altitude_m >= 2.5
                ):
                    print(
                        "✅ Kalkış tamamlandı: "
                        f"{position.relative_altitude_m:.2f} m"
                    )
                    break

                if (
                    time.monotonic() - kalkis_baslangici
                    > GOREV_ZAMAN_ASIMI_S
                ):
                    raise TimeoutError(
                        "Kalkış süresi aşıldı."
                    )

                await asyncio.sleep(0.2)

            print(
                "Kazanan drone'un göreli hedefine "
                "gidiliyor..."
            )

            await drone.action.goto_location(
                hedef_lat,
                hedef_lon,
                hedef_absolute_altitude,
                0.0,
            )

            hedefte_sayac = 0
            hedef_bekleme_baslangici = time.monotonic()

            while True:
                hedef_mesafesi = son_konum.get(
                    "hedef_mesafesi"
                )

                if (
                    hedef_mesafesi is not None
                    and hedef_mesafesi
                    <= HEDEF_TOLERANSI_M
                ):
                    hedefte_sayac += 1
                else:
                    hedefte_sayac = 0

                if hedefte_sayac >= 5:
                    print(
                        "✅ Hedefe ulaşıldı. Hata: "
                        f"{hedef_mesafesi:.2f} m"
                    )
                    break

                if (
                    time.monotonic()
                    - hedef_bekleme_baslangici
                    > GOREV_ZAMAN_ASIMI_S
                ):
                    raise TimeoutError(
                        "Hedefe ulaşma süresi aşıldı."
                    )

                await asyncio.sleep(0.2)

            print("Hedefte 3 saniye bekleniyor...")
            await drone.action.hold()
            await asyncio.sleep(3)

            print("RTL başlatılıyor...")
            await drone.action.return_to_launch()

            await asyncio.wait_for(
                yerde_mi_bekle(drone),
                timeout=GOREV_ZAMAN_ASIMI_S,
            )

            drone_havada = False

            toplam_sure = (
                time.monotonic() - baslangic_zamani
            )
            home_hatasi = son_konum.get(
                "home_mesafesi",
                math.nan,
            )
            hedef_hatasi = son_konum.get(
                "hedef_mesafesi",
                math.nan,
            )

            print("✅ İniş tamamlandı.")
            print(
                f"Kazanan drone: "
                f"Drone {kazanan['drone_id']}"
            )
            print(
                f"Toplam görev süresi: "
                f"{toplam_sure:.2f} s"
            )
            print(
                f"Son home hatası: "
                f"{home_hatasi:.2f} m"
            )
            print(
                f"Son hedef mesafesi: "
                f"{hedef_hatasi:.2f} m"
            )
            print(
                f"İhale CSV: {ihale_csv.resolve()}"
            )
            print(
                f"Uçuş CSV: {ucus_csv.resolve()}"
            )

        except Exception as hata:
            print(f"❌ Görev hatası: {hata}")

            if drone_havada:
                print(
                    "Güvenlik için RTL gönderiliyor..."
                )

                try:
                    await drone.action.return_to_launch()

                    await asyncio.wait_for(
                        yerde_mi_bekle(drone),
                        timeout=GOREV_ZAMAN_ASIMI_S,
                    )
                except Exception as rtl_hatasi:
                    print(f"RTL hatası: {rtl_hatasi}")

        finally:
            kayit_gorevi.cancel()

            try:
                await kayit_gorevi
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())

