"""
Correction Tab Widget
=====================
Leg ID correction with interactive slider interface.
Matches the reference design with frame slider and swap button.
"""

import os
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .styles import ModernStyle


class CorrectionTab(QWidget):
    """Tab for leg ID correction with interactive visualization."""
    
    correction_complete = pyqtSignal()
    
    def __init__(self, corrector, project_manager):
        super().__init__()
        self.corrector = corrector
        self.project_manager = project_manager
        self.data = None
        self.current_frame = 0
        self.total_frames = 0
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- LEFT PANEL: Skeleton Overlay Canvas & Slider ---
        left_group = QGroupBox("Right Leg (Green) & Left Leg (Red) Pose Visualization")
        left_layout = QVBoxLayout(left_group)
        
        # Visualization canvas
        self.canvas = FigureCanvas(Figure(figsize=(8, 5), facecolor='white'))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.axes = self.canvas.figure.add_subplot(111)
        self.axes.text(0.5, 0.5, 'Per-Frame Leg ID Visualization\n\nClick "Load Scaled Data" to display pose samples', 
                       horizontalalignment='center', verticalalignment='center', transform=self.axes.transAxes, color='#888888', fontsize=12)
        self.axes.axis('off')
        left_layout.addWidget(self.canvas, stretch=1)
        
        # Frame slider layout
        slider_layout = QHBoxLayout()
        self.slider_indicator = QLabel()
        self.slider_indicator.setFixedWidth(4)
        self.slider_indicator.setStyleSheet("background-color: #00CED1;")
        slider_layout.addWidget(self.slider_indicator)
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(100)
        self.frame_slider.setValue(0)
        self.frame_slider.valueChanged.connect(self.on_slider_changed)
        self.frame_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999;
                height: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #40E0D0;
                border: none;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #e0e0e0;
                border-radius: 5px;
            }
        """)
        slider_layout.addWidget(self.frame_slider)
        left_layout.addLayout(slider_layout)
        main_layout.addWidget(left_group, stretch=3)
        
        # --- RIGHT PANEL: Controls & Buttons ---
        right_group = QGroupBox("Leg ID Correction Panel")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(15)
        
        # Load button
        self.load_btn = QPushButton("Load Scaled Data")
        self.load_btn.setCursor(Qt.PointingHandCursor)
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }}
        """)
        self.load_btn.clicked.connect(self.load_data)
        right_layout.addWidget(self.load_btn)
        
        # Frame indicator label
        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px; color: #333333;")
        right_layout.addWidget(self.frame_label)
        
        # Swap button
        self.swap_btn = QPushButton("Swap Left-Right ID (S)")
        self.swap_btn.setCursor(Qt.PointingHandCursor)
        self.swap_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.BTN_SWAP};
                color: #000000;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #FFB732;
            }}
            QPushButton:disabled {{
                background-color: #E0E0E0;
                color: #A0A0A0;
            }}
        """)
        self.swap_btn.clicked.connect(self.swap_current_frame)
        self.swap_btn.setEnabled(False)
        right_layout.addWidget(self.swap_btn)
        
        # Auto correct button
        self.auto_btn = QPushButton("Auto Correct Swaps")
        self.auto_btn.setCursor(Qt.PointingHandCursor)
        self.auto_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1976D2;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #1565C0;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
            }}
        """)
        self.auto_btn.clicked.connect(self.auto_correct)
        self.auto_btn.setEnabled(False)
        right_layout.addWidget(self.auto_btn)
        
        # Complete & Proceed button
        self.complete_btn = QPushButton("Save Correction & Proceed")
        self.complete_btn.setCursor(Qt.PointingHandCursor)
        self.complete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #40E0D0;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #35C4B5;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
            }}
        """)
        self.complete_btn.clicked.connect(self.save_and_complete)
        self.complete_btn.setEnabled(False)
        right_layout.addWidget(self.complete_btn)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 5px; font-size: 12px;")
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()
        main_layout.addWidget(right_group, stretch=2)
        
    def load_data(self):
        """Load scaled pose data for correction."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "No project loaded")
            return
        
        # Load from scaled_pose output - session-aware
        input_path = self.project_manager.find_output_file(subject_id, "scaled_pose", session_id)
        
        if not input_path:
            QMessageBox.warning(self, "Error", "Scaled pose file not found")
            return
        
        success, msg, count = self.corrector.load_scaled_data(input_path)
        
        if success:
            self.corrector.select_primary_person()
            self.data = self.corrector.extract_gait_joints()
            self.total_frames = len(self.data)
            self.current_frame = 0
            
            # Update slider
            self.frame_slider.setMaximum(self.total_frames - 1)
            self.frame_slider.setValue(0)
            
            # Enable buttons
            self.swap_btn.setEnabled(True)
            self.auto_btn.setEnabled(True)
            self.complete_btn.setEnabled(True)
            
            # Plot
            self.plot_trajectories()
            self.update_frame_label()
            
            self.status_label.setText(f"✓ Loaded {count} frames from scaled data")
            self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        else:
            QMessageBox.warning(self, "Error", msg)
            
    def plot_trajectories(self):
        """Plot ankle trajectories with current frame indicator."""
        if self.data is None:
            return
        
        self.axes.clear()
        
        # Get joint order
        joint_order = list(self.corrector.GAIT_JOINTS.keys())
        r_ankle_idx = joint_order.index("RAnkle")
        l_ankle_idx = joint_order.index("LAnkle")
        mid_hip_idx = joint_order.index("MidHip")
        
        # Calculate relative positions
        frames = np.arange(self.total_frames)
        
        r_ankle_x = self.data[:, r_ankle_idx, 0]
        l_ankle_x = self.data[:, l_ankle_idx, 0]
        mid_hip_x = self.data[:, mid_hip_idx, 0]
        
        # Relative to mid hip
        r_rel = r_ankle_x - mid_hip_x
        l_rel = l_ankle_x - mid_hip_x
        
        # Plot trajectories
        self.axes.plot(frames, l_rel, 'b-', linewidth=1.5, label='Ankle Kiri (L)')
        self.axes.plot(frames, r_rel, 'r-', linewidth=1.5, label='Ankle Kanan (R)')
        
        # Current frame indicator (green dashed line)
        self.frame_line = self.axes.axvline(
            self.current_frame, color='green', linestyle='--', linewidth=2
        )
        
        # Current frame points
        if not np.isnan(r_rel[self.current_frame]):
            self.axes.plot(self.current_frame, r_rel[self.current_frame], 
                          'ro', markersize=10, zorder=5)
        if not np.isnan(l_rel[self.current_frame]):
            self.axes.plot(self.current_frame, l_rel[self.current_frame], 
                          'bo', markersize=10, zorder=5)
        
        # Styling
        self.axes.set_xlabel('Frame', fontsize=12)
        self.axes.set_ylabel('Posisi X Relatif (px)', fontsize=12)
        self.axes.set_title(f'Visualisasi Posisi X Relatif - Frame {self.current_frame}', fontsize=14)
        self.axes.legend(loc='upper right', fontsize=10)
        self.axes.grid(True, alpha=0.3)
        self.axes.set_facecolor('white')
        
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        
    def on_slider_changed(self, value):
        """Handle frame slider change."""
        self.current_frame = value
        self.update_frame_label()
        self.plot_trajectories()
        
    def update_frame_label(self):
        """Update the frame counter label."""
        self.frame_label.setText(f"Frame: {self.current_frame} / {self.total_frames - 1}")
        
    def swap_current_frame(self):
        """Swap left-right labels at current frame."""
        if self.data is None:
            return
        
        # Swap at current frame
        self.data = self.corrector.manual_swap(self.data, self.current_frame, self.current_frame)
        self.plot_trajectories()
        
        self.status_label.setText(f"Swapped L/R at frame {self.current_frame}")
        self.status_label.setStyleSheet(f"color: {ModernStyle.WARNING};")
        
    def auto_correct(self):
        """Run automatic L/R correction."""
        if self.data is None:
            QMessageBox.warning(self, "Warning", "Please load data first")
            return
        
        # Re-run auto correction
        self.data, info = self.corrector.auto_correct()
        self.plot_trajectories()
        
        self.status_label.setText(
            f"✓ Auto-corrected {info.get('frames_corrected', 0)} frames. "
            f"Consistency: {info.get('corrected_consistency', 0):.1%}"
        )
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
    def save_and_complete(self):
        """Save corrected data and mark as complete."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id or self.data is None:
            return
        
        fps = self.project_manager.metadata.get("fps", 30.0)
        
        # Use session-aware output path
        output_path = self.project_manager.get_output_file_path(
            subject_id, "correction_legid", ".json", session_id
        )
        
        self.corrector.save_corrected_data(self.data, output_path, fps)
        
        self.status_label.setText(f"✓ Saved: {output_path}")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
        # Update pipeline status
        self.project_manager.update_pipeline_status(subject_id, "correction", "completed")
        
        self.correction_complete.emit()
        QMessageBox.information(self, "Success", "Correction data saved!")
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_S:
            self.swap_current_frame()
        elif event.key() == Qt.Key_Left:
            if self.current_frame > 0:
                self.frame_slider.setValue(self.current_frame - 1)
        elif event.key() == Qt.Key_Right:
            if self.current_frame < self.total_frames - 1:
                self.frame_slider.setValue(self.current_frame + 1)
