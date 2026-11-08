# Gait Analysis Markerless

Sistem analisis gait berbasis OpenPose untuk ekstraksi parameter berjalan dari video sagittal. Aplikasi ini menyediakan antarmuka GUI modern untuk menganalisis pola berjalan tanpa menggunakan marker fisik.

## Fitur Utama

- **Analisis Video** - Ekstraksi pose dari video berjalan menggunakan OpenPose
- **Deteksi Otomatis** - Deteksi gait event (Heel Strike & Toe Off) secara otomatis
- **Koreksi Manual** - Tools untuk koreksi ID kaki kiri/kanan dan gait events
- **Skalabilitas** - Konversi koordinat piksel ke satuan meter
- **Signal Processing** - Preprocessing dan filtering sinyal koordinat
- **Gait Parameters** - Kalkulasi parameter gait (stride length, step length, cadence, dll)
- **Laporan** - Visualisasi hasil analisis dan ekspor laporan

## Instalasi

### Prasyarat

- Python 3.8 atau lebih baru
- OpenPose (portable atau terinstal)

### Langkah Instalasi

```bash
# Clone repository
git clone <repository-url>
cd Gait_Analysis

# Buat virtual environment (opsional)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Penggunaan

Jalankan aplikasi GUI:

```bash
python src/gui/main.py
```

### Alur Kerja Analisis

1. **Project Input** - Buat project baru dengan subject ID dan pilih video
2. **OpenPose** - Ekstraksi pose keypoints dari video
3. **Scaling** - Kalibrasi skala menggunakan referensi panjang (tinggi badan)
4. **Correction** - Koreksi ID kaki kiri/kanan jika diperlukan
5. **Preprocessing** - Filtering dan smoothing sinyal koordinat
6. **Gait Event** - Deteksi dan koreksi manual heel strike/toe off
7. **Gait Parameters** - Kalkulasi parameter gait final
8. **Report** - Lihat dan ekspor hasil analisis

## Struktur Project

```
Gait_Analysis/
├── src/
│   ├── gui/                    # Komponen antarmuka PyQt5
│   │   ├── main.py             # Entry point aplikasi
│   │   ├── dashboard_tab.py    # Tab dashboard
│   │   ├── analysis_tab.py     # Tab analisis pipeline
│   │   ├── report_tab.py       # Tab laporan hasil
│   │   └── ...                 # Tab dan komponen lainnya
│   ├── project_input/          # Manajemen input project
│   ├── openpose/               # Ekstraksi pose dari video
│   ├── scaling/                # Konversi skala piksel ke meter
│   ├── correction_legid/       # Koreksi ID kaki kiri/kanan
│   ├── signal_processing/      # Preprocessing sinyal
│   ├── gait_event/             # Deteksi gait events
│   └── gait_parameter/         # Kalkulasi parameter gait
├── config/
│   ├── openpose_config.yaml    # Konfigurasi OpenPose
│   ├── signal_config.yaml      # Konfigurasi signal processing
│   └── gait_config.yaml        # Konfigurasi parameter gait
├── data/                       # Data project (auto-generated)
├── requirements.txt            # Dependencies Python
└── README.md
```

## Konfigurasi

File konfigurasi tersedia di folder `config/`:

- **openpose_config.yaml** - Path OpenPose dan parameter ekstraksi
- **signal_config.yaml** - Parameter filtering dan smoothing
- **gait_config.yaml** - Parameter deteksi gait event

## Dependencies

- numpy >= 1.21.0
- scipy >= 1.7.0
- opencv-python >= 4.5.0
- PyQt5 >= 5.15.0
- matplotlib >= 3.4.0
- pyyaml >= 5.4.0
- pandas >= 1.3.0

## Lisensi

© 2026 Gait Analysis Markerless
