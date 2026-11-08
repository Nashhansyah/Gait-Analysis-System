"""
Signal Preprocessing Module
===========================
Cleans and prepares pose signals for gait analysis.

Pipeline Tahapan:
1. Confidence Filtering - Menandai keypoint dengan confidence rendah sebagai NaN
2. Gap Filling - Mengisi celah data dengan interpolasi linier
3. Savitzky-Golay Filter - Untuk deteksi gait event (preserve peaks)
4. Butterworth Low-Pass Filter - Untuk analisis parameter gait
"""

import os
import json
import numpy as np
from scipy import signal as scipy_signal
from scipy.signal import savgol_filter, medfilt
from scipy.interpolate import interp1d
from typing import Dict, List, Tuple, Optional
import yaml


class SignalPreprocessor:
    """
    Handles signal preprocessing for gait analysis.
    
    This class implements 4-stage preprocessing:
    1. Confidence Filtering
    2. Gap Filling
    3. Savitzky-Golay Filter (for gait events)
    4. Butterworth Low-Pass Filter (for parameters)
    """
    
    # Critical keypoints that require higher confidence threshold
    CRITICAL_KEYPOINTS = ["RAnkle", "LAnkle", "MidHip"]
    
    def __init__(self, config_path: str = "config/signal_config.yaml"):
        """
        Initialize Signal Preprocessor with configuration.
        
        Args:
            config_path: Path to signal processing configuration file
        """
        self.config = self._load_config(config_path)
        
        # Confidence filtering config
        conf_config = self.config.get("confidence_filtering", {})
        self.conf_enabled = conf_config.get("enabled", True)
        self.default_conf_threshold = conf_config.get("default_threshold", 0.3)
        self.critical_conf_thresholds = conf_config.get("critical_keypoints", {
            "RAnkle": 0.4,
            "LAnkle": 0.4,
            "MidHip": 0.4
        })
        
        # Gap filling config
        gap_config = self.config.get("gap_filling", {})
        self.gap_method = gap_config.get("method", "linear")
        self.max_gap_frames = gap_config.get("max_gap_frames", 10)
        self.gap_fallback = gap_config.get("fallback", ["backward", "forward"])
        
        # Savitzky-Golay filter config
        savgol_config = self.config.get("savgol_filter", {})
        self.savgol_enabled = savgol_config.get("enabled", True)
        self.savgol_window = savgol_config.get("window_length", 11)
        self.savgol_polyorder = savgol_config.get("polyorder", 2)
        
        # Butterworth filter config
        butter_config = self.config.get("butterworth_filter", {})
        self.butter_enabled = butter_config.get("enabled", True)
        self.filter_order = butter_config.get("order", 2)
        self.cutoff_freq = butter_config.get("cutoff_freq", 2.5)
        
        # Median filter config (untuk menghilangkan spike)
        median_config = self.config.get("median_filter", {})
        self.median_enabled = median_config.get("enabled", True)
        self.median_kernel = median_config.get("kernel_size", 5)
        
        # Outlier config
        outlier_config = self.config.get("outlier_handling", {})
        self.outlier_enabled = outlier_config.get("enabled", False)
        self.velocity_threshold = outlier_config.get("velocity_threshold", 2000.0)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def preprocess(self, data: Dict, for_gait_events: bool = False) -> Dict:
        """
        Run full preprocessing pipeline on pose data.
        
        Args:
            data: Pose data dictionary from scaling output
            for_gait_events: If True, use Savitzky-Golay filter.
                           If False, use Butterworth filter.
            
        Returns:
            Preprocessed data dictionary
        """
        fps = data.get("metadata", {}).get("fps", 30.0)
        
        # Convert to numpy arrays for processing
        arrays = self._dict_to_arrays(data)
        
        # Tahap 1: Confidence Filtering
        if self.conf_enabled:
            arrays = self._apply_confidence_filter(arrays)
        
        # Tahap 2: Gap Filling (interpolasi)
        arrays = self._apply_gap_filling(arrays)
        
        # Tahap 2.5: Median Filter (menghilangkan spike)
        if self.median_enabled:
            arrays = self._apply_median_filter(arrays)
        
        # Tahap 3 atau 4: Apply appropriate filter
        if for_gait_events and self.savgol_enabled:
            # Tahap 3: Savitzky-Golay Filter (untuk deteksi gait event)
            arrays = self._apply_savgol_filter(arrays, fps)
        elif self.butter_enabled:
            # Tahap 4: Butterworth Low-Pass Filter (untuk parameter gait)
            arrays = self._apply_butterworth_filter(arrays, fps)
        
        # Handle outliers if enabled
        if self.outlier_enabled:
            arrays = self._remove_outliers(arrays, fps)
        
        # Compute derivatives
        arrays = self._compute_derivatives(arrays, fps)
        
        # Convert back to dictionary
        result = self._arrays_to_dict(arrays, data, fps)
        
        return result
    
    def _dict_to_arrays(self, data: Dict) -> Dict[str, np.ndarray]:
        """
        Convert dictionary data to numpy arrays.
        
        Returns:
            Dictionary with joint arrays {joint_name: array(frames, 3)}
        """
        frames = data.get("frames", [])
        n_frames = len(frames)
        
        # Get joint names from first valid frame
        joint_names = []
        for frame in frames:
            joints = frame.get("joints", {})
            if joints:
                joint_names = list(joints.keys())
                break
        
        # Initialize arrays
        arrays = {}
        for joint_name in joint_names:
            arrays[joint_name] = np.full((n_frames, 3), np.nan)  # x, y, conf
        
        # Fill arrays
        for i, frame in enumerate(frames):
            for joint_name in joint_names:
                joint_data = frame.get("joints", {}).get(joint_name, {})
                
                x = joint_data.get("x")
                y = joint_data.get("y")
                conf = joint_data.get("confidence", 0)
                
                if x is not None and y is not None:
                    arrays[joint_name][i, :] = [x, y, conf]
        
        return arrays
    
    def _arrays_to_dict(self, arrays: Dict[str, np.ndarray], 
                        original_data: Dict, fps: float) -> Dict:
        """Convert numpy arrays back to dictionary format."""
        result = {
            "metadata": original_data.get("metadata", {}).copy(),
            "frames": []
        }
        
        result["metadata"]["preprocessed"] = True
        result["metadata"]["filter_cutoff"] = self.cutoff_freq
        result["metadata"]["savgol_window"] = self.savgol_window
        
        # Get frame count from first array
        first_joint = list(arrays.keys())[0]
        n_frames = len(arrays[first_joint])
        
        for i in range(n_frames):
            frame_data = {
                "frame_index": i,
                "time": i / fps,
                "joints": {}
            }
            
            for joint_name, arr in arrays.items():
                if arr.ndim == 2 and arr.shape[1] >= 3:
                    frame_data["joints"][joint_name] = {
                        "x": float(arr[i, 0]) if not np.isnan(arr[i, 0]) else None,
                        "y": float(arr[i, 1]) if not np.isnan(arr[i, 1]) else None,
                        "confidence": float(arr[i, 2]) if not np.isnan(arr[i, 2]) else 0.0
                    }
                    
                    # Add velocity if available
                    if arr.shape[1] >= 5:
                        frame_data["joints"][joint_name]["vx"] = float(arr[i, 3]) if not np.isnan(arr[i, 3]) else None
                        frame_data["joints"][joint_name]["vy"] = float(arr[i, 4]) if not np.isnan(arr[i, 4]) else None
                    
                    # Add acceleration if available
                    if arr.shape[1] >= 7:
                        frame_data["joints"][joint_name]["ax"] = float(arr[i, 5]) if not np.isnan(arr[i, 5]) else None
                        frame_data["joints"][joint_name]["ay"] = float(arr[i, 6]) if not np.isnan(arr[i, 6]) else None
            
            result["frames"].append(frame_data)
        
        return result
    
    def _apply_confidence_filter(self, arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Tahap 1: Confidence Filtering
        
        Keypoint dengan nilai confidence di bawah threshold akan ditandai sebagai NaN.
        - Ankle (RAnkle, LAnkle) dan MidHip: threshold 0.4
        - Keypoint lainnya: threshold 0.3
        """
        result = {}
        
        for joint_name, arr in arrays.items():
            filtered = arr.copy()
            
            # Determine threshold for this joint
            if joint_name in self.critical_conf_thresholds:
                threshold = self.critical_conf_thresholds[joint_name]
            else:
                threshold = self.default_conf_threshold
            
            # Mark low-confidence points as NaN
            for i in range(len(arr)):
                conf = arr[i, 2]  # confidence is in column 2
                if np.isnan(conf) or conf < threshold:
                    filtered[i, 0] = np.nan  # x
                    filtered[i, 1] = np.nan  # y
            
            result[joint_name] = filtered
        
        return result
    
    def _apply_gap_filling(self, arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Tahap 2: Gap Filling (Pengisian Celah Data)
        
        Menggunakan interpolasi linier untuk mengisi celah data:
        - Maksimal 10 frame berturut-turut
        - Jika celah > 10 frame, gunakan backward fill dan forward fill
        """
        result = {}
        
        for joint_name, arr in arrays.items():
            filled = arr.copy()
            
            for coord_idx in [0, 1]:  # x and y
                values = arr[:, coord_idx]
                
                # Find valid indices
                valid_mask = ~np.isnan(values)
                valid_indices = np.where(valid_mask)[0]
                
                if len(valid_indices) < 2:
                    # Not enough valid points, apply fallback fill
                    filled[:, coord_idx] = self._fallback_fill(values)
                    continue
                
                # Process each gap
                interpolated_values = values.copy()
                
                for i in range(len(valid_indices) - 1):
                    start_idx = valid_indices[i]
                    end_idx = valid_indices[i + 1]
                    gap_size = end_idx - start_idx - 1
                    
                    if gap_size > 0:
                        if gap_size <= self.max_gap_frames:
                            # Linear interpolation for gaps <= max_gap_frames
                            start_val = values[start_idx]
                            end_val = values[end_idx]
                            
                            for j in range(start_idx + 1, end_idx):
                                t = (j - start_idx) / (end_idx - start_idx)
                                interpolated_values[j] = start_val + t * (end_val - start_val)
                        else:
                            # Fallback: backward fill from end and forward fill from start
                            mid_point = start_idx + (end_idx - start_idx) // 2
                            
                            # Forward fill from start
                            for j in range(start_idx + 1, mid_point):
                                interpolated_values[j] = values[start_idx]
                            
                            # Backward fill from end
                            for j in range(mid_point, end_idx):
                                interpolated_values[j] = values[end_idx]
                
                # Handle leading NaNs (before first valid point)
                if valid_indices[0] > 0:
                    for j in range(valid_indices[0]):
                        interpolated_values[j] = values[valid_indices[0]]
                
                # Handle trailing NaNs (after last valid point)
                if valid_indices[-1] < len(values) - 1:
                    for j in range(valid_indices[-1] + 1, len(values)):
                        interpolated_values[j] = values[valid_indices[-1]]
                
                filled[:, coord_idx] = interpolated_values
            
            result[joint_name] = filled
        
        return result
    
    def _fallback_fill(self, values: np.ndarray) -> np.ndarray:
        """Apply backward and forward fill as fallback."""
        filled = values.copy()
        
        # Forward fill
        for i in range(1, len(filled)):
            if np.isnan(filled[i]) and not np.isnan(filled[i - 1]):
                filled[i] = filled[i - 1]
        
        # Backward fill for remaining NaNs
        for i in range(len(filled) - 2, -1, -1):
            if np.isnan(filled[i]) and not np.isnan(filled[i + 1]):
                filled[i] = filled[i + 1]
        
        return filled
    
    def _apply_median_filter(self, arrays: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Tahap 2.5: Median Filter (Untuk Menghilangkan Spike)
        
        Median filter sangat efektif untuk menghilangkan spike/outlier karena:
        - Menggantikan setiap nilai dengan median dari nilai-nilai sekitarnya
        - Spike individual otomatis tereliminasi karena bukan median
        - Tidak mempengaruhi sinyal yang smooth
        
        Default kernel_size: 5 (menggunakan 5 sampel untuk menghitung median)
        """
        result = {}
        
        for joint_name, arr in arrays.items():
            filtered = arr.copy()
            
            for coord_idx in [0, 1]:  # x and y
                values = arr[:, coord_idx]
                
                # Skip if all NaN
                if np.all(np.isnan(values)):
                    continue
                
                # Fill NaN temporarily for filtering
                filled = self._fill_nan_for_filter(values)
                
                # Ensure kernel size is odd and valid
                kernel_size = self.median_kernel
                if kernel_size % 2 == 0:
                    kernel_size += 1
                kernel_size = min(kernel_size, len(filled))
                if kernel_size % 2 == 0:
                    kernel_size -= 1
                
                if kernel_size >= 3:
                    # Apply median filter
                    filtered_signal = medfilt(filled, kernel_size)
                    filtered[:, coord_idx] = filtered_signal
                else:
                    filtered[:, coord_idx] = filled
            
            result[joint_name] = filtered
        
        return result
    
    def _apply_savgol_filter(self, arrays: Dict[str, np.ndarray], 
                             fps: float) -> Dict[str, np.ndarray]:
        """
        Tahap 3: Savitzky-Golay Filter (Untuk Deteksi Gait Event)
        
        Mempertahankan fitur penting sinyal seperti peak dan valley.
        - window_length: 11 sampel (atau disesuaikan dengan panjang data)
        - polyorder: 2
        
        Jika Savitzky-Golay gagal, gunakan Butterworth sebagai cadangan.
        """
        result = {}
        
        for joint_name, arr in arrays.items():
            filtered = arr.copy()
            
            for coord_idx in [0, 1]:  # x and y
                values = arr[:, coord_idx]
                n_valid = np.sum(~np.isnan(values))
                
                if n_valid < self.savgol_window:
                    # Data too short for Savitzky-Golay, use Butterworth as fallback
                    filtered[:, coord_idx] = self._butterworth_fallback(values, fps)
                    continue
                
                # Prepare data for filtering (fill NaN temporarily)
                filled = self._fill_nan_for_filter(values)
                
                try:
                    # Adjust window length if needed (must be odd and <= data length)
                    window_length = min(self.savgol_window, len(filled))
                    if window_length % 2 == 0:
                        window_length -= 1
                    
                    if window_length > self.savgol_polyorder:
                        # Apply Savitzky-Golay filter
                        filtered_signal = savgol_filter(filled, window_length, self.savgol_polyorder)
                        
                        # Restore NaN positions for points that were originally NaN
                        # (keep interpolated values since we need continuous signal)
                        filtered[:, coord_idx] = filtered_signal
                    else:
                        filtered[:, coord_idx] = filled
                        
                except Exception:
                    # Fallback to Butterworth if Savitzky-Golay fails
                    filtered[:, coord_idx] = self._butterworth_fallback(values, fps)
            
            result[joint_name] = filtered
        
        return result
    
    def _butterworth_fallback(self, values: np.ndarray, fps: float) -> np.ndarray:
        """Apply Butterworth filter as fallback when Savitzky-Golay fails."""
        filled = self._fill_nan_for_filter(values)
        
        if len(filled) < 10:
            return filled
        
        try:
            nyquist = fps / 2
            normalized_cutoff = self.cutoff_freq / nyquist
            
            if normalized_cutoff >= 1:
                normalized_cutoff = 0.99
            
            b, a = scipy_signal.butter(self.filter_order, normalized_cutoff, btype='low')
            filtered_signal = scipy_signal.filtfilt(b, a, filled)
            return filtered_signal
        except Exception:
            return filled
    
    def _apply_butterworth_filter(self, arrays: Dict[str, np.ndarray], 
                                  fps: float) -> Dict[str, np.ndarray]:
        """
        Tahap 4: Butterworth Low-Pass Filter (Untuk Analisis Parameter Gait)
        
        Menghilangkan komponen noise frekuensi tinggi.
        - cutoff frequency: 2.5 Hz (sesuai karakteristik gait manusia)
        - filter order: 2
        - Menggunakan filtfilt() untuk zero-phase distortion
        """
        result = {}
        
        # Calculate normalized cutoff frequency
        nyquist = fps / 2
        normalized_cutoff = self.cutoff_freq / nyquist
        
        # Ensure cutoff is valid
        if normalized_cutoff >= 1:
            normalized_cutoff = 0.99
        
        # Design filter
        b, a = scipy_signal.butter(self.filter_order, normalized_cutoff, btype='low')
        
        for joint_name, arr in arrays.items():
            filtered = arr.copy()
            
            for coord_idx in [0, 1]:  # x and y
                values = arr[:, coord_idx]
                
                # Only filter if we have enough valid data
                valid_mask = ~np.isnan(values)
                if np.sum(valid_mask) < 10:
                    continue
                
                # Fill NaN temporarily for filtering
                filled = self._fill_nan_for_filter(values)
                
                # Apply filter using filtfilt (zero-phase filtering)
                try:
                    filtered_signal = scipy_signal.filtfilt(b, a, filled)
                    filtered[:, coord_idx] = filtered_signal
                except Exception:
                    # Keep original if filtering fails
                    pass
            
            result[joint_name] = filtered
        
        return result
    
    def _fill_nan_for_filter(self, values: np.ndarray) -> np.ndarray:
        """Fill NaN values for filtering (temporary)."""
        filled = values.copy()
        
        # Forward fill
        for i in range(1, len(filled)):
            if np.isnan(filled[i]):
                filled[i] = filled[i - 1]
        
        # Backward fill for leading NaNs
        for i in range(len(filled) - 2, -1, -1):
            if np.isnan(filled[i]):
                filled[i] = filled[i + 1]
        
        return filled
    
    def _remove_outliers(self, arrays: Dict[str, np.ndarray], 
                         fps: float) -> Dict[str, np.ndarray]:
        """
        Remove outliers based on velocity threshold.
        
        Marks data points as NaN if velocity exceeds physiological limits.
        """
        result = {}
        
        for joint_name, arr in arrays.items():
            cleaned = arr.copy()
            
            # Calculate velocity
            dx = np.diff(arr[:, 0])
            dy = np.diff(arr[:, 1])
            velocity = np.sqrt(dx**2 + dy**2) * fps
            
            # Find outliers
            outlier_mask = velocity > self.velocity_threshold
            
            # Mark outliers as NaN
            for i in np.where(outlier_mask)[0]:
                cleaned[i + 1, :2] = np.nan
            
            result[joint_name] = cleaned
        
        return result
    
    def _compute_derivatives(self, arrays: Dict[str, np.ndarray], 
                             fps: float) -> Dict[str, np.ndarray]:
        """
        Compute velocity and acceleration from position data.
        
        Note: Derivatives are computed AFTER filtering to reduce noise.
        """
        result = {}
        dt = 1.0 / fps
        
        for joint_name, arr in arrays.items():
            n_frames = arr.shape[0]
            
            # Expand array to include derivatives: x, y, conf, vx, vy, ax, ay
            expanded = np.full((n_frames, 7), np.nan)
            expanded[:, :3] = arr[:, :3]  # Copy position and confidence
            
            # Compute velocity (central difference)
            for coord_idx in [0, 1]:
                pos = arr[:, coord_idx]
                vel_idx = coord_idx + 3  # vx=3, vy=4
                
                for i in range(1, n_frames - 1):
                    if not np.isnan(pos[i-1]) and not np.isnan(pos[i+1]):
                        expanded[i, vel_idx] = (pos[i+1] - pos[i-1]) / (2 * dt)
            
            # Compute acceleration from velocity
            for vel_idx, acc_idx in [(3, 5), (4, 6)]:
                vel = expanded[:, vel_idx]
                
                for i in range(1, n_frames - 1):
                    if not np.isnan(vel[i-1]) and not np.isnan(vel[i+1]):
                        expanded[i, acc_idx] = (vel[i+1] - vel[i-1]) / (2 * dt)
            
            result[joint_name] = expanded
        
        return result
    
    def get_signal(self, data: Dict, joint_name: str, 
                   signal_type: str = "x") -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract a specific signal for visualization.
        
        Args:
            data: Preprocessed data dictionary
            joint_name: Name of joint
            signal_type: "x", "y", "vx", "vy", "ax", or "ay"
            
        Returns:
            Tuple of (time_array, signal_array)
        """
        frames = data.get("frames", [])
        fps = data.get("metadata", {}).get("fps", 30.0)
        
        times = []
        values = []
        
        for frame in frames:
            times.append(frame.get("time", frame["frame_index"] / fps))
            joint_data = frame.get("joints", {}).get(joint_name, {})
            values.append(joint_data.get(signal_type))
        
        times = np.array(times)
        values = np.array([v if v is not None else np.nan for v in values])
        
        return times, values
    
    def save_preprocessed_data(self, data: Dict, output_path: str) -> str:
        """
        Save preprocessed data to JSON file.
        
        Args:
            data: Preprocessed data dictionary
            output_path: Path for output file
            
        Returns:
            Path to saved file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return output_path
    
    def load_scaled_data(self, input_path: str) -> Tuple[bool, str, Dict]:
        """
        Load scaled pose data from JSON file.
        
        Args:
            input_path: Path to input JSON file
            
        Returns:
            Tuple of (success, message, data)
        """
        if not os.path.exists(input_path):
            return False, f"File not found: {input_path}", {}
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return True, "Data loaded successfully", data
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {str(e)}", {}
    
    def compare_before_after(self, original: Dict, preprocessed: Dict, 
                             joint_name: str) -> Dict:
        """
        Generate comparison data for before/after visualization.
        
        Args:
            original: Original scaled data
            preprocessed: Preprocessed data
            joint_name: Joint to compare
            
        Returns:
            Dictionary with comparison arrays
        """
        fps = original.get("metadata", {}).get("fps", 30.0)
        
        orig_times, orig_x = self.get_signal(original, joint_name, "x")
        prep_times, prep_x = self.get_signal(preprocessed, joint_name, "x")
        
        orig_times, orig_y = self.get_signal(original, joint_name, "y")
        prep_times, prep_y = self.get_signal(preprocessed, joint_name, "y")
        
        return {
            "times": orig_times.tolist(),
            "original": {"x": orig_x.tolist(), "y": orig_y.tolist()},
            "preprocessed": {"x": prep_x.tolist(), "y": prep_y.tolist()}
        }
    
    def load_openpose_raw(self, openpose_dir: str, fps: float = 30.0) -> Tuple[bool, str, Dict]:
        """
        Load raw OpenPose JSON files and convert to dict format.
        
        This allows preprocessing to work directly on raw OpenPose data
        before scaling, resulting in smoother signals.
        
        Args:
            openpose_dir: Directory containing OpenPose JSON files
            fps: Video frame rate
            
        Returns:
            Tuple of (success, message, data_dict)
        """
        if not os.path.exists(openpose_dir):
            return False, f"Directory not found: {openpose_dir}", {}
        
        # Find all keypoint JSON files
        json_files = sorted([
            f for f in os.listdir(openpose_dir)
            if f.endswith('_keypoints.json')
        ])
        
        if not json_files:
            return False, "No keypoint files found in directory", {}
        
        # Gait-relevant joints (BODY_25 model)
        GAIT_JOINTS = {
            "MidHip": 8,
            "RHip": 9,
            "RKnee": 10,
            "RAnkle": 11,
            "LHip": 12,
            "LKnee": 13,
            "LAnkle": 14
        }
        
        joint_order = list(GAIT_JOINTS.keys())
        n_frames = len(json_files)
        
        result = {
            "metadata": {
                "frame_count": n_frames,
                "fps": fps,
                "duration": n_frames / fps,
                "joints": joint_order,
                "unit": "pixel"  # Important: data is in pixels
            },
            "frames": []
        }
        
        for frame_idx, json_file in enumerate(json_files):
            file_path = os.path.join(openpose_dir, json_file)
            
            frame_data = {
                "frame_index": frame_idx,
                "time": frame_idx / fps,
                "joints": {}
            }
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                people = data.get("people", [])
                
                if people:
                    # Select best person (most complete keypoints)
                    best_person = None
                    best_score = -1
                    
                    for person in people:
                        keypoints = person.get("pose_keypoints_2d", [])
                        score = 0
                        for joint_name, joint_idx in GAIT_JOINTS.items():
                            idx = joint_idx * 3
                            if idx + 2 < len(keypoints) and keypoints[idx + 2] > 0:
                                score += keypoints[idx + 2]
                        if score > best_score:
                            best_score = score
                            best_person = person
                    
                    if best_person:
                        keypoints = best_person.get("pose_keypoints_2d", [])
                        
                        for joint_name, joint_idx in GAIT_JOINTS.items():
                            kp_idx = joint_idx * 3
                            
                            if kp_idx + 2 < len(keypoints):
                                x = keypoints[kp_idx]
                                y = keypoints[kp_idx + 1]
                                conf = keypoints[kp_idx + 2]
                                
                                frame_data["joints"][joint_name] = {
                                    "x": float(x) if conf > 0 else None,
                                    "y": float(y) if conf > 0 else None,
                                    "confidence": float(conf)
                                }
                            else:
                                frame_data["joints"][joint_name] = {
                                    "x": None, "y": None, "confidence": 0.0
                                }
                    else:
                        for joint_name in GAIT_JOINTS.keys():
                            frame_data["joints"][joint_name] = {
                                "x": None, "y": None, "confidence": 0.0
                            }
                else:
                    for joint_name in GAIT_JOINTS.keys():
                        frame_data["joints"][joint_name] = {
                            "x": None, "y": None, "confidence": 0.0
                        }
                        
            except (json.JSONDecodeError, IOError):
                for joint_name in GAIT_JOINTS.keys():
                    frame_data["joints"][joint_name] = {
                        "x": None, "y": None, "confidence": 0.0
                    }
            
            result["frames"].append(frame_data)
        
        return True, f"Loaded {n_frames} frames from OpenPose", result
