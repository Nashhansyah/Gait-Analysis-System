"""
Camera Recording Dialog
========================
Dialog for recording video from camera with live preview,
countdown timer with audio cue, and phone camera (IP stream) support.
"""

import os
import tempfile
import time
import winsound
from datetime import datetime
from threading import Thread

import cv2
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont

from .styles import ModernStyle


class VideoThread(QThread):
    """Thread for capturing video frames from camera."""
    
    frame_ready = pyqtSignal(object)  # Emits numpy array (frame)
    connection_failed = pyqtSignal(str)
    connection_success = pyqtSignal(dict)  # Emits camera properties on first frame
    
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.running = False
        self.cap = None
        self._first_frame = True
        
    def run(self):
        """Main thread loop for capturing frames."""
        # Parse source - could be int (local camera) or string (URL)
        if isinstance(self.source, str) and self.source.startswith("http"):
            cap_source = self.source
        else:
            try:
                cap_source = int(self.source)
            except ValueError:
                cap_source = self.source
        
        self.cap = cv2.VideoCapture(cap_source)
        
        if not self.cap.isOpened():
            self.connection_failed.emit(f"Could not connect to camera: {self.source}")
            return
            
        self.running = True
        
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Emit connection success on first frame
                if self._first_frame:
                    self._first_frame = False
                    props = {
                        'fps': self.cap.get(cv2.CAP_PROP_FPS) or 30.0,
                        'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    }
                    self.connection_success.emit(props)
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.01)  # Brief pause if no frame
                
        # Properly release camera
        if self.cap:
            self.cap.release()
            self.cap = None
        
    def stop(self):
        """Stop the video capture thread."""
        self.running = False
        if not self.wait(3000):  # Wait up to 3 seconds
            self.terminate()  # Force terminate if not responding
            self.wait()
        
    def get_properties(self):
        """Get camera properties."""
        if self.cap and self.cap.isOpened():
            return {
                'fps': self.cap.get(cv2.CAP_PROP_FPS) or 30.0,
                'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            }
        return {'fps': 30.0, 'width': 640, 'height': 480}


class CameraRecordingDialog(QDialog):
    """Dialog for recording video from camera with countdown and audio cue."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera Recording")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(ModernStyle.get_stylesheet())
        
        # State variables
        self.video_thread = None
        self.is_connected = False
        self.is_recording = False
        self.recorded_video_path = None
        self.video_writer = None
        self.current_frame = None
        self.recording_start_time = None
        self.frame_count = 0
        self.camera_props = {'fps': 30.0, 'width': 640, 'height': 480}
        self.camera_sources = []
        
        # Timer for duration display
        self.duration_timer = QTimer()
        self.duration_timer.timeout.connect(self._update_duration)
        
        self.setup_ui()
        self._refresh_camera_list()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Camera source selection
        source_group = QGroupBox("Camera Source")
        source_group.setStyleSheet("QGroupBox { font-weight: bold; color: #000000; }")
        source_layout = QFormLayout(source_group)
        
        source_row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_row.addWidget(self.source_combo, 2)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setToolTip("Scan for newly connected USB cameras")
        self.refresh_btn.clicked.connect(self._refresh_camera_list)
        source_row.addWidget(self.refresh_btn)
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("http://192.168.x.x:8080/video")
        self.ip_input.setVisible(False)
        source_row.addWidget(self.ip_input, 2)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect_camera)
        source_row.addWidget(self.connect_btn)
        
        source_layout.addRow("Source:", source_row)
        
        self.connection_status = QLabel("⚪ Not connected")
        self.connection_status.setStyleSheet(f"color: {ModernStyle.TEXT_SECONDARY};")
        source_layout.addRow("Status:", self.connection_status)
        
        layout.addWidget(source_group)
        
        # Video preview area
        preview_group = QGroupBox("Live Preview")
        preview_group.setStyleSheet("QGroupBox { font-weight: bold; color: #000000; }")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("Camera preview will appear here")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setStyleSheet(f"""
            background-color: #000;
            border: 2px solid {ModernStyle.PRIMARY};
            border-radius: 8px;
        """)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # Recording controls
        control_group = QGroupBox("Recording Controls")
        control_group.setStyleSheet("QGroupBox { font-weight: bold; color: #000000; }")
        control_layout = QHBoxLayout(control_group)
        
        self.start_btn = QPushButton("Start Recording")
        self.start_btn.setStyleSheet(f"background-color: {ModernStyle.SUCCESS}; color: #FFFFFF;")
        self.start_btn.clicked.connect(self._start_recording)
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setStyleSheet(f"background-color: {ModernStyle.ERROR}; color: #FFFFFF;")
        self.stop_btn.clicked.connect(self._stop_recording)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        # Recording indicator
        self.rec_indicator = QLabel("⚫")
        self.rec_indicator.setFont(QFont('Segoe UI', 20))
        control_layout.addWidget(self.rec_indicator)
        
        # Duration display
        self.duration_label = QLabel("00:00")
        self.duration_label.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.duration_label.setStyleSheet(f"color: {ModernStyle.TEXT};")
        control_layout.addWidget(self.duration_label)
        
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Recording")
        self.save_btn.setStyleSheet(f"""
            background-color: {ModernStyle.SUCCESS};
            color: #FFFFFF;
            font-weight: bold;
            padding: 15px 30px;
            min-width: 150px;
        """)
        self.save_btn.clicked.connect(self._save_and_close)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(f"""
            background-color: {ModernStyle.ERROR};
            color: #FFFFFF;
            font-weight: bold;
            padding: 15px 30px;
            min-width: 150px;
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def _refresh_camera_list(self):
        """Detect and populate available cameras dynamically."""
        self.source_combo.clear()
        self.camera_sources = []
        
        try:
            from PyQt5.QtMultimedia import QCameraInfo
            cameras = QCameraInfo.availableCameras()
            if cameras:
                for idx, cam in enumerate(cameras):
                    name = cam.description() or f"Camera {idx}"
                    self.source_combo.addItem(f"Camera {idx}: {name}")
                    self.camera_sources.append({"type": "local", "index": idx, "name": name})
            else:
                for idx in range(4):
                    self.source_combo.addItem(f"Local Camera {idx}")
                    self.camera_sources.append({"type": "local", "index": idx, "name": f"Local Camera {idx}"})
        except Exception:
            for idx in range(4):
                self.source_combo.addItem(f"Local Camera {idx}")
                self.camera_sources.append({"type": "local", "index": idx, "name": f"Local Camera {idx}"})

        # Always append IP Camera
        self.source_combo.addItem("IP Camera (Phone)")
        self.camera_sources.append({"type": "ip", "index": None, "name": "IP Camera"})
        
    def _on_source_changed(self, index):
        """Handle camera source selection change."""
        if 0 <= index < len(self.camera_sources):
            is_ip = self.camera_sources[index]["type"] == "ip"
            self.ip_input.setVisible(is_ip)
        
    def _connect_camera(self):
        """Connect to the selected camera source."""
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            
        index = self.source_combo.currentIndex()
        if index < 0 or index >= len(self.camera_sources):
            return
            
        source_info = self.camera_sources[index]
        if source_info["type"] == "local":
            source = str(source_info["index"])
        else:
            source = self.ip_input.text().strip()
            if not source:
                QMessageBox.warning(self, "Error", "Please enter IP camera URL")
                return
                
        self.connection_status.setText("🟡 Connecting...")
        self.connection_status.setStyleSheet(f"color: {ModernStyle.WARNING};")
        
        # Start video thread
        self.video_thread = VideoThread(source)
        self.video_thread.frame_ready.connect(self._on_frame_ready)
        self.video_thread.connection_failed.connect(self._on_connection_failed)
        self.video_thread.connection_success.connect(self._on_connection_success)
        self.video_thread.start()
        
    def _on_connection_success(self, props):
        """Handle successful camera connection (called on first frame)."""
        self.is_connected = True
        self.camera_props = props
        self.connection_status.setText(f"🟢 Connected ({int(props['width'])}x{int(props['height'])} @ {props['fps']:.0f}fps)")
        self.connection_status.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        self.start_btn.setEnabled(True)
        self.connect_btn.setText("Reconnect")
            
    def _on_connection_failed(self, message):
        """Handle camera connection failure."""
        self.is_connected = False
        self.connection_status.setText(f"🔴 {message}")
        self.connection_status.setStyleSheet(f"color: {ModernStyle.ERROR};")
        self.start_btn.setEnabled(False)
        
    def _on_frame_ready(self, frame):
        """Handle new frame from camera."""
        self.current_frame = frame
        
        # Write frame if recording (after countdown)
        if self.is_recording and self.video_writer:
            self.video_writer.write(frame)
            self.frame_count += 1
        
        # Display frame in preview
        self._display_frame(frame)
        
    def _display_frame(self, frame):
        """Display a frame in the preview label."""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Add recording indicator
        if self.is_recording:
            cv2.circle(rgb_frame, (30, 30), 15, (255, 0, 0), -1)  # Red dot
            
        # Convert to QImage
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit preview while maintaining aspect ratio
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.preview_label.setPixmap(scaled_pixmap)
        
    def _start_recording(self):
        """Start the recording process immediately."""
        if not self.is_connected:
            return
            
        # Disable start button, enable stop
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Create temporary file for recording
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recorded_video_path = os.path.join(temp_dir, f"gait_recording_{timestamp}.mp4")
        
        # Play beep to indicate recording started
        Thread(target=lambda: winsound.Beep(1000, 300), daemon=True).start()
        
        # Start recording immediately
        self._begin_actual_recording()
            
    def _begin_actual_recording(self):
        """Begin the actual video recording after countdown."""
        self.is_countdown = False
        self.is_recording = True
        self.frame_count = 0
        self.recording_start_time = datetime.now()
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = self.camera_props['fps']
        width = int(self.camera_props['width'])
        height = int(self.camera_props['height'])
        
        self.video_writer = cv2.VideoWriter(
            self.recorded_video_path, 
            fourcc, 
            fps, 
            (width, height)
        )
        
        # Start duration timer
        self.duration_timer.start(1000)
        
        # Update indicator
        self.rec_indicator.setText("🔴")
        self.rec_indicator.setStyleSheet(f"color: {ModernStyle.ERROR};")
        
    def _update_duration(self):
        """Update the recording duration display."""
        if self.recording_start_time:
            elapsed = (datetime.now() - self.recording_start_time).total_seconds()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")
            
    def _stop_recording(self):
        """Stop the recording."""
        self.is_recording = False
        self.duration_timer.stop()
        
        # Close video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        # Update UI
        self.rec_indicator.setText("⚫")
        self.rec_indicator.setStyleSheet("")
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        
        # Enable save if we have a recording
        if self.recorded_video_path and os.path.exists(self.recorded_video_path):
            file_size = os.path.getsize(self.recorded_video_path)
            if file_size > 0:
                self.save_btn.setEnabled(True)
                self.connection_status.setText(f"🟢 Recording saved ({file_size // 1024} KB)")
            else:
                self.connection_status.setText("🟡 Recording may be empty")
                
    def _save_and_close(self):
        """Save the recording and close dialog."""
        if self.recorded_video_path and os.path.exists(self.recorded_video_path):
            # Stop camera before closing (but keep video path)
            if self.video_thread:
                self.video_thread.stop()
                self.video_thread = None
            self.is_connected = False
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No recording to save")
            
    def get_video_path(self):
        """Get the path to the recorded video."""
        return self.recorded_video_path
        
    def get_video_info(self):
        """Get information about the recorded video."""
        if not self.recorded_video_path:
            return None
            
        return {
            "path": self.recorded_video_path,
            "source": "camera",
            "fps": self.camera_props['fps'],
            "width": self.camera_props['width'],
            "height": self.camera_props['height'],
            "frame_count": self.frame_count,
            "duration": self.frame_count / self.camera_props['fps'] if self.camera_props['fps'] > 0 else 0
        }
        
    def _cleanup(self):
        """Clean up resources before closing."""
        # Stop recording if active
        if self.is_recording:
            self._stop_recording()
        
        # Stop video thread
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
            
        # Stop timer
        self.duration_timer.stop()
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        self.is_connected = False
            
    def reject(self):
        """Handle Cancel button - properly clean up before closing."""
        self._cleanup()
        super().reject()
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        self._cleanup()
        super().closeEvent(event)
