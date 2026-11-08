"""
Gait Parameter Tab Widget
=========================
Gait parameter extraction, video playback, phase visualization, and results display.
Identical layout to Analysis Report for seamless workflow experience.
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSplitter,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QTabWidget, QSizePolicy,
    QScrollArea, QFrame, QFileDialog, QProgressDialog, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .styles import ModernStyle
from .report_tab import VideoPlayer


class GaitParameterTab(QWidget):
    """Tab for gait parameter extraction and display (Identical to ReportTab layout)."""
    
    parameters_complete = pyqtSignal()
    
    def __init__(self, extractor, project_manager, pose_extractor=None):
        super().__init__()
        self.extractor = extractor
        self.project_manager = project_manager
        self.pose_extractor = pose_extractor
        self.events_data = None
        self.gait_params = None
        self.frame_indicator_line = None
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
        
        # --- HEADER BAR ---
        header = QHBoxLayout()
        
        title = QLabel("Gait Parameters Analysis")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #000000;
        """)
        header.addWidget(title)
        
        header.addStretch()
        
        self.compute_btn = QPushButton("Compute Parameters")
        self.compute_btn.setCursor(Qt.PointingHandCursor)
        self.compute_btn.setStyleSheet("""
            QPushButton {
                background-color: #40E0D0;
                color: #FFFFFF;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #35C4B5;
            }
        """)
        self.compute_btn.clicked.connect(self.compute_parameters)
        header.addWidget(self.compute_btn)
        
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SUCCESS};
                color: #000000;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
                color: #FFFFFF;
            }}
        """)
        self.export_btn.clicked.connect(self.export_csv)
        self.export_btn.setEnabled(False)
        header.addWidget(self.export_btn)
        
        self.export_excel_btn = QPushButton("Export Excel (.xlsx)")
        self.export_excel_btn.setCursor(Qt.PointingHandCursor)
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
        
        self.export_frames_btn = QPushButton("Simpan Foto OpenPose (High-Res)")
        self.export_frames_btn.setCursor(Qt.PointingHandCursor)
        self.export_frames_btn.setToolTip("Simpan foto per-frame hasil OpenPose dengan resolusi tinggi pada folder tersendiri")
        self.export_frames_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AC7;
                color: #FFFFFF;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
                color: #FFFFFF;
            }
        """)
        self.export_frames_btn.clicked.connect(self.export_openpose_frames)
        self.export_frames_btn.setEnabled(False)
        header.addWidget(self.export_frames_btn)
        
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
        
        # Right Side Column: Summary & Detail Tables
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Summary table
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
        
        # Detail tables tab
        detail_tabs = QTabWidget()
        
        self.cycle_table = QTableWidget()
        self.cycle_table.setColumnCount(6)
        self.cycle_table.setHorizontalHeaderLabels(["Cycle", "Side", "Duration (s)", "Stance %", "Swing %", "Speed (m/s)"])
        self.cycle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cycle_table.verticalHeader().setVisible(False)
        detail_tabs.addTab(self.cycle_table, "Siklus Gait")
        
        self.step_table = QTableWidget()
        self.step_table.setColumnCount(5)
        self.step_table.setHorizontalHeaderLabels(["Step", "Side", "Time (s)", "Length (m)", "Velocity (m/s)"])
        self.step_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.step_table.verticalHeader().setVisible(False)
        detail_tabs.addTab(self.step_table, "Detail Langkah")
        
        self.kinematic_table = QTableWidget()
        self.kinematic_table.setColumnCount(6)
        self.kinematic_table.setHorizontalHeaderLabels(["Sudut Sendi", "Kaki", "Mean", "Min", "Max", "ROM"])
        self.kinematic_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.kinematic_table.verticalHeader().setVisible(False)
        detail_tabs.addTab(self.kinematic_table, "Sudut Sendi (Kinematik)")
        
        right_layout.addWidget(detail_tabs)
        main_layout.addWidget(right_column, stretch=1)
        
        layout.addWidget(main_container)
        
        # --- FULL-WIDTH KINEMATICS WAVEFORMS GRAPH ---
        kinematic_group = QGroupBox("📈 Grafik Kinematika Sudut Sendi (Hip, Knee, Ankle)")
        kinematic_layout = QVBoxLayout(kinematic_group)
        self.kinematic_figure = Figure(figsize=(12, 4.5), facecolor='white')
        self.kinematic_canvas = FigureCanvas(self.kinematic_figure)
        self.kinematic_canvas.setMinimumHeight(340)
        kinematic_layout.addWidget(self.kinematic_canvas)
        layout.addWidget(kinematic_group)
        
        # Connect video frame indicator
        self.video_player.frame_changed.connect(self.update_frame_indicator)
        
        # --- BOTTOM STATUS LABEL ---
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.status_label)
        
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

    def showEvent(self, event):
        """Auto compute or load parameters when tab becomes visible."""
        super().showEvent(event)
        if self.project_manager.current_subject_id:
            self.compute_parameters()

    def compute_parameters(self):
        """Compute gait parameters and load identical report layout content."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "No project loaded. Please select a subject first.")
            return
        
        # Load OpenPose video
        openpose_folder = self.project_manager.get_openpose_output_path(subject_id, session_id)
        video_path = None
        
        if os.path.exists(openpose_folder):
            for f in os.listdir(openpose_folder):
                if f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_folder, f)
                    break
        
        if not video_path and os.path.exists(openpose_folder):
            possible_names = ["output_video.avi", "output.avi", "rendered.avi"]
            for name in possible_names:
                path = os.path.join(openpose_folder, name)
                if os.path.exists(path):
                    video_path = path
                    break
        
        if not video_path:
            video_path = self.project_manager.get_video_path(subject_id, session_id)
        
        if video_path and os.path.exists(video_path):
            self.video_player.load_video(video_path)
            self.export_frames_btn.setEnabled(True)
        
        # Load gait events for phase plotting
        events_path = self.project_manager.find_output_file(subject_id, "gait_events", session_id)
        if events_path and os.path.exists(events_path):
            with open(events_path, 'r') as f:
                self.events_data = json.load(f)
            self.plot_gait_phases()
            
            # Load pose data and extract parameters
            pose_path = self.project_manager.find_output_file(subject_id, "scaled_pose", session_id)
            if pose_path and os.path.exists(pose_path):
                success, msg, events, cycles = self.extractor.load_events(events_path)
                if success:
                    success, msg, pose_data = self.extractor.load_pose_data(pose_path)
                    if success:
                        self.extractor.compute_all_parameters(events, cycles, pose_data)
                        self.update_summary_table()
                        self.update_cycle_table()
                        self.update_step_table()
                        self.update_kinematic_table()
                        self.plot_kinematics_waveforms()
                        self.export_btn.setEnabled(True)
                        self.export_excel_btn.setEnabled(True)
                        self.export_frames_btn.setEnabled(True)
                        
                        # Save summary to project output folder
                        summary_path = self.project_manager.get_output_file_path(
                            subject_id, "gait_parameters_summary", ".json", session_id
                        )
                        self.extractor.save_parameters(summary_path)
                        self.project_manager.update_pipeline_status(subject_id, "gait_parameter", "completed")
                        self.parameters_complete.emit()

        session_str = f" (Session: {session_id})" if session_id and session_id != "default" else ""
        self.status_label.setText(f"✓ Gait parameters computed for {subject_id}{session_str}")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")

    def plot_gait_phases(self):
        """Plot stance/swing phase visualization matching ReportTab."""
        self.phase_axes.clear()
        
        if not self.events_data:
            return
        
        phase_labels = self.events_data.get("phase_labels", {})
        cycles = self.events_data.get("gait_cycles", [])
        
        stance_color = '#2F4F4F'
        swing_color = '#87CEEB'
        double_support_color = '#FF6347'
        
        row_height = 0.30
        y_kiri = 0.78
        y_ds = 0.48
        y_kanan = 0.18
        
        if phase_labels:
            self._plot_from_phase_labels(phase_labels, y_kiri, y_kanan, y_ds,
                                          row_height, stance_color, swing_color, 
                                          double_support_color)
        elif cycles:
            self._plot_from_cycles(cycles, y_kiri, y_kanan, row_height, stance_color, swing_color)
        else:
            self.phase_axes.text(0.5, 0.5, "No gait phase data available", 
                                ha='center', va='center', fontsize=12, color='gray')
            self.phase_canvas.draw()
            return
        
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
        """Plot contiguous phase runs for left, right, and double support."""
        if phase_labels:
            first_key = next(iter(phase_labels))
            if isinstance(first_key, str):
                phase_labels = {int(k): v for k, v in phase_labels.items()}
        
        if not phase_labels:
            return
        
        frames = sorted(phase_labels.keys())
        detected_frames = [f for f in frames if phase_labels.get(f, {}).get("left") is not None or phase_labels.get(f, {}).get("right") is not None]
        
        if detected_frames:
            self.min_frame = min(detected_frames)
            self.max_frame = max(detected_frames)
        else:
            self.min_frame = min(frames)
            self.max_frame = max(frames)
        
        def plot_side_phases(side: str, y_pos: float):
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
        
        plot_side_phases("left", y_kiri)
        plot_side_phases("right", y_kanan)
        
        ds_runs = []
        current_ds = False
        start_frame = None
        
        for frame in frames:
            left_phase = phase_labels.get(frame, {}).get("left")
            right_phase = phase_labels.get(frame, {}).get("right")
            
            is_double_support = (left_phase == "stance" and right_phase == "stance") or \
                                (left_phase == "stance" and right_phase is None) or \
                                (right_phase == "stance" and left_phase is None)
            
            if is_double_support != current_ds:
                if current_ds and start_frame is not None:
                    ds_runs.append((start_frame, frame - 1))
                current_ds = is_double_support
                start_frame = frame if is_double_support else None
        
        if current_ds and start_frame is not None:
            ds_runs.append((start_frame, frames[-1]))
        
        for start_f, end_f in ds_runs:
            width = end_f - start_f + 1
            self.phase_axes.barh(y_ds, width, left=start_f, 
                                height=row_height, color=double_support_color,
                                edgecolor='white', linewidth=0.5, alpha=0.85)
            if width > 15:
                self.phase_axes.text(start_f + width/2, y_ds, 'DS', 
                                    ha='center', va='center', color='white', 
                                    fontsize=7, fontweight='bold')

    def _plot_from_cycles(self, cycles, y_kiri, y_kanan, row_height, stance_color, swing_color):
        """Fallback: Plot phases from gait_cycles."""
        left_cycles = [c for c in cycles if c.get("side", "").lower() == "left"]
        right_cycles = [c for c in cycles if c.get("side", "").lower() == "right"]
        
        all_frames = [c.get("start_frame", 0) for c in cycles] + [c.get("end_frame", 1) for c in cycles]
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
        """Update vertical frame line indicator position synced with video playback."""
        frame = max(self.min_frame, min(frame_idx, self.max_frame))
        if self.frame_indicator_line is not None:
            self.frame_indicator_line.set_xdata([frame, frame])
            self.phase_canvas.draw_idle()
            
        if hasattr(self, 'kinematic_lines') and self.kinematic_lines:
            for line in self.kinematic_lines:
                line.set_xdata([frame, frame])
            self.kinematic_canvas.draw_idle()

    def update_summary_table(self):
        """Update summary parameters table."""
        rows = self.extractor.get_parameter_table()
        self.summary_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(row.get("parameter", "")))
            self.summary_table.setItem(i, 1, QTableWidgetItem(row.get("value", "")))

    def update_cycle_table(self):
        """Update gait cycles table."""
        cycles = self.extractor.cycle_data
        self.cycle_table.setRowCount(len(cycles))
        for i, cycle in enumerate(cycles):
            items = [
                QTableWidgetItem(str(cycle.get("cycle_id", i) + 1)),
                QTableWidgetItem(cycle.get("side", "").capitalize()),
                QTableWidgetItem(f"{cycle.get('cycle_time', 0):.3f}"),
                QTableWidgetItem(f"{cycle.get('stance_ratio', 0)*100:.1f}%"),
                QTableWidgetItem(f"{cycle.get('swing_ratio', 0)*100:.1f}%"),
                QTableWidgetItem(f"{cycle.get('walking_speed', 0):.3f}")
            ]
            if not cycle.get("valid", True):
                from PyQt5.QtGui import QColor, QBrush
                red_bg = QBrush(QColor(255, 200, 200))
                red_text = QColor(139, 0, 0)
                reason = cycle.get("invalid_reason", "Outside normal duration range")
                for item in items:
                    item.setBackground(red_bg)
                    item.setForeground(QBrush(red_text))
                    item.setToolTip(f"⚠️ Invalid: {reason}")
            
            for col, item in enumerate(items):
                self.cycle_table.setItem(i, col, item)

    def update_step_table(self):
        """Update per-step details table."""
        steps = self.extractor.step_data
        self.step_table.setRowCount(len(steps))
        for i, step in enumerate(steps):
            self.step_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.step_table.setItem(i, 1, QTableWidgetItem(step.get("side", "").capitalize()))
            self.step_table.setItem(i, 2, QTableWidgetItem(f"{step.get('step_time', 0):.3f}"))
            self.step_table.setItem(i, 3, QTableWidgetItem(f"{step.get('step_length', 0):.3f}"))
            self.step_table.setItem(i, 4, QTableWidgetItem(f"{step.get('step_velocity', 0):.3f}"))

    def update_kinematic_table(self):
        """Update joint kinematics table (Hip, Knee, Ankle angles)."""
        rows = self.extractor.get_kinematic_table()
        self.kinematic_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.kinematic_table.setItem(i, 0, QTableWidgetItem(row.get("joint", "")))
            self.kinematic_table.setItem(i, 1, QTableWidgetItem(row.get("side", "")))
            self.kinematic_table.setItem(i, 2, QTableWidgetItem(row.get("mean", "")))
            self.kinematic_table.setItem(i, 3, QTableWidgetItem(row.get("min", "")))
            self.kinematic_table.setItem(i, 4, QTableWidgetItem(row.get("max", "")))
            self.kinematic_table.setItem(i, 5, QTableWidgetItem(row.get("rom", "")))

    def plot_kinematics_waveforms(self):
        """Plot Hip, Knee, and Ankle joint angle time series."""
        self.kinematic_figure.clear()
        kinematics = self.extractor.kinematics
        if not kinematics:
            return
        
        times = kinematics.get("time", [])
        if not times:
            return
            
        r_hip = kinematics.get("right", {}).get("hip_angle", [])
        r_knee = kinematics.get("right", {}).get("knee_angle", [])
        r_ankle = kinematics.get("right", {}).get("ankle_angle", [])
        
        l_hip = kinematics.get("left", {}).get("hip_angle", [])
        l_knee = kinematics.get("left", {}).get("knee_angle", [])
        l_ankle = kinematics.get("left", {}).get("ankle_angle", [])
        
        frames = list(range(len(times)))
        
        # 3 Subplots for Hip, Knee, and Ankle angles
        ax1 = self.kinematic_figure.add_subplot(311)
        ax2 = self.kinematic_figure.add_subplot(312, sharex=ax1)
        ax3 = self.kinematic_figure.add_subplot(313, sharex=ax1)
        
        # 1. Hip Angle
        ax1.plot(frames, l_hip, 'b-', label='Panggul Kiri', linewidth=1.5)
        ax1.plot(frames, r_hip, 'r-', label='Panggul Kanan', linewidth=1.5)
        ax1.set_ylabel('Hip (°)', fontsize=8)
        ax1.legend(loc='upper right', fontsize=7)
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # 2. Knee Angle
        ax2.plot(frames, l_knee, 'b-', label='Lutut Kiri', linewidth=1.5)
        ax2.plot(frames, r_knee, 'r-', label='Lutut Kanan', linewidth=1.5)
        ax2.set_ylabel('Knee (°)', fontsize=8)
        ax2.legend(loc='upper right', fontsize=7)
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # 3. Ankle Angle
        ax3.plot(frames, l_ankle, 'b-', label='Ankle Kiri', linewidth=1.5)
        ax3.plot(frames, r_ankle, 'r-', label='Ankle Kanan', linewidth=1.5)
        ax3.set_ylabel('Ankle (°)', fontsize=8)
        ax3.set_xlabel('Frame Number', fontsize=9)
        ax3.legend(loc='upper right', fontsize=7)
        ax3.grid(True, linestyle='--', alpha=0.5)
        
        current_frame = self.video_player.current_frame if self.video_player else 0
        self.kinematic_lines = [
            ax1.axvline(x=current_frame, color='red', linewidth=1.5, linestyle='--'),
            ax2.axvline(x=current_frame, color='red', linewidth=1.5, linestyle='--'),
            ax3.axvline(x=current_frame, color='red', linewidth=1.5, linestyle='--')
        ]
        
        self.kinematic_figure.tight_layout()
        self.kinematic_canvas.draw()

    def export_csv(self):
        """Export computed parameters to CSV and Excel."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        if not subject_id:
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
        
        paths = self.extractor.export_csv(output_dir, subject_id, video_path=video_path, session_id=session_id)
        if paths:
            QMessageBox.information(self, "Export Complete", f"Data exported successfully to:\n{output_dir}\n\nFiles: CSV & Excel (.xlsx)")
            self.status_label.setText(f"✓ Exported CSV and Excel reports to {output_dir}")
            self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")
        else:
            QMessageBox.warning(self, "Error", "Failed to export data")

    def export_excel(self):
        """Export parameters explicitly to multi-sheet Excel file."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        if not subject_id:
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
        
        excel_path = self.extractor.export_excel(output_dir, subject_id, video_path, session_id=session_id)
        if os.path.exists(excel_path):
            QMessageBox.information(self, "Excel Export Successful", f"Excel Report saved to:\n{excel_path}")
            self.status_label.setText(f"✓ Exported Excel report to {os.path.basename(excel_path)}")
            self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")
        else:
            QMessageBox.warning(self, "Error", "Failed to export Excel report")

    def export_openpose_frames(self):
        """Export high-resolution per-frame OpenPose photos to a dedicated folder."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        if not subject_id:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih subjek/proyek terlebih dahulu.")
            return

        # Default dedicated output folder: data/openpose_frames/{subject_id}/{session_id}
        default_dir = self.project_manager.get_openpose_frames_output_dir(subject_id, session_id)
        
        # Ask user to choose or confirm target folder
        target_dir = QFileDialog.getExistingDirectory(
            self, 
            "Pilih Folder Penyimpanan Foto OpenPose (High-Res)", 
            default_dir
        )
        
        if not target_dir:
            return
            
        os.makedirs(target_dir, exist_ok=True)
        
        openpose_dir = self.project_manager.get_openpose_output_path(subject_id, session_id)
        raw_video_path = self.project_manager.get_video_path(subject_id, session_id)
        
        if not self.pose_extractor:
            from openpose.pose_extraction import PoseExtractor
            self.pose_extractor = PoseExtractor()
            
        # Create progress dialog
        progress = QProgressDialog("Mengekstrak foto per-frame resolusi tinggi...", "Batal", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Simpan Foto OpenPose")
        progress.show()
        
        def update_progress(current, total):
            if total > 0:
                percent = int((current / total) * 100)
                progress.setValue(percent)
                progress.setLabelText(f"Menyimpan foto per-frame: {current} / {total}...")
            QApplication.processEvents()

        success, msg, info = self.pose_extractor.export_highres_openpose_frames(
            openpose_dir=openpose_dir,
            target_dir=target_dir,
            raw_video_path=raw_video_path,
            progress_callback=update_progress
        )
        
        progress.close()
        
        if success:
            saved_count = info.get("total_frames", 0)
            res_str = info.get("resolution", "")
            out_folder = info.get("target_dir", target_dir)
            
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Ekstraksi Foto Selesai")
            msg_box.setText(f"✓ {saved_count} foto per-frame resolusi tinggi ({res_str}) berhasil disimpan!")
            msg_box.setInformativeText(f"Folder Penyimpanan:\n{out_folder}")
            
            open_btn = msg_box.addButton("Buka Folder", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Ok)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == open_btn:
                try:
                    os.startfile(out_folder)
                except Exception:
                    pass
                
            self.status_label.setText(f"✓ Berhasil menyimpan {saved_count} foto OpenPose ke {out_folder}")
            self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")
        else:
            QMessageBox.warning(self, "Gagal Menyimpan", f"Gagal mengekstrak foto per-frame: {msg}")
