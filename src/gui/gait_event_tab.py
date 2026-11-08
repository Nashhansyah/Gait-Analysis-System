"""
Gait Event Tab Widget
=====================
Interactive gait event detection, visualization, and manual correction.
Features:
- Frame slider for navigation
- Auto detection
- Manual add/delete HS/TO
- Visual markers on plot
"""

import os
import json
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .styles import ModernStyle


class GaitEventTab(QWidget):
    """Tab for gait event detection and manual correction."""
    
    events_complete = pyqtSignal()
    
    def __init__(self, detector, project_manager):
        super().__init__()
        self.detector = detector
        self.project_manager = project_manager
        self.data = None
        self.events = {"right": {"heel_strikes": [], "toe_offs": []},
                       "left": {"heel_strikes": [], "toe_offs": []}}
        self.current_frame = 0
        self.total_frames = 0
        self.times = []
        self.r_ankle = []
        self.l_ankle = []
        self.fps = 30.0
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- LEFT PANEL: Matplotlib Plot Canvas & Slider ---
        left_group = QGroupBox("Kinematic Signal Diagram & Event Markers (HS/TO)")
        left_layout = QVBoxLayout(left_group)
        
        # Visualization canvas
        self.canvas = FigureCanvas(Figure(figsize=(8, 5), facecolor='white'))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.axes = self.canvas.figure.add_subplot(111)
        self.axes.text(0.5, 0.5, 'Ankle vs Hip Movement Graph (Local Peak = HS, Local Valley = TO)\n\nClick "Load Data" to load signal waveforms', 
                       horizontalalignment='center', verticalalignment='center', transform=self.axes.transAxes, color='#888888', fontsize=12)
        self.axes.axis('off')
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)
        left_layout.addWidget(self.canvas, stretch=1)
        
        # Frame slider
        slider_layout = QHBoxLayout()
        slider_indicator = QLabel()
        slider_indicator.setFixedWidth(4)
        slider_indicator.setStyleSheet("background-color: #40E0D0;")
        slider_layout.addWidget(slider_indicator)
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(100)
        self.frame_slider.setValue(0)
        self.frame_slider.valueChanged.connect(self.on_slider_changed)
        self.frame_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999;
                height: 10px;
                background: #f0f0f0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #40E0D0;
                border: none;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
        """)
        slider_layout.addWidget(self.frame_slider)
        left_layout.addLayout(slider_layout)
        main_layout.addWidget(left_group, stretch=3)
        
        # --- RIGHT PANEL: Controls & Action Buttons ---
        right_group = QGroupBox("Gait Event Control Panel")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(12)
        
        # Load & Auto Detect Buttons
        self.load_btn = QPushButton("Load Preprocessed Data")
        self.load_btn.setCursor(Qt.PointingHandCursor)
        self.load_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ModernStyle.PRIMARY};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }}
        """)
        self.load_btn.clicked.connect(self.load_data)
        right_layout.addWidget(self.load_btn)
        
        self.detect_btn = QPushButton("Auto Detect Events (HS/TO)")
        self.detect_btn.setCursor(Qt.PointingHandCursor)
        self.detect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1976D2;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }}
            QPushButton:disabled {{
                background-color: #B0BEC5;
            }}
        """)
        self.detect_btn.clicked.connect(self.auto_detect)
        self.detect_btn.setEnabled(False)
        right_layout.addWidget(self.detect_btn)
        
        # Frame indicator label
        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px; color: #333333;")
        right_layout.addWidget(self.frame_label)
        
        # Event Editing Section
        edit_group = QGroupBox("Manual Event Correction")
        edit_layout = QVBoxLayout(edit_group)
        edit_layout.setSpacing(6)
        
        # Add HS buttons
        hs_layout = QHBoxLayout()
        self.add_hs_left_btn = QPushButton("Add HS Left")
        self.add_hs_left_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.add_hs_left_btn.clicked.connect(lambda: self.add_event("left", "heel_strike"))
        self.add_hs_left_btn.setEnabled(False)
        hs_layout.addWidget(self.add_hs_left_btn)
        
        self.add_hs_right_btn = QPushButton("Add HS Right")
        self.add_hs_right_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.add_hs_right_btn.clicked.connect(lambda: self.add_event("right", "heel_strike"))
        self.add_hs_right_btn.setEnabled(False)
        hs_layout.addWidget(self.add_hs_right_btn)
        edit_layout.addLayout(hs_layout)
        
        # Add TO buttons
        to_layout = QHBoxLayout()
        self.add_to_left_btn = QPushButton("Add TO Left")
        self.add_to_left_btn.setStyleSheet("background-color: #03A9F4; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.add_to_left_btn.clicked.connect(lambda: self.add_event("left", "toe_off"))
        self.add_to_left_btn.setEnabled(False)
        to_layout.addWidget(self.add_to_left_btn)
        
        self.add_to_right_btn = QPushButton("Add TO Right")
        self.add_to_right_btn.setStyleSheet("background-color: #8BC34A; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.add_to_right_btn.clicked.connect(lambda: self.add_event("right", "toe_off"))
        self.add_to_right_btn.setEnabled(False)
        to_layout.addWidget(self.add_to_right_btn)
        edit_layout.addLayout(to_layout)
        
        # Delete button
        self.delete_btn = QPushButton("Delete Event at Frame")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #E53935;
                color: white;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_event_at_current_frame)
        self.delete_btn.setEnabled(False)
        edit_layout.addWidget(self.delete_btn)
        
        right_layout.addWidget(edit_group)
        
        # Save & Proceed button
        self.save_btn = QPushButton("Confirm Events & Proceed")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #40E0D0;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #35C4B5;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
            }
        """)
        self.save_btn.clicked.connect(self.save_and_complete)
        self.save_btn.setEnabled(False)
        right_layout.addWidget(self.save_btn)
        
        # Status Label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; padding: 4px;")
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()
        main_layout.addWidget(right_group, stretch=2)
        
        # Hidden table for internal tracking (not displayed)
        self.events_table = QTableWidget()
        self.events_table.setVisible(False)
        
    def load_data(self):
        """Load corrected pose data."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            QMessageBox.warning(self, "Warning", "No project loaded")
            return
        
        # Load from correction_legid (after scaling and correction) - session-aware
        input_path = self.project_manager.find_output_file(subject_id, "correction_legid", session_id)
        
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Corrected data not found.\nPlease complete L/R Correction first.")
            return
        
        with open(input_path, 'r') as f:
            self.data = json.load(f)
        
        # Compute reference signals
        self.times, self.r_ankle, self.l_ankle = self.compute_reference_signal()
        self.total_frames = len(self.times)
        self.fps = self.data.get("metadata", {}).get("fps", 30.0)
        
        # Update slider
        self.frame_slider.setMaximum(self.total_frames - 1)
        self.frame_slider.setValue(0)
        
        # Enable buttons
        self.detect_btn.setEnabled(True)
        self.add_hs_left_btn.setEnabled(True)
        self.add_hs_right_btn.setEnabled(True)
        self.add_to_left_btn.setEnabled(True)
        self.add_to_right_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        # Plot
        self.plot_events()
        self.update_frame_label()
        
        self.status_label.setText(f"✓ Loaded {self.total_frames} frames")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
    def compute_reference_signal(self):
        """Compute ankle position relative to pelvis."""
        frames = self.data.get("frames", [])
        
        times = []
        r_ankle = []
        l_ankle = []
        
        for frame in frames:
            times.append(frame.get("time", 0))
            joints = frame.get("joints", {})
            
            mid_hip = joints.get("MidHip", {})
            r_ank = joints.get("RAnkle", {})
            l_ank = joints.get("LAnkle", {})
            
            mid_x = mid_hip.get("x", 0) or 0
            r_x = r_ank.get("x", 0) or 0
            l_x = l_ank.get("x", 0) or 0
            
            r_ankle.append(r_x - mid_x)
            l_ankle.append(l_x - mid_x)
        
        return np.array(times), np.array(r_ankle), np.array(l_ankle)
    
    def auto_detect(self):
        """Run automatic event detection."""
        if self.data is None:
            return
        
        # Use detector to find events
        self.events = self.detector.detect_all_events(self.data)
        self.detector.construct_gait_cycles(self.fps)
        
        # Plot and update table
        self.plot_events()
        self.update_events_table()
        
        n_hs = (len(self.events.get("right", {}).get("heel_strikes", [])) + 
                len(self.events.get("left", {}).get("heel_strikes", [])))
        n_to = (len(self.events.get("right", {}).get("toe_offs", [])) + 
                len(self.events.get("left", {}).get("toe_offs", [])))
        
        self.status_label.setText(f"✓ Detected {n_hs} HS, {n_to} TO")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
    def plot_events(self):
        """Plot ankle trajectories with event markers."""
        self.axes.clear()
        
        if len(self.times) == 0:
            return
        
        # Convert times to frames for x-axis
        frames = np.arange(len(self.times))
        
        # Plot trajectories
        self.axes.plot(frames, self.l_ankle, 'b-', linewidth=1.5, label='Ankle Kiri (L)')
        self.axes.plot(frames, self.r_ankle, 'r-', linewidth=1.5, label='Ankle Kanan (R)')
        
        # Current frame indicator
        self.axes.axvline(self.current_frame, color='gray', linestyle=':', linewidth=2, alpha=0.8)
        
        # Current frame points
        if self.current_frame < len(self.r_ankle):
            self.axes.plot(self.current_frame, self.r_ankle[self.current_frame], 
                          'ro', markersize=10, zorder=5)
            self.axes.plot(self.current_frame, self.l_ankle[self.current_frame], 
                          'bo', markersize=10, zorder=5)
        
        # Event markers with distinct shapes and colors
        # HS Left = Blue circle with down arrow (▼)
        # HS Right = Red circle with down arrow (▼)  
        # TO Left = Cyan triangle up (▲)
        # TO Right = Orange triangle up (▲)
        
        hs_left_plotted = False
        hs_right_plotted = False
        to_left_plotted = False
        to_right_plotted = False
        
        # Plot HS Left - Blue down triangle
        for hs in self.events.get("left", {}).get("heel_strikes", []):
            frame = hs.get("frame", 0)
            if frame < len(self.l_ankle):
                y = self.l_ankle[frame]
                if not hs_left_plotted:
                    self.axes.plot(frame, y, 'v', color='#2196F3', markersize=14, 
                                  markeredgecolor='black', markeredgewidth=1.5,
                                  label='▼ HS Left', zorder=10)
                    hs_left_plotted = True
                else:
                    self.axes.plot(frame, y, 'v', color='#2196F3', markersize=14, 
                                  markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                # Vertical line
                self.axes.axvline(frame, color='#2196F3', linestyle='--', alpha=0.5, linewidth=1)
        
        # Plot HS Right - Red down triangle
        for hs in self.events.get("right", {}).get("heel_strikes", []):
            frame = hs.get("frame", 0)
            if frame < len(self.r_ankle):
                y = self.r_ankle[frame]
                if not hs_right_plotted:
                    self.axes.plot(frame, y, 'v', color='#F44336', markersize=14, 
                                  markeredgecolor='black', markeredgewidth=1.5,
                                  label='▼ HS Right', zorder=10)
                    hs_right_plotted = True
                else:
                    self.axes.plot(frame, y, 'v', color='#F44336', markersize=14, 
                                  markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                self.axes.axvline(frame, color='#F44336', linestyle='--', alpha=0.5, linewidth=1)
        
        # Plot TO Left - Cyan up triangle
        for to in self.events.get("left", {}).get("toe_offs", []):
            frame = to.get("frame", 0)
            if frame < len(self.l_ankle):
                y = self.l_ankle[frame]
                if not to_left_plotted:
                    self.axes.plot(frame, y, '^', color='#00BCD4', markersize=12, 
                                  markeredgecolor='black', markeredgewidth=1.5,
                                  label='▲ TO Left', zorder=10)
                    to_left_plotted = True
                else:
                    self.axes.plot(frame, y, '^', color='#00BCD4', markersize=12, 
                                  markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                self.axes.axvline(frame, color='#00BCD4', linestyle=':', alpha=0.4, linewidth=1)
        
        # Plot TO Right - Orange up triangle
        for to in self.events.get("right", {}).get("toe_offs", []):
            frame = to.get("frame", 0)
            if frame < len(self.r_ankle):
                y = self.r_ankle[frame]
                if not to_right_plotted:
                    self.axes.plot(frame, y, '^', color='#FF9800', markersize=12, 
                                  markeredgecolor='black', markeredgewidth=1.5,
                                  label='▲ TO Right', zorder=10)
                    to_right_plotted = True
                else:
                    self.axes.plot(frame, y, '^', color='#FF9800', markersize=12, 
                                  markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                self.axes.axvline(frame, color='#FF9800', linestyle=':', alpha=0.4, linewidth=1)
        
        # Styling
        self.axes.set_xlabel('Frame', fontsize=12)
        self.axes.set_ylabel('Posisi X Relatif (px)', fontsize=12)
        self.axes.set_title(f'Visualisasi Gait Events (HS/TO) - Frame Aktif: {self.current_frame}', 
                           fontsize=14)
        self.axes.legend(loc='upper right', fontsize=9, ncol=2)
        self.axes.grid(True, alpha=0.3)
        self.axes.set_facecolor('white')
        
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        
    def on_slider_changed(self, value):
        """Handle frame slider change."""
        self.current_frame = value
        self.update_frame_label()
        self.update_delete_button_state()
        self.plot_events()
        
    def update_frame_label(self):
        """Update frame counter label."""
        time_s = self.current_frame / self.fps if self.fps > 0 else 0
        self.frame_label.setText(f"Frame: {self.current_frame} / {self.total_frames - 1} ({time_s:.2f}s)")
        
    def on_plot_click(self, event):
        """Handle click on plot for quick navigation."""
        if event.inaxes != self.axes:
            return
        
        if event.xdata is not None:
            frame = int(round(event.xdata))
            frame = max(0, min(frame, self.total_frames - 1))
            self.frame_slider.setValue(frame)
            
    def add_event(self, side: str, event_type: str):
        """Add an event at current frame."""
        frame = self.current_frame
        time = frame / self.fps if self.fps > 0 else 0
        
        event = {"frame": frame, "time": time}
        
        if event_type == "heel_strike":
            # Check if already exists
            existing = self.events.get(side, {}).get("heel_strikes", [])
            if any(e["frame"] == frame for e in existing):
                QMessageBox.warning(self, "Warning", f"HS already exists at frame {frame}")
                return
            
            if side not in self.events:
                self.events[side] = {"heel_strikes": [], "toe_offs": []}
            self.events[side]["heel_strikes"].append(event)
            self.events[side]["heel_strikes"].sort(key=lambda x: x["frame"])
            
        else:  # toe_off
            existing = self.events.get(side, {}).get("toe_offs", [])
            if any(e["frame"] == frame for e in existing):
                QMessageBox.warning(self, "Warning", f"TO already exists at frame {frame}")
                return
            
            if side not in self.events:
                self.events[side] = {"heel_strikes": [], "toe_offs": []}
            self.events[side]["toe_offs"].append(event)
            self.events[side]["toe_offs"].sort(key=lambda x: x["frame"])
        
        self.plot_events()
        self.update_events_table()
        self.update_delete_button_state()
        
        event_name = "HS" if event_type == "heel_strike" else "TO"
        self.status_label.setText(f"Added {event_name} {side} at frame {frame}")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
    def get_events_at_frame(self, frame: int) -> list:
        """Get all events at a specific frame."""
        events_at_frame = []
        
        for side in ["right", "left"]:
            for hs in self.events.get(side, {}).get("heel_strikes", []):
                if hs.get("frame") == frame:
                    events_at_frame.append({
                        "frame": frame,
                        "type": "heel_strike",
                        "type_display": "Heel Strike",
                        "side": side,
                        "side_display": side.capitalize()
                    })
            
            for to in self.events.get(side, {}).get("toe_offs", []):
                if to.get("frame") == frame:
                    events_at_frame.append({
                        "frame": frame,
                        "type": "toe_off",
                        "type_display": "Toe Off",
                        "side": side,
                        "side_display": side.capitalize()
                    })
        
        return events_at_frame
    
    def update_delete_button_state(self):
        """Update delete button state based on events at current frame."""
        events_at_frame = self.get_events_at_frame(self.current_frame)
        has_events = len(events_at_frame) > 0
        self.delete_btn.setEnabled(has_events)
        
        if has_events:
            # Update button text to show what will be deleted
            if len(events_at_frame) == 1:
                e = events_at_frame[0]
                self.delete_btn.setText(f"🗑️ Delete {e['type_display']} ({e['side_display']})")
            else:
                self.delete_btn.setText(f"🗑️ Delete ({len(events_at_frame)} events)")
        else:
            self.delete_btn.setText("🗑️ Delete at Frame")
    
    def delete_event_at_current_frame(self):
        """Delete event(s) at the current frame."""
        events_at_frame = self.get_events_at_frame(self.current_frame)
        
        if not events_at_frame:
            return
        
        # If multiple events, show selection dialog
        if len(events_at_frame) > 1:
            from PyQt5.QtWidgets import QInputDialog
            
            options = [f"{e['type_display']} - {e['side_display']}" for e in events_at_frame]
            options.append("All events at this frame")
            
            choice, ok = QInputDialog.getItem(
                self, "Select Event to Delete",
                f"Multiple events at frame {self.current_frame}.\nSelect which to delete:",
                options, 0, False
            )
            
            if not ok:
                return
            
            if choice == "All events at this frame":
                # Delete all events at this frame
                for event in events_at_frame:
                    self._remove_event(event["side"], event["type"], self.current_frame)
                self.status_label.setText(f"Deleted {len(events_at_frame)} events at frame {self.current_frame}")
            else:
                # Delete specific event
                idx = options.index(choice)
                event = events_at_frame[idx]
                self._remove_event(event["side"], event["type"], self.current_frame)
                self.status_label.setText(f"Deleted {event['type_display']} ({event['side_display']}) at frame {self.current_frame}")
        else:
            # Single event - delete directly
            event = events_at_frame[0]
            self._remove_event(event["side"], event["type"], self.current_frame)
            self.status_label.setText(f"Deleted {event['type_display']} ({event['side_display']}) at frame {self.current_frame}")
        
        self.status_label.setStyleSheet(f"color: {ModernStyle.WARNING};")
        self.plot_events()
        self.update_events_table()
        self.update_delete_button_state()
    
    def _remove_event(self, side: str, event_type: str, frame: int):
        """Remove a specific event."""
        if event_type == "heel_strike":
            events_list = self.events.get(side, {}).get("heel_strikes", [])
            self.events[side]["heel_strikes"] = [e for e in events_list if e.get("frame") != frame]
        else:
            events_list = self.events.get(side, {}).get("toe_offs", [])
            self.events[side]["toe_offs"] = [e for e in events_list if e.get("frame") != frame]
    
    def on_event_selected(self):
        """Handle event selection in table (kept for compatibility)."""
        pass
    
    def delete_selected_event(self):
        """Delete selected event (redirects to frame-based delete)."""
        self.delete_event_at_current_frame()
        
    def update_events_table(self):
        """Update the events table."""
        all_events = []
        
        for side in ["right", "left"]:
            for hs in self.events.get(side, {}).get("heel_strikes", []):
                all_events.append({
                    "frame": hs["frame"],
                    "time": hs["time"],
                    "type": "Heel Strike",
                    "side": side.capitalize()
                })
            for to in self.events.get(side, {}).get("toe_offs", []):
                all_events.append({
                    "frame": to["frame"],
                    "time": to["time"],
                    "type": "Toe Off",
                    "side": side.capitalize()
                })
        
        all_events.sort(key=lambda x: x["frame"])
        
        self.events_table.setRowCount(len(all_events))
        
        for i, event in enumerate(all_events):
            self.events_table.setItem(i, 0, QTableWidgetItem(str(event["frame"])))
            self.events_table.setItem(i, 1, QTableWidgetItem(f"{event['time']:.3f}"))
            self.events_table.setItem(i, 2, QTableWidgetItem(event["type"]))
            self.events_table.setItem(i, 3, QTableWidgetItem(event["side"]))
            
    def save_and_complete(self):
        """Save events and mark as complete."""
        subject_id = self.project_manager.current_subject_id
        session_id = self.project_manager.current_session_id
        
        if not subject_id:
            return
        
        # Use session-aware output path
        output_path = self.project_manager.get_output_file_path(
            subject_id, "gait_events", ".json", session_id
        )
        
        # Transfer events to detector and REBUILD gait_cycles
        # This ensures any deleted/added events are reflected in the cycles
        self.detector.events = self.events
        self.detector.construct_gait_cycles(self.fps)  # Rebuild cycles with current events
        
        # Label phases using events directly (works even without complete cycles)
        self.detector.label_phases(self.total_frames)
        
        # Now save (includes phase_labels)
        self.detector.save_events(output_path)
        
        self.status_label.setText("✓ Events saved successfully")
        self.status_label.setStyleSheet(f"color: {ModernStyle.SUCCESS};")
        
        # Update pipeline status
        self.project_manager.update_pipeline_status(subject_id, "gait_event", "completed")
        
        self.events_complete.emit()
        QMessageBox.information(self, "Success", "Gait events saved!")
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Left:
            if self.current_frame > 0:
                self.frame_slider.setValue(self.current_frame - 1)
        elif event.key() == Qt.Key_Right:
            if self.current_frame < self.total_frames - 1:
                self.frame_slider.setValue(self.current_frame + 1)
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_event()
