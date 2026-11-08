"""
Dashboard Tab Widget
====================
Main dashboard showing project statistics and quick actions.
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QFrame, QMessageBox, QInputDialog, QLineEdit,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor

from .styles import ModernStyle


class StatCard(QFrame):
    """A card widget for displaying a statistic."""
    
    def __init__(self, title: str, value: str, icon: str = "", color: str = None):
        super().__init__()
        self.setObjectName("StatCard")
        self.setStyleSheet("""
            QFrame#StatCard {
                background-color: #1ABC9C;
                border: 2px solid transparent;
                border-radius: 12px;
                padding: 15px;
            }
            QFrame#StatCard:hover {
                border: 2px solid #000000;
                background-color: #48C9B0;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Icon and title
        header = QHBoxLayout()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI", 24))
            icon_label.setStyleSheet("color: #FFFFFF; background-color: transparent;")
            header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold; background-color: transparent;")
        header.addWidget(title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 28px;
            font-weight: bold;
            background-color: transparent;
        """)
        layout.addWidget(self.value_label)
        
        # Setup DropShadow Effect for Animation
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(5)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        
        self.anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    def enterEvent(self, event):
        self.anim.setStartValue(self.shadow.blurRadius())
        self.anim.setEndValue(25)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.setStartValue(self.shadow.blurRadius())
        self.anim.setEndValue(5)
        self.anim.start()
        super().leaveEvent(event)
        
    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardTab(QWidget):
    """Dashboard tab showing project overview and quick actions."""
    
    new_project_clicked = pyqtSignal()
    load_project_clicked = pyqtSignal()
    delete_project_clicked = pyqtSignal()
    project_selected = pyqtSignal(str, str)  # subject_id, session_id
    
    def __init__(self, project_manager):
        super().__init__()
        self.project_manager = project_manager
        self.setup_ui()
        self.refresh_stats()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(25)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Homepage")
        title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: #000000;
            padding: 10px 0;
        """)
        layout.addWidget(title)
        
        # Welcome message removed
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        self.projects_card = StatCard("Total Projects", "0", "📁", ModernStyle.ACCENT)
        stats_layout.addWidget(self.projects_card)
        
        self.completed_card = StatCard("Completed", "0", "✅", ModernStyle.SUCCESS)
        stats_layout.addWidget(self.completed_card)
        
        self.storage_card = StatCard("Storage Used", "0 MB", "💾", ModernStyle.SUCCESS)
        stats_layout.addWidget(self.storage_card)
        

        # Quick Actions
        actions_group = QFrame()
        actions_group.setStyleSheet(f"""
            QFrame {{
                padding-top: 10px;
            }}
        """)
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setSpacing(20)
        
        # Add stretch to push buttons to the right
        actions_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {ModernStyle.PRIMARY};
                color: {ModernStyle.TEXT};
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.PRIMARY};
                color: #FFFFFF;
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_stats)
        actions_layout.addWidget(refresh_btn)

        # New Project button
        new_btn = QPushButton("New Subject")
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {ModernStyle.SUCCESS};
                color: {ModernStyle.TEXT};
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.SUCCESS};
                color: #FFFFFF;
            }}
        """)
        new_btn.clicked.connect(self.on_new_subject)
        actions_layout.addWidget(new_btn)

        # Delete Project button
        delete_btn = QPushButton("Delete Project")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {ModernStyle.ERROR};
                color: {ModernStyle.TEXT};
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {ModernStyle.ERROR};
                color: #fff;
            }}
        """)
        delete_btn.clicked.connect(self.on_delete_project)
        actions_layout.addWidget(delete_btn)
        layout.addWidget(actions_group)
        
        # Add Stats layout after Quick Actions
        layout.addLayout(stats_layout)
        
        # Recent Projects
        recent_group = QGroupBox("Project")
        recent_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 16px;
                font-weight: bold;
                padding-top: 20px;
            }}
        """)
        self.recent_layout = QVBoxLayout(recent_group)
        
        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search projects...")
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                padding: 10px;
                font-size: 14px;
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 5px;
                background-color: {ModernStyle.SURFACE};
            }}
        """)
        self.search_bar.textChanged.connect(self.on_search_changed)
        self.recent_layout.addWidget(self.search_bar)
        
        # Grid layout for projects
        self.projects_grid_widget = QWidget()
        self.projects_grid = QGridLayout(self.projects_grid_widget)
        self.projects_grid.setSpacing(10)
        self.recent_layout.addWidget(self.projects_grid_widget)
        
        self.no_projects_label = QLabel("No projects found.")
        self.no_projects_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; padding: 20px;")
        self.recent_layout.addWidget(self.no_projects_label)
        
        layout.addWidget(recent_group)
        
        layout.addStretch()
        
    def refresh_stats(self):
        """Refresh dashboard statistics."""
        subjects = self.project_manager.get_existing_subjects()
        
        # Count projects
        self.projects_card.set_value(str(len(subjects)))
        
        # Calculate storage
        total_size = self.calculate_storage()
        if total_size < 1024:
            size_str = f"{total_size:.1f} KB"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} MB"
        else:
            size_str = f"{total_size / (1024 * 1024):.2f} GB"
        self.storage_card.set_value(size_str)
        
        # Count completed projects
        completed = 0
        for subject in subjects:
            success, _, metadata = self.project_manager.load_project(subject, set_current=False)
            if success:
                status = metadata.get("pipeline_status", {})
                if status.get("gait_parameter") == "completed":
                    completed += 1
        self.completed_card.set_value(str(completed))
        
        # Update recent projects list
        self.update_recent_projects(subjects)
        
    def calculate_storage(self) -> float:
        """Calculate total storage used in KB."""
        data_path = Path(self.project_manager.base_data_path)
        if not data_path.exists():
            return 0
        
        total = 0
        for file in data_path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        
        return total / 1024  # Return in KB
        
    def on_search_changed(self, text):
        self.refresh_stats()

    def update_recent_projects(self, subjects: list):
        """Update the recent projects list."""
        # Clear existing project buttons
        while self.projects_grid.count():
            item = self.projects_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        search_text = self.search_bar.text().lower()
        filtered_subjects = [s for s in subjects if search_text in s.lower()]
        
        if not filtered_subjects:
            self.no_projects_label.show()
            self.projects_grid_widget.hide()
            return
        
        self.no_projects_label.hide()
        self.projects_grid_widget.show()
        
        # Add project buttons in 3 columns
        row, col = 0, 0
        for subject in filtered_subjects:
            btn = QPushButton(f"{subject}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ModernStyle.SURFACE};
                    color: {ModernStyle.TEXT};
                    border: 1px solid {ModernStyle.PRIMARY};
                    text-align: left;
                    padding: 15px 20px;
                    font-size: 14px;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: #1ABC9C;
                    color: #ffffff;
                }}
            """)
            btn.clicked.connect(lambda checked, s=subject: self.on_subject_clicked(s))
            self.projects_grid.addWidget(btn, row, col)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
            
    def on_new_subject(self):
        """Open dialog to create a new subject, then add session."""
        from .project_dialogs import NewSubjectDialog, AddSessionDialog
        
        dialog = NewSubjectDialog(self.project_manager, self)
        if dialog.exec_() == dialog.Accepted:
            subject_id = dialog.get_subject_id()
            if subject_id:
                self.refresh_stats()
                
                # Auto-open AddSessionDialog for new subject
                session_dialog = AddSessionDialog(self.project_manager, subject_id, self)
                if session_dialog.exec_() == session_dialog.Accepted:
                    session_id = session_dialog.get_session_id()
                    if session_id:
                        self.project_selected.emit(subject_id, session_id)
                        self.refresh_stats()
    
    def on_subject_clicked(self, subject_id: str):
        """Open dialog to add session or load existing session."""
        from .project_dialogs import AddSessionDialog, confirm_action, show_info, show_warning
        from PyQt5.QtWidgets import QDialog, QScrollArea, QRadioButton, QButtonGroup
        
        # Get existing sessions
        sessions = self.project_manager.get_sessions(subject_id)
        
        # If subject has sessions, ask what to do
        if sessions and not sessions[0].get("is_legacy", False):
            choice_dialog = QDialog(self)
            choice_dialog.setWindowTitle(f"Subject: {subject_id}")
            choice_dialog.setMinimumWidth(450)
            layout = QVBoxLayout(choice_dialog)
            
            label = QLabel(f"Subject '{subject_id}' has {len(sessions)} session(s):")
            label.setStyleSheet("font-size: 14px; padding: 10px;")
            layout.addWidget(label)
            
            # Session container with scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(200)
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: 1px solid {ModernStyle.PRIMARY};
                    border-radius: 5px;
                    background-color: {ModernStyle.SURFACE};
                }}
            """)
            
            session_container = QWidget()
            session_layout = QVBoxLayout(session_container)
            session_layout.setSpacing(5)
            session_layout.setContentsMargins(5, 5, 5, 5)
            
            # Radio button group for session selection
            button_group = QButtonGroup(choice_dialog)
            selected_session = [None]  # Use list to allow modification in lambda
            
            def delete_session(session_id_to_delete):
                """Delete a session after confirmation."""
                if confirm_action(
                    choice_dialog, "Confirm Delete",
                    f"Are you sure you want to delete session '{session_id_to_delete}'?\n\n"
                    "This action cannot be undone!"
                ):
                    success, msg = self.project_manager.delete_project(subject_id, session_id_to_delete)
                    if success:
                        show_info(choice_dialog, "Success", msg)
                        choice_dialog.done(3)  # 3 = refresh needed
                    else:
                        show_warning(choice_dialog, "Error", msg)
            
            def delete_entire_project():
                """Delete the entire project (all sessions) after confirmation."""
                if confirm_action(
                    choice_dialog, "Confirm Delete Project",
                    f"Are you sure you want to delete the entire project '{subject_id}' and all its sessions?\n\n"
                    "This action cannot be undone!"
                ):
                    success, msg = self.project_manager.delete_project(subject_id)
                    if success:
                        show_info(choice_dialog, "Success", msg)
                        choice_dialog.done(3)  # 3 = refresh needed
                    else:
                        show_warning(choice_dialog, "Error", msg)
            
            for i, s in enumerate(sessions):
                row = QWidget()
                row.setStyleSheet(f"""
                    QWidget {{
                        background-color: {ModernStyle.BACKGROUND};
                        border-radius: 5px;
                        padding: 5px;
                    }}
                    QWidget:hover {{
                        background-color: #40E0D0;
                    }}
                """)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(10, 8, 10, 8)
                
                # Radio button for selection
                radio = QRadioButton(f"📂 {s['session_id']}")
                radio.setStyleSheet("font-size: 13px; background-color: transparent;")
                radio.setProperty("session_id", s['session_id'])
                if i == 0:
                    radio.setChecked(True)
                    selected_session[0] = s['session_id']
                radio.toggled.connect(lambda checked, sid=s['session_id']: 
                    selected_session.__setitem__(0, sid) if checked else None)
                button_group.addButton(radio)
                row_layout.addWidget(radio)
                
                row_layout.addStretch()
                
                # Delete button
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(32, 32)
                delete_btn.setToolTip(f"Delete session '{s['session_id']}'")
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ModernStyle.ERROR};
                        border: none;
                        border-radius: 5px;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: #c73e54;
                    }}
                """)
                delete_btn.clicked.connect(lambda _, sid=s['session_id']: delete_session(sid))
                row_layout.addWidget(delete_btn)
                
                session_layout.addWidget(row)
            
            session_layout.addStretch()
            scroll_area.setWidget(session_container)
            layout.addWidget(scroll_area)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            add_btn = QPushButton("Add New Session")
            add_btn.setStyleSheet(f"background-color: {ModernStyle.SUCCESS}; color: #FFFFFF; padding: 10px; font-weight: bold;")
            add_btn.clicked.connect(lambda: choice_dialog.done(1))  # 1 = add new
            btn_layout.addWidget(add_btn)
            
            load_btn = QPushButton("Load Selected")
            load_btn.setStyleSheet(f"background-color: {ModernStyle.PRIMARY}; color: #FFFFFF; padding: 10px; font-weight: bold;")
            load_btn.clicked.connect(lambda: choice_dialog.done(2))  # 2 = load
            btn_layout.addWidget(load_btn)
            
            delete_selected_btn = QPushButton("Delete Selected")
            delete_selected_btn.setStyleSheet(f"background-color: {ModernStyle.ERROR}; color: #FFFFFF; padding: 10px; font-weight: bold;")
            delete_selected_btn.clicked.connect(lambda: delete_session(selected_session[0]) if selected_session[0] else None)
            btn_layout.addWidget(delete_selected_btn)
            
            delete_proj_btn = QPushButton("Delete Project")
            delete_proj_btn.setStyleSheet(f"background-color: #8B0000; color: #FFFFFF; padding: 10px; font-weight: bold;")
            delete_proj_btn.clicked.connect(delete_entire_project)
            btn_layout.addWidget(delete_proj_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(choice_dialog.reject)
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
            
            result = choice_dialog.exec_()
            
            if result == 1:  # Add new session
                dialog = AddSessionDialog(self.project_manager, subject_id, self)
                if dialog.exec_() == dialog.Accepted:
                    session_id = dialog.get_session_id()
                    if session_id:
                        self.project_selected.emit(subject_id, session_id)
                        self.refresh_stats()
            elif result == 2:  # Load selected
                if selected_session[0]:
                    self.select_project(subject_id, selected_session[0])
            elif result == 3:  # Session was deleted, refresh and reopen
                self.refresh_stats()
                # Reopen dialog if there are remaining sessions
                remaining_sessions = self.project_manager.get_sessions(subject_id)
                if remaining_sessions:
                    self.on_subject_clicked(subject_id)
        else:
            # No sessions yet - open add session dialog directly
            dialog = AddSessionDialog(self.project_manager, subject_id, self)
            if dialog.exec_() == dialog.Accepted:
                session_id = dialog.get_session_id()
                if session_id:
                    self.project_selected.emit(subject_id, session_id)
                    self.refresh_stats()
    
    def select_project(self, subject_id: str, session_id: str = None):
        """Select and load a project with optional session."""
        success, msg, metadata = self.project_manager.load_project(subject_id, session_id)
        if success:
            # Use provided session or get current session from metadata
            if not session_id:
                sessions = self.project_manager.get_sessions(subject_id)
                if sessions:
                    session_id = sessions[0].get("session_id", "default")
                else:
                    session_id = "default"
            
            self.project_selected.emit(subject_id, session_id)
        else:
            QMessageBox.warning(self, "Error", msg)
            
    def on_load_project(self):
        """Handle load project click - show subject selection."""
        subjects = self.project_manager.get_existing_subjects()
        
        if not subjects:
            QMessageBox.information(self, "Info", "No existing subjects found")
            return
        
        subject, ok = QInputDialog.getItem(
            self, "Select Subject", "Choose a subject:", subjects, 0, False
        )
        
        if ok and subject:
            self.on_subject_clicked(subject)
            
    def on_delete_project(self):
        """Handle delete project click."""
        from .project_dialogs import DeleteProjectDialog
        
        dialog = DeleteProjectDialog(self.project_manager, self)
        dialog.exec_()
        self.refresh_stats()
