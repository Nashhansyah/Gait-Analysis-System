"""
Report Tab Widget
=================
Displays analysis results with video, visualizations, and data tables.
"""

import os
import json
import cv2
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSplitter,
    QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QComboBox, QSizePolicy,
    QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from .styles import ModernStyle


class VideoPlayer(QWidget):
    """Widget for playing OpenPose output video."""
    
    # Signal emitted when current frame changes
    frame_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.video_capture = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fps = 30
        self.current_frame = 0
        self.total_frames = 0
        self.playing = False
        
        # Auto-crop to remove black bars
        self.crop_region = None  # (x, y, w, h) or None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setStyleSheet(f"""
            background-color: #000;
            border-radius: 8px;
        """)
        self.video_label.setText("No video loaded")
        layout.addWidget(self.video_label)
        
        # Controls
        controls = QHBoxLayout()
        
        self.play_btn = QPushButton("Play")
        self.play_btn.setStyleSheet(f"background-color: {ModernStyle.SUCCESS}; color: #000; padding: 8px 20px;")
        self.play_btn.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(f"background-color: {ModernStyle.ERROR}; padding: 8px 20px;")
        self.stop_btn.clicked.connect(self.stop)
        controls.addWidget(self.stop_btn)
        
        controls.addStretch()
        
        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setStyleSheet(f"color: {ModernStyle.TEXT};")
        controls.addWidget(self.frame_label)
        
        layout.addLayout(controls)
        
    def load_video(self, video_path: str):
        """Load a video file."""
        if not os.path.exists(video_path):
            return False
        
        self.stop()
        
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            return False
        
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        
        # Detect crop region from first frame to remove black bars
        ret, first_frame = self.video_capture.read()
        if ret:
            self.crop_region = self._detect_crop_region(first_frame)
        else:
            self.crop_region = None
        
        self.show_frame(0)
        return True
    
    def _detect_crop_region(self, frame):
        """Detect black bars and return crop region (x, y, w, h).
        
        Returns None if no significant black bars detected.
        """
        if frame is None:
            return None
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # Threshold to detect black pixels (threshold = 15 for near-black)
        threshold = 15
        
        # Find non-black region by checking mean brightness per row/column
        row_means = gray.mean(axis=1)
        col_means = gray.mean(axis=0)
        
        content_rows = row_means > threshold
        content_cols = col_means > threshold
        
        if not content_rows.any() or not content_cols.any():
            return None
        
        # Find boundaries
        y_start = int(content_rows.argmax())
        y_end = int(h - content_rows[::-1].argmax())
        x_start = int(content_cols.argmax())
        x_end = int(w - content_cols[::-1].argmax())
        
        crop_w = x_end - x_start
        crop_h = y_end - y_start
        
        # Only apply crop if black bars > 5% on any side
        min_crop = 0.05
        if (x_start / w > min_crop or (w - x_end) / w > min_crop or
            y_start / h > min_crop or (h - y_end) / h > min_crop):
            return (x_start, y_start, crop_w, crop_h)
        
        return None
        
    def show_frame(self, frame_idx: int):
        """Display a specific frame."""
        if self.video_capture is None:
            return
        
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.video_capture.read()
        
        if ret:
            # Apply auto-crop if detected
            if self.crop_region:
                x, y, w, h = self.crop_region
                frame = frame[y:y+h, x:x+w]
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit label
            h, w = frame_rgb.shape[:2]
            label_w = self.video_label.width()
            label_h = self.video_label.height()
            
            scale = min(label_w / w, label_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            if new_w > 0 and new_h > 0:
                frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
                
                # Convert to QImage
                bytes_per_line = 3 * new_w
                q_image = QImage(frame_resized.data, new_w, new_h, 
                                bytes_per_line, QImage.Format_RGB888)
                
                self.video_label.setPixmap(QPixmap.fromImage(q_image))
        
        self.current_frame = frame_idx
        self.frame_label.setText(f"Frame: {frame_idx} / {self.total_frames - 1}")
        
        # Emit signal to update frame indicator in phase visualization
        self.frame_changed.emit(frame_idx)
        
    def update_frame(self):
        """Update to next frame (called by timer)."""
        self.current_frame += 1
        
        # Loop back to start
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
        
        self.show_frame(self.current_frame)
        
    def toggle_play(self):
        """Toggle play/pause."""
        if self.playing:
            self.pause()
        else:
            self.play()
            
    def play(self):
        """Start playback."""
        if self.video_capture is None:
            return
        
        self.playing = True
        self.play_btn.setText("Pause")
        interval = int(1000 / self.fps)
        self.timer.start(interval)
        
    def pause(self):
        """Pause playback."""
        self.playing = False
        self.play_btn.setText("Play")
        self.timer.stop()
        
    def stop(self):
        """Stop and reset playback."""
        self.pause()
        self.current_frame = 0
        if self.video_capture:
            self.show_frame(0)
            
    def closeEvent(self, event):
        """Clean up on close."""
        self.stop()
        if self.video_capture:
            self.video_capture.release()
        super().closeEvent(event)


class ReportTab(QWidget):
    """Report tab showing video, visualizations, and results table."""
    
    def __init__(self, project_manager, param_extractor):
        super().__init__()
        self.project_manager = project_manager
        self.param_extractor = param_extractor
        self.loaded_subject_id = None
        self.loaded_session_id = None
        self.events_data = None
        self.gait_params = None
        self.frame_indicator_line = None  # Reference to vertical line indicator
        self.min_frame = 0
        self.max_frame = 0
        self.setup_ui()
        
    def setup_ui(self):
        # Outer layout containing scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title and controls
        header = QHBoxLayout()
        header.setSpacing(15)
        
        title = QLabel("Analysis Report")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #000000;
        """)
        header.addWidget(title)
        
        self.project_info_label = QLabel("No project loaded")
        self.project_info_label.setStyleSheet("""
            font-size: 13px;
            color: #444444;
            background-color: #E8ECEF;
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: bold;
        """)
        header.addWidget(self.project_info_label)
        
        header.addStretch()
        
        self.load_btn = QPushButton("📂 Load Report")
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: #FFFFFF;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #16A085;
            }}
        """)
        self.load_btn.clicked.connect(self.open_load_dialog)
        header.addWidget(self.load_btn)
        
        self.export_btn = QPushButton("Export CSV & All")
        self.export_btn.setStyleSheet(f"background-color: {ModernStyle.SUCCESS}; color: #000; padding: 10px 20px; font-weight: bold;")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        header.addWidget(self.export_btn)
        
        self.export_excel_btn = QPushButton("Export Excel (.xlsx)")
        self.export_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D6F42;
                color: #FFFFFF;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #155231;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
                color: #FFFFFF;
            }
        """)
        self.export_excel_btn.clicked.connect(self.export_excel)
        self.export_excel_btn.setEnabled(False)
        header.addWidget(self.export_excel_btn)
        
        layout.addLayout(header)
        
        # --- MAIN TWO-COLUMN CONTAINER ---
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)
        
        # Left Side Column: Video Player + Gait Phase Visualization (directly under video)
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Video player
        video_group = QGroupBox("OpenPose Video Player")
        video_layout = QVBoxLayout(video_group)
        self.video_player = VideoPlayer()
        video_layout.addWidget(self.video_player)
        left_layout.addWidget(video_group)
        
        # Gait Phase Diagram directly under video
        phase_group = QGroupBox("Visualisasi Fase Gait (Stance, Swing, & Double Support)")
        phase_layout = QVBoxLayout(phase_group)
        self.phase_canvas = FigureCanvas(Figure(figsize=(7, 3.5), facecolor='white'))
        self.phase_canvas.setMinimumHeight(280)
        self.phase_axes = self.phase_canvas.figure.add_subplot(111)
        phase_layout.addWidget(self.phase_canvas)
        left_layout.addWidget(phase_group)
        
        main_layout.addWidget(left_column, stretch=1)
        
        # Right Side Column: Parameter Tables
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Summary parameters table
        summary_group = QGroupBox("Ringkasan Parameter Gait")
        summary_layout = QVBoxLayout(summary_group)
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Parameter", "Nilai"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setMinimumHeight(180)
        summary_layout.addWidget(self.summary_table)
        right_layout.addWidget(summary_group)
        
        # Detailed tables group in tabs
        detail_tabs = QTabWidget()
        
        self.cycle_table = QTableWidget()
        self.cycle_table.setColumnCount(6)
        self.cycle_table.setHorizontalHeaderLabels(["Cycle", "Side", "Duration (s)", "Stance %", "Swing %", "Speed (m/s)"])
        self.cycle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cycle_table.verticalHeader().setVisible(False)
        detail_tabs.addTab(self.cycle_table, "Siklus Gait")
        
        self.kinematic_table = QTableWidget()
        self.kinematic_table.setColumnCount(6)
        self.kinematic_table.setHorizontalHeaderLabels(["Sudut Sendi", "Kaki", "Mean", "Min", "Max", "ROM"])
        self.kinematic_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.kinematic_table.verticalHeader().setVisible(False)
        detail_tabs.addTab(self.kinematic_table, "Sudut Sendi (Kinematik)")
        
        right_layout.addWidget(detail_tabs)
        main_layout.addWidget(right_column, stretch=1)
        
        layout.addWidget(main_container)
        
        # Connect video player frame changes to update frame indicator
        self.video_player.frame_changed.connect(self.update_frame_indicator)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.status_label)
        
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)
        
    def open_load_dialog(self):
        """Open modal window for selecting subject and session to load in ReportTab."""
        from PyQt5.QtWidgets import QDialog
        from .project_dialogs import LoadReportProjectDialog
        
        dialog = LoadReportProjectDialog(
            self.project_manager,
            current_subject=self.loaded_subject_id,
            current_session=self.loaded_session_id,
            parent=self
        )
        if dialog.exec_() == QDialog.Accepted:
            subject_id, session_id = dialog.get_selected_project()
            if subject_id and session_id:
                self.load_report_for_project(subject_id, session_id)
                
    def load_report(self):
        """Backward compatibility / load button trigger."""
        self.open_load_dialog()

    def load_report_for_project(self, subject_id: str, session_id: str):
        """Load report data for specific subject and session independently."""
        self.loaded_subject_id = subject_id
        self.loaded_session_id = session_id
        
        # Update header project info
        self.project_info_label.setText(f"📁 Subject: <b>{subject_id}</b> &nbsp;|&nbsp; Session: <b>{session_id}</b>")
        
        # Use project manager's session-aware path for OpenPose output
        openpose_folder = self.project_manager.get_openpose_output_path(subject_id, session_id)
        
        video_path = None
        
        # Priority 1: Find video with *_openpose.avi pattern (generated by run_openpose)
        if os.path.exists(openpose_folder):
            for f in os.listdir(openpose_folder):
                if f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_folder, f)
                    break
        
        # Priority 2: Check for other common OpenPose output video names
        if not video_path and os.path.exists(openpose_folder):
            possible_names = [
                "output_video.avi", "output.avi", "rendered.avi",
                "video_output.avi", "keypoints_video.avi"
            ]
            
            for name in possible_names:
                path = os.path.join(openpose_folder, name)
                if os.path.exists(path):
                    video_path = path
                    break
        
        # Priority 3: Try to find any other video file in openpose folder
        if not video_path and os.path.exists(openpose_folder):
            for f in os.listdir(openpose_folder):
                if f.endswith(('.avi', '.mp4')) and not f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_folder, f)
                    break
        
        # Fallback: Use original input video
        if not video_path:
            video_path = self.project_manager.get_video_path(subject_id, session_id)
        
        if video_path and os.path.exists(video_path):
            self.video_player.load_video(video_path)
        
        # Load gait events using session-aware path
        events_path = self.project_manager.find_output_file(subject_id, "gait_events", session_id)
        
        if events_path and os.path.exists(events_path):
            with open(events_path, 'r', encoding='utf-8') as f:
                self.events_data = json.load(f)
            self.plot_gait_phases()
        else:
            self.events_data = None
            self.phase_axes.clear()
            self.phase_canvas.draw()
        
        # Load parameters using session-aware path
        params_path = self.project_manager.find_output_file(subject_id, "gait_parameters_summary", session_id)
        
        if params_path and os.path.exists(params_path):
            self.load_parameters(subject_id, session_id)
            self.export_btn.setEnabled(True)
            self.export_excel_btn.setEnabled(True)
        else:
            self.summary_table.setRowCount(0)
            self.cycle_table.setRowCount(0)
            self.kinematic_table.setRowCount(0)
            self.export_btn.setEnabled(False)
            self.export_excel_btn.setEnabled(False)
        
        session_str = f" (Session: {session_id})" if session_id and session_id != "default" else ""
        self.status_label.setText(f"✓ Report loaded for {subject_id}{session_str}")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")
        
    def plot_gait_phases(self):
        """Plot stance/swing phase visualization using phase_labels.
        
        Uses phase_labels for full coverage including phases outside of
        complete gait cycles (e.g., swing at recording start).
        """
        self.phase_axes.clear()
        
        if not self.events_data:
            return
        
        # Prioritize phase_labels over gait_cycles
        phase_labels = self.events_data.get("phase_labels", {})
        cycles = self.events_data.get("gait_cycles", [])
        
        # Colors
        stance_color = '#2F4F4F'  # Dark teal for STANCE
        swing_color = '#87CEEB'   # Light sky blue for SWING
        double_support_color = '#FF6347'  # Tomato red for Double Support
        
        # Row positions (3 rows: Kiri, Double Support, Kanan)
        row_height = 0.30
        y_kiri = 0.78   # Top row (Left/Kiri)
        y_ds = 0.48     # Middle row (Double Support)
        y_kanan = 0.18  # Bottom row (Right/Kanan)
        
        if phase_labels:
            # Use phase_labels for full coverage
            self._plot_from_phase_labels(phase_labels, y_kiri, y_kanan, y_ds,
                                          row_height, stance_color, swing_color, 
                                          double_support_color)
        elif cycles:
            # Fallback to cycle-based plotting
            self._plot_from_cycles(cycles, y_kiri, y_kanan, 
                                   row_height, stance_color, swing_color)
        else:
            self.phase_axes.text(0.5, 0.5, "Tidak ada data fase gait", 
                                ha='center', va='center', fontsize=12, color='gray')
            self.phase_canvas.draw()
            return
        
        # Add current frame indicator line
        current_frame = self.video_player.current_frame if self.video_player else 0
        current_frame = max(self.min_frame, min(current_frame, self.max_frame))
        self.frame_indicator_line = self.phase_axes.axvline(
            x=current_frame, color='red', linewidth=2, linestyle='-'
        )
        
        # Add legend patches for Stance, Swing, Double Support
        import matplotlib.patches as mpatches
        stance_patch = mpatches.Patch(color=stance_color, label='STANCE (Tumpuan)')
        swing_patch = mpatches.Patch(color=swing_color, label='SWING (Ayunan)')
        ds_patch = mpatches.Patch(color=double_support_color, label='Double Support (DS)')
        self.phase_axes.legend(handles=[stance_patch, swing_patch, ds_patch], loc='upper right', fontsize=8, ncol=3, framealpha=0.9)
        
        # Styling
        self.phase_axes.set_xlim(self.min_frame, self.max_frame)
        self.phase_axes.set_ylim(-0.05, 1.05)
        self.phase_axes.set_yticks([y_kanan, y_ds, y_kiri])
        self.phase_axes.set_yticklabels(['Kaki Kanan', 'Double Support', 'Kaki Kiri'], fontsize=10, fontweight='bold')
        self.phase_axes.set_xlabel('Frame Number', fontsize=10, fontweight='bold')
        
        self.phase_axes.set_facecolor('white')
        self.phase_axes.grid(True, axis='x', linestyle='--', alpha=0.5)
        self.phase_axes.spines['top'].set_visible(False)
        self.phase_axes.spines['right'].set_visible(False)
        self.phase_axes.spines['left'].set_color('#cccccc')
        self.phase_axes.spines['bottom'].set_color('#cccccc')
        self.phase_axes.tick_params(axis='x', labelsize=9)
        
        self.phase_canvas.figure.tight_layout()
        self.phase_canvas.draw()
    
    def _plot_from_phase_labels(self, phase_labels, y_kiri, y_kanan, y_ds,
                                 row_height, stance_color, swing_color, 
                                 double_support_color):
        """Plot phases from phase_labels dictionary including double support."""
        # Convert string keys to int if needed
        if phase_labels:
            first_key = next(iter(phase_labels))
            if isinstance(first_key, str):
                phase_labels = {int(k): v for k, v in phase_labels.items()}
        
        if not phase_labels:
            return
        
        frames = sorted(phase_labels.keys())
        
        # Find actual range where phases are detected (non-null)
        detected_frames = []
        for f in frames:
            left_phase = phase_labels.get(f, {}).get("left")
            right_phase = phase_labels.get(f, {}).get("right")
            if left_phase is not None or right_phase is not None:
                detected_frames.append(f)
        
        if detected_frames:
            self.min_frame = min(detected_frames)
            self.max_frame = max(detected_frames)
        else:
            self.min_frame = min(frames)
            self.max_frame = max(frames)
        
        def plot_side_phases(side: str, y_pos: float):
            """Plot contiguous phase runs for one side."""
            runs = []
            current_phase = None
            start_frame = None
            
            for frame in frames:
                phase = phase_labels.get(frame, {}).get(side)
                
                if phase != current_phase:
                    if current_phase is not None and start_frame is not None:
                        runs.append((start_frame, frame - 1, current_phase))
                    current_phase = phase
                    start_frame = frame
            
            if current_phase is not None and start_frame is not None:
                runs.append((start_frame, frames[-1], current_phase))
            
            for start_f, end_f, phase in runs:
                if phase is None:
                    continue
                
                width = end_f - start_f + 1
                color = stance_color if phase == "stance" else swing_color
                text_color = 'white' if phase == "stance" else 'black'
                
                self.phase_axes.barh(y_pos, width, left=start_f, 
                                    height=row_height, color=color,
                                    edgecolor='white', linewidth=0.5)
                
                if width > 12:
                    self.phase_axes.text(start_f + width/2, y_pos, phase.upper(), 
                                        ha='center', va='center', color=text_color, 
                                        fontsize=7, fontweight='bold')
        
        # Plot left and right sides
        plot_side_phases("left", y_kiri)
        plot_side_phases("right", y_kanan)
        
        # Plot Double Support
        # Double support occurs when:
        # 1. Both legs are in stance phase, OR
        # 2. One leg is in stance but the other leg is not detected (null)
        ds_runs = []
        current_ds = False
        start_frame = None
        
        for frame in frames:
            left_phase = phase_labels.get(frame, {}).get("left")
            right_phase = phase_labels.get(frame, {}).get("right")
            
            # Check for double support condition
            is_double_support = False
            if left_phase == "stance" and right_phase == "stance":
                # Both legs in stance
                is_double_support = True
            elif left_phase == "stance" and right_phase is None:
                # Left stance, right not detected
                is_double_support = True
            elif right_phase == "stance" and left_phase is None:
                # Right stance, left not detected
                is_double_support = True
            
            if is_double_support != current_ds:
                if current_ds and start_frame is not None:
                    ds_runs.append((start_frame, frame - 1))
                current_ds = is_double_support
                start_frame = frame if is_double_support else None
        
        # Handle last run
        if current_ds and start_frame is not None:
            ds_runs.append((start_frame, frames[-1]))
        
        # Draw double support bars
        for start_f, end_f in ds_runs:
            width = end_f - start_f + 1
            self.phase_axes.barh(y_ds, width, left=start_f, 
                                height=row_height, color=double_support_color,
                                edgecolor='white', linewidth=0.5, alpha=0.85)
            
            if width > 15:
                self.phase_axes.text(start_f + width/2, y_ds, 'DS', 
                                    ha='center', va='center', color='white', 
                                    fontsize=7, fontweight='bold')
    
    def _plot_from_cycles(self, cycles, y_kiri, y_kanan, 
                          row_height, stance_color, swing_color):
        """Fallback: Plot phases from gait_cycles."""
        left_cycles = [c for c in cycles if c.get("side", "").lower() == "left"]
        right_cycles = [c for c in cycles if c.get("side", "").lower() == "right"]
        
        all_frames = []
        for c in cycles:
            all_frames.append(c.get("start_frame", 0))
            all_frames.append(c.get("end_frame", 1))
        
        if not all_frames:
            return
        
        self.min_frame = min(all_frames)
        self.max_frame = max(all_frames)
        
        def plot_row(cycles_list, y_pos):
            for cycle in cycles_list:
                start_frame = cycle.get("start_frame", 0)
                end_frame = cycle.get("end_frame", start_frame + 1)
                
                toe_off_data = cycle.get("toe_off", {})
                toe_off_frame = toe_off_data.get("frame") if isinstance(toe_off_data, dict) else None
                
                if toe_off_frame is None:
                    stance_ratio = cycle.get("stance_ratio", 0.6)
                    if stance_ratio <= 0 or stance_ratio >= 1:
                        stance_ratio = 0.6
                    frame_duration = end_frame - start_frame
                    toe_off_frame = start_frame + int(frame_duration * stance_ratio)
                
                stance_frames = toe_off_frame - start_frame
                swing_frames = end_frame - toe_off_frame
                
                self.phase_axes.barh(y_pos, stance_frames, left=start_frame, 
                                    height=row_height, color=stance_color,
                                    edgecolor='white', linewidth=0.5)
                if stance_frames > 8:
                    self.phase_axes.text(start_frame + stance_frames/2, y_pos, 'STANCE', 
                                        ha='center', va='center', color='white', 
                                        fontsize=7, fontweight='bold')
                
                self.phase_axes.barh(y_pos, swing_frames, left=toe_off_frame, 
                                    height=row_height, color=swing_color, 
                                    edgecolor='white', linewidth=0.5)
                if swing_frames > 8:
                    self.phase_axes.text(toe_off_frame + swing_frames/2, y_pos, 'SWING', 
                                        ha='center', va='center', color='black', 
                                        fontsize=7, fontweight='bold')
        
        if left_cycles:
            plot_row(left_cycles, y_kiri)
        if right_cycles:
            plot_row(right_cycles, y_kanan)
    
    def update_frame_indicator(self, frame_idx: int):
        """Update the vertical frame indicator line position.
        
        Called when video player frame changes to sync the red line
        with current playback position.
        """
        if self.frame_indicator_line is None:
            return
        
        # Clamp frame to valid range
        frame = max(self.min_frame, min(frame_idx, self.max_frame))
        
        # Update line position
        self.frame_indicator_line.set_xdata([frame, frame])
        
        # Redraw only the canvas (efficient update)
        self.phase_canvas.draw_idle()
        
    def load_parameters(self, subject_id: str, session_id: str = None):
        """Load and display gait parameters."""
        target_session = session_id or self.loaded_session_id or self.project_manager.current_session_id
        
        # Use session-aware paths via project_manager
        events_path = self.project_manager.find_output_file(
            subject_id, "gait_events", target_session
        )
        
        # Load scaled pose data (MUST use scaled_pose for meter-based calculations)
        pose_path = self.project_manager.find_output_file(
            subject_id, "scaled_pose", target_session
        )
        
        if events_path and os.path.exists(events_path):
            success, msg, events, cycles = self.param_extractor.load_events(events_path)
            if success and pose_path and os.path.exists(pose_path):
                success, msg, pose_data = self.param_extractor.load_pose_data(pose_path)
                if success:
                    self.param_extractor.compute_all_parameters(events, cycles, pose_data)
                    self.update_summary_table()
                    self.update_cycle_table()
                    self.update_kinematic_table()
                    
    def update_summary_table(self):
        """Update the summary parameters table."""
        rows = self.param_extractor.get_parameter_table()
        
        self.summary_table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(row.get("parameter", "")))
            self.summary_table.setItem(i, 1, QTableWidgetItem(row.get("value", "")))
            
    def update_cycle_table(self):
        """Update the cycle table."""
        cycles = self.param_extractor.cycle_data
        
        self.cycle_table.setRowCount(len(cycles))
        
        for i, cycle in enumerate(cycles):
            # Create table items
            cycle_id_item = QTableWidgetItem(str(cycle.get("cycle_id", i) + 1))  # 1-based
            side_item = QTableWidgetItem(cycle.get("side", "").capitalize())
            duration_item = QTableWidgetItem(f"{cycle.get('cycle_time', 0):.3f}")
            stance_item = QTableWidgetItem(f"{cycle.get('stance_ratio', 0)*100:.1f}%")
            swing_item = QTableWidgetItem(f"{cycle.get('swing_ratio', 0)*100:.1f}%")
            speed_item = QTableWidgetItem(f"{cycle.get('walking_speed', 0):.3f}")
            
            items = [cycle_id_item, side_item, duration_item, stance_item, swing_item, speed_item]
            
            # Highlight invalid cycles with red background
            if not cycle.get("valid", True):
                from PyQt5.QtGui import QColor, QBrush
                red_bg = QBrush(QColor(255, 200, 200))  # Light red background
                red_text = QColor(139, 0, 0)  # Dark red text
                for item in items:
                    item.setBackground(red_bg)
                    item.setForeground(QBrush(red_text))
                    
                # Add tooltip with reason
                reason = cycle.get("invalid_reason", "Outside normal duration range")
                for item in items:
                    item.setToolTip(f"⚠️ Invalid: {reason}")
            
            # Set items in table
            self.cycle_table.setItem(i, 0, cycle_id_item)
            self.cycle_table.setItem(i, 1, side_item)
            self.cycle_table.setItem(i, 2, duration_item)
            self.cycle_table.setItem(i, 3, stance_item)
            self.cycle_table.setItem(i, 4, swing_item)
            self.cycle_table.setItem(i, 5, speed_item)

    def update_kinematic_table(self):
        """Update joint kinematics table (Hip, Knee, Ankle angles)."""
        rows = self.param_extractor.get_kinematic_table()
        self.kinematic_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.kinematic_table.setItem(i, 0, QTableWidgetItem(row.get("joint", "")))
            self.kinematic_table.setItem(i, 1, QTableWidgetItem(row.get("side", "")))
            self.kinematic_table.setItem(i, 2, QTableWidgetItem(row.get("mean", "")))
            self.kinematic_table.setItem(i, 3, QTableWidgetItem(row.get("min", "")))
            self.kinematic_table.setItem(i, 4, QTableWidgetItem(row.get("max", "")))
            self.kinematic_table.setItem(i, 5, QTableWidgetItem(row.get("rom", "")))
            
    def export_report(self):
        """Export all parameters to CSV and Excel."""
        subject_id = self.loaded_subject_id
        session_id = self.loaded_session_id
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please load a report first.")
            return
        
        # Get video path for embedding frame thumbnails
        openpose_folder = self.project_manager.get_openpose_output_path(subject_id, session_id)
        video_path = None
        if os.path.exists(openpose_folder):
            for f in os.listdir(openpose_folder):
                if f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_folder, f)
                    break
        if not video_path:
            video_path = self.project_manager.get_video_path(subject_id, session_id)
        
        output_dir = self.project_manager.get_gait_parameters_output_dir(subject_id, session_id)
        
        paths = self.param_extractor.export_csv(output_dir, subject_id, video_path=video_path, session_id=session_id)
        
        QMessageBox.information(
            self, "Export Complete",
            f"All analysis reports exported to:\n{output_dir}\n\nIncluded: CSV files and formatted Excel file (.xlsx)"
        )

    def export_excel(self):
        """Export parameters explicitly to Excel report file."""
        subject_id = self.loaded_subject_id
        session_id = self.loaded_session_id
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please load a report first.")
            return
        
        output_dir = self.project_manager.get_gait_parameters_output_dir(subject_id, session_id)
        
        # Get video path for embedding frame thumbnails
        openpose_folder = self.project_manager.get_openpose_output_path(subject_id, session_id)
        video_path = None
        if os.path.exists(openpose_folder):
            for f in os.listdir(openpose_folder):
                if f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_folder, f)
                    break
        if not video_path:
            video_path = self.project_manager.get_video_path(subject_id, session_id)
        
        excel_path = self.param_extractor.export_excel(output_dir, subject_id, video_path, session_id=session_id)
        if os.path.exists(excel_path):
            QMessageBox.information(
                self, "Excel Export Successful",
                f"Excel Report saved to:\n{excel_path}"
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to export Excel report")
