from dataclasses import dataclass
from math import hypot


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


MESAFE_AGIRLIGI = 2.0
ENERJI_AGIRLIGI = 1.0
BATARYA_AGIRLIGI = 20.0
METRE_BASI_ENERJI = 0.50
MIN_GUVENLI_BATARYA = 30.0


def teklif_hesapla(drone, gorev):
    mesafe = hypot(
        gorev.x_m - drone.x_m,
        gorev.y_m - drone.y_m,
    )

    gidis_donus_mesafesi = 2 * mesafe
    tahmini_enerji = gidis_donus_mesafesi * METRE_BASI_ENERJI

    if drone.batarya_yuzde < MIN_GUVENLI_BATARYA:
        return None

    if drone.batarya_yuzde - tahmini_enerji < MIN_GUVENLI_BATARYA:
        return None

    teklif = (
        gorev.odul
        - MESAFE_AGIRLIGI * mesafe
        - ENERJI_AGIRLIGI * tahmini_enerji
        + BATARYA_AGIRLIGI * (drone.batarya_yuzde / 100)
    )

    return {
        "drone_id": drone.drone_id,
        "mesafe_m": mesafe,
        "tahmini_enerji_yuzde": tahmini_enerji,
        "kalan_batarya_yuzde": drone.batarya_yuzde - tahmini_enerji,
        "teklif_puani": teklif,
    }


dronelar = [
    Drone(drone_id=1, x_m=0, y_m=0, batarya_yuzde=70),
    Drone(drone_id=2, x_m=4, y_m=0, batarya_yuzde=90),
    Drone(drone_id=3, x_m=2, y_m=4, batarya_yuzde=45),
]

gorev = Gorev(
    gorev_id=1,
    x_m=0,
    y_m=5,
    odul=100,
)

teklifler = []

print("=== DİNAMİK GÖREV İHALESİ ===")
print(
    f"Görev {gorev.gorev_id} | "
    f"Konum: ({gorev.x_m}, {gorev.y_m}) | "
    f"Ödül: {gorev.odul}"
)

for drone in dronelar:
    sonuc = teklif_hesapla(drone, gorev)

    if sonuc is None:
        print(
            f"Drone {drone.drone_id} | "
            f"Batarya: %{drone.batarya_yuzde:.1f} | "
            "TEKLİF REDDEDİLDİ"
        )
        continue

    teklifler.append(sonuc)

    print(
        f"Drone {drone.drone_id} | "
        f"Mesafe: {sonuc['mesafe_m']:.2f} m | "
        f"Batarya: %{drone.batarya_yuzde:.1f} | "
        f"Tahmini enerji: %{sonuc['tahmini_enerji_yuzde']:.2f} | "
        f"Teklif: {sonuc['teklif_puani']:.2f}"
    )

if not teklifler:
    print("\nGörevi güvenli şekilde tamamlayabilecek drone bulunamadı.")
else:
    kazanan = max(
        teklifler,
        key=lambda teklif: (
            teklif["teklif_puani"],
            -teklif["drone_id"],
        ),
    )

    print("\n=== İHALE SONUCU ===")
    print(f"Kazanan: Drone {kazanan['drone_id']}")
    print(f"Kazanan teklif: {kazanan['teklif_puani']:.2f}")
    print(f"Görev mesafesi: {kazanan['mesafe_m']:.2f} m")
    print(
        "Tahmini görev sonu batarya: "
        f"%{kazanan['kalan_batarya_yuzde']:.2f}"
    )

