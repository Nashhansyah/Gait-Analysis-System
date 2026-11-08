"""
Gait Event & Segmentation Module
================================
Identifies gait events and segments walking into phases.
This module:
- Detects Heel Strike (HS) events
- Detects Toe Off (TO) events
- Constructs gait cycles
- Labels stance and swing phases
- Provides manual correction interface

Uses Savitzky-Golay filter for smoothing reference signals
while preserving peaks and valleys crucial for event detection.
"""

import os
import json
import numpy as np
from scipy import signal as scipy_signal
from scipy.signal import savgol_filter
from typing import Dict, List, Tuple, Optional
import yaml


class GaitEventDetector:
    """
    Handles gait event detection and cycle segmentation.
    
    This class:
    - Computes reference signals
    - Detects heel strikes and toe offs
    - Segments gait cycles
    - Labels phases
    - Supports manual correction
    
    It does NOT:
    - Filter signals (done in preprocessing)
    - Calculate gait parameters
    """
    
    def __init__(self, config_path: str = "config/gait_config.yaml"):
        """
        Initialize Gait Event Detector with configuration.
        
        Args:
            config_path: Path to gait configuration file
        """
        self.config = self._load_config(config_path)
        
        # Extract config values
        cycle_config = self.config.get("gait_cycle", {})
        self.min_cycle_duration = cycle_config.get("min_duration", 0.6)
        self.max_cycle_duration = cycle_config.get("max_duration", 2.0)
        
        hs_config = self.config.get("event_detection", {}).get("heel_strike", {})
        self.min_peak_distance = hs_config.get("min_peak_distance", 15)
        self.min_prominence = hs_config.get("min_prominence", 0.02)
        
        to_config = self.config.get("event_detection", {}).get("toe_off", {})
        self.to_search_start = to_config.get("search_window_start", 0.30)
        self.to_search_end = to_config.get("search_window_end", 0.80)
        
        # Storage
        self.events: Dict = {}
        self.gait_cycles: List = []
        self.phase_labels: Dict = {}
        self.walking_direction: str = "unknown"  # 'left_to_right' or 'right_to_left'
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _detect_walking_direction(self, data: Dict) -> str:
        """
        Detect walking direction based on hip movement over time.
        
        If hip X position decreases over time -> walking right to left.
        If hip X position increases over time -> walking left to right.
        
        Returns:
            'left_to_right' or 'right_to_left'
        """
        frames = data.get("frames", [])
        if len(frames) < 10:
            return "left_to_right"  # Default assumption
        
        hip_x_values = []
        for frame in frames:
            hip = frame.get("joints", {}).get("MidHip", {})
            x = hip.get("x")
            if x is not None:
                hip_x_values.append(x)
        
        if len(hip_x_values) < 10:
            return "left_to_right"
        
        # Compare first and last 20% of values
        n = len(hip_x_values)
        first_quarter = np.nanmean(hip_x_values[:n//5])
        last_quarter = np.nanmean(hip_x_values[-n//5:])
        
        if last_quarter < first_quarter:
            return "right_to_left"  # X decreasing -> walking right to left
        else:
            return "left_to_right"  # X increasing -> walking left to right
    
    def compute_reference_signal(self, data: Dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute ankle position relative to pelvis (MidHip).
        
        This is the primary signal for gait event detection.
        For LEFT-TO-RIGHT walking: Heel Strike at maximum (ankle in front of hip).
        For RIGHT-TO-LEFT walking: Signal is inverted so peaks still represent HS.
        
        Uses Savitzky-Golay filter to smooth signals while preserving
        peaks and valleys crucial for event detection.
        
        Args:
            data: Preprocessed pose data dictionary
            
        Returns:
            Tuple of (times, right_ankle_rel, left_ankle_rel)
        """
        frames = data.get("frames", [])
        fps = data.get("metadata", {}).get("fps", 30.0)
        n_frames = len(frames)
        
        # Detect walking direction
        self.walking_direction = self._detect_walking_direction(data)
        
        times = np.array([f.get("time", i / fps) for i, f in enumerate(frames)])
        r_ankle_rel = np.full(n_frames, np.nan)
        l_ankle_rel = np.full(n_frames, np.nan)
        
        for i, frame in enumerate(frames):
            joints = frame.get("joints", {})
            
            mid_hip = joints.get("MidHip", {})
            r_ankle = joints.get("RAnkle", {})
            l_ankle = joints.get("LAnkle", {})
            
            hip_x = mid_hip.get("x")
            r_x = r_ankle.get("x")
            l_x = l_ankle.get("x")
            
            if hip_x is not None and r_x is not None:
                r_ankle_rel[i] = r_x - hip_x
            
            if hip_x is not None and l_x is not None:
                l_ankle_rel[i] = l_x - hip_x
        
        # CRITICAL: Invert signal for right-to-left walking
        # When walking right-to-left, positive X means ankle is BEHIND hip (Toe Off)
        # and negative X means ankle is IN FRONT of hip (Heel Strike)
        # So we invert the signal to make peaks represent Heel Strike consistently
        if self.walking_direction == "right_to_left":
            r_ankle_rel = -r_ankle_rel
            l_ankle_rel = -l_ankle_rel
        
        # Apply Savitzky-Golay filter to smooth signals while preserving peaks
        r_ankle_rel = self._apply_savgol_to_signal(r_ankle_rel)
        l_ankle_rel = self._apply_savgol_to_signal(l_ankle_rel)
        
        return times, r_ankle_rel, l_ankle_rel
    
    def _apply_savgol_to_signal(self, signal: np.ndarray, 
                                 window_length: int = 11, 
                                 polyorder: int = 2) -> np.ndarray:
        """
        Apply Savitzky-Golay filter to a signal.
        
        Preserves peaks and valleys while reducing noise.
        Falls back to original signal if filtering fails.
        
        Args:
            signal: Input signal array (may contain NaN)
            window_length: Window length for filter (must be odd)
            polyorder: Polynomial order for filter
            
        Returns:
            Filtered signal array
        """
        # Count valid (non-NaN) data points
        valid_mask = ~np.isnan(signal)
        n_valid = np.sum(valid_mask)
        
        if n_valid < window_length:
            # Not enough data for filtering, return original
            return signal
        
        # Fill NaN values temporarily for filtering
        filled = signal.copy()
        valid_indices = np.where(valid_mask)[0]
        
        # Fill leading NaNs
        if valid_indices[0] > 0:
            filled[:valid_indices[0]] = signal[valid_indices[0]]
        
        # Fill trailing NaNs
        if valid_indices[-1] < len(signal) - 1:
            filled[valid_indices[-1] + 1:] = signal[valid_indices[-1]]
        
        # Linear interpolation for gaps
        for i in range(len(valid_indices) - 1):
            start = valid_indices[i]
            end = valid_indices[i + 1]
            if end - start > 1:
                for j in range(start + 1, end):
                    t = (j - start) / (end - start)
                    filled[j] = signal[start] + t * (signal[end] - signal[start])
        
        try:
            # Adjust window length if needed (must be odd and <= data length)
            actual_window = min(window_length, len(filled))
            if actual_window % 2 == 0:
                actual_window -= 1
            
            if actual_window > polyorder:
                filtered = savgol_filter(filled, actual_window, polyorder)
                return filtered
            else:
                return filled
                
        except Exception:
            # Return filled signal if filtering fails
            return filled

    
    def detect_heel_strikes(self, times: np.ndarray, ankle_rel: np.ndarray,
                           side: str) -> List[Dict]:
        """
        Detect Heel Strike events using peak detection.
        
        Heel Strike occurs at maximum anterior position of ankle 
        relative to pelvis (positive peak in sagittal view).
        
        Args:
            times: Time array
            ankle_rel: Ankle position relative to pelvis
            side: "left" or "right"
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        # Handle NaN values
        valid_mask = ~np.isnan(ankle_rel)
        if np.sum(valid_mask) < 10:
            return events
        
        # Fill NaN for peak detection
        filled = ankle_rel.copy()
        filled[~valid_mask] = np.nanmean(ankle_rel)
        
        # Find peaks (maximum anterior position = heel strike)
        peaks, properties = scipy_signal.find_peaks(
            filled,
            distance=self.min_peak_distance,
            prominence=self.min_prominence
        )
        
        for peak_idx in peaks:
            if valid_mask[peak_idx]:
                events.append({
                    "frame": int(peak_idx),
                    "time": float(times[peak_idx]),
                    "event_type": "heel_strike",
                    "side": side,
                    "value": float(ankle_rel[peak_idx]),
                    "auto_detected": True
                })
        
        return events
    
    def detect_toe_offs(self, times: np.ndarray, ankle_rel: np.ndarray,
                        heel_strikes: List[Dict], side: str) -> List[Dict]:
        """
        Detect Toe Off events based on signal pattern within gait cycle.
        
        TO is detected as the minimum point between consecutive heel strikes
        within the search window.
        
        Args:
            times: Time array
            ankle_rel: Ankle position relative to pelvis
            heel_strikes: List of HS events for this side
            side: "left" or "right"
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        if len(heel_strikes) < 2:
            return events
        
        for i in range(len(heel_strikes) - 1):
            hs_start = heel_strikes[i]["frame"]
            hs_end = heel_strikes[i + 1]["frame"]
            
            cycle_length = hs_end - hs_start
            
            # Search window for TO
            search_start = int(hs_start + cycle_length * self.to_search_start)
            search_end = int(hs_start + cycle_length * self.to_search_end)
            
            # Find minimum in search window (posterior position = toe off)
            window = ankle_rel[search_start:search_end + 1]
            
            if len(window) == 0 or np.all(np.isnan(window)):
                continue
            
            # Find minimum (ignoring NaN)
            valid_indices = np.where(~np.isnan(window))[0]
            if len(valid_indices) == 0:
                continue
            
            min_idx = valid_indices[np.argmin(window[valid_indices])]
            to_frame = search_start + min_idx
            
            events.append({
                "frame": int(to_frame),
                "time": float(times[to_frame]),
                "event_type": "toe_off",
                "side": side,
                "value": float(ankle_rel[to_frame]),
                "auto_detected": True
            })
        
        return events
    
    def detect_all_events(self, data: Dict) -> Dict:
        """
        Detect all gait events from preprocessed data.
        
        Args:
            data: Preprocessed pose data dictionary
            
        Returns:
            Dictionary with detected events
        """
        times, r_ankle_rel, l_ankle_rel = self.compute_reference_signal(data)
        
        # Detect heel strikes
        r_hs = self.detect_heel_strikes(times, r_ankle_rel, "right")
        l_hs = self.detect_heel_strikes(times, l_ankle_rel, "left")
        
        # Detect toe offs
        r_to = self.detect_toe_offs(times, r_ankle_rel, r_hs, "right")
        l_to = self.detect_toe_offs(times, l_ankle_rel, l_hs, "left")
        
        self.events = {
            "right": {
                "heel_strikes": r_hs,
                "toe_offs": r_to
            },
            "left": {
                "heel_strikes": l_hs,
                "toe_offs": l_to
            },
            "metadata": {
                "fps": data.get("metadata", {}).get("fps", 30.0),
                "frame_count": len(data.get("frames", [])),
                "walking_direction": self.walking_direction
            }
        }
        
        return self.events
    
    def construct_gait_cycles(self, fps: float = 30.0) -> List[Dict]:
        """
        Construct gait cycles from heel strike events.
        
        A gait cycle is defined as HS → HS of the same leg.
        Cycles outside normal duration limits are included but marked as invalid.
        
        Args:
            fps: Frame rate for duration calculation
            
        Returns:
            List of gait cycle dictionaries
        """
        cycles = []
        
        for side in ["right", "left"]:
            heel_strikes = self.events.get(side, {}).get("heel_strikes", [])
            toe_offs = self.events.get(side, {}).get("toe_offs", [])
            
            for i in range(len(heel_strikes) - 1):
                start_hs = heel_strikes[i]
                end_hs = heel_strikes[i + 1]
                
                duration = end_hs["time"] - start_hs["time"]
                
                # Validate duration - mark invalid instead of skipping
                is_valid = True
                invalid_reason = None
                
                if duration < self.min_cycle_duration:
                    is_valid = False
                    invalid_reason = f"Duration too short ({duration:.2f}s < {self.min_cycle_duration}s)"
                elif duration > self.max_cycle_duration:
                    is_valid = False
                    invalid_reason = f"Duration too long ({duration:.2f}s > {self.max_cycle_duration}s)"
                
                # Find corresponding TO
                to_event = None
                for to in toe_offs:
                    if start_hs["frame"] < to["frame"] < end_hs["frame"]:
                        to_event = to
                        break
                
                cycle = {
                    "cycle_id": len(cycles),
                    "side": side,
                    "start_frame": start_hs["frame"],
                    "end_frame": end_hs["frame"],
                    "start_time": start_hs["time"],
                    "end_time": end_hs["time"],
                    "duration": duration,
                    "heel_strike_start": start_hs,
                    "heel_strike_end": end_hs,
                    "toe_off": to_event,
                    "valid": is_valid,
                    "invalid_reason": invalid_reason
                }
                
                # Calculate stance and swing phases
                if to_event:
                    stance_duration = to_event["time"] - start_hs["time"]
                    swing_duration = end_hs["time"] - to_event["time"]
                    
                    cycle["stance_duration"] = stance_duration
                    cycle["swing_duration"] = swing_duration
                    cycle["stance_ratio"] = stance_duration / duration
                    cycle["swing_ratio"] = swing_duration / duration
                
                cycles.append(cycle)
        
        self.gait_cycles = sorted(cycles, key=lambda c: c["start_frame"])
        return self.gait_cycles
    
    def label_phases(self, n_frames: int) -> Dict[int, Dict]:
        """
        Label each frame with gait phase information using events directly.
        
        This method detects phases based on event sequence, not gait cycles:
        - HS → TO = STANCE (foot on ground)
        - TO → HS = SWING (foot in air)
        
        Works even when complete cycles (HS-TO-HS) are not formed.
        
        Args:
            n_frames: Total number of frames
            
        Returns:
            Dictionary mapping frame index to phase labels
        """
        labels = {}
        
        for frame in range(n_frames):
            labels[frame] = {
                "left": None,
                "right": None
            }
        
        # Label each side using events directly
        for side in ["left", "right"]:
            labels = self._label_side_phases(labels, side, n_frames)
        
        self.phase_labels = labels
        return labels
    
    def _label_side_phases(self, labels: Dict, side: str, n_frames: int) -> Dict:
        """
        Label phases for one side using events directly.
        
        Creates a merged timeline of all events sorted by frame,
        then labels frames between consecutive events.
        
        Args:
            labels: Existing labels dictionary
            side: "left" or "right"
            n_frames: Total number of frames
            
        Returns:
            Updated labels dictionary
        """
        hs_events = self.events.get(side, {}).get("heel_strikes", [])
        to_events = self.events.get(side, {}).get("toe_offs", [])
        
        # Merge all events with their type
        all_events = []
        for hs in hs_events:
            all_events.append({"frame": hs.get("frame", 0), "type": "hs"})
        for to in to_events:
            all_events.append({"frame": to.get("frame", 0), "type": "to"})
        
        # Sort by frame
        all_events.sort(key=lambda e: e["frame"])
        
        if not all_events:
            return labels
        
        # Label frames between consecutive events
        for i in range(len(all_events) - 1):
            current_event = all_events[i]
            next_event = all_events[i + 1]
            
            start_frame = current_event["frame"]
            end_frame = next_event["frame"]
            
            # Determine phase based on event sequence
            if current_event["type"] == "hs" and next_event["type"] == "to":
                # HS → TO = STANCE
                phase = "stance"
            elif current_event["type"] == "to" and next_event["type"] == "hs":
                # TO → HS = SWING
                phase = "swing"
            else:
                # HS → HS or TO → TO (invalid sequence, skip)
                continue
            
            # Label frames in this range
            for f in range(start_frame, end_frame):
                if 0 <= f < n_frames:
                    labels[f][side] = phase
        
        return labels
    
    def add_event(self, frame: int, event_type: str, side: str,
                  times: np.ndarray, ankle_rel: np.ndarray) -> Dict:
        """
        Manually add a gait event.
        
        Args:
            frame: Frame index
            event_type: "heel_strike" or "toe_off"
            side: "left" or "right"
            times: Time array
            ankle_rel: Ankle relative position array
            
        Returns:
            Created event dictionary
        """
        value = ankle_rel[frame] if not np.isnan(ankle_rel[frame]) else 0.0
        
        event = {
            "frame": int(frame),
            "time": float(times[frame]),
            "event_type": event_type,
            "side": side,
            "value": float(value),
            "auto_detected": False
        }
        
        # Add to appropriate list
        event_list_key = "heel_strikes" if event_type == "heel_strike" else "toe_offs"
        
        if side not in self.events:
            self.events[side] = {"heel_strikes": [], "toe_offs": []}
        
        self.events[side][event_list_key].append(event)
        self.events[side][event_list_key].sort(key=lambda e: e["frame"])
        
        return event
    
    def remove_event(self, frame: int, event_type: str, side: str) -> bool:
        """
        Remove a gait event.
        
        Args:
            frame: Frame index
            event_type: "heel_strike" or "toe_off"
            side: "left" or "right"
            
        Returns:
            Success boolean
        """
        event_list_key = "heel_strikes" if event_type == "heel_strike" else "toe_offs"
        
        if side not in self.events:
            return False
        
        events = self.events[side].get(event_list_key, [])
        
        for i, event in enumerate(events):
            if event["frame"] == frame:
                events.pop(i)
                return True
        
        return False
    
    def validate_events(self) -> List[str]:
        """
        Validate event sequence for biomechanical plausibility.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        for side in ["right", "left"]:
            hs_events = self.events.get(side, {}).get("heel_strikes", [])
            to_events = self.events.get(side, {}).get("toe_offs", [])
            
            # Check for alternating pattern between sides
            # (simplified check - in real gait, sides should alternate)
            
            # Check HS-TO sequence within each side
            for i in range(len(hs_events) - 1):
                hs1 = hs_events[i]
                hs2 = hs_events[i + 1]
                
                # Find TO between these HS
                to_between = [to for to in to_events 
                             if hs1["frame"] < to["frame"] < hs2["frame"]]
                
                if len(to_between) == 0:
                    warnings.append(f"Missing TO between HS at frames {hs1['frame']} and {hs2['frame']} ({side})")
                elif len(to_between) > 1:
                    warnings.append(f"Multiple TOs between HS at frames {hs1['frame']} and {hs2['frame']} ({side})")
        
        return warnings
    
    def get_events_for_visualization(self) -> Dict:
        """
        Get events in format suitable for plotting.
        
        Returns:
            Dictionary with event information for visualization
        """
        viz_data = {
            "right_hs": [],
            "right_to": [],
            "left_hs": [],
            "left_to": []
        }
        
        for side in ["right", "left"]:
            for hs in self.events.get(side, {}).get("heel_strikes", []):
                viz_data[f"{side}_hs"].append({
                    "frame": hs["frame"],
                    "time": hs["time"],
                    "value": hs["value"]
                })
            
            for to in self.events.get(side, {}).get("toe_offs", []):
                viz_data[f"{side}_to"].append({
                    "frame": to["frame"],
                    "time": to["time"],
                    "value": to["value"]
                })
        
        return viz_data
    
    def save_events(self, output_path: str) -> str:
        """
        Save events and cycles to JSON file.
        
        Args:
            output_path: Path for output file
            
        Returns:
            Path to saved file
        """
        output_data = {
            "events": self.events,
            "gait_cycles": self.gait_cycles,
            "phase_labels": self.phase_labels,
            "validation": self.validate_events()
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        return output_path
    
    def load_events(self, input_path: str) -> Tuple[bool, str]:
        """
        Load events from JSON file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Tuple of (success, message)
        """
        if not os.path.exists(input_path):
            return False, f"File not found: {input_path}"
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.events = data.get("events", {})
            self.gait_cycles = data.get("gait_cycles", [])
            
            return True, "Events loaded successfully"
            
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {str(e)}"
