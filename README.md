# Gait Analysis Markerless

[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.11-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](#requirements)

A desktop application for **markerless gait analysis** built on **OpenPose**, using a single sagittal camera. It covers the full pipeline: pose extraction, signal cleaning, pixel-to-meter calibration, manual correction, gait-event detection, parameter extraction, and CSV/Excel reporting.

The GUI is built with **PyQt5** and has four main pages: **Homepage**, **Analysis**, **Report**, and **Monitoring**.

**Bahasa Indonesia:** [README.id.md](README.id.md)

---

## Demo

> 🎬 A short GIF (walking video → skeleton overlay → gait-phase plot) and GUI screenshots will be added here.

<!--
Once you add the media files under docs/images/, replace this section with:

| Homepage | Analysis pipeline |
|:--:|:--:|
| ![Homepage](docs/images/dashboard.png) | ![Pipeline](docs/images/analysis.png) |

| Report & gait phases | Monitoring trends |
|:--:|:--:|
| ![Report](docs/images/report.png) | ![Monitoring](docs/images/monitoring.png) |

![Pipeline demo](docs/images/demo.gif)
-->

Walkthrough in 20 seconds: create a subject and session → run the 6-step wizard → open the
report to see the video synced with the STANCE/SWING phase chart → export a multi-sheet Excel
file containing spatiotemporal parameters, gait cycles, per-step details, and joint kinematics.

---

## Features

| Page | Features |
|---|---|
| **Homepage** | Subject & session management, project statistics (subjects, sessions, storage size), search, add/delete projects and sessions |
| **Analysis** | Sequential 6-step wizard with per-step status and auto-advance on completion |
| **Report** | Video player synchronized with the gait-phase plot, summary tables, per-cycle details, and joint kinematics; CSV & Excel export |
| **Monitoring** | Gait parameter trends across sessions for rehabilitation progress tracking (8 charts) |

Supporting features:

- **Record video directly** from a local webcam or a phone camera over an IP stream (`http://.../video`), with a countdown and audio cue before recording starts.
- **Manual correction** of left/right leg IDs per frame (swap) or automatically for the whole video.
- **Manual gait-event correction** (add/remove heel strikes and toe offs).
- **High-resolution OpenPose frame export** with skeleton overlay.
- Data is stored per subject and per session, so measurement history can be compared over time.

---

## Pipeline (6 Steps)

```
Video               OpenPose            Preprocessing        Scaling
  │                    │                    │                  │
  └──► 1. OpenPose ────┴──► 2. Preprocessing ──► 3. Scaling ──┘
                                                               │
     6. Parameters ◄── 5. Gait Event ◄── 4. Correction ◄──────┘
```

1. **OpenPose** — Runs `OpenPoseDemo.exe` via subprocess with the `BODY_25` model, one person, JSON keypoint output (optional overlay video `*_openpose.avi`).
2. **Preprocessing** — Coordinate signal cleaning:
   - Confidence filtering (threshold 0.3; ankles and mid-hip 0.4)
   - Gap filling with linear interpolation (max 10 frames, backward/forward fill fallback)
   - Median filter (kernel 5) to remove spikes
   - Savitzky–Golay filter (window 11, polyorder 2) to preserve peaks and valleys
   - Butterworth low-pass filter, order 2, 2.5 Hz cutoff, for parameter analysis
   - Resampling to 30 fps
3. **Scaling** — Pixel-to-meter calibration by marking two reference points on a frame and entering their real-world distance (e.g. body height); the scale factor is then applied to all coordinates.
4. **Correction** — Enforces left/right leg label consistency: per-frame manual swap (shortcut `S`) or *Auto Correct Swaps* for the whole video.
5. **Gait Event** — Automatic detection:
   - **Heel Strike (HS)** = peak of the ankle position relative to the hip (`scipy.find_peaks`)
   - **Toe Off (TO)** = minimum point between two consecutive HS events
   - Stance/swing phase labeling, gait-cycle construction (valid duration 0.6–2.0 s), plus biomechanical validation
6. **Parameters** — Computes spatial, temporal, spatiotemporal, and joint kinematics parameters, then saves them as JSON/CSV/Excel.

---

## Requirements

- **Windows 10/11** — the recording audio cue uses `winsound`, and OpenPose is executed as an `.exe`.
- **Python 3.9 – 3.11** (tested on 3.11.8).
- **OpenPose** (Windows portable/demo) with the `BODY_25` model.
- A camera/webcam (optional, only for live recording).

Python dependencies: `numpy`, `scipy`, `opencv-python`, `PyQt5`, `matplotlib`, `pyyaml`, `pandas`, `openpyxl`.

---

## Installation

```bat
git clone https://github.com/Nashhansyah/Gait-Analysis-System.git
cd Gait-Analysis-System

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### OpenPose configuration

Set your OpenPose installation paths in `config/openpose_config.yaml`:

```yaml
openpose:
  executable_path: "C:/openpose/bin/OpenPoseDemo.exe"
  model_folder: "C:/openpose/models"
  model_pose: "BODY_25"
```

---

## Running the Application

```bat
python src/gui/main.py
```

---

## Usage Guide

### 1. Homepage — create a project

1. Click **New Subject** and enter the subject name/ID.
2. Click **Add New Session** on that subject.
3. Choose the video source: **Browse** a file, or record directly (webcam / phone IP camera).
4. The video is copied into the project folder and its metadata (fps, resolution, frame count, duration) is saved automatically.

### 2. Analysis — run the pipeline

Select a session and follow the 6-step wizard. Each completed step advances to the next one automatically.

- **OpenPose** — run pose extraction; an overlay video option is available.
- **Preprocessing** — run the filters; a before/after signal comparison plot is provided.
- **Scaling** — mark two reference points and enter the real-world distance (meters).
- **Correction** — inspect frames with swapped leg labels, then use swap or auto-correct.
- **Gait Event** — run *Auto Detect Events (HS/TO)*, then fix any incorrect events manually.
- **Parameters** — click **Compute Parameters** to calculate all parameters and joint kinematics.

### 3. Report — view and export results

- Select a project/session and load the report.
- The video plays alongside the gait-phase plot (STANCE/SWING per side) with a frame indicator.
- Tables are available for the parameter summary, per-cycle details, and joint angles.
- Use **Export CSV & All** / **Export Excel (.xlsx)** to save the report.

### 4. Monitoring — trends across sessions

Select a subject and click **Analyze** to see trend charts for walking speed, cadence, stride length, step length, and left/right stance-swing ratios across sessions.

> **Recording tips:** the subject walks perpendicular to the camera (sagittal view), the whole body is visible, only one person is in frame, the camera is static, and lighting is adequate so keypoint confidence stays high.

---

## Computed Parameters

**Per step**

| Parameter | Unit | Description |
|---|---|---|
| `step_time` | s | Duration of one step |
| `step_length` | m | Horizontal distance between foot positions |
| `step_velocity` | m/s | Step velocity |

**Per cycle**

| Parameter | Unit | Description |
|---|---|---|
| `cycle_time` | s | Duration of one gait cycle |
| `stride_length` | m | Stride length |
| `walking_speed` | m/s | Walking speed |
| `cadence` | steps/min | Cadence |
| `stance_ratio` / `swing_ratio` | % | Stance/swing phase proportion (overall and per side) |

**Kinematics**

**Hip**, **knee**, and **ankle** angles for both left and right sides, each with `mean`, `min`, `max`, `std`, and **ROM** (range of motion) in degrees.

Summary statistics produced for every parameter: `mean`, `std`, `min`, `max`, `median`.

---

## Configuration

| File | Contents |
|---|---|
| `config/openpose_config.yaml` | OpenPose paths, pose model (`BODY_25`), joint indices, execution options |
| `config/signal_config.yaml` | Confidence thresholds, gap filling, median/Savitzky–Golay/Butterworth filters, resampling |
| `config/gait_config.yaml` | Cycle duration limits, stance/swing ratios, HS/TO detection parameters, biomechanical constraints |

---

## Repository Structure

```
Gait_Analysis/
├── src/
│   ├── gui/                    # PyQt5 interface
│   │   ├── main.py             # Application entry point
│   │   ├── sidebar.py          # Homepage/Analysis/Report/Monitoring navigation
│   │   ├── styles.py           # Theme & styles
│   │   ├── dashboard_tab.py    # Subject & session management
│   │   ├── analysis_tab.py     # 6-step pipeline wizard
│   │   ├── openpose_tab.py     # Step 1
│   │   ├── preprocessing_tab.py# Step 2
│   │   ├── scaling_tab.py      # Step 3
│   │   ├── correction_tab.py   # Step 4
│   │   ├── gait_event_tab.py   # Step 5
│   │   ├── gait_param_tab.py   # Step 6
│   │   ├── report_tab.py       # Reporting & export
│   │   ├── rehabilitation_tab.py# Monitoring trends
│   │   ├── project_dialogs.py  # Subject/session/video dialogs
│   │   └── camera_recording_dialog.py # Webcam/IP camera recording
│   ├── project_input/          # Project structure & metadata management
│   ├── openpose/               # OpenPose execution wrapper
│   ├── signal_processing/      # Signal filtering & smoothing
│   ├── scaling/                # Pixel → meter conversion
│   ├── correction_legid/       # Left/right leg label correction
│   ├── gait_event/             # HS/TO detection & gait cycles
│   ├── gait_parameter/         # Parameters & kinematics + export
│   └── rehabilitation/         # Cross-session data aggregation
├── config/                     # YAML configuration files
├── data/                       # Project data (auto-generated, not committed)
├── docs/images/                # Screenshots & demo GIF for the README
├── requirements.txt
├── CITATION.cff
├── LICENSE
├── README.md                   # Documentation (English, default)
└── README.id.md                # Documentation (Bahasa Indonesia)
```

---

## Output Data

All results are stored in the `data/` folder (created automatically) using the naming pattern `{subject}_{session}` — the `default` session name is omitted from file names:

```
data/
├── metadata/{subject}.json                      # Video info + per-session pipeline status
├── input_video/{subject}/{session}/video_raw.mp4
├── openpose_raw/{subject}/{session}/*_keypoints.json
├── openpose_frames/{subject}/{session}/         # High-res frames with skeleton
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

The Excel workbook contains 5 sheets:

1. **Ringkasan Parameter** (spatiotemporal summary)
2. **Siklus Gait** (gait cycles)
3. **Detail Langkah** (per-step details)
4. **Ringkasan Sudut Sendi** (kinematics summary)
5. **Deret Waktu Sudut** (angle time series per frame with video frame images)

---

## Repository Notes

The `data/`, `.venv/`, and `__pycache__/` folders, as well as design assets (`*.drawio`, `*.docx`, `*.png`, `prd.md`), are **not committed** (see `.gitignore`). The repository only contains code, configuration, and documentation. Measurement data stays locally on your machine.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| OpenPose fails to run | Check `executable_path` and `model_folder` in `config/openpose_config.yaml` |
| Many `NaN` keypoints | Improve lighting/contrast and make sure the full body is visible; lower the confidence thresholds in `signal_config.yaml` |
| HS/TO detection is off | Correct manually in the Gait Event step; adjust `min_peak_distance`, `min_prominence`, or cycle duration limits in `gait_config.yaml` |
| Unrealistic lengths/speeds | Redo the calibration in the Scaling step (two reference points + real-world distance) |
| No audio during recording | The audio cue is Windows-only (`winsound`) |
| All cycles marked invalid | Parameters are still computed using all cycles with a warning; check video quality and detected events |

---

## Citation

If you use this software in research or a clinical project, please cite it using the metadata in [CITATION.cff](CITATION.cff).

---

## License

Released under the [MIT License](LICENSE).

© 2026 Gait Analysis Markerless
