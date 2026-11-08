"""
Pose Extraction Module
======================
Handles OpenPose execution and output processing.
This module:
- Runs OpenPose as external subprocess
- Validates output JSON files
- Normalizes keypoint data to internal format
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml


class PoseExtractor:
    """
    Manages OpenPose execution and output processing.
    
    This class only:
    - Runs OpenPose
    - Validates output
    - Normalizes JSON format
    
    It does NOT:
    - Calculate gait parameters
    - Make biomechanical decisions
    - Filter or process signals
    """
    
    # BODY_25 joint indices
    JOINT_NAMES = {
        0: "Nose", 1: "Neck", 2: "RShoulder", 3: "RElbow", 4: "RWrist",
        5: "LShoulder", 6: "LElbow", 7: "LWrist", 8: "MidHip",
        9: "RHip", 10: "RKnee", 11: "RAnkle", 12: "LHip",
        13: "LKnee", 14: "LAnkle", 15: "REye", 16: "LEye",
        17: "REar", 18: "LEar", 19: "LBigToe", 20: "LSmallToe",
        21: "LHeel", 22: "RBigToe", 23: "RSmallToe", 24: "RHeel"
    }
    
    # Joints relevant for gait analysis
    GAIT_JOINTS = [1, 8, 9, 10, 11, 12, 13, 14, 19, 21, 22, 24]  # Neck, MidHip, RHip, RKnee, RAnkle, LHip, LKnee, LAnkle, LBigToe, LHeel, RBigToe, RHeel
    
    def __init__(self, config_path: str = "config/openpose_config.yaml"):
        """
        Initialize PoseExtractor with configuration.
        
        Args:
            config_path: Path to OpenPose configuration file
        """
        self.config = self._load_config(config_path)
        self.openpose_path = self.config.get("openpose", {}).get(
            "executable_path", "C:/openpose/bin/OpenPoseDemo.exe"
        )
        self.model_folder = self.config.get("openpose", {}).get(
            "model_folder", "C:/openpose/models"
        )
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def run_openpose(self, video_path: str, output_dir: str,
                     progress_callback=None, generate_video: bool = True) -> Tuple[bool, str, Dict]:
        """
        Execute OpenPose on a video file.
        
        Args:
            video_path: Path to input video
            output_dir: Directory for JSON output
            progress_callback: Optional callback(current_frame, total_frames)
            generate_video: If True, generate output video with pose overlay (default: True)
            
        Returns:
            Tuple of (success, message, info_dict)
        """
        # Validate inputs
        if not os.path.exists(video_path):
            return False, f"Video not found: {video_path}", {}
        
        if not os.path.exists(self.openpose_path):
            return False, f"OpenPose not found: {self.openpose_path}", {}
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Build OpenPose command
        cmd = [
            self.openpose_path,
            "--video", video_path,
            "--write_json", output_dir,
            "--model_folder", self.model_folder,
            "--model_pose", "BODY_25",
            "--number_people_max", "1",
            "--display", "0",
            "--render_pose", "1" if generate_video else "0"
        ]
        
        # Add video output if requested
        if generate_video:
            # Generate output video path
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_video_path = os.path.join(output_dir, f"{video_name}_openpose.avi")
            cmd.extend(["--write_video", output_video_path])
        
        try:
            # Run OpenPose
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.openpose_path)
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                return False, f"OpenPose failed: {stderr}", {}
            
            # Validate output
            success, msg, info = self.validate_output(output_dir)
            
            # Add video output path to info if generated
            if generate_video and success:
                info["output_video_path"] = output_video_path
            
            return success, msg, info
            
        except FileNotFoundError:
            return False, "OpenPose executable not found", {}
        except Exception as e:
            return False, f"Error running OpenPose: {str(e)}", {}
    
    def validate_output(self, output_dir: str) -> Tuple[bool, str, Dict]:
        """
        Validate OpenPose JSON output files.
        
        Args:
            output_dir: Directory containing JSON files
            
        Returns:
            Tuple of (success, message, info_dict)
        """
        if not os.path.exists(output_dir):
            return False, "Output directory not found", {}
        
        json_files = sorted([
            f for f in os.listdir(output_dir) 
            if f.endswith('_keypoints.json')
        ])
        
        if not json_files:
            return False, "No keypoint JSON files found", {}
        
        # Check for missing frames and keypoints quality
        total_frames = len(json_files)
        frames_with_person = 0
        missing_keypoints_count = 0
        
        for json_file in json_files:
            file_path = os.path.join(output_dir, json_file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if data.get("people") and len(data["people"]) > 0:
                    frames_with_person += 1
                    keypoints = data["people"][0].get("pose_keypoints_2d", [])
                    
                    # Check gait-relevant joints
                    for joint_idx in self.GAIT_JOINTS:
                        idx = joint_idx * 3
                        if idx + 2 < len(keypoints):
                            conf = keypoints[idx + 2]
                            if conf == 0:
                                missing_keypoints_count += 1
                                
            except (json.JSONDecodeError, KeyError):
                continue
        
        detection_rate = frames_with_person / total_frames if total_frames > 0 else 0
        
        info = {
            "total_frames": total_frames,
            "frames_with_person": frames_with_person,
            "detection_rate": detection_rate,
            "missing_keypoints": missing_keypoints_count
        }
        
        if detection_rate < 0.8:
            return False, f"Low detection rate: {detection_rate:.1%}", info
        
        return True, f"Validated {total_frames} frames", info
    
    def load_keypoints(self, output_dir: str) -> List[Dict]:
        """
        Load all keypoint data from JSON files.
        
        Args:
            output_dir: Directory containing JSON files
            
        Returns:
            List of frame data dictionaries
        """
        json_files = sorted([
            f for f in os.listdir(output_dir) 
            if f.endswith('_keypoints.json')
        ])
        
        frames_data = []
        
        for frame_idx, json_file in enumerate(json_files):
            file_path = os.path.join(output_dir, json_file)
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                frame_data = {
                    "frame_index": frame_idx,
                    "filename": json_file,
                    "keypoints": None,
                    "has_person": False
                }
                
                if data.get("people") and len(data["people"]) > 0:
                    keypoints = data["people"][0].get("pose_keypoints_2d", [])
                    frame_data["keypoints"] = self._parse_keypoints(keypoints)
                    frame_data["has_person"] = True
                
                frames_data.append(frame_data)
                
            except (json.JSONDecodeError, KeyError, IOError):
                frames_data.append({
                    "frame_index": frame_idx,
                    "filename": json_file,
                    "keypoints": None,
                    "has_person": False
                })
        
        return frames_data
    
    def _parse_keypoints(self, keypoints_flat: List[float]) -> Dict:
        """
        Parse flat keypoint array into structured dictionary.
        
        Args:
            keypoints_flat: Flat array [x0, y0, c0, x1, y1, c1, ...]
            
        Returns:
            Dictionary with joint names as keys
        """
        parsed = {}
        
        for joint_idx, joint_name in self.JOINT_NAMES.items():
            idx = joint_idx * 3
            if idx + 2 < len(keypoints_flat):
                parsed[joint_name] = {
                    "x": keypoints_flat[idx],
                    "y": keypoints_flat[idx + 1],
                    "confidence": keypoints_flat[idx + 2]
                }
            else:
                parsed[joint_name] = {"x": 0, "y": 0, "confidence": 0}
        
        return parsed
    
    def extract_gait_joints(self, frames_data: List[Dict]) -> Dict:
        """
        Extract only gait-relevant joints from full keypoint data.
        
        Args:
            frames_data: List of frame data from load_keypoints()
            
        Returns:
            Dictionary with gait joint time series
        """
        gait_joint_names = [self.JOINT_NAMES[idx] for idx in self.GAIT_JOINTS]
        
        result = {
            "frame_count": len(frames_data),
            "joints": gait_joint_names,
            "data": []
        }
        
        for frame in frames_data:
            frame_joints = {
                "frame_index": frame["frame_index"],
                "has_person": frame["has_person"],
                "joints": {}
            }
            
            if frame["keypoints"]:
                for joint_name in gait_joint_names:
                    if joint_name in frame["keypoints"]:
                        frame_joints["joints"][joint_name] = frame["keypoints"][joint_name]
            
            result["data"].append(frame_joints)
        
        return result
    
    def get_video_with_pose(self, video_path: str, output_video_path: str,
                           output_dir: str) -> Tuple[bool, str]:
        """
        Generate video with pose overlay using OpenPose.
        
        Args:
            video_path: Input video path
            output_video_path: Output video path
            output_dir: JSON output directory
            
        Returns:
            Tuple of (success, message)
        """
        if not os.path.exists(self.openpose_path):
            return False, "OpenPose not found"
        
        cmd = [
            self.openpose_path,
            "--video", video_path,
            "--write_json", output_dir,
            "--write_video", output_video_path,
            "--model_folder", self.model_folder,
            "--model_pose", "BODY_25",
            "--number_people_max", "1"
        ]
        
        try:
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                return False, f"OpenPose failed: {process.stderr}"
            
            return True, "Video with pose generated successfully"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    def export_highres_openpose_frames(self, openpose_dir: str, target_dir: str, 
                                       raw_video_path: Optional[str] = None,
                                       progress_callback=None) -> Tuple[bool, str, Dict]:
        """
        Export high-resolution per-frame photos of OpenPose detection results to target_dir.
        
        Args:
            openpose_dir: Directory containing OpenPose output video or keypoint JSON files
            target_dir: Target directory to save individual frame photos
            raw_video_path: Optional path to raw input video (for fallback rendering)
            progress_callback: Optional callable(current_frame, total_frames)
            
        Returns:
            Tuple of (success, message, info_dict)
        """
        import cv2
        os.makedirs(target_dir, exist_ok=True)
        
        # 1. Look for rendered OpenPose video (*_openpose.avi, output_video.avi, etc.)
        video_path = None
        if os.path.exists(openpose_dir):
            for f in os.listdir(openpose_dir):
                if f.endswith('_openpose.avi'):
                    video_path = os.path.join(openpose_dir, f)
                    break
            if not video_path:
                for name in ["output_video.avi", "output.avi", "rendered.avi"]:
                    p = os.path.join(openpose_dir, name)
                    if os.path.exists(p):
                        video_path = p
                        break

        # If rendered OpenPose video is found, extract frames directly
        if video_path and os.path.exists(video_path):
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                saved_count = 0
                frame_idx = 0
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_name = f"frame_{frame_idx:05d}.png"
                    out_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(out_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                    saved_count += 1
                    
                    if progress_callback:
                        progress_callback(saved_count, total_frames)
                    
                    frame_idx += 1
                
                cap.release()
                if saved_count > 0:
                    return True, f"Berhasil menyimpan {saved_count} foto per-frame resolusi tinggi ({width}x{height})", {
                        "total_frames": saved_count,
                        "resolution": f"{width}x{height}",
                        "target_dir": target_dir
                    }

        # 2. Fallback: Draw keypoint overlay onto raw_video_path using JSON keypoint files
        if raw_video_path and os.path.exists(raw_video_path) and os.path.exists(openpose_dir):
            cap = cv2.VideoCapture(raw_video_path)
            if not cap.isOpened():
                return False, "Tidak dapat membuka file video sumber", {}
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Load frames keypoints
            json_files = sorted([f for f in os.listdir(openpose_dir) if f.endswith('_keypoints.json')])
            
            # BODY_25 pairs for skeleton visualization
            body25_pairs = [
                (1, 8), (1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7),
                (8, 9), (9, 10), (10, 11), (8, 12), (12, 13), (13, 14),
                (1, 0), (0, 15), (15, 17), (0, 16), (16, 18), (14, 19),
                (19, 20), (14, 21), (11, 22), (22, 23), (11, 24)
            ]
            
            saved_count = 0
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Draw skeleton if matching json exists
                if frame_idx < len(json_files):
                    json_path = os.path.join(openpose_dir, json_files[frame_idx])
                    try:
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                        if data.get("people") and len(data["people"]) > 0:
                            kp = data["people"][0].get("pose_keypoints_2d", [])
                            # Draw lines
                            for j1, j2 in body25_pairs:
                                idx1, idx2 = j1 * 3, j2 * 3
                                if idx1 + 2 < len(kp) and idx2 + 2 < len(kp):
                                    x1, y1, c1 = kp[idx1], kp[idx1+1], kp[idx1+2]
                                    x2, y2, c2 = kp[idx2], kp[idx2+1], kp[idx2+2]
                                    if c1 > 0.1 and c2 > 0.1:
                                        pt1 = (int(round(x1)), int(round(y1)))
                                        pt2 = (int(round(x2)), int(round(y2)))
                                        cv2.line(frame, pt1, pt2, (0, 255, 0), 3)
                            # Draw joints
                            for j in range(25):
                                idx = j * 3
                                if idx + 2 < len(kp):
                                    x, y, c = kp[idx], kp[idx+1], kp[idx+2]
                                    if c > 0.1:
                                        pt = (int(round(x)), int(round(y)))
                                        cv2.circle(frame, pt, 4, (0, 0, 255), -1)
                    except Exception:
                        pass
                
                frame_name = f"frame_{frame_idx:05d}.png"
                out_path = os.path.join(target_dir, frame_name)
                cv2.imwrite(out_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                saved_count += 1
                
                if progress_callback:
                    progress_callback(saved_count, total_frames)
                
                frame_idx += 1
            
            cap.release()
            if saved_count > 0:
                return True, f"Berhasil menyimpan {saved_count} foto per-frame resolusi tinggi ({width}x{height})", {
                    "total_frames": saved_count,
                    "resolution": f"{width}x{height}",
                    "target_dir": target_dir
                }
        
        return False, "Tidak ditemukan data video atau keypoints OpenPose", {}
