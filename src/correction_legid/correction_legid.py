"""
Correction Leg ID Module
========================
Standardizes pose data and ensures left-right consistency.
This module:
- Selects the main subject from multi-person detections
- Filters relevant joints for gait analysis
- Aggregates frame-by-frame data into time series
- Checks and corrects left-right label consistency
"""

import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class LegIDCorrector:
    """
    Handles pose data standardization and left-right consistency correction.
    
    This class only:
    - Selects the primary subject
    - Selects relevant joints
    - Aggregates to time series
    - Corrects left-right labels
    
    It does NOT:
    - Apply scaling
    - Filter signals
    - Detect gait events
    """
    
    # Gait-relevant joints (BODY_25 model)
    GAIT_JOINTS = {
        "Neck": 1,
        "MidHip": 8,
        "RHip": 9,
        "RKnee": 10,
        "RAnkle": 11,
        "LHip": 12,
        "LKnee": 13,
        "LAnkle": 14,
        "LBigToe": 19,
        "LHeel": 21,
        "RBigToe": 22,
        "RHeel": 24
    }
    
    # Paired joints for left-right swap
    PAIRED_JOINTS = [
        ("RHip", "LHip"),
        ("RKnee", "LKnee"),
        ("RAnkle", "LAnkle"),
        ("RBigToe", "LBigToe"),
        ("RHeel", "LHeel")
    ]
    
    def __init__(self):
        """Initialize the Leg ID Corrector."""
        self.raw_data: List[Dict] = []
        self.corrected_data: Dict = {}
        self.swap_log: List[int] = []  # Frames where swap was applied
        self.scaled_data_dict: Dict = {}  # Store loaded scaled data
        self.fps: float = 30.0  # Default FPS
    
    def load_scaled_data(self, input_path: str) -> Tuple[bool, str, int]:
        """
        Load scaled pose data from JSON file.
        
        This method loads scaled_pose JSON output and converts it to the internal
        numpy array format for correction processing.
        
        Args:
            input_path: Path to scaled_pose JSON file
            
        Returns:
            Tuple of (success, message, frame_count)
        """
        if not os.path.exists(input_path):
            return False, f"File not found: {input_path}", 0
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {str(e)}", 0
        
        # Store the dict for later saving
        self.scaled_data_dict = data
        self.fps = data.get("metadata", {}).get("fps", 30.0)
        
        frames = data.get("frames", [])
        if not frames:
            return False, "No frame data found", 0
        
        # Convert dict format to raw_data format (similar to OpenPose raw)
        # This allows existing methods to work
        self.raw_data = []
        
        joint_order = list(self.GAIT_JOINTS.keys())
        
        for frame_data in frames:
            joints = frame_data.get("joints", {})
            
            # Create a fake OpenPose-like structure
            keypoints = [0.0] * 75  # 25 joints * 3 (x, y, conf)
            
            for joint_name, joint_idx in self.GAIT_JOINTS.items():
                joint_info = joints.get(joint_name, {})
                kp_idx = joint_idx * 3
                
                x = joint_info.get("x")
                y = joint_info.get("y")
                conf = joint_info.get("confidence", 0.0)
                
                keypoints[kp_idx] = float(x) if x is not None else 0.0
                keypoints[kp_idx + 1] = float(y) if y is not None else 0.0
                keypoints[kp_idx + 2] = float(conf) if (x is not None and y is not None) else 0.0
            
            self.raw_data.append({
                "people": [{
                    "pose_keypoints_2d": keypoints
                }]
            })
        
        return True, f"Loaded {len(frames)} frames from scaled data", len(frames)
        
    def load_openpose_output(self, openpose_dir: str) -> Tuple[bool, str, int]:
        """
        Load all OpenPose JSON files from directory.
        
        Args:
            openpose_dir: Directory containing JSON keypoint files
            
        Returns:
            Tuple of (success, message, frame_count)
        """
        if not os.path.exists(openpose_dir):
            return False, f"Directory not found: {openpose_dir}", 0
        
        json_files = sorted([
            f for f in os.listdir(openpose_dir)
            if f.endswith('_keypoints.json')
        ])
        
        if not json_files:
            return False, "No keypoint files found", 0
        
        self.raw_data = []
        
        for json_file in json_files:
            file_path = os.path.join(openpose_dir, json_file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.raw_data.append(data)
            except (json.JSONDecodeError, IOError) as e:
                self.raw_data.append({"people": []})
        
        return True, f"Loaded {len(self.raw_data)} frames", len(self.raw_data)
    
    def select_primary_person(self) -> Tuple[bool, str]:
        """
        Select the primary person in multi-person scenarios.
        Uses the person with most consistent bounding box across frames.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.raw_data:
            return False, "No data loaded"
        
        # For single person, this is straightforward
        # For multi-person, we track the most centered/consistent person
        
        for frame_data in self.raw_data:
            people = frame_data.get("people", [])
            
            if len(people) > 1:
                # Select person closest to center or with largest bounding box
                best_person = self._select_best_person(people)
                frame_data["people"] = [best_person] if best_person else []
        
        return True, "Primary person selected"
    
    def _select_best_person(self, people: List[Dict]) -> Optional[Dict]:
        """
        Select the best person from multiple detections.
        Criteria: Most complete keypoints in gait-relevant joints.
        """
        best_score = -1
        best_person = None
        
        for person in people:
            keypoints = person.get("pose_keypoints_2d", [])
            
            # Count valid gait joints
            score = 0
            for joint_name, joint_idx in self.GAIT_JOINTS.items():
                idx = joint_idx * 3
                if idx + 2 < len(keypoints) and keypoints[idx + 2] > 0:
                    score += keypoints[idx + 2]  # Weight by confidence
            
            if score > best_score:
                best_score = score
                best_person = person
        
        return best_person
    
    def extract_gait_joints(self) -> np.ndarray:
        """
        Extract only gait-relevant joints into numpy array.
        
        Returns:
            Array of shape (frames, joints, 3) where 3 = [x, y, confidence]
        """
        n_frames = len(self.raw_data)
        n_joints = len(self.GAIT_JOINTS)
        
        # Initialize with NaN
        data = np.full((n_frames, n_joints, 3), np.nan)
        
        joint_order = list(self.GAIT_JOINTS.keys())
        
        for frame_idx, frame_data in enumerate(self.raw_data):
            people = frame_data.get("people", [])
            
            if not people:
                continue
            
            keypoints = people[0].get("pose_keypoints_2d", [])
            
            for j_idx, joint_name in enumerate(joint_order):
                openpose_idx = self.GAIT_JOINTS[joint_name]
                kp_idx = openpose_idx * 3
                
                if kp_idx + 2 < len(keypoints):
                    x = keypoints[kp_idx]
                    y = keypoints[kp_idx + 1]
                    conf = keypoints[kp_idx + 2]
                    
                    if conf > 0:
                        data[frame_idx, j_idx, :] = [x, y, conf]
        
        return data
    
    def check_lr_consistency(self, data: np.ndarray) -> Tuple[List[int], float]:
        """
        Check left-right consistency across frames based on trajectory continuity.
        
        Detects true OpenPose tracking swap glitches (sudden frame-to-frame teleportation
        between left and right ankles) while allowing natural crossing of left and right feet 
        during normal walking.
        
        Args:
            data: Joint data array (frames, joints, 3)
            
        Returns:
            Tuple of (inconsistent_frame_indices, consistency_score)
        """
        joint_order = list(self.GAIT_JOINTS.keys())
        r_ankle_idx = joint_order.index("RAnkle")
        l_ankle_idx = joint_order.index("LAnkle")
        
        inconsistent_frames = []
        
        for frame_idx in range(1, len(data)):
            r_curr = data[frame_idx, r_ankle_idx, :2]
            l_curr = data[frame_idx, l_ankle_idx, :2]
            r_prev = data[frame_idx - 1, r_ankle_idx, :2]
            l_prev = data[frame_idx - 1, l_ankle_idx, :2]
            
            if np.isnan(r_curr).any() or np.isnan(l_curr).any() or \
               np.isnan(r_prev).any() or np.isnan(l_prev).any():
                continue
            
            # Distance if tracking is maintained normally
            d_normal = np.sum((r_curr - r_prev) ** 2) + np.sum((l_curr - l_prev) ** 2)
            # Distance if tracking was swapped between left and right
            d_swapped = np.sum((r_curr - l_prev) ** 2) + np.sum((l_curr - r_prev) ** 2)
            
            # If swapped distance is significantly smaller, a tracking swap occurred
            if d_swapped < d_normal:
                inconsistent_frames.append(frame_idx)
        
        total_valid = max(1, len(data) - 1)
        consistency_score = 1.0 - (len(inconsistent_frames) / total_valid)
        
        return inconsistent_frames, consistency_score
    
    def swap_left_right(self, data: np.ndarray, frame_indices: List[int]) -> np.ndarray:
        """
        Swap left and right joint labels for specified frames.
        
        Args:
            data: Joint data array (frames, joints, 3)
            frame_indices: List of frame indices to swap
            
        Returns:
            Corrected data array
        """
        corrected = data.copy()
        joint_order = list(self.GAIT_JOINTS.keys())
        
        for frame_idx in frame_indices:
            for r_joint, l_joint in self.PAIRED_JOINTS:
                r_idx = joint_order.index(r_joint)
                l_idx = joint_order.index(l_joint)
                
                # Swap
                temp = corrected[frame_idx, r_idx, :].copy()
                corrected[frame_idx, r_idx, :] = corrected[frame_idx, l_idx, :]
                corrected[frame_idx, l_idx, :] = temp
        
        self.swap_log = frame_indices
        return corrected
    
    def auto_correct(self) -> Tuple[np.ndarray, Dict]:
        """
        Perform automatic left-right correction.
        
        Returns:
            Tuple of (corrected_data, correction_info)
        """
        # Select primary person
        self.select_primary_person()
        
        # Extract gait joints
        data = self.extract_gait_joints()
        
        # Check consistency
        inconsistent_frames, consistency_score = self.check_lr_consistency(data)
        
        correction_info = {
            "original_consistency": consistency_score,
            "frames_corrected": len(inconsistent_frames),
            "swap_log": inconsistent_frames
        }
        
        # Apply correction if needed
        if inconsistent_frames:
            data = self.swap_left_right(data, inconsistent_frames)
            
            # Re-check consistency
            _, new_consistency = self.check_lr_consistency(data)
            correction_info["corrected_consistency"] = new_consistency
        else:
            correction_info["corrected_consistency"] = consistency_score
        
        return data, correction_info
    
    def manual_swap(self, data: np.ndarray, start_frame: int, 
                    end_frame: int) -> np.ndarray:
        """
        Manually swap left-right labels for a frame range.
        
        Args:
            data: Joint data array
            start_frame: Start of range (inclusive)
            end_frame: End of range (inclusive)
            
        Returns:
            Corrected data array
        """
        frame_indices = list(range(start_frame, end_frame + 1))
        return self.swap_left_right(data, frame_indices)
    
    def to_timeseries_dict(self, data: np.ndarray, fps: float = 30.0) -> Dict:
        """
        Convert numpy array to structured time series dictionary.
        
        Args:
            data: Joint data array (frames, joints, 3)
            fps: Video frame rate
            
        Returns:
            Structured dictionary with time series data
        """
        joint_order = list(self.GAIT_JOINTS.keys())
        n_frames = data.shape[0]
        
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
        
        for frame_idx in range(n_frames):
            frame_data = {
                "frame_index": frame_idx,
                "time": frame_idx / fps,
                "joints": {}
            }
            
            for j_idx, joint_name in enumerate(joint_order):
                x, y, conf = data[frame_idx, j_idx, :]
                
                frame_data["joints"][joint_name] = {
                    "x": float(x) if not np.isnan(x) else None,
                    "y": float(y) if not np.isnan(y) else None,
                    "confidence": float(conf) if not np.isnan(conf) else 0.0
                }
            
            result["frames"].append(frame_data)
        
        return result
    
    def save_corrected_data(self, data: np.ndarray, output_path: str,
                           fps: float = 30.0, correction_info: Dict = None) -> str:
        """
        Save corrected pose data to JSON file.
        
        Args:
            data: Corrected joint data array
            output_path: Path for output JSON file
            fps: Video frame rate
            correction_info: Optional correction metadata
            
        Returns:
            Path to saved file
        """
        output_data = self.to_timeseries_dict(data, fps)
        
        if correction_info:
            output_data["correction_info"] = correction_info
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        return output_path
    
    def get_trajectory_data(self, data: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Get joint trajectory data for visualization.
        
        Args:
            data: Joint data array (frames, joints, 3)
            
        Returns:
            Dictionary with joint trajectories {joint_name: (x_array, y_array)}
        """
        joint_order = list(self.GAIT_JOINTS.keys())
        trajectories = {}
        
        for j_idx, joint_name in enumerate(joint_order):
            x_vals = data[:, j_idx, 0]
            y_vals = data[:, j_idx, 1]
            trajectories[joint_name] = (x_vals, y_vals)
        
        return trajectories
