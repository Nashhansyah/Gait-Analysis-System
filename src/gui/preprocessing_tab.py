"""
Preprocessing Tab Widget
========================
Signal preprocessing with before/after visualization.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from .styles import ModernStyle


class PreprocessingTab(QWidget):
    """Tab for signal preprocessing."""
    
    preprocessing_complete = pyqtSignal()
    
    def __init__(self, preprocessor, project_manager):
        super().__init__()
        self.preprocessor = preprocessor
        self.project_manager = project_manager
        self.original_data = None
        self.preprocessed_data = None
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- LEFT PANEL: Diagram Canvas ---
        left_group = QGroupBox("Gait Signal Visualization Diagram")
        left_layout = QVBoxLayout(left_group)
        
        self.canvas = FigureCanvas(Figure(figsize=(8, 5), facecolor='white'))
        self.axes = self.canvas.figure.add_subplot(111)
        self.axes.text(0.5, 0.5, 'Kinematic Signal Graph (Original vs Filtered)\n\nClick "Run Preprocessing" to view signal waveforms', 
                       horizontalalignment='center', verticalalignment='center', transform=self.axes.transAxes, color='#888888', fontsize=12)
        self.axes.axis('off')
        left_layout.addWidget(self.canvas, stretch=1)
        main_layout.addWidget(left_group, stretch=3)
        
        # --- RIGHT PANEL: Controls & Configuration ---
        right_group = QGroupBox("Preprocessing Control Panel")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(15)
        
        info_group = QGroupBox("Filtering Pipeline Steps")
        info_layout = QVBoxLayout(info_group)
        
        steps = [
            "✓ Temporal alignment & resampling",
            "✓ Low-pass Butterworth filter (6 Hz)",
            "✓ Missing data interpolation",
            "✓ Outlier removal",
            "✓ Computation velocity & acceleration"
        ]
        
        for step in steps:
            label = QLabel(step)
            label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; padding: 3px; font-size: 12px;")
            info_layout.addWidget(label)
            
        right_layout.addWidget(info_group)
        
        # Run button
        self.run_btn = QPushButton("Run Preprocessing & Proceed")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #40E0D0;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #35C4B5;
            }}
        """)
        self.run_btn.clicked.connect(self.run_preprocessing)
        right_layout.addWidget(self.run_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()
        main_layout.addWidget(right_group, stretch=2)
        
    def run_preprocessing(self):
        """Run the preprocessing pipeline."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "No project loaded")
            return
        
        # NEW: Load directly from OpenPose raw (before scaling) - session-aware
        openpose_dir = self.project_manager.get_openpose_output_path(subject_id, session_id)
        fps = self.project_manager.metadata.get("fps", 30.0)
        
        success, msg, data = self.preprocessor.load_openpose_raw(openpose_dir, fps)
        if not success:
            QMessageBox.warning(self, "Error", f"Failed to load OpenPose data: {msg}")
            return
        
        self.original_data = data.copy()
        
        # Run preprocessing (now in PIXEL units - smoother!)
        self.preprocessed_data = self.preprocessor.preprocess(data)
        
        # Save using session-aware path
        output_path = self.project_manager.get_output_file_path(
            subject_id, "preprocessed_signal", ".json", session_id
        )
        self.preprocessor.save_preprocessed_data(self.preprocessed_data, output_path)
        
        # Plot comparison
        self.plot_comparison()
        
        self.status_label.setText("✓ Preprocessing completed (filtered in pixels)")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
        # Update pipeline status
        self.project_manager.update_pipeline_status(subject_id, "preprocessing", "completed")
        
        self.preprocessing_complete.emit()
        
    def plot_comparison(self):
        """Plot before/after comparison."""
        self.axes.clear()
        
        orig_times, orig_y = self.preprocessor.get_signal(self.original_data, "RAnkle", "y")
        prep_times, prep_y = self.preprocessor.get_signal(self.preprocessed_data, "RAnkle", "y")
        
        self.axes.plot(orig_times, orig_y, 'b-', alpha=0.4, linewidth=1, label='Original')
        self.axes.plot(prep_times, prep_y, 'r-', linewidth=1.5, label='Filtered')
        
        self.axes.set_xlabel('Time (s)', fontsize=12)
        self.axes.set_ylabel('Y Position (m)', fontsize=12)
        self.axes.set_title('Signal Preprocessing: Right Ankle Y', fontsize=14)
        self.axes.legend(loc='upper right')
        self.axes.grid(True, alpha=0.3)
        
        self.canvas.figure.tight_layout()
        self.canvas.draw()
