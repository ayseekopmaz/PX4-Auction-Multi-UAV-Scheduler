# 🚁 PX4 & MAVSDK Auction-Based Multi-UAV Mission Scheduler

![PX4](https://img.shields.io/badge/Autopilot-PX4-blue)
![Sim-Environment](https://img.shields.io/badge/Simulation-Gazebo-orange)
![API](https://img.shields.io/badge/API-MAVSDK%20Python-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

Bu proje; çoklu İHA (Drone) filolarında **açık artırma / ihale algoritması (Auction-based Task Allocation)** kullanarak otonom görev dağılımı sağlayan ve **PX4 / Gazebo** ortamında uçuş testlerini otomatize eden bir simülasyon altyapısıdır[cite: 12, 19].

Sistem, tanımlanan her görev için filodaki droneların konum, batarya ve mesafe maliyetlerini hesaplar; en optimize teklif puanını veren drone'a görevi atayarak otonom uçuşu başlatır[cite: 17, 19].

---

## 💡 Öne Çıkan Özellikler

* 🎯 **Dinamik Görev İhale Algoritması:** Görev ödülü, mesafe maliyeti, tahmini enerji tüketimi ve anlık batarya yüzdesine göre teklif puanı (`bid_score`) hesaplar[cite: 17, 19].
* 🛡️ **Güvenli Batarya Koruması:** Tahmini görev sonu bataryası $\%30$'un altına düşen dronelar ihaleden otomatik reddedilir[cite: 17, 19].
* ✈️ **Tam Otonom Uçuş (MAVSDK & PX4):** İhaleyi kazanan drone otonom olarak arm olur, kalkış yapar, hedefe yönelir, bekler ve RTL (Return-to-Launch) ile iniş gerçekleştirir[cite: 15, 18, 19].
* 🧪 **Otomatik Deney & Senaryo Testleri:** Farklı batarya, farklı mesafe, düşük batarya reddi ve eşit teklif senaryolarını ardışık $10$'ar kez ($40$ kontrollü deney) koşturabilir[cite: 12, 20].
* 📊 **Ayrıntılı Telemetri & CSV Analizi:** Uçuş süreleri, hedef varış hataları, home dönüş sapmaları ve irtifa verilerini milisaniyelik kaydedip istatistiksel özet çıkarır[cite: 12, 14, 16].

---

## 🧰 Donanım ve Yazılım Gereksinimleri

* **İşletim Sistemi:** Linux (Ubuntu 20.04/22.04 önerilir) veya Windows WSL2
* **Otopilot & Simülasyon:** PX4-Autopilot & Gazebo SITL
* **Dil & Kütüphaneler:** Python 3.8+, `mavsdk`, `asyncio`[cite: 11, 13, 15]

---


