import asyncio

import kontrollu_deneyler as kd


kd.DRONELAR = [
    kd.Drone(1, 0.0, 0.0, 70.0),
    kd.Drone(2, 0.0, 0.0, 70.0),
    kd.Drone(3, 4.0, 0.0, 40.0),
]

kd.GOREV = kd.Gorev(
    gorev_id=4,
    x_m=0.0,
    y_m=3.0,
    odul=100.0,
)


if __name__ == "__main__":
    print("=" * 60)
    print("PİLOT UÇUŞ 4/4: EŞİT TEKLİF - KÜÇÜK ID")
    print("Beklenen eşit teklif: Drone 1 = Drone 2")
    print("Beklenen kazanan: Drone 1")
    print("Beklenen uçuş mesafesi: 3 metre kuzey")
    print("=" * 60)

    asyncio.run(kd.main())

