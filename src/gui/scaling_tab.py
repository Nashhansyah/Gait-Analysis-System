"""
Scaling Tab Widget
==================
Pixel-to-meter scaling with video frame display for reference point selection.
"""

import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QPushButton, QLabel, QDoubleSpinBox, QSlider, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QLocale
from PyQt5.QtGui import QImage, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .styles import ModernStyle


class ScalingTab(QWidget):
    """Tab for scaling with video frame display."""
    
    scaling_complete = pyqtSignal()
    
    def __init__(self, scaler, project_manager):
        super().__init__()
        self.scaler = scaler
        self.project_manager = project_manager
        self.video_capture = None
        self.current_frame = None
        self.total_frames = 0
        self.point_a = None
        self.point_b = None
        self.selecting_point = None  # 'A' or 'B'
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Info label
        info = QLabel(
            "Select two reference points on the video and enter the real-world distance.\n"
            "Click 'Select Point A' then click on the video, then 'Select Point B' and click again."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY}; padding: 10px;")
        layout.addWidget(info)
        
        # Main content layout
        content_layout = QHBoxLayout()
        
        # Left side - Video display
        video_group = QGroupBox("Video Reference")
        video_layout = QVBoxLayout(video_group)
        
        # Video canvas using matplotlib for click handling (100% fit, zero margins)
        self.video_canvas = FigureCanvas(Figure(figsize=(10, 7), facecolor='#1a1a2e'))
        self.video_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_axes = self.video_canvas.figure.add_axes([0, 0, 1, 1])
        self.video_axes.set_facecolor('#1a1a2e')
        self.video_axes.axis('off')
        
        # Connect click event
        self.video_canvas.mpl_connect('button_press_event', self.on_video_click)
        video_layout.addWidget(self.video_canvas, 1, Qt.AlignCenter)
        
        # Frame slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Frame:"))
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(100)
        self.frame_slider.valueChanged.connect(self.on_frame_changed)
        slider_layout.addWidget(self.frame_slider)
        
        self.frame_label = QLabel("0 / 0")
        slider_layout.addWidget(self.frame_label)
        
        video_layout.addLayout(slider_layout)
        
        # Load video button
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.setStyleSheet(f"background-color: {ModernStyle.PRIMARY};")
        self.load_video_btn.clicked.connect(self.load_video)
        video_layout.addWidget(self.load_video_btn)
        
        content_layout.addWidget(video_group, stretch=2)
        
        # Right side - Controls
        controls_group = QGroupBox("Reference Points")
        controls_layout = QVBoxLayout(controls_group)
        
        # Point A selection
        point_a_layout = QHBoxLayout()
        self.select_a_btn = QPushButton("Select Point A")
        self.select_a_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #e94560;
                padding: 10px;
            }}
        """)
        self.select_a_btn.clicked.connect(lambda: self.start_point_selection('A'))
        point_a_layout.addWidget(self.select_a_btn)
        
        self.point_a_label = QLabel("Not set")
        self.point_a_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY};")
        point_a_layout.addWidget(self.point_a_label)
        controls_layout.addLayout(point_a_layout)
        
        # Point B selection
        point_b_layout = QHBoxLayout()
        self.select_b_btn = QPushButton("Select Point B")
        self.select_b_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4ecca3;
                color: #000;
                padding: 10px;
            }}
        """)
        self.select_b_btn.clicked.connect(lambda: self.start_point_selection('B'))
        point_b_layout.addWidget(self.select_b_btn)
        
        self.point_b_label = QLabel("Not set")
        self.point_b_label.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY};")
        point_b_layout.addWidget(self.point_b_label)
        controls_layout.addLayout(point_b_layout)
        
        # Manual input option
        controls_layout.addWidget(QLabel("Or enter coordinates manually:"))
        
        form_layout = QFormLayout()
        
        # Point A manual
        a_coords = QHBoxLayout()
        self.point_a_x = QDoubleSpinBox()
        self.point_a_x.setRange(0, 10000)
        self.point_a_y = QDoubleSpinBox()
        self.point_a_y.setRange(0, 10000)
        a_coords.addWidget(QLabel("X:"))
        a_coords.addWidget(self.point_a_x)
        a_coords.addWidget(QLabel("Y:"))
        a_coords.addWidget(self.point_a_y)
        form_layout.addRow("Point A:", a_coords)
        
        # Point B manual
        b_coords = QHBoxLayout()
        self.point_b_x = QDoubleSpinBox()
        self.point_b_x.setRange(0, 10000)
        self.point_b_y = QDoubleSpinBox()
        self.point_b_y.setRange(0, 10000)
        b_coords.addWidget(QLabel("X:"))
        b_coords.addWidget(self.point_b_x)
        b_coords.addWidget(QLabel("Y:"))
        b_coords.addWidget(self.point_b_y)
        form_layout.addRow("Point B:", b_coords)
        
        # Real distance
        self.real_distance = QDoubleSpinBox()
        self.real_distance.setLocale(QLocale(QLocale.Indonesian, QLocale.Indonesia))  # Use comma as decimal separator
        self.real_distance.setRange(0.01, 100)
        self.real_distance.setValue(1.0)
        self.real_distance.setDecimals(3)
        self.real_distance.setSuffix(" m")
        form_layout.addRow("Real Distance:", self.real_distance)
        
        controls_layout.addLayout(form_layout)
        
        # Compute button
        self.compute_btn = QPushButton("Compute Scale Factor")
        self.compute_btn.setStyleSheet(f"background-color: {ModernStyle.PRIMARY}; padding: 12px;")
        self.compute_btn.clicked.connect(self.compute_scale)
        controls_layout.addWidget(self.compute_btn)
        
        # Result label
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        controls_layout.addWidget(self.result_label)
        
        # Apply button
        self.apply_btn = QPushButton("Apply Scale & Proceed")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #40E0D0;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px;
                font-weight: bold;
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
        self.apply_btn.clicked.connect(self.apply_scaling)
        self.apply_btn.setEnabled(False)
        controls_layout.addWidget(self.apply_btn)
        
        controls_layout.addStretch()
        content_layout.addWidget(controls_group, 1)
        
        layout.addLayout(content_layout)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
    def load_video(self):
        """Load video for frame selection."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "No project loaded")
            return
        
        video_path = self.project_manager.get_video_path(subject_id, session_id)
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "Error", "Video file not found")
            return
        
        self.video_capture = cv2.VideoCapture(video_path)
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.frame_slider.setMaximum(self.total_frames - 1)
        self.frame_slider.setValue(0)
        
        self.show_frame(0)
        self.status_label.setText(f"Video loaded: {w} × {h} px ({self.total_frames} frames)")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-weight: bold;")
        
    def on_frame_changed(self, value):
        """Handle frame slider change."""
        self.show_frame(value)
        self.frame_label.setText(f"{value} / {self.total_frames - 1}")
        
    def show_frame(self, frame_idx):
        """Display a video frame preserving exact aspect ratio without distortion."""
        if self.video_capture is None:
            return
        
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.video_capture.read()
        
        if ret:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_frame = frame_rgb
            
            h, w = frame_rgb.shape[:2]
            video_ar = w / float(h)
            
            # Dynamically fit video canvas width to match exact video aspect ratio
            canvas_h = max(self.video_canvas.height(), 350)
            target_w = int(canvas_h * video_ar)
            if abs(self.video_canvas.maximumWidth() - target_w) > 5:
                self.video_canvas.setFixedWidth(target_w)
            
            self.video_axes.clear()
            self.video_axes.set_position([0, 0, 1, 1])
            self.video_axes.imshow(frame_rgb, aspect='auto')
            self.video_axes.axis('off')
            
            # Draw points if set
            if self.point_a:
                self.video_axes.plot(self.point_a[0], self.point_a[1], 
                                    'ro', markersize=12, label='Point A')
                self.video_axes.annotate('A', self.point_a, fontsize=14, 
                                        color='red', fontweight='bold',
                                        xytext=(10, 10), textcoords='offset points')
            
            if self.point_b:
                self.video_axes.plot(self.point_b[0], self.point_b[1], 
                                    'go', markersize=12, label='Point B')
                self.video_axes.annotate('B', self.point_b, fontsize=14, 
                                        color='green', fontweight='bold',
                                        xytext=(10, 10), textcoords='offset points')
            
            # Draw line between points
            if self.point_a and self.point_b:
                self.video_axes.plot(
                    [self.point_a[0], self.point_b[0]],
                    [self.point_a[1], self.point_b[1]],
                    'y--', linewidth=2
                )
            
            self.video_canvas.draw()
            
    def start_point_selection(self, point):
        """Start selecting a point."""
        self.selecting_point = point
        if point == 'A':
            self.status_label.setText("Click on the video to select Point A")
            self.status_label.setStyleSheet(f"color: {ModernStyle.ACCENT};")
        else:
            self.status_label.setText("Click on the video to select Point B")
            self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
            
    def on_video_click(self, event):
        """Handle click on video."""
        if event.inaxes != self.video_axes:
            return
        
        if self.selecting_point is None:
            return
        
        x, y = event.xdata, event.ydata
        
        if self.selecting_point == 'A':
            self.point_a = (x, y)
            self.point_a_label.setText(f"({x:.0f}, {y:.0f})")
            self.point_a_x.setValue(x)
            self.point_a_y.setValue(y)
        else:
            self.point_b = (x, y)
            self.point_b_label.setText(f"({x:.0f}, {y:.0f})")
            self.point_b_x.setValue(x)
            self.point_b_y.setValue(y)
        
        self.selecting_point = None
        self.status_label.setText("Point selected. Set both points and enter real distance.")
        self.status_label.setStyleSheet(f"color: {ModernStyle.TEXT};")
        
        # Redraw to show the point
        self.show_frame(self.frame_slider.value())
        
    def compute_scale(self):
        """Compute the scale factor."""
        point_a = (self.point_a_x.value(), self.point_a_y.value())
        point_b = (self.point_b_x.value(), self.point_b_y.value())
        real_dist = self.real_distance.value()
        
        success, msg = self.scaler.set_reference_points(point_a, point_b, real_dist)
        
        if not success:
            QMessageBox.warning(self, "Error", msg)
            return
        
        success, msg, scale = self.scaler.compute_scale_factor()
        
        if success:
            self.result_label.setText(f"Scale Factor: {scale:.6f} m/pixel")
            self.result_label.setStyleSheet(f"color: {ModernStyle.SUCCESS}; font-size: 14px; font-weight: bold;")
            self.apply_btn.setEnabled(True)
        else:
            self.result_label.setText(f"Error: {msg}")
            self.result_label.setStyleSheet(f"color: {ModernStyle.ERROR};")
            
    def apply_scaling(self):
        """Apply scaling to pose data."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            return
        
        # NEW: Load from preprocessed_signal (data already filtered in pixels) - session-aware
        input_path = self.project_manager.find_output_file(subject_id, "preprocessed_signal", session_id)
        
        if not input_path:
            QMessageBox.warning(self, "Error", "Preprocessed signal file not found")
            return
        
        success, msg, data = self.scaler.load_pose_data(input_path)
        if not success:
            QMessageBox.warning(self, "Error", f"Load preprocessed data failed: {msg}")
            return
        
        # Apply scaling (pixel -> meter)
        scaled_data = self.scaler.apply_scaling_to_dict(data)
        
        # Use session-aware output path
        output_path = self.project_manager.get_output_file_path(
            subject_id, "scaled_pose", ".json", session_id
        )
        
        self.scaler.save_scaled_data(scaled_data, output_path)
        
        self.status_label.setText(f"✓ Scaling applied (pixels → meters)")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
        # Update pipeline status
        self.project_manager.update_pipeline_status(subject_id, "scaling", "completed")
        
        self.scaling_complete.emit()
        QMessageBox.information(self, "Success", "Scaling applied successfully!")
        
    def showEvent(self, event):
        """Auto load video when tab becomes visible if project is active."""
        super().showEvent(event)
        if self.video_capture is None and self.project_manager.current_subject_id:
            self.load_video()

    def closeEvent(self, event):
        """Release video capture on close."""
        if self.video_capture:
            self.video_capture.release()
        super().closeEvent(event)
