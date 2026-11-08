"""
Analysis Tab Widget
===================
Container tab with sequential Wizard/Stepper workflow for all pipeline stages.
Supports multi-session analysis.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from .styles import ModernStyle
from .openpose_tab import OpenPoseTab
from .scaling_tab import ScalingTab
from .correction_tab import CorrectionTab
from .preprocessing_tab import PreprocessingTab
from .gait_event_tab import GaitEventTab
from .gait_param_tab import GaitParameterTab


class AnalysisTab(QWidget):
    """Container for all analysis pipeline stages as a unified sequential wizard workflow."""
    
    analysis_complete = pyqtSignal()
    
    STEP_NAMES = [
        "1. OpenPose",
        "2. Preprocessing",
        "3. Scaling",
        "4. Correction",
        "5. Gait Event",
        "6. Parameters"
    ]
    
    def __init__(self, project_manager, pose_extractor, corrector, 
                 scaler, preprocessor, event_detector, param_extractor):
        super().__init__()
        self.project_manager = project_manager
        
        # Store module references
        self.pose_extractor = pose_extractor
        self.corrector = corrector
        self.scaler = scaler
        self.preprocessor = preprocessor
        self.event_detector = event_detector
        self.param_extractor = param_extractor
        
        # Current session tracking
        self.current_subject_id = None
        self.current_session_id = None
        
        self.current_step = 0
        self.step_completed = [False] * len(self.STEP_NAMES)
        self.step_buttons = []
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Top Header Frame
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernStyle.SURFACE};
                border-radius: 10px;
                border: 1px solid {ModernStyle.PRIMARY};
                padding: 10px;
            }}
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(6)
        
        # Title with session indicator
        self.title = QLabel("Gait Analysis Pipeline Workflow")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        header_layout.addWidget(self.title)
        
        # Session info label
        self.session_label = QLabel("Select a subject from Dashboard to begin analysis")
        self.session_label.setStyleSheet(f"font-size: 13px; color: {ModernStyle.TEXT_SECONDARY};")
        header_layout.addWidget(self.session_label)
        
        # --- Stepper Bar ---
        stepper_layout = QHBoxLayout()
        stepper_layout.setSpacing(6)
        stepper_layout.setContentsMargins(0, 5, 0, 0)
        
        for i, name in enumerate(self.STEP_NAMES):
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, idx=i: self.go_to_step(idx))
            stepper_layout.addWidget(btn)
            self.step_buttons.append(btn)
            
            # Arrow indicator between steps
            if i < len(self.STEP_NAMES) - 1:
                arrow = QLabel("➔")
                arrow.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; font-weight: bold; font-size: 14px;")
                arrow.setAlignment(Qt.AlignCenter)
                stepper_layout.addWidget(arrow)
                
        header_layout.addLayout(stepper_layout)
        layout.addWidget(header_frame)
        
        # --- Stacked Widget for Pipeline Pages ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {ModernStyle.BACKGROUND};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 10px;
            }}
        """)
        
        # Create pipeline step pages
        self.openpose_tab = OpenPoseTab(self.pose_extractor, self.project_manager)
        self.preprocessing_tab = PreprocessingTab(self.preprocessor, self.project_manager)
        self.scaling_tab = ScalingTab(self.scaler, self.project_manager)
        self.correction_tab = CorrectionTab(self.corrector, self.project_manager)
        self.gait_event_tab = GaitEventTab(self.event_detector, self.project_manager)
        self.gait_param_tab = GaitParameterTab(self.param_extractor, self.project_manager, self.pose_extractor)
        
        # Add pages to stacked widget in sequential order
        self.stacked_widget.addWidget(self.openpose_tab)         # Index 0
        self.stacked_widget.addWidget(self.preprocessing_tab)    # Index 1
        self.stacked_widget.addWidget(self.scaling_tab)          # Index 2
        self.stacked_widget.addWidget(self.correction_tab)       # Index 3
        self.stacked_widget.addWidget(self.gait_event_tab)       # Index 4
        self.stacked_widget.addWidget(self.gait_param_tab)       # Index 5
        
        layout.addWidget(self.stacked_widget, stretch=1)
        
        # --- Bottom Navigation Bar ---
        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernStyle.SURFACE};
                border-radius: 8px;
                border: 1px solid {ModernStyle.PRIMARY};
                padding: 6px;
            }}
        """)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_prev = QPushButton("Previous Step")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFixedHeight(34)
        self.btn_prev.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 6px;
                padding: 0 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E0F7FA;
            }}
            QPushButton:disabled {{
                background-color: #F5F5F5;
                color: #B0BEC5;
                border-color: #CFD8DC;
            }}
        """)
        self.btn_prev.clicked.connect(self.prev_step)
        nav_layout.addWidget(self.btn_prev)
        
        self.lbl_nav_status = QLabel("Step 1 of 6: 1. OpenPose")
        self.lbl_nav_status.setAlignment(Qt.AlignCenter)
        self.lbl_nav_status.setStyleSheet("font-weight: bold; font-size: 13px; color: #000000;")
        nav_layout.addWidget(self.lbl_nav_status, stretch=1)
        
        self.btn_next = QPushButton("Next Step")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFixedHeight(34)
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: #40E0D0;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #35C4B5;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
                color: #FFFFFF;
            }}
        """)
        self.btn_next.clicked.connect(self.next_step)
        nav_layout.addWidget(self.btn_next)
        
        layout.addWidget(nav_frame)
        
        # Refresh stepper buttons visual state
        self.update_stepper_ui()

    def update_stepper_ui(self):
        """Update visual styling of stepper header buttons and nav bar state."""
        for i, btn in enumerate(self.step_buttons):
            if i == self.current_step:
                # Active step
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #40E0D0;
                        color: #FFFFFF;
                        border: 1px solid #35C4B5;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 0 10px;
                    }
                """)
            elif self.step_completed[i]:
                # Completed step
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        border: 1px solid #A5D6A7;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 0 10px;
                    }
                """)
                btn.setText(self.STEP_NAMES[i])
            else:
                # Pending step
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FAFAFA;
                        color: #616161;
                        border: 1px solid #E0E0E0;
                        border-radius: 6px;
                        font-size: 12px;
                        padding: 0 10px;
                    }
                    QPushButton:hover {
                        background-color: #F0F4F8;
                    }
                """)
                btn.setText(self.STEP_NAMES[i])

        # Enable/Disable previous & next buttons
        self.btn_prev.setEnabled(self.current_step > 0)
        self.btn_next.setEnabled(self.current_step < len(self.STEP_NAMES) - 1)
        
        current_name = self.STEP_NAMES[self.current_step]
        self.lbl_nav_status.setText(f"Step {self.current_step + 1} of 6: {current_name}")

    def go_to_step(self, step_index: int):
        """Navigate directly to a specific step."""
        if 0 <= step_index < len(self.STEP_NAMES):
            self.current_step = step_index
            self.stacked_widget.setCurrentIndex(step_index)
            self.update_stepper_ui()

    def prev_step(self):
        """Go to the previous step in wizard."""
        if self.current_step > 0:
            self.go_to_step(self.current_step - 1)

    def next_step(self):
        """Go to the next step in wizard."""
        if self.current_step < len(self.STEP_NAMES) - 1:
            self.go_to_step(self.current_step + 1)

    def setup_connections(self):
        """Connect completion signals between sequential pipeline stages for auto-advance."""
        # Step 0 (OpenPose) complete -> mark step completed & auto advance to Step 1 (Preprocessing)
        self.openpose_tab.processing_complete.connect(lambda: self._on_stage_completed(0))
        
        # Step 1 (Preprocessing) complete -> mark step completed & auto advance to Step 2 (Scaling)
        self.preprocessing_tab.preprocessing_complete.connect(lambda: self._on_stage_completed(1))
        
        # Step 2 (Scaling) complete -> mark step completed & auto advance to Step 3 (Correction)
        self.scaling_tab.scaling_complete.connect(lambda: self._on_stage_completed(2))
        
        # Step 3 (Correction) complete -> mark step completed & auto advance to Step 4 (Gait Event)
        self.correction_tab.correction_complete.connect(lambda: self._on_stage_completed(3))
        
        # Step 4 (Gait Event) complete -> mark step completed & auto advance to Step 5 (Parameters)
        self.gait_event_tab.events_complete.connect(lambda: self._on_stage_completed(4))

    def _on_stage_completed(self, completed_step_index: int):
        """Handler when a stage completes processing."""
        if 0 <= completed_step_index < len(self.step_completed):
            self.step_completed[completed_step_index] = True
            
        # Automatically advance to next step if not at the final step
        if completed_step_index < len(self.STEP_NAMES) - 1:
            self.go_to_step(completed_step_index + 1)
        else:
            self.update_stepper_ui()
            self.analysis_complete.emit()

    def load_project(self, subject_id: str, session_id: str = None):
        """Load a project with specific session."""
        self.current_subject_id = subject_id
        self.current_session_id = session_id or self.project_manager.DEFAULT_SESSION_ID
        
        # Update session label
        if session_id and session_id != self.project_manager.DEFAULT_SESSION_ID:
            self.session_label.setText(f"📁 Subject: {subject_id}  |  📂 Session: {session_id}")
        else:
            self.session_label.setText(f"📁 Subject: {subject_id}")
        
        # Set session in project manager
        self.project_manager.set_current_session(subject_id, self.current_session_id)
        
        # Reset step progress for new project loading
        self.step_completed = [False] * len(self.STEP_NAMES)
        
        # Go to first step (OpenPose)
        self.go_to_step(0)

    def update_stage_status(self, stage_index: int, status: str):
        """Update visual status of a pipeline stage."""
        if 0 <= stage_index < len(self.step_completed):
            if status == "completed":
                self.step_completed[stage_index] = True
            self.update_stepper_ui()

