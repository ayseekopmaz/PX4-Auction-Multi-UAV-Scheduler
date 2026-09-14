import kontrollu_deneyler as kd


SENARYOLAR = [
    {
        "ad": "farkli_batarya",
        "dronelar": [
            kd.Drone(1, 0.0, 0.0, 50.0),
            kd.Drone(2, 0.0, 0.0, 70.0),
            kd.Drone(3, 0.0, 0.0, 90.0),
        ],
        "gorev": kd.Gorev(1, 0.0, 3.0, 100.0),
        "beklenen_kazanan": 3,
        "beklenen_reddedilen": [],
    },
    {
        "ad": "farkli_mesafe",
        "dronelar": [
            kd.Drone(1, 0.0, 0.0, 70.0),
            kd.Drone(2, 0.0, 3.0, 70.0),
            kd.Drone(3, 4.0, 0.0, 70.0),
        ],
        "gorev": kd.Gorev(1, 0.0, 5.0, 100.0),
        "beklenen_kazanan": 2,
        "beklenen_reddedilen": [],
    },
    {
        "ad": "dusuk_batarya_reddi",
        "dronelar": [
            kd.Drone(1, 0.0, 4.5, 30.0),
            kd.Drone(2, 0.0, 2.0, 70.0),
            kd.Drone(3, 4.0, 0.0, 80.0),
        ],
        "gorev": kd.Gorev(1, 0.0, 5.0, 100.0),
        "beklenen_kazanan": 2,
        "beklenen_reddedilen": [1],
    },
    {
        "ad": "esit_teklif_kucuk_id",
        "dronelar": [
            kd.Drone(1, 0.0, 0.0, 70.0),
            kd.Drone(2, 0.0, 0.0, 70.0),
            kd.Drone(3, 4.0, 0.0, 40.0),
        ],
        "gorev": kd.Gorev(1, 0.0, 3.0, 100.0),
        "beklenen_kazanan": 1,
        "beklenen_reddedilen": [],
    },
]


def senaryoyu_test_et(senaryo):
    kd.DRONELAR = senaryo["dronelar"]
    kd.GOREV = senaryo["gorev"]

    teklifler, kazanan = kd.ihaleyi_calistir()

    reddedilenler = sorted(
        teklif["drone_id"]
        for teklif in teklifler
        if not teklif["uygun"]
    )

    kazanan_dogru = (
        kazanan["drone_id"]
        == senaryo["beklenen_kazanan"]
    )
    ret_dogru = (
        reddedilenler
        == senaryo["beklenen_reddedilen"]
    )

    basarili = kazanan_dogru and ret_dogru

    print("\n--- TEST SONUCU ---")
    print(f"Senaryo: {senaryo['ad']}")
    print(
        f"Beklenen kazanan: "
        f"Drone {senaryo['beklenen_kazanan']}"
    )
    print(f"Gerçek kazanan: Drone {kazanan['drone_id']}")
    print(
        f"Beklenen reddedilenler: "
        f"{senaryo['beklenen_reddedilen']}"
    )
    print(f"Gerçek reddedilenler: {reddedilenler}")
    print("SONUÇ:", "BAŞARILI ✅" if basarili else "HATALI ❌")

    return basarili


def main():
    sonuclar = []

    for sira, senaryo in enumerate(SENARYOLAR, start=1):
        print("\n" + "=" * 60)
        print(
            f"PİLOT SENARYO {sira}/{len(SENARYOLAR)}: "
            f"{senaryo['ad']}"
        )
        print("=" * 60)

        sonuclar.append(senaryoyu_test_et(senaryo))

    print("\n" + "=" * 60)
    print("GENEL PİLOT TEST SONUCU")
    print("=" * 60)
    print(f"Başarılı senaryo: {sum(sonuclar)}/4")

    if all(sonuclar):
        print("Dört ihale senaryosu doğrulandı ✅")
    else:
        print("En az bir senaryoda hata bulundu ❌")


if __name__ == "__main__":
    main()

