import asyncio
import csv
import math
import time
from pathlib import Path

from mavsdk import System


KALKIS_IRTIFASI_M = 3.0
HEDEF_KUZEY_M = 5.0
HEDEF_TOLERANSI_M = 0.7
GOREV_ZAMAN_ASIMI_S = 90


def mesafe_m(lat1, lon1, lat2, lon2):
    """İki GPS noktası arasındaki yatay mesafe."""
    r = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(d_lambda / 2) ** 2
    )

    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def ilk_konum(drone):
    async for position in drone.telemetry.position():
        return position


async def konum_kaydi(
    drone,
    csv_writer,
    dosya,
    baslangic_zamani,
    home_lat,
    home_lon,
    hedef_lat,
    hedef_lon,
    son_konum,
):
    async for position in drone.telemetry.position():
        home_mesafesi = mesafe_m(
            position.latitude_deg,
            position.longitude_deg,
            home_lat,
            home_lon,
        )

        hedef_mesafesi = mesafe_m(
            position.latitude_deg,
            position.longitude_deg,
            hedef_lat,
            hedef_lon,
        )

        son_konum["position"] = position
        son_konum["home_mesafesi"] = home_mesafesi
        son_konum["hedef_mesafesi"] = hedef_mesafesi

        csv_writer.writerow(
            [
                round(time.monotonic() - baslangic_zamani, 3),
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
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    print("PX4 bağlantısı bekleniyor...")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ PX4 bağlantısı kuruldu.")
            break

    print("GPS ve home konumu bekleniyor...")

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("✅ Konum sistemi hazır.")
            break

    home = await ilk_konum(drone)

    home_lat = home.latitude_deg
    home_lon = home.longitude_deg
    home_absolute_altitude = home.absolute_altitude_m

    # Yaklaşık 5 metre kuzeydeki hedef
    hedef_lat = home_lat + (HEDEF_KUZEY_M / 111111.0)
    hedef_lon = home_lon
    hedef_absolute_altitude = (
        home_absolute_altitude + KALKIS_IRTIFASI_M
    )

    print(f"Home:  {home_lat:.7f}, {home_lon:.7f}")
    print(f"Hedef: {hedef_lat:.7f}, {hedef_lon:.7f}")
    print("Görev: 3 m kalkış → 5 m kuzey → RTL")

    zaman_etiketi = time.strftime("%Y%m%d_%H%M%S")
    csv_yolu = Path(f"ucus_verisi_{zaman_etiketi}.csv")
    son_konum = {}

    with csv_yolu.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as dosya:
        writer = csv.writer(dosya)

        writer.writerow(
            [
                "sure_s",
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
                son_konum,
            )
        )

        drone_havada = False

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

                await asyncio.sleep(0.2)

            print("5 metre kuzeydeki hedefe gidiliyor...")

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
                    and hedef_mesafesi <= HEDEF_TOLERANSI_M
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
                    time.monotonic() - hedef_bekleme_baslangici
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
            toplam_sure = time.monotonic() - baslangic_zamani
            home_hatasi = son_konum.get("home_mesafesi", math.nan)

            print("✅ İniş tamamlandı.")
            print(f"Toplam görev süresi: {toplam_sure:.2f} s")
            print(f"Son home hatası: {home_hatasi:.2f} m")
            print(f"CSV kaydedildi: {csv_yolu.resolve()}")

        except Exception as hata:
            print(f"❌ Görev hatası: {hata}")

            if drone_havada:
                print("Güvenlik için RTL gönderiliyor...")

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


if __name__ == "__main__": asyncio.run(main())

