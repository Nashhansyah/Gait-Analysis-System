# Gait Analysis Markerless

[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.11-blue)](https://www.python.org/)
[![Python Syntax Check](https://github.com/Nashhansyah/Gait-Analysis-System/actions/workflows/python-syntax.yml/badge.svg)](https://github.com/Nashhansyah/Gait-Analysis-System/actions/workflows/python-syntax.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](#persyaratan)

Aplikasi desktop untuk analisis gaya berjalan (*gait analysis*) **markerless** berbasis **OpenPose** dari video sagittal satu kamera. Pipeline lengkap mulai dari ekstraksi pose, pembersihan sinyal, kalibrasi skala, koreksi manual, deteksi gait event, hingga perhitungan parameter dan ekspor laporan.

Antarmuka dibangun dengan **PyQt5** dan terdiri dari 4 halaman utama: **Homepage**, **Analysis**, **Report**, dan **Monitoring**.

**English:** [README.md](README.md)

---

## Demo

> 🎬 GIF singkat (video berjalan → skeleton overlay → plot fase gait) dan screenshot GUI akan ditambahkan di sini.

<!--
Setelah file media ditaruh di docs/images/, ganti bagian ini dengan:

| Homepage | Pipeline analisis |
|:--:|:--:|
| ![Homepage](docs/images/dashboard.png) | ![Pipeline](docs/images/analysis.png) |

| Report & fase gait | Tren monitoring |
|:--:|:--:|
| ![Report](docs/images/report.png) | ![Monitoring](docs/images/monitoring.png) |

![Demo pipeline](docs/images/demo.gif)
-->

Alur singkat: buat subject dan session → jalankan wizard 6 tahap → buka Report untuk melihat
video tersinkron dengan grafik fase STANCE/SWING → ekspor Excel multi-sheet berisi parameter
spasiotemporal, siklus gait, detail per langkah, dan kinematik sendi.

---

## Fitur Utama

| Halaman | Fitur |
|---|---|
| **Homepage** | Manajemen *subject* & *session*, statistik project (jumlah subject/session, ukuran storage), pencarian, tambah/hapus project dan session |
| **Analysis** | Wizard 6 tahap berurutan dengan status tiap tahap dan auto-advance setelah tahap selesai |
| **Report** | Player video tersinkron dengan plot fase gait, tabel ringkasan, detail siklus, dan kinematik sendi; ekspor CSV & Excel |
| **Monitoring** | Tren parameter gait antar session untuk memantau progres rehabilitasi (8 grafik) |

Fitur pendukung:

- **Rekam video langsung** dari webcam lokal atau kamera HP via IP stream (`http://.../video`), dilengkapi hitung mundur dan isyarat audio sebelum rekaman mulai.
- **Koreksi manual** ID kaki kiri/kanan per frame (swap) maupun otomatis.
- **Koreksi manual gait event** (tambah/hapus *heel strike* dan *toe off*).
- **Ekspor foto OpenPose resolusi tinggi** dengan skeleton overlay per frame.
- Data disimpan per *subject* dan per *session*, sehingga riwayat pengukuran bisa dibandingkan.

---

## Alur Pipeline (6 Tahap)

```
Video               OpenPose            Preprocessing        Scaling
  │                    │                    │                  │
  └──► 1. OpenPose ────┴──► 2. Preprocessing ──► 3. Scaling ──┘
                                                               │
     6. Parameters ◄── 5. Gait Event ◄── 4. Correction ◄──────┘
```

1. **OpenPose** — Menjalankan `OpenPoseDemo.exe` via subprocess dengan model `BODY_25`, 1 orang, output JSON keypoint (opsional video overlay `*_openpose.avi`).
2. **Preprocessing** — Pembersihan sinyal koordinat:
   - *Confidence filtering* (threshold 0.3; ankle & mid-hip 0.4)
   - *Gap filling* interpolasi linear (maks. 10 frame, fallback backward/forward fill)
   - *Median filter* (kernel 5) untuk menghilangkan spike
   - *Savitzky–Golay* (window 11, polyorder 2) untuk mempertahankan bentuk peak/valley
   - *Butterworth low-pass* orde 2, cutoff 2.5 Hz untuk analisis parameter
   - *Resampling* ke 30 fps
3. **Scaling** — Kalibrasi piksel → meter dengan menandai 2 titik referensi pada frame dan memasukkan jarak nyata (mis. tinggi badan), lalu faktor skala diterapkan ke seluruh koordinat.
4. **Correction** — Memastikan konsistensi label kaki kiri/kanan: swap per frame secara manual (shortcut `S`) atau *Auto Correct Swaps* untuk seluruh video.
5. **Gait Event** — Deteksi otomatis:
   - **Heel Strike (HS)** = peak posisi ankle relatif terhadap hip (`scipy.find_peaks`)
   - **Toe Off (TO)** = titik minimum di antara dua HS berurutan
   - Pelabelan fase *stance*/*swing*, pembentukan siklus gait (durasi valid 0.6–2.0 s), plus validasi biomekanik
6. **Parameters** — Perhitungan parameter spasial, temporal, spasiotemporal, dan kinematik sendi, lalu disimpan sebagai JSON/CSV/Excel.

---

## Persyaratan

- **Windows 10/11** — isyarat audio rekaman memakai `winsound`, dan OpenPose dijalankan sebagai `.exe`.
- **Python 3.9 – 3.11** (diuji pada 3.11.8).
- **OpenPose** (Windows portable/demo) beserta model `BODY_25`.
- Kamera/webcam (opsional, hanya untuk perekaman langsung).

Dependensi Python: `numpy`, `scipy`, `opencv-python`, `PyQt5`, `matplotlib`, `pyyaml`, `pandas`, `openpyxl`.

---

## Instalasi

```bat
git clone https://github.com/Nashhansyah/Gait-Analysis-System.git
cd Gait-Analysis-System

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### Konfigurasi OpenPose

Sesuaikan path instalasi OpenPose di `config/openpose_config.yaml`:

```yaml
openpose:
  executable_path: "C:/openpose/bin/OpenPoseDemo.exe"
  model_folder: "C:/openpose/models"
  model_pose: "BODY_25"
```

---

## Menjalankan Aplikasi

```bat
python src/gui/main.py
```

---

## Panduan Penggunaan

### 1. Homepage — buat project

1. Klik **New Subject**, masukkan nama/ID subject.
2. Klik **Add New Session** pada subject tersebut.
3. Pilih sumber video: **Browse** file, atau **rekam** langsung (webcam/IP kamera HP).
4. Video disalin ke folder project, metadata (fps, resolusi, jumlah frame, durasi) tersimpan otomatis.

### 2. Analysis — jalankan pipeline

Pilih session lalu ikuti wizard 6 tahap. Tiap tahap selesai akan otomatis mengarahkan ke tahap berikutnya.

- **OpenPose** — jalankan ekstraksi; tersedia opsi membuat video overlay.
- **Preprocessing** — jalankan filter; tersedia plot perbandingan sinyal sebelum/sesudah.
- **Scaling** — tandai 2 titik referensi dan isi jarak nyata (meter).
- **Correction** — periksa frame yang label kakinya tertukar, gunakan swap atau auto-correct.
- **Gait Event** — jalankan *Auto Detect Events (HS/TO)*, lalu perbaiki manual bila ada event yang salah.
- **Parameters** — klik **Compute Parameters** untuk menghitung seluruh parameter + kinematik.

### 3. Report — lihat & ekspor hasil

- Pilih project/session, lalu muat laporan.
- Video diputar bersamaan dengan plot fase gait (STANCE/SWING per sisi) dan indikator frame.
- Tabel tersedia untuk ringkasan parameter, detail siklus, dan sudut sendi.
- **Export CSV & All** / **Export Excel (.xlsx)** untuk menyimpan laporan.

### 4. Monitoring — tren antar session

Pilih subject lalu klik **Analyze** untuk melihat grafik tren *walking speed*, *cadence*, *stride length*, *step length*, serta *stance/swing ratio* kiri dan kanan antar session.

> **Tips perekaman:** subjek berjalan tegak lurus terhadap kamera (tampak sagittal), seluruh tubuh terlihat, satu orang dalam frame, kamera statis, dan pencahayaan cukup agar confidence keypoint tinggi.

---

## Parameter yang Dihitung

**Per langkah (step)**

| Parameter | Satuan | Keterangan |
|---|---|---|
| `step_time` | s | Durasi satu langkah |
| `step_length` | m | Jarak horizontal antar posisi kaki |
| `step_velocity` | m/s | Kecepatan langkah |

**Per siklus (cycle)**

| Parameter | Satuan | Keterangan |
|---|---|---|
| `cycle_time` | s | Durasi satu siklus gait |
| `stride_length` | m | Panjang satu stride |
| `walking_speed` | m/s | Kecepatan berjalan |
| `cadence` | steps/min | Kadence |
| `stance_ratio` / `swing_ratio` | % | Proporsi fase stance/swing (total dan per sisi) |

**Kinematik**

Sudut **hip**, **knee**, dan **ankle** untuk sisi kiri & kanan, masing-masing dengan `mean`, `min`, `max`, `std`, dan **ROM** (range of motion) dalam derajat.

Ringkasan statistik yang dihasilkan: `mean`, `std`, `min`, `max`, `median` untuk tiap parameter.

---

## Konfigurasi

| File | Isi |
|---|---|
| `config/openpose_config.yaml` | Path OpenPose, model pose (`BODY_25`), indeks joint, opsi eksekusi |
| `config/signal_config.yaml` | Threshold confidence, gap filling, median/Savitzky–Golay/Butterworth filter, resampling |
| `config/gait_config.yaml` | Batas durasi siklus, rasio stance/swing, parameter deteksi HS/TO, batasan biomekanik |

---

## Struktur Repository

```
Gait_Analysis/
├── src/
│   ├── gui/                    # Antarmuka PyQt5
│   │   ├── main.py             # Entry point aplikasi
│   │   ├── sidebar.py          # Navigasi Homepage/Analysis/Report/Monitoring
│   │   ├── styles.py           # Tema & style
│   │   ├── dashboard_tab.py    # Manajemen subject & session
│   │   ├── analysis_tab.py     # Wizard pipeline 6 tahap
│   │   ├── openpose_tab.py     # Tahap 1
│   │   ├── preprocessing_tab.py# Tahap 2
│   │   ├── scaling_tab.py      # Tahap 3
│   │   ├── correction_tab.py   # Tahap 4
│   │   ├── gait_event_tab.py   # Tahap 5
│   │   ├── gait_param_tab.py   # Tahap 6
│   │   ├── report_tab.py       # Laporan & ekspor
│   │   ├── rehabilitation_tab.py# Monitoring tren
│   │   ├── project_dialogs.py  # Dialog subject/session/video
│   │   └── camera_recording_dialog.py # Rekaman webcam/IP kamera
│   ├── project_input/          # Manajemen struktur project & metadata
│   ├── openpose/               # Wrapper eksekusi OpenPose
│   ├── signal_processing/      # Filtering & smoothing sinyal
│   ├── scaling/                # Konversi piksel → meter
│   ├── correction_legid/       # Koreksi label kaki kiri/kanan
│   ├── gait_event/             # Deteksi HS/TO & siklus gait
│   ├── gait_parameter/         # Parameter & kinematik + ekspor
│   └── rehabilitation/         # Agregasi data antar session
├── config/                     # File konfigurasi YAML
├── data/                       # Data project (auto-generated, tidak di-commit)
├── docs/images/                # Screenshot & GIF demo untuk README
├── requirements.txt
├── CITATION.cff
├── LICENSE
├── README.md                   # Dokumentasi (English, default)
└── README.id.md                # Dokumentasi (Bahasa Indonesia)
```

---

## Output Data

Seluruh hasil disimpan di folder `data/` (dibuat otomatis) dengan format penamaan `{subject}_{session}` — nama session `default` dihilangkan dari nama file:

```
data/
├── metadata/{subject}.json                      # Info video + status pipeline per session
├── input_video/{subject}/{session}/video_raw.mp4
├── openpose_raw/{subject}/{session}/*_keypoints.json
├── openpose_frames/{subject}/{session}/         # Foto resolusi tinggi + skeleton
├── correction_legid/{subject}_corrected.json
├── scaled_pose/{subject}_scaled.json
├── preprocessed_signal/{subject}_signal.json
├── gait_events/{subject}_events.json
└── gait_parameters/{subject}/{session}/
    ├── {subject}_{session}_step.csv
    ├── {subject}_{session}_cycle.csv
    ├── {subject}_{session}_summary.csv
    ├── {subject}_{session}_kinematics.csv
    └── {subject}_{session}_gait_analysis_report.xlsx
```

File Excel berisi 5 sheet:

1. **Ringkasan Parameter** — parameter spasiotemporal
2. **Siklus Gait** — detail per siklus
3. **Detail Langkah** — detail per langkah
4. **Ringkasan Sudut Sendi** — statistik kinematik
5. **Deret Waktu Sudut** — time series sudut per frame disertai gambar frame video

---

## Catatan Repository

Folder `data/`, `.venv/`, `__pycache__/`, serta aset desain (`*.drawio`, `*.docx`, `*.png`, `prd.md`) **tidak di-commit** (lihat `.gitignore`). Repository hanya berisi kode, konfigurasi, dan dokumentasi. Data hasil pengukuran tetap tersimpan lokal di mesin masing-masing.

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| OpenPose gagal dijalankan | Periksa `executable_path` dan `model_folder` di `config/openpose_config.yaml` |
| Banyak keypoint `NaN` | Perbaiki pencahayaan/kontras, pastikan seluruh tubuh terlihat; turunkan threshold confidence di `signal_config.yaml` |
| Deteksi HS/TO meleset | Koreksi manual di tahap Gait Event; sesuaikan `min_peak_distance`, `min_prominence`, atau batas durasi siklus di `gait_config.yaml` |
| Hasil panjang/kecepatan tidak realistis | Ulangi kalibrasi di tahap Scaling (2 titik referensi + jarak nyata) |
| Tidak ada suara saat rekaman | Isyarat audio hanya tersedia di Windows (`winsound`) |
| Semua siklus ditandai tidak valid | Parameter tetap dihitung memakai seluruh siklus dengan peringatan; periksa kualitas video/event |

---

## Sitasi

Jika perangkat lunak ini dipakai dalam penelitian atau proyek klinis, silakan sitasi menggunakan metadata di [CITATION.cff](CITATION.cff).

---

## Lisensi

Dirilis di bawah [MIT License](LICENSE).

© 2026 Gait Analysis Markerless
