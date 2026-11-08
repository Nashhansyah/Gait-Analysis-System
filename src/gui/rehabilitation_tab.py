"""
Monitoring Tab Widget (Rehabilitation)
======================================
Visualizes gait parameter trends across multiple sessions for progress monitoring.
Uses sub-tabs to separate session data table and parameter visualizations.
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTabWidget,
    QPushButton, QLabel, QComboBox, QTableWidget, QScrollArea,
    QTableWidgetItem, QHeaderView, QMessageBox, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from gui.styles import ModernStyle
from rehabilitation.rehabilitation_logic import RehabilitationLogic

class RehabilitationTab(QWidget):
    """Tab for tracking rehabilitation progress and comparing sessions."""
    
    def __init__(self, project_manager):
        super().__init__()
        self.project_manager = project_manager
        self.logic = RehabilitationLogic(project_manager)
        self.plot_data = None
        self.session_data = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Gait Monitoring")
        title.setStyleSheet(f"""
            font-size: 22px; 
            font-weight: bold; 
            color: #000000;
            padding: 5px 0;
        """)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # Selection Area with better styling
        selection_frame = QFrame()
        selection_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernStyle.SURFACE};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setContentsMargins(15, 12, 15, 12)
        selection_layout.setSpacing(15)
        
        subject_label = QLabel("Subject:")
        subject_label.setStyleSheet(f"color: {ModernStyle.TEXT}; font-size: 13px; font-weight: bold;")
        selection_layout.addWidget(subject_label)
        
        self.subject_combo = QComboBox()
        self.subject_combo.setMinimumWidth(180)
        self.subject_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {ModernStyle.BACKGROUND};
                color: {ModernStyle.TEXT};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
        """)
        selection_layout.addWidget(self.subject_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: {ModernStyle.TEXT};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #1a4a7a;
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_subjects)
        selection_layout.addWidget(self.refresh_btn)
        
        self.analyze_btn = QPushButton("Compare Sessions")
        self.analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.SUCCESS};
                color: #000;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3db892;
            }}
        """)
        self.analyze_btn.clicked.connect(self.analyze_subject)
        selection_layout.addWidget(self.analyze_btn)
        
        selection_layout.addStretch()
        layout.addWidget(selection_frame)
        
        # Sub-tabs for Data and Visualization
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {ModernStyle.BACKGROUND};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 10px;
                margin-top: -1px;
            }}
            QTabBar::tab {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                padding: 12px 35px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                min-width: 150px;
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
        """)
        
        # Tab 1: Session Data
        self.data_tab = self._create_data_tab()
        self.sub_tabs.addTab(self.data_tab, "Session Data")
        
        # Tab 2: Parameter Trends
        self.trends_tab = self._create_trends_tab()
        self.sub_tabs.addTab(self.trends_tab, "Parameter Trends")
        
        layout.addWidget(self.sub_tabs)
        
        # Initial load
        self.refresh_subjects()
        
    def _create_data_tab(self):
        """Create the session data tab with styled table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Info header
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernStyle.PRIMARY};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_icon = QLabel("ℹ️")
        info_icon.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(info_icon)
        
        info_label = QLabel("Summary of all recorded sessions with key gait metrics.")
        info_label.setStyleSheet(f"color: {ModernStyle.TEXT}; font-size: 12px;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        
        layout.addWidget(info_frame)
        
        # Session Table with improved styling
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(10)
        self.session_table.setHorizontalHeaderLabels([
            "Session", "Date", "Steps", "Speed\n(m/s)", "Cadence\n(spm)", 
            "Step Length\n(m)", "L Stance\n(%)", "L Swing\n(%)", "R Stance\n(%)", "R Swing\n(%)"
        ])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.session_table.verticalHeader().setVisible(False)
        self.session_table.setAlternatingRowColors(True)
        self.session_table.setShowGrid(True)
        self.session_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {ModernStyle.SURFACE};
                color: {ModernStyle.TEXT};
                gridline-color: #333;
                border: none;
                border-radius: 8px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QTableWidget::item:alternate {{
                background-color: {ModernStyle.BACKGROUND};
            }}
            QTableWidget::item:selected {{
                background-color: {ModernStyle.ACCENT};
            }}
            QHeaderView::section {{
                background-color: {ModernStyle.PRIMARY};
                color: {ModernStyle.TEXT};
                padding: 12px 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-bottom: 2px solid {ModernStyle.ACCENT};
            }}
        """)
        layout.addWidget(self.session_table)
        
        return widget
        
    def _create_trends_tab(self):
        """Create the parameter trends visualization tab with scroll."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Info header
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ModernStyle.PRIMARY};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        
        info_icon = QLabel("📈")
        info_icon.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(info_icon)
        
        info_label = QLabel("Track how gait parameters change across sessions over time.")
        info_label.setStyleSheet(f"color: {ModernStyle.TEXT}; font-size: 12px;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        
        layout.addWidget(info_frame)
        
        # Scroll Area for Charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {ModernStyle.BACKGROUND};
                border: 1px solid {ModernStyle.PRIMARY};
                border-radius: 8px;
            }}
            QScrollBar:vertical {{
                background-color: {ModernStyle.SURFACE};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {ModernStyle.PRIMARY};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {ModernStyle.ACCENT};
            }}
        """)
        
        # Chart container
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create matplotlib canvas with 2-column layout (4 rows x 2 cols = 8 charts)
        self.trends_canvas = FigureCanvas(Figure(figsize=(14, 20), facecolor='#1a1a2e'))
        self.trends_canvas.figure.patch.set_facecolor('#1a1a2e')
        self.trends_canvas.setMinimumHeight(1000)
        chart_layout.addWidget(self.trends_canvas)
        
        scroll.setWidget(chart_container)
        layout.addWidget(scroll)
        
        return widget
        
    def refresh_subjects(self):
        """Update subject list in combo box."""
        subjects = self.project_manager.get_existing_subjects()
        self.subject_combo.clear()
        self.subject_combo.addItems(subjects)
        
        # Select current project subject if available
        if self.project_manager.current_subject_id:
            idx = self.subject_combo.findText(self.project_manager.current_subject_id)
            if idx >= 0:
                self.subject_combo.setCurrentIndex(idx)
                
    def analyze_subject(self):
        """Collect session data and update all views."""
        subject_id = self.subject_combo.currentText()
        if not subject_id:
            QMessageBox.warning(self, "Warning", "Please select a subject first.")
            return
            
        self.session_data = self.logic.get_subject_sessions_data(subject_id)
        if not self.session_data or len(self.session_data) < 1:
            QMessageBox.information(self, "Info", f"No complete session data for subject '{subject_id}'.\n\nMake sure to run the full analysis pipeline for at least one session.")
            return
            
        self.plot_data = self.logic.prepare_plot_data(self.session_data)
        
        # Update all tabs
        self.update_session_table()
        self.update_trends_charts()
        
    def update_session_table(self):
        """Update the session data table."""
        if not self.session_data:
            return
            
        self.session_table.setRowCount(len(self.session_data))
        
        for i, entry in enumerate(self.session_data):
            params = entry.get("parameters", {})
            
            # Create items with center alignment (per-side ratios)
            items = [
                QTableWidgetItem(entry.get("session_id", "")),
                QTableWidgetItem(entry.get("date", "")[:10]),
                QTableWidgetItem(str(int(params.get('step_count', 0)))),
                QTableWidgetItem(f"{params.get('mean_walking_speed', 0):.3f}"),
                QTableWidgetItem(f"{params.get('mean_cadence', 0):.1f}"),
                QTableWidgetItem(f"{params.get('mean_step_length', 0):.3f}"),
                QTableWidgetItem(f"{params.get('left_stance_ratio', 0):.1%}"),
                QTableWidgetItem(f"{params.get('left_swing_ratio', 0):.1%}"),
                QTableWidgetItem(f"{params.get('right_stance_ratio', 0):.1%}"),
                QTableWidgetItem(f"{params.get('right_swing_ratio', 0):.1%}")
            ]
            
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                self.session_table.setItem(i, col, item)
                
        # Resize rows to content
        self.session_table.resizeRowsToContents()
            
    def update_trends_charts(self):
        """Render trend charts using Matplotlib with improved styling."""
        if not self.plot_data:
            return
            
        self.trends_canvas.figure.clear()
        
        # All 8 parameters from gait parameter calculation (per-side ratios for clinical use)
        params = [
            ("mean_walking_speed", "Walking Speed", "m/s", "#e94560"),
            ("mean_cadence", "Cadence", "steps/min", "#4ecca3"),
            ("mean_stride_length", "Stride Length", "m", "#9b59b6"),
            ("mean_step_length", "Step Length", "cm", "#3498db"),
            # Per-side ratios (clinical standard)
            ("left_stance_ratio", "Left Stance Ratio", "%", "#2196F3"),
            ("left_swing_ratio", "Left Swing Ratio", "%", "#03A9F4"),
            ("right_stance_ratio", "Right Stance Ratio", "%", "#F44336"),
            ("right_swing_ratio", "Right Swing Ratio", "%", "#FF5722"),
        ]
        
        x_labels = self.plot_data["dates"]
        num_sessions = len(x_labels)
        
        for i, (key, title, unit, color) in enumerate(params, 1):
            # Use 2-column grid layout (4 rows x 2 cols)
            ax = self.trends_canvas.figure.add_subplot(4, 2, i)
            values = self.plot_data.get(key, [])
            
            if not values:
                continue
            
            x_positions = range(len(x_labels))
            
            # Plot line and dots with shadow effect
            ax.plot(x_positions, values, marker='o', linestyle='-', linewidth=2.5, 
                   color=color, markersize=10, markeredgecolor='white', markeredgewidth=2)
            
            # Fill area under curve with gradient effect
            ax.fill_between(x_positions, values, alpha=0.15, color=color)
            
            # Styling
            ax.set_title(f"{title} ({unit})", color='white', fontsize=13, fontweight='bold', pad=15)
            ax.set_facecolor('#252540')
            ax.tick_params(colors='#aaa', labelsize=10)
            ax.grid(True, linestyle='--', alpha=0.2, color='#555')
            
            # Set Y-axis limits with padding so data appears in the middle
            min_val = min(values)
            max_val = max(values)
            data_range = max_val - min_val if max_val != min_val else max_val * 0.2
            padding = data_range * 0.4  # 40% padding above and below
            y_min = min_val - padding
            y_max = max_val + padding
            # Ensure y_min is not negative for ratio/speed values
            if min_val >= 0:
                y_min = max(0, y_min)
            ax.set_ylim(y_min, y_max)
            
            # Set x-axis labels
            ax.set_xticks(x_positions)
            ax.set_xticklabels(x_labels, rotation=0, fontsize=9)
            
            # Set spine colors
            for spine in ax.spines.values():
                spine.set_color('#444')
                spine.set_linewidth(0.5)
                
            # Add value labels with background
            for x, y in zip(x_positions, values):
                ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", 
                            xytext=(0, 14), ha='center', color='white', fontsize=10,
                            fontweight='bold',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor=color, 
                                     edgecolor='none', alpha=0.8))
            
            # Add subtle mean reference line
            if len(values) > 1:
                mean_val = sum(values) / len(values)
                ax.axhline(y=mean_val, color='white', linestyle='--', alpha=0.3, linewidth=1)

        self.trends_canvas.figure.tight_layout(pad=3.0, h_pad=4.0)
        self.trends_canvas.draw()
