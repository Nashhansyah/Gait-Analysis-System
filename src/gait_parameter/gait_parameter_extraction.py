"""
Gait Parameter Extraction Module
================================
Calculates quantitative gait parameters from events and phases.
This module:
- Computes temporal parameters (timing)
- Computes spatial parameters (distances)
- Computes spatio-temporal parameters (speed)
- Aggregates statistics per subject
- Exports to CSV format
"""

import os
import json
import csv
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class GaitParameterExtractor:
    """
    Extracts quantitative gait parameters from event and phase data.
    
    This class:
    - Calculates all gait parameters
    - Aggregates per-step and per-cycle
    - Generates statistical summaries
    - Exports to various formats
    """
    
    def __init__(self):
        """Initialize the Gait Parameter Extractor."""
        self.parameters: Dict = {}
        self.step_data: List[Dict] = []
        self.cycle_data: List[Dict] = []
        self.summary: Dict = {}
        self.kinematics: Dict = {}
        
    def compute_all_parameters(self, events: Dict, gait_cycles: List[Dict],
                                pose_data: Dict) -> Dict:
        """
        Compute all gait parameters from events and pose data.
        
        Args:
            events: Gait events dictionary
            gait_cycles: List of gait cycle dictionaries
            pose_data: Preprocessed pose data dictionary
            
        Returns:
            Dictionary with all computed parameters
        """
        fps = events.get("metadata", {}).get("fps", 30.0)
        
        # Compute spatial and temporal parameters
        self.step_data = self._compute_step_parameters(events, pose_data, fps)
        self.cycle_data = self._compute_cycle_parameters(gait_cycles, pose_data, fps)
        
        # Compute joint kinematics (Hip, Knee, Ankle angles)
        self.kinematics = self.compute_kinematics(pose_data)
        
        # Compute summary statistics
        self.summary = self._compute_summary()
        self.summary["kinematics"] = self.kinematics.get("summary", {})
        
        self.parameters = {
            "metadata": {
                "computed_at": datetime.now().isoformat(),
                "fps": fps,
                "num_steps": len(self.step_data),
                "num_cycles": len(self.cycle_data)
            },
            "step_parameters": self.step_data,
            "cycle_parameters": self.cycle_data,
            "kinematics": self.kinematics,
            "summary": self.summary
        }
        
        return self.parameters
    
    def _compute_step_parameters(self, events: Dict, pose_data: Dict,
                                  fps: float) -> List[Dict]:
        """
        Compute parameters for each step.
        
        A step is defined as one foot contact to the next opposite foot contact.
        """
        steps = []
        
        # Combine and sort all heel strikes
        all_hs = []
        for side in ["right", "left"]:
            for hs in events.get(side, {}).get("heel_strikes", []):
                all_hs.append({**hs, "side": side})
        
        all_hs.sort(key=lambda x: x["frame"])
        
        if len(all_hs) < 2:
            return steps
        
        # Get frames data for spatial calculation
        frames = pose_data.get("frames", [])
        
        for i in range(len(all_hs) - 1):
            hs1 = all_hs[i]
            hs2 = all_hs[i + 1]
            
            # Step time
            step_time = hs2["time"] - hs1["time"]
            
            # Calculate step length from ankle positions
            step_length = self._calculate_step_length(
                frames, hs1["frame"], hs2["frame"], hs1["side"], hs2["side"]
            )
            
            # Step velocity
            step_velocity = step_length / step_time if step_time > 0 else 0
            
            step = {
                "step_id": i,
                "start_side": hs1["side"],
                "end_side": hs2["side"],
                "start_frame": hs1["frame"],
                "end_frame": hs2["frame"],
                "start_time": hs1["time"],
                "end_time": hs2["time"],
                "step_time": step_time,
                "step_length": step_length,
                "step_velocity": step_velocity
            }
            
            steps.append(step)
        
        return steps
    
    def _calculate_step_length(self, frames: List[Dict], frame1: int, frame2: int,
                               side1: str, side2: str) -> float:
        """
        Calculate step length from ankle positions at heel strikes.
        
        Step length = distance between ankle positions at consecutive heel strikes.
        """
        if frame1 >= len(frames) or frame2 >= len(frames):
            return 0.0
        
        # Get ankle positions at each heel strike
        ankle1_joint = f"{side1[0].upper()}Ankle"  # RAnkle or LAnkle
        ankle2_joint = f"{side2[0].upper()}Ankle"
        
        joints1 = frames[frame1].get("joints", {})
        joints2 = frames[frame2].get("joints", {})
        
        ankle1 = joints1.get(ankle1_joint, {})
        ankle2 = joints2.get(ankle2_joint, {})
        
        x1 = ankle1.get("x")
        x2 = ankle2.get("x")
        
        if x1 is None or x2 is None:
            return 0.0
        
        # Step length is the horizontal distance
        return abs(x2 - x1)
    
    def _compute_cycle_parameters(self, gait_cycles: List[Dict],
                                   pose_data: Dict, fps: float) -> List[Dict]:
        """
        Compute parameters for each gait cycle.
        
        All cycles (valid and invalid) are included in output.
        Invalid cycles are marked but still displayed in GUI.
        """
        cycle_params = []
        frames = pose_data.get("frames", [])
        
        for cycle in gait_cycles:
            is_valid = cycle.get("valid", True)
            invalid_reason = cycle.get("invalid_reason")
            
            # Basic temporal parameters
            cycle_time = cycle.get("duration", 0)
            stance_time = cycle.get("stance_duration", 0)
            swing_time = cycle.get("swing_duration", 0)
            
            # Stride length (distance covered in one full cycle)
            stride_length = self._calculate_stride_length(
                frames, cycle["start_frame"], cycle["end_frame"], cycle["side"]
            )
            
            # Walking speed
            walking_speed = stride_length / cycle_time if cycle_time > 0 else 0
            
            params = {
                "cycle_id": cycle.get("cycle_id", 0),
                "side": cycle["side"],
                "start_frame": cycle["start_frame"],
                "end_frame": cycle["end_frame"],
                "cycle_time": cycle_time,
                "stance_time": stance_time,
                "swing_time": swing_time,
                "stance_ratio": cycle.get("stance_ratio", 0),
                "swing_ratio": cycle.get("swing_ratio", 0),
                "stride_length": stride_length,
                "walking_speed": walking_speed,
                "cadence": 60.0 / cycle_time if cycle_time > 0 else 0,  # steps/minute
                "valid": is_valid,
                "invalid_reason": invalid_reason
            }
            
            cycle_params.append(params)
        
        return cycle_params
    
    def _calculate_stride_length(self, frames: List[Dict], start_frame: int,
                                  end_frame: int, side: str) -> float:
        """
        Calculate stride length from ankle positions.
        
        Stride length = distance ankle travels during one complete gait cycle.
        """
        if start_frame >= len(frames) or end_frame >= len(frames):
            return 0.0
        
        ankle_joint = f"{side[0].upper()}Ankle"
        
        start_joints = frames[start_frame].get("joints", {})
        end_joints = frames[end_frame].get("joints", {})
        
        start_ankle = start_joints.get(ankle_joint, {})
        end_ankle = end_joints.get(ankle_joint, {})
        
        x_start = start_ankle.get("x")
        x_end = end_ankle.get("x")
        
        if x_start is None or x_end is None:
            return 0.0
        
        return abs(x_end - x_start)
    
    def _compute_summary(self) -> Dict:
        """
        Compute summary statistics for all parameters.
        
        Prioritizes valid cycles, but falls back to all cycles if no valid ones exist.
        When using invalid cycles, a warning flag is set for UI display.
        """
        summary = {
            "step": {},
            "cycle": {},
            "overall": {},
            "warnings": []
        }
        
        # Step statistics
        if self.step_data:
            step_times = [s["step_time"] for s in self.step_data]
            step_lengths = [s["step_length"] for s in self.step_data if s["step_length"] > 0]
            step_velocities = [s["step_velocity"] for s in self.step_data if s["step_velocity"] > 0]
            
            summary["step"] = {
                "count": len(self.step_data),
                "step_time": self._compute_stats(step_times),
                "step_length": self._compute_stats(step_lengths),
                "step_velocity": self._compute_stats(step_velocities)
            }
        
        # Cycle statistics - prefer valid cycles, fallback to all cycles
        valid_cycles = [c for c in self.cycle_data if c.get("valid", True)]
        
        # If no valid cycles but we have cycles, use all cycles with warning
        use_all_cycles = False
        cycles_to_use = valid_cycles
        
        if not valid_cycles and self.cycle_data:
            cycles_to_use = self.cycle_data
            use_all_cycles = True
            summary["warnings"].append(
                "⚠️ All gait cycles exceed normal duration threshold. "
                "Parameters calculated using all detected cycles."
            )
        
        if cycles_to_use:
            cycle_times = [c["cycle_time"] for c in cycles_to_use]
            stance_ratios = [c["stance_ratio"] for c in cycles_to_use if c["stance_ratio"] > 0]
            swing_ratios = [c["swing_ratio"] for c in cycles_to_use if c["swing_ratio"] > 0]
            stride_lengths = [c["stride_length"] for c in cycles_to_use if c["stride_length"] > 0]
            walking_speeds = [c["walking_speed"] for c in cycles_to_use if c["walking_speed"] > 0]
            cadences = [c["cadence"] for c in cycles_to_use if c["cadence"] > 0]
            
            summary["cycle"] = {
                "count": len(cycles_to_use),
                "total_count": len(self.cycle_data),
                "invalid_count": len(self.cycle_data) - len(valid_cycles),
                "using_all_cycles": use_all_cycles,
                "cycle_time": self._compute_stats(cycle_times),
                "stance_ratio": self._compute_stats(stance_ratios),
                "swing_ratio": self._compute_stats(swing_ratios),
                "stride_length": self._compute_stats(stride_lengths),
                "walking_speed": self._compute_stats(walking_speeds),
                "cadence": self._compute_stats(cadences)
            }
        
        # Overall summary - based on cycles_to_use (valid or all)
        if cycles_to_use:
            # Calculate per-side ratios for clinical assessment
            left_cycles = [c for c in cycles_to_use if c.get("side", "").lower() == "left"]
            right_cycles = [c for c in cycles_to_use if c.get("side", "").lower() == "right"]
            
            left_stance = [c["stance_ratio"] for c in left_cycles if c["stance_ratio"] > 0]
            left_swing = [c["swing_ratio"] for c in left_cycles if c["swing_ratio"] > 0]
            right_stance = [c["stance_ratio"] for c in right_cycles if c["stance_ratio"] > 0]
            right_swing = [c["swing_ratio"] for c in right_cycles if c["swing_ratio"] > 0]
            
            summary["overall"] = {
                "mean_cadence": summary["cycle"].get("cadence", {}).get("mean", 0),
                "mean_walking_speed": summary["cycle"].get("walking_speed", {}).get("mean", 0),
                "mean_stride_length": summary["cycle"].get("stride_length", {}).get("mean", 0),
                "mean_step_length": summary["step"].get("step_length", {}).get("mean", 0),
                # Combined ratios (for backward compatibility)
                "mean_stance_ratio": summary["cycle"].get("stance_ratio", {}).get("mean", 0),
                "mean_swing_ratio": summary["cycle"].get("swing_ratio", {}).get("mean", 0),
                # Per-side ratios (clinical standard)
                "left_stance_ratio": sum(left_stance) / len(left_stance) if left_stance else 0,
                "left_swing_ratio": sum(left_swing) / len(left_swing) if left_swing else 0,
                "right_stance_ratio": sum(right_stance) / len(right_stance) if right_stance else 0,
                "right_swing_ratio": sum(right_swing) / len(right_swing) if right_swing else 0,
                "using_all_cycles": use_all_cycles
            }
        
        return summary
    
    def _compute_stats(self, values: List[float]) -> Dict:
        """Compute basic statistics for a list of values."""
        if not values:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "median": 0}
        
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "median": float(np.median(arr))
        }

    def _calculate_angle_3points(self, p1: Optional[Dict], p2: Optional[Dict], p3: Optional[Dict]) -> float:
        """
        Calculate interior 2D angle (in degrees) at vertex p2 formed by p2->p1 and p2->p3.
        
        Args:
            p1: First point dict {'x': float, 'y': float}
            p2: Vertex point dict {'x': float, 'y': float}
            p3: Third point dict {'x': float, 'y': float}
            
        Returns:
            Angle in degrees (0.0 to 180.0), or np.nan if invalid.
        """
        if not p1 or not p2 or not p3:
            return float(np.nan)
        
        x1, y1 = p1.get("x"), p1.get("y")
        x2, y2 = p2.get("x"), p2.get("y")
        x3, y3 = p3.get("x"), p3.get("y")
        
        if None in (x1, y1, x2, y2, x3, y3):
            return float(np.nan)
        
        u = np.array([x1 - x2, y1 - y2], dtype=float)
        v = np.array([x3 - x2, y3 - y2], dtype=float)
        
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        
        if norm_u < 1e-6 or norm_v < 1e-6:
            return float(np.nan)
        
        cos_angle = np.clip(np.dot(u, v) / (norm_u * norm_v), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))

    def compute_kinematics(self, pose_data: Dict) -> Dict:
        """
        Compute joint kinematics (Hip, Knee, Ankle angles) for each frame.
        
        Args:
            pose_data: Preprocessed or scaled pose data
            
        Returns:
            Kinematics dictionary containing time series and summary statistics.
        """
        frames = pose_data.get("frames", [])
        fps = pose_data.get("metadata", {}).get("fps", 30.0)
        
        times = []
        r_hip, r_knee, r_ankle = [], [], []
        l_hip, l_knee, l_ankle = [], [], []
        
        for i, frame in enumerate(frames):
            t = frame.get("time", i / fps)
            times.append(t)
            joints = frame.get("joints", {})
            
            # Right side keypoints
            r_hip_pt = joints.get("RHip")
            r_knee_pt = joints.get("RKnee")
            r_ankle_pt = joints.get("RAnkle")
            
            # Left side keypoints
            l_hip_pt = joints.get("LHip")
            l_knee_pt = joints.get("LKnee")
            l_ankle_pt = joints.get("LAnkle")
            
            # Upper/Foot references if optional joints are available
            neck_pt = joints.get("Neck")
            r_toe_pt = joints.get("RBigToe")
            l_toe_pt = joints.get("LBigToe")
            
            r_neck_ref = neck_pt if (neck_pt and neck_pt.get("x") is not None) else (
                {"x": r_hip_pt["x"], "y": r_hip_pt["y"] - 1.0} if r_hip_pt and r_hip_pt.get("x") is not None and r_hip_pt.get("y") is not None else None
            )
            l_neck_ref = neck_pt if (neck_pt and neck_pt.get("x") is not None) else (
                {"x": l_hip_pt["x"], "y": l_hip_pt["y"] - 1.0} if l_hip_pt and l_hip_pt.get("x") is not None and l_hip_pt.get("y") is not None else None
            )
            
            r_foot_ref = r_toe_pt if (r_toe_pt and r_toe_pt.get("x") is not None) else (
                {"x": r_ankle_pt["x"] + 0.2, "y": r_ankle_pt["y"]} if r_ankle_pt and r_ankle_pt.get("x") is not None and r_ankle_pt.get("y") is not None else None
            )
            l_foot_ref = l_toe_pt if (l_toe_pt and l_toe_pt.get("x") is not None) else (
                {"x": l_ankle_pt["x"] + 0.2, "y": l_ankle_pt["y"]} if l_ankle_pt and l_ankle_pt.get("x") is not None and l_ankle_pt.get("y") is not None else None
            )
            
            # Calculate angles in degrees
            rh = self._calculate_angle_3points(r_neck_ref, r_hip_pt, r_knee_pt)
            rk = self._calculate_angle_3points(r_hip_pt, r_knee_pt, r_ankle_pt)
            ra = self._calculate_angle_3points(r_knee_pt, r_ankle_pt, r_foot_ref)
            
            lh = self._calculate_angle_3points(l_neck_ref, l_hip_pt, l_knee_pt)
            lk = self._calculate_angle_3points(l_hip_pt, l_knee_pt, l_ankle_pt)
            la = self._calculate_angle_3points(l_knee_pt, l_ankle_pt, l_foot_ref)
            
            r_hip.append(rh)
            r_knee.append(rk)
            r_ankle.append(ra)
            
            l_hip.append(lh)
            l_knee.append(lk)
            l_ankle.append(la)
            
        kinematics = {
            "time": times,
            "right": {
                "hip_angle": r_hip,
                "knee_angle": r_knee,
                "ankle_angle": r_ankle
            },
            "left": {
                "hip_angle": l_hip,
                "knee_angle": l_knee,
                "ankle_angle": l_ankle
            },
            "summary": {
                "right": {
                    "hip": self._compute_angle_stats(r_hip),
                    "knee": self._compute_angle_stats(r_knee),
                    "ankle": self._compute_angle_stats(r_ankle)
                },
                "left": {
                    "hip": self._compute_angle_stats(l_hip),
                    "knee": self._compute_angle_stats(l_knee),
                    "ankle": self._compute_angle_stats(l_ankle)
                }
            }
        }
        return kinematics

    def _compute_angle_stats(self, values: List[float]) -> Dict:
        """Compute mean, min, max, std, and ROM for angle series."""
        clean = [v for v in values if v is not None and not np.isnan(v)]
        if not clean:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "rom": 0.0}
        arr = np.array(clean)
        mn = float(np.min(arr))
        mx = float(np.max(arr))
        return {
            "mean": float(np.mean(arr)),
            "min": mn,
            "max": mx,
            "std": float(np.std(arr)),
            "rom": float(mx - mn)
        }

    def get_kinematic_table(self) -> List[Dict]:
        """
        Get structured kinematic parameter table for GUI display.
        
        Returns:
            List of dicts: [{'joint': str, 'side': str, 'mean': str, 'min': str, 'max': str, 'rom': str}]
        """
        summary = self.kinematics.get("summary", {})
        r_sum = summary.get("right", {})
        l_sum = summary.get("left", {})
        
        rows = []
        joints_map = [
            ("Sudut Panggul (Hip Angle)", "hip"),
            ("Sudut Lutut (Knee Angle)", "knee"),
            ("Sudut Pergelangan Kaki (Ankle Angle)", "ankle")
        ]
        
        for name, key in joints_map:
            for side_name, side_data in [("Kiri", l_sum.get(key, {})), ("Kanan", r_sum.get(key, {}))]:
                mean_v = side_data.get("mean", 0.0)
                min_v = side_data.get("min", 0.0)
                max_v = side_data.get("max", 0.0)
                rom_v = side_data.get("rom", 0.0)
                
                rows.append({
                    "joint": name,
                    "side": side_name,
                    "mean": f"{mean_v:.1f}°" if mean_v else "-",
                    "min": f"{min_v:.1f}°" if min_v else "-",
                    "max": f"{max_v:.1f}°" if max_v else "-",
                    "rom": f"{rom_v:.1f}°" if rom_v else "-"
                })
                
        return rows
    
    def export_csv(self, output_dir: str, subject_id: str, video_path: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, str]:
        """
        Export parameters to CSV files.
        
        Args:
            output_dir: Output directory
            subject_id: Subject identifier
            video_path: Optional video path for Excel embedding
            session_id: Optional session identifier
            
        Returns:
            Dictionary with paths to created files
        """
        os.makedirs(output_dir, exist_ok=True)

        if not session_id:
            dir_name = os.path.basename(os.path.normpath(output_dir))
            if dir_name.startswith("session_"):
                session_id = dir_name

        prefix = f"{subject_id}_{session_id}" if session_id and session_id != "default" else subject_id
        
        paths = {}
        
        # Export step parameters
        step_path = os.path.join(output_dir, f"{prefix}_step.csv")
        self._export_step_csv(step_path)
        paths["step"] = step_path
        
        # Export cycle parameters
        cycle_path = os.path.join(output_dir, f"{prefix}_cycle.csv")
        self._export_cycle_csv(cycle_path)
        paths["cycle"] = cycle_path
        
        # Export summary
        summary_path = os.path.join(output_dir, f"{prefix}_summary.csv")
        self._export_summary_csv(summary_path)
        paths["summary"] = summary_path
        
        # Export kinematics (joint angles)
        kinematics_path = os.path.join(output_dir, f"{prefix}_kinematics.csv")
        self._export_kinematics_csv(kinematics_path)
        paths["kinematics"] = kinematics_path
        
        # Export unified multi-sheet Excel file
        excel_path = self.export_excel(output_dir, subject_id, video_path=video_path, session_id=session_id)
        paths["excel"] = excel_path
        
        return paths

    def export_excel(self, output_dir: str, subject_id: str, video_path: Optional[str] = None, session_id: Optional[str] = None) -> str:
        """
        Export all parameters and kinematics to a single, beautifully formatted multi-sheet Excel file (.xlsx).
        
        The 'Deret Waktu Sudut' sheet presents angle data strictly per frame index (no seconds column) 
        accompanied by an embedded image of each video frame.
        
        Sheets included:
        1. Ringkasan Parameter (Spatiotemporal Summary)
        2. Siklus Gait (Gait Cycles)
        3. Detail Langkah (Per-Step Details)
        4. Ringkasan Sudut Sendi (Kinematics Summary)
        5. Deret Waktu Sudut (Kinematics Time-Series with Frame Images)
        
        Args:
            output_dir: Directory path for export
            subject_id: Subject identifier
            video_path: Optional path to input or OpenPose video file
            session_id: Optional session identifier
            
        Returns:
            Path to exported Excel file
        """
        import cv2, io, glob
        from openpyxl.drawing.image import Image
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        os.makedirs(output_dir, exist_ok=True)

        if not session_id:
            dir_name = os.path.basename(os.path.normpath(output_dir))
            if dir_name.startswith("session_"):
                session_id = dir_name

        excel_filename = f"{subject_id}_{session_id}_gait_analysis_report.xlsx" if session_id and session_id != "default" else f"{subject_id}_gait_analysis_report.xlsx"
        excel_path = os.path.join(output_dir, excel_filename)
        
        # Try to locate video file if not explicitly provided or if provided path doesn't exist
        if not video_path or not os.path.exists(video_path):
            curr = os.path.abspath(output_dir)
            data_dir = None
            while curr:
                if os.path.basename(curr) == 'data':
                    data_dir = curr
                    break
                parent = os.path.dirname(curr)
                if parent == curr:
                    break
                curr = parent
            if not data_dir:
                data_dir = os.path.dirname(os.path.dirname(os.path.abspath(output_dir)))

            target_session_folder = session_id if session_id else "*"
            possible_patterns = [
                os.path.join(output_dir, f"{subject_id}_openpose.avi"),
                os.path.join(output_dir, "*.avi"),
                os.path.join(data_dir, "openpose_raw", subject_id, target_session_folder, "*_openpose.avi"),
                os.path.join(data_dir, "openpose_raw", subject_id, target_session_folder, "*.avi"),
                os.path.join(data_dir, "openpose_raw", subject_id, "*", "*_openpose.avi"),
                os.path.join(data_dir, "input_video", subject_id, target_session_folder, "video_raw.mp4"),
                os.path.join(data_dir, "input_video", subject_id, target_session_folder, "*.mp4"),
                os.path.join(data_dir, "input_video", subject_id, "*", "*.mp4"),
                os.path.join(data_dir, "input_video", subject_id, "*", "*.avi"),
            ]
            for pattern in possible_patterns:
                matches = glob.glob(pattern)
                if matches:
                    video_path = matches[0]
                    break

        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 1. Summary Sheet
                summary_rows = self.get_parameter_table()
                df_summary = pd.DataFrame(summary_rows)
                df_summary.to_excel(writer, sheet_name="Ringkasan Parameter", index=False)
                
                # 2. Gait Cycles Sheet
                if self.cycle_data:
                    df_cycles = pd.DataFrame(self.cycle_data)
                    df_cycles.to_excel(writer, sheet_name="Siklus Gait", index=False)
                else:
                    pd.DataFrame([{"info": "Data siklus gait tidak tersedia"}]).to_excel(writer, sheet_name="Siklus Gait", index=False)
                    
                # 3. Step Details Sheet
                if self.step_data:
                    df_steps = pd.DataFrame(self.step_data)
                    df_steps.to_excel(writer, sheet_name="Detail Langkah", index=False)
                else:
                    pd.DataFrame([{"info": "Data langkah tidak tersedia"}]).to_excel(writer, sheet_name="Detail Langkah", index=False)
                    
                # 4. Kinematics Summary Sheet
                kin_summary_rows = self.get_kinematic_table()
                df_kin_summary = pd.DataFrame(kin_summary_rows)
                df_kin_summary.to_excel(writer, sheet_name="Ringkasan Sudut Sendi", index=False)
                
                # 5. Kinematics Time-Series Sheet (Per Frame with Image column)
                if self.kinematics:
                    r_hip = self.kinematics.get("right", {}).get("hip_angle", [])
                    r_knee = self.kinematics.get("right", {}).get("knee_angle", [])
                    r_ankle = self.kinematics.get("right", {}).get("ankle_angle", [])
                    
                    l_hip = self.kinematics.get("left", {}).get("hip_angle", [])
                    l_knee = self.kinematics.get("left", {}).get("knee_angle", [])
                    l_ankle = self.kinematics.get("left", {}).get("ankle_angle", [])
                    
                    num_frames = max(len(r_hip), len(r_knee), len(l_hip), len(l_knee))
                    
                    kin_series = []
                    for i in range(num_frames):
                        kin_series.append({
                            "Frame": i,
                            "Gambar Frame": "",  # Placeholder for image
                            "Sudut Panggul Kanan (°)": round(r_hip[i], 2) if i < len(r_hip) and not np.isnan(r_hip[i]) else None,
                            "Sudut Lutut Kanan (°)": round(r_knee[i], 2) if i < len(r_knee) and not np.isnan(r_knee[i]) else None,
                            "Sudut Ankle Kanan (°)": round(r_ankle[i], 2) if i < len(r_ankle) and not np.isnan(r_ankle[i]) else None,
                            "Sudut Panggul Kiri (°)": round(l_hip[i], 2) if i < len(l_hip) and not np.isnan(l_hip[i]) else None,
                            "Sudut Lutut Kiri (°)": round(l_knee[i], 2) if i < len(l_knee) and not np.isnan(l_knee[i]) else None,
                            "Sudut Ankle Kiri (°)": round(l_ankle[i], 2) if i < len(l_ankle) and not np.isnan(l_ankle[i]) else None,
                        })
                    df_kin_series = pd.DataFrame(kin_series)
                    df_kin_series.to_excel(writer, sheet_name="Deret Waktu Sudut", index=False)
                
                # Apply openpyxl styling & embed frame images
                workbook = writer.book
                
                header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
                header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                align_center = Alignment(horizontal="center", vertical="center")
                thin_border = Border(
                    left=Side(style='thin', color='D9D9D9'),
                    right=Side(style='thin', color='D9D9D9'),
                    top=Side(style='thin', color='D9D9D9'),
                    bottom=Side(style='thin', color='D9D9D9')
                )
                
                # Format standard sheets
                for sheetname in workbook.sheetnames:
                    ws = workbook[sheetname]
                    ws.views.sheetView[0].showGridLines = True
                    
                    # Format Header Row
                    for cell in ws[1]:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = align_center
                    
                    if sheetname != "Deret Waktu Sudut":
                        # Auto-adjust column widths for non-image sheets
                        for col in ws.columns:
                            max_len = 0
                            col_letter = col[0].column_letter
                            for cell in col:
                                cell.border = thin_border
                                cell.alignment = align_center
                                val_str = str(cell.value if cell.value is not None else '')
                                if len(val_str) > max_len:
                                    max_len = len(val_str)
                            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

                # Format 'Deret Waktu Sudut' sheet and insert video frame images
                if "Deret Waktu Sudut" in workbook.sheetnames:
                    ws_kin = workbook["Deret Waktu Sudut"]
                    
                    # Set explicit column widths
                    ws_kin.column_dimensions['A'].width = 10
                    ws_kin.column_dimensions['B'].width = 34  # Accommodate 240px image width
                    for col_letter in ['C', 'D', 'E', 'F', 'G', 'H']:
                        ws_kin.column_dimensions[col_letter].width = 24
                        
                    # Open video if path exists
                    cap = cv2.VideoCapture(video_path) if video_path and os.path.exists(video_path) else None
                    
                    num_rows = ws_kin.max_row
                    for row_idx in range(2, num_rows + 1):
                        ws_kin.row_dimensions[row_idx].height = 140  # Height for 180px thumbnail
                        frame_i = row_idx - 2
                        
                        # Apply borders & centering to data cells
                        for col_idx in range(1, 9):
                            c = ws_kin.cell(row=row_idx, column=col_idx)
                            c.border = thin_border
                            c.alignment = align_center
                            
                        # Extract and insert frame image into Column B
                        if cap and cap.isOpened():
                            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_i)
                            ret, frame_img = cap.read()
                            if ret:
                                resized = cv2.resize(frame_img, (240, 180), interpolation=cv2.INTER_AREA)
                                success_enc, buf = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                                if success_enc:
                                    img = Image(io.BytesIO(buf.tobytes()))
                                    img.width = 240
                                    img.height = 180
                                    ws_kin.add_image(img, f"B{row_idx}")
                                    
                    if cap:
                        cap.release()
                        
        except Exception as e:
            print(f"Warning: Failed to export Excel file: {e}")
            
        return excel_path
        
    def _export_kinematics_csv(self, path: str):
        """Export joint angle time series to CSV."""
        if not self.kinematics:
            return
        
        times = self.kinematics.get("time", [])
        r_hip = self.kinematics.get("right", {}).get("hip_angle", [])
        r_knee = self.kinematics.get("right", {}).get("knee_angle", [])
        r_ankle = self.kinematics.get("right", {}).get("ankle_angle", [])
        
        l_hip = self.kinematics.get("left", {}).get("hip_angle", [])
        l_knee = self.kinematics.get("left", {}).get("knee_angle", [])
        l_ankle = self.kinematics.get("left", {}).get("ankle_angle", [])
        
        fieldnames = [
            "frame", "time", 
            "right_hip_angle", "right_knee_angle", "right_ankle_angle",
            "left_hip_angle", "left_knee_angle", "left_ankle_angle"
        ]
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i in range(len(times)):
                writer.writerow({
                    "frame": i,
                    "time": f"{times[i]:.4f}",
                    "right_hip_angle": f"{r_hip[i]:.2f}" if i < len(r_hip) and not np.isnan(r_hip[i]) else "",
                    "right_knee_angle": f"{r_knee[i]:.2f}" if i < len(r_knee) and not np.isnan(r_knee[i]) else "",
                    "right_ankle_angle": f"{r_ankle[i]:.2f}" if i < len(r_ankle) and not np.isnan(r_ankle[i]) else "",
                    "left_hip_angle": f"{l_hip[i]:.2f}" if i < len(l_hip) and not np.isnan(l_hip[i]) else "",
                    "left_knee_angle": f"{l_knee[i]:.2f}" if i < len(l_knee) and not np.isnan(l_knee[i]) else "",
                    "left_ankle_angle": f"{l_ankle[i]:.2f}" if i < len(l_ankle) and not np.isnan(l_ankle[i]) else ""
                })
    
    def _export_step_csv(self, path: str):
        """Export step parameters to CSV."""
        if not self.step_data:
            return
        
        fieldnames = [
            "step_id", "start_side", "end_side",
            "start_frame", "end_frame", "start_time", "end_time",
            "step_time", "step_length", "step_velocity"
        ]
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for step in self.step_data:
                row = {k: step.get(k, "") for k in fieldnames}
                writer.writerow(row)
    
    def _export_cycle_csv(self, path: str):
        """Export cycle parameters to CSV."""
        if not self.cycle_data:
            return
        
        fieldnames = [
            "cycle_id", "side", "start_frame", "end_frame",
            "cycle_time", "stance_time", "swing_time",
            "stance_ratio", "swing_ratio",
            "stride_length", "walking_speed", "cadence"
        ]
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for cycle in self.cycle_data:
                row = {k: cycle.get(k, "") for k in fieldnames}
                writer.writerow(row)
    
    def _export_summary_csv(self, path: str):
        """Export summary statistics to CSV."""
        if not self.summary:
            return
        
        rows = []
        
        overall = self.summary.get("overall", {})
        for param, value in overall.items():
            rows.append({
                "parameter": param,
                "value": value,
                "unit": self._get_unit(param)
            })
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["parameter", "value", "unit"])
            writer.writeheader()
            writer.writerows(rows)
    
    def _get_unit(self, param: str) -> str:
        """Get unit for a parameter."""
        units = {
            "mean_cadence": "steps/min",
            "mean_walking_speed": "m/s",
            "mean_stride_length": "m",
            "mean_step_length": "m",
            "mean_stance_ratio": "ratio",
            "mean_swing_ratio": "ratio",
            "left_stance_ratio": "ratio",
            "left_swing_ratio": "ratio",
            "right_stance_ratio": "ratio",
            "right_swing_ratio": "ratio",
            "cycle_time": "s",
            "step_time": "s",
            "stance_time": "s",
            "swing_time": "s"
        }
        return units.get(param, "")
    
    def save_parameters(self, output_path: str) -> str:
        """
        Save all parameters to JSON file.
        
        Args:
            output_path: Path for output file
            
        Returns:
            Path to saved file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.parameters, f, indent=2)
        
        return output_path
    
    def load_events(self, events_path: str) -> Tuple[bool, str, Dict, List]:
        """
        Load events data from JSON file.
        
        Args:
            events_path: Path to events JSON file
            
        Returns:
            Tuple of (success, message, events, gait_cycles)
        """
        if not os.path.exists(events_path):
            return False, f"File not found: {events_path}", {}, []
        
        try:
            with open(events_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            events = data.get("events", {})
            gait_cycles = data.get("gait_cycles", [])
            
            return True, "Events loaded", events, gait_cycles
            
        except json.JSONDecodeError as e:
            return False, f"JSON error: {str(e)}", {}, []
    
    def load_pose_data(self, pose_path: str) -> Tuple[bool, str, Dict]:
        """
        Load pose data from JSON file.
        
        Args:
            pose_path: Path to pose JSON file
            
        Returns:
            Tuple of (success, message, data)
        """
        if not os.path.exists(pose_path):
            return False, f"File not found: {pose_path}", {}
        
        try:
            with open(pose_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return True, "Pose data loaded", data
            
        except json.JSONDecodeError as e:
            return False, f"JSON error: {str(e)}", {}
    
    def get_parameter_table(self) -> List[Dict]:
        """
        Get parameters in table format for GUI display.
        
        Returns:
            List of parameter rows matching reference format
        """
        rows = []
        
        # Check if using all cycles (including invalid ones)
        overall = self.summary.get("overall", {})
        warnings = self.summary.get("warnings", [])
        using_all_cycles = overall.get("using_all_cycles", False)
        
        # Add warning row if using invalid cycles
        if using_all_cycles or warnings:
            warning_msg = warnings[0] if warnings else "⚠️ Using all cycles (some exceed duration threshold)"
            rows.append({
                "parameter": "⚠️ Warning",
                "value": "Slow walking detected"
            })
        
        # Detected Steps
        step_count = len(self.step_data) if self.step_data else 0
        rows.append({
            "parameter": "Detected Steps",
            "value": str(step_count)
        })
        
        # Get overall stats
        step_stats = self.summary.get("step", {})
        cycle_stats = self.summary.get("cycle", {})
        
        # Cadence (steps/min)
        cadence = overall.get("mean_cadence", 0)
        rows.append({
            "parameter": "Cadence (steps/min)",
            "value": f"{cadence:.2f}" if cadence else "-"
        })
        
        # Step Length (cm) - convert from m to cm
        step_length_m = overall.get("mean_step_length", 0)
        step_length_cm = step_length_m * 100  # Convert to cm
        rows.append({
            "parameter": "Step Length (cm)",
            "value": f"{step_length_cm:.2f}" if step_length_m else "-"
        })
        
        # Walking Speed (m/s)
        walking_speed = overall.get("mean_walking_speed", 0)
        rows.append({
            "parameter": "Walking Speed (m/s)",
            "value": f"{walking_speed:.3f}" if walking_speed else "-"
        })
        
        # Avg Step Time (s)
        avg_step_time = step_stats.get("step_time", {}).get("mean", 0)
        rows.append({
            "parameter": "Avg Step Time (s)",
            "value": f"{avg_step_time:.3f}" if avg_step_time else "-"
        })
        
        # Left Stance (%) - calculate from left cycles only
        left_stance = self._get_side_stance_ratio("left")
        rows.append({
            "parameter": "Left Stance (%)",
            "value": f"{left_stance*100:.1f}" if left_stance else "-"
        })
        
        # Left Swing (%)
        left_swing = self._get_side_swing_ratio("left")
        rows.append({
            "parameter": "Left Swing (%)",
            "value": f"{left_swing*100:.1f}" if left_swing else "-"
        })
        
        # Right Stance (%)
        right_stance = self._get_side_stance_ratio("right")
        rows.append({
            "parameter": "Right Stance (%)",
            "value": f"{right_stance*100:.1f}" if right_stance else "-"
        })
        
        # Right Swing (%)
        right_swing = self._get_side_swing_ratio("right")
        rows.append({
            "parameter": "Right Swing (%)",
            "value": f"{right_swing*100:.1f}" if right_swing else "-"
        })
        
        return rows
    
    def _get_side_stance_ratio(self, side: str) -> float:
        """Get average stance ratio for a specific side."""
        if not self.cycle_data:
            return 0.0
        
        side_cycles = [c for c in self.cycle_data if c.get("side", "").lower() == side.lower()]
        if not side_cycles:
            # If no side-specific data, use overall
            return self.summary.get("overall", {}).get("mean_stance_ratio", 0.0)
        
        ratios = [c.get("stance_ratio", 0) for c in side_cycles if c.get("stance_ratio", 0) > 0]
        return float(np.mean(ratios)) if ratios else 0.0
    
    def _get_side_swing_ratio(self, side: str) -> float:
        """Get average swing ratio for a specific side."""
        if not self.cycle_data:
            return 0.0
        
        side_cycles = [c for c in self.cycle_data if c.get("side", "").lower() == side.lower()]
        if not side_cycles:
            return self.summary.get("overall", {}).get("mean_swing_ratio", 0.0)
        
        ratios = [c.get("swing_ratio", 0) for c in side_cycles if c.get("swing_ratio", 0) > 0]
        return float(np.mean(ratios)) if ratios else 0.0

