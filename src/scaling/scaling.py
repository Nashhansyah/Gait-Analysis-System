"""
Scaling Module
==============
Converts pose coordinates from pixel space to physical units.
This module:
- Accepts two reference points with known real-world distance
- Calculates scale factor
- Applies scaling to all pose time series data
"""

import os
import json
import numpy as np
from typing import Dict, Tuple, Optional
import math


class PoseScaler:
    """
    Handles conversion from pixel coordinates to physical units.
    
    This class only:
    - Validates reference points
    - Computes scale factor
    - Applies scaling to coordinates
    
    It does NOT:
    - Filter signals
    - Interpolate data
    - Extract features
    """
    
    def __init__(self):
        """Initialize the Pose Scaler."""
        self.scale_factor: Optional[float] = None
        self.reference_point_a: Optional[Tuple[float, float]] = None
        self.reference_point_b: Optional[Tuple[float, float]] = None
        self.real_distance: Optional[float] = None
        self.unit: str = "meter"
        
    def set_reference_points(self, point_a: Tuple[float, float],
                             point_b: Tuple[float, float],
                             real_distance: float,
                             unit: str = "meter") -> Tuple[bool, str]:
        """
        Set reference points for scaling calculation.
        
        Args:
            point_a: First reference point (x, y) in pixels
            point_b: Second reference point (x, y) in pixels
            real_distance: Actual distance between points
            unit: Unit of measurement (default: meter)
            
        Returns:
            Tuple of (success, message)
        """
        # Validate points
        if point_a == point_b:
            return False, "Reference points cannot be identical"
        
        if real_distance <= 0:
            return False, "Real distance must be positive"
        
        # Store reference points
        self.reference_point_a = point_a
        self.reference_point_b = point_b
        self.real_distance = real_distance
        self.unit = unit
        
        return True, "Reference points set successfully"
    
    def compute_scale_factor(self) -> Tuple[bool, str, float]:
        """
        Calculate the scale factor from reference points.
        
        Returns:
            Tuple of (success, message, scale_factor)
        """
        if self.reference_point_a is None or self.reference_point_b is None:
            return False, "Reference points not set", 0.0
        
        if self.real_distance is None or self.real_distance <= 0:
            return False, "Real distance not set", 0.0
        
        # Calculate pixel distance
        dx = self.reference_point_b[0] - self.reference_point_a[0]
        dy = self.reference_point_b[1] - self.reference_point_a[1]
        pixel_distance = math.sqrt(dx * dx + dy * dy)
        
        if pixel_distance < 1:
            return False, "Pixel distance too small", 0.0
        
        # Calculate scale factor
        self.scale_factor = self.real_distance / pixel_distance
        
        return True, f"Scale factor: {self.scale_factor:.6f} {self.unit}/pixel", self.scale_factor
    
    def apply_scaling(self, data: np.ndarray) -> np.ndarray:
        """
        Apply scaling to pose time series data.
        
        Args:
            data: Joint data array (frames, joints, 3) where 3 = [x, y, confidence]
            
        Returns:
            Scaled data array (confidence unchanged)
        """
        if self.scale_factor is None:
            # Compute if not already done
            success, _, _ = self.compute_scale_factor()
            if not success:
                return data
        
        scaled_data = data.copy()
        
        # Scale x and y coordinates, keep confidence as is
        scaled_data[:, :, 0] *= self.scale_factor  # x
        scaled_data[:, :, 1] *= self.scale_factor  # y
        # scaled_data[:, :, 2] unchanged (confidence)
        
        return scaled_data
    
    def apply_scaling_to_dict(self, data: Dict) -> Dict:
        """
        Apply scaling to pose data in dictionary format.
        
        Args:
            data: Pose time series dictionary from correction_legid output
            
        Returns:
            Scaled data dictionary
        """
        if self.scale_factor is None:
            success, _, _ = self.compute_scale_factor()
            if not success:
                return data
        
        scaled_data = data.copy()
        
        # Update metadata
        scaled_data["metadata"]["unit"] = self.unit
        scaled_data["metadata"]["scale_factor"] = self.scale_factor
        scaled_data["metadata"]["reference_points"] = {
            "point_a": self.reference_point_a,
            "point_b": self.reference_point_b,
            "real_distance": self.real_distance
        }
        
        # Scale each frame's joint coordinates
        for frame in scaled_data.get("frames", []):
            for joint_name, joint_data in frame.get("joints", {}).items():
                if joint_data.get("x") is not None:
                    joint_data["x"] *= self.scale_factor
                if joint_data.get("y") is not None:
                    joint_data["y"] *= self.scale_factor
        
        return scaled_data
    
    def validate_scaling(self, data: Dict) -> Tuple[bool, str, Dict]:
        """
        Perform sanity checks on scaled data.
        
        Args:
            data: Scaled pose data dictionary
            
        Returns:
            Tuple of (valid, message, validation_info)
        """
        validation_info = {}
        warnings = []
        
        frames = data.get("frames", [])
        if not frames:
            return False, "No frame data", {}
        
        # Calculate some basic metrics
        ankle_positions = []
        step_estimates = []
        
        for frame in frames:
            joints = frame.get("joints", {})
            
            # Get ankle positions
            r_ankle = joints.get("RAnkle", {})
            l_ankle = joints.get("LAnkle", {})
            
            if r_ankle.get("x") is not None and l_ankle.get("x") is not None:
                r_x = r_ankle["x"]
                l_x = l_ankle["x"]
                ankle_positions.append((r_x, l_x))
                
                # Estimate step length from ankle distance
                step_est = abs(r_x - l_x)
                step_estimates.append(step_est)
        
        if step_estimates:
            mean_step = np.mean(step_estimates)
            max_step = np.max(step_estimates)
            
            validation_info["mean_ankle_distance"] = float(mean_step)
            validation_info["max_ankle_distance"] = float(max_step)
            
            # Check for physiologically implausible values
            if mean_step > 2.0:  # > 2 meters average seems wrong
                warnings.append(f"Mean step distance ({mean_step:.2f}m) seems too large")
            if mean_step < 0.05:  # < 5cm seems too small
                warnings.append(f"Mean step distance ({mean_step:.2f}m) seems too small")
            if max_step > 3.0:  # > 3m step impossible
                warnings.append(f"Maximum step distance ({max_step:.2f}m) is implausible")
        
        validation_info["warnings"] = warnings
        
        is_valid = len(warnings) == 0
        message = "Scaling validation passed" if is_valid else f"Warnings: {'; '.join(warnings)}"
        
        return is_valid, message, validation_info
    
    def save_scaled_data(self, data: Dict, output_path: str) -> str:
        """
        Save scaled pose data to JSON file.
        
        Args:
            data: Scaled pose data dictionary
            output_path: Path for output file
            
        Returns:
            Path to saved file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return output_path
    
    def load_pose_data(self, input_path: str) -> Tuple[bool, str, Dict]:
        """
        Load pose data from JSON file.
        
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
    
    def load_openpose_raw_data(self, openpose_dir: str, fps: float = 30.0) -> Tuple[bool, str, Dict]:
        """
        Load raw OpenPose JSON files and convert to dict format.
        
        This method loads directly from OpenPose output directory and converts
        the data into the same format as correction_legid output, so it can be
        used with apply_scaling_to_dict.
        
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
                "unit": "pixel"
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
    
    def get_scaling_info(self) -> Dict:
        """
        Get current scaling configuration.
        
        Returns:
            Dictionary with scaling parameters
        """
        return {
            "reference_point_a": self.reference_point_a,
            "reference_point_b": self.reference_point_b,
            "real_distance": self.real_distance,
            "scale_factor": self.scale_factor,
            "unit": self.unit
        }
    
    def estimate_step_length(self, data: Dict, percentile: int = 90) -> Optional[float]:
        """
        Estimate typical step length from scaled data.
        Useful for sanity checking the scale factor.
        
        Args:
            data: Scaled pose data dictionary
            percentile: Percentile of ankle distances to use
            
        Returns:
            Estimated step length in physical units
        """
        ankle_distances = []
        
        for frame in data.get("frames", []):
            joints = frame.get("joints", {})
            r_ankle = joints.get("RAnkle", {})
            l_ankle = joints.get("LAnkle", {})
            
            if r_ankle.get("x") is not None and l_ankle.get("x") is not None:
                dist = abs(r_ankle["x"] - l_ankle["x"])
                ankle_distances.append(dist)
        
        if ankle_distances:
            return float(np.percentile(ankle_distances, percentile))
        return None
