"""
Project Dialog Windows
======================
Dialog windows for subject and session management.
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QComboBox, QScrollArea, QRadioButton, QButtonGroup, QWidget
)
from PyQt5.QtCore import Qt

from .styles import ModernStyle


def confirm_action(parent, title, message):
    """Show a confirmation dialog with explicit Green (Yes) and Red (No) buttons."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Question)
    
    yes_btn = msg_box.addButton("  Ya (Yes)  ", QMessageBox.YesRole)
    no_btn = msg_box.addButton("  Tidak (No)  ", QMessageBox.NoRole)
    msg_box.setDefaultButton(no_btn)
    
    # Direct styling on button objects ensures rendering over any native/global style
    yes_btn.setStyleSheet("""
        background-color: #198754 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 13px !important;
        border: 2px solid #146c43 !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        min-width: 75px !important;
    """)
    
    no_btn.setStyleSheet("""
        background-color: #dc3545 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 13px !important;
        border: 2px solid #b02a37 !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        min-width: 75px !important;
    """)
    
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #ffffff;
        }
        QLabel {
            color: #000000 !important;
            font-size: 13px !important;
            font-weight: bold !important;
        }
    """)
    
    msg_box.exec_()
    return msg_box.clickedButton() == yes_btn


def show_info(parent, title, message):
    """Show an information dialog with explicit Green OK button."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)
    
    ok_btn = msg_box.addButton("  OK  ", QMessageBox.AcceptRole)
    ok_btn.setStyleSheet("""
        background-color: #198754 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 13px !important;
        border: 2px solid #146c43 !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        min-width: 75px !important;
    """)
    
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #ffffff;
        }
        QLabel {
            color: #000000 !important;
            font-size: 13px !important;
            font-weight: bold !important;
        }
    """)
    msg_box.exec_()


def show_warning(parent, title, message):
    """Show a warning dialog with explicit Red OK button."""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning)
    
    ok_btn = msg_box.addButton("  OK  ", QMessageBox.AcceptRole)
    ok_btn.setStyleSheet("""
        background-color: #dc3545 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 13px !important;
        border: 2px solid #b02a37 !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        min-width: 75px !important;
    """)
    
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #ffffff;
        }
        QLabel {
            color: #000000 !important;
            font-size: 13px !important;
            font-weight: bold !important;
        }
    """)
    msg_box.exec_()


class NewSubjectDialog(QDialog):
    """Dialog for creating a new subject/project."""
    
    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.subject_id = None
        
        self.setWindowTitle("New Subject")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Create New Subject")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: #000000;
        """)
        layout.addWidget(title)
        
        # Subject ID input
        form_group = QGroupBox("Subject Information")
        form_layout = QFormLayout(form_group)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter subject name (e.g., patient_001)")
        self.subject_input.setMinimumHeight(35)
        form_layout.addRow("Subject Name:", self.subject_input)
        
        # Info label
        info_label = QLabel("This will create a folder for the subject. Sessions can be added later.")
        info_label.setStyleSheet("color: #000000; font-size: 12px; font-weight: bold;")
        info_label.setWordWrap(True)
        form_layout.addRow("", info_label)
        
        layout.addWidget(form_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #6c757d;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("Create Subject")
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SUCCESS};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
            }}
        """)
        create_btn.clicked.connect(self.create_subject)
        btn_layout.addWidget(create_btn)
        
        layout.addLayout(btn_layout)
        
    def create_subject(self):
        """Create the subject folder."""
        subject_id = self.subject_input.text().strip()
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please enter a subject name")
            return
        
        # Validate subject ID (without session - just check format and duplicates)
        valid, msg = self.project_manager.validate_subject_id(subject_id)
        if not valid:
            QMessageBox.warning(self, "Invalid Subject Name", msg)
            return
        
        # Create subject folder structure (minimal - just metadata folder and entry)
        self.subject_id = subject_id
        
        # Create minimal metadata for subject
        metadata_dir = os.path.join(self.project_manager.base_data_path, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        import json
        from datetime import datetime
        
        metadata = {
            "subject_id": subject_id,
            "created_at": datetime.now().isoformat(),
            "sessions": {}
        }
        
        metadata_path = os.path.join(metadata_dir, f"{subject_id}_project.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.accept()
    
    def get_subject_id(self):
        """Return the created subject ID."""
        return self.subject_id


class AddSessionDialog(QDialog):
    """Dialog for adding a session with video to an existing subject."""
    
    def __init__(self, project_manager, subject_id, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.subject_id = subject_id
        self.session_id = None
        self.video_path = None
        
        self.setWindowTitle(f"Add Session - {subject_id}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel(f"Add Session for: {self.subject_id}")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: #000000;
        """)
        layout.addWidget(title)
        
        # Session input
        session_group = QGroupBox("Session Information")
        session_layout = QFormLayout(session_group)
        
        # Get next session number
        sessions = self.project_manager.get_sessions(self.subject_id)
        next_session_num = self._get_next_session_number(sessions)
        
        self.session_input = QLineEdit()
        self.session_input.setText(f"session_{next_session_num}")
        self.session_input.setPlaceholderText(f"e.g., session_{next_session_num}")
        self.session_input.setMinimumHeight(35)
        session_layout.addRow("Session Name:", self.session_input)
        
        # Show existing sessions
        if sessions:
            existing_text = ", ".join([s["session_id"] for s in sessions if not s.get("is_legacy")])
            if existing_text:
                existing_label = QLabel(f"Existing sessions: {existing_text}")
            else:
                existing_label = QLabel("No sessions yet")
            existing_label.setStyleSheet("color: #000000; font-size: 12px; font-weight: bold;")
            session_layout.addRow("", existing_label)
        
        layout.addWidget(session_group)
        
        # Video acquisition
        video_group = QGroupBox("Video Input")
        video_layout = QVBoxLayout(video_group)
        
        btn_layout = QHBoxLayout()
        
        browse_btn = QPushButton("Browse Video")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ABC9C;
                color: #FFFFFF;
            }
        """)
        browse_btn.clicked.connect(self.browse_video)
        btn_layout.addWidget(browse_btn)
        
        record_btn = QPushButton("Record Camera")
        record_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ABC9C;
                color: #FFFFFF;
            }
        """)
        record_btn.clicked.connect(self.record_video)
        btn_layout.addWidget(record_btn)
        
        video_layout.addLayout(btn_layout)
        
        # Video info
        self.video_info_label = QLabel("No video selected")
        self.video_info_label.setStyleSheet("color: #000000; padding: 10px; font-weight: bold;")
        video_layout.addWidget(self.video_info_label)
        
        layout.addWidget(video_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc3545;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.create_btn = QPushButton("Create Session")
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SUCCESS};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
            }}
        """)
        self.create_btn.clicked.connect(self.create_session)
        btn_layout.addWidget(self.create_btn)
        
        layout.addLayout(btn_layout)
    
    def _get_next_session_number(self, sessions):
        """Calculate the next session number."""
        if not sessions:
            return 1
        
        max_num = 0
        for s in sessions:
            session_id = s.get("session_id", "")
            # Try to extract number from session_N format
            if session_id.startswith("session_"):
                try:
                    num = int(session_id.split("_")[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    pass
            # Also check just numbers
            elif session_id.isdigit():
                max_num = max(max_num, int(session_id))
        
        return max_num + 1
    
    def browse_video(self):
        """Open file dialog to select video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.video_path = file_path
            self.video_info_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.video_info_label.setStyleSheet("color: #000000; padding: 10px; font-weight: bold;")
    
    def record_video(self):
        """Open camera recording dialog."""
        from PyQt5.QtWidgets import QDialog as QDlg
        from .camera_recording_dialog import CameraRecordingDialog
        
        dialog = CameraRecordingDialog(self)
        if dialog.exec_() == QDlg.Accepted:
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
                self.video_info_label.setText(f"Recorded: video{duration_str}")
                self.video_info_label.setStyleSheet("color: #000000; padding: 10px; font-weight: bold;")
    
    def create_session(self):
        """Create the session with video."""
        session_id = self.session_input.text().strip()
        
        if not session_id:
            QMessageBox.warning(self, "Warning", "Please enter a session name")
            return
        
        # Validate session ID
        if not all(c.isalnum() or c == '_' for c in session_id):
            QMessageBox.warning(self, "Warning", "Session name can only contain letters, numbers, and underscores")
            return
        
        # Check if session exists
        if self.project_manager.session_exists(self.subject_id, session_id):
            QMessageBox.warning(self, "Warning", f"Session '{session_id}' already exists")
            return
        
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please select or record a video")
            return
        
        # Import video
        success, msg, video_info = self.project_manager.browse_video(
            self.video_path, self.subject_id, session_id
        )
        
        if not success:
            QMessageBox.critical(self, "Error", msg)
            return
        
        # Save metadata
        self.project_manager.save_metadata(self.subject_id, video_info, session_id=session_id)
        
        self.session_id = session_id
        self.accept()
    
    def get_session_id(self):
        """Return the created session ID."""
        return self.session_id


class DeleteProjectDialog(QDialog):
    """Dialog for deleting projects and sessions with a breakdown view."""
    
    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        
        self.setWindowTitle("Delete Project / Session")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_subjects()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("Delete Project or Session")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #000000;
        """)
        layout.addWidget(title)
        
        # Project selection
        form_layout = QFormLayout()
        self.subject_combo = QComboBox()
        self.subject_combo.setMinimumHeight(35)
        self.subject_combo.currentTextChanged.connect(self.on_subject_changed)
        form_layout.addRow("Select Project:", self.subject_combo)
        layout.addLayout(form_layout)
        
        # Breakdown group
        self.breakdown_group = QGroupBox("Project Breakdown (Sessions)")
        self.breakdown_layout = QVBoxLayout(self.breakdown_group)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(150)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 5px;
                background-color: {ModernStyle.SURFACE};
            }}
        """)
        
        self.session_container = QWidget()
        self.session_list_layout = QVBoxLayout(self.session_container)
        self.session_list_layout.setSpacing(5)
        self.session_list_layout.setContentsMargins(5, 5, 5, 5)
        
        self.scroll_area.setWidget(self.session_container)
        self.breakdown_layout.addWidget(self.scroll_area)
        
        # Radio button group for selection
        self.button_group = QButtonGroup(self)
        self.selected_session = [None]
        
        layout.addWidget(self.breakdown_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        # Delete Session button
        self.delete_session_btn = QPushButton("Delete Selected Session")
        self.delete_session_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.ERROR};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #c73e54;
            }}
        """)
        self.delete_session_btn.clicked.connect(self.delete_selected_session)
        btn_layout.addWidget(self.delete_session_btn)
        
        # Delete Entire Project button
        self.delete_project_btn = QPushButton("Delete Entire Project")
        self.delete_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5b0000;
            }
        """)
        self.delete_project_btn.clicked.connect(self.delete_entire_project)
        btn_layout.addWidget(self.delete_project_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def load_subjects(self):
        subjects = self.project_manager.get_existing_subjects()
        self.subject_combo.clear()
        self.subject_combo.addItems(subjects)
        
        # Disable buttons if no projects
        has_projects = len(subjects) > 0
        self.delete_session_btn.setEnabled(has_projects)
        self.delete_project_btn.setEnabled(has_projects)
        
    def on_subject_changed(self, subject_id):
        # Clear previous session list
        while self.session_list_layout.count():
            item = self.session_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not subject_id:
            return
            
        sessions = self.project_manager.get_sessions(subject_id)
        
        # Clear button group
        for btn in self.button_group.buttons():
            self.button_group.removeButton(btn)
            
        self.selected_session[0] = None
        
        if not sessions:
            no_sess_label = QLabel("No sessions found for this project.")
            no_sess_label.setStyleSheet("color: #777777; padding: 10px;")
            self.session_list_layout.addWidget(no_sess_label)
            self.delete_session_btn.setEnabled(False)
            return
            
        self.delete_session_btn.setEnabled(True)
        
        for i, s in enumerate(sessions):
            radio = QRadioButton(f"📂 {s['session_id']} (Created: {s.get('created_at', 'N/A')[:10]})")
            radio.setStyleSheet("font-size: 13px; padding: 5px;")
            if i == 0:
                radio.setChecked(True)
                self.selected_session[0] = s['session_id']
            radio.toggled.connect(lambda checked, sid=s['session_id']: 
                self.selected_session.__setitem__(0, sid) if checked else None)
            self.button_group.addButton(radio)
            self.session_list_layout.addWidget(radio)
            
        self.session_list_layout.addStretch()
        
    def delete_selected_session(self):
        subject_id = self.subject_combo.currentText()
        session_id = self.selected_session[0]
        
        if not subject_id or not session_id:
            show_warning(self, "Warning", "Please select a session to delete.")
            return
            
        if confirm_action(
            self, "Confirm Delete",
            f"Are you sure you want to delete session '{session_id}' of project '{subject_id}'?\n\n"
            "This action cannot be undone!"
        ):
            success, msg = self.project_manager.delete_project(subject_id, session_id)
            if success:
                show_info(self, "Success", msg)
                self.on_subject_changed(subject_id)
                self.load_subjects()
            else:
                show_warning(self, "Error", msg)
                
    def delete_entire_project(self):
        subject_id = self.subject_combo.currentText()
        if not subject_id:
            show_warning(self, "Warning", "Please select a project to delete.")
            return
            
        if confirm_action(
            self, "Confirm Delete Project",
            f"Are you sure you want to delete the entire project '{subject_id}' and all its sessions?\n\n"
            "This action cannot be undone!"
        ):
            success, msg = self.project_manager.delete_project(subject_id)
            if success:
                show_info(self, "Success", msg)
                self.load_subjects()
            else:
                show_warning(self, "Error", msg)


class LoadReportProjectDialog(QDialog):
    """Dialog specifically for selecting a subject and session to load in ReportTab independently."""
    
    def __init__(self, project_manager, current_subject=None, current_session=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.selected_subject_id = current_subject
        self.selected_session_id = current_session
        
        self.setWindowTitle("Load Report - Select Project & Session")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_subjects()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header title
        title = QLabel("Select Project for Report")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        layout.addWidget(title)
        
        subtitle = QLabel("Choose a Subject/Patient and Session to view its analysis report independently.")
        subtitle.setStyleSheet("font-size: 12px; color: #555555;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Form group
        form_group = QGroupBox("Project Selection")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)
        
        # Subject dropdown
        self.subject_combo = QComboBox()
        self.subject_combo.setMinimumHeight(38)
        self.subject_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #000000;
            }
        """)
        self.subject_combo.currentTextChanged.connect(self.on_subject_changed)
        form_layout.addRow("Subject / Patient:", self.subject_combo)
        
        # Session dropdown
        self.session_combo = QComboBox()
        self.session_combo.setMinimumHeight(38)
        self.session_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #000000;
            }
        """)
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        form_layout.addRow("Session:", self.session_combo)
        
        layout.addWidget(form_group)
        
        # Session Info / Available Outputs Card
        self.info_group = QGroupBox("Report Data Status")
        info_layout = QVBoxLayout(self.info_group)
        self.info_label = QLabel("Select a project and session...")
        self.info_label.setStyleSheet("font-size: 12px; color: #333333; padding: 5px;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        layout.addWidget(self.info_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.load_btn = QPushButton("Load Selected Report")
        self.load_btn.setMinimumHeight(40)
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #16A085;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
                color: #FFFFFF;
            }}
        """)
        self.load_btn.clicked.connect(self.on_load_clicked)
        btn_layout.addWidget(self.load_btn)
        
        layout.addLayout(btn_layout)
        
    def load_subjects(self):
        subjects = self.project_manager.get_existing_subjects()
        self.subject_combo.clear()
        if not subjects:
            self.info_label.setText("⚠️ No projects available. Please create/load a project on the Homepage first.")
            self.load_btn.setEnabled(False)
            return
            
        self.subject_combo.addItems(subjects)
        if self.selected_subject_id in subjects:
            self.subject_combo.setCurrentText(self.selected_subject_id)
            
    def on_subject_changed(self, subject_id):
        self.session_combo.clear()
        if not subject_id:
            self.load_btn.setEnabled(False)
            return
            
        sessions = self.project_manager.get_sessions(subject_id)
        if not sessions:
            self.session_combo.addItem("default")
        else:
            for s in sessions:
                self.session_combo.addItem(s["session_id"])
                
        if self.selected_session_id and self.session_combo.findText(self.selected_session_id) >= 0:
            self.session_combo.setCurrentText(self.selected_session_id)
            
        self.update_info_status()
        
    def on_session_changed(self, session_id):
        self.update_info_status()
        
    def update_info_status(self):
        subject_id = self.subject_combo.currentText()
        session_id = self.session_combo.currentText()
        
        if not subject_id or not session_id:
            self.info_label.setText("No subject or session selected.")
            self.load_btn.setEnabled(False)
            return
            
        # Check files availability
        has_events = bool(self.project_manager.find_output_file(subject_id, "gait_events", session_id))
        has_params = bool(self.project_manager.find_output_file(subject_id, "gait_parameters_summary", session_id))
        openpose_path = self.project_manager.get_openpose_output_path(subject_id, session_id)
        has_video = (os.path.exists(openpose_path) if openpose_path else False) or bool(self.project_manager.get_video_path(subject_id, session_id))
        
        status_lines = []
        status_lines.append(f"<b>Subject:</b> {subject_id} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Session:</b> {session_id}")
        status_lines.append("<b>Available Report Data:</b>")
        status_lines.append(f"• Video: {'✓ Ready' if has_video else '❌ Missing'}")
        status_lines.append(f"• Gait Events: {'✓ Ready' if has_events else '⚠️ Not computed'}")
        status_lines.append(f"• Gait Parameters: {'✓ Ready' if has_params else '⚠️ Not computed'}")
        
        self.info_label.setText("<br>".join(status_lines))
        self.load_btn.setEnabled(True)
        
    def on_load_clicked(self):
        self.selected_subject_id = self.subject_combo.currentText()
        self.selected_session_id = self.session_combo.currentText()
        self.accept()
        
    def get_selected_project(self):
        return self.selected_subject_id, self.selected_session_id


