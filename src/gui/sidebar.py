"""
Sidebar Widget
==============
Navigation sidebar with 3 main sections: Dashboard, Analysis, Report.
Fixed collapsed view with only icons.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal

from .styles import ModernStyle


class Sidebar(QWidget):
    """Navigation sidebar for main sections."""
    
    section_selected = pyqtSignal(int)
    
    SECTIONS = [
        ("Homepage", "⊞", "dashboard"),
        ("Analysis", "⌕", "analysis"),
        ("Report", "▤", "report"),
        ("Monitoring", "∿", "rehabilitation")
    ]
    
    COLLAPSED_WIDTH = 60
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)
        
        # Section list
        self.section_list = QListWidget()
        self.section_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
            }}
            QListWidget::item {{
                padding: 15px 0px;
                border-radius: 10px;
                margin: 5px 3px;
                font-size: 24px;
                color: #000000;
            }}
            QListWidget::item:selected {{
                background-color: #40E0D0;
            }}
            QListWidget::item:hover {{
                background-color: #40E0D0;
            }}
        """)
        
        for name, icon, key in self.SECTIONS:
            item = QListWidgetItem(icon)
            item.setData(Qt.UserRole, key)
            item.setToolTip(name)
            item.setTextAlignment(Qt.AlignCenter)
            self.section_list.addItem(item)
        
        self.section_list.currentRowChanged.connect(self.section_selected.emit)
        self.section_list.setCurrentRow(0)
        layout.addWidget(self.section_list)
        
        layout.addStretch()
        
        # Set fixed width
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        
    def set_current_section(self, index: int):
        """Set the current section by index."""
        self.section_list.setCurrentRow(index)

