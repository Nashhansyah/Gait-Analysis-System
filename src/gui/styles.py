"""
Modern Style Module
====================
Dark theme styling for PyQt5 GUI.
"""


class ModernStyle:
    """Modern dark theme colors and stylesheet."""
    
    # Color palette
    BACKGROUND = "#f8f9fa"
    SURFACE = "#ffffff"
    PRIMARY = "#0d6efd"
    ACCENT = "#dc3545"
    TEXT = "#212529"
    TEXT_SECONDARY = "#6c757d"
    SUCCESS = "#198754"
    WARNING = "#ffc107"
    ERROR = "#dc3545"
    
    # Button colors
    BTN_SWAP = "#fd7e14"  # Orange for swap
    BTN_SUCCESS = "#198754"  # Green for complete/save
    BTN_PRIMARY = "#0d6efd"  # Blue for actions
    BTN_DANGER = "#dc3545"  # Red for delete/cancel
    
    @staticmethod
    def get_stylesheet():
        return f"""
            QMainWindow, QWidget {{
                background-color: {ModernStyle.BACKGROUND};
                color: {ModernStyle.TEXT};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }}
            
            QGroupBox {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: {ModernStyle.ACCENT};
            }}
            
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background-color: #0b5ed7;
            }}
            
            QPushButton:pressed {{
                background-color: #0a58ca;
            }}
            
            QPushButton:disabled {{
                background-color: #e9ecef;
                color: #adb5bd;
            }}
            
            QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton, QDialogButtonBox QPushButton {{
                background-color: {ModernStyle.PRIMARY} !important;
                color: #ffffff !important;
                border: 1px solid #0b5ed7 !important;
                border-radius: 4px !important;
                padding: 6px 16px !important;
                min-height: 18px !important;
            }}

            QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover, QDialogButtonBox QPushButton:hover {{
                background-color: #0b5ed7 !important;
                color: #ffffff !important;
            }}

            QDialog QPushButton:pressed, QMessageBox QPushButton:pressed, QInputDialog QPushButton:pressed, QDialogButtonBox QPushButton:pressed {{
                background-color: #0a58ca !important;
                color: #ffffff !important;
            }}
            
            QPushButton[class="swap"] {{
                background-color: {ModernStyle.BTN_SWAP};
                color: #000000;
            }}
            
            QPushButton[class="success"] {{
                background-color: {ModernStyle.BTN_SUCCESS};
                color: #000000;
            }}
            
            QPushButton[class="danger"] {{
                background-color: {ModernStyle.BTN_DANGER};
            }}
            
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 6px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {ModernStyle.ACCENT};
            }}
            
            QSlider::groove:horizontal {{
                border: 1px solid {ModernStyle.PRIMARY};
                height: 8px;
                background: {ModernStyle.SURFACE};
                border-radius: 4px;
            }}
            
            QSlider::handle:horizontal {{
                background: {ModernStyle.ACCENT};
                border: none;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            
            QSlider::sub-page:horizontal {{
                background: {ModernStyle.PRIMARY};
                border-radius: 4px;
            }}
            
            QListWidget {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 8px;
                padding: 5px;
            }}
            
            QListWidget::item {{
                color: {ModernStyle.TEXT};
                padding: 10px;
                border-radius: 4px;
                margin: 2px;
            }}
            
            QListWidget::item:selected {{
                background-color: {ModernStyle.PRIMARY};
                color: #ffffff;
            }}
            
            QListWidget::item:hover {{
                background-color: #e9ecef;
                color: {ModernStyle.TEXT};
            }}
            
            QTabWidget::pane {{
                background-color: {ModernStyle.SURFACE};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 8px;
            }}
            
            QTabBar::tab {{
                background-color: #e9ecef;
                color: {ModernStyle.TEXT};
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }}
            
            QTabBar::tab:selected {{
                background-color: #40E0D0;
                color: #FFFFFF;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: #E0F7FA;
                color: #000000;
            }}
            
            QTableWidget {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 8px;
                gridline-color: {ModernStyle.PRIMARY};
            }}
            
            QTableWidget::item {{
                color: {ModernStyle.TEXT};
                padding: 8px;
            }}
            
            QHeaderView::section {{
                background-color: {ModernStyle.PRIMARY};
                color: #ffffff;
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
            
            QProgressBar {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 6px;
                height: 25px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {ModernStyle.SUCCESS};
                border-radius: 5px;
            }}
            
            QScrollBar:vertical {{
                background-color: {ModernStyle.SURFACE};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {ModernStyle.PRIMARY};
                border-radius: 6px;
                min-height: 30px;
            }}
            
            QLabel {{
                color: {ModernStyle.TEXT};
            }}
            
            QSplitter::handle {{
                background-color: {ModernStyle.PRIMARY};
            }}
            
            QMenuBar {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                padding: 5px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {ModernStyle.PRIMARY};
                color: #ffffff;
            }}
            
            QMenu {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
            }}
            
            QMenu::item:selected {{
                background-color: {ModernStyle.PRIMARY};
                color: #ffffff;
            }}
        """
