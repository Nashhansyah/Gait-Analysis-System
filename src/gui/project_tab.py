"""
Project Tab Widget
==================
Handles project initialization and video acquisition with multi-session support.
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QComboBox
)
from PyQt5.QtCore import pyqtSignal

from .styles import ModernStyle


class ProjectTab(QWidget):
    """Tab for project initialization and video acquisition."""
    
    # Emits (subject_id, session_id) tuple
    project_created = pyqtSignal(str, str)
    
    def __init__(self, project_manager):
        super().__init__()
        self.project_manager = project_manager
        self.video_path = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Subject & Session input
        subject_group = QGroupBox("Subject Information")
        subject_layout = QFormLayout(subject_group)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter subject ID (e.g., subject_01)")
        self.subject_input.textChanged.connect(self._on_subject_changed)
        subject_layout.addRow("Subject ID:", self.subject_input)
        
        # Session input
        session_layout = QHBoxLayout()
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Enter session name (e.g., session_1)")
        session_layout.addWidget(self.session_input)
        
        # Existing sessions dropdown (hidden by default)
        self.existing_sessions_combo = QComboBox()
        self.existing_sessions_combo.setPlaceholderText("Or select existing subject...")
        self.existing_sessions_combo.setVisible(False)
        session_layout.addWidget(self.existing_sessions_combo)
        
        subject_layout.addRow("Session:", session_layout)
        
        # Info label for existing subject
        self.subject_info_label = QLabel("")
        self.subject_info_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; font-style: italic;")
        subject_layout.addRow("", self.subject_info_label)
        
        layout.addWidget(subject_group)
        
        # Video acquisition
        video_group = QGroupBox("Video Acquisition")
        video_layout = QVBoxLayout(video_group)
        
        btn_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Browse Video")
        self.browse_btn.setStyleSheet(f"background-color: {ModernStyle.PRIMARY};")
        self.browse_btn.clicked.connect(self.browse_video)
        btn_layout.addWidget(self.browse_btn)
        
        self.record_btn = QPushButton("Record Camera")
        self.record_btn.setStyleSheet(f"background-color: {ModernStyle.PRIMARY};")
        self.record_btn.clicked.connect(self.record_video)
        btn_layout.addWidget(self.record_btn)
        
        video_layout.addLayout(btn_layout)
        
        # Video info display
        self.video_info_label = QLabel("No video selected")
        self.video_info_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; padding: 10px;")
        video_layout.addWidget(self.video_info_label)
        
        layout.addWidget(video_group)
        
        # Initialize button
        self.init_btn = QPushButton("Initialize Project")
        self.init_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SUCCESS};
                color: #000000;
                font-size: 16px;
                padding: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3db892;
            }}
        """)
        self.init_btn.clicked.connect(self.initialize_project)
        layout.addWidget(self.init_btn)
        
        # Status display
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 10px; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _on_subject_changed(self, text):
        """Handle subject ID text change to show existing sessions."""
        subject_id = text.strip()
        
        if not subject_id:
            self.subject_info_label.setText("")
            self.existing_sessions_combo.setVisible(False)
            return
        
        # Check if subject exists
        existing_subjects = self.project_manager.get_existing_subjects()
        
        if subject_id in existing_subjects:
            # Subject exists - show sessions
            sessions = self.project_manager.get_sessions(subject_id)
            session_count = len(sessions)
            session_names = [s["session_id"] for s in sessions]
            
            self.subject_info_label.setText(
                f"ℹ️ Subject exists with {session_count} session(s): {', '.join(session_names)}. "
                f"Enter a new session name to add another recording."
            )
            self.subject_info_label.setStyleSheet(f"color: {ModernStyle.PRIMARY}; font-style: italic;")
        else:
            self.subject_info_label.setText("")
            self.existing_sessions_combo.setVisible(False)
        
    def browse_video(self):
        """Open file dialog to select video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.video_path = file_path
            self.video_info_label.setText(f"✓ Selected: {os.path.basename(file_path)}")
            self.video_info_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; padding: 10px;")
            
    def record_video(self):
        """Open camera recording dialog."""
        from PyQt5.QtWidgets import QDialog
        from .camera_recording_dialog import CameraRecordingDialog
        
        dialog = CameraRecordingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            video_path = dialog.get_video_path()
            if video_path:
                self.video_path = video_path
                video_info = dialog.get_video_info()
                duration_str = ""
                if video_info and video_info.get('duration'):
                    duration = video_info['duration']
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    duration_str = f" ({mins}:{secs:02d})"
                self.video_info_label.setText(f"✓ Recorded: video{duration_str}")
                self.video_info_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; padding: 10px;")
        
    def initialize_project(self):
        """Initialize the project with entered information."""
        subject_id = self.subject_input.text().strip()
        session_id = self.session_input.text().strip()
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please enter a Subject ID")
            return
        
        # Check if subject exists
        existing_subjects = self.project_manager.get_existing_subjects()
        is_existing_subject = subject_id in existing_subjects
        
        # For existing subject, session_id is required
        if is_existing_subject and not session_id:
            QMessageBox.warning(
                self, "Warning", 
                f"Subject '{subject_id}' already exists. Please enter a Session name to add a new recording."
            )
            return
        
        # For new subject without session, use default
        if not is_existing_subject and not session_id:
            session_id = self.project_manager.DEFAULT_SESSION_ID
        
        # Validate subject and session ID
        valid, msg = self.project_manager.validate_subject_id(subject_id, session_id if is_existing_subject else None)
        if not valid:
            QMessageBox.warning(self, "Invalid Input", msg)
            return
        
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please select a video file")
            return
        
        # Import video with session
        success, msg, video_info = self.project_manager.browse_video(
            self.video_path, subject_id, session_id
        )
        
        if not success:
            QMessageBox.critical(self, "Error", msg)
            return
        
        # Save metadata with session
        self.project_manager.save_metadata(subject_id, video_info, session_id=session_id)
        
        # Display status
        if session_id == self.project_manager.DEFAULT_SESSION_ID:
            status_text = f"✓ Project initialized: {subject_id}"
        else:
            status_text = f"✓ Project initialized: {subject_id} / {session_id}"
        
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; padding: 10px; font-size: 14px;")
        
        # Clear inputs for next project
        self.video_path = None
        self.video_info_label.setText("No video selected")
        self.video_info_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; padding: 10px;")
        
        # Emit signal with both subject_id and session_id
        self.project_created.emit(subject_id, session_id)
    
    def set_for_new_session(self, subject_id: str):
        """Pre-fill the form for adding a new session to existing subject."""
        self.subject_input.setText(subject_id)
        self.session_input.setFocus()
        self.session_input.setPlaceholderText("Enter new session name")
