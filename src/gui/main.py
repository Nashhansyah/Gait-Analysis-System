"""
Gait Analysis GUI - Main Application
=====================================
Modern PyQt5 interface with 3 main sections:
1. Dashboard - Project overview and management
2. Analysis - Pipeline stages (Project Input → Gait Parameters)
3. Report - Results visualization
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStackedWidget, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt

# Import styles and widgets
from gui.styles import ModernStyle
from gui.sidebar import Sidebar
from gui.dashboard_tab import DashboardTab
from gui.analysis_tab import AnalysisTab
from gui.report_tab import ReportTab
from gui.rehabilitation_tab import RehabilitationTab

# Import pipeline modules
from project_input.project_input_manager import ProjectInputManager
from openpose.pose_extraction import PoseExtractor
from correction_legid.correction_legid import LegIDCorrector
from scaling.scaling import PoseScaler
from signal_processing.signal_preprocessing import SignalPreprocessor
from gait_event.gait_event_segmentation import GaitEventDetector
from gait_parameter.gait_parameter_extraction import GaitParameterExtractor


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gait Analysis Markerless")
        self.setGeometry(100, 100, 1400, 900)
        
        # Get project root directory (parent of src folder)
        project_root = Path(__file__).parent.parent.parent
        data_path = str(project_root / "data")
        config_path = project_root / "config"
        
        # Initialize pipeline modules with absolute paths
        self.project_manager = ProjectInputManager(data_path)
        self.pose_extractor = PoseExtractor(str(config_path / "openpose_config.yaml"))
        self.corrector = LegIDCorrector()
        self.scaler = PoseScaler()
        self.preprocessor = SignalPreprocessor(str(config_path / "signal_config.yaml"))
        self.event_detector = GaitEventDetector(str(config_path / "gait_config.yaml"))
        self.param_extractor = GaitParameterExtractor()
        
        self.setup_ui()
        self.setup_connections()
        self.create_menu()
        
    def setup_ui(self):
        """Setup the main user interface."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Main content area (stacked widget)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background-color: {ModernStyle.BACKGROUND};")
        
        # Create main tabs
        self.dashboard_tab = DashboardTab(self.project_manager)
        self.analysis_tab = AnalysisTab(
            self.project_manager,
            self.pose_extractor,
            self.corrector,
            self.scaler,
            self.preprocessor,
            self.event_detector,
            self.param_extractor
        )
        self.report_tab = ReportTab(self.project_manager, self.param_extractor)
        self.rehabilitation_tab = RehabilitationTab(self.project_manager)
        
        self.content_stack.addWidget(self.dashboard_tab)
        self.content_stack.addWidget(self.analysis_tab)
        self.content_stack.addWidget(self.report_tab)
        self.content_stack.addWidget(self.rehabilitation_tab)
        
        layout.addWidget(self.content_stack)
        
    def setup_connections(self):
        """Setup signal connections."""
        # Dashboard project_selected -> go to analysis
        self.dashboard_tab.project_selected.connect(self.on_project_loaded)
        
    def create_menu(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                padding: 8px;
                font-size: 13px;
            }}
            QMenuBar::item {{
                padding: 8px 15px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {ModernStyle.PRIMARY};
            }}
            QMenu {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
            }}
            QMenu::item {{
                padding: 8px 30px;
            }}
            QMenu::item:selected {{
                background-color: {ModernStyle.PRIMARY};
            }}
        """)
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Window", self.new_window)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # Top-level navigation buttons
        menubar.addAction("Homepage", lambda: self.on_section_selected(0))
        menubar.addAction("Analysis", lambda: self.on_section_selected(1))
        menubar.addAction("Report", lambda: self.on_section_selected(2))
        menubar.addAction("Monitoring", lambda: self.on_section_selected(3))
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about)
        
    def on_section_selected(self, index: int):
        """Handle section selection in sidebar."""
        self.content_stack.setCurrentIndex(index)
        
        # Refresh dashboard when selected
        if index == 0:
            self.dashboard_tab.refresh_stats()
            
    def on_project_loaded(self, subject_id: str, session_id: str = None):
        """Handle project loaded from dashboard."""
        # Go to analysis tab and load session
        self.content_stack.setCurrentIndex(1)
        self.analysis_tab.load_project(subject_id, session_id)
        
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About",
            "<h2>Gait Analysis Markerless</h2>"
            "<p>OpenPose-based gait analysis system</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Video-based gait analysis</li>"
            "<li>Automatic pose extraction</li>"
            "<li>Gait event detection</li>"
            "<li>Parameter calculation</li>"
            "<li>Report generation</li>"
            "</ul>"
            "<p>Version 1.0.0</p>"
        )
    
    def new_window(self):
        """Open a new application window."""
        new_win = MainWindow()
        new_win.showMaximized()
        # Keep reference to prevent garbage collection
        if not hasattr(self, '_child_windows'):
            self._child_windows = []
        self._child_windows.append(new_win)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(ModernStyle.get_stylesheet())
    
    window = MainWindow()
    window.showMaximized()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
