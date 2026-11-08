"""
OpenPose Tab Widget
===================
Handles OpenPose execution with progress indicator.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QProgressBar, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt

from .styles import ModernStyle


class OpenPoseWorker(QThread):
    """Background worker for OpenPose execution."""
    
    finished = pyqtSignal(bool, str, dict)
    progress = pyqtSignal(str)
    
    def __init__(self, pose_extractor, video_path, output_dir):
        super().__init__()
        self.pose_extractor = pose_extractor
        self.video_path = video_path
        self.output_dir = output_dir
        
    def run(self):
        self.progress.emit("Starting OpenPose...")
        success, msg, info = self.pose_extractor.run_openpose(
            self.video_path, self.output_dir
        )
        self.finished.emit(success, msg, info)


class OpenPoseTab(QWidget):
    """Tab for OpenPose execution with progress indicator."""
    
    processing_complete = pyqtSignal()
    
    def __init__(self, pose_extractor, project_manager):
        super().__init__()
        self.pose_extractor = pose_extractor
        self.project_manager = project_manager
        self.worker = None
        self.animation_timer = None
        self.animation_dots = 0
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- LEFT PANEL: Video & Diagram Preview ---
        left_group = QGroupBox("Video Display & Pose Detection")
        left_layout = QVBoxLayout(left_group)
        
        # Placeholder or Video Canvas for OpenPose Preview
        self.preview_label = QLabel("Video & Pose Overlay Display Area\n\n(Video will be rendered here during OpenPose processing)")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #1A1A2E;
                color: #A0A0B0;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(self.preview_label, stretch=1)
        main_layout.addWidget(left_group, stretch=3)
        
        # --- RIGHT PANEL: Configuration & Control Buttons ---
        right_group = QGroupBox("Control & Configuration Panel")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(15)
        
        # Configuration form
        config_form = QFormLayout()
        self.openpose_path = QLineEdit("C:/openpose/bin/OpenPoseDemo.exe")
        config_form.addRow("OpenPose Path:", self.openpose_path)
        
        self.model_path = QLineEdit("C:/openpose/models")
        config_form.addRow("Model Folder:", self.model_path)
        right_layout.addLayout(config_form)
        
        # Run button
        self.run_btn = QPushButton("Run OpenPose & Proceed")
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
            QPushButton:disabled {{
                background-color: #B0BEC5;
            }}
        """)
        self.run_btn.clicked.connect(self.run_openpose)
        right_layout.addWidget(self.run_btn)
        
        # Status section
        status_box = QVBoxLayout()
        status_title = QLabel("Processing Status:")
        status_title.setStyleSheet("font-weight: bold; color: #333333;")
        status_box.addWidget(status_title)
        
        self.status_label = QLabel("Ready to Process")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #F1F1F1;
                color: #333333;
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        
        status_hlayout = QHBoxLayout()
        status_hlayout.addWidget(self.status_label)
        status_hlayout.addStretch()
        status_box.addLayout(status_hlayout)
        
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                height: 8px;
                background-color: #E0E0E0;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #40E0D0;
                border-radius: 4px;
            }
        """)
        status_box.addWidget(self.progress)
        right_layout.addLayout(status_box)
        
        # Results Label
        self.results_label = QLabel("")
        self.results_label.setStyleSheet("font-size: 13px; padding: 5px;")
        right_layout.addWidget(self.results_label)
        
        right_layout.addStretch()
        main_layout.addWidget(right_group, stretch=2)
        
    def run_openpose(self):
        """Execute OpenPose on the video."""
        subject_id = self.project_manager.current_subject_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please initialize a project first")
            return
        
        video_path = self.project_manager.get_video_path(subject_id)
        output_dir = self.project_manager.get_openpose_output_path(subject_id)
        
        if not video_path:
            QMessageBox.warning(self, "Warning", "Video not found")
            return
        
        # Update UI
        self.run_btn.setEnabled(False)
        # self.progress.setVisible(True)  # Disabled in favor of spinner
        
        # Start animation
        self.start_processing_animation()
        
        # Start worker thread
        self.worker = OpenPoseWorker(self.pose_extractor, video_path, output_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def start_processing_animation(self):
        """Start the processing animation."""
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.animation_frame_idx = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(100)
        
    def update_animation(self):
        """Update the processing animation."""
        frame = self.spinner_frames[self.animation_frame_idx]
        self.animation_frame_idx = (self.animation_frame_idx + 1) % len(self.spinner_frames)
        self.status_label.setText(f"{frame} Processing keypoints")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #E5F2F9;
                color: #007AC7;
                border-radius: 15px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
    def on_progress(self, message):
        """Handle progress updates."""
        pass
        
    def on_finished(self, success, msg, info):
        """Handle completion."""
        # Stop animation
        if self.animation_timer:
            self.animation_timer.stop()
        
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("OpenPose Complete")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #EAF5E8;
                    color: #359B2E;
                    border-radius: 15px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            
            self.results_label.setText(f"✓ Successfully processed {info.get('total_frames', 0)} frames")
            self.results_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-size: 14px; padding: 10px;")
            
            # Update pipeline status
            subject_id = self.project_manager.current_subject_id
            if subject_id:
                self.project_manager.update_pipeline_status(subject_id, "openpose", "completed")
            
            self.processing_complete.emit()
        else:
            self.status_label.setText("OpenPose Failed")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #FDEAEA;
                    color: #D12020;
                    border-radius: 15px;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            
            self.results_label.setText("✗ Processing failed")
            self.results_label.setStyleSheet(f"color: {ModernStyle.ERROR}; font-size: 14px; padding: 10px;")
