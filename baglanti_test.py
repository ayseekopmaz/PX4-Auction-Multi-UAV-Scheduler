import asyncio
from mavsdk import System


async def main():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    print("PX4 bağlantısı bekleniyor...")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ PX4 bağlantısı kuruldu.")
            break

    async for health in drone.telemetry.health():
        print(f"Global konum hazır: {health.is_global_position_ok}")
        print(f"Home konumu hazır: {health.is_home_position_ok}")
        break

    async for battery in drone.telemetry.battery():
        print(f"Batarya: %{battery.remaining_percent:.1f}")
        break

    async for position in drone.telemetry.position():
        print(f"Enlem: {position.latitude_deg:.7f}")
        print(f"Boylam: {position.longitude_deg:.7f}")
        print(f"Bağıl irtifa: {position.relative_altitude_m:.2f} m")
        break

    print("✅ MAVSDK telemetri testi tamamlandı.")


if __name__ == "__main__":
    asyncio.run(main())




